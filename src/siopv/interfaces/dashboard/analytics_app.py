"""SIOPV Security Analytics — Multi-Page Streamlit Application.

Entry point for the SIOPV analytics dashboard. Uses ``st.navigation``
and ``st.Page`` (Streamlit 1.36+ multi-page API) to organize the
dashboard into three pages:

1. **Security Analytics** — KPIs, severity charts, ML analysis, vulnerability table
2. **Live Monitor** — Observer mode + manual pipeline execution with React Flow diagram
3. **Scan History** — Historical runs and scan-to-scan comparison

Launch:
    streamlit run src/siopv/interfaces/dashboard/analytics_app.py

The application shares a compiled graph and database connection across
all pages via ``st.session_state``, initialized once at startup.
"""

from __future__ import annotations

import sqlite3

import streamlit as st
import structlog
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph

from siopv.application.orchestration.graph import PipelineGraphBuilder

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Shared resources (initialized once per session)
# ---------------------------------------------------------------------------


@st.cache_resource
def _get_db_connection() -> sqlite3.Connection:
    """Create a cached SQLite connection to the checkpoint database.

    Uses WAL mode for concurrent read access from the dashboard
    while pipeline processes write checkpoints.
    """
    from siopv.infrastructure.config import get_settings  # noqa: PLC0415

    db_path = get_settings().checkpoint_db_path
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    logger.info("analytics_db_connected", db_path=str(db_path))
    return conn


@st.cache_resource
def _get_graph() -> CompiledStateGraph:  # type: ignore[type-arg]
    """Build and compile the pipeline graph with checkpointer.

    The graph is compiled without port implementations since the
    analytics dashboard only reads checkpoint state — it doesn't
    execute pipeline nodes.
    """
    conn = _get_db_connection()
    checkpointer = SqliteSaver(conn)

    builder = PipelineGraphBuilder()
    builder.build()
    compiled = builder.compile(with_checkpointer=False)
    compiled.checkpointer = checkpointer

    logger.info("analytics_graph_compiled")
    return compiled


def _initialize_shared_state() -> None:
    """Store shared resources in session state for access by all pages."""
    if "shared_graph" not in st.session_state:
        st.session_state["shared_graph"] = _get_graph()
    if "shared_conn" not in st.session_state:
        st.session_state["shared_conn"] = _get_db_connection()


# ---------------------------------------------------------------------------
# Page definitions
# ---------------------------------------------------------------------------


def page_security_analytics() -> None:
    """Security Analytics page entry point."""
    from siopv.interfaces.dashboard.pages.security_analytics import (  # noqa: PLC0415
        render_security_analytics,
    )

    render_security_analytics()


def page_live_monitor() -> None:
    """Live Monitor page entry point."""
    from siopv.interfaces.dashboard.pages.live_monitor import render_live_monitor  # noqa: PLC0415

    render_live_monitor()


def page_scan_history() -> None:
    """Scan History page entry point."""
    from siopv.interfaces.dashboard.pages.scan_history import render_scan_history  # noqa: PLC0415

    render_scan_history()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """SIOPV Security Analytics Dashboard — multi-page application."""
    st.set_page_config(
        page_title="SIOPV - Security Analytics",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Widen sidebar for better readability of pipeline run labels
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { min-width: 380px; max-width: 480px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _initialize_shared_state()

    # Multi-page navigation (Streamlit 1.36+ API)
    pages = st.navigation(
        {
            "Analytics": [
                st.Page(page_security_analytics, title="Security Analytics", default=True),
                st.Page(page_live_monitor, title="Live Monitor"),
                st.Page(page_scan_history, title="Scan History"),
            ],
        }
    )

    # Sidebar branding
    st.sidebar.title("SIOPV")
    st.sidebar.caption("Sistema Inteligente de Orquestacion y Priorizacion de Vulnerabilidades")

    pages.run()


if __name__ == "__main__":
    main()
