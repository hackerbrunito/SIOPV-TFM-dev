"""Pipeline execution summary component for the SIOPV monitor dashboard.

Renders a post-execution dashboard with metrics, timing breakdown, output
artifacts, and classification distribution.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from siopv.domain.constants import (
    PIPELINE_NODE_LABELS,
    RISK_PROBABILITY_CRITICAL_THRESHOLD,
    RISK_PROBABILITY_HIGH_THRESHOLD,
    RISK_PROBABILITY_LOW_THRESHOLD,
    RISK_PROBABILITY_MEDIUM_THRESHOLD,
    SECONDS_PER_MINUTE,
)
from siopv.interfaces.dashboard.components.pipeline_flow import FlowPlaceholders


def render_pipeline_summary(
    flow: FlowPlaceholders,
    final_data: dict[str, Any],
) -> None:
    """Render the post-execution summary dashboard.

    Displays key metrics, node timing breakdown, classification distribution,
    and links to output artifacts.

    Args:
        flow: Completed ``FlowPlaceholders`` with timing data per node.
        final_data: Accumulated state data from all node outputs.
    """
    st.divider()
    st.subheader("Execution Summary")

    _render_key_metrics(final_data)
    _render_timing_breakdown(flow)
    _render_classification_distribution(final_data)
    _render_output_artifacts(final_data)
    _render_errors(final_data)


def _render_key_metrics(data: dict[str, Any]) -> None:
    """Render the top-level metrics row.

    Args:
        data: Accumulated pipeline state data.
    """
    vuln_count = len(data.get("vulnerabilities", []))
    classification_count = len(data.get("classifications", {}))
    escalated_count = len(data.get("escalated_cves", []))
    error_count = len(data.get("errors", []))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Vulnerabilities", vuln_count)
    with col2:
        st.metric("Classified", classification_count)
    with col3:
        st.metric("Escalated", escalated_count)
    with col4:
        st.metric("Errors", error_count, delta_color="inverse" if error_count > 0 else "off")


def _render_timing_breakdown(flow: FlowPlaceholders) -> None:
    """Render per-node timing breakdown.

    Args:
        flow: Completed flow with timing data.
    """
    st.markdown("#### Timing Breakdown")

    timing_data: list[dict[str, Any]] = []
    total_seconds = 0.0

    for name, state in flow.node_states.items():
        elapsed = state.elapsed_seconds
        if elapsed is not None and state.status in ("complete", "error"):
            timing_data.append(
                {
                    "Node": PIPELINE_NODE_LABELS.get(name, name),
                    "Status": state.status.capitalize(),
                    "Duration": state.elapsed_display,
                    "Seconds": round(elapsed, 2),
                }
            )
            total_seconds += elapsed

    if timing_data:
        st.dataframe(
            timing_data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Node": st.column_config.TextColumn("Node", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Duration": st.column_config.TextColumn("Duration", width="small"),
                "Seconds": st.column_config.NumberColumn("Seconds", format="%.2f"),
            },
        )
        st.caption(f"Total pipeline time: {_format_total_time(total_seconds)}")
    else:
        st.info("No timing data available.")


def _render_classification_distribution(data: dict[str, Any]) -> None:
    """Render risk classification distribution as a bar chart.

    Groups classifications into CRITICAL / HIGH / MEDIUM / LOW / MINIMAL
    buckets based on domain threshold constants.

    Args:
        data: Accumulated pipeline state data.
    """
    classifications = data.get("classifications", {})
    if not classifications:
        return

    st.markdown("#### Risk Classification Distribution")

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

    # Only show if there's data
    if any(v > 0 for v in buckets.values()):
        col1, col2, col3, col4, col5 = st.columns(5)
        columns = [col1, col2, col3, col4, col5]
        colors = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🔵",
            "MINIMAL": "⚪",
        }
        for (label, count), col in zip(buckets.items(), columns, strict=True):
            with col:
                st.metric(f"{colors[label]} {label}", count)


def _render_output_artifacts(data: dict[str, Any]) -> None:
    """Render links and paths to generated output artifacts.

    Args:
        data: Accumulated pipeline state data.
    """
    pdf_path = data.get("output_pdf_path")
    csv_path = data.get("output_csv_path")
    json_path = data.get("output_json_path")
    jira_keys = data.get("output_jira_keys", [])

    has_artifacts = pdf_path or csv_path or json_path or jira_keys
    if not has_artifacts:
        return

    st.markdown("#### Output Artifacts")

    if pdf_path:
        st.markdown(f"**PDF Report:** `{pdf_path}`")
    if csv_path:
        st.markdown(f"**CSV Export:** `{csv_path}`")
    if json_path:
        st.markdown(f"**JSON Export:** `{json_path}`")
    if jira_keys:
        st.markdown(f"**Jira Tickets:** {', '.join(jira_keys)}")


def _render_errors(data: dict[str, Any]) -> None:
    """Render any pipeline errors or warnings.

    Args:
        data: Accumulated pipeline state data.
    """
    errors: list[str] = data.get("errors", [])
    output_errors: list[str] = data.get("output_errors", [])

    if not errors and not output_errors:
        return

    st.markdown("#### Errors & Warnings")

    if errors:
        with st.expander(f"Pipeline Errors ({len(errors)})", expanded=True):
            for error in errors:
                st.error(error)

    if output_errors:
        with st.expander(f"Output Warnings ({len(output_errors)})"):
            for error in output_errors:
                st.warning(error)


def _format_total_time(seconds: float) -> str:
    """Format total seconds into a human-readable string.

    Args:
        seconds: Total elapsed seconds.

    Returns:
        Formatted time string.
    """
    if seconds < SECONDS_PER_MINUTE:
        return f"{seconds:.1f}s"
    minutes = int(seconds // SECONDS_PER_MINUTE)
    remaining = seconds % 60
    return f"{minutes}m {remaining:.0f}s"


__all__ = [
    "render_pipeline_summary",
]
