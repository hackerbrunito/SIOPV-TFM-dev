"""Tests for the decision panel dashboard component."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from siopv.interfaces.dashboard.components.decision_panel import (
    _render_modify_form,
    render_decision_panel,
)


class TestRenderDecisionPanel:
    """Tests for render_decision_panel."""

    @patch("siopv.interfaces.dashboard.components.decision_panel.st")
    def test_renders_three_buttons(self, mock_st: MagicMock) -> None:
        mock_col = MagicMock()
        mock_col.__enter__ = MagicMock(return_value=mock_col)
        mock_col.__exit__ = MagicMock(return_value=False)
        mock_st.columns.return_value = [mock_col, mock_col, mock_col]
        mock_st.button.return_value = False
        mock_st.session_state = {}

        case: dict[str, object] = {
            "thread_id": "t-001",
            "state": {},
        }
        callback = MagicMock()
        render_decision_panel(case, on_decision=callback)

        mock_st.subheader.assert_called_once_with("Decision")
        assert mock_st.button.call_count == 3

    @patch("siopv.interfaces.dashboard.components.decision_panel.st")
    def test_approve_calls_callback(self, mock_st: MagicMock) -> None:
        mock_col = MagicMock()
        mock_col.__enter__ = MagicMock(return_value=mock_col)
        mock_col.__exit__ = MagicMock(return_value=False)
        mock_st.columns.return_value = [mock_col, mock_col, mock_col]
        # First button (Approve) returns True, others False
        mock_st.button.side_effect = [True, False, False]
        mock_st.session_state = {}

        case: dict[str, object] = {
            "thread_id": "t-001",
            "state": {},
        }
        callback = MagicMock()
        render_decision_panel(case, on_decision=callback)

        callback.assert_called_once_with("t-001", "approve", None, None)

    def test_callback_signature_accepts_correct_types(self) -> None:
        """Verify the callback signature is callable with correct types."""

        def sample_callback(
            thread_id: str,
            decision: str,
            modified_score: float | None,
            modified_recommendation: str | None,
        ) -> None:
            pass

        # Should not raise
        sample_callback("t-001", "approve", None, None)
        sample_callback("t-001", "modify", 0.75, "Updated recommendation")


class TestRenderModifyForm:
    """Tests for _render_modify_form."""

    @patch("siopv.interfaces.dashboard.components.decision_panel.st")
    def test_renders_score_input_and_text_area(self, mock_st: MagicMock) -> None:
        mock_col = MagicMock()
        mock_col.__enter__ = MagicMock(return_value=mock_col)
        mock_col.__exit__ = MagicMock(return_value=False)
        mock_st.columns.return_value = [mock_col, mock_col]
        mock_st.button.return_value = False
        mock_st.number_input.return_value = 0.5
        mock_st.text_area.return_value = ""

        callback = MagicMock()
        _render_modify_form("t-001", {}, on_decision=callback)

        mock_st.number_input.assert_called_once()
        mock_st.text_area.assert_called_once()
        # Submit + Cancel buttons
        assert mock_st.button.call_count == 2

    @patch("siopv.interfaces.dashboard.components.decision_panel.st")
    def test_submit_calls_callback_with_modified_values(self, mock_st: MagicMock) -> None:
        mock_col = MagicMock()
        mock_col.__enter__ = MagicMock(return_value=mock_col)
        mock_col.__exit__ = MagicMock(return_value=False)
        mock_st.columns.return_value = [mock_col, mock_col]
        # Submit button True, Cancel False
        mock_st.button.side_effect = [True, False]
        mock_st.number_input.return_value = 0.75
        mock_st.text_area.return_value = "Updated recommendation"
        mock_st.session_state = {}

        callback = MagicMock()
        _render_modify_form("t-002", {}, on_decision=callback)

        callback.assert_called_once_with("t-002", "modify", 0.75, "Updated recommendation")
        assert mock_st.session_state["show_modify_t-002"] is False
        mock_st.rerun.assert_called_once()

    @patch("siopv.interfaces.dashboard.components.decision_panel.st")
    def test_submit_with_empty_recommendation_passes_none(self, mock_st: MagicMock) -> None:
        mock_col = MagicMock()
        mock_col.__enter__ = MagicMock(return_value=mock_col)
        mock_col.__exit__ = MagicMock(return_value=False)
        mock_st.columns.return_value = [mock_col, mock_col]
        mock_st.button.side_effect = [True, False]
        mock_st.number_input.return_value = 0.9
        mock_st.text_area.return_value = ""
        mock_st.session_state = {}

        callback = MagicMock()
        _render_modify_form("t-003", {}, on_decision=callback)

        callback.assert_called_once_with("t-003", "modify", 0.9, None)

    @patch("siopv.interfaces.dashboard.components.decision_panel.st")
    def test_cancel_hides_form(self, mock_st: MagicMock) -> None:
        mock_col = MagicMock()
        mock_col.__enter__ = MagicMock(return_value=mock_col)
        mock_col.__exit__ = MagicMock(return_value=False)
        mock_st.columns.return_value = [mock_col, mock_col]
        # Submit False, Cancel True
        mock_st.button.side_effect = [False, True]
        mock_st.number_input.return_value = 0.5
        mock_st.text_area.return_value = ""
        mock_st.session_state = {"show_modify_t-004": True}

        callback = MagicMock()
        _render_modify_form("t-004", {}, on_decision=callback)

        callback.assert_not_called()
        assert mock_st.session_state["show_modify_t-004"] is False
        mock_st.rerun.assert_called_once()


class TestDecisionPanelRejectCallback:
    """Tests for reject button callback invocation."""

    @patch("siopv.interfaces.dashboard.components.decision_panel.st")
    def test_reject_calls_callback(self, mock_st: MagicMock) -> None:
        mock_col = MagicMock()
        mock_col.__enter__ = MagicMock(return_value=mock_col)
        mock_col.__exit__ = MagicMock(return_value=False)
        mock_st.columns.return_value = [mock_col, mock_col, mock_col]
        # Approve False, Reject True, Modify False
        mock_st.button.side_effect = [False, True, False]
        mock_st.session_state = {}

        case: dict[str, object] = {"thread_id": "t-rej", "state": {}}
        callback = MagicMock()
        render_decision_panel(case, on_decision=callback)

        callback.assert_called_once_with("t-rej", "reject", None, None)

    @patch("siopv.interfaces.dashboard.components.decision_panel.st")
    def test_modify_button_shows_form(self, mock_st: MagicMock) -> None:
        mock_col = MagicMock()
        mock_col.__enter__ = MagicMock(return_value=mock_col)
        mock_col.__exit__ = MagicMock(return_value=False)
        # First columns(3) for main buttons, then columns(2) for modify form
        mock_st.columns.side_effect = [
            [mock_col, mock_col, mock_col],
            [mock_col, mock_col],
        ]
        # Approve False, Reject False, Modify True, then Submit False, Cancel False
        mock_st.button.side_effect = [False, False, True, False, False]
        mock_st.number_input.return_value = 0.5
        mock_st.text_area.return_value = ""
        mock_st.session_state = {}

        case: dict[str, object] = {"thread_id": "t-mod", "state": {}}
        callback = MagicMock()
        render_decision_panel(case, on_decision=callback)

        assert mock_st.session_state["show_modify_t-mod"] is True

    @patch("siopv.interfaces.dashboard.components.decision_panel.st")
    def test_shows_modify_form_when_session_state_set(self, mock_st: MagicMock) -> None:
        mock_col = MagicMock()
        mock_col.__enter__ = MagicMock(return_value=mock_col)
        mock_col.__exit__ = MagicMock(return_value=False)
        # 3 columns for main buttons + 2 columns for modify form
        mock_st.columns.side_effect = [[mock_col, mock_col, mock_col], [mock_col, mock_col]]
        mock_st.button.side_effect = [False, False, False, False, False]
        mock_st.number_input.return_value = 0.5
        mock_st.text_area.return_value = ""
        mock_st.session_state = {"show_modify_t-show": True}

        case: dict[str, object] = {"thread_id": "t-show", "state": {}}
        callback = MagicMock()
        render_decision_panel(case, on_decision=callback)

        mock_st.divider.assert_called_once()
        mock_st.number_input.assert_called_once()
