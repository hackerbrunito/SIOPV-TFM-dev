# LangGraph — Context7 Cache

## Current Version: langgraph 0.2+ / langgraph-checkpoint 4.0.1

## Key API Patterns

### StateGraph
- `from langgraph.graph import StateGraph, START, END`
- `StateGraph(State)` where `State` is a TypedDict or Pydantic model
- `.add_node("name", function)` — node functions receive state, return partial state updates
- `.add_edge("from", "to")` — unconditional edges
- `.add_conditional_edges("from", router_fn, {"value": "node"})` — conditional routing
- `.compile(checkpointer=checkpointer)` — compile graph with persistence

### Interrupt (Human-in-the-Loop)
- `from langgraph.types import interrupt, Command`
- `value = interrupt({"question": "Approve?", "data": ...})` — pauses graph, returns value to caller
- Resume with `Command(resume={"action": "approve"})` — becomes return value of `interrupt()`
- Requires a checkpointer to persist state during interruption
- `interrupt()` accepts any JSON-serializable value

### Checkpointer
- `from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver` for async SQLite
- `from langgraph.checkpoint.sqlite import SqliteSaver` for sync SQLite
- Must implement: `.put()`, `.put_writes()`, `.get_tuple()`
- `async with AsyncSqliteSaver.from_conn_string("siopv_checkpoints.db") as saver:`
- Thread-based: `config = {"configurable": {"thread_id": "unique-id"}}`

### State Management
- Annotated reducers: `messages: Annotated[list, add_messages]`
- Partial state updates — nodes return only changed fields
- `state.get("field", default)` for safe access

### Streaming (v2 format, opt-in)
- `stream()` yields `StreamPart` dicts with `type`, `ns`, `data`, `interrupts`
- `invoke()` returns `GraphOutput` with `.value` and `.interrupts`

### Deprecated / Changed
- `NodeInterrupt` exception → use `interrupt()` function (simpler, more flexible)
- Thread callbacks → use streaming v2 format
- `MemorySaver` → use `SqliteSaver` / `AsyncSqliteSaver` for production
