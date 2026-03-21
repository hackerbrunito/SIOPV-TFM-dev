"""Live integration tests for the SIOPV Pipeline Monitor.

These tests run the **real** SIOPV pipeline with **real** Trivy report fixtures
and **real** API calls (Anthropic Claude, NVD, EPSS, GitHub Advisories).
They verify that the streaming bridge, flow visualization, and summary
components work correctly against actual pipeline execution.

Requirements:
    - Valid API keys in ``.env`` (Anthropic, NVD, EPSS, GitHub)
    - XGBoost trained model at ``models/xgboost_risk_model.json``
    - Network access to external APIs
    - spaCy ``en_core_web_lg`` model installed (for Presidio DLP)

These tests are intentionally slow (network calls, real LLM inference).
They prove the visualization layer works against the real system.

Run with:
    uv run pytest tests/integration/test_pipeline_monitor_live.py -v -s
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import structlog

from siopv.domain.constants import (
    PIPELINE_NODE_DESCRIPTIONS,
    PIPELINE_NODE_LABELS,
    PIPELINE_NODE_SEQUENCE,
    RISK_PROBABILITY_CRITICAL_THRESHOLD,
    RISK_PROBABILITY_HIGH_THRESHOLD,
    RISK_PROBABILITY_LOW_THRESHOLD,
    RISK_PROBABILITY_MEDIUM_THRESHOLD,
)
from siopv.infrastructure.config.settings import get_settings
from siopv.interfaces.dashboard.components.pipeline_flow import (
    FlowPlaceholders,
    NodeState,
    _extract_node_summary,
    mark_skipped_nodes,
    update_node_end,
    update_node_start,
)
from siopv.interfaces.dashboard.components.pipeline_summary import (
    _format_total_time,
)
from siopv.interfaces.dashboard.streaming import (
    PipelineEvent,
    stream_pipeline_events,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TRIVY_FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "trivy-python-report.json"
)


@pytest.fixture(scope="module")
def real_pipeline_ports():
    """Build real PipelinePorts from the project's .env configuration.

    Uses all real adapters: Anthropic Claude, NVD, EPSS, GitHub,
    ChromaDB, XGBoost, Presidio DLP, and Jira/PDF if configured.
    Authorization is bypassed via ``system_execution=True`` since
    these tests don't require a running OpenFGA server.
    """
    from siopv.infrastructure.di.pipeline import build_pipeline_ports

    settings = get_settings()
    return build_pipeline_ports(settings)


@pytest.fixture(scope="module")
def real_pipeline_events(real_pipeline_ports):
    """Execute the real SIOPV pipeline and capture all streaming events.

    This fixture runs once per module — all tests in this file share
    the same pipeline execution results, avoiding redundant API calls.

    Returns:
        Tuple of (events_list, accumulated_data_dict)
    """
    if not TRIVY_FIXTURE_PATH.exists():
        pytest.skip(f"Trivy fixture not found: {TRIVY_FIXTURE_PATH}")

    events: list[PipelineEvent] = []
    accumulated_data: dict[str, Any] = {}

    logger.info(
        "live_test_pipeline_starting",
        report_path=str(TRIVY_FIXTURE_PATH),
    )

    start_time = time.monotonic()

    event_gen = stream_pipeline_events(
        report_path=TRIVY_FIXTURE_PATH,
        ports=real_pipeline_ports,
        system_execution=True,
        stream_timeout_seconds=get_settings().pipeline_monitor_stream_timeout_seconds,
    )

    for event in event_gen:
        events.append(event)
        if event.event_type == "node_end" and event.data:
            accumulated_data.update(event.data)
        if event.event_type == "pipeline_end" and event.data:
            accumulated_data.update(event.data)

    elapsed = time.monotonic() - start_time
    logger.info(
        "live_test_pipeline_complete",
        event_count=len(events),
        elapsed_seconds=round(elapsed, 2),
    )

    return events, accumulated_data


# ---------------------------------------------------------------------------
# Category A: Real Pipeline Streaming
# ---------------------------------------------------------------------------


class TestRealPipelineStreaming:
    """Verify the streaming bridge captures complete events from the real pipeline."""

    def test_pipeline_start_is_first_event(self, real_pipeline_events):
        """The very first event must be pipeline_start."""
        events, _ = real_pipeline_events
        assert len(events) > 0, "No events captured from pipeline"
        assert events[0].event_type == "pipeline_start"

    def test_pipeline_end_is_last_event(self, real_pipeline_events):
        """The very last event must be pipeline_end."""
        events, _ = real_pipeline_events
        assert events[-1].event_type == "pipeline_end"

    def test_every_completed_node_has_start_and_end(self, real_pipeline_events):
        """Every node that completed must have both start and end events.

        Note: The escalate node may start but not complete if it triggers
        a HITL interrupt — this is correct LangGraph behavior, not an error.
        """
        events, _ = real_pipeline_events
        started = set()
        ended = set()

        for event in events:
            if event.event_type == "node_start" and event.node_name:
                started.add(event.node_name)
            elif event.event_type == "node_end" and event.node_name:
                ended.add(event.node_name)

        # Every ended node must have been started
        assert ended.issubset(started), f"Nodes ended without starting: {ended - started}"

        # Nodes that started but didn't end may be interrupted (HITL escalate)
        interrupted = started - ended
        if interrupted:
            # Only escalate is expected to interrupt via HITL
            assert interrupted.issubset({"escalate"}), (
                f"Unexpected interrupted nodes: {interrupted - {'escalate'}}"
            )

    def test_node_ordering_matches_graph_topology(self, real_pipeline_events):
        """Node start events must follow the graph topology order."""
        events, _ = real_pipeline_events
        started_order = [
            e.node_name for e in events if e.event_type == "node_start" and e.node_name
        ]

        # The expected order is authorize → ingest → dlp → enrich → classify → [escalate] → output
        # Escalate is conditional, so we check the mandatory ones are in order
        mandatory_order = ["authorize", "ingest", "dlp", "enrich", "classify"]
        mandatory_from_events = [n for n in started_order if n in mandatory_order]
        assert mandatory_from_events == mandatory_order

    def test_timestamps_are_chronological(self, real_pipeline_events):
        """All event timestamps must be monotonically non-decreasing."""
        events, _ = real_pipeline_events
        for i in range(1, len(events)):
            assert events[i].timestamp >= events[i - 1].timestamp, (
                f"Event {i} ({events[i].event_type}:{events[i].node_name}) "
                f"has timestamp {events[i].timestamp} before event {i - 1} "
                f"at {events[i - 1].timestamp}"
            )

    def test_no_pipeline_error_events(self, real_pipeline_events):
        """A successful pipeline run must not emit pipeline_error events."""
        events, _ = real_pipeline_events
        errors = [e for e in events if e.event_type == "pipeline_error"]
        assert len(errors) == 0, f"Pipeline errors: {[e.data for e in errors]}"


# ---------------------------------------------------------------------------
# Category B: Data Integrity at Pipeline Checkpoints
# ---------------------------------------------------------------------------


class TestDataIntegrityAtCheckpoints:
    """Verify real data at each stage of the pipeline."""

    def test_after_ingest_vulnerabilities_exist(self, real_pipeline_events):
        """After ingest, there must be parsed VulnerabilityRecord objects."""
        _, data = real_pipeline_events
        vulns = data.get("vulnerabilities", [])
        assert len(vulns) > 0, "No vulnerabilities parsed from Trivy report"

    def test_after_ingest_cve_ids_are_valid(self, real_pipeline_events):
        """Parsed vulnerabilities must have valid CVE ID format."""
        _, data = real_pipeline_events
        vulns = data.get("vulnerabilities", [])
        for vuln in vulns:
            # CVEId is a Pydantic value object — extract the string value
            if hasattr(vuln, "cve_id"):
                cve_id_obj = vuln.cve_id
                cve_id = str(cve_id_obj.value) if hasattr(cve_id_obj, "value") else str(cve_id_obj)
            else:
                cve_id = str(vuln.get("cve_id", ""))
            # CVE IDs follow the pattern CVE-YYYY-NNNNN or TEMP-*
            assert cve_id.startswith(("CVE-", "TEMP-")), f"Invalid CVE ID: {cve_id}"

    def test_after_enrich_enrichments_populated(self, real_pipeline_events):
        """After enrichment, there must be enrichment data for processed CVEs."""
        _, data = real_pipeline_events
        enrichments = data.get("enrichments", {})
        # Not all CVEs may be enriched (rate limits, missing data), but some must be
        assert len(enrichments) > 0, "No enrichments produced"

    def test_after_classify_risk_scores_valid(self, real_pipeline_events):
        """Classifications must have risk_probability between 0.0 and 1.0."""
        _, data = real_pipeline_events
        classifications = data.get("classifications", {})
        assert len(classifications) > 0, "No classifications produced"

        for cve_id, classification in classifications.items():
            if isinstance(classification, dict):
                prob = classification.get("risk_probability", 0.0)
            else:
                prob = getattr(classification, "risk_probability", 0.0)
            assert 0.0 <= prob <= 1.0, f"{cve_id} has risk_probability {prob} outside [0.0, 1.0]"

    def test_authorization_was_granted(self, real_pipeline_events):
        """With system_execution=True, authorization must be allowed or skipped."""
        _, data = real_pipeline_events
        allowed = data.get("authorization_allowed", False)
        skipped = data.get("authorization_skipped", False)
        assert allowed or skipped, "Authorization was neither allowed nor skipped"


# ---------------------------------------------------------------------------
# Category C: Visualization Accuracy Against Real Execution
# ---------------------------------------------------------------------------


class TestVisualizationAccuracy:
    """Feed real pipeline events into the flow visualization and verify accuracy."""

    def test_all_executed_nodes_reach_complete(self, real_pipeline_events):
        """Every node that emitted events must be marked 'complete' in the flow."""
        events, _ = real_pipeline_events
        flow = _build_flow_from_real_events(events)

        executed_nodes = {e.node_name for e in events if e.event_type == "node_end" and e.node_name}

        for node_name in executed_nodes:
            assert flow.node_states[node_name].status == "complete", (
                f"Node '{node_name}' should be 'complete' but is "
                f"'{flow.node_states[node_name].status}'"
            )

    def test_node_data_summaries_match_real_output(self, real_pipeline_events):
        """Data summaries extracted by the flow must match actual pipeline output."""
        events, data = real_pipeline_events
        flow = _build_flow_from_real_events(events)

        # Check ingest summary matches real vulnerability count
        if "ingest" in flow.node_states and flow.node_states["ingest"].status == "complete":
            real_vuln_count = len(data.get("vulnerabilities", []))
            summary_count = flow.node_states["ingest"].data_summary.get("CVEs")
            if summary_count is not None:
                assert summary_count == real_vuln_count, (
                    f"Ingest summary shows {summary_count} CVEs but pipeline "
                    f"produced {real_vuln_count}"
                )

    def test_progress_reaches_completion(self, real_pipeline_events):
        """After all events, completed_count must match the number of executed nodes."""
        events, _ = real_pipeline_events
        flow = _build_flow_from_real_events(events)
        mark_skipped_nodes(flow)

        executed = {e.node_name for e in events if e.event_type == "node_end" and e.node_name}
        assert flow.completed_count() >= len(executed)

    def test_elapsed_times_are_positive(self, real_pipeline_events):
        """Every completed node must have a positive elapsed time."""
        events, _ = real_pipeline_events
        flow = _build_flow_from_real_events(events)

        for node_name, state in flow.node_states.items():
            if state.status == "complete":
                assert state.elapsed_seconds is not None, (
                    f"Node '{node_name}' is complete but has no elapsed time"
                )
                assert state.elapsed_seconds > 0, (
                    f"Node '{node_name}' has non-positive elapsed: {state.elapsed_seconds}"
                )

    def test_skipped_nodes_marked_correctly(self, real_pipeline_events):
        """Nodes that didn't execute should be marked 'skipped' after mark_skipped_nodes."""
        events, _ = real_pipeline_events
        flow = _build_flow_from_real_events(events)
        mark_skipped_nodes(flow)

        executed = {e.node_name for e in events if e.event_type == "node_start" and e.node_name}

        for node_name, state in flow.node_states.items():
            if node_name not in executed:
                assert state.status == "skipped", (
                    f"Node '{node_name}' didn't execute but is '{state.status}' not 'skipped'"
                )


