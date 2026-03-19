"""Unit tests for the SIOPV Human-in-the-Loop Dashboard app module."""

from __future__ import annotations

import sqlite3
from typing import Any
from unittest.mock import MagicMock, patch

from langgraph.types import Command

from siopv.interfaces.dashboard.app import (
    _initialize_session_state,
    get_interrupted_threads,
    handle_decision,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeSessionState(dict[str, Any]):
    """Dict-like stand-in for ``st.session_state``.

    Supports both dict-style and attribute-style access, mirroring
    Streamlit's ``SessionState`` behaviour.
    """

    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key) from None

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value

    def __delattr__(self, key: str) -> None:
        try:
            del self[key]
        except KeyError:
            raise AttributeError(key) from None


def _make_snapshot(
    *,
    has_next: bool = True,
    has_interrupts: bool = True,
    interrupt_value: Any = None,
    values: dict[str, Any] | None = None,
    created_at: str | None = "2026-03-17T10:00:00Z",
) -> MagicMock:
    """Build a mock StateSnapshot returned by ``graph.get_state``."""
    snapshot = MagicMock()
    snapshot.next = ("escalate",) if has_next else ()
    snapshot.values = values or {"escalation_required": True}
    snapshot.created_at = created_at

    if has_interrupts:
        interrupt = MagicMock()
        interrupt.value = interrupt_value or {"cve_id": "CVE-2026-0001"}
        task = MagicMock()
        task.interrupts = [interrupt]
        snapshot.tasks = [task]
    else:
        task = MagicMock()
        task.interrupts = []
        snapshot.tasks = [task]

    return snapshot


# ---------------------------------------------------------------------------
# _initialize_session_state
# ---------------------------------------------------------------------------


class TestInitializeSessionState:
    """Tests for ``_initialize_session_state``."""

    @patch("siopv.interfaces.dashboard.app.st")
    def test_sets_expected_defaults(self, mock_st: MagicMock) -> None:
        mock_st.session_state = FakeSessionState()

        _initialize_session_state()

        assert mock_st.session_state["selected_thread_id"] is None
        assert mock_st.session_state["polling_interval"] == 5
        assert mock_st.session_state["last_poll"] is None
        assert mock_st.session_state["pending_cases"] == []

    @patch("siopv.interfaces.dashboard.app.st")
    def test_preserves_existing_values(self, mock_st: MagicMock) -> None:
        mock_st.session_state = FakeSessionState(
            {"selected_thread_id": "thread-abc", "polling_interval": 10},
        )

        _initialize_session_state()

        assert mock_st.session_state["selected_thread_id"] == "thread-abc"
        assert mock_st.session_state["polling_interval"] == 10
        # New keys still get defaults
        assert mock_st.session_state["last_poll"] is None
        assert mock_st.session_state["pending_cases"] == []


# ---------------------------------------------------------------------------
# get_interrupted_threads
# ---------------------------------------------------------------------------


