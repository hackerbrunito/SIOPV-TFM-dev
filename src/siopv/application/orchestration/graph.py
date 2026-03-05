"""LangGraph pipeline builder for SIOPV orchestration.

Builds and compiles the StateGraph with nodes, edges, and checkpointing.
Based on specification section 3.4.
"""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, cast

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
    route_after_authorization,
)
from siopv.application.orchestration.state import PipelineState, create_initial_state

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
    from siopv.application.ports.ml_classifier import MLClassifierPort

logger = structlog.get_logger(__name__)

# Default checkpoint database path
DEFAULT_CHECKPOINT_DB = "siopv_checkpoints.db"

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


class PipelineGraphBuilder:
    """Builder for the SIOPV LangGraph pipeline.

    Constructs a StateGraph with the following nodes:
    - authorize: Authorization gatekeeper (Phase 5 - Zero Trust)
    - ingest: Parse Trivy report (Phase 1)
    - dlp: DLP guardrail — sanitize descriptions (Phase 6)
    - enrich: Context enrichment with CRAG (Phase 2)
    - classify: ML risk classification (Phase 3)
    - escalate: Human review escalation (Phase 4)

    Flow: START -> authorize -> (if allowed) -> ingest -> dlp -> enrich -> classify -> ...

    Conditional routing is based on:
    - Authorization check (Phase 5): If denied -> end with 403
    - Uncertainty Trigger (Phase 4): If ML/LLM discrepancy high -> escalate
    """

    def __init__(
        self,
        *,
        checkpoint_db_path: str | Path | None = None,
        authorization_port: AuthorizationPort | None = None,
        dlp_port: DLPPort | None = None,
        nvd_client: NVDClientPort | None = None,
        epss_client: EPSSClientPort | None = None,
        github_client: GitHubAdvisoryClientPort | None = None,
        osint_client: OSINTSearchClientPort | None = None,
        vector_store: VectorStorePort | None = None,
        classifier: MLClassifierPort | None = None,
    ) -> None:
        """Initialize the pipeline builder.

        Args:
            checkpoint_db_path: Path to SQLite checkpoint database
            authorization_port: Authorization port for Phase 5 gatekeeper
            dlp_port: DLP port for Phase 6 privacy guardrail
            nvd_client: NVD API client for enrichment
            epss_client: EPSS API client for enrichment
            github_client: GitHub Advisory client for enrichment
            osint_client: OSINT search client for enrichment
            vector_store: Vector store for enrichment cache
            classifier: ML classifier for risk classification
        """
        self._checkpoint_db_path = checkpoint_db_path or DEFAULT_CHECKPOINT_DB
        self._authorization_port = authorization_port
        self._dlp_port = dlp_port
        self._nvd_client = nvd_client
        self._epss_client = epss_client
        self._github_client = github_client
        self._osint_client = osint_client
        self._vector_store = vector_store
        self._classifier = classifier

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
        """Add all pipeline nodes to the graph."""

        if self._graph is None:
            msg = "Graph not initialized. Call build() first."
            raise RuntimeError(msg)

        # Authorize node - Phase 5 gatekeeper (Zero Trust)
        # async wrapper needed because authorization_node is async and
        # Python does not support async lambda
        async def _authorize_node(state: PipelineState) -> dict[str, object]:
            return await authorization_node(
                state,
                authorization_port=self._authorization_port,
            )

        self._graph.add_node("authorize", _authorize_node)

        # Ingest node - wraps Phase 1 use case
        self._graph.add_node("ingest", ingest_node)

        # DLP node - Phase 6 guardrail (sanitize vulnerability descriptions)
        async def _dlp_node(state: PipelineState) -> dict[str, object]:
            return await dlp_node(state, dlp_port=self._dlp_port)

        self._graph.add_node("dlp", _dlp_node)

        # Enrich node - wraps Phase 2 use case with injected dependencies
        async def _enrich_node(state: PipelineState) -> dict[str, object]:
            return await enrich_node(
                state,
                nvd_client=self._nvd_client,
                epss_client=self._epss_client,
                github_client=self._github_client,
                osint_client=self._osint_client,
                vector_store=self._vector_store,
            )

        self._graph.add_node("enrich", _enrich_node)

        # Classify node - wraps Phase 3 use case
        self._graph.add_node(
            "classify",
            lambda state: classify_node(state, classifier=self._classifier),
        )

        # Escalate node - handles uncertainty escalation
        self._graph.add_node("escalate", escalate_node)

        logger.debug(
            "pipeline_nodes_added",
            nodes=["authorize", "ingest", "dlp", "enrich", "classify", "escalate"],
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
        self._graph.add_conditional_edges(
            "classify",
            route_after_classify,
            {
                "escalate": "escalate",
                "continue": END,
                "end": END,
            },
        )

        # After escalate, go to end
        self._graph.add_conditional_edges(
            "escalate",
            route_after_escalate,
            {
                "end": END,
            },
        )

        logger.debug("pipeline_edges_added")

    def _create_checkpointer(self) -> SqliteSaver:
        """Create and initialize SQLite checkpointer.

        Returns:
            SqliteSaver instance for LangGraph checkpointing

        Raises:
            ValueError: If checkpoint database path validation fails
        """

        db_path = _validate_path(
            Path(self._checkpoint_db_path),
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
            return self.compile()
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
    *,
    checkpoint_db_path: str | Path | None = None,
    authorization_port: AuthorizationPort | None = None,
    dlp_port: DLPPort | None = None,
    nvd_client: NVDClientPort | None = None,
    epss_client: EPSSClientPort | None = None,
    github_client: GitHubAdvisoryClientPort | None = None,
    osint_client: OSINTSearchClientPort | None = None,
    vector_store: VectorStorePort | None = None,
    classifier: MLClassifierPort | None = None,
    with_checkpointer: bool = True,
) -> CompiledStateGraph[PipelineState]:
    """Factory function to create and compile the pipeline graph.

    Args:
        checkpoint_db_path: Path to SQLite checkpoint database
        authorization_port: Authorization port for Phase 5 gatekeeper
        dlp_port: DLP port for Phase 6 privacy guardrail
        nvd_client: NVD API client for enrichment
        epss_client: EPSS API client for enrichment
        github_client: GitHub Advisory client for enrichment
        osint_client: OSINT search client for enrichment
        vector_store: Vector store for enrichment cache
        classifier: ML classifier for risk classification
        with_checkpointer: Whether to enable checkpointing

    Returns:
        Compiled StateGraph ready for invocation
    """
    builder = PipelineGraphBuilder(
        checkpoint_db_path=checkpoint_db_path,
        authorization_port=authorization_port,
        dlp_port=dlp_port,
        nvd_client=nvd_client,
        epss_client=epss_client,
        github_client=github_client,
        osint_client=osint_client,
        vector_store=vector_store,
        classifier=classifier,
    )

    return builder.build().compile(with_checkpointer=with_checkpointer)


async def run_pipeline(
    report_path: str | Path,
    *,
    thread_id: str | None = None,
    user_id: str | None = None,
    project_id: str | None = None,
    checkpoint_db_path: str | Path | None = None,
    authorization_port: AuthorizationPort | None = None,
    dlp_port: DLPPort | None = None,
    nvd_client: NVDClientPort | None = None,
    epss_client: EPSSClientPort | None = None,
    github_client: GitHubAdvisoryClientPort | None = None,
    osint_client: OSINTSearchClientPort | None = None,
    vector_store: VectorStorePort | None = None,
    classifier: MLClassifierPort | None = None,
) -> PipelineState:
    """Run the full pipeline on a Trivy report (async).

    Uses ``ainvoke()`` because some graph nodes are async
    (authorization_node, dlp_node, enrich_node).
    Callers in sync contexts (e.g. CLI) should wrap with ``asyncio.run()``.

    Args:
        report_path: Path to Trivy JSON report
        thread_id: Optional thread ID for checkpointing
        user_id: Optional user ID for authorization (Phase 5)
        project_id: Optional project ID for authorization context (Phase 5)
        checkpoint_db_path: Path to checkpoint database
        authorization_port: Optional authorization port for Phase 5 gatekeeper
        dlp_port: Optional DLP port for Phase 6 privacy guardrail
        nvd_client: Optional NVD API client for enrichment
        epss_client: Optional EPSS API client for enrichment
        github_client: Optional GitHub Advisory client for enrichment
        osint_client: Optional OSINT search client for enrichment
        vector_store: Optional vector store for enrichment cache
        classifier: Optional ML classifier

    Returns:
        Final pipeline state with all results
    """

    # Create initial state
    initial_state = create_initial_state(
        report_path=str(report_path),
        thread_id=thread_id or str(uuid.uuid4()),
        user_id=user_id,
        project_id=project_id,
    )

    # Build graph without checkpointer first (checkpointer added below)
    builder = PipelineGraphBuilder(
        checkpoint_db_path=checkpoint_db_path,
        authorization_port=authorization_port,
        dlp_port=dlp_port,
        nvd_client=nvd_client,
        epss_client=epss_client,
        github_client=github_client,
        osint_client=osint_client,
        vector_store=vector_store,
        classifier=classifier,
    )

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
    if checkpoint_db_path is not None:
        db_path = _validate_path(
            Path(checkpoint_db_path),
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
    )

    return cast(PipelineState, result)


__all__ = [
    "ALLOWED_DB_EXTENSIONS",
    "ALLOWED_OUTPUT_EXTENSIONS",
    "DEFAULT_CHECKPOINT_DB",
    "PipelineGraphBuilder",
    "create_pipeline_graph",
    "run_pipeline",
]
