# Truth-05: SIOPV `docs/` and `rules/` Files
**Generated:** 2026-03-13
**Authority:** truth-00 directory structure + Round 3 Gap Analysis (Sections 1, 2, 3)
**Scope:** `siopv/.claude/rules/` (3 files) and `siopv/.claude/docs/` (5 files)

---

## 1. Docs Inventory

| File | Action | Source | Purpose |
|------|--------|--------|---------|
| `docs/verification-thresholds.md` | ADAPT | sec-llm-workbench/.claude/docs/verification-thresholds.md | SIOPV pass/fail criteria — add 83% coverage floor, Phase 7 health check |
| `docs/model-selection-strategy.md` | COPY | sec-llm-workbench/.claude/docs/model-selection-strategy.md | Haiku/Sonnet/Opus routing — universal, no SIOPV changes needed |
| `docs/python-standards.md` | COPY | sec-llm-workbench/.claude/docs/python-standards.md | Python 3.11+ standards — exact SIOPV stack (uv, Pydantic v2, httpx, structlog) |
| `docs/errors-to-rules.md` | NEW | — | SIOPV-specific error log seeded with Stage 2 violation patterns |
| `docs/siopv-phase7-8-context.md` | NEW | Stage 3 final report library facts | Code-implementer context: Streamlit, Jira ADF, fpdf2, Redis, LangSmith patterns |

---

## 2. Rules Inventory

| File | Action | Source | Purpose |
|------|--------|--------|---------|
| `rules/agent-reports.md` | COPY | sec-llm-workbench/.claude/rules/agent-reports.md | Timestamp-UUID report naming — universal, prevents race conditions |
| `rules/placeholder-conventions.md` | COPY | sec-llm-workbench/.claude/rules/placeholder-conventions.md | Template syntax conventions — universal |
| `rules/tech-stack.md` | ADAPT | sec-llm-workbench/.claude/rules/tech-stack.md | Add Phase 7/8 libraries; remove meta-project `mcp-setup.md` reference |

---

## 3. ADAPT Specifications

### 3.1 `rules/tech-stack.md`

**Changes from source:**
- Add Phase 7/8 libraries to the stack list: `streamlit`, `fpdf2`, `redis.asyncio`, `langgraph`, `openfga-sdk`, `presidio-analyzer`, `presidio-anonymizer`, `langsmith`
- Remove the line: `**→ See `.claude/docs/mcp-setup.md` for Context7 MCP setup instructions**` (meta-project file, not in SIOPV)
- Keep paths frontmatter, core Python stack, Before/After Write rules

**Full file content for SIOPV:**
```markdown
---
paths:
  - "**/*.py"
  - "pyproject.toml"
---

# Tech Stack

- Python 3.11+ (`list[str]`, `X | None`)
- uv (not pip)
- Pydantic v2
- httpx async
- structlog
- pathlib
- langgraph (LangGraph 0.2+)
- streamlit (Phase 7 — use `@st.fragment`, `st.cache_resource`, ThreadPoolExecutor bridge)
- fpdf2 (Phase 8 — `add_font()` requires `fname` since v2.7)
- redis.asyncio (not aioredis — merged into redis-py ≥4.2)
- openfga-sdk
- presidio-analyzer / presidio-anonymizer
- langsmith (tracing — requires LANGCHAIN_API_KEY env var)

## Before Write/Edit
Query Context7 MCP for library syntax.

## After Write/Edit
Execute /verify before commit.
```

---

### 3.2 `docs/verification-thresholds.md`

**Changes from source:**
1. **test-generator section:** Change `coverage >= 80%` → `coverage >= 83%` (SIOPV current baseline from MEMORY.md)
2. **code-reviewer section:** Change `Test coverage < 80%` → `Test coverage < 83%`
3. **Per-Module Coverage Floor section:** Keep 50% floor — unchanged
4. **Add new row to Verification Thresholds Table:**
   ```
   | **pytest coverage (overall)** | Testing | >= 83% | < 83% | ✅ Yes | test-generator |
   ```
5. **Add new entry after smoke-test-runner section:**
   ```
   ### Phase 7 Health Check
   **Check:** Streamlit app starts without exception: `uv run streamlit run src/siopv/interfaces/ui/app.py --headless`
   **Pass:** Process starts, no ImportError or RuntimeError in first 5 seconds
   **Fail:** Any crash, ImportError, or async boundary violation at startup
   ```
6. **Remove** the `## Cost Monitoring` section (meta-project scripts not in SIOPV)
7. **Remove** the `## Related Files` section (workflow paths differ in SIOPV)
8. **Update** `## Workflow Integration` to reference `siopv/.claude/workflow/` paths

**Keep unchanged:** All 15 agent threshold definitions (rows 1–15 in table), Command Blockers section, Adding New Thresholds section.

---

## 4. NEW Specifications

### 4.1 `docs/errors-to-rules.md`

