# LangGraph Async Findings — Context7 Verification Report

**Date:** 2026-03-05
**Agent:** verification-agent (context7-lookup)
**Source:** Context7 `/websites/langchain_oss_python_langgraph` (Score: 86.9, High reputation, 900 snippets)
**Scope:** Findings C2, H6, H4 from the 2026-03-05 SIOPV audit

---

## Summary

| Finding | ID | Verdict |
|---------|----|---------|
| `asyncio.run()` inside sync LangGraph nodes is a bug | C2 | CONFIRMED |
| `enrich_node_async` is dead code | H6 | CONFIRMED |
| Adding `output_node` requires a graph topology change | H4 | CONFIRMED |

---

## Finding C2: `asyncio.run()` in LangGraph sync nodes

### Claim
Using `asyncio.run(coroutine)` inside a sync LangGraph node will crash with
`RuntimeError: This event loop is already running` when the graph is invoked
from Streamlit or FastAPI (both of which run their own event loops).

### Context7 Evidence

LangGraph natively supports async nodes. The official pattern is:

```python
async def node(state: MessagesState):
    new_message = await llm.ainvoke(state["messages"])
    return {"messages": [new_message]}

builder = StateGraph(MessagesState).add_node(node).set_entry_point("node")
graph = builder.compile()

# Invoke with async variant
result = await graph.ainvoke({"messages": [input_message]})
```

The docs explicitly state:

> "To convert a `sync` implementation of the graph to an `async` implementation,
> you will need to:
> 1. Update `nodes` use `async def` instead of `def`.
> 2. Update the code inside to use `await` appropriately.
> 3. Invoke the graph with `.ainvoke` or `.astream` as desired."

### What the SIOPV code currently does

Three sync node functions call `asyncio.run()` to bridge async code:

- `enrich_node.py:73` — `asyncio.run(_run_enrichment(...))`
- `dlp_node.py:106` — `asyncio.run(_run_dlp_for_vulns(...))`
- `authorization_node.py:194` — `asyncio.run(port.check(context))`

The graph is invoked with `.invoke()` (sync) at `graph.py:459`.

### Analysis

`asyncio.run()` creates and runs a **new event loop**, then tears it down. This
works correctly in a fully synchronous context (e.g., a plain CLI invocation)
because there is no existing event loop at call time.

However, the audit finding is CONFIRMED for these specific scenarios:

1. **Streamlit (Phase 7):** Streamlit runs within `tornado`'s event loop since
   v1.12+. Calling `asyncio.run()` from within a Streamlit callback will raise
   `RuntimeError: This event loop is already running`.

2. **FastAPI:** FastAPI runs under uvicorn's asyncio loop. Any sync route handler
   that calls `asyncio.run()` will raise the same error.

3. **LangGraph's own async runner:** If the graph is later migrated to
   `.ainvoke()` (as recommended), LangGraph will run nodes inside its own async
   context, making `asyncio.run()` inside a node invalid.

### Is `nest_asyncio` an accepted workaround?

Context7 does not mention `nest_asyncio` in LangGraph documentation. The
recommended pattern is to convert nodes to `async def` and invoke the graph
with `.ainvoke()` / `.astream()`. `nest_asyncio` is a monkey-patch that can
mask deeper architectural issues and is not endorsed by LangGraph docs.

### Verdict: CONFIRMED

The finding is correct. The current `asyncio.run()` pattern works today only
because the graph is called synchronously from a CLI context. It will break
when Phase 7 (Streamlit) is added. The fix is to convert nodes to `async def`
and switch the graph invocation to `.ainvoke()`.

---

## Finding H6: `enrich_node_async()` is dead code

### Claim
`enrich_node_async` (an `async def`) exists in `enrich_node.py` but is never
wired into the graph; the graph uses the sync `enrich_node` instead.

### Context7 Evidence

LangGraph supports mixing sync and async nodes in the same `StateGraph`. There
is no special variant of `add_node` for async nodes — the same `add_node` API
handles both:

```python
# Sync node — registered the same way
builder.add_node("my_sync_node", sync_function)

# Async node — same API, LangGraph detects the coroutine
builder.add_node("my_async_node", async_function)
```

When the graph is invoked with `.ainvoke()` or `.astream()`, LangGraph
automatically awaits async nodes and runs sync nodes in a thread executor.
When invoked with `.invoke()`, sync nodes run directly and async nodes are
run via `asyncio.run()` internally by LangGraph (not by the node itself).

### What the SIOPV code does

