# LangGraph — Context7 Cache (Pre-Wave Research)

> Queried: 2026-03-17 | Source: LangChain docs + web research

## Core API Patterns

### interrupt() Function (Python)
```python
from langgraph.types import interrupt, Command

def my_node(state: State) -> Command:
    result = interrupt({"question": "Approve?", "details": state["info"]})
    if result["approved"]:
        return Command(goto="proceed")
    return Command(goto="cancel")
```

### Command Resume Pattern
```python
from langgraph.types import Command

# Resume after interrupt
graph.invoke(Command(resume=value), config)
```

### Checkpoint Setup
```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

checkpointer = AsyncSqliteSaver.from_conn_string("siopv_checkpoints.db")
config = {"configurable": {"thread_id": "unique-id"}}
graph = builder.compile(checkpointer=checkpointer)
```

### StateGraph Configuration
```python
from langgraph.graph import StateGraph, START, END

builder = StateGraph(SiopvState)
builder.add_node("authorize", authorize_node)
builder.add_edge(START, "authorize")
builder.add_conditional_edges("classify", route_classification)
graph = builder.compile(checkpointer=checkpointer)
```

## Key Best Practices

1. **State:** Small, typed, validated. Use TypedDict or Pydantic.
2. **Reducers:** Use sparingly — only when merging parallel outputs.
3. **Edges:** Simple edges where possible; conditional edges only at real decision points.
4. **Cycles:** Always bounded — never infinite loops.
5. **thread_id:** Always send consistently; checkpointer must be in same namespace.
6. **interrupt() placement:** Dynamic — can be conditional. Node restarts from beginning when resumed.
7. **Production checkpointer:** Use Postgres or SQLite (not MemorySaver) for durability.

## Critical Constraint
> The node restarts from the beginning when resumed after interrupt(). Any code before interrupt() runs again.