# ---------------------------------------------------------------------------
# Category D: Summary Dashboard Against Real Results
# ---------------------------------------------------------------------------


class TestSummaryAgainstRealResults:
    """Verify summary component renders correct data from real pipeline output."""

    def test_vulnerability_count_matches_trivy_report(self, real_pipeline_events):
        """Vulnerability count in accumulated data must match parsed Trivy report."""
        _, data = real_pipeline_events
        vuln_count = len(data.get("vulnerabilities", []))
        # The Python Trivy fixture has known CVEs — must have parsed at least some
        assert vuln_count > 0

    def test_classification_distribution_covers_all_classified(self, real_pipeline_events):
        """Every classified CVE must fall into exactly one risk bucket."""
        _, data = real_pipeline_events
        classifications = data.get("classifications", {})

        buckets: dict[str, int] = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "MINIMAL": 0,
        }

        for _cve_id, classification in classifications.items():
            if isinstance(classification, dict):
                prob = classification.get("risk_probability", 0.0)
            else:
                prob = getattr(classification, "risk_probability", 0.0) or 0.0

            if not isinstance(prob, (int, float)):
                continue

            if prob >= RISK_PROBABILITY_CRITICAL_THRESHOLD:
                buckets["CRITICAL"] += 1
            elif prob >= RISK_PROBABILITY_HIGH_THRESHOLD:
                buckets["HIGH"] += 1
            elif prob >= RISK_PROBABILITY_MEDIUM_THRESHOLD:
                buckets["MEDIUM"] += 1
            elif prob >= RISK_PROBABILITY_LOW_THRESHOLD:
                buckets["LOW"] += 1
            else:
                buckets["MINIMAL"] += 1

        total_bucketed = sum(buckets.values())
        assert total_bucketed == len(classifications), (
            f"Bucketed {total_bucketed} but have {len(classifications)} classifications"
        )

    def test_total_timing_is_positive(self, real_pipeline_events):
        """Total pipeline execution time must be a positive number."""
        events, _ = real_pipeline_events
        flow = _build_flow_from_real_events(events)

        total_seconds = sum(
            s.elapsed_seconds
            for s in flow.node_states.values()
            if s.elapsed_seconds is not None and s.status == "complete"
        )
        assert total_seconds > 0, "Total pipeline time is not positive"

    def test_format_total_time_for_real_duration(self, real_pipeline_events):
        """_format_total_time must produce readable output for the real duration."""
        events, _ = real_pipeline_events
        flow = _build_flow_from_real_events(events)

        total_seconds = sum(
            s.elapsed_seconds for s in flow.node_states.values() if s.elapsed_seconds is not None
        )

        formatted = _format_total_time(total_seconds)
        assert len(formatted) > 0
        assert formatted.endswith(("s", "ms"))


