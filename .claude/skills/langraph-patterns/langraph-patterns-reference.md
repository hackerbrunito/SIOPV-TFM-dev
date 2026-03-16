# LangGraph Patterns — Full Reference

Complete code examples for LangGraph 0.2+ in SIOPV.

---

## State Graph Basico

```python
from dataclasses import dataclass, field
from typing import Literal

from langgraph.graph import END, START, StateGraph


@dataclass
class PipelineState:
    """State object that flows through the graph."""

    input_data: str
    processed: bool = False
    results: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    current_step: str = "start"


def create_pipeline() -> StateGraph:
    """Create a simple processing pipeline."""

    workflow = StateGraph(PipelineState)

    # Add nodes
    workflow.add_node("process", process_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("output", output_node)

    # Entry point
    workflow.add_edge(START, "process")

    # Add edges
    workflow.add_edge("process", "validate")
    workflow.add_conditional_edges(
        "validate",
        should_continue,
        {
            "continue": "output",
            "retry": "process",
            "end": END,
        }
    )
    workflow.add_edge("output", END)

    return workflow.compile()
```

---

## Node Functions

```python
async def process_node(state: PipelineState) -> PipelineState:
    """Process input data."""
    try:
        # Processing logic here
        state.results.append(f"Processed: {state.input_data}")
        state.processed = True
        state.current_step = "process"
    except Exception as e:
        state.errors.append(f"Process error: {e}")
    return state


async def validate_node(state: PipelineState) -> PipelineState:
    """Validate processed results."""
    state.current_step = "validate"
    # Validation logic
    return state


def should_continue(state: PipelineState) -> Literal["continue", "retry", "end"]:
    """Conditional edge function."""
    if state.errors:
        return "end"
    if not state.processed:
        return "retry"
    return "continue"
```

---

## Parallel Execution

```python
from langgraph.graph import END, START, StateGraph

def create_parallel_pipeline() -> StateGraph:
    """Pipeline with parallel branches."""

    workflow = StateGraph(PipelineState)

    # Parallel nodes (executed concurrently)
    workflow.add_node("fetch_nvd", fetch_nvd_node)
    workflow.add_node("fetch_github", fetch_github_node)
    workflow.add_node("fetch_epss", fetch_epss_node)

    # Merge node
    workflow.add_node("merge", merge_results_node)

    # Fan-out from START to all parallel nodes
    # LangGraph executes nodes concurrently when they share the same source
    workflow.add_edge(START, "fetch_nvd")
    workflow.add_edge(START, "fetch_github")
    workflow.add_edge(START, "fetch_epss")

    # All parallel nodes lead to merge
    workflow.add_edge("fetch_nvd", "merge")
    workflow.add_edge("fetch_github", "merge")
    workflow.add_edge("fetch_epss", "merge")

    workflow.add_edge("merge", END)

    return workflow.compile()
```

---

## Checkpointing (Persistence)

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver

# Development: In-memory checkpointer
memory_saver = InMemorySaver()

# Production: Postgres checkpointer
# IMPORTANT: Never hardcode credentials — use environment variables
postgres_saver = PostgresSaver.from_conn_string(
    settings.checkpoint_db_uri  # e.g. "${CHECKPOINT_DB_URI}" from .env
)

# Compile with checkpointer
graph = workflow.compile(checkpointer=memory_saver)

# Execute with thread_id for persistence
config = {"configurable": {"thread_id": "session-123"}}
result = await graph.ainvoke(initial_state, config)

# Resume from checkpoint
resumed = await graph.ainvoke(None, config)  # Continues from last state
```

---

## Human-in-the-Loop

```python
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode


@dataclass
class HumanLoopState:
    vulnerability: dict
    classification: str | None = None
    human_approved: bool = False
    needs_review: bool = False


async def classify_node(state: HumanLoopState) -> HumanLoopState:
    """Classify vulnerability risk."""
    # ML classification
    state.classification = await model.predict(state.vulnerability)

    # Flag for human review if uncertain
    confidence = await model.get_confidence(state.vulnerability)
    if confidence < 0.8:
        state.needs_review = True

    return state


async def human_review_node(state: HumanLoopState) -> HumanLoopState:
    """Wait for human approval."""
    # This node will pause execution until human input
    # In Streamlit: st.button("Approve Classification")
    return state


def needs_human_review(state: HumanLoopState) -> str:
    """Check if human review is needed."""
    if state.needs_review and not state.human_approved:
        return "human_review"
    return "continue"
```

---

## Error Handling

```python
from langgraph.graph import END, START, StateGraph


async def safe_node(state: PipelineState) -> PipelineState:
    """Node with error handling."""
    try:
        result = await risky_operation()
        state.results.append(result)
    except TimeoutError:
        state.errors.append("Operation timed out")
        # Don't re-raise - let graph continue
    except Exception as e:
        state.errors.append(f"Unexpected error: {e}")
        # Log for debugging
        logger.exception("Node failed", error=str(e))

    return state


def create_resilient_pipeline() -> StateGraph:
    """Pipeline that handles errors gracefully."""

    workflow = StateGraph(PipelineState)

    workflow.add_node("risky_step", safe_node)
    workflow.add_node("fallback", fallback_node)
    workflow.add_node("final", final_node)

    workflow.add_edge(START, "risky_step")

    workflow.add_conditional_edges(
        "risky_step",
        lambda s: "fallback" if s.errors else "final",
        {
            "fallback": "fallback",
            "final": "final",
        }
    )

    workflow.add_edge("fallback", "final")
    workflow.add_edge("final", END)

    return workflow.compile()
```

---

## Streaming Results

```python
# Stream node outputs as they complete
async for event in graph.astream(initial_state):
    print(f"Node completed: {event}")

# Stream with specific output
async for chunk in graph.astream(initial_state, stream_mode="values"):
    print(f"State update: {chunk}")
```

---

## Testing Graphs

```python
import pytest
from langgraph.graph import StateGraph


@pytest.fixture
def pipeline():
    return create_pipeline()


@pytest.mark.asyncio
async def test_happy_path(pipeline):
    state = PipelineState(input_data="test")
    result = await pipeline.ainvoke(state)

    assert result.processed is True
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_error_handling(pipeline):
    state = PipelineState(input_data="invalid")
    result = await pipeline.ainvoke(state)

    assert len(result.errors) > 0
```
