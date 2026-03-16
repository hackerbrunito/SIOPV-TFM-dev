# SIOPV Phase 4 & 5 Audit Report

**Date:** 2026-03-05
**Auditor:** Senior Code Auditor Agent
**Scope:** Phase 4 (LangGraph Orchestration) + Phase 5 (OpenFGA Authorization)
**Status:** READ-ONLY audit — no code changes made

---

## Executive Summary

- **`run_pipeline()` does NOT forward enrichment clients** to `create_pipeline_graph()`, meaning the enrichment phase (Phase 2) will always run in degraded "minimal enrichment" mode when called via `run_pipeline()`. This is a confirmed critical gap between the function's interface and its implementation.
- **`asyncio.run()` is used inside synchronous LangGraph nodes** (`authorization_node.py:194` and `enrich_node.py:73`, `dlp_node.py:106`), which will raise `RuntimeError: This event loop is already running` if these nodes are ever invoked from an async context (e.g., FastAPI, Streamlit, or any async runner).
- **`enrich_node_async()` is dead code** — it is defined and exported but is never wired into the graph; the graph uses only the sync `enrich_node`. The same applies to `ingest_node_from_dict()`.

---

## Findings Table

### Group 1: Errors (code-level bugs)

| # | Severity | File:Line | Issue | Recommended Fix |
|---|----------|-----------|-------|-----------------|
| 1 | CRITICAL | `graph.py:439-444` | `run_pipeline()` calls `create_pipeline_graph()` but does NOT pass `nvd_client`, `epss_client`, `github_client`, `osint_client`, or `vector_store`. These 5 parameters are accepted by `run_pipeline()` in its signature... except they are NOT in the signature at all. Enrichment clients are simply absent from `run_pipeline()`'s parameter list, meaning callers have no way to inject them. The graph builder supports them but the public convenience function does not. | Add `nvd_client`, `epss_client`, `github_client`, `osint_client`, `vector_store` parameters to `run_pipeline()` and forward them to `create_pipeline_graph()`. |
| 2 | HIGH | `authorization_node.py:194` | `asyncio.run(port.check(context))` inside a synchronous LangGraph node. If the pipeline is invoked from an async context (FastAPI, Streamlit, async test), this raises `RuntimeError: This event loop is already running`. | Replace with `anyio.from_thread.run_sync()` pattern or restructure the node to be async. LangGraph supports async nodes. |
| 3 | HIGH | `enrich_node.py:73` | `asyncio.run(_run_enrichment(...))` inside the synchronous `enrich_node`. Same issue as #2 — will break in any async runner. | Convert `enrich_node` to async, or use `anyio.from_thread.run_sync()`. |
| 4 | HIGH | `dlp_node.py:106` | `asyncio.run(_run_dlp_for_vulns(...))` inside the synchronous `dlp_node`. Same event-loop collision risk. | Same fix as #2/#3. |

### Group 2: Gaps (missing functionality)

