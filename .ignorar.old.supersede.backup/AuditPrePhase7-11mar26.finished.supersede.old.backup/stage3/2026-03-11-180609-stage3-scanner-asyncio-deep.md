# STAGE-3 Deep Scan: asyncio Patterns
**Agent:** scanner-asyncio
**Timestamp:** 2026-03-11-180609
**Wave:** Round 2-A (parallel)

---

## 1. Files Scanned

| # | File | Lines |
|---|------|-------|
| 1 | `interfaces/cli/main.py` | 261 |
| 2 | `application/orchestration/nodes/dlp_node.py` | 111 |
| 3 | `application/orchestration/nodes/enrich_node.py` | 265 |
| 4 | `application/orchestration/nodes/ingest_node.py` | 135 |
| 5 | `adapters/llm/__init__.py` | 1 (empty) |

Supplemental (via grep, no file slot used):
- `application/orchestration/graph.py` — targeted line queries for node registration and invocation patterns

---

## 2. asyncio.run() Occurrences

### 2.1 — cli/main.py:87

```python
result = asyncio.run(
    run_pipeline(
        report_path=report_path,
        user_id=user_id,
        project_id=project_id,
    )
)
```

**Context:** Inside Typer sync command `process_report()`. This is the top-level CLI entry point calling the async pipeline.

**Risk:** LOW — **Correct usage.** Typer command functions are plain sync `def`. Using `asyncio.run()` to drive an async coroutine from a sync entry point is the standard pattern. No event loop is running when Typer invokes `process_report()`, so there is no nesting risk. This usage is intentional and documented in `graph.py:426`.

**Note:** `asyncio.run()` is the **only** occurrence across all 5 scanned files. No other `asyncio.run()` calls were found in node functions.

---

## 3. async def / def Pattern Summary

### cli/main.py

| Function | Signature | Correct? |
|----------|-----------|----------|
| `main` | `def` | ✅ Typer callback |
| `process_report` | `def` | ✅ Typer command |
| `dashboard` | `def` | ✅ Typer command |
| `train_model` | `def` | ✅ Typer command |
| `version` | `def` | ✅ Typer command |

### dlp_node.py

| Function | Signature | Correct? |
|----------|-----------|----------|
| `_sanitize_one` (inner) | `async def` | ✅ Used with asyncio.gather |
| `_run_dlp_for_vulns` | `async def` | ✅ Awaited by dlp_node |
| `_build_dlp_result` | `def` | ✅ Pure data builder |
| `dlp_node` | `async def` | ⚠️ See §4 |

### enrich_node.py

| Function | Signature | Correct? |
|----------|-----------|----------|
| `enrich_node` | `async def` | ⚠️ See §4 |
| `_run_enrichment` | `async def` | ✅ Awaited by enrich_node |
| `_create_minimal_enrichments` | `def` | ✅ Pure data builder |
| `enrich_node_async` | `async def` | ⚠️ Redundant — see §4.2 |

### ingest_node.py

| Function | Signature | Correct? |
|----------|-----------|----------|
| `ingest_node` | `def` | ✅ Sync, correct for LangGraph |
| `ingest_node_from_dict` | `def` | ✅ Sync, correct |

---

## 4. Event Loop Risk Assessment

### 4.1 Async Node Registration (MEDIUM — design concern)

`dlp_node` and `enrich_node` are both `async def`. In `graph.py`, they are registered via wrapper closures:

```python
# graph.py:189
async def _dlp_node(state: PipelineState) -> dict[str, object]:
    ...  # injects dlp_port, then: await dlp_node(state, dlp_port=...)
self._graph.add_node("dlp", _dlp_node)

# graph.py:195
async def _enrich_node(state: PipelineState) -> dict[str, object]:
    ...  # injects clients, then: await enrich_node(state, ...)
self._graph.add_node("enrich", _enrich_node)
```

`run_pipeline` uses `graph.ainvoke()` (lines 491, 494), which is LangGraph's async invocation path. This is the **correct** approach for async nodes.

**Risk:** LOW under current setup. However: if any caller ever switches from `ainvoke` to `invoke` (sync), all async nodes will silently return un-awaited coroutines rather than raise immediately — a subtle bug that could surface as empty state keys.

