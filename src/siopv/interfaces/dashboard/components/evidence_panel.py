"""Evidence panel component for the SIOPV review dashboard.

Renders the Triada de Evidencia for a selected escalated case:
1. AI Summary -- Claude synthesis of enriched context
2. LIME Chart -- feature importance bar chart
3. Chain-of-Thought Log -- full LLM reasoning trace
"""

from __future__ import annotations

from typing import Any

import pandas as pd  # type: ignore[import-untyped]
import streamlit as st


def render_evidence_panel(case: dict[str, Any]) -> None:
    """Render the evidence panel with three tabs.

    Args:
        case: Selected case dict from get_interrupted_threads()
    """
    st.subheader("Evidence Review")

    state = case.get("state", {})
    escalated_cves: list[str] = state.get("escalated_cves", [])
    classifications: dict[str, Any] = state.get("classifications", {})
    enrichments: dict[str, Any] = state.get("enrichments", {})

    tab_summary, tab_lime, tab_cot = st.tabs(
        [
            "AI Summary",
            "LIME Explanation",
            "Chain-of-Thought",
        ]
    )

    with tab_summary:
        _render_ai_summary(escalated_cves, enrichments, classifications)

    with tab_lime:
        _render_lime_chart(escalated_cves, classifications)

    with tab_cot:
        _render_chain_of_thought(escalated_cves, classifications)


def _render_ai_summary(
    escalated_cves: list[str],
    enrichments: dict[str, Any],
    classifications: dict[str, Any],
) -> None:
    """Render the AI summary tab with enrichment data per CVE.

    Args:
        escalated_cves: List of escalated CVE IDs
        enrichments: Dict mapping CVE ID to enrichment data
        classifications: Dict mapping CVE ID to classification result
    """
    if not escalated_cves:
        st.info("No escalated CVEs to display.")
        return

    for cve_id in escalated_cves:
        st.markdown(f"### {cve_id}")

        enrichment = enrichments.get(cve_id)
        classification = classifications.get(cve_id)

        if enrichment is None and classification is None:
            st.warning(f"No enrichment data available for {cve_id}.")
            continue

        if enrichment is not None:
            # EnrichmentData may be a dict or dataclass-like object
            enrichment_dict = enrichment if isinstance(enrichment, dict) else vars(enrichment)

            nvd_description = enrichment_dict.get("nvd_description", "N/A")
            epss_score = enrichment_dict.get("epss_score")
            github_advisories = enrichment_dict.get("github_advisories", [])

            st.markdown(f"**NVD Description:** {nvd_description}")

            if epss_score is not None:
                st.markdown(f"**EPSS Score:** {epss_score:.4f}")
            else:
                st.markdown("**EPSS Score:** N/A")

            if github_advisories:
                st.markdown(f"**GitHub Advisories:** {len(github_advisories)} found")
            else:
                st.markdown("**GitHub Advisories:** None")

        if classification is not None:
            classification_dict = (
                classification if isinstance(classification, dict) else vars(classification)
            )
            risk_score = classification_dict.get("risk_probability")
            if risk_score is not None:
                st.markdown(f"**Risk Score:** {risk_score:.4f}")

        st.divider()


def _render_lime_chart(
    escalated_cves: list[str],
    classifications: dict[str, Any],
) -> None:
    """Render LIME feature importance chart for escalated CVEs.

    Args:
        escalated_cves: List of escalated CVE IDs
        classifications: Dict mapping CVE ID to classification result
    """
    if not escalated_cves:
        st.info("No escalated CVEs to display.")
        return

    rendered_any = False

    for cve_id in escalated_cves:
        classification = classifications.get(cve_id)
        if classification is None:
            continue

        classification_dict = (
            classification if isinstance(classification, dict) else vars(classification)
        )

        # LIME explanation may be stored as feature_importances or explanation
        lime_data = (
            classification_dict.get("feature_importances")
            or classification_dict.get("explanation")
            or classification_dict.get("lime_explanation")
        )

        if lime_data is None or not isinstance(lime_data, dict):
            continue

        st.markdown(f"### {cve_id}")
        df = pd.DataFrame(
            {"Feature": list(lime_data.keys()), "Weight": list(lime_data.values())}
        ).sort_values("Weight", ascending=True)

        st.bar_chart(df.set_index("Feature"))
        rendered_any = True

    if not rendered_any:
        st.info("LIME explanation not available for this case.")


def _render_chain_of_thought(
    escalated_cves: list[str],
    classifications: dict[str, Any],
) -> None:
    """Render chain-of-thought reasoning logs for escalated CVEs.

    Args:
        escalated_cves: List of escalated CVE IDs
        classifications: Dict mapping CVE ID to classification result
    """
    if not escalated_cves:
        st.info("No escalated CVEs to display.")
        return

    rendered_any = False

    for cve_id in escalated_cves:
        classification = classifications.get(cve_id)
        if classification is None:
            continue

        classification_dict = (
            classification if isinstance(classification, dict) else vars(classification)
        )

        # Chain-of-thought may be stored under various keys
        cot_log = (
            classification_dict.get("chain_of_thought")
            or classification_dict.get("reasoning_trace")
            or classification_dict.get("cot_log")
        )

        if cot_log is None:
            continue

        st.markdown(f"### {cve_id}")
        cot_text = cot_log if isinstance(cot_log, str) else str(cot_log)
        st.code(cot_text, language="text")
        rendered_any = True

    if not rendered_any:
        st.info("Chain-of-thought log not available for this case.")
