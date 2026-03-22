"""SIOPV Pipeline Monitor — Real-time Visualization Dashboard.

Streamlit application for executing and monitoring the SIOPV vulnerability
processing pipeline in real time.  Shows each graph node's progress, timing,
and data flow as the pipeline processes a Trivy report.

Uses LangGraph ``astream_events(version="v2")`` via a thread-based
async-to-sync bridge to stream node-level events into Streamlit's
synchronous rendering model.

Launch: streamlit run src/siopv/interfaces/dashboard/pipeline_monitor.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st
import structlog

from siopv.domain.constants import PIPELINE_NODE_LABELS
from siopv.interfaces.dashboard.components.pipeline_flow import (
    create_flow_placeholders,
    mark_skipped_nodes,
    update_node_end,
    update_node_error,
    update_node_start,
)
from siopv.interfaces.dashboard.components.pipeline_summary import (
    render_pipeline_summary,
)
from siopv.interfaces.dashboard.streaming import (
    PipelineEvent,
    stream_pipeline_events,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------


def _initialize_session_state() -> None:
    """Ensure required keys exist in Streamlit session state."""
    defaults: dict[str, Any] = {
        "pipeline_running": False,
        "pipeline_completed": False,
        "last_run_data": None,
        "last_run_flow": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------------------------------------------------------------------------
# Sidebar — execution configuration
# ---------------------------------------------------------------------------


def _render_sidebar() -> dict[str, Any]:
    """Render the sidebar with pipeline execution configuration.

    Returns:
        Dict with configuration values: ``report_path``, ``user_id``,
        ``project_id``, ``batch_size``.
    """
    from siopv.infrastructure.config import get_settings  # noqa: PLC0415

    settings = get_settings()

    st.sidebar.header("Pipeline Configuration")

    report_path = st.sidebar.text_input(
        "Trivy Report Path",
        value="",
        placeholder="/path/to/trivy-report.json",
        help="Absolute path to a Trivy JSON vulnerability report.",
    )

    uploaded_file = st.sidebar.file_uploader(
        "Or upload a Trivy JSON report",
        type=["json"],
        help="Upload a Trivy vulnerability report in JSON format.",
    )

    st.sidebar.divider()

    user_id = st.sidebar.text_input(
        "User ID",
        value=settings.default_user_id or "",
        help="User identifier for authorization (Phase 5). Uses .env default if blank.",
    )

    project_id = st.sidebar.text_input(
        "Project ID",
        value=settings.default_project_id,
        help="Project identifier for authorization context.",
    )

    system_execution = st.sidebar.checkbox(
        "System Execution (bypass authorization)",
        value=True,
        help="Skip OpenFGA authorization check. Use when OpenFGA server is not running.",
    )

    batch_size = st.sidebar.number_input(
        "Batch Size",
        min_value=1,
        max_value=500,
        value=50,
        step=10,
        help="Maximum concurrent enrichment requests.",
    )

    return {
        "report_path": report_path.strip() if report_path else None,
        "uploaded_file": uploaded_file,
        "user_id": user_id.strip() or settings.default_user_id,
        "project_id": project_id.strip() or settings.default_project_id,
        "system_execution": system_execution,
        "batch_size": int(batch_size),
    }


# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------


def _resolve_report_path(config: dict[str, Any]) -> Path | None:
    """Resolve the report path from sidebar config.

    Handles both direct path input and file upload. Uploaded files are
    saved to a temporary location.

    Args:
        config: Sidebar configuration dict.

    Returns:
        Resolved ``Path`` to the report file, or ``None`` if not provided.
    """
    # Direct path takes priority
    if config["report_path"]:
        path = Path(config["report_path"])
        if path.exists() and path.is_file():
            return path
        st.error(f"Report file not found: {config['report_path']}")
        return None

    # Uploaded file — save to temp location
    uploaded = config["uploaded_file"]
    if uploaded is not None:
        from siopv.infrastructure.config import get_settings  # noqa: PLC0415

        settings = get_settings()
        output_dir = settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        temp_path = output_dir / f"uploaded_{uploaded.name}"
        temp_path.write_bytes(uploaded.getvalue())
        return temp_path

    return None


def _execute_pipeline(config: dict[str, Any], report_path: Path) -> None:
    """Execute the pipeline with real-time visualization.

    Builds pipeline ports, starts streaming, and updates the flow
    visualization as events arrive.

    Args:
        config: Sidebar configuration dict.
        report_path: Resolved path to the Trivy report.
    """
    from siopv.infrastructure.config import get_settings  # noqa: PLC0415
    from siopv.infrastructure.di.pipeline import build_pipeline_ports  # noqa: PLC0415

    settings = get_settings()

    st.session_state.pipeline_running = True
    st.session_state.pipeline_completed = False

    # Build ports
    with st.status("Initializing pipeline components...", expanded=False) as init_status:
        try:
            ports = build_pipeline_ports(
                settings,
                batch_size=config["batch_size"],
                output_dir=settings.output_dir,
            )
            init_status.update(label="Pipeline components initialized", state="complete")
        except Exception as exc:
            init_status.update(label=f"Initialization failed: {exc}", state="error")
            st.session_state.pipeline_running = False
            logger.exception("pipeline_init_failed", error=str(exc))
            return

    # Create flow visualization
    flow = create_flow_placeholders()

    # Execution log
    log_container = st.container()

    # Stream events
    accumulated_data: dict[str, Any] = {}

    try:
        event_gen = stream_pipeline_events(
            report_path=report_path,
            ports=ports,
            user_id=config["user_id"],
            project_id=config["project_id"],
            system_execution=config["system_execution"],
            stream_timeout_seconds=settings.pipeline_monitor_stream_timeout_seconds,
        )

        for event in event_gen:
            _handle_event(event, flow, log_container, accumulated_data)

    except TimeoutError:
        st.error("Pipeline execution timed out. Check system resources and API connectivity.")
        logger.exception("pipeline_streaming_timeout")
    except Exception as exc:
        st.error(f"Pipeline execution failed: {exc}")
        logger.exception("pipeline_execution_failed", error=str(exc))
    finally:
        # Mark any remaining pending nodes as skipped
        mark_skipped_nodes(flow)
        st.session_state.pipeline_running = False
        st.session_state.pipeline_completed = True
        st.session_state.last_run_data = accumulated_data
        st.session_state.last_run_flow = flow

    # Render summary
    if accumulated_data:
        render_pipeline_summary(flow, accumulated_data)


def _handle_event(
    event: PipelineEvent,
    flow: Any,
    log_container: Any,
    accumulated_data: dict[str, Any],
) -> None:
    """Process a single pipeline event and update the UI.

    Args:
        event: The structured pipeline event.
        flow: Flow placeholders for node card updates.
        log_container: Streamlit container for the execution log.
        accumulated_data: Running dict of all state data from node outputs.
    """
    if event.event_type == "pipeline_start":
        with log_container:
            st.caption("Pipeline execution started")

    elif event.event_type == "node_start" and event.node_name:
        label = PIPELINE_NODE_LABELS.get(event.node_name, event.node_name)
        update_node_start(flow, event.node_name, event.timestamp)
        with log_container:
            st.markdown(f"**{label}** — started at `{event.timestamp.strftime('%H:%M:%S')}`")

    elif event.event_type == "node_end" and event.node_name:
        label = PIPELINE_NODE_LABELS.get(event.node_name, event.node_name)
        update_node_end(flow, event.node_name, event.timestamp, event.data)
        accumulated_data.update(event.data)

        elapsed = flow.node_states[event.node_name].elapsed_display
        with log_container:
            st.markdown(f"**{label}** — complete ({elapsed})")

    elif event.event_type == "node_error" and event.node_name:
        label = PIPELINE_NODE_LABELS.get(event.node_name, event.node_name)
        error_msg = event.data.get("error", "Unknown error")
        update_node_error(flow, event.node_name, str(error_msg))
        with log_container:
            st.error(f"**{label}** — failed: {error_msg}")

    elif event.event_type == "pipeline_end":
        accumulated_data.update(event.data)
        with log_container:
            st.markdown("**Pipeline execution complete**")

    elif event.event_type == "pipeline_error":
        error_msg = event.data.get("error", "Unknown error")
        with log_container:
            st.error(f"**Pipeline error:** {error_msg}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Render the SIOPV Pipeline Monitor dashboard."""
    st.set_page_config(
        page_title="SIOPV - Pipeline Monitor",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("SIOPV — Pipeline Monitor")
    st.caption(
        "Real-time visualization of the vulnerability processing pipeline. "
        "Upload a Trivy report and watch each stage execute live."
    )

    _initialize_session_state()

    config = _render_sidebar()

    # Execution trigger
    report_path = _resolve_report_path(config)

    if (
        st.sidebar.button(
            "Execute Pipeline",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.pipeline_running or report_path is None,
        )
        and report_path is not None
    ):
        _execute_pipeline(config, report_path)

    # Show guidance when idle
    if not st.session_state.pipeline_running and not st.session_state.pipeline_completed:
        st.info(
            "Configure a Trivy report path or upload a JSON file in the sidebar, "
            "then click **Execute Pipeline** to start."
        )

    # Re-render last summary if page is rerun after completion
    if (
        st.session_state.pipeline_completed
        and not st.session_state.pipeline_running
        and st.session_state.last_run_data
        and st.session_state.last_run_flow
    ):
        _render_last_run_summary()


def _render_last_run_summary() -> None:
    """Re-render the summary from the last completed pipeline run.

    Uses cached data and flow state from ``st.session_state`` to avoid
    re-executing the pipeline on Streamlit reruns.
    """
    st.divider()
    st.subheader("Last Execution Results")
    render_pipeline_summary(
        st.session_state.last_run_flow,
        st.session_state.last_run_data,
    )


if __name__ == "__main__":
    main()
