"""SIOPV Security Analytics Dashboard — Main Page.

Displays live vulnerability analysis with KPI indicators, severity
distribution, ML classification analysis, and a growing vulnerability
table.  Data updates in real time as the pipeline processes CVEs.

This page reads from the checkpoint database to display results from
webhook-triggered or manually-triggered pipeline executions.
"""

from __future__ import annotations

import sqlite3
from typing import Any

import pandas as pd
import streamlit as st
import structlog

from siopv.interfaces.dashboard.components.charts.kpi_indicators import (
    render_kpi_row,
)
from siopv.interfaces.dashboard.components.charts.ml_analysis_charts import (
    render_escalation_breakdown,
    render_ml_vs_llm_scatter,
    render_risk_treemap,
)
from siopv.interfaces.dashboard.components.charts.severity_charts import (
    render_cvss_histogram,
    render_epss_vs_cvss_scatter,
    render_severity_breakdown,
)
from siopv.interfaces.dashboard.components.charts.timing_charts import (
    render_node_timing_chart,
    render_output_artifacts,
    render_pipeline_total_time,
)
from siopv.interfaces.dashboard.components.observer import (
    PipelineRunInfo,
    get_active_runs,
    get_completed_runs,
)

logger = structlog.get_logger(__name__)


def render_security_analytics() -> None:
    """Render the Security Analytics page."""
    st.header("Security Analytics")

    # Get graph and connection from session state (set by analytics_app.py)
    graph = st.session_state.get("shared_graph")
    conn = st.session_state.get("shared_conn")

    if graph is None or conn is None:
        st.error("Dashboard not properly initialized. Graph or database connection missing.")
        return

    # Sidebar: select which pipeline run to view
    selected_run = _render_run_selector(graph, conn)

    if selected_run is None:
        st.info(
            "No pipeline runs found. Execute the pipeline via the webhook "
            "or the Live Monitor page, then return here to view analytics."
        )
        return

    state = selected_run.current_state

    # KPI row (always visible)
    render_kpi_row(state)

    st.divider()

    # Tabbed content
    tab_severity, tab_ml, tab_table, tab_timing = st.tabs(
        [
            "Severity & Risk",
            "ML Analysis",
            "Vulnerability Table",
            "Pipeline Performance",
        ]
    )

    with tab_severity:
        _render_severity_tab(state)

    with tab_ml:
        _render_ml_tab(state)

    with tab_table:
        _render_vulnerability_table(state)

    with tab_timing:
        _render_timing_tab(state, selected_run)


# ---------------------------------------------------------------------------
# Run selector
# ---------------------------------------------------------------------------


def _render_run_selector(
    graph: Any,
    conn: sqlite3.Connection,
) -> PipelineRunInfo | None:
    """Render a sidebar selector for choosing which pipeline run to view.

    Shows active runs first, then recent completed runs.

    Args:
        graph: Compiled graph with checkpointer.
        conn: SQLite connection.

    Returns:
        Selected PipelineRunInfo or None.
    """
    with st.sidebar:
        st.subheader("Pipeline Runs")

        # Auto-detect active runs
        active = get_active_runs(graph, conn)
        completed = get_completed_runs(graph, conn, limit=20)

        all_runs = active + completed
        if not all_runs:
            return None

        # Build display labels
        labels: list[str] = []
        for run in all_runs:
            status = (
                "RUNNING" if run.is_running else ("INTERRUPTED" if run.is_interrupted else "DONE")
            )
            vuln_label = f"{run.vulnerability_count} CVEs" if run.vulnerability_count else "pending"
            time_label = run.created_at[:19] if run.created_at else "unknown"
            labels.append(f"[{status}] {vuln_label} — {time_label}")

        selected_idx = st.selectbox(
            "Select a pipeline run",
            range(len(labels)),
            format_func=lambda i: labels[i],
        )

        if selected_idx is not None:
            result: PipelineRunInfo = all_runs[selected_idx]
            return result

    return all_runs[0] if all_runs else None


# ---------------------------------------------------------------------------
# Tab renderers
# ---------------------------------------------------------------------------


def _render_severity_tab(state: dict[str, Any]) -> None:
    """Render the Severity & Risk tab."""
    classifications = state.get("classifications", {})
    vulnerabilities = state.get("vulnerabilities", [])
    enrichments = state.get("enrichments", {})

    col1, col2 = st.columns(2)

    with col1:
        render_severity_breakdown(classifications)

    with col2:
        render_cvss_histogram(vulnerabilities)

    render_epss_vs_cvss_scatter(vulnerabilities, enrichments, classifications)


def _render_ml_tab(state: dict[str, Any]) -> None:
    """Render the ML Analysis tab."""
    classifications = state.get("classifications", {})
    llm_confidence = state.get("llm_confidence", {})

    col1, col2 = st.columns(2)

    with col1:
        render_ml_vs_llm_scatter(classifications, llm_confidence)

    with col2:
        render_escalation_breakdown(state)

    render_risk_treemap(classifications)


