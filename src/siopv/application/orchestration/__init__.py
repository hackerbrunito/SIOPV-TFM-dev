"""LangGraph orchestration for SIOPV pipeline.

Phase 4 implementation: Orchestration and Uncertainty Management.
Provides the StateGraph-based workflow with conditional routing
based on ML/LLM confidence discrepancy.

Based on specification section 3.4.
"""

from __future__ import annotations

from siopv.application.orchestration.edges import (
    RouteType,
    route_after_classify,
    route_after_escalate,
    should_escalate_route,
)
from siopv.application.orchestration.graph import (
    PipelineGraphBuilder,
    create_pipeline_graph,
    run_pipeline,
)
from siopv.application.orchestration.nodes import (
    classify_node,
    enrich_node,
    escalate_node,
    ingest_node,
)
from siopv.application.orchestration.state import (
    DiscrepancyHistory,
    DiscrepancyResult,
    PipelineState,
    ThresholdConfig,
    create_initial_state,
)
from siopv.application.orchestration.utils import (
    calculate_escalation_candidates,
    check_any_escalation_needed,
    should_escalate_cve,
)

__all__ = [
    "DiscrepancyHistory",
    "DiscrepancyResult",
    "PipelineGraphBuilder",
    "PipelineState",
    "RouteType",
    "ThresholdConfig",
    "calculate_escalation_candidates",
    "check_any_escalation_needed",
    "classify_node",
    "create_initial_state",
    "create_pipeline_graph",
    "enrich_node",
    "escalate_node",
    "ingest_node",
    "route_after_classify",
    "route_after_escalate",
    "run_pipeline",
    "should_escalate_cve",
    "should_escalate_route",
]
