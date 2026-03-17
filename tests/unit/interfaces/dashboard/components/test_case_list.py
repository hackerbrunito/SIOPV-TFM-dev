"""Tests for the case list dashboard component."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from siopv.interfaces.dashboard.components.case_list import (
    _format_elapsed_time,
    _get_level_badge,
    render_case_list,
)


class TestFormatElapsedTime:
    """Tests for _format_elapsed_time helper."""

    def test_none_returns_unknown(self) -> None:
        assert _format_elapsed_time(None) == "unknown"

    def test_invalid_string_returns_unknown(self) -> None:
        assert _format_elapsed_time("not-a-date") == "unknown"

    def test_recent_timestamp_shows_minutes(self) -> None:
        recent = (datetime.now(UTC) - timedelta(minutes=15)).isoformat()
        result = _format_elapsed_time(recent)
        assert result.endswith("m ago")

    def test_hours_ago_timestamp(self) -> None:
        hours_ago = (datetime.now(UTC) - timedelta(hours=5)).isoformat()
        result = _format_elapsed_time(hours_ago)
        assert result.endswith("h ago")

    def test_days_ago_timestamp(self) -> None:
        days_ago = (datetime.now(UTC) - timedelta(days=3)).isoformat()
        result = _format_elapsed_time(days_ago)
        assert result.endswith("d ago")

    def test_naive_datetime_treated_as_utc(self) -> None:
        naive = (datetime.now(UTC) - timedelta(hours=2)).replace(tzinfo=None).isoformat()
        result = _format_elapsed_time(naive)
        assert result.endswith("h ago")


class TestGetLevelBadge:
    """Tests for _get_level_badge helper."""

    def test_level_0(self) -> None:
        assert _get_level_badge(0) == "[NEW]"

    def test_level_1(self) -> None:
        assert _get_level_badge(1) == "[4h+]"

    def test_level_2(self) -> None:
        assert _get_level_badge(2) == "[8h+]"

    def test_level_3(self) -> None:
        assert _get_level_badge(3) == "[AUTO]"

    def test_unknown_level(self) -> None:
        assert _get_level_badge(99) == "[???]"


class TestRenderCaseList:
    """Tests for render_case_list."""

    @patch("siopv.interfaces.dashboard.components.case_list.st")
    def test_empty_list_shows_info(self, mock_st: MagicMock) -> None:
        render_case_list([])
        mock_st.subheader.assert_called_once_with("Pending Cases")
        mock_st.info.assert_called_once_with("No pending cases.")

    @patch("siopv.interfaces.dashboard.components.case_list.st")
    def test_single_case_renders_button(self, mock_st: MagicMock) -> None:
        mock_st.session_state = {}
        mock_st.button.return_value = False

        cases = [
            {
                "thread_id": "t-001",
                "state": {"escalated_cves": ["CVE-2024-1234"], "escalation_level": 1},
                "created_at": None,
            },
        ]
        render_case_list(cases)
        mock_st.button.assert_called_once()

    @patch("siopv.interfaces.dashboard.components.case_list.st")
    def test_truncates_cve_list_beyond_three(self, mock_st: MagicMock) -> None:
        mock_st.session_state = {}
        mock_st.button.return_value = False

        cases = [
            {
                "thread_id": "t-002",
                "state": {
                    "escalated_cves": ["CVE-1", "CVE-2", "CVE-3", "CVE-4", "CVE-5"],
                    "escalation_level": 0,
                },
                "created_at": None,
            },
        ]
        render_case_list(cases)

        call_args = mock_st.button.call_args
        label = call_args[0][0]
        assert "(+2 more)" in label