class TestGetInterruptedThreads:
    """Tests for ``get_interrupted_threads``."""

    def test_returns_empty_for_empty_db(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "CREATE TABLE checkpoints (thread_id TEXT, checkpoint_ns TEXT, data BLOB)",
        )
        graph = MagicMock()

        result = get_interrupted_threads(graph, conn)

        assert result == []
        graph.get_state.assert_not_called()
        conn.close()

    def test_identifies_interrupted_thread(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "CREATE TABLE checkpoints (thread_id TEXT, checkpoint_ns TEXT, data BLOB)",
        )
        conn.execute(
            "INSERT INTO checkpoints VALUES (?, ?, ?)",
            ("tid-1", "", b""),
        )
        conn.commit()

        snapshot = _make_snapshot(
            interrupt_value={"cve_id": "CVE-2026-9999"},
            values={"escalation_required": True, "escalated_cves": ["CVE-2026-9999"]},
        )
        graph = MagicMock()
        graph.get_state.return_value = snapshot

        result = get_interrupted_threads(graph, conn)

        assert len(result) == 1
        assert result[0]["thread_id"] == "tid-1"
        assert result[0]["interrupt_data"] == {"cve_id": "CVE-2026-9999"}
        assert result[0]["state"]["escalation_required"] is True
        assert result[0]["created_at"] == "2026-03-17T10:00:00Z"
        conn.close()

    def test_skips_non_interrupted_thread(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "CREATE TABLE checkpoints (thread_id TEXT, checkpoint_ns TEXT, data BLOB)",
        )
        conn.execute(
            "INSERT INTO checkpoints VALUES (?, ?, ?)",
            ("tid-2", "", b""),
        )
        conn.commit()

        snapshot = _make_snapshot(has_next=True, has_interrupts=False)
        graph = MagicMock()
        graph.get_state.return_value = snapshot

        result = get_interrupted_threads(graph, conn)

        assert result == []
        conn.close()

    def test_skips_completed_thread(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "CREATE TABLE checkpoints (thread_id TEXT, checkpoint_ns TEXT, data BLOB)",
        )
        conn.execute(
            "INSERT INTO checkpoints VALUES (?, ?, ?)",
            ("tid-3", "", b""),
        )
        conn.commit()

        snapshot = _make_snapshot(has_next=False)
        graph = MagicMock()
        graph.get_state.return_value = snapshot

        result = get_interrupted_threads(graph, conn)

        assert result == []
        conn.close()

    def test_handles_get_state_exception_gracefully(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "CREATE TABLE checkpoints (thread_id TEXT, checkpoint_ns TEXT, data BLOB)",
        )
        conn.execute(
            "INSERT INTO checkpoints VALUES (?, ?, ?)",
            ("tid-err", "", b""),
        )
        conn.commit()

        graph = MagicMock()
        graph.get_state.side_effect = RuntimeError("corrupt checkpoint")

        result = get_interrupted_threads(graph, conn)

        assert result == []
        conn.close()

    def test_multiple_threads_mixed(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "CREATE TABLE checkpoints (thread_id TEXT, checkpoint_ns TEXT, data BLOB)",
        )
        conn.execute("INSERT INTO checkpoints VALUES (?, ?, ?)", ("a", "", b""))
        conn.execute("INSERT INTO checkpoints VALUES (?, ?, ?)", ("b", "", b""))
        conn.execute("INSERT INTO checkpoints VALUES (?, ?, ?)", ("c", "", b""))
        conn.commit()

        snap_interrupted = _make_snapshot(interrupt_value={"cve_id": "CVE-1"})
        snap_clean = _make_snapshot(has_next=True, has_interrupts=False)
        snap_done = _make_snapshot(has_next=False)

        graph = MagicMock()
        graph.get_state.side_effect = [snap_interrupted, snap_clean, snap_done]

        result = get_interrupted_threads(graph, conn)

        assert len(result) == 1
        assert result[0]["thread_id"] == "a"
        conn.close()


# ---------------------------------------------------------------------------
# handle_decision
# ---------------------------------------------------------------------------


class TestHandleDecision:
    """Tests for ``handle_decision``."""

    @patch("siopv.interfaces.dashboard.app.get_graph")
    @patch("siopv.interfaces.dashboard.app.st")
    def test_invokes_graph_with_correct_command(
        self,
        mock_st: MagicMock,
        mock_get_graph: MagicMock,
    ) -> None:
        mock_st.session_state = FakeSessionState(
            {"selected_thread_id": "tid-resume"},
        )
        mock_graph = MagicMock()
        mock_get_graph.return_value = mock_graph

        handle_decision(
            thread_id="tid-resume",
            decision="approve",
            score=None,
            recommendation=None,
        )

        mock_graph.invoke.assert_called_once()
        call_args = mock_graph.invoke.call_args
        cmd = call_args[0][0]
        assert isinstance(cmd, Command)
        assert cmd.resume == {
            "decision": "approve",
            "modified_score": None,
            "modified_recommendation": None,
        }
        config = call_args[1]["config"]
        assert config == {"configurable": {"thread_id": "tid-resume"}}

    @patch("siopv.interfaces.dashboard.app.get_graph")
    @patch("siopv.interfaces.dashboard.app.st")
    def test_clears_selected_thread_after_decision(
        self,
        mock_st: MagicMock,
        mock_get_graph: MagicMock,
    ) -> None:
        mock_st.session_state = FakeSessionState(
            {"selected_thread_id": "tid-clear"},
        )
        mock_get_graph.return_value = MagicMock()

        handle_decision(
            thread_id="tid-clear",
            decision="reject",
            score=None,
            recommendation=None,
        )

        assert mock_st.session_state["selected_thread_id"] is None

    @patch("siopv.interfaces.dashboard.app.get_graph")
    @patch("siopv.interfaces.dashboard.app.st")
    def test_modify_decision_passes_score_and_recommendation(
        self,
        mock_st: MagicMock,
        mock_get_graph: MagicMock,
    ) -> None:
        mock_st.session_state = FakeSessionState(
            {"selected_thread_id": "tid-mod"},
        )
        mock_graph = MagicMock()
        mock_get_graph.return_value = mock_graph

        handle_decision(
            thread_id="tid-mod",
            decision="modify",
            score=0.85,
            recommendation="Patch immediately",
        )

        cmd = mock_graph.invoke.call_args[0][0]
        assert cmd.resume == {
            "decision": "modify",
            "modified_score": 0.85,
            "modified_recommendation": "Patch immediately",
        }


