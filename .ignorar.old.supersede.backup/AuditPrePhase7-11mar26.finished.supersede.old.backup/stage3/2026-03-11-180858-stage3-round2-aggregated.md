# STAGE-3 Round 2 Aggregated Report
**Aggregator:** round2-aggregator
**Timestamp:** 2026-03-11-180858
**Sources:** scanner-asyncio-deep (180609) + scanner-openfga-deep (180630)

---

## 1. Executive Summary

Round 2 performed two parallel deep scans:

- **scanner-asyncio** (R2-A): Audited all async/await patterns across the pipeline — CLI, orchestration nodes (dlp, enrich, ingest), and LLM adapter stub. Focused on `asyncio.run()` misuse, event loop nesting, and Phase 7 Streamlit risks.
- **scanner-openfga** (R2-B): Audited the full OpenFGA authorization stack — port purity, DI factory wiring, node async correctness, configuration, and Phase 7 reusability.

**Overall verdict:** The codebase is in better shape than STAGE-2 suspected. The single `asyncio.run()` call is correct. The authorization node is fully async and fail-secure. Two actionable structural issues remain: (1) 3 independent adapter instances in DI, and (2) one dead async export (`enrich_node_async`). Phase 7 can proceed with targeted bridging work.

---

## 2. asyncio.run() Occurrences

| # | File | Line | Pattern | Risk |
|---|------|------|---------|------|
| 1 | `interfaces/cli/main.py` | 87 | `asyncio.run(run_pipeline(...))` inside sync Typer command | **LOW — correct usage** |

**No other `asyncio.run()` calls found** across orchestration nodes, adapters, or graph assembly.

**No `asyncio.get_event_loop()` calls found** in orchestration layer.

**No `nest_asyncio` usage found** anywhere.

---

## 3. Async Node Pattern Inventory

| File / Function | Signature | Registered in Graph | Correct? |
|----------------|-----------|---------------------|---------|
| `cli/main.py:process_report` | `def` (sync Typer) | N/A | ✅ |
| `orchestration/nodes/dlp_node.py:dlp_node` | `async def` | `"dlp"` via `async _dlp_node` closure | ✅ |
| `orchestration/nodes/enrich_node.py:enrich_node` | `async def` | `"enrich"` via `async _enrich_node` closure | ✅ |
| `orchestration/nodes/enrich_node.py:enrich_node_async` | `async def` | **NOT registered** | ⚠️ Dead code |
| `orchestration/nodes/ingest_node.py:ingest_node` | `def` (sync) | `"ingest"` | ✅ |
| `orchestration/nodes/authorization_node.py:authorization_node` | `async def` | `"authorize"` | ✅ |

Graph invocation: `graph.ainvoke()` — correct async path. No sync `graph.invoke()` found.

---

## 4. OpenFGA Wiring Issues

### F-01 (MEDIUM — CONFIRMED from STAGE-2 #5): 3 Independent Adapter Instances

**Root cause:** `create_authorization_adapter()` at `di/authorization.py:52` has **no `@lru_cache`**.

Each of the 3 port getters calls it independently, creating 3 separate `OpenFGAAdapter` objects:

| Line | Getter | Status |
|------|--------|--------|
| `di/authorization.py:100` | `get_authorization_port()` | Cached, but creates fresh adapter |
| `di/authorization.py:135` | `get_authorization_store_port()` | Cached, but creates fresh adapter |
| `di/authorization.py:174` | `get_authorization_model_port()` | Cached, but creates fresh adapter |

**Downstream effects:**
- 3 OpenFGA HTTP connections (not 1)
- 3 independent circuit breakers — a trip on one does not propagate to others
- 3 separate `_cached_model_id` states — model ID refresh on one is not visible to others
- `initialize()` must be called on all 3 separately; no lifecycle coordination

### F-02 (LOW): `getattr()` Fallbacks Hide Missing Settings

`getattr(settings, "openfga_authorization_model_id", None)` silently defaults to `None` rather than raising a startup error. Reduces observability but is not a security risk.

### F-03 (LOW): `initialize()` Lifecycle Not Enforced by DI

No `await adapter.initialize()` in `di/authorization.py`. Callers must initialize each adapter manually. With 3 instances (F-01), this is error-prone.

---

## 5. Combined REMEDIATION-HARDENING Fix List (Prioritized)

