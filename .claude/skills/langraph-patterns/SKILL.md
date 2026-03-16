---
name: langraph-patterns
description: "LangGraph 0.2+ patterns: state graphs, nodes, checkpointing, HITL. USE WHEN code imports langgraph or user asks about LangGraph graphs or state machines."
user-invocable: false
---

# LangGraph Patterns

LangGraph 0.2+ implementation patterns for SIOPV pipeline orchestration.
Covers state graphs, node functions, parallel execution, checkpointing, human-in-the-loop,
error handling, streaming, and testing.

## When to use

Apply these patterns when implementing or modifying LangGraph orchestration in SIOPV
(Phase 4 — graph.py, nodes, edges, state) or Phase 7 (HITL with Streamlit + interrupt).

## Quick checklist

1. Define state as `@dataclass` with typed fields and defaults
2. Create `StateGraph(YourState)` — add nodes, edges, conditional edges
3. Node functions: `async def node(state) -> state` — always return state
4. Conditional edges: pure function returning `Literal[...]` string
5. Compile with checkpointer: `workflow.compile(checkpointer=saver)`
6. Execute with `thread_id`: `await graph.ainvoke(state, {"configurable": {"thread_id": "..."}})`
7. For HITL: use `interrupt()` in node, resume with `graph.ainvoke(None, config)`
8. Test with `pytest.mark.asyncio` + `InMemorySaver`

## Key patterns (quick reference)

- **State**: `@dataclass` with `field(default_factory=list)` for collections
- **Graph**: `StateGraph(State)` → `add_node()` → `add_edge()` → `compile()`
- **Parallel**: Multiple edges from same source node (LangGraph runs concurrently)
- **Checkpoint**: `InMemorySaver()` (dev) or `PostgresSaver` (prod) — use env vars for DB URI
- **HITL**: `interrupt()` pauses execution; resume with `ainvoke(None, config)`
- **Streaming**: `async for event in graph.astream(state, stream_mode="values")`
- **Error handling**: Try/except in nodes, append to `state.errors`, don't re-raise

## Full reference

For complete code examples and detailed patterns, see:
@./langraph-patterns-reference.md
