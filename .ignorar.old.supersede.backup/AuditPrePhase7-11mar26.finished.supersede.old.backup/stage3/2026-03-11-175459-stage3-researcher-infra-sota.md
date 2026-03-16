# STAGE-3 Researcher Infra — State-of-the-Art Report
Generated: 2026-03-11-175459

---

## 1. LangGraph 0.2+ Verified Patterns

### 1.1 interrupt() / resume — Current API

```python
from langgraph.types import interrupt, Command

# Inside a node: pause and surface payload to caller
def hitl_node(state: SIOPVState) -> Command:
    decision = interrupt({
        "question": "Approve this vulnerability report?",
        "details": state["classification_result"],
    })
    # After Command(resume=...) is invoked, `decision` = the resume value
    return Command(goto="output_node" if decision else "escalate")
```

Resume pattern (Streamlit or API layer calls this):
```python
from langgraph.types import Command

config = {"configurable": {"thread_id": "siopv-thread-<uuid>"}}

# First invocation — hits interrupt, returns immediately
result = graph.invoke({"report_id": "CVE-2025-1234"}, config=config)
interrupt_payload = result["__interrupt__"][0].value  # dict with question+details

# After human responds — resume
resumed = graph.invoke(Command(resume=True), config=config)  # or Command(resume={"action": "approve"})
```

**Async streaming variant** (preferred for Streamlit):
```python
async for metadata, mode, chunk in graph.astream(
    initial_input, stream_mode=["messages", "updates"], config=config
):
    if mode == "updates" and "__interrupt__" in chunk:
        payload = chunk["__interrupt__"][0].value
        # Surface to Streamlit UI, collect response, then:
        initial_input = Command(resume=user_response)
        break
```

### 1.2 SQLite Checkpointing — Current API

```python
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

# SQLite connection — use check_same_thread=False for async contexts
conn = sqlite3.connect("siopv_checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)

# Optional: encrypted checkpoints
from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
serde = EncryptedSerializer.from_pycryptodome_aes()  # reads LANGGRAPH_AES_KEY env var
checkpointer = SqliteSaver(conn, serde=serde)

# Compile graph WITH checkpointer (mandatory for interrupt to work)
graph = builder.compile(checkpointer=checkpointer)
```

**Key gotcha**: `interrupt()` requires a checkpointer at compile time. Without it, `interrupt()` raises at runtime.

### 1.3 TypedDict State with SQLite — Gotchas

- LangGraph serializes TypedDict state to JSON for SQLite. All state values must be JSON-serializable.
- Avoid storing non-serializable objects (e.g., open file handles, httpx clients) in state.
- State keys can be added/removed across graph versions with full backward/forward compatibility.
- State keys that are **renamed** lose their saved values in existing threads.
- State keys whose **types change incompatibly** may cause issues for in-flight threads.

### 1.4 Adding output_node (Phase 8 Topology Change)

LangGraph graph migration rules (verified from docs):
- **Threads at END**: any topology change is fully supported (add/remove/rename nodes, change edges).
- **Interrupted threads**: adding new nodes is OK. Renaming or removing nodes that a thread is about to enter is NOT supported.
- **Adding `output_node`** for Phase 8: safe for all threads since it's appended after the final node (classify/escalate → output_node → END).

Pattern for Phase 8 topology:
```python
# Phase 7 (current): ... → classify → [escalate] → END
# Phase 8: ... → classify → [escalate] → output_node → END

builder.add_node("output_node", output_node_fn)
builder.add_edge("classify", "output_node")   # adjust conditional edges as needed
builder.add_edge("escalate", "output_node")
builder.add_edge("output_node", END)
```

No migration scripts needed — SQLite checkpoints for completed threads are unaffected.

---

## 2. LangSmith Verified Patterns

### 2.1 Python Client — List & Read Runs

