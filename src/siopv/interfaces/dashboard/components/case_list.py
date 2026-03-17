"""Case list component for the SIOPV review dashboard.

Renders a scrollable list of pending escalated cases.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import streamlit as st

from siopv.domain.constants import CASE_LIST_CVE_DISPLAY_LIMIT, ELAPSED_TIME_HOURS_PER_DAY


def render_case_list(cases: list[dict[str, Any]]) -> None:
    """Render the list of pending escalation cases.

    Each row shows: CVE IDs, severity indicators, elapsed time,
    and escalation level. Clicking selects the case for review.

    Args:
        cases: List of case dicts from get_interrupted_threads()
    """
    st.subheader("Pending Cases")

    if not cases:
        st.info("No pending cases.")
        return

    for case in cases:
        thread_id = case["thread_id"]
        state = case.get("state", {})
        created_at = case.get("created_at")

        # Extract CVE IDs from escalated_cves in state
        escalated_cves: list[str] = state.get("escalated_cves", [])
        escalation_level: int = state.get("escalation_level", 0)

        # Calculate elapsed time
        elapsed_str = _format_elapsed_time(created_at)

        # Escalation level badge
        level_badge = _get_level_badge(escalation_level)

        # Build display
        cve_summary = ", ".join(escalated_cves[:CASE_LIST_CVE_DISPLAY_LIMIT])
        if len(escalated_cves) > CASE_LIST_CVE_DISPLAY_LIMIT:
            cve_summary += f" (+{len(escalated_cves) - CASE_LIST_CVE_DISPLAY_LIMIT} more)"

        is_selected = st.session_state.get("selected_thread_id") == thread_id

        if st.button(
            f"{level_badge} {cve_summary or 'No CVEs'} — {elapsed_str}",
            key=f"case_{thread_id}",
            type="primary" if is_selected else "secondary",
            use_container_width=True,
        ):
            st.session_state.selected_thread_id = thread_id


def _format_elapsed_time(created_at: str | None) -> str:
    """Format elapsed time since case creation.

    Args:
        created_at: ISO 8601 timestamp string

    Returns:
        Human-readable elapsed time string
    """
    if not created_at:
        return "unknown"

    try:
        created = datetime.fromisoformat(created_at)
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        now = datetime.now(UTC)
        delta = now - created

        hours = delta.total_seconds() / 3600
    except (ValueError, TypeError):
        return "unknown"
    else:
        if hours < 1:
            minutes = int(delta.total_seconds() / 60)
            return f"{minutes}m ago"
        if hours < ELAPSED_TIME_HOURS_PER_DAY:
            return f"{int(hours)}h ago"
        days = int(hours / ELAPSED_TIME_HOURS_PER_DAY)
        return f"{days}d ago"


def _get_level_badge(level: int) -> str:
    """Get escalation level indicator.

    Args:
        level: Escalation level (0-3)

    Returns:
        Badge string indicating urgency
    """
    badges = {
        0: "[NEW]",
        1: "[4h+]",
        2: "[8h+]",
        3: "[AUTO]",
    }
    return badges.get(level, "[???]")