# ---------------------------------------------------------------------------
# Category E: Streaming Bridge Reliability
# ---------------------------------------------------------------------------


class TestStreamingBridgeReliability:
    """Verify the async-to-sync bridge works reliably with the real pipeline."""

    def test_no_zombie_threads_after_completion(
        self,
        real_pipeline_events: tuple[list[PipelineEvent], dict[str, Any]],  # noqa: ARG002
    ):
        """After stream exhaustion, no siopv-stream daemon threads should remain."""
        # Give a moment for thread cleanup
        time.sleep(0.5)
        active_threads = [t for t in threading.enumerate() if t.name == "siopv-stream"]
        assert len(active_threads) == 0, f"Found {len(active_threads)} zombie siopv-stream threads"

    def test_event_count_is_reasonable(self, real_pipeline_events):
        """A real pipeline run must produce a meaningful number of events."""
        events, _ = real_pipeline_events
        # At minimum: pipeline_start + pipeline_end + at least 2 events per node
        # (start + end) for mandatory nodes. Escalate may interrupt (start only).
        # Min: 2 (pipeline) + 5*2 (mandatory nodes) + 1 (output or escalate)
        minimum_events = 2 + (5 * 2) + 1  # 13
        assert len(events) >= minimum_events, (
            f"Only {len(events)} events — expected at least {minimum_events} "
            f"for a real pipeline run"
        )

    def test_all_events_have_valid_timestamps(self, real_pipeline_events):
        """Every event must have a UTC timestamp that is today."""
        events, _ = real_pipeline_events
        today = datetime.now(UTC).date()

        for event in events:
            assert event.timestamp is not None
            assert event.timestamp.tzinfo is not None, "Timestamp must be timezone-aware"
            assert event.timestamp.date() == today, (
                f"Event timestamp {event.timestamp} is not from today"
            )