| # | Severity | File:Line | Issue | Recommended Fix |
|---|----------|-----------|-------|-----------------|
| 5 | HIGH | `graph.py` (entire file) | No `output_node` exists anywhere in the codebase. The graph ends at `escalate → END` or `classify → END`. Phase 8 (Jira + PDF output) requires a new node wired AFTER `classify`/`escalate`, not just new files — the graph topology must change. | Plan for topology change: add `output_node` before `END` in both the classify and escalate branches. |
| 6 | MEDIUM | `state.py` | `PipelineState` has no fields for Phase 7 (Human-in-the-Loop / Streamlit) or Phase 8 (Output / Jira + PDF). Fields are only present for Phases 1-6. Adding these later requires a TypedDict extension and may break checkpointed state in SQLite. | Add placeholder fields for Phase 7/8 now (e.g., `human_review_result`, `output_report_path`, `jira_ticket_id`) to avoid breaking checkpoint schema later. |
| 7 | MEDIUM | `docker-compose.yml` | `OPENFGA_AUTHN_PRESHARED_KEYS=dev-key-siopv-local-1` is a hardcoded insecure key — not parameterized from environment variable. The adjacent comment acknowledges this but it is still shipped as-is. | Change to `OPENFGA_AUTHN_PRESHARED_KEYS=${OPENFGA_API_KEY}` and provide a `.env.example`. |
| 8 | MEDIUM | `classify_node.py:134-141` | `_estimate_llm_confidence()` is a pure math heuristic based on `risk_probability`, not an actual LLM call. The comment at line 134 says "In production, this would come from actual LLM evaluation" — but `adapters/llm/` is an empty directory. The confidence value fed into the escalation routing is a proxy, not a real LLM confidence. | Document this clearly as a known limitation. Create a ticket for Phase 4 LLM integration. The empty `adapters/llm/` directory should either have a stub adapter or be removed. |
| 9 | LOW | `openfga/` directory | `model.fga` and `model.json` exist at `/Users/bruno/siopv/openfga/` — good. However, the docker-compose does not mount or reference these files during the `openfga-migrate` or `openfga` service startup. The authorization model must be manually uploaded via API after the service starts. | Add documentation (or a setup script) explaining that the model at `openfga/model.fga` must be applied via `fga model write` after service startup. |

### Group 3: Inconsistencies

| # | Severity | File:Line | Issue | Recommended Fix |
|---|----------|-----------|-------|-----------------|
| 10 | HIGH | `enrich_node.py:193-267` | `enrich_node_async()` is defined, exported in `__all__`, but is never imported or used by the graph. The graph wires only the synchronous `enrich_node`. This creates a misleading API surface and dead code. | Remove `enrich_node_async` from `__all__` and add a deprecation notice or delete it. If async execution is desired, convert the graph node itself to async instead. |
| 11 | MEDIUM | `ingest_node.py:87-128` | `ingest_node_from_dict()` is defined but NOT wired into the graph and NOT in `nodes/__init__.py`. It is an orphaned alternative entry point. | Either wire it into the graph as a conditional start path, or move it to a utility module and document it explicitly as a helper function only. |
| 12 | MEDIUM | `docker-compose.yml:113` and `docker-compose.yml:201` | Both the `openfga-migrate` service (line 113) and the `openfga` service (line 201) hardcode `postgres://openfga:openfga@openfga-postgres:5432/openfga?sslmode=disable`. This is the same credential twice, with `sslmode=disable`. The `openfga-postgres` service (line 346-348) also hardcodes `POSTGRES_USER=openfga` and `POSTGRES_PASSWORD=openfga`. These are confirmed at those exact lines (note: audit memory mentioned lines 113 and 201 — confirmed correct). | Parameterize: `OPENFGA_DATASTORE_URI=postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@openfga-postgres:5432/openfga?sslmode=require`. |
| 13 | LOW | `graph.py:100` | Docstring in `PipelineGraphBuilder` lists `escalate` under "Phase 4 - Orchestration" but the file comment says Phase 4 is complete. The actual escalate node is the terminal node — but Phase 8's output is not in the graph at all. The docstring will become misleading once Phase 8 is added. | Update docstring when Phase 8 is implemented. |

### Group 4: Forgotten Tasks

| # | Severity | File:Line | Issue | Recommended Fix |
|---|----------|-----------|-------|-----------------|
| 14 | HIGH | `classify_node.py:134` | Comment: `"In production, this would come from actual LLM evaluation"` — this is a placeholder that has been shipped as-is. The escalation logic (route_after_classify) depends on `llm_confidence` values that are heuristic estimates. If the ML probability is 0.9, `_estimate_llm_confidence` will return ~0.97, meaning discrepancy with itself will be low and escalation will rarely trigger — defeating the intent of the uncertainty trigger. | Implement real LLM confidence via an adapter in `adapters/llm/`. Until then, document this explicitly as a known limitation in the project's architecture notes. |
| 15 | MEDIUM | `docker-compose.yml:211` | `OPENFGA_PLAYGROUND_ENABLED=true` — the playground exposes a UI that allows unrestricted tuple reads/writes in development. This is commented as a risk but left enabled. | Set `OPENFGA_PLAYGROUND_ENABLED=${OPENFGA_PLAYGROUND_ENABLED:-false}` to default-off. |