# ---------------------------------------------------------------------------
# get_db_connection
# ---------------------------------------------------------------------------


class TestGetDbConnection:
    """Tests for ``get_db_connection``."""

    @patch("siopv.infrastructure.config.get_settings")
    @patch("siopv.interfaces.dashboard.app.sqlite3")
    @patch("siopv.interfaces.dashboard.app.st")
    def test_connects_with_wal_mode(
        self,
        mock_st: MagicMock,  # noqa: ARG002
        mock_sqlite: MagicMock,
        mock_get_settings: MagicMock,
    ) -> None:
        from siopv.interfaces.dashboard.app import get_db_connection

        mock_get_settings.return_value.checkpoint_db_path = "siopv_checkpoints.db"
        mock_conn = MagicMock()
        mock_sqlite.connect.return_value = mock_conn

        # Clear any cached result
        get_db_connection.clear()
        result = get_db_connection()

        mock_sqlite.connect.assert_called_once_with("siopv_checkpoints.db", check_same_thread=False)
        mock_conn.execute.assert_called_once_with("PRAGMA journal_mode=WAL")
        assert result is mock_conn

    @patch("siopv.infrastructure.config.get_settings")
    @patch("siopv.interfaces.dashboard.app.sqlite3")
    @patch("siopv.interfaces.dashboard.app.st")
    def test_uses_settings_checkpoint_db_path(
        self,
        mock_st: MagicMock,  # noqa: ARG002
        mock_sqlite: MagicMock,
        mock_get_settings: MagicMock,
    ) -> None:
        from siopv.interfaces.dashboard.app import get_db_connection

        mock_get_settings.return_value.checkpoint_db_path = "custom_checkpoints.db"
        mock_conn = MagicMock()
        mock_sqlite.connect.return_value = mock_conn

        get_db_connection.clear()
        get_db_connection()

        mock_sqlite.connect.assert_called_once_with(
            "custom_checkpoints.db", check_same_thread=False
        )


# ---------------------------------------------------------------------------
# get_graph
# ---------------------------------------------------------------------------


