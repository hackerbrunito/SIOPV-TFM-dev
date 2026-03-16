## Batch C of 4 — LangGraph Library

**Files analyzed:**
- `/Users/bruno/siopv/src/siopv/application/orchestration/graph.py`
- `/Users/bruno/siopv/src/siopv/application/orchestration/nodes/dlp_node.py`
- `/Users/bruno/siopv/src/siopv/application/orchestration/state.py`

**Library verified:** langgraph
**Context7 source:** `/websites/langchain_oss_python_langgraph` (Benchmark Score: 86.9, Source Reputation: High)
**Timestamp:** 2026-02-20-164911

---

## Verification Methodology

The following APIs were used in the code and verified against Context7 documentation:

1. `from langgraph.graph import END, START, StateGraph` — imports
2. `from langgraph.graph.state import CompiledStateGraph` — type import
3. `from langgraph.checkpoint.sqlite import SqliteSaver` — checkpointer import
4. `StateGraph(PipelineState)` — constructor
5. `graph.add_node(name, fn)` — node registration
6. `graph.add_edge(src, dst)` — edge registration
7. `graph.add_conditional_edges(src, router_fn, mapping)` — conditional routing
8. `graph.compile(checkpointer=...)` — graph compilation
9. `SqliteSaver(conn)` — checkpointer constructor (with `sqlite3.connect(...)`)
10. `compiled.get_graph().draw_mermaid()` — visualization
11. `compiled.invoke(state, config)` — execution
12. `TypedDict` with `Annotated[list[str], operator.add]` — append-only reducer
13. `from langchain_core.runnables import RunnableConfig` — config type

---

## Verified API vs Code Comparison

### Import paths
- **Code (`graph.py`, lines 16–18):**
  ```python
  from langchain_core.runnables import RunnableConfig
  from langgraph.checkpoint.sqlite import SqliteSaver
  from langgraph.graph import END, START, StateGraph
  from langgraph.graph.state import CompiledStateGraph
  ```
- **Verified:** Context7 confirms `from langgraph.graph import StateGraph, START, END` ✅
- **Verified:** `from langgraph.checkpoint.sqlite import SqliteSaver` ✅ (shown in multiple Context7 snippets)
- **Verified:** `from langchain_core.runnables import RunnableConfig` ✅ (used in verified snippets)
- `CompiledStateGraph` from `langgraph.graph.state` — used only as a type annotation; the return type of `graph.compile()`. Context7 docs show `graph.compile()` returns the compiled graph object. This import is for type hints only and is valid. ✅

### `StateGraph(PipelineState)` constructor
- **Verified signature:** `StateGraph(State)` where State is a TypedDict
- **Code (`graph.py`, line 155):** `self._graph = StateGraph(PipelineState)` ✅

### `graph.add_node(name, fn)` — two-argument form
- **Verified:** Context7 shows both `workflow.add_node(node_a)` (one-arg, using function name) and `workflow.add_node("read_email", read_email)` (two-arg, explicit name + callable) ✅
- **Code (`graph.py`, lines 174–211):**
  ```python
  self._graph.add_node("authorize", lambda state: ...)
  self._graph.add_node("ingest", ingest_node)
  self._graph.add_node("dlp", lambda state: ...)
  ```
  All usages pass `(name_string, callable)` — valid ✅

### `graph.add_edge(src, dst)`
- **Verified:** `workflow.add_edge(START, "node_a")` and `workflow.add_edge("node_a", "node_b")` ✅
- **Code (`graph.py`, lines 226, 239–241):**
  ```python
  self._graph.add_edge(START, "authorize")
  self._graph.add_edge("ingest", "dlp")
  self._graph.add_edge("dlp", "enrich")
  self._graph.add_edge("enrich", "classify")
  ```
  All valid ✅