### Group 5: Test Gaps

| # | Severity | File:Line | Issue | Recommended Fix |
|---|----------|-----------|-------|-----------------|
| 16 | HIGH | `tests/unit/orchestration/` | `pytest tests/unit/orchestration/ --co -q` returns **0 tests collected**. All 111 orchestration tests live under `tests/unit/application/orchestration/` — the path in the audit spec does not match the actual test location. More critically: the path `tests/unit/orchestration/` is empty or non-existent. | Confirm test discovery path and ensure CI uses the correct path `tests/unit/application/orchestration/`. |
| 17 | HIGH | `src/.../orchestration/nodes/*.py` | Coverage for core node files is critically low: `enrich_node.py` at 18%, `escalate_node.py` at 16%, `classify_node.py` at 15%, `authorization_node.py` at 30%. The 111 collected tests cover the nodes structurally but with minimal coverage on actual logic branches. | Add tests for: DLP + auth node integration, enrichment client injection path, escalation routing with real discrepancy values. |
| 18 | HIGH | `tests/integration/test_openfga_real_server.py:32` | Real OpenFGA server integration tests are auto-skipped via `pytestmark = pytest.mark.skipif(not OPENFGA_API_URL, ...)`. These tests will never run in CI unless `SIOPV_OPENFGA_API_URL` is set. There is no Docker-based CI configuration to bring up OpenFGA for integration testing. | Add a `docker-compose.test.yml` or GitHub Actions service to run OpenFGA for integration tests. |
| 19 | MEDIUM | `tests/integration/test_authorization_integration.py` | Despite being in `tests/integration/`, this test file uses `unittest.mock` with no real OpenFGA server — it is actually a unit test mislabeled as integration. This inflates the apparent integration test coverage. | Move to `tests/unit/adapters/authorization/` or rename to clarify it does not require Docker. |
| 20 | MEDIUM | `src/siopv/application/orchestration/edges.py` | `edges.py` has only 17% coverage. The `calculate_batch_discrepancies()` function (lines 119-200) which implements the adaptive threshold logic is essentially untested — it is not called by `route_after_classify` and only appears in direct test calls to `TestCalculateBatchDiscrepancies`. This function could be removed from the routing path without breaking anything. | Verify whether `calculate_batch_discrepancies` is actually used in the routing path. If not, document it as a utility function only. Add tests for adaptive threshold behavior. |

---

## Detailed Findings by Audit Checklist Item

### 1. `run_pipeline()` parameter forwarding

**Status: CONFIRMED GAP**

`run_pipeline()` signature (graph.py:403-413):
```python
def run_pipeline(
    report_path: str | Path,
    *,
    thread_id: str | None = None,
    user_id: str | None = None,
    project_id: str | None = None,
    checkpoint_db_path: str | Path | None = None,
    authorization_port: AuthorizationPort | None = None,
    dlp_port: DLPPort | None = None,
    classifier: MLClassifierPort | None = None,
) -> PipelineState:
```

The parameters `nvd_client`, `epss_client`, `github_client`, `osint_client`, and `vector_store` are **completely absent** from `run_pipeline()`'s parameter list. The call to `create_pipeline_graph()` at lines 439-444 only passes `checkpoint_db_path`, `authorization_port`, `dlp_port`, `classifier`, and `with_checkpointer`. Callers of `run_pipeline()` have NO way to inject enrichment clients. The enrich_node will always call `_create_minimal_enrichments()` (returning stub data with `relevance_score=0.5`) when invoked via `run_pipeline()`.

### 2. Graph topology completeness

**No `output_node` exists.** Graph terminates at:
- `classify → (conditional)` → either `escalate → END` or directly `END`