class TestGetGraph:
    """Tests for ``get_graph``."""

    @patch("siopv.interfaces.dashboard.app.PipelineGraphBuilder")
    @patch("siopv.interfaces.dashboard.app.SqliteSaver")
    @patch("siopv.interfaces.dashboard.app.get_db_connection")
    @patch("siopv.interfaces.dashboard.app.st")
    def test_builds_and_compiles_graph(
        self,
        mock_st: MagicMock,  # noqa: ARG002
        mock_get_conn: MagicMock,
        mock_saver_cls: MagicMock,
        mock_builder_cls: MagicMock,
    ) -> None:
        from siopv.interfaces.dashboard.app import get_graph

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        mock_saver = MagicMock()
        mock_saver_cls.return_value = mock_saver

        mock_builder = MagicMock()
        mock_compiled = MagicMock()
        mock_builder.compile.return_value = mock_compiled
        mock_builder_cls.return_value = mock_builder

        get_graph.clear()
        result = get_graph()

        mock_builder.build.assert_called_once()
        mock_builder.compile.assert_called_once_with(with_checkpointer=False)
        assert mock_compiled.checkpointer is mock_saver
        assert result is mock_compiled


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for ``main``."""

    @patch("siopv.interfaces.dashboard.app.get_db_connection")
    @patch("siopv.interfaces.dashboard.app.get_graph")
    @patch("siopv.interfaces.dashboard.app.get_interrupted_threads")
    @patch("siopv.interfaces.dashboard.app.render_case_list")
    @patch("siopv.interfaces.dashboard.app.render_evidence_panel")
    @patch("siopv.interfaces.dashboard.app.render_decision_panel")
    @patch("siopv.interfaces.dashboard.app.st")
    def test_main_no_cases_shows_info(
        self,
        mock_st: MagicMock,
        mock_decision: MagicMock,  # noqa: ARG002
        mock_evidence: MagicMock,  # noqa: ARG002
        mock_case_list: MagicMock,  # noqa: ARG002
        mock_get_threads: MagicMock,
        mock_get_graph: MagicMock,  # noqa: ARG002
        mock_get_conn: MagicMock,  # noqa: ARG002
    ) -> None:
        from siopv.interfaces.dashboard.app import main

        mock_st.session_state = FakeSessionState()
        mock_st.session_state["pending_cases"] = []
        mock_get_threads.return_value = []

        # st.fragment returns a decorator that just calls the function
        mock_st.fragment.return_value = lambda f: f

        main()

        mock_st.set_page_config.assert_called_once()
        mock_st.title.assert_called_once()
        mock_st.info.assert_called_with("No escalated cases pending review.")

    @patch("siopv.interfaces.dashboard.app.get_db_connection")
    @patch("siopv.interfaces.dashboard.app.get_graph")
    @patch("siopv.interfaces.dashboard.app.get_interrupted_threads")
    @patch("siopv.interfaces.dashboard.app.render_case_list")
    @patch("siopv.interfaces.dashboard.app.render_evidence_panel")
    @patch("siopv.interfaces.dashboard.app.render_decision_panel")
    @patch("siopv.interfaces.dashboard.app.st")
    def test_main_with_cases_renders_panels(
        self,
        mock_st: MagicMock,
        mock_decision: MagicMock,
        mock_evidence: MagicMock,
        mock_case_list: MagicMock,
        mock_get_threads: MagicMock,
        mock_get_graph: MagicMock,  # noqa: ARG002
        mock_get_conn: MagicMock,  # noqa: ARG002
    ) -> None:
        from siopv.interfaces.dashboard.app import main

        case = {
            "thread_id": "t-sel",
            "interrupt_data": {},
            "state": {},
            "created_at": "2026-03-17T10:00:00Z",
        }
        mock_st.session_state = FakeSessionState(
            {"selected_thread_id": "t-sel", "pending_cases": [case]},
        )
        mock_get_threads.return_value = [case]

        # st.fragment returns a decorator that just calls the function
        mock_st.fragment.return_value = lambda f: f

        # columns context managers
        mock_col = MagicMock()
        mock_col.__enter__ = MagicMock(return_value=mock_col)
        mock_col.__exit__ = MagicMock(return_value=False)
        mock_st.columns.return_value = [mock_col, mock_col]

        main()

        mock_case_list.assert_called_once_with([case])
        mock_evidence.assert_called_once_with(case)
        mock_decision.assert_called_once()

    @patch("siopv.interfaces.dashboard.app.get_db_connection")
    @patch("siopv.interfaces.dashboard.app.get_graph")
    @patch("siopv.interfaces.dashboard.app.get_interrupted_threads")
    @patch("siopv.interfaces.dashboard.app.render_case_list")
    @patch("siopv.interfaces.dashboard.app.st")
    def test_main_no_selection_shows_select_prompt(
        self,
        mock_st: MagicMock,
        mock_case_list: MagicMock,  # noqa: ARG002
        mock_get_threads: MagicMock,
        mock_get_graph: MagicMock,  # noqa: ARG002
        mock_get_conn: MagicMock,  # noqa: ARG002
    ) -> None:
        from siopv.interfaces.dashboard.app import main

        case = {
            "thread_id": "t-xyz",
            "interrupt_data": {},
            "state": {},
            "created_at": "2026-03-17T10:00:00Z",
        }
        mock_st.session_state = FakeSessionState(
            {"selected_thread_id": None, "pending_cases": [case]},
        )
        mock_get_threads.return_value = [case]
        mock_st.fragment.return_value = lambda f: f

        mock_col = MagicMock()
        mock_col.__enter__ = MagicMock(return_value=mock_col)
        mock_col.__exit__ = MagicMock(return_value=False)
        mock_st.columns.return_value = [mock_col, mock_col]

        main()

        mock_st.info.assert_called_with("Select a case from the list to review.")
