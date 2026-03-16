# Fix C2 Part 2: Update graph.py for async nodes

**Date:** 2026-03-05
**Task:** #10 (c2-fixer-2)
**Status:** COMPLETE

## Problem

After C2 Part 1 converted `dlp_node`, `enrich_node`, and `authorization_node` from sync to async, the graph builder and pipeline runner needed updates:

1. **Sync lambdas wrapping async functions** returned coroutines instead of results
2. **`graph.invoke()`** fails with async nodes — LangGraph requires `ainvoke()` for graphs containing async nodes
3. **`SqliteSaver`** does not support async methods — `ainvoke()` requires `AsyncSqliteSaver`
4. **Tests** used sync `invoke()` and sync `run_pipeline()` calls

## Changes Made

### `src/siopv/application/orchestration/graph.py`
- Replaced sync lambdas for `authorize`, `dlp`, and `enrich` nodes with `async def` wrapper functions (Python does not support `async lambda`)
- Converted `run_pipeline()` from sync to `async def`, using `await graph.ainvoke()`
- When `checkpoint_db_path` is provided, uses `AsyncSqliteSaver.from_conn_string()` as async context manager instead of sync `SqliteSaver`
- Added import for `AsyncSqliteSaver` from `langgraph.checkpoint.sqlite.aio`

### `src/siopv/interfaces/cli/main.py`
- Wrapped `run_pipeline()` call with `asyncio.run()` since CLI is a sync entry point
- Added `asyncio` import

### `tests/unit/application/orchestration/test_graph.py`
- Converted 3 `TestRunPipeline` test methods to `async def` with `await run_pipeline()`
- Converted `test_graph_routing_logic` to `async def` with `await graph.ainvoke()`
- Works with `asyncio_mode = "auto"` (no explicit `@pytest.mark.asyncio` needed)

## Verification

- **pytest:** 1404 passed, 12 skipped, 0 failures (including all 15 test_graph.py tests)
- **mypy:** 0 errors on `src/siopv/application/orchestration/` and `src/siopv/interfaces/cli/main.py`