The `route_after_escalate` function (edges.py:234) always returns `"end"`. There is no output processing, Jira ticket creation, or PDF generation in the graph. This is expected for Phase 8 not yet implemented, but the graph topology documentation does not reflect this gap.

All declared nodes ARE wired: `authorize`, `ingest`, `dlp`, `enrich`, `classify`, `escalate` all appear in both `_add_nodes()` and `_add_edges()`. No dangling nodes detected.

### 3. `asyncio.run()` anti-pattern

**Status: CONFIRMED at 3 locations:**

- `authorization_node.py:194`: `return asyncio.run(port.check(context))` inside `_run_authorization_check()`
- `enrich_node.py:73`: `enrichments = asyncio.run(_run_enrichment(...))` inside `enrich_node()`
- `dlp_node.py:106`: `per_cve = asyncio.run(_run_dlp_for_vulns(...))` inside `dlp_node()`

The comment at authorization_node.py:181-192 explicitly acknowledges this limitation: "If called from an async context, the caller should use the async port.check() method directly instead of this helper." However, no async node variants are wired into the graph.

### 4. Orphaned `enrich_node_async()`

**Status: CONFIRMED orphaned.**

`enrich_node_async` is:
- Defined at `enrich_node.py:193`
- Exported in `enrich_node.py:__all__` (line 264)
- NOT imported in `nodes/__init__.py`
- NOT used anywhere in `graph.py`
- NOT referenced in any test that exercises the graph

It is dead code. The graph only uses the synchronous `enrich_node`.

### 5. Dead code beyond `enrich_node_async`

- `ingest_node_from_dict()` (`ingest_node.py:87`): Defined, not in `nodes/__init__.py`, not wired into graph
- `calculate_batch_discrepancies()` (`edges.py:119`): Defined and tested in isolation but never called from `route_after_classify` — the routing uses `should_escalate_route()` which calls `_check_escalation_needed()` → `check_any_escalation_needed()` via utils, bypassing the batch discrepancy function entirely

### 6. State field completeness

`PipelineState` (state.py) covers:
- Phase 1 (ingestion): `vulnerabilities`, `report_path` ✅
- Phase 2 (enrichment): `enrichments` ✅
- Phase 3 (classification): `classifications` ✅
- Phase 4 (orchestration): `escalated_cves`, `llm_confidence`, `processed_count`, `errors` ✅
- Phase 5 (authorization): `user_id`, `project_id`, `system_execution`, `authorization_allowed`, `authorization_skipped`, `authorization_result` ✅
- Phase 6 (DLP): `dlp_result` ✅
- Phase 7 (Human-in-the-Loop): **MISSING** — no fields
- Phase 8 (Output): **MISSING** — no fields

### 7. Edge routing completeness

`route_after_authorization` returns `"ingest"` or `"end"` — both mapped in graph edges. ✅

`route_after_classify` returns `"escalate"`, `"continue"`, or `"end"` — all three mapped in graph edges. ✅

`route_after_escalate` always returns `"end"` — mapped. ✅

No missing route branches detected. The `RouteType = Literal["escalate", "continue", "end"]` type is consistent.

**One subtle issue:** `route_after_classify` short-circuits to `"end"` if `errors` is non-empty (line 219). This means a DLP or enrichment failure causes classify to also be skipped, and the pipeline ends silently with errors in state but no classification output. This may be intentional but is worth documenting.

### 8. OpenFGA model file

`/Users/bruno/siopv/openfga/model.fga` and `openfga/model.json` **exist**. The JSON model has schema_version 1.1 with `user`, `organization`, and `project` type definitions.

**The model is NOT mounted or referenced in docker-compose.** The `openfga-migrate` service runs database schema migration only (not model upload). There is no `openfga-setup` service or script that calls the OpenFGA API to apply the model. This means:
1. After `docker-compose up`, the OpenFGA instance has no authorization model loaded
2. Any call to `check()` will fail with "no authorization models found"
3. The health check (`validate_model()`) will return `False`

### 9. OpenFGA hardcoded credentials

