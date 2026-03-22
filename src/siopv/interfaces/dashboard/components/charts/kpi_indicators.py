"""KPI indicator components for the SIOPV Security Analytics Dashboard.

Renders Plotly gauge indicators and Streamlit metrics for key
vulnerability management KPIs: total count, critical/high severity,
exploitation risk (EPSS), and average ML risk score.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from siopv.domain.constants import (
    EPSS_HIGH_RISK_THRESHOLD,
    RISK_PROBABILITY_CRITICAL_THRESHOLD,
    RISK_PROBABILITY_HIGH_THRESHOLD,
)


def render_kpi_row(state: dict[str, Any], previous_state: dict[str, Any] | None = None) -> None:
    """Render the top-row KPI indicators.

    Shows four key metrics with delta comparison to a previous scan
    (if available) plus a summary gauge.

    Args:
        state: Current pipeline accumulated state.
        previous_state: Previous scan state for delta comparison (optional).
    """
    vulns = state.get("vulnerabilities", [])
    classifications = state.get("classifications", {})
    enrichments = state.get("enrichments", {})

    vuln_count = len(vulns)

    # Calculate derived metrics
    critical_high_count = _count_critical_high(classifications)
    high_epss_count = _count_high_epss(enrichments)
    avg_risk_score = _average_risk_score(classifications)

    # Previous scan deltas
    prev_vuln = len(previous_state.get("vulnerabilities", [])) if previous_state else None
    prev_critical_high = (
        _count_critical_high(previous_state.get("classifications", {})) if previous_state else None
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Total Vulnerabilities",
            vuln_count,
            delta=vuln_count - prev_vuln if prev_vuln is not None else None,
            delta_color="inverse",
        )

    with col2:
        st.metric(
            "Critical + High",
            critical_high_count,
            delta=(
                critical_high_count - prev_critical_high if prev_critical_high is not None else None
            ),
            delta_color="inverse",
        )

    with col3:
        st.metric(
            "High EPSS Risk",
            high_epss_count,
            help=f"CVEs with EPSS > {EPSS_HIGH_RISK_THRESHOLD} (high exploitation probability)",
        )

    with col4:
        st.metric(
            "Escalated",
            len(state.get("escalated_cves", [])),
            help="CVEs requiring human review due to ML/LLM uncertainty",
        )

    with col5:
        _render_risk_gauge(avg_risk_score)


def _render_risk_gauge(avg_score: float) -> None:
    """Render a Plotly angular gauge for average risk score.

    Args:
        avg_score: Average risk probability across all classifications (0.0-1.0).
    """
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=avg_score,
            number={"suffix": "", "valueformat": ".2f"},
            title={"text": "Avg Risk Score"},
            gauge={
                "axis": {"range": [0, 1], "tickwidth": 1},
                "bar": {"color": _risk_color(avg_score)},
                "steps": [
                    {"range": [0, 0.2], "color": "#1a1a2e"},
                    {"range": [0.2, 0.4], "color": "#16213e"},
                    {"range": [0.4, 0.6], "color": "#1a1a2e"},
                    {"range": [0.6, 0.8], "color": "#16213e"},
                    {"range": [0.8, 1.0], "color": "#1a1a2e"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": RISK_PROBABILITY_CRITICAL_THRESHOLD,
                },
            },
        )
    )
    fig.update_layout(
        height=200,
        margin={"l": 20, "r": 20, "t": 40, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#fafafa"},
    )
    st.plotly_chart(fig, key="risk_gauge", width="stretch")


def _count_critical_high(classifications: dict[str, Any]) -> int:
    """Count CVEs classified as CRITICAL or HIGH risk."""
    count = 0
    for classification in classifications.values():
        prob = _get_risk_probability(classification)
        if prob >= RISK_PROBABILITY_HIGH_THRESHOLD:
            count += 1
    return count


def _count_high_epss(enrichments: dict[str, Any]) -> int:
    """Count CVEs with EPSS score above the high-risk threshold."""
    count = 0
    for enrichment in enrichments.values():
        epss = (
            enrichment.get("epss_score")
            if isinstance(enrichment, dict)
            else getattr(enrichment, "epss_score", None)
        )
        if epss is not None and isinstance(epss, (int, float)) and epss > EPSS_HIGH_RISK_THRESHOLD:
            count += 1
    return count


def _average_risk_score(classifications: dict[str, Any]) -> float:
    """Calculate average risk probability across all classifications."""
    if not classifications:
        return 0.0
    scores = [_get_risk_probability(c) for c in classifications.values()]
    valid = [s for s in scores if s > 0]
    return sum(valid) / len(valid) if valid else 0.0


def _get_risk_probability(classification: Any) -> float:
    """Extract risk_probability from a classification (dict or object)."""
    if isinstance(classification, dict):
        return float(classification.get("risk_probability", 0.0) or 0.0)
    return float(getattr(classification, "risk_probability", 0.0) or 0.0)


def _risk_color(score: float) -> str:
    """Map risk score to a color."""
    if score >= RISK_PROBABILITY_CRITICAL_THRESHOLD:
        return "#ef4444"  # red
    if score >= RISK_PROBABILITY_HIGH_THRESHOLD:
        return "#f97316"  # orange
    return "#22c55e"  # green


__all__ = [
    "render_kpi_row",
]