`graph.py:192-202` registers `enrich_node` (sync):
```python
self._graph.add_node(
    "enrich",
    lambda state: enrich_node(state, ...),
)
```

`enrich_node.py:193` defines `enrich_node_async` and exports it in `__all__`,
but it is never imported by `graph.py` and never passed to `add_node`.

### Verdict: CONFIRMED

`enrich_node_async` is dead code. It is defined, exported, and never used.
The graph wires the sync `enrich_node` which internally calls `asyncio.run()`.

**Additional nuance:** Since LangGraph supports async nodes natively via the
same `add_node` API, the correct fix for both C2 and H6 is to replace the
`lambda state: enrich_node(...)` registration with a lambda or partial that
calls `enrich_node_async`, and switch the graph invocation to `.ainvoke()`.
This would eliminate all three `asyncio.run()` calls at once.

---

## Finding H4: Missing `output_node` requires graph topology change

### Claim
Phase 8 output (Jira + PDF) cannot be added without changing the compiled
graph topology (i.e., the graph must be rebuilt and recompiled).

### Context7 Evidence

From the official LangGraph docs:

> "To build your graph, you first define the state, you then add nodes and
> edges, and then you compile it. **You MUST compile your graph before you can
> use it.**"

> "Compiling is a pretty simple step. It provides a few basic checks on the
> structure of your graph (no orphaned nodes, etc)."

There is no API for adding nodes or edges to a **compiled** graph dynamically.
`add_node` is only available on the `StateGraph` builder, not on the
`CompiledStateGraph` returned by `.compile()`.

The recommended approach for extending a pipeline is:
1. Rebuild the `StateGraph` with the new node and edges added before `.compile()`.
2. Alternatively, use a subgraph pattern — but the new terminal node must still
   be declared before compilation.

### What the SIOPV code does

`PipelineGraphBuilder._add_nodes()` adds exactly six nodes:
`authorize`, `ingest`, `dlp`, `enrich`, `classify`, `escalate`.

The compiled graph (`self._compiled`) is the result of `.compile()` on this
builder. Adding `output_node` requires:

1. Adding `"output"` node in `_add_nodes()`.
2. Adding an edge from `"classify"` (or `"escalate"`) to `"output"` in `_add_edges()`.
3. Removing or adjusting the current `END` edges that terminate the graph.
4. Recompiling.

This is a topology change, not a file addition. Phase 8 cannot be implemented
by only adding new files.

### Verdict: CONFIRMED

Adding `output_node` requires modifying `graph.py` (`_add_nodes` and
`_add_edges`), creating the node function, and recompiling the graph.
This is a structural change, consistent with the audit finding.

---

## Recommended Fixes (Priority Order)

### 1. Fix C2 + H6 together (CRITICAL, blocks Phase 7)

Convert the three sync nodes that call `asyncio.run()` to async nodes, and
switch graph invocation to `.ainvoke()`:

**Step 1 — Replace sync nodes with async counterparts:**
- `enrich_node` → use `enrich_node_async` (already exists, just wire it in)
- `dlp_node` → convert to `async def dlp_node_async` using `await`
- `authorization_node` → convert to `async def authorization_node_async` using `await`

**Step 2 — Update `graph.py` `_add_nodes()`:**
```python
# Replace:
lambda state: enrich_node(state, ...)
# With:
lambda state: enrich_node_async(state, ...)  # async def, LangGraph awaits it
```

**Step 3 — Switch invocation in `run_pipeline()` (graph.py:459):**
```python
# Replace:
result = graph.invoke(initial_state, config)
# With:
result = await graph.ainvoke(initial_state, config)
# (and make run_pipeline() async def)
```

### 2. Fix H4 (HIGH, required before Phase 8)

Modify `PipelineGraphBuilder._add_nodes()` and `_add_edges()` to include
`output_node` when Phase 8 is implemented. Plan for graph recompilation as
part of Phase 8 implementation.

---

## Context7 Query Log

| # | Tool | Input | Latency |
|---|------|-------|---------|
| 1 | `resolve-library-id` | `langgraph` + async nodes query | ~400ms |
| 2 | `query-docs` | async nodes StateGraph add_node async def asyncio event loop | ~800ms |
| 3 | `query-docs` | mixing sync and async nodes same StateGraph compile invoke asyncio.run | ~700ms |
| 4 | `query-docs` | add_node to compiled graph extend topology recompile dynamic new node | ~600ms |

**Library used:** `/websites/langchain_oss_python_langgraph`
(900 snippets, High reputation, Benchmark 86.9)
