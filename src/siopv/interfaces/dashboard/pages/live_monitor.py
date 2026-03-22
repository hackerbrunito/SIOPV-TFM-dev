"""SIOPV Live Pipeline Monitor — Page 2.

Two modes:
1. **Observer mode** — passively watches for webhook-triggered pipeline
   executions by polling the checkpoint database.
2. **Manual mode** — user uploads/specifies a Trivy report and triggers
   execution directly.

The observer mode uses ``@st.fragment(run_every=0.5)`` to poll the
checkpoint database for active pipeline threads and display their
progress in real time.
"""

from __future__ import annotations

import sqlite3
from typing import Any

import streamlit as st
import structlog
from streamlit_flow import streamlit_flow
from streamlit_flow.elements import StreamlitFlowEdge, StreamlitFlowNode
from streamlit_flow.layouts import LayeredLayout
from streamlit_flow.state import StreamlitFlowState

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
# Node status → visual style mapping
# ---------------------------------------------------------------------------

_STATUS_STYLES: dict[str, dict[str, str]] = {
    "pending": {
        "background": "#374151",
        "border": "2px solid #6b7280",
        "color": "#9ca3af",
    },
    "running": {
        "background": "#1e3a5f",
        "border": "2px solid #3b82f6",
        "color": "#93c5fd",
    },
    "complete": {
        "background": "#14532d",
        "border": "2px solid #22c55e",
        "color": "#86efac",
    },
    "error": {
        "background": "#450a0a",
        "border": "2px solid #ef4444",
        "color": "#fca5a5",
    },
    "skipped": {
        "background": "#1f2937",
        "border": "2px dashed #4b5563",
        "color": "#6b7280",
    },
}


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


def _render_observer_mode(graph: Any, conn: sqlite3.Connection) -> None:
    """Render observer mode: poll checkpoint DB for active pipelines.

    Uses st.fragment(run_every=0.5) for automatic polling (500ms).
    """
    flow_placeholder = st.empty()
    detail_placeholder = st.container()

    @st.fragment(run_every=0.5)
    def poll_active_pipelines() -> None:
        active = get_active_runs(graph, conn)

        if not active:
            # Check for recently completed runs
            from siopv.interfaces.dashboard.components.observer import (  # noqa: PLC0415
                get_completed_runs,
            )

            recent = get_completed_runs(graph, conn, limit=1)
            if recent:
                run = recent[0]
                st.session_state["observed_run"] = run
                with flow_placeholder.container():
                    _render_pipeline_flow_diagram(run)
                st.caption("Last completed pipeline run")
            else:
                st.info("Waiting for pipeline execution... (polling every 500ms)")
            return

        # Show the most recent active run
        run = active[0]
        st.session_state["observed_run"] = run

        with flow_placeholder.container():
            _render_pipeline_flow_diagram(run)

        st.caption(
            f"Observing thread {run.thread_id[:12]}... "
            f"| Step {run.step_count} "
            f"| {run.vulnerability_count} CVEs"
        )

    poll_active_pipelines()

    # Detail panel for selected node
    observed_run = st.session_state.get("observed_run")
    if observed_run:
        with detail_placeholder:
            _render_node_detail_panel(observed_run)


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
# Pipeline flow diagram (React Flow via streamlit-flow)
# ---------------------------------------------------------------------------


def _render_pipeline_flow_diagram(run: PipelineRunInfo) -> None:
    """Render the pipeline as an interactive flow diagram using React Flow.

    Nodes are colored by execution status. Edges between active nodes
    are animated to show data flow.

    Args:
        run: Current pipeline run information.
    """
    nodes: list[StreamlitFlowNode] = []
    edges: list[StreamlitFlowEdge] = []

    completed = run.completed_nodes
    pending_next = set(run.pending_nodes)

    for i, node_name in enumerate(PIPELINE_NODE_SEQUENCE):
        # Determine status
        if node_name in completed:
            status = "complete"
        elif node_name in pending_next or (run.is_interrupted and node_name == "escalate"):
            status = "running"
        else:
            # Check if any later node completed (this one was skipped)
            later_nodes = set(PIPELINE_NODE_SEQUENCE[i + 1 :])
            status = "skipped" if later_nodes & completed else "pending"

        style = _STATUS_STYLES[status]
        label = PIPELINE_NODE_LABELS[node_name]
        status_icon = {
            "pending": "",
            "running": " ...",
            "complete": " OK",
            "error": " !",
            "skipped": " --",
        }[status]

        nodes.append(
            StreamlitFlowNode(
                id=node_name,
                pos=(0, 0),
                data={"content": f"**{label}**{status_icon}"},
                node_type="default",
                source_position="right",
                target_position="left",
                style={
                    "backgroundColor": style["background"],
                    "border": style["border"],
                    "color": style["color"],
                    "padding": "10px",
                    "borderRadius": "8px",
                    "fontSize": "14px",
                    "width": "140px",
                    "textAlign": "center",
                },
            )
        )

    # Create edges between sequential nodes
    edge_pairs = [
        ("authorize", "ingest"),
        ("ingest", "dlp"),
        ("dlp", "enrich"),
        ("enrich", "classify"),
        ("classify", "escalate"),
        ("classify", "output"),
        ("escalate", "output"),
    ]

    for source, target in edge_pairs:
        # Animate edges where data is currently flowing
        is_animated = source in completed and (target in pending_next or target in completed)

        edges.append(
            StreamlitFlowEdge(
                id=f"{source}-{target}",
                source=source,
                target=target,
                animated=is_animated,
                style={"stroke": "#3b82f6" if is_animated else "#4b5563"},
            )
        )

    flow_state = StreamlitFlowState(nodes, edges)

    selected = streamlit_flow(
        "pipeline_flow",
        flow_state,
        layout=LayeredLayout(direction="right"),
        fit_view=True,
        height=250,
        get_node_on_click=True,
        get_edge_on_click=False,
        pan_on_drag=True,
        allow_zoom=True,
        show_minimap=False,
        show_controls=False,
        style={"backgroundColor": "#0e1117"},
    )

    if selected and hasattr(selected, "nodes"):
        # User clicked a node — store selection for detail panel
        clicked_nodes = [n for n in selected.nodes if hasattr(n, "id")]
        if clicked_nodes:
            st.session_state["selected_flow_node"] = clicked_nodes[0].id


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
        st.caption("Click on a pipeline node above to see details.")
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
    """Render node-specific data from the pipeline state.

    Uses a dispatch table to keep branch count under the linter limit.

    Args:
        node_name: Pipeline node name.
        state: Pipeline accumulated state.
    """
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
