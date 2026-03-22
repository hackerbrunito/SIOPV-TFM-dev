"""Pipeline timing and performance charts for the SIOPV Analytics Dashboard.

Renders:
- Node timing horizontal bar chart (bottleneck identification)
- Vulnerability processing rate line chart
- Output artifacts summary cards
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from siopv.domain.constants import (
    PIPELINE_NODE_LABELS,
    PIPELINE_NODE_SEQUENCE,
    SECONDS_PER_MINUTE,
)
from siopv.interfaces.dashboard.components.pipeline_flow import FlowPlaceholders


def render_node_timing_chart(flow: FlowPlaceholders | None) -> None:
    """Render horizontal bar chart showing elapsed time per pipeline node.

    Highlights the slowest node (bottleneck) in a different color.

    Args:
        flow: FlowPlaceholders with timing data, or None if not available.
    """
    if flow is None:
        st.info("Pipeline timing data not available yet.")
        return

    node_names: list[str] = []
    elapsed_times: list[float] = []
    colors: list[str] = []

    max_elapsed = 0.0

    for name in PIPELINE_NODE_SEQUENCE:
        state = flow.node_states.get(name)
        if state is not None and state.elapsed_seconds is not None and state.status == "complete":
            label = PIPELINE_NODE_LABELS.get(name, name)
            node_names.append(label)
            elapsed_times.append(round(state.elapsed_seconds, 2))
            max_elapsed = max(max_elapsed, state.elapsed_seconds)

    if not node_names:
        st.info("No completed nodes with timing data.")
        return

    # Color the slowest node differently (bottleneck indicator)
    for elapsed in elapsed_times:
        if elapsed == max_elapsed and max_elapsed > 0:
            colors.append("#ef4444")  # Red for bottleneck
        else:
            colors.append("#3b82f6")  # Blue for normal

    fig = go.Figure(
        go.Bar(
            y=node_names,
            x=elapsed_times,
            orientation="h",
            marker_color=colors,
            text=[_format_time(t) for t in elapsed_times],
            textposition="auto",
        )
    )
    fig.update_layout(
        title="Pipeline Node Timing (bottleneck in red)",
        xaxis_title="Seconds",
        yaxis_title="",
        height=300,
        margin={"l": 100, "r": 20, "t": 40, "b": 40},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#fafafa"},
        xaxis={"gridcolor": "#333"},
        yaxis={"autorange": "reversed"},
    )
    st.plotly_chart(fig, key="node_timing", width="stretch")


def render_output_artifacts(state: dict[str, Any]) -> None:
    """Render output artifacts as information cards.

    Args:
        state: Pipeline accumulated state.
    """
    pdf_path = state.get("output_pdf_path")
    csv_path = state.get("output_csv_path")
    json_path = state.get("output_json_path")
    jira_keys = state.get("output_jira_keys", [])
    output_errors = state.get("output_errors", [])

    has_artifacts = pdf_path or csv_path or json_path or jira_keys
    if not has_artifacts:
        st.info("No output artifacts generated yet.")
        return

    st.markdown("#### Generated Artifacts")

    cols = st.columns(4)

    with cols[0]:
        if pdf_path:
            st.metric("PDF Report", "Generated")
            st.caption(f"`{pdf_path}`")
        else:
            st.metric("PDF Report", "N/A")

    with cols[1]:
        if csv_path:
            st.metric("CSV Export", "Generated")
            st.caption(f"`{csv_path}`")
        else:
            st.metric("CSV Export", "N/A")

    with cols[2]:
        if json_path:
            st.metric("JSON Export", "Generated")
            st.caption(f"`{json_path}`")
        else:
            st.metric("JSON Export", "N/A")

    with cols[3]:
        if jira_keys:
            st.metric("Jira Tickets", len(jira_keys))
            st.caption(", ".join(jira_keys))
        else:
            st.metric("Jira Tickets", "N/A")

    if output_errors:
        with st.expander(f"Output Warnings ({len(output_errors)})"):
            for error in output_errors:
                st.warning(error)


def render_pipeline_total_time(flow: FlowPlaceholders | None) -> None:
    """Render total pipeline execution time as a metric.

    Args:
        flow: FlowPlaceholders with timing data.
    """
    if flow is None:
        return

    total = sum(
        s.elapsed_seconds
        for s in flow.node_states.values()
        if s.elapsed_seconds is not None and s.status == "complete"
    )

    if total > 0:
        st.metric("Total Pipeline Time", _format_time(total))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _format_time(seconds: float) -> str:
    """Format seconds into human-readable string."""
    if seconds < 1.0:
        return f"{seconds * 1000:.0f}ms"
    if seconds < SECONDS_PER_MINUTE:
        return f"{seconds:.1f}s"
    minutes = int(seconds // SECONDS_PER_MINUTE)
    remaining = seconds % SECONDS_PER_MINUTE
    return f"{minutes}m {remaining:.0f}s"


__all__ = [
    "render_node_timing_chart",
    "render_output_artifacts",
    "render_pipeline_total_time",
]