def _render_vulnerability_table(state: dict[str, Any]) -> None:
    """Render the live vulnerability table.

    Shows all vulnerabilities with their classification results,
    CVSS scores, EPSS scores, and severity labels. Sortable and
    filterable via Streamlit's native dataframe widget.
    """
    vulnerabilities = state.get("vulnerabilities", [])
    classifications = state.get("classifications", {})
    enrichments = state.get("enrichments", {})

    if not vulnerabilities:
        st.info("No vulnerabilities processed yet.")
        return

    rows: list[dict[str, Any]] = []
    for vuln in vulnerabilities:
        cve_id = _get_cve_id(vuln)
        if not cve_id:
            continue

        # Get CVSS
        cvss = _get_float_attr(vuln, "cvss_score", "cvss_base_score")

        # Get package info
        package = _get_str_attr(vuln, "package_name", "pkg_name")
        severity_trivy = _get_str_attr(vuln, "severity")

        # Get enrichment data
        enrichment = enrichments.get(cve_id)
        epss = _get_float_from(enrichment, "epss_score") if enrichment else None

        # Get classification
        classification = classifications.get(cve_id)
        risk_prob = _get_float_from(classification, "risk_probability") if classification else None

        # Determine ML severity
        ml_severity = _severity_label(risk_prob) if risk_prob is not None else "N/A"

        rows.append(
            {
                "CVE ID": cve_id,
                "Package": package or "N/A",
                "Trivy Severity": severity_trivy or "N/A",
                "CVSS": round(cvss, 1) if cvss is not None else None,
                "EPSS": round(epss, 4) if epss is not None else None,
                "ML Risk Score": round(risk_prob, 3) if risk_prob is not None else None,
                "ML Severity": ml_severity,
            }
        )

    if not rows:
        st.info("No vulnerability data to display.")
        return

    df = pd.DataFrame(rows)

    # Color configuration for severity column
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=min(len(rows) * 35 + 38, 600),
        column_config={
            "CVE ID": st.column_config.TextColumn("CVE ID", width="medium"),
            "Package": st.column_config.TextColumn("Package", width="medium"),
            "Trivy Severity": st.column_config.TextColumn("Trivy", width="small"),
            "CVSS": st.column_config.NumberColumn("CVSS", format="%.1f", width="small"),
            "EPSS": st.column_config.NumberColumn("EPSS", format="%.4f", width="small"),
            "ML Risk Score": st.column_config.ProgressColumn(
                "ML Risk",
                min_value=0.0,
                max_value=1.0,
                format="%.3f",
                width="medium",
            ),
            "ML Severity": st.column_config.TextColumn("ML Severity", width="small"),
        },
    )

    st.caption(f"Showing {len(rows)} vulnerabilities")


def _render_timing_tab(
    state: dict[str, Any],
    run_info: PipelineRunInfo,
) -> None:
    """Render the Pipeline Performance tab."""
    # Try to get flow from session state (if pipeline was run via monitor)
    flow = st.session_state.get("last_run_flow")

    col1, col2 = st.columns([2, 1])

    with col1:
        render_node_timing_chart(flow)

    with col2:
        render_pipeline_total_time(flow)
        st.divider()
        st.metric("Total Steps", run_info.step_count)
        st.metric("Errors", run_info.error_count, delta_color="inverse")

    render_output_artifacts(state)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_cve_id(vuln: Any) -> str:
    """Extract CVE ID string from a vulnerability record."""
    if isinstance(vuln, dict):
        return str(vuln.get("cve_id", ""))
    cve_id_obj = getattr(vuln, "cve_id", None)
    if cve_id_obj is None:
        return ""
    return str(cve_id_obj.value) if hasattr(cve_id_obj, "value") else str(cve_id_obj)


def _get_float_attr(obj: Any, *attrs: str) -> float | None:
    """Try to get a float value from multiple attribute names."""
    for attr in attrs:
        val = obj.get(attr) if isinstance(obj, dict) else getattr(obj, attr, None)
        if val is not None and isinstance(val, (int, float)):
            return float(val)
    return None


def _get_str_attr(obj: Any, *attrs: str) -> str | None:
    """Try to get a string value from multiple attribute names."""
    for attr in attrs:
        val = obj.get(attr) if isinstance(obj, dict) else getattr(obj, attr, None)
        if val is not None:
            return str(val)
    return None


def _get_float_from(obj: Any, attr: str) -> float | None:
    """Get a float value from an object or dict."""
    if obj is None:
        return None
    val = obj.get(attr) if isinstance(obj, dict) else getattr(obj, attr, None)
    if val is not None and isinstance(val, (int, float)):
        return float(val)
    return None


def _severity_label(risk_prob: float) -> str:
    """Map risk probability to severity label."""
    from siopv.domain.constants import (  # noqa: PLC0415
        RISK_PROBABILITY_CRITICAL_THRESHOLD,
        RISK_PROBABILITY_HIGH_THRESHOLD,
        RISK_PROBABILITY_LOW_THRESHOLD,
        RISK_PROBABILITY_MEDIUM_THRESHOLD,
    )

    if risk_prob >= RISK_PROBABILITY_CRITICAL_THRESHOLD:
        return "CRITICAL"
    if risk_prob >= RISK_PROBABILITY_HIGH_THRESHOLD:
        return "HIGH"
    if risk_prob >= RISK_PROBABILITY_MEDIUM_THRESHOLD:
        return "MEDIUM"
    if risk_prob >= RISK_PROBABILITY_LOW_THRESHOLD:
        return "LOW"
    return "MINIMAL"


__all__ = [
    "render_security_analytics",
]
