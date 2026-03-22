"""LangGraph pipeline builder for SIOPV orchestration.

Builds and compiles the StateGraph with nodes, edges, and checkpointing.
Based on specification section 3.4.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import structlog
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from siopv.application.orchestration.edges import (
    route_after_classify,
    route_after_escalate,
)
from siopv.application.orchestration.nodes import (
    authorization_node,
    classify_node,
    dlp_node,
    enrich_node,
    escalate_node,
    ingest_node,
    output_node,
    route_after_authorization,
)
from siopv.application.orchestration.state import PipelineState, create_initial_state
from siopv.application.use_cases.ingest_trivy import IngestTrivyReportUseCase

if TYPE_CHECKING:
    from siopv.application.ports import (
        AuthorizationPort,
        EPSSClientPort,
        GitHubAdvisoryClientPort,
        NVDClientPort,
        OSINTSearchClientPort,
        VectorStorePort,
    )
    from siopv.application.ports.dlp import DLPPort
    from siopv.application.ports.feature_engineering import FeatureEngineerPort
    from siopv.application.ports.jira_client import JiraClientPort
    from siopv.application.ports.llm_analysis import LLMAnalysisPort
    from siopv.application.ports.metrics_exporter import MetricsExporterPort
    from siopv.application.ports.ml_classifier import MLClassifierPort
    from siopv.application.ports.parsing import TrivyParserPort
    from siopv.application.ports.pdf_generator import PdfGeneratorPort
    from siopv.domain.value_objects.discrepancy import ThresholdConfig
    from siopv.domain.value_objects.escalation import EscalationConfig

logger = structlog.get_logger(__name__)


@dataclass
class PipelinePorts:
    """Bundle of all port dependencies for the pipeline graph.

    Groups all injectable ports and configuration into a single object,
    replacing 16-parameter signatures on builder, factory, and runner.
    """

    checkpoint_db_path: str | Path | None = None
    trivy_parser: TrivyParserPort | None = None
    authorization_port: AuthorizationPort | None = None
    dlp_port: DLPPort | None = None
    nvd_client: NVDClientPort | None = None
    epss_client: EPSSClientPort | None = None
    github_client: GitHubAdvisoryClientPort | None = None
    osint_client: OSINTSearchClientPort | None = None
    vector_store: VectorStorePort | None = None
    classifier: MLClassifierPort | None = None
    feature_engineer: FeatureEngineerPort | None = None
    llm_analysis: LLMAnalysisPort | None = None
    jira: JiraClientPort | None = None
    pdf: PdfGeneratorPort | None = None
    metrics: MetricsExporterPort | None = None
    threshold_config: ThresholdConfig | None = None
    escalation_config: EscalationConfig | None = None
    batch_size: int | None = None
    output_dir: Path | None = None


# Allowed file extensions for validation
ALLOWED_DB_EXTENSIONS = {".db", ".sqlite", ".sqlite3"}
ALLOWED_OUTPUT_EXTENSIONS = {".md", ".mmd", ".mermaid", ".txt"}


def _validate_path(
    path: Path,
    *,
    must_exist: bool = False,
    allowed_extensions: set[str] | None = None,
) -> Path:
    """Validate and resolve path to prevent traversal attacks.

    Args:
        path: Path to validate
        must_exist: If True, verify parent directory exists
        allowed_extensions: Set of allowed file extensions (e.g., {".db", ".sqlite"})

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If path validation fails
    """
    resolved = path.resolve()

    if must_exist and not resolved.parent.exists():
        msg = f"Parent directory does not exist: {resolved.parent}"
        raise ValueError(msg)

    if allowed_extensions and resolved.suffix.lower() not in allowed_extensions:
        msg = f"Invalid file extension '{resolved.suffix}'. Allowed: {allowed_extensions}"
        raise ValueError(msg)

    return resolved


def _make_async_node(fn: Any, **kwargs: Any) -> Any:
    """Create an async node closure binding keyword args to an async node function."""

    async def _node(state: PipelineState) -> dict[str, object]:
        result: dict[str, object] = await fn(state, **kwargs)
        return result

    return _node


def _make_sync_node(fn: Any, **kwargs: Any) -> Any:
    """Create a sync node closure binding keyword args to a sync node function."""

    def _node(state: PipelineState) -> dict[str, object]:
        result: dict[str, object] = fn(state, **kwargs)
        return result

    return _node


class PipelineGraphBuilder:
    """Builder for the SIOPV LangGraph pipeline.

    Constructs a StateGraph with the following nodes:
    - authorize: Authorization gatekeeper (Phase 5 - Zero Trust)
    - ingest: Parse Trivy report (Phase 1)
    - dlp: DLP guardrail — sanitize descriptions (Phase 6)
    - enrich: Context enrichment with CRAG (Phase 2)
    - classify: ML risk classification (Phase 3)
    - escalate: Human review escalation (Phase 4)
    - output: Report generation — Jira, PDF, CSV/JSON (Phase 8)

    Flow: START -> authorize -> ingest -> dlp -> enrich -> classify -> [escalate] -> output -> END

    Conditional routing is based on:
    - Authorization check (Phase 5): If denied -> end with 403
    - Uncertainty Trigger (Phase 4): If ML/LLM discrepancy high -> escalate
    """

    def __init__(self, ports: PipelinePorts | None = None) -> None:
        """Initialize the pipeline builder.

        Args:
            ports: Bundle of all port dependencies and configuration.
        """
        self._ports = ports or PipelinePorts()
        self._graph: StateGraph[PipelineState] | None = None
        self._compiled: CompiledStateGraph[PipelineState] | None = None

    def build(self) -> PipelineGraphBuilder:
        """Build the StateGraph with all nodes and edges.

        Returns:
            Self for method chaining
        """
        logger.info("building_pipeline_graph")

        # Create StateGraph with PipelineState schema
        self._graph = StateGraph(PipelineState)

        # Add nodes
        self._add_nodes()

        # Add edges
        self._add_edges()

        logger.info("pipeline_graph_built")
        return self

    def _add_nodes(self) -> None:
        """Add all pipeline nodes to the graph.

        Uses _make_node to bind port dependencies to each node function,
        reducing repetitive closure boilerplate.
        """
        if self._graph is None:
            msg = "Graph not initialized. Call build() first."
            raise RuntimeError(msg)

        p = self._ports

        # Authorize (Phase 5 gatekeeper)
        self._graph.add_node(
            "authorize",
            _make_async_node(authorization_node, authorization_port=p.authorization_port),
        )

        # Ingest (Phase 1)
        ingest_use_case = (
            IngestTrivyReportUseCase(parser=p.trivy_parser) if p.trivy_parser is not None else None
        )
        self._graph.add_node("ingest", _make_sync_node(ingest_node, use_case=ingest_use_case))

        # DLP (Phase 6 guardrail)
        self._graph.add_node("dlp", _make_async_node(dlp_node, dlp_port=p.dlp_port))

        # Enrich (Phase 2 CRAG)
        enrich_kwargs: dict[str, object] = {
            "nvd_client": p.nvd_client,
            "epss_client": p.epss_client,
            "github_client": p.github_client,
            "osint_client": p.osint_client,
            "vector_store": p.vector_store,
            "llm_analysis": p.llm_analysis,
        }
        if p.batch_size is not None:
            enrich_kwargs["max_concurrent"] = p.batch_size
        self._graph.add_node(
            "enrich",
            _make_async_node(enrich_node, **enrich_kwargs),
        )

        # Classify (Phase 3 ML)
        self._graph.add_node(
            "classify",
            _make_async_node(
                classify_node,
                classifier=p.classifier,
                llm_analysis=p.llm_analysis,
                feature_engineer=p.feature_engineer,
            ),
        )

        # Escalate (Phase 4 + Phase 7 HITL)
        esc = p.escalation_config
        self._graph.add_node(
            "escalate",
            _make_sync_node(
                escalate_node,
                level_thresholds=esc.level_thresholds if esc else None,
                review_deadline_hours=esc.review_deadline_hours if esc else None,
                threshold_config=p.threshold_config,
            ),
        )

        # Output (Phase 8)
        self._graph.add_node(
            "output",
            _make_async_node(
                output_node, jira=p.jira, pdf=p.pdf, metrics=p.metrics, output_dir=p.output_dir
            ),
        )

        logger.debug(
            "pipeline_nodes_added",
            nodes=["authorize", "ingest", "dlp", "enrich", "classify", "escalate", "output"],
        )

    def _add_edges(self) -> None:
        """Add all edges and conditional routing to the graph."""

        if self._graph is None:
            msg = "Graph not initialized. Call build() first."
            raise RuntimeError(msg)

        # Flow: START -> authorize -> (conditional) -> ingest -> dlp -> enrich -> classify
        self._graph.add_edge(START, "authorize")

        # Conditional routing after authorization (Phase 5 gatekeeper)
        self._graph.add_conditional_edges(
            "authorize",
            route_after_authorization,
            {
                "ingest": "ingest",
                "end": END,
            },
        )

        # Linear flow: ingest -> dlp (Phase 6) -> enrich -> classify
        self._graph.add_edge("ingest", "dlp")
        self._graph.add_edge("dlp", "enrich")
        self._graph.add_edge("enrich", "classify")

        # Conditional routing after classify based on uncertainty
        _threshold_config = self._ports.threshold_config

        def _route_after_classify(state: dict[str, object]) -> str:
            return route_after_classify(state, config=_threshold_config)

        self._graph.add_conditional_edges(
            "classify",
            _route_after_classify,
            {
                "escalate": "escalate",
                "continue": "output",
                "end": END,
            },
        )

        # After escalate, go to output
        self._graph.add_conditional_edges(
            "escalate",
            route_after_escalate,
            {
                "end": "output",
            },
        )

        # Output -> END
        self._graph.add_edge("output", END)

        logger.debug("pipeline_edges_added")

    def _create_checkpointer(self) -> SqliteSaver:
        """Create and initialize SQLite checkpointer.

        Returns:
            SqliteSaver instance for LangGraph checkpointing

        Raises:
            ValueError: If checkpoint database path validation fails
        """

        if self._ports.checkpoint_db_path is None:
            msg = "checkpoint_db_path must be set in PipelinePorts (from settings)"
            raise ValueError(msg)
        db_path = _validate_path(
            Path(self._ports.checkpoint_db_path),
            allowed_extensions=ALLOWED_DB_EXTENSIONS,
        )
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        logger.info("checkpointer_initialized", db_path=str(db_path))
        return SqliteSaver(conn)

    def compile(self, *, with_checkpointer: bool = True) -> CompiledStateGraph[PipelineState]:
        """Compile the graph with optional checkpointing.

        Args:
            with_checkpointer: Whether to enable SQLite checkpointing

        Returns:
            Compiled StateGraph ready for invocation
        """
        if self._graph is None:
            self.build()

        if self._graph is None:
            msg = "Failed to build graph"
            raise RuntimeError(msg)

        checkpointer = self._create_checkpointer() if with_checkpointer else None
        self._compiled = cast(
            CompiledStateGraph[PipelineState],
            self._graph.compile(checkpointer=checkpointer),
        )

        logger.info(
            "pipeline_graph_compiled",
            with_checkpointer=with_checkpointer,
        )

        return self._compiled

    def get_compiled(self) -> CompiledStateGraph[PipelineState]:
        """Get the compiled graph, compiling if necessary.

        Returns:
            Compiled StateGraph
        """
        if self._compiled is None:
            use_checkpointer = self._ports.checkpoint_db_path is not None
            return self.compile(with_checkpointer=use_checkpointer)
        return self._compiled

    def visualize(self) -> str:
        """Generate Mermaid diagram of the graph.

        Returns:
            Mermaid diagram string
        """
        compiled = self.get_compiled()
        return compiled.get_graph().draw_mermaid()

    def save_visualization(self, output_path: Path | str) -> Path:
        """Save graph visualization to file.

        Args:
            output_path: Path to save the Mermaid diagram

        Returns:
            Path to saved file

        Raises:
            ValueError: If path validation fails
        """
        # Validate output path
        validated_path = _validate_path(
            Path(output_path),
            must_exist=True,
            allowed_extensions=ALLOWED_OUTPUT_EXTENSIONS,
        )

        mermaid = self.visualize()

        validated_path.write_text(mermaid)
        logger.info("visualization_saved", path=str(validated_path))

        return validated_path


def create_pipeline_graph(
    ports: PipelinePorts | None = None,
    *,
    with_checkpointer: bool = True,
) -> CompiledStateGraph[PipelineState]:
    """Factory function to create and compile the pipeline graph.

    Args:
        ports: Bundle of all port dependencies and configuration.
        with_checkpointer: Whether to enable checkpointing

    Returns:
        Compiled StateGraph ready for invocation
    """
    builder = PipelineGraphBuilder(ports)
    return builder.build().compile(with_checkpointer=with_checkpointer)


async def run_pipeline(
    report_path: str | Path,
    ports: PipelinePorts | None = None,
    *,
    thread_id: str | None = None,
    user_id: str | None = None,
    project_id: str | None = None,
    system_execution: bool = False,
) -> PipelineState:
    """Run the full pipeline on a Trivy report (async).

    Uses ``ainvoke()`` because some graph nodes are async
    (authorization_node, dlp_node, enrich_node, output_node).
    Callers in sync contexts (e.g. CLI) should wrap with ``asyncio.run()``.

    Args:
        report_path: Path to Trivy JSON report
        ports: Bundle of all port dependencies and configuration.
        thread_id: Optional thread ID for checkpointing
        user_id: Optional user ID for authorization (Phase 5)
        project_id: Optional project ID for authorization context (Phase 5)

    Returns:
        Final pipeline state with all results
    """
    ports = ports or PipelinePorts()

    # Create initial state
    initial_state = create_initial_state(
        report_path=str(report_path),
        thread_id=thread_id or str(uuid.uuid4()),
        user_id=user_id,
        project_id=project_id,
        system_execution=system_execution,
    )

    builder = PipelineGraphBuilder(ports)

    # Configure execution
    config: RunnableConfig = {"configurable": {"thread_id": initial_state["thread_id"]}}

    logger.info(
        "pipeline_execution_started",
        report_path=str(report_path),
        thread_id=initial_state["thread_id"],
        user_id=user_id,
        project_id=project_id,
    )

    # Execute pipeline via ainvoke — required because some nodes are async.
    # When checkpointing is requested, use AsyncSqliteSaver (the sync
    # SqliteSaver does not support ainvoke).
    if ports.checkpoint_db_path is not None:
        db_path = _validate_path(
            Path(ports.checkpoint_db_path),
            allowed_extensions=ALLOWED_DB_EXTENSIONS,
        )
        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
            graph = builder.build().compile(with_checkpointer=False)
            # Attach async checkpointer to the compiled graph
            graph.checkpointer = checkpointer
            result = await graph.ainvoke(initial_state, config)
    else:
        graph = builder.build().compile(with_checkpointer=False)
        result = await graph.ainvoke(initial_state, config)

    logger.info(
        "pipeline_execution_complete",
        thread_id=initial_state["thread_id"],
        authorization_allowed=result.get("authorization_allowed"),
        vulnerability_count=len(result.get("vulnerabilities", [])),
        classification_count=len(result.get("classifications", {})),
        escalated_count=len(result.get("escalated_cves", [])),
        error_count=len(result.get("errors", [])),
        output_error_count=len(result.get("output_errors", [])),
    )

    return cast(PipelineState, result)


__all__ = [
    "ALLOWED_DB_EXTENSIONS",
    "ALLOWED_OUTPUT_EXTENSIONS",
    "PipelineGraphBuilder",
    "PipelinePorts",
    "create_pipeline_graph",
    "run_pipeline",
]
