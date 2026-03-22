"""Severity and risk distribution charts for the SIOPV Analytics Dashboard.

Renders:
- Severity breakdown horizontal bar chart (CRITICAL/HIGH/MEDIUM/LOW/MINIMAL)
- CVSS base score histogram
- EPSS vs CVSS scatter plot (exploitation probability vs severity)
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from siopv.domain.constants import (
    EPSS_HIGH_RISK_THRESHOLD,
    RISK_PROBABILITY_CRITICAL_THRESHOLD,
    RISK_PROBABILITY_HIGH_THRESHOLD,
    RISK_PROBABILITY_LOW_THRESHOLD,
    RISK_PROBABILITY_MEDIUM_THRESHOLD,
)

# Color palette for severity levels (consistent across all charts)
SEVERITY_COLORS: dict[str, str] = {
    "CRITICAL": "#ef4444",
    "HIGH": "#f97316",
    "MEDIUM": "#eab308",
    "LOW": "#3b82f6",
    "MINIMAL": "#6b7280",
}


def render_severity_breakdown(classifications: dict[str, Any]) -> None:
    """Render a horizontal bar chart showing vulnerability count by severity.

    Args:
        classifications: Dict mapping CVE ID to classification result.
    """
    if not classifications:
        st.info("No classification data available yet.")
        return

    buckets = _bucket_by_severity(classifications)

    # Order: CRITICAL first (top of bar chart)
    severity_order = ["MINIMAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    counts = [buckets[s] for s in severity_order]
    colors = [SEVERITY_COLORS[s] for s in severity_order]

    fig = go.Figure(
        go.Bar(
            y=severity_order,
            x=counts,
            orientation="h",
            marker_color=colors,
            text=counts,
            textposition="auto",
        )
    )
    fig.update_layout(
        title="Severity Distribution",
        xaxis_title="Number of CVEs",
        yaxis_title="",
        height=300,
        margin={"l": 80, "r": 20, "t": 40, "b": 40},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#fafafa"},
        xaxis={"gridcolor": "#333"},
    )
    st.plotly_chart(fig, key="severity_breakdown", width="stretch")


def render_cvss_histogram(vulnerabilities: list[Any]) -> None:
    """Render a histogram of CVSS base scores across all vulnerabilities.

    Args:
        vulnerabilities: List of VulnerabilityRecord objects or dicts.
    """
    if not vulnerabilities:
        st.info("No vulnerability data available yet.")
        return

    scores = _extract_cvss_scores(vulnerabilities)
    if not scores:
        st.info("No CVSS scores available.")
        return

    fig = go.Figure(
        go.Histogram(
            x=scores,
            nbinsx=20,
            marker_color="#3b82f6",
            marker_line={"color": "#1e40af", "width": 1},
        )
    )
    fig.update_layout(
        title="CVSS Base Score Distribution",
        xaxis_title="CVSS Score",
        yaxis_title="Count",
        xaxis={"range": [0, 10], "dtick": 1, "gridcolor": "#333"},
        yaxis={"gridcolor": "#333"},
        height=300,
        margin={"l": 40, "r": 20, "t": 40, "b": 40},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#fafafa"},
    )
    st.plotly_chart(fig, key="cvss_histogram", width="stretch")


def render_epss_vs_cvss_scatter(
    vulnerabilities: list[Any],
    enrichments: dict[str, Any],
    classifications: dict[str, Any],
) -> None:
    """Render scatter plot: EPSS (Y) vs CVSS (X), colored by ML risk.

    Each dot is a CVE. Shows which high-CVSS vulnerabilities actually
    have high exploitation probability, helping analysts prioritize.

    Args:
        vulnerabilities: List of VulnerabilityRecord objects or dicts.
        enrichments: Dict mapping CVE ID to enrichment data.
        classifications: Dict mapping CVE ID to classification result.
    """
    if not vulnerabilities or not enrichments:
        st.info("Enrichment data needed for EPSS vs CVSS analysis.")
        return

    data = _build_scatter_data(vulnerabilities, enrichments, classifications)
    if not data:
        st.info("Insufficient data for EPSS vs CVSS scatter plot.")
        return

    cve_ids = [d["cve_id"] for d in data]
    cvss_scores = [d["cvss"] for d in data]
    epss_scores = [d["epss"] for d in data]
    risk_scores = [d["risk"] for d in data]
    severities = [d["severity"] for d in data]

    fig = go.Figure(
        go.Scatter(
            x=cvss_scores,
            y=epss_scores,
            mode="markers",
            marker={
                "size": 10,
                "color": risk_scores,
                "colorscale": "RdYlGn_r",
                "colorbar": {"title": "ML Risk"},
                "line": {"width": 1, "color": "#333"},
            },
            text=cve_ids,
            customdata=list(zip(severities, risk_scores, strict=False)),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "CVSS: %{x:.1f}<br>"
                "EPSS: %{y:.4f}<br>"
                "ML Risk: %{customdata[1]:.3f}<br>"
                "Severity: %{customdata[0]}"
                "<extra></extra>"
            ),
        )
    )

    # Add reference lines
    fig.add_hline(
        y=EPSS_HIGH_RISK_THRESHOLD,
        line_dash="dash",
        line_color="#ef4444",
        annotation_text=f"EPSS High Risk ({EPSS_HIGH_RISK_THRESHOLD})",
        annotation_position="top left",
    )
    fig.add_vline(
        x=7.0,
        line_dash="dash",
        line_color="#f97316",
        annotation_text="CVSS High (7.0)",
        annotation_position="top right",
    )

    fig.update_layout(
        title="EPSS vs CVSS — Exploitation Probability vs Severity",
        xaxis_title="CVSS Base Score",
        yaxis_title="EPSS Score (30-day exploitation probability)",
        xaxis={"range": [0, 10.5], "gridcolor": "#333"},
        yaxis={"gridcolor": "#333"},
        height=400,
        margin={"l": 60, "r": 20, "t": 40, "b": 40},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#fafafa"},
    )
    st.plotly_chart(fig, key="epss_vs_cvss", width="stretch")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _bucket_by_severity(classifications: dict[str, Any]) -> dict[str, int]:
    """Bucket classifications into severity levels by risk probability."""
    buckets: dict[str, int] = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
        "MINIMAL": 0,
    }
    for classification in classifications.values():
        prob = _get_risk_prob(classification)
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


def _extract_cvss_scores(vulnerabilities: list[Any]) -> list[float]:
    """Extract CVSS base scores from vulnerability records."""
    scores: list[float] = []
    for vuln in vulnerabilities:
        if isinstance(vuln, dict):
            score = vuln.get("cvss_score") or vuln.get("cvss_base_score")
        else:
            score = getattr(vuln, "cvss_score", None) or getattr(vuln, "cvss_base_score", None)
        if score is not None and isinstance(score, (int, float)):
            scores.append(float(score))
    return scores


def _build_scatter_data(
    vulnerabilities: list[Any],
    enrichments: dict[str, Any],
    classifications: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build scatter plot data by joining vuln, enrichment, and classification data."""
    data: list[dict[str, Any]] = []

    for vuln in vulnerabilities:
        cve_id = _get_cve_id(vuln)
        if not cve_id:
            continue

        # Get CVSS score
        cvss = _get_cvss(vuln)
        if cvss is None:
            continue

        # Get EPSS from enrichment
        enrichment = enrichments.get(cve_id)
        epss = _get_epss(enrichment) if enrichment else None
        if epss is None:
            continue

        # Get ML risk score from classification
        classification = classifications.get(cve_id)
        risk = _get_risk_prob(classification) if classification else 0.0

        # Determine severity label
        severity = _severity_label(risk)

        data.append(
            {
                "cve_id": cve_id,
                "cvss": cvss,
                "epss": epss,
                "risk": risk,
                "severity": severity,
            }
        )

    return data