### `graph.add_conditional_edges(src, router_fn, mapping)`
- **Verified:** `builder.add_conditional_edges("generate_query", should_continue)` — two-arg form confirmed. Mapping dict form also valid per docs.
- **Code (`graph.py`, lines 229–261):**
  ```python
  self._graph.add_conditional_edges(
      "authorize",
      route_after_authorization,
      {"ingest": "ingest", "end": END},
  )
  self._graph.add_conditional_edges(
      "classify",
      route_after_classify,
      {"escalate": "escalate", "continue": END, "end": END},
  )
  self._graph.add_conditional_edges(
      "escalate",
      route_after_escalate,
      {"end": END},
  )
  ```
  Three-argument form `(source, router_fn, path_map)` is the standard documented pattern ✅

### `graph.compile(checkpointer=...)`
- **Verified:** `graph = workflow.compile(checkpointer=checkpointer)` ✅
- **Code (`graph.py`, line 302):** `self._graph.compile(checkpointer=checkpointer)` ✅
- Also: `self._graph.compile(checkpointer=None)` (when `with_checkpointer=False`) — passing `None` as checkpointer is equivalent to no checkpointer, valid. ✅

### `SqliteSaver(conn)` constructor
- **Verified:** `SqliteSaver(sqlite3.connect("checkpoint.db"))` — positional `sqlite3.Connection` argument ✅
- **Code (`graph.py`, lines 279–281):**
  ```python
  conn = sqlite3.connect(str(db_path), check_same_thread=False)
  return SqliteSaver(conn)
  ```
  Valid — uses `sqlite3.connect(..., check_same_thread=False)` which is a standard SQLite flag for multi-threaded use. ✅

### `compiled.get_graph().draw_mermaid()` — visualization
- **Verified:** Context7 shows `agent.get_graph(xray=True).draw_mermaid_png()` — this confirms `get_graph()` exists and returns a drawable graph object.
- **Code (`graph.py`, line 329):** `compiled.get_graph().draw_mermaid()` — calls `draw_mermaid()` (without PNG), which returns a string (Mermaid diagram format). This is the text-based variant of the visualization API. ✅

### `compiled.invoke(state, config)` — execution
- **Verified:** `graph.invoke({"foo": "", "bar":[]}, config)` ✅
- **Code (`graph.py`, line 459):** `result = graph.invoke(initial_state, config)` ✅
- Config format `{"configurable": {"thread_id": "1"}}` is verified ✅

### `TypedDict` with `Annotated[list[str], operator.add]` — append reducer
- **Verified:** Context7 confirms `Annotated[list[str], add]` (where `add = operator.add`) as the standard LangGraph pattern for append-only list fields.
- **Code (`state.py`, lines 64, 67):**
  ```python
  escalated_cves: Annotated[list[str], operator.add]
  errors: Annotated[list[str], operator.add]
  ```
  ✅

### `PipelineState(TypedDict, total=False)` — optional fields
- **Verified:** TypedDict is the standard LangGraph state schema type (explicitly documented: "LangGraph requires TypedDict"). `total=False` makes all fields optional, which is valid Python and common in LangGraph state definitions. ✅

### `asyncio.run(dlp_port.sanitize(ctx))` in `dlp_node.py`
- **Code (`dlp_node.py`, line 78):** `result = asyncio.run(dlp_port.sanitize(ctx))`
- This is pure Python stdlib (`asyncio.run`), not a LangGraph API. It is used to run the async `sanitize` coroutine from a synchronous node function. This is technically valid but carries a risk: `asyncio.run()` creates a new event loop, which may fail if called from within an already-running event loop. LangGraph nodes can run in async contexts in some configurations. However, this is a design consideration (not a hallucination of a library API).
- **Assessment:** Not a hallucination — `asyncio.run()` is valid stdlib usage. ✅

---

## Findings

No hallucinations detected. All LangGraph API calls match the verified documentation from Context7.

**One design note (not a hallucination):** The use of `asyncio.run()` inside a synchronous LangGraph node (`dlp_node.py`, line 78) is valid stdlib usage, but may raise `RuntimeError: This event loop is already running` if LangGraph executes nodes asynchronously in some configurations. This is an architectural concern, not an incorrect API call.

---

## Summary

- Total hallucinations: 0
- HIGH: 0
- MEDIUM: 0
- LOW: 0
- Threshold status: **PASS** (0 hallucinations found)
