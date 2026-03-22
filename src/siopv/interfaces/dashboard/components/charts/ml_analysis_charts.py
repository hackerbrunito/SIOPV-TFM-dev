"""ML analysis charts for the SIOPV Security Analytics Dashboard.

Renders:
- XGBoost vs LLM confidence scatter (discrepancy detection)
- Escalation reasons pie chart
- Risk classification treemap
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from siopv.domain.constants import (
    RISK_PROBABILITY_CRITICAL_THRESHOLD,
    RISK_PROBABILITY_HIGH_THRESHOLD,
    RISK_PROBABILITY_LOW_THRESHOLD,
    RISK_PROBABILITY_MEDIUM_THRESHOLD,
)


def render_ml_vs_llm_scatter(
    classifications: dict[str, Any],
    llm_confidence: dict[str, float],
) -> None:
    """Render scatter plot comparing XGBoost risk scores vs LLM confidence.

    Points near the diagonal indicate agreement between ML and LLM.
    Points far from the diagonal indicate discrepancy — potential
    escalation triggers.

    Args:
        classifications: Dict mapping CVE ID to classification result.
        llm_confidence: Dict mapping CVE ID to LLM confidence score.
    """
    if not classifications:
        st.info("No classification data available yet.")
        return

    cve_ids: list[str] = []
    ml_scores: list[float] = []
    llm_scores: list[float] = []

    for cve_id, classification in classifications.items():
        ml_risk = _get_risk_prob(classification)
        llm_conf = llm_confidence.get(cve_id, 0.0)

        cve_ids.append(cve_id)
        ml_scores.append(ml_risk)
        llm_scores.append(llm_conf)

    if not cve_ids:
        st.info("No ML/LLM comparison data available.")
        return

    # Calculate discrepancy for color coding
    discrepancies = [abs(ml - llm) for ml, llm in zip(ml_scores, llm_scores, strict=False)]

    fig = go.Figure(
        go.Scatter(
            x=ml_scores,
            y=llm_scores,
            mode="markers",
            marker={
                "size": 10,
                "color": discrepancies,
                "colorscale": "RdYlGn_r",
                "colorbar": {"title": "Discrepancy"},
                "line": {"width": 1, "color": "#333"},
            },
            text=cve_ids,
            hovertemplate=(
                "<b>%{text}</b><br>"
                "XGBoost Risk: %{x:.3f}<br>"
                "LLM Confidence: %{y:.3f}<br>"
                "Discrepancy: %{marker.color:.3f}"
                "<extra></extra>"
            ),
        )
    )

    # Add diagonal reference line (perfect agreement)
    fig.add_shape(
        type="line",
        x0=0,
        y0=0,
        x1=1,
        y1=1,
        line={"color": "#6b7280", "dash": "dash", "width": 1},
    )

    fig.update_layout(
        title="XGBoost ML Risk vs LLM Confidence (CRAG)",
        xaxis_title="XGBoost Risk Probability",
        yaxis_title="LLM Confidence Score",
        xaxis={"range": [-0.05, 1.05], "gridcolor": "#333"},
        yaxis={"range": [-0.05, 1.05], "gridcolor": "#333"},
        height=400,
        margin={"l": 60, "r": 20, "t": 40, "b": 40},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#fafafa"},
    )
    st.plotly_chart(fig, key="ml_vs_llm", width="stretch")


def render_escalation_breakdown(
    state: dict[str, Any],
) -> None:
    """Render pie chart showing escalation reasons.

    Args:
        state: Pipeline accumulated state.
    """
    escalated = state.get("escalated_cves", [])
    classifications = state.get("classifications", {})
    total_classified = len(classifications)

    if total_classified == 0:
        st.info("No classification data available yet.")
        return

    escalated_count = len(escalated)
    not_escalated = total_classified - escalated_count

    if escalated_count == 0:
        st.success(f"All {total_classified} CVEs classified without escalation.")
        return

    labels = ["Escalated (human review)", "Auto-classified"]
    values = [escalated_count, not_escalated]
    colors = ["#f97316", "#22c55e"]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            marker={"colors": colors, "line": {"color": "#1a1a2e", "width": 2}},
            textinfo="label+percent+value",
            hovertemplate="%{label}: %{value} CVEs (%{percent})<extra></extra>",
            hole=0.4,
        )
    )
    fig.update_layout(
        title="Escalation Breakdown",
        height=350,
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#fafafa"},
        showlegend=True,
        legend={"orientation": "h", "y": -0.1},
    )
    st.plotly_chart(fig, key="escalation_breakdown", width="stretch")


def render_risk_treemap(classifications: dict[str, Any]) -> None:
    """Render a treemap showing CVE distribution by risk level.

    Hierarchical: severity level → individual CVEs, sized by risk score.

    Args:
        classifications: Dict mapping CVE ID to classification result.
    """
    if not classifications:
        st.info("No classification data available yet.")
        return

    cve_ids: list[str] = []
    parents: list[str] = []
    values: list[float] = []
    colors: list[str] = []

    # Add root
    severity_levels = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINIMAL"]
    severity_colors = {
        "CRITICAL": "#ef4444",
        "HIGH": "#f97316",
        "MEDIUM": "#eab308",
        "LOW": "#3b82f6",
        "MINIMAL": "#6b7280",
    }

    # Add severity level nodes
    for level in severity_levels:
        cve_ids.append(level)
        parents.append("")
        values.append(0)  # Plotly calculates from children
        colors.append(severity_colors[level])

    # Add individual CVEs under their severity level
    for cve_id, classification in classifications.items():
        risk = _get_risk_prob(classification)
        severity = _severity_label(risk)

        cve_ids.append(cve_id)
        parents.append(severity)
        values.append(max(risk, 0.01))  # Avoid zero-size
        colors.append(severity_colors[severity])

    fig = go.Figure(
        go.Treemap(
            labels=cve_ids,
            parents=parents,
            values=values,
            marker={"colors": colors, "line": {"width": 1, "color": "#1a1a2e"}},
            textinfo="label+value",
            hovertemplate="<b>%{label}</b><br>Risk: %{value:.3f}<extra></extra>",
            branchvalues="total",
        )
    )
    fig.update_layout(
        title="Risk Classification Treemap",
        height=400,
        margin={"l": 10, "r": 10, "t": 40, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#fafafa"},
    )
    st.plotly_chart(fig, key="risk_treemap", width="stretch")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_risk_prob(classification: Any) -> float:
    """Extract risk probability from a classification.

    Handles ClassificationResult (risk_score.risk_probability)
    and dict representations.
    """
    if classification is None:
        return 0.0
    if isinstance(classification, dict):
        return float(classification.get("risk_probability", 0.0) or 0.0)
    # ClassificationResult -> risk_score -> risk_probability
    risk_score = getattr(classification, "risk_score", None)
    if risk_score is not None:
        prob = getattr(risk_score, "risk_probability", None)
        if prob is not None:
            return float(prob)
    return float(getattr(classification, "risk_probability", 0.0) or 0.0)


def _severity_label(risk_prob: float) -> str:
    """Map risk probability to severity label."""
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
    "render_escalation_breakdown",
    "render_ml_vs_llm_scatter",
    "render_risk_treemap",
]
