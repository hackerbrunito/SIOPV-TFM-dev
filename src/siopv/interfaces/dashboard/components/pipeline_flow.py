"""Pipeline flow visualization component for the SIOPV monitor dashboard.

Renders a horizontal node chain with live status indicators, elapsed time,
and data summaries per node.  Uses ``st.empty()`` placeholders for in-place
updates during streaming execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

import streamlit as st

from siopv.domain.constants import (
    MILLISECONDS_THRESHOLD,
    PIPELINE_NODE_DESCRIPTIONS,
    PIPELINE_NODE_LABELS,
    PIPELINE_NODE_SEQUENCE,
    SECONDS_PER_MINUTE,
)

# ---------------------------------------------------------------------------
# Node state tracking
# ---------------------------------------------------------------------------

NodeStatus = Literal["pending", "running", "complete", "skipped", "error"]

_STATUS_ICONS: dict[NodeStatus, str] = {
    "pending": "⬜",
    "running": "🔄",
    "complete": "✅",
    "skipped": "⏭️",
    "error": "❌",
}

_STATUS_COLORS: dict[NodeStatus, str] = {
    "pending": "#6b7280",
    "running": "#3b82f6",
    "complete": "#22c55e",
    "skipped": "#a3a3a3",
    "error": "#ef4444",
}


@dataclass
class NodeState:
    """Tracks the runtime state of a single pipeline node.

    Attributes:
        name: Internal node name (e.g. ``"authorize"``).
        label: Human-readable display label.
        description: Tooltip description of the node's purpose.
        status: Current execution status.
        started_at: UTC timestamp when the node started executing.
        completed_at: UTC timestamp when the node finished.
        data_summary: Key-value pairs extracted from the node's output.
        error_message: Error detail if the node failed.
    """

    name: str
    label: str
    description: str
    status: NodeStatus = "pending"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    data_summary: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None

    @property
    def elapsed_seconds(self) -> float | None:
        """Calculate elapsed time in seconds, or ``None`` if not started."""
        if self.started_at is None:
            return None
        end = self.completed_at or datetime.now(UTC)
        return (end - self.started_at).total_seconds()

    @property
    def elapsed_display(self) -> str:
        """Human-readable elapsed time string."""
        elapsed = self.elapsed_seconds
        if elapsed is None:
            return ""
        if elapsed < MILLISECONDS_THRESHOLD:
            return f"{elapsed * 1000:.0f}ms"
        if elapsed < SECONDS_PER_MINUTE:
            return f"{elapsed:.1f}s"
        minutes = int(elapsed // SECONDS_PER_MINUTE)
        seconds = elapsed % SECONDS_PER_MINUTE
        return f"{minutes}m {seconds:.0f}s"


# ---------------------------------------------------------------------------
# Placeholder manager
# ---------------------------------------------------------------------------


@dataclass
class FlowPlaceholders:
    """Manages ``st.empty()`` placeholders for each pipeline node.

    Created once during the Streamlit script run, then updated in-place
    as streaming events arrive.

    Attributes:
        node_states: Ordered mapping of node name to ``NodeState``.
        placeholders: Mapping of node name to ``st.empty()`` widget.
        progress_bar: The overall progress bar placeholder.
    """

    node_states: dict[str, NodeState] = field(default_factory=dict)
    placeholders: dict[str, Any] = field(default_factory=dict)
    progress_bar: Any = None

    def completed_count(self) -> int:
        """Count nodes that have finished (complete or skipped)."""
        return sum(1 for ns in self.node_states.values() if ns.status in ("complete", "skipped"))


def create_flow_placeholders() -> FlowPlaceholders:
    """Create the visual pipeline flow layout with empty placeholders.

    Renders a horizontal row of node cards connected by arrows, plus
    an overall progress bar.  Each card is backed by a ``st.empty()``
    placeholder that can be updated in-place.

    Returns:
        ``FlowPlaceholders`` instance ready for updates.
    """
    flow = FlowPlaceholders()

    # Initialize node states
    for name in PIPELINE_NODE_SEQUENCE:
        flow.node_states[name] = NodeState(
            name=name,
            label=PIPELINE_NODE_LABELS[name],
            description=PIPELINE_NODE_DESCRIPTIONS[name],
        )

    # Progress bar
    flow.progress_bar = st.empty()
    flow.progress_bar.progress(0.0, text="Pipeline ready")

    # Render node cards in columns
    cols = st.columns(len(PIPELINE_NODE_SEQUENCE))
    for i, name in enumerate(PIPELINE_NODE_SEQUENCE):
        with cols[i]:
            flow.placeholders[name] = st.empty()
            _render_node_card(flow.placeholders[name], flow.node_states[name])

    return flow


def update_node_start(flow: FlowPlaceholders, node_name: str, timestamp: datetime) -> None:
    """Mark a node as running and update its placeholder.

    Args:
        flow: The flow placeholders instance.
        node_name: Internal name of the node that started.
        timestamp: UTC timestamp of the start event.
    """
    if node_name not in flow.node_states:
        return

    state = flow.node_states[node_name]
    state.status = "running"
    state.started_at = timestamp

    _render_node_card(flow.placeholders[node_name], state)
    _update_progress(flow)


def update_node_end(
    flow: FlowPlaceholders,
    node_name: str,
    timestamp: datetime,
    data: dict[str, Any],
) -> None:
    """Mark a node as complete and update its placeholder with output data.

    Args:
        flow: The flow placeholders instance.
        node_name: Internal name of the node that completed.
        timestamp: UTC timestamp of the end event.
        data: State update produced by the node (for extracting summaries).
    """
    if node_name not in flow.node_states:
        return

    state = flow.node_states[node_name]
    state.status = "complete"
    state.completed_at = timestamp
    state.data_summary = _extract_node_summary(node_name, data)

    _render_node_card(flow.placeholders[node_name], state)
    _update_progress(flow)


def update_node_error(
    flow: FlowPlaceholders,
    node_name: str,
    error_message: str,
) -> None:
    """Mark a node as errored.

    Args:
        flow: The flow placeholders instance.
        node_name: Internal name of the node that failed.
        error_message: Error description.
    """
    if node_name not in flow.node_states:
        return

    state = flow.node_states[node_name]
    state.status = "error"
    state.completed_at = datetime.now(UTC)
    state.error_message = error_message

    _render_node_card(flow.placeholders[node_name], state)
    _update_progress(flow)


def mark_skipped_nodes(flow: FlowPlaceholders) -> None:
    """Mark all remaining pending nodes as skipped (e.g. escalate not triggered).

    Args:
        flow: The flow placeholders instance.
    """
    for name, state in flow.node_states.items():
        if state.status == "pending":
            state.status = "skipped"
            _render_node_card(flow.placeholders[name], state)
    _update_progress(flow)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _render_node_card(placeholder: Any, state: NodeState) -> None:
    """Render a single node card into its placeholder.

    Uses ``st.markdown`` with inline CSS for a compact card layout.
    The card shows status icon, label, elapsed time, and a data summary.

    Args:
        placeholder: ``st.empty()`` widget to render into.
        state: Current node state.
    """
    icon = _STATUS_ICONS[state.status]
    color = _STATUS_COLORS[state.status]
    elapsed = state.elapsed_display

    # Build summary lines
    summary_lines: list[str] = []
    if elapsed:
        summary_lines.append(elapsed)
    for key, value in state.data_summary.items():
        summary_lines.append(f"{key}: {value}")
    if state.error_message:
        summary_lines.append(f"Error: {state.error_message[:50]}")

    summary_html = "<br>".join(summary_lines) if summary_lines else "&nbsp;"

    card_html = f"""
    <div style="
        border: 2px solid {color};
        border-radius: 8px;
        padding: 8px;
        text-align: center;
        min-height: 100px;
        background: {"#1e293b" if state.status == "running" else "#0e1117"};
    ">
        <div style="font-size: 1.4em;">{icon}</div>
        <div style="font-weight: bold; color: {color}; font-size: 0.85em; margin: 4px 0;">
            {state.label}
        </div>
        <div style="font-size: 0.75em; color: #9ca3af;">
            {summary_html}
        </div>
    </div>
    """
    placeholder.markdown(card_html, unsafe_allow_html=True)


def _update_progress(flow: FlowPlaceholders) -> None:
    """Update the overall progress bar.

    Args:
        flow: The flow placeholders instance.
    """
    total = len(PIPELINE_NODE_SEQUENCE)
    completed = flow.completed_count()
    has_running = any(s.status == "running" for s in flow.node_states.values())
    has_error = any(s.status == "error" for s in flow.node_states.values())

    progress = completed / total if total > 0 else 0.0

    if has_error:
        text = f"Pipeline error — {completed}/{total} nodes completed"
    elif completed == total or (completed > 0 and not has_running):
        text = f"Pipeline complete — {completed}/{total} nodes"
    elif has_running:
        running_names = [
            PIPELINE_NODE_LABELS[s.name] for s in flow.node_states.values() if s.status == "running"
        ]
        text = f"Running: {', '.join(running_names)} — {completed}/{total} complete"
    else:
        text = "Pipeline ready"

    flow.progress_bar.progress(progress, text=text)


def _extract_node_summary(node_name: str, data: dict[str, Any]) -> dict[str, Any]:
    """Extract a human-readable summary from a node's output data.

    Each node produces different state updates.  Uses a dispatch table
    to map node names to their respective extraction functions.

    Args:
        node_name: Internal name of the completed node.
        data: State update dict from the node.

    Returns:
        Dict of label-value pairs for display.
    """
    extractor = _NODE_SUMMARY_EXTRACTORS.get(node_name)
    if extractor is None:
        return {}
    result: dict[str, Any] = extractor(data)
    return result


def _extract_authorize(data: dict[str, Any]) -> dict[str, Any]:
    allowed = data.get("authorization_allowed")
    if allowed is not None:
        return {"Access": "Granted" if allowed else "Denied"}
    return {}


def _extract_ingest(data: dict[str, Any]) -> dict[str, Any]:
    vulns = data.get("vulnerabilities")
    if isinstance(vulns, list):
        return {"CVEs": len(vulns)}
    return {}


def _extract_dlp(data: dict[str, Any]) -> dict[str, Any]:
    dlp_result = data.get("dlp_result")
    if isinstance(dlp_result, dict):
        return {"Sanitized": dlp_result.get("sanitized_count", 0)}
    return {}


def _extract_enrich(data: dict[str, Any]) -> dict[str, Any]:
    enrichments = data.get("enrichments")
    if isinstance(enrichments, dict):
        return {"Enriched": len(enrichments)}
    return {}


def _extract_classify(data: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    classifications = data.get("classifications")
    if isinstance(classifications, dict):
        summary["Classified"] = len(classifications)
    escalated = data.get("escalated_cves")
    if isinstance(escalated, list) and escalated:
        summary["Escalated"] = len(escalated)
    return summary


def _extract_escalate(data: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    decision = data.get("human_decision")
    if decision:
        summary["Decision"] = decision
    level = data.get("escalation_level")
    if level is not None:
        summary["Level"] = level
    return summary


def _extract_output(data: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    jira_keys = data.get("output_jira_keys")
    if isinstance(jira_keys, list) and jira_keys:
        summary["Jira"] = len(jira_keys)
    if data.get("output_pdf_path"):
        summary["PDF"] = "Generated"
    errors = data.get("output_errors")
    if isinstance(errors, list) and errors:
        summary["Warnings"] = len(errors)
    return summary


_NODE_SUMMARY_EXTRACTORS: dict[str, Any] = {
    "authorize": _extract_authorize,
    "ingest": _extract_ingest,
    "dlp": _extract_dlp,
    "enrich": _extract_enrich,
    "classify": _extract_classify,
    "escalate": _extract_escalate,
    "output": _extract_output,
}


__all__ = [
    "FlowPlaceholders",
    "NodeState",
    "NodeStatus",
    "create_flow_placeholders",
    "mark_skipped_nodes",
    "update_node_end",
    "update_node_error",
    "update_node_start",
]
