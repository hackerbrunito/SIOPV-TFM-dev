"""SIOPV Scan History & Comparison — Page 3.

Displays historical pipeline executions and allows comparing two scans
to identify new, fixed, and unchanged vulnerabilities between scans.
Data is read from the LangGraph checkpoint database.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st
import structlog

from siopv.interfaces.dashboard.components.charts.severity_charts import SEVERITY_COLORS
from siopv.interfaces.dashboard.components.observer import (
    PipelineRunInfo,
    get_completed_runs,
)

logger = structlog.get_logger(__name__)


def render_scan_history() -> None:
    """Render the Scan History & Comparison page."""
    st.header("Scan History & Comparison")

    graph = st.session_state.get("shared_graph")
    conn = st.session_state.get("shared_conn")

    if graph is None or conn is None:
        st.error("Dashboard not properly initialized.")
        return

    completed = get_completed_runs(graph, conn, limit=50)

    if not completed:
        st.info("No completed pipeline runs found in the checkpoint database.")
        return

    # History table
    _render_history_table(completed)

    st.divider()

    # Comparison selector
    from siopv.domain.constants import MIN_SCANS_FOR_COMPARISON  # noqa: PLC0415

    if len(completed) >= MIN_SCANS_FOR_COMPARISON:
        _render_comparison(completed)
    else:
        st.info("At least two completed scans are needed for comparison.")


def _render_history_table(runs: list[PipelineRunInfo]) -> None:
    """Render a table of historical pipeline runs.

    Args:
        runs: List of completed PipelineRunInfo objects.
    """
    st.subheader("Completed Scans")

    rows: list[dict[str, Any]] = []
    for run in runs:
        rows.append(
            {
                "Thread ID": run.thread_id[:12] + "...",
                "Date": run.created_at[:19] if run.created_at else "N/A",
                "Vulnerabilities": run.vulnerability_count,
                "Classified": run.classification_count,
                "Escalated": run.escalated_count,
                "Errors": run.error_count,
                "Steps": run.step_count,
            }
        )

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Thread ID": st.column_config.TextColumn("Run ID", width="medium"),
            "Date": st.column_config.TextColumn("Timestamp", width="medium"),
            "Vulnerabilities": st.column_config.NumberColumn("CVEs", width="small"),
            "Classified": st.column_config.NumberColumn("Classified", width="small"),
            "Escalated": st.column_config.NumberColumn("Escalated", width="small"),
            "Errors": st.column_config.NumberColumn("Errors", width="small"),
            "Steps": st.column_config.NumberColumn("Steps", width="small"),
        },
    )


def _render_comparison(runs: list[PipelineRunInfo]) -> None:
    """Render scan comparison: select two scans and show diff.

    Args:
        runs: List of completed PipelineRunInfo objects.
    """
    st.subheader("Compare Scans")

    labels = [
        f"{run.created_at[:19] if run.created_at else 'N/A'} — "
        f"{run.vulnerability_count} CVEs ({run.thread_id[:8]})"
        for run in runs
    ]

    col1, col2 = st.columns(2)

    with col1:
        scan_a_idx = st.selectbox(
            "Scan A (older)",
            range(len(labels)),
            index=min(1, len(labels) - 1),
            format_func=lambda i: labels[i],
        )

    with col2:
        scan_b_idx = st.selectbox(
            "Scan B (newer)", range(len(labels)), index=0, format_func=lambda i: labels[i]
        )

    if scan_a_idx == scan_b_idx:
        st.warning("Select two different scans to compare.")
        return

    scan_a = runs[scan_a_idx]
    scan_b = runs[scan_b_idx]

    # Extract CVE sets
    cves_a = _extract_cve_set(scan_a.current_state)
    cves_b = _extract_cve_set(scan_b.current_state)

    new_cves = cves_b - cves_a
    fixed_cves = cves_a - cves_b
    unchanged_cves = cves_a & cves_b

    # Comparison metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "New CVEs",
            len(new_cves),
            delta=len(new_cves),
            delta_color="inverse",
            help="Vulnerabilities found in Scan B but not in Scan A",
        )

    with col2:
        st.metric(
            "Fixed CVEs",
            len(fixed_cves),
            delta=-len(fixed_cves),
            delta_color="normal",
            help="Vulnerabilities in Scan A that are gone in Scan B",
        )

    with col3:
        st.metric(
            "Unchanged",
            len(unchanged_cves),
            help="Vulnerabilities present in both scans",
        )

    with col4:
        total_a = len(cves_a) or 1
        reduction = ((len(cves_a) - len(cves_b)) / total_a) * 100
        st.metric(
            "Risk Reduction",
            f"{reduction:+.1f}%",
            help="Percentage change in total vulnerability count",
        )

    # Severity trend comparison
    _render_severity_comparison(scan_a, scan_b)

    # CVE diff lists
    if new_cves:
        with st.expander(f"New CVEs ({len(new_cves)})", expanded=False):
            st.write(", ".join(sorted(new_cves)))

    if fixed_cves:
        with st.expander(f"Fixed CVEs ({len(fixed_cves)})", expanded=False):
            st.write(", ".join(sorted(fixed_cves)))


def _render_severity_comparison(
    scan_a: PipelineRunInfo,
    scan_b: PipelineRunInfo,
) -> None:
    """Render grouped bar chart comparing severity distribution between scans.

    Args:
        scan_a: Older scan.
        scan_b: Newer scan.
    """
    buckets_a = _bucket_by_severity(scan_a.current_state.get("classifications", {}))
    buckets_b = _bucket_by_severity(scan_b.current_state.get("classifications", {}))

    severity_levels = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINIMAL"]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Scan A (older)",
            x=severity_levels,
            y=[buckets_a[s] for s in severity_levels],
            marker_color="#6b7280",
            text=[buckets_a[s] for s in severity_levels],
            textposition="auto",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Scan B (newer)",
            x=severity_levels,
            y=[buckets_b[s] for s in severity_levels],
            marker_color=[SEVERITY_COLORS[s] for s in severity_levels],
            text=[buckets_b[s] for s in severity_levels],
            textposition="auto",
        )
    )

    fig.update_layout(
        title="Severity Distribution — Scan Comparison",
        barmode="group",
        xaxis_title="Severity Level",
        yaxis_title="Number of CVEs",
        height=350,
        margin={"l": 40, "r": 20, "t": 40, "b": 40},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#fafafa"},
        yaxis={"gridcolor": "#333"},
        legend={"orientation": "h", "y": -0.2},
    )
    st.plotly_chart(fig, key="severity_comparison", width="stretch")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_cve_set(state: dict[str, Any]) -> set[str]:
    """Extract the set of CVE IDs from pipeline state."""
    vulns = state.get("vulnerabilities", [])
    cve_ids: set[str] = set()

    for vuln in vulns:
        if isinstance(vuln, dict):
            cve_id = str(vuln.get("cve_id", ""))
        else:
            cve_id_obj = getattr(vuln, "cve_id", None)
            if cve_id_obj is None:
                continue
            cve_id = str(cve_id_obj.value) if hasattr(cve_id_obj, "value") else str(cve_id_obj)
        if cve_id:
            cve_ids.add(cve_id)

    return cve_ids


def _bucket_by_severity(classifications: dict[str, Any]) -> dict[str, int]:
    """Bucket classifications by severity level."""
    from siopv.domain.constants import (  # noqa: PLC0415
        RISK_PROBABILITY_CRITICAL_THRESHOLD,
        RISK_PROBABILITY_HIGH_THRESHOLD,
        RISK_PROBABILITY_LOW_THRESHOLD,
        RISK_PROBABILITY_MEDIUM_THRESHOLD,
    )

    buckets: dict[str, int] = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
        "MINIMAL": 0,
    }

    for classification in classifications.values():
        if isinstance(classification, dict):
            prob = float(classification.get("risk_probability", 0.0) or 0.0)
        else:
            prob = float(getattr(classification, "risk_probability", 0.0) or 0.0)

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

    return buckets


__all__ = [
    "render_scan_history",
]
