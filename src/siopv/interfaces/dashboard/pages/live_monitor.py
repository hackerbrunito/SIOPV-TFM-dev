"""SIOPV Live Pipeline Monitor — Page 2.

Two modes:
1. **Observer mode** — passively watches for webhook-triggered pipeline
   executions by polling the checkpoint database.
2. **Manual mode** — user uploads/specifies a Trivy report and triggers
   execution directly.

Architecture (observer):
  - ``st.graphviz_chart`` renders the pipeline diagram as an inline SVG.
    Unlike iframe-based components (streamlit-flow, agraph), built-in
    Streamlit chart elements update the existing DOM node in-place via
    dagre-d3, avoiding destroy/recreate flicker on reruns.
  - ``@st.fragment(run_every=2)`` runs an *invisible* poller (zero UI)
    that only calls ``st.rerun()`` when the pipeline state actually
    changes.  This means the diagram is rock-stable when idle.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

import graphviz  # type: ignore[import-not-found]
import streamlit as st
import structlog

from siopv.domain.constants import (
    PIPELINE_NODE_DESCRIPTIONS,
    PIPELINE_NODE_LABELS,
    PIPELINE_NODE_SEQUENCE,
)
from siopv.interfaces.dashboard.components.observer import (
    PipelineRunInfo,
    get_active_runs,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Node status → Graphviz style mapping
# ---------------------------------------------------------------------------

_GRAPHVIZ_STYLES: dict[str, dict[str, str]] = {
    "pending": {
        "fillcolor": "#374151",
        "color": "#6b7280",
        "fontcolor": "#9ca3af",
        "style": "filled,rounded",
    },
    "running": {
        "fillcolor": "#1e3a5f",
        "color": "#3b82f6",
        "fontcolor": "#93c5fd",
        "style": "filled,rounded,bold",
    },
    "complete": {
        "fillcolor": "#14532d",
        "color": "#22c55e",
        "fontcolor": "#86efac",
        "style": "filled,rounded",
    },
    "error": {
        "fillcolor": "#450a0a",
        "color": "#ef4444",
        "fontcolor": "#fca5a5",
        "style": "filled,rounded",
    },
    "skipped": {
        "fillcolor": "#1f2937",
        "color": "#4b5563",
        "fontcolor": "#6b7280",
        "style": "filled,rounded,dashed",
    },
}

_STATUS_ICONS: dict[str, str] = {
    "pending": "",
    "running": " ...",
    "complete": " OK",
    "error": " !",
    "skipped": " --",
}

# Edge pairs for the pipeline graph
_EDGE_PAIRS: list[tuple[str, str]] = [
    ("authorize", "ingest"),
    ("ingest", "dlp"),
    ("dlp", "enrich"),
    ("enrich", "classify"),
    ("classify", "escalate"),
    ("classify", "output"),
    ("escalate", "output"),
]


def render_live_monitor() -> None:
    """Render the Live Pipeline Monitor page."""
    st.header("Live Pipeline Monitor")

    graph = st.session_state.get("shared_graph")
    conn = st.session_state.get("shared_conn")

    if graph is None or conn is None:
        st.error("Dashboard not properly initialized.")
        return

    # Mode selector
    mode = st.radio(
        "Monitor Mode",
        ["Observer (auto-detect webhook pipelines)", "Manual (upload Trivy report)"],
        horizontal=True,
    )

    st.divider()

    if mode.startswith("Observer"):
        _render_observer_mode(graph, conn)
    else:
        _render_manual_mode()


# ---------------------------------------------------------------------------
# Observer mode
# ---------------------------------------------------------------------------


def _build_observer_fingerprint(run: PipelineRunInfo) -> str:
    """Build a compact hash to detect when the observer state changes."""
    data = {
        "tid": run.thread_id,
        "step": run.step_count,
        "completed": sorted(run.completed_nodes),
        "pending": list(run.pending_nodes),
        "running": run.is_running,
        "interrupted": run.is_interrupted,
    }
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _render_observer_mode(graph: Any, conn: sqlite3.Connection) -> None:
    """Render observer mode with invisible polling and stable Graphviz diagram.

    Pattern: the ``@st.fragment(run_every=2)`` poller contains ZERO visible
    UI elements.  It only reads SQLite and conditionally calls ``st.rerun()``
    when the pipeline state transitions.  The Graphviz diagram is rendered
    outside the fragment as a regular Streamlit element, so it is only
    redrawn on actual full-page reruns (i.e. when state changes).
    """
    # ── Initial load ──────────────────────────────────────────────────
    if "observed_run" not in st.session_state:
        _poll_once(graph, conn)

    # ── Controls ──────────────────────────────────────────────────────
    watching = st.session_state.get("_observer_watching", False)
    col1, col2 = st.columns([1, 4])
    with col1:
        if watching:
            if st.button("Stop Auto-Refresh"):
                st.session_state["_observer_watching"] = False
                st.rerun()
        elif st.button("Start Auto-Refresh", type="primary"):
            st.session_state["_observer_watching"] = True
            st.rerun()
    with col2:
        if watching:
            st.caption("Polling every 2 seconds — diagram updates only on state changes")
        else:
            st.caption("Auto-refresh paused")

    # ── Invisible poller (ZERO UI inside) ─────────────────────────────
    if watching:

        @st.fragment(run_every=2)
        def _silent_poller() -> None:
            prev_fp = st.session_state.get("_observer_fingerprint", "")
            _poll_once(graph, conn)
            new_fp = st.session_state.get("_observer_fingerprint", "")
            if new_fp != prev_fp:
                st.rerun()

        _silent_poller()

    # ── Render the diagram (outside the fragment — stable) ────────────
    observed_run: PipelineRunInfo | None = st.session_state.get("observed_run")

    if observed_run is None:
        st.info("No pipeline runs found. Send a Trivy report via webhook to start.")
        return

    _render_pipeline_graphviz(observed_run)

    is_active = st.session_state.get("_observer_is_active", False)
    if is_active:
        st.caption(
            f"Observing thread {observed_run.thread_id[:12]}... "
            f"| Step {observed_run.step_count} "
            f"| {observed_run.vulnerability_count} CVEs"
        )
    else:
        st.caption("Last completed pipeline run")

    _render_node_detail_panel(observed_run)


def _poll_once(graph: Any, conn: sqlite3.Connection) -> None:
    """Single poll: check for active runs, fall back to completed."""
    active = get_active_runs(graph, conn)

    if active:
        run = active[0]
        st.session_state["observed_run"] = run
        st.session_state["_observer_fingerprint"] = _build_observer_fingerprint(run)
        st.session_state["_observer_is_active"] = True
        return

    # No active — only query completed if we don't already have one cached
    if st.session_state.get("_observer_is_active") is False:
        return

    from siopv.interfaces.dashboard.components.observer import (  # noqa: PLC0415
        get_completed_runs,
    )

    recent = get_completed_runs(graph, conn, limit=1)
    if recent:
        run = recent[0]
        st.session_state["observed_run"] = run
        st.session_state["_observer_fingerprint"] = _build_observer_fingerprint(run)
    st.session_state["_observer_is_active"] = False


# ---------------------------------------------------------------------------
# Manual mode (delegates to existing pipeline_monitor)
# ---------------------------------------------------------------------------


def _render_manual_mode() -> None:
    """Render manual execution mode.

    Delegates to the existing pipeline_monitor module's execution logic.
    """
    from siopv.interfaces.dashboard.pipeline_monitor import (  # noqa: PLC0415
        _execute_pipeline,
        _initialize_session_state,
        _render_sidebar,
        _resolve_report_path,
    )

    _initialize_session_state()
    config = _render_sidebar()
    report_path = _resolve_report_path(config)

    if (
        st.button(
            "Execute Pipeline",
            type="primary",
            disabled=st.session_state.get("pipeline_running", False) or report_path is None,
        )
        and report_path is not None
    ):
        _execute_pipeline(config, report_path)


# ---------------------------------------------------------------------------
# Pipeline flow diagram (Graphviz — built-in, no iframe, no flicker)
# ---------------------------------------------------------------------------


def _render_pipeline_graphviz(run: PipelineRunInfo) -> None:
    """Render the pipeline as a Graphviz directed graph.

    Uses ``st.graphviz_chart`` which is a built-in Streamlit element that
    updates its SVG in-place via dagre-d3, avoiding the destroy/recreate
    cycle that causes flickering with iframe-based custom components.

    Args:
        run: Current pipeline run information.
    """
    dot = graphviz.Digraph(
        "pipeline",
        graph_attr={
            "rankdir": "LR",
            "bgcolor": "transparent",
            "splines": "ortho",
            "nodesep": "0.6",
            "ranksep": "0.8",
            "pad": "0.3",
        },
        node_attr={
            "shape": "box",
            "fontname": "Helvetica",
            "fontsize": "11",
            "width": "1.4",
            "height": "0.5",
            "penwidth": "2",
        },
        edge_attr={
            "arrowsize": "0.8",
            "penwidth": "1.5",
        },
    )

    completed = run.completed_nodes
    pending_next = set(run.pending_nodes)

    for i, node_name in enumerate(PIPELINE_NODE_SEQUENCE):
        # Determine status
        if node_name in completed:
            status = "complete"
        elif node_name in pending_next or (run.is_interrupted and node_name == "escalate"):
            status = "running"
        else:
            later_nodes = set(PIPELINE_NODE_SEQUENCE[i + 1 :])
            status = "skipped" if later_nodes & completed else "pending"

        gv_style = _GRAPHVIZ_STYLES[status]
        label = PIPELINE_NODE_LABELS[node_name] + _STATUS_ICONS[status]

        dot.node(node_name, label, **gv_style)

    for source, target in _EDGE_PAIRS:
        is_active = source in completed and (target in pending_next or target in completed)
        dot.edge(
            source,
            target,
            color="#3b82f6" if is_active else "#4b5563",
            penwidth="2.5" if is_active else "1.0",
        )

    st.graphviz_chart(dot)


# ---------------------------------------------------------------------------
# Node detail panel
# ---------------------------------------------------------------------------


def _render_node_detail_panel(run: PipelineRunInfo) -> None:
    """Render detail panel for the selected pipeline node.

    Shows description, status, and extracted data from the pipeline state.

    Args:
        run: Current pipeline run information.
    """
    selected_node = st.session_state.get("selected_flow_node")

    if selected_node is None:
        # Show a summary instead of "click a node"
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Vulnerabilities", run.vulnerability_count)
        col2.metric("Classified", run.classification_count)
        col3.metric("Escalated", run.escalated_count)
        col4.metric("Errors", run.error_count)
        return

    if selected_node not in PIPELINE_NODE_LABELS:
        return

    label = PIPELINE_NODE_LABELS[selected_node]
    description = PIPELINE_NODE_DESCRIPTIONS[selected_node]
    state = run.current_state

    is_completed = selected_node in run.completed_nodes

    with st.expander(f"Node Detail: {label}", expanded=True):
        st.markdown(f"**{label}**")
        st.markdown(description)

        if is_completed:
            st.success("Status: Complete")
            _render_node_data(selected_node, state)
        elif selected_node in run.pending_nodes:
            st.info("Status: Running...")
        else:
            st.caption("Status: Pending")


def _render_node_data(node_name: str, state: dict[str, Any]) -> None:
    """Render node-specific data from the pipeline state."""
    renderer = _NODE_DATA_RENDERERS.get(node_name)
    if renderer is not None:
        renderer(state)


def _render_authorize_data(state: dict[str, Any]) -> None:
    skipped = state.get("authorization_skipped", False)
    allowed = state.get("authorization_allowed", False)
    if skipped:
        st.markdown("Authorization: **Skipped** (system execution)")
    elif allowed:
        st.markdown("Authorization: **Granted**")
    else:
        st.markdown("Authorization: **Denied**")


def _render_ingest_data(state: dict[str, Any]) -> None:
    st.metric("Vulnerabilities Parsed", len(state.get("vulnerabilities", [])))


def _render_dlp_data(state: dict[str, Any]) -> None:
    dlp_result = state.get("dlp_result")
    if isinstance(dlp_result, dict):
        st.metric("Fields Sanitized", dlp_result.get("sanitized_count", 0))


def _render_enrich_data(state: dict[str, Any]) -> None:
    st.metric("CVEs Enriched", len(state.get("enrichments", {})))
    st.caption("Sources: NVD, EPSS, GitHub Advisories, OSINT, Vector Store")


def _render_classify_data(state: dict[str, Any]) -> None:
    st.metric("CVEs Classified", len(state.get("classifications", {})))
    st.metric("Escalated for Review", len(state.get("escalated_cves", [])))
    st.caption("Dual classification: XGBoost ML + Claude LLM (CRAG)")


def _render_escalate_data(state: dict[str, Any]) -> None:
    decision = state.get("human_decision")
    if decision:
        st.markdown(f"Human Decision: **{decision}**")
    st.metric("Escalation Level", state.get("escalation_level", 0))


def _render_output_data(state: dict[str, Any]) -> None:
    jira_keys = state.get("output_jira_keys", [])
    pdf_path = state.get("output_pdf_path")
    if jira_keys:
        st.markdown(f"Jira Tickets: **{', '.join(jira_keys)}**")
    if pdf_path:
        st.markdown(f"PDF Report: `{pdf_path}`")


_NODE_DATA_RENDERERS: dict[str, Any] = {
    "authorize": _render_authorize_data,
    "ingest": _render_ingest_data,
    "dlp": _render_dlp_data,
    "enrich": _render_enrich_data,
    "classify": _render_classify_data,
    "escalate": _render_escalate_data,
    "output": _render_output_data,
}


__all__ = [
    "render_live_monitor",
]
