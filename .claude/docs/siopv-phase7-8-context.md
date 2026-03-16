# SIOPV Phase 7 & 8: Verified Library Patterns

**Source:** Stage 3 research (2026-03-11) — all facts verified against official docs.
**Mandatory:** code-implementer MUST read this before writing any Phase 7 or Phase 8 code.

---

## Streamlit (Phase 7)

### Auto-refresh fragments
```python
@st.fragment(run_every="15s")   # NOT sleep+rerun
def live_queue_panel() -> None:
    data = get_queue_state()
    st.dataframe(data)
```

### Async bridge (REQUIRED — Streamlit runs in sync thread)
```python
from concurrent.futures import ThreadPoolExecutor
import asyncio

_executor = ThreadPoolExecutor(max_workers=4)

def run_async(coro):
    """Call from Streamlit sync context to execute async coroutine."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
```

### Cached resources
```python
@st.cache_resource
def get_graph() -> CompiledStateGraph:
    return build_siopv_graph()
```

### LIME memory leak prevention
```python
fig = explainer.as_pyplot_figure()
st.pyplot(fig)
plt.close(fig)   # ALWAYS — prevents memory leak in long sessions
```

### Port configuration
```bash
export STREAMLIT_SERVER_PORT=8501  # via env var, not CLI arg
```

---

## LangGraph (Phase 7 — human-in-the-loop)

### interrupt() requires checkpointer at compile time
```python
# CORRECT — checkpointer must be passed at compile, not at invoke
from langgraph.checkpoint.sqlite import SqliteSaver

memory = SqliteSaver.from_conn_string("siopv_checkpoints.db")
graph = builder.compile(
    checkpointer=memory,
    interrupt_before=["escalate"],  # Phase 7 escalation node
)
```

### Threading: LangGraph graph is NOT thread-safe
- Never share a compiled graph across Streamlit sessions
- Use `@st.cache_resource` with one graph per session or global singleton with locks
- `graph.ainvoke()` must be called from async context — use async bridge above

---

## Jira v3 (Phase 8)

### ADF format — plain strings are REJECTED
```python
# WRONG — plain string silently fails or raises 400
description = "This is a vulnerability report"

# CORRECT — Atlassian Document Format
description = {
    "version": 1,
    "type": "doc",
    "content": [
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "This is a vulnerability report"}]
        }
    ]
}
```

### Use httpx.AsyncClient — sync libs block event loop
```python
async def create_jira_issue(payload: dict) -> str:
    async with httpx.AsyncClient(auth=(user, token), timeout=30.0) as client:
        resp = await client.post(f"{jira_url}/rest/api/3/issue", json=payload)
        resp.raise_for_status()
        return resp.json()["key"]
```

---

## fpdf2 (Phase 8)

### `fname` parameter required since v2.7 (BREAKING CHANGE)
```python
# WRONG — breaks on fpdf2 >= 2.7
pdf.add_font("DejaVu", "", "DejaVuSans.ttf")

# CORRECT
pdf.add_font("DejaVu", "", fname="DejaVuSans.ttf")
```

### PDF generation order (must be sequential — no async)
```python
pdf = FPDF()
pdf.add_page()          # 1. Add page first
pdf.set_font("Helvetica", size=12)   # 2. Set font before any text
pdf.cell(200, 10, text="Report Title")  # 3. Use 'text=' kwarg (not positional since v2.7)
pdf.output("report.pdf")
```

---

## Redis (Phase 7 — queue / state persistence)

### Use redis.asyncio — aioredis is deprecated (merged into redis-py ≥4.2)
```python
import redis.asyncio as aioredis   # NOT: import aioredis

async def get_client() -> aioredis.Redis:
    return aioredis.Redis(host="localhost", port=6379, decode_responses=True)

# ALWAYS close client when done
async def cleanup(client: aioredis.Redis) -> None:
    await client.aclose()   # NOT: client.close()
```

### Key convention for SIOPV
```
siopv:queue:{cve_id}          # pending escalation items
siopv:decision:{cve_id}       # analyst decision result
siopv:session:{session_id}    # LangGraph thread state cache
```

---

## OpenTelemetry (existing — Phase 7 OTel additions)

### HTTPXClientInstrumentor ordering constraint
```python
# CORRECT — instrument BEFORE creating any httpx clients
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
HTTPXClientInstrumentor().instrument()

# THEN create clients
client = httpx.AsyncClient()
```
**Note:** `HTTPXClientInstrumentor` does NOT cover module-level `httpx.get()` calls.
Only covers `httpx.AsyncClient` / `httpx.Client` instances created AFTER instrumentation.

---

## LangSmith (Phase 7 — tracing)

### Environment variables (set in .env)
```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<your-key>
LANGCHAIN_PROJECT=siopv-phase7
```

### No code changes needed — LangGraph auto-traces when env vars set
- All `graph.invoke()` / `graph.ainvoke()` calls traced automatically
- Phase 7 escalation decisions visible in LangSmith dashboard

---

## Phase 8 — Exact Graph Topology Changes (3 changes only)

File: `src/siopv/application/orchestration/graph.py`
Method: `_add_edges()`

```python
# Change 1: Add conditional edge from classify to output/escalate
self._graph.add_conditional_edges(
    "classify",
    route_to_output,    # new routing function
    {"output": "output", "escalate": "escalate"},
)

# Change 2: Add output node edge to END
self._graph.add_edge("output", END)

# Change 3: Add escalate → output edge (after human approval)
self._graph.add_edge("escalate", "output")
```

**Zero node logic changes** — only topology (edge) changes in Phase 8.