**Purpose:** SIOPV-specific error log, separate from global `~/.claude/rules/errors-to-rules.md`.
Seeded with Stage 2 hexagonal violations as concrete error patterns.

```markdown
# SIOPV Project Errors → Rules Log

Project-specific errors. Reviewed by agents at session start.
> **Global log:** `~/.claude/rules/errors-to-rules.md`

---

## Logged Errors

### 2026-03-11: Adapter imports in application layer (Stage 2 CRITICAL)

**Error:** `application/use_cases/ingest_trivy.py:17` imports `TrivyParser` directly from
`adapters/`. `application/use_cases/classify_risk.py:18` imports `FeatureEngineer` from
`adapters/`. Application layer must depend only on ports (abstract interfaces).

**Rule:** Use cases MUST import only from `domain/` and `application/ports/`. If an adapter
class is needed, inject it via the port interface. Never import from `adapters/` in `application/`.

---

### 2026-03-11: DI ports left as None in CLI (Stage 2 HIGH)

**Error:** `interfaces/cli/main.py` wires all 8 adapter ports as `None`. The dependency
injection container is never invoked at CLI entry point.

**Rule:** ALWAYS call the DI factory functions (`infrastructure/di/`) before constructing
the orchestration graph in the CLI. Verify with: `assert port is not None` before graph init.

---

### 2026-03-11: Duplicate OpenFGA adapter instances (Stage 2 MEDIUM)

**Error:** `infrastructure/di/authorization.py` creates 3 separate `OpenFGAAdapter` instances
instead of caching one. Causes multiple connections and inconsistent state.

**Rule:** ALWAYS decorate DI factory functions with `@lru_cache`. One adapter instance per
process. OpenFGA adapter is expensive to create — `@lru_cache` is mandatory.

---

### 2026-03-11: Missing DLPPort inheritance (Stage 2 MEDIUM)

**Error:** `adapters/dlp/dual_layer_adapter.py` does not explicitly inherit from `DLPPort`.
Passes duck-typing tests but breaks strict port compliance checks.

**Rule:** Every adapter class MUST explicitly inherit from its port interface. No implicit
duck typing. Pattern: `class DualLayerDLPAdapter(DLPPort):`.

---

### 2026-03-11: Use case instantiated directly in node (Stage 2 MEDIUM)

**Error:** `application/orchestration/nodes/ingest_node.py` directly instantiates
`IngestTrivyUseCase()` instead of receiving it via constructor injection.

**Rule:** LangGraph nodes are thin wrappers. They MUST receive use cases via constructor
injection — never instantiate domain/application objects inside node functions.

---

### 2026-03-11: Domain logic in LangGraph edge routing (Stage 2 LOW)

**Error:** `application/orchestration/edges.py::calculate_batch_discrepancies()` contains
domain logic (discrepancy calculation) that belongs in a domain service.

**Rule:** LangGraph edges must contain only routing decisions (if/else on state fields).
Any calculation or business logic belongs in a domain service, called from a node.
```

---

### 4.2 `docs/siopv-phase7-8-context.md`

**Purpose:** Distilled Stage 3 verified library facts. Loaded by code-implementer and phase7/8 builder agents as mandatory context before writing any Phase 7 or 8 code.

```markdown
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
```

---

## 5. COPY Confirmations

| File | Source Path | Notes |
|------|-------------|-------|
| `rules/agent-reports.md` | `/Users/bruno/sec-llm-workbench/.claude/rules/agent-reports.md` | Timestamp UUID naming, wave timing — universal |
| `rules/placeholder-conventions.md` | `/Users/bruno/sec-llm-workbench/.claude/rules/placeholder-conventions.md` | Syntax conventions — universal |
| `docs/model-selection-strategy.md` | `/Users/bruno/sec-llm-workbench/.claude/docs/model-selection-strategy.md` | Haiku/Sonnet/Opus routing — no project-specific changes |
| `docs/python-standards.md` | `/Users/bruno/sec-llm-workbench/.claude/docs/python-standards.md` | Python 3.11+ — exact SIOPV stack, no changes |

---

## 6. Excluded Items

| File | Why Excluded |
|------|-------------|
| `docs/techniques.md` | META-ONLY — meta-project techniques catalog, references non-SIOPV projects |
| `docs/mcp-setup.md` | META-ONLY — meta-project MCP infrastructure setup |
| `docs/agent-tool-schemas.md` | META-ONLY — meta-project orchestration tooling (TeamCreate, SendMessage schemas) |
| `docs/traceability.md` | META-ONLY — meta-project tracing setup with meta-project paths |
| `docs/errors-to-rules.md` (meta version) | SUPERSEDED — SIOPV gets own `docs/errors-to-rules.md` [NEW]; meta log is cross-project only |
| `docs/2026-03-12-...-universal-project-automation-template-...md` | META-ONLY — Stage 4 process documentation |