```python
from langsmith import Client

client = Client()  # reads LANGSMITH_API_KEY, LANGSMITH_PROJECT from env

# List runs for a project (returns iterator)
runs = client.list_runs(
    project_name="siopv-production",
    run_type="chain",           # "llm", "tool", "chain", "retriever"
    filter='eq(status, "success")',
    start_time=datetime(2026, 3, 1),
    limit=50,
    is_root=True,               # only root runs (no parent)
)
for run in runs:
    print(run.id, run.name, run.inputs, run.outputs)

# Fetch single run by ID
run = client.read_run(run_id="a36092d2-4ad5-4fb4-9c0d-0dba9a2ed836")
print(run.start_time, run.end_time, run.outputs)

# Fetch by list of IDs
selected = list(client.list_runs(id=["uuid1", "uuid2"]))
```

### 2.2 For PDF Inclusion — CoT Trace Extraction

```python
from langsmith import Client
from datetime import datetime, timezone

client = Client()

def extract_trace_for_pdf(thread_id: str, project: str = "siopv") -> dict:
    """Pull LangSmith runs for a given thread_id and format for PDF."""
    runs = list(client.list_runs(
        project_name=project,
        filter=f'eq(metadata_key, "thread_id", "{thread_id}")',
        is_root=False,
        run_type="llm",
    ))
    return {
        "thread_id": thread_id,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "llm_calls": [
            {
                "name": r.name,
                "start": r.start_time.isoformat() if r.start_time else None,
                "end": r.end_time.isoformat() if r.end_time else None,
                "inputs": r.inputs,
                "outputs": r.outputs,
                "total_tokens": r.total_tokens,
            }
            for r in runs
        ],
    }
```

**Tag runs for retrieval** (set at invocation time via metadata):
```python
config = {
    "configurable": {"thread_id": "siopv-thread-<uuid>"},
    "metadata": {"thread_id": "siopv-thread-<uuid>", "report_id": "CVE-2025-1234"},
}
graph.invoke(input, config=config)
```

### 2.3 REST API (fallback if SDK unavailable)

```bash
curl "https://api.smith.langchain.com/runs?project_name=siopv&is_root=true&limit=10" \
  -H "x-api-key: $LANGSMITH_API_KEY"
```

---

## 3. Redis + FastAPI + OpenTelemetry Verified Patterns

### 3.1 Redis Async Cache (EPSS score layer)

```python
# Use redis.asyncio (bundled in redis-py >= 4.2 — NO separate aioredis needed)
import redis.asyncio as redis
import json
import hashlib
from typing import Optional, Any

class EPSSRedisCache:
    def __init__(self, redis_url: str, default_ttl: int = 86400):  # 24h default
        self.client = redis.from_url(redis_url)  # handles connection pooling
        self.default_ttl = default_ttl

    def _key(self, cve_id: str) -> str:
        return f"epss:score:{cve_id.upper()}"  # e.g. "epss:score:CVE-2025-1234"

    async def get(self, cve_id: str) -> Optional[dict]:
        data = await self.client.get(self._key(cve_id))
        return json.loads(data) if data else None

    async def set(self, cve_id: str, score_data: dict, ttl: Optional[int] = None) -> None:
        await self.client.setex(
            self._key(cve_id),
            ttl or self.default_ttl,
            json.dumps(score_data),
        )

    async def close(self) -> None:
        await self.client.aclose()
```

httpx + Redis cache-aside pattern:
```python
import httpx

async def fetch_epss_score(cve_id: str, cache: EPSSRedisCache) -> dict:
    cached = await cache.get(cve_id)
    if cached:
        return cached
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.first.org/data/v1/epss",
            params={"cve": cve_id},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
    await cache.set(cve_id, data)
    return data
```

Key naming convention: `epss:score:{CVE_ID}` (colon-delimited namespace:entity:discriminator)

### 3.2 FastAPI + OpenTelemetry

```python
# pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from fastapi import FastAPI

# Step 1: Configure provider (once at startup)
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)

# Step 2: Create app
app = FastAPI()

# Step 3: Instrument AFTER app creation
FastAPIInstrumentor.instrument_app(
    app,
    excluded_urls="healthz,readyz,metrics",
    http_capture_headers_server_request=["x-request-id", "x-tenant-id"],
    http_capture_headers_sanitize_fields=["authorization", "set-cookie"],
)
```

Optional custom span enrichment:
```python
from opentelemetry.trace import Span

def server_request_hook(span: Span, scope: dict) -> None:
    if span and span.is_recording():
        # Extract tenant/thread context from headers
        headers = dict(scope.get("headers", []))
        if b"x-thread-id" in headers:
            span.set_attribute("siopv.thread_id", headers[b"x-thread-id"].decode())

FastAPIInstrumentor.instrument_app(app, server_request_hook=server_request_hook)
```