def _get_cve_id(vuln: Any) -> str:
    """Extract CVE ID string from a vulnerability record."""
    if isinstance(vuln, dict):
        return str(vuln.get("cve_id", ""))
    cve_id_obj = getattr(vuln, "cve_id", None)
    if cve_id_obj is None:
        return ""
    return str(cve_id_obj.value) if hasattr(cve_id_obj, "value") else str(cve_id_obj)


def _get_cvss(vuln: Any) -> float | None:
    """Extract CVSS score from a vulnerability record."""
    if isinstance(vuln, dict):
        val = vuln.get("cvss_score") or vuln.get("cvss_base_score")
    else:
        val = getattr(vuln, "cvss_score", None) or getattr(vuln, "cvss_base_score", None)
    if val is not None and isinstance(val, (int, float)):
        return float(val)
    return None


def _get_epss(enrichment: Any) -> float | None:
    """Extract EPSS score from enrichment data."""
    if isinstance(enrichment, dict):
        val = enrichment.get("epss_score")
    else:
        val = getattr(enrichment, "epss_score", None)
    if val is not None and isinstance(val, (int, float)):
        return float(val)
    return None


def _get_risk_prob(classification: Any) -> float:
    """Extract risk probability from a classification."""
    if classification is None:
        return 0.0
    if isinstance(classification, dict):
        return float(classification.get("risk_probability", 0.0) or 0.0)
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
    "SEVERITY_COLORS",
    "render_cvss_histogram",
    "render_epss_vs_cvss_scatter",
    "render_severity_breakdown",
]