| Priority | ID | Source | File | Action |
|----------|----|--------|------|--------|
| **P1** | RH-01 | F-01 | `di/authorization.py:52` | Add `@lru_cache` to `_get_shared_adapter()` factory; redirect all 3 port getters to it → 1 adapter, 1 connection |
| **P2** | RH-Fix-B | asyncio | `enrich_node.py:190–258` | Remove dead `enrich_node_async`; update `__all__` to export only `enrich_node` |
| **P3** | RH-03 | F-03 | `di/authorization.py` | Add `async def initialize_authorization(settings)` lifecycle helper; call once at graph startup |
| **P4** | RH-Fix-C | asyncio | Phase 7 code (new) | Implement `st.cache_resource` + background-thread `asyncio.run()` bridge for Streamlit pipeline calls |
| **P5** | RH-Fix-D | asyncio | `dlp_node.py`, `enrich_node.py` | Add `# LangGraph async node — requires ainvoke` comments on async node functions |
| **P6** | RH-02 | F-02 | `Settings` class | Add Pydantic validators to emit startup warnings for missing `openfga_authorization_model_id` |
| **P7** | RH-Fix-A | asyncio | `graph.py` | Add assertion at `run_pipeline` entry confirming `ainvoke` is the invocation path |

---

## 6. Phase 7 Readiness Assessment

**Can the existing OpenFGA adapter gate Streamlit?**

**YES — with required bridging. The adapter is architecturally ready.**

| Capability | Status |
|------------|--------|
| `AuthorizationPort.check()` for page gating | ✅ Reusable as-is |
| `AuthorizationPort.batch_check()` for multi-resource UI | ✅ Available |
| Protocol-based port — no Streamlit imports needed | ✅ |
| Circuit breaker + retry for transient failures | ✅ Already present |
| Async bridge for Streamlit sync context | ❌ Must implement |
| `initialize()` call at Streamlit startup | ❌ Must implement (1x via `st.cache_resource`) |
| Fix F-01 (3 instances) before Phase 7 | ⚠️ Recommended before Phase 7 build |

**Recommended Phase 7 initialization pattern:**
```python
@st.cache_resource
def get_authz_port():
    settings = get_settings()
    port = get_authorization_port(settings)
    asyncio.run(port.initialize())  # Safe: no loop running at Streamlit startup
    return port
```

For pipeline calls from Streamlit callbacks (async pipeline in sync Streamlit thread):
```python
from concurrent.futures import ThreadPoolExecutor
import asyncio

_executor = ThreadPoolExecutor(max_workers=1)

def run_pipeline_sync(report_path, user_id, project_id):
    future = _executor.submit(asyncio.run, run_pipeline(report_path, user_id, project_id))
    return future.result()
```

---

## 7. Conflicts and Discrepancies Between Agents

**No conflicts found.** Both agents are consistent:

- asyncio scanner confirmed `authorization_node` has **no `asyncio.run()`** — OpenFGA scanner confirmed the same independently.
- Both agents independently identified that `graph.ainvoke()` is the correct invocation path.
- OpenFGA scanner's Phase 7 async bridging concern (Streamlit sync context) is consistent with asyncio scanner's §4.6 Phase 7 risk.
- STAGE-2 Finding #5 (3 uncached adapters) confirmed by OpenFGA scanner with precise line numbers.

---

## 8. Open Questions for Round 3 or REMEDIATION-HARDENING

1. **Does `graph.py` call `initialize()` on the authorization adapter at startup?** The OpenFGA scanner found no evidence of this call in `di/authorization.py` — it may exist in `graph.py` itself. Round 3 or REMEDIATION-HARDENING should verify.

2. **Is `enrich_node_async` referenced anywhere outside `enrich_node.py`?** Asyncio scanner marked it dead, but a broader grep across all test files and integration tests is needed to confirm safe removal.

3. **What OpenFGA relation model does Phase 7 need?** Current model supports `Action.VIEW` on `ResourceType.PROJECT`. Phase 7 UI admin views may need additional relations (`EDIT`, `ADMIN`) — authorization model schema review is needed before Phase 7 build.

4. **Does the Streamlit `dashboard` command (cli/main.py:124–151) share any event loop with the subprocess it launches?** Asyncio scanner assessed this as safe (subprocess isolation), but confirmation that no shared state or socket is passed to the subprocess is recommended.

---

## 9. Summary Statistics

| Category | Count |
|----------|-------|
| Files scanned (combined) | 10 |
| `asyncio.run()` occurrences (correct usage) | 1 |
| `asyncio.run()` occurrences (incorrect/risky) | 0 |
| OpenFGA DI findings (F-01..F-03) | 3 |
| Dead code items | 1 (`enrich_node_async`) |
| REMEDIATION-HARDENING fixes identified | 7 |
| Phase 7 blockers (hard) | 1 (async bridge) |
| Phase 7 blockers (soft/recommended) | 2 (F-01 fix, initialize lifecycle) |
