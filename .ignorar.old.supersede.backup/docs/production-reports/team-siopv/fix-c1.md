# Fix C1: Forward enrichment clients in run_pipeline()

**Date:** 2026-03-05
**File:** `src/siopv/application/orchestration/graph.py`
**Status:** COMPLETE

## Problem

`run_pipeline()` accepted `authorization_port`, `dlp_port`, and `classifier` but did NOT accept or forward the 5 enrichment-related parameters to `create_pipeline_graph()`:
- `nvd_client`
- `epss_client`
- `github_client`
- `osint_client`
- `vector_store`

This meant callers of `run_pipeline()` could never inject enrichment clients, so `enrich_node` would always run with `None` clients.

## Fix Applied

1. Added 5 parameters to `run_pipeline()` signature (with `None` defaults, matching `create_pipeline_graph()`).
2. Added corresponding docstring entries.
3. Forwarded all 5 parameters in the `create_pipeline_graph()` call inside `run_pipeline()`.

## Test Results

- All pre-existing tests unaffected (new params have `None` defaults, backward-compatible).
- 4 pre-existing failures in `test_graph.py` and node tests due to async node coroutine issue (audit finding #7) -- unrelated to this fix.
- 352+ tests pass, 12 skipped.
