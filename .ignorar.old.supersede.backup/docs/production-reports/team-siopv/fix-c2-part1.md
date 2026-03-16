# Task #9: Convert asyncio.run() to async def in 3 node files

**Date:** 2026-03-05
**Agent:** c2-fixer-1
**Status:** COMPLETE

## Changes Made

### 1. `src/siopv/application/orchestration/nodes/dlp_node.py`
- Changed `def dlp_node(...)` to `async def dlp_node(...)`
- Replaced `asyncio.run(_run_dlp_for_vulns(...))` with `await _run_dlp_for_vulns(...)`
- Linter auto-removed unused `import asyncio`

### 2. `src/siopv/application/orchestration/nodes/enrich_node.py`
- Changed `def enrich_node(...)` to `async def enrich_node(...)`
- Replaced `asyncio.run(_run_enrichment(...))` with `await _run_enrichment(...)`
- Linter auto-removed unused `import asyncio`

### 3. `src/siopv/application/orchestration/nodes/authorization_node.py`
- Changed `def authorization_node(...)` to `async def authorization_node(...)`
- Changed `def _execute_authorization_check(...)` to `async def` with `await`
- Changed `def _run_authorization_check(...)` to `async def` with `await port.check(context)`
- Linter auto-removed unused `import asyncio`

### Test files updated
- `tests/unit/application/orchestration/nodes/test_dlp_node.py` — all `def test_` calling `dlp_node` changed to `async def test_` with `await`; patches changed from `asyncio.run` to `_run_dlp_for_vulns`
- `tests/unit/application/orchestration/nodes/test_enrich_node.py` — all `def test_` calling `enrich_node` changed to `async def test_` with `await`; exception test patch changed from `asyncio.run` to `_run_enrichment`
- `tests/unit/application/orchestration/test_authorization_node.py` — all `def test_` calling `authorization_node` changed to `async def test_` with `await`

## Test Results
- **Before:** 26 failures
- **After:** 4 failures (all in `test_graph.py` — Task #10 scope, not this task)
- **1400 passed, 12 skipped, 3 warnings**

## Notes
- `graph.py` was NOT touched (Task #10 responsibility)
- The 4 remaining `test_graph.py` failures are expected: `graph.py` still calls these node functions synchronously
- `enrich_node_async` (already existed as async) was left untouched