**Status: CONFIRMED at exact lines:**

- `docker-compose.yml:113`: `OPENFGA_DATASTORE_URI=postgres://openfga:openfga@openfga-postgres:5432/openfga?sslmode=disable` (openfga-migrate service)
- `docker-compose.yml:201`: `OPENFGA_DATASTORE_URI=postgres://openfga:openfga@openfga-postgres:5432/openfga?sslmode=disable` (openfga service)
- `docker-compose.yml:346-348`: `POSTGRES_USER=openfga`, `POSTGRES_PASSWORD=openfga` (openfga-postgres service)
- `docker-compose.yml:206`: `OPENFGA_AUTHN_PRESHARED_KEYS=dev-key-siopv-local-1` (hardcoded insecure API key)

All four are acknowledged with PRODUCTION/WARNING comments in the file, but remain hardcoded defaults.

### 10. Integration tests skip condition

**Status: CONFIRMED**

`tests/integration/test_openfga_real_server.py:32`:
```python
pytestmark = pytest.mark.skipif(
    not OPENFGA_API_URL,
    reason="SIOPV_OPENFGA_API_URL not set - real OpenFGA server not available",
)
```

Where `OPENFGA_API_URL = os.getenv("SIOPV_OPENFGA_API_URL")` (line 30). These tests skip whenever the env var is unset, which is always true in CI unless explicitly configured. The "integration" tests in `tests/integration/test_authorization_integration.py` use mocks and do NOT skip.

### 11. DI wiring for auth

**Status: CONFIRMED EXPORTED**

`infrastructure/di/__init__.py` exports:
- `get_authorization_port` ✅
- `get_authorization_store_port` ✅
- `get_authorization_model_port` ✅
- `create_authorization_adapter` ✅

The DI module is properly wired. However, DI coverage is 0% (`src/siopv/infrastructure/di/__init__.py` at 0%, `authorization.py` at 0%), meaning these factories are never exercised in the test suite.

### 12. Missing error handling for OpenFGA unreachable

**Status: PARTIALLY MITIGATED via circuit breaker and fail-secure**

When OpenFGA is unreachable:
- `OpenFGAAdapter.check()` raises `AuthorizationCheckError` (wrapped in circuit breaker logic)
- `authorization_node._execute_authorization_check()` calls `_run_authorization_check()` which calls `asyncio.run(port.check(context))`
- If `port.check()` raises `AuthorizationCheckError`, it is caught at `authorization_node.py:349` and returns `_create_error_state("Authorization check failed: service error")` with `authorization_allowed=False`
- This triggers `route_after_authorization` to return `"end"`, halting the pipeline

**Fail-secure behavior IS implemented correctly.** However, there is a gap: if `asyncio.run()` itself raises `RuntimeError` (event loop collision), this is caught by the bare `except Exception` at line 357, which also returns a denial state. The error message is generic ("Authorization node error: unexpected failure") and does not distinguish between an unreachable service and a programming error.

---

## Ruff Check Result

```
cd ~/siopv && uv run ruff check src/siopv/application/orchestration/
All checks passed!
```

No ruff violations in the orchestration module.

---

## Summary Statistics

| Category | Count |
|----------|-------|
| CRITICAL findings | 1 |
| HIGH findings | 8 |
| MEDIUM findings | 7 |
| LOW findings | 4 |
| **Total** | **20** |

| Phase | Coverage | Status |
|-------|----------|--------|
| authorization_node.py | 30% | Inadequate |
| graph.py | 25% | Inadequate |
| edges.py | 17% | Inadequate |
| enrich_node.py | 18% | Inadequate |
| escalate_node.py | 16% | Inadequate |
| classify_node.py | 15% | Inadequate |
| dlp_node.py | 32% | Inadequate |
| ingest_node.py | 82% | Acceptable |
| state.py | 79% | Acceptable |

---

**Report saved:** `~/siopv/.ignorar/production-reports/audit-2026-03-05/phase-4-5-audit.md`
**Audit completed:** 2026-03-05