### 4.2 Redundant `enrich_node_async` (LOW — dead code risk)

`enrich_node.py:190` defines `enrich_node_async`, which is identical to `enrich_node` except for logging labels. Both are exported via `__all__`. The graph only registers `enrich_node`. `enrich_node_async` is dead code and a maintenance hazard.

### 4.3 asyncio.gather in DLP Node (LOW — correct usage)

`dlp_node.py:41`:
```python
pairs = await asyncio.gather(*[_sanitize_one(v) for v in vulnerabilities])
```
This runs concurrent DLP sanitization per vulnerability. It is called inside `_run_dlp_for_vulns` which is itself `async def` and awaited by `dlp_node`. No nesting risk. Correct concurrent pattern.

### 4.4 No asyncio.get_event_loop() Found

Grep over `orchestration/` confirms zero occurrences of `asyncio.get_event_loop()`. No legacy loop-retrieval patterns.

### 4.5 No nest_asyncio Found

Zero occurrences of `nest_asyncio` across scanned files. No workarounds present.

### 4.6 Phase 7 Streamlit Risk (MEDIUM — future)

`cli/main.py:124–151` — `dashboard` command launches Streamlit via `subprocess.run(...)`. This is safe: Streamlit runs in a separate process, so no event loop is shared. However, **if Phase 7 Streamlit code calls the pipeline directly (not via subprocess)** and Streamlit's internal server has its own event loop running, calling `asyncio.run()` or `graph.ainvoke()` from within a Streamlit callback would raise `RuntimeError: This event loop is already running`. This must be guarded in Phase 7.

---

## 5. Recommended Fix Patterns for REMEDIATION-HARDENING

### Fix A — Guard async nodes against sync invocation

Add an assertion in `run_pipeline` to enforce `ainvoke` usage:

```python
# In graph.py, at the top of run_pipeline
import asyncio
if not asyncio.get_event_loop().is_running():
    raise RuntimeError("run_pipeline must be called from an async context or via asyncio.run()")
```
Alternatively, add a check that the graph was compiled with async-capable nodes before calling `invoke`.

### Fix B — Remove dead `enrich_node_async`

`enrich_node.py:190–258` is a duplicate of `enrich_node`. Remove it and update `__all__` to export only `enrich_node`. This prevents future confusion about which function to register in the graph.

### Fix C — Phase 7 Streamlit async bridge

When Phase 7 Streamlit code needs to call the pipeline, use `asyncio.get_event_loop().run_until_complete()` with a loop check, or prefer the `anyio` bridge:

```python
import anyio

# In Streamlit callback (sync context, but Streamlit may have a loop):
result = anyio.from_thread.run_sync(run_pipeline, ...)
```

Or use `asyncio.run()` only if confirmed no loop is running:
```python
try:
    loop = asyncio.get_running_loop()
    # Already in async context — schedule as task
    result = loop.run_until_complete(run_pipeline(...))  # WRONG in running loop
except RuntimeError:
    result = asyncio.run(run_pipeline(...))  # Safe only if no loop running
```

**Recommended for Streamlit:** Use a dedicated background thread with `concurrent.futures` + `asyncio.run()` to avoid event loop conflicts entirely.

### Fix D — Annotate async nodes explicitly

Add `# LangGraph async node — requires ainvoke` comments on `dlp_node` and `enrich_node` to make the async requirement visible to future maintainers.

---

## 6. Summary

- **`asyncio.run()` found in 1 location only:** `cli/main.py:87`. Usage is correct — sync Typer command driving top-level async pipeline. No nesting risk.
- **Two async nodes (`dlp_node`, `enrich_node`):** Both correctly wrapped as async closures in `graph.py` and driven via `graph.ainvoke()`. No `asyncio.run()` inside any node.
- **`ingest_node` is correctly sync:** Aligns with LangGraph's default sync node contract; no async operations needed.
- **Dead code risk:** `enrich_node_async` is a duplicate export not registered in the graph — should be removed before Phase 7 to prevent graph wiring confusion.
- **Phase 7 risk (MEDIUM):** If Streamlit calls pipeline directly (not subprocess), event loop nesting will crash. Recommend anyio bridge or background-thread `asyncio.run()` pattern for Phase 7 implementation.