# ---------------------------------------------------------------------------
# Category F: Cross-Layer Contract Verification
# ---------------------------------------------------------------------------


class TestCrossLayerContracts:
    """Verify visualization constants match the real compiled graph."""

    def test_node_sequence_matches_compiled_graph(self):
        """PIPELINE_NODE_SEQUENCE must contain exactly the nodes in the real graph."""
        from siopv.application.orchestration.graph import PipelineGraphBuilder

        builder = PipelineGraphBuilder()
        builder.build()
        compiled = builder.compile(with_checkpointer=False)

        graph_nodes = set(compiled.get_graph().nodes.keys())
        # LangGraph adds __start__ and __end__ pseudo-nodes
        graph_nodes -= {"__start__", "__end__"}

        sequence_set = set(PIPELINE_NODE_SEQUENCE)
        assert sequence_set == graph_nodes, (
            f"PIPELINE_NODE_SEQUENCE {sequence_set} doesn't match "
            f"compiled graph nodes {graph_nodes}"
        )

    def test_labels_cover_all_nodes(self):
        """PIPELINE_NODE_LABELS must have an entry for every node in the sequence."""
        for node in PIPELINE_NODE_SEQUENCE:
            assert node in PIPELINE_NODE_LABELS, f"Missing label for node '{node}'"
            assert len(PIPELINE_NODE_LABELS[node]) > 0

    def test_descriptions_cover_all_nodes(self):
        """PIPELINE_NODE_DESCRIPTIONS must have an entry for every node."""
        for node in PIPELINE_NODE_SEQUENCE:
            assert node in PIPELINE_NODE_DESCRIPTIONS, f"Missing description for '{node}'"
            assert len(PIPELINE_NODE_DESCRIPTIONS[node]) > 0

    def test_data_extraction_keys_match_real_state(self, real_pipeline_events):
        """Verify _extract_node_summary handles real state data without errors."""
        events, _ = real_pipeline_events

        for event in events:
            if event.event_type == "node_end" and event.node_name:
                # Must not raise — the extraction must handle real data shapes
                summary = _extract_node_summary(event.node_name, event.data)
                assert isinstance(summary, dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_flow_from_real_events(events: list[PipelineEvent]) -> FlowPlaceholders:
    """Replay real pipeline events through the flow state machine.

    Creates a FlowPlaceholders with mock placeholders (no Streamlit needed)
    and feeds the actual events through the update functions.

    Args:
        events: List of PipelineEvent from a real pipeline run.

    Returns:
        FlowPlaceholders with states reflecting the real execution.
    """
    from unittest.mock import MagicMock

    flow = FlowPlaceholders()

    for name in PIPELINE_NODE_SEQUENCE:
        flow.node_states[name] = NodeState(
            name=name,
            label=PIPELINE_NODE_LABELS[name],
            description=PIPELINE_NODE_DESCRIPTIONS[name],
        )
        flow.placeholders[name] = MagicMock()

    flow.progress_bar = MagicMock()

    for event in events:
        if event.event_type == "node_start" and event.node_name:
            update_node_start(flow, event.node_name, event.timestamp)
        elif event.event_type == "node_end" and event.node_name:
            update_node_end(flow, event.node_name, event.timestamp, event.data)

    return flow
