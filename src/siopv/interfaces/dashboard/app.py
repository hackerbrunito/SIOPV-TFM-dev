"""SIOPV Human-in-the-Loop Dashboard.

Streamlit application for reviewing escalated vulnerability cases.
Polls the SQLite checkpoint database for interrupted pipeline threads
and allows human analysts to submit review decisions.

Launch: streamlit run src/siopv/interfaces/dashboard/app.py
"""

from __future__ import annotations

import asyncio
import sqlite3
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig

import streamlit as st
import structlog
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from siopv.application.orchestration.graph import (
    PipelineGraphBuilder,
)
from siopv.interfaces.dashboard.components.case_list import render_case_list
from siopv.interfaces.dashboard.components.decision_panel import (
    render_decision_panel,
)
from siopv.interfaces.dashboard.components.evidence_panel import (
    render_evidence_panel,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Cached resources
# ---------------------------------------------------------------------------


@st.cache_resource
def get_db_connection() -> sqlite3.Connection:
    """Create a cached SQLite connection to the checkpoint database.

    Uses WAL mode for concurrent read access from the Streamlit process
    while the pipeline process writes checkpoints.

    Returns:
        SQLite connection with WAL mode and check_same_thread disabled.
    """
    from siopv.infrastructure.config import get_settings  # noqa: PLC0415

    db_path = get_settings().checkpoint_db_path
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    logger.info("dashboard_db_connected", db_path=str(db_path))
    return conn


@st.cache_resource
def get_graph() -> CompiledStateGraph:  # type: ignore[type-arg]
    """Build and compile the pipeline graph with a SqliteSaver checkpointer.

    The graph is compiled without port implementations since the dashboard
    only needs to read checkpoint state and invoke ``Command(resume=...)``.

    Returns:
        Compiled LangGraph StateGraph with SqliteSaver checkpointer.
    """
    conn = get_db_connection()
    checkpointer = SqliteSaver(conn)

    builder = PipelineGraphBuilder()
    builder.build()

    compiled = builder.compile(with_checkpointer=False)
    # Attach the shared checkpointer backed by the WAL-mode connection
    compiled.checkpointer = checkpointer

    logger.info("dashboard_graph_compiled")
    return compiled


# ---------------------------------------------------------------------------
# Thread discovery
# ---------------------------------------------------------------------------


def get_interrupted_threads(
    graph: CompiledStateGraph,  # type: ignore[type-arg]
    conn: sqlite3.Connection,
) -> list[dict[str, Any]]:
    """Discover threads with pending interrupts in the checkpoint database.

    Queries the ``checkpoints`` table for distinct ``thread_id`` values, then
    inspects each thread's state snapshot to determine whether it has pending
    interrupt tasks.

    Args:
        graph: Compiled pipeline graph with checkpointer attached.
        conn: SQLite connection to the checkpoint database.

    Returns:
        List of dicts, each containing ``thread_id``, ``interrupt_data``,
        ``state``, and ``created_at`` for threads awaiting human review.
    """
    cursor = conn.execute(
        "SELECT DISTINCT thread_id FROM checkpoints WHERE checkpoint_ns = ''",
    )
    thread_ids = [row[0] for row in cursor.fetchall()]

    interrupted: list[dict[str, Any]] = []
    for tid in thread_ids:
        config: RunnableConfig = {"configurable": {"thread_id": tid}}
        try:
            snapshot = graph.get_state(config)
            if snapshot and snapshot.next and snapshot.tasks:
                has_interrupts = any(t.interrupts for t in snapshot.tasks)
                if has_interrupts:
                    interrupt_value = snapshot.tasks[0].interrupts[0].value
                    interrupted.append(
                        {
                            "thread_id": tid,
                            "interrupt_data": interrupt_value,
                            "state": snapshot.values,
                            "created_at": snapshot.created_at,
                        },
                    )
        except Exception:
            logger.exception("error_checking_thread", thread_id=tid)

    return interrupted


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------


def _initialize_session_state() -> None:
    """Ensure required keys exist in Streamlit session state."""
    defaults: dict[str, Any] = {
        "selected_thread_id": None,
        "polling_interval": 5,
        "last_poll": None,
        "pending_cases": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------------------------------------------------------------------------
# Decision handler
# ---------------------------------------------------------------------------


def handle_decision(
    thread_id: str,
    decision: str,
    score: float | None,
    recommendation: str | None,
) -> None:
    """Submit a human review decision and resume the interrupted pipeline.

    Invokes the compiled graph with a ``Command(resume=...)`` containing
    the analyst's decision, optional modified score, and recommendation.

    Args:
        thread_id: The pipeline thread to resume.
        decision: One of ``"approve"``, ``"reject"``, or ``"modify"``.
        score: Optional overridden risk score (when decision is ``"modify"``).
        recommendation: Optional overridden recommendation text.
    """
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    resume_value: dict[str, Any] = {
        "decision": decision,
        "modified_score": score,
        "modified_recommendation": recommendation,
    }
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver  # noqa: PLC0415

    from siopv.infrastructure.config import get_settings  # noqa: PLC0415

    async def _resume_pipeline() -> None:
        """Resume the pipeline asynchronously (required for async nodes)."""
        db_path = get_settings().checkpoint_db_path
        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
            builder = PipelineGraphBuilder()
            builder.build()
            compiled = builder.compile(with_checkpointer=False)
            compiled.checkpointer = checkpointer
            await compiled.ainvoke(Command(resume=resume_value), config=config)

    asyncio.run(_resume_pipeline())
    st.session_state.selected_thread_id = None
    logger.info("decision_submitted", thread_id=thread_id, decision=decision)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Render the SIOPV Human-in-the-Loop review dashboard."""
    st.set_page_config(page_title="SIOPV - Review Dashboard", layout="wide")
    st.title("SIOPV \u2014 Vulnerability Review Dashboard")

    _initialize_session_state()

    graph = get_graph()
    conn = get_db_connection()

    # Polling fragment — refreshes pending cases every N seconds
    @st.fragment(run_every=5)
    def poll_cases() -> None:
        cases = get_interrupted_threads(graph, conn)
        st.session_state.pending_cases = cases
        st.caption(f"Polling\u2026 {len(cases)} pending case(s)")

    poll_cases()

    cases: list[dict[str, Any]] = st.session_state.get("pending_cases", [])

    if not cases:
        st.info("No escalated cases pending review.")
        return

    left_col, right_col = st.columns([1, 2])

    with left_col:
        render_case_list(cases)

    with right_col:
        selected: str | None = st.session_state.get("selected_thread_id")
        if selected:
            case = next(
                (c for c in cases if c["thread_id"] == selected),
                None,
            )
            if case:
                render_evidence_panel(case)
                render_decision_panel(
                    case,
                    on_decision=handle_decision,
                )
        else:
            st.info("Select a case from the list to review.")


if __name__ == "__main__":
    main()