### 3.3 OpenTelemetry httpx Instrumentation

```python
# pip install opentelemetry-instrumentation-httpx
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

# Global (instruments all AsyncClient / Client instances created after this call)
HTTPXClientInstrumentor().instrument()

# All httpx.AsyncClient() created after this point are auto-traced
async with httpx.AsyncClient() as client:
    resp = await client.get("https://api.first.org/data/v1/epss")
```

**Important caveat**: Module-level functions `httpx.get()`, `httpx.post()` are NOT instrumented
by global `instrument()`. Only `Client` / `AsyncClient` instances are traced.
See: opentelemetry-python-contrib issue #1742.

### 3.4 OpenTelemetry SQLAlchemy Instrumentation

```python
# pip install opentelemetry-instrumentation-sqlalchemy
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

SQLAlchemyInstrumentor().instrument(engine=engine)  # or instrument() globally
```

---

## 4. Libraries Verified

| Library | Tier 1 (Context7) | Tier 3 (WebSearch) |
|---------|-------------------|--------------------|
| LangGraph 0.2+ | ✅ `/websites/langchain_oss_python_langgraph` (258→900 snippets) | ✅ (cross-checked) |
| LangSmith SDK | ✅ `/langchain-ai/langsmith-sdk` + `/websites/langchain_langsmith` | ✅ (REST API confirmed) |
| FastAPI | ✅ `/fastapi/fastapi` | ✅ FastAPIInstrumentor signature confirmed |
| OpenTelemetry Python | ✅ `/websites/opentelemetry-python_readthedocs_io_en_stable` | ✅ httpx issue #1742 confirmed |
| Redis async | N/A (not in Context7) | ✅ redis-py >= 4.2 redis.asyncio confirmed |

Training data was NOT relied upon — all patterns verified via 3-tier chain.

---

## 5. Key Findings Summary

1. **LangGraph interrupt API**: `interrupt(payload)` inside node + `Command(resume=value)` to resume. Both sync (`graph.invoke`) and async (`graph.astream`) are supported. Payload must be JSON-serializable.

2. **SQLite checkpointing**: `SqliteSaver(sqlite3.connect("db.db", check_same_thread=False))` — `check_same_thread=False` is critical for async FastAPI/Streamlit contexts. Optional `EncryptedSerializer` available.

3. **Phase 8 topology change is safe**: Adding `output_node` to the END of the graph is fully supported for all completed threads. In-flight interrupted threads can safely enter new downstream nodes.

4. **LangSmith trace retrieval**: Use `client.list_runs(project_name=..., filter=..., is_root=True)` for root traces. Tag runs with `metadata={"thread_id": ...}` at invocation time to enable retrieval by thread. `client.read_run(run_id)` for single run.

5. **Redis async**: `redis.asyncio` (not `aioredis`) is the current standard. `redis.from_url(REDIS_URL)` handles pooling. Use `setex(key, ttl_seconds, json.dumps(data))` for atomic set+expire.

6. **FastAPI + OTel**: Call `FastAPIInstrumentor.instrument_app(app)` AFTER app creation and AFTER `TracerProvider` setup. Use `excluded_urls` for health/metrics endpoints.

7. **httpx OTel**: `HTTPXClientInstrumentor().instrument()` once at startup covers all `AsyncClient` instances. Module-level `httpx.get()` is NOT covered — always use `AsyncClient`.

8. **No aioredis**: `aioredis` was merged into redis-py >= 4.2. Import: `import redis.asyncio as redis`. Do NOT add `aioredis` as a dependency.

9. **LangSmith requires env vars**: `LANGSMITH_API_KEY` + `LANGSMITH_PROJECT` + `LANGSMITH_TRACING_V2=true`. The SDK auto-traces LangGraph when these are set — no manual instrumentation needed for basic tracing.

10. **EPSS cache key convention**: `epss:score:{CVE_ID_UPPERCASE}` with 24h TTL (EPSS scores update daily). Store full FIRST.org API response as JSON.
