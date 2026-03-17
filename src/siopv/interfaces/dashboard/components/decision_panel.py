"""Decision panel component for the SIOPV review dashboard.

Renders the action buttons for human review decisions:
- Approve: Accept vulnerability classification as-is
- Reject: Mark as false positive / low priority
- Modify: Edit risk score or remediation recommendation
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st


def render_decision_panel(
    case: dict[str, Any],
    *,
    on_decision: Callable[[str, str, float | None, str | None], None],
) -> None:
    """Render the decision panel with action buttons.

    Args:
        case: Selected case dict
        on_decision: Callback(thread_id, decision, modified_score, modified_recommendation)
    """
    st.subheader("Decision")

    thread_id = case["thread_id"]

    col_approve, col_reject, col_modify = st.columns(3)

    with col_approve:
        if st.button(
            "Approve",
            key=f"approve_{thread_id}",
            type="primary",
            use_container_width=True,
        ):
            on_decision(thread_id, "approve", None, None)
            st.rerun()

    with col_reject:
        if st.button(
            "Reject",
            key=f"reject_{thread_id}",
            type="secondary",
            use_container_width=True,
        ):
            on_decision(thread_id, "reject", None, None)
            st.rerun()

    with col_modify:
        if st.button(
            "Modify",
            key=f"modify_{thread_id}",
            type="secondary",
            use_container_width=True,
        ):
            st.session_state[f"show_modify_{thread_id}"] = True

    # Show modify form if modify button was clicked
    if st.session_state.get(f"show_modify_{thread_id}", False):
        _render_modify_form(thread_id, case.get("state", {}), on_decision=on_decision)


def _render_modify_form(
    thread_id: str,
    _state: dict[str, Any],
    *,
    on_decision: Callable[[str, str, float | None, str | None], None],
) -> None:
    """Render the modification form for score/recommendation override.

    Args:
        thread_id: Pipeline thread ID
        state: Current pipeline state
        on_decision: Callback for submitting the modification
    """
    st.divider()
    st.markdown("**Modify Classification**")

    # Get current values for defaults
    current_score = 0.5  # Default

    modified_score = st.number_input(
        "Risk Score Override",
        min_value=0.0,
        max_value=1.0,
        value=current_score,
        step=0.05,
        key=f"score_{thread_id}",
    )

    modified_recommendation = st.text_area(
        "Recommendation Override",
        value="",
        key=f"recommendation_{thread_id}",
        placeholder="Enter modified remediation recommendation...",
    )

    col_submit, col_cancel = st.columns(2)

    with col_submit:
        if st.button(
            "Submit Modification",
            key=f"submit_modify_{thread_id}",
            type="primary",
            use_container_width=True,
        ):
            on_decision(
                thread_id,
                "modify",
                modified_score,
                modified_recommendation or None,
            )
            st.session_state[f"show_modify_{thread_id}"] = False
            st.rerun()

    with col_cancel:
        if st.button(
            "Cancel",
            key=f"cancel_modify_{thread_id}",
            use_container_width=True,
        ):
            st.session_state[f"show_modify_{thread_id}"] = False
            st.rerun()
