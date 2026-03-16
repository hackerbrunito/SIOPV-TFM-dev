# SIOPV Phase 6 + Cross-cutting Audit Report

**Date:** 2026-03-05
**Auditor:** Read-only audit (no code changes)
**Scope:** Phase 6 (DLP/Presidio) + CLI, DI container, empty adapter stubs, test health
**Target:** `~/siopv/`

---

## Executive Summary

- **DI container is critically incomplete:** `infrastructure/di/__init__.py` exports only authentication and authorization functions — `get_dlp_port()` and `get_dual_layer_dlp_port()` exist in `di/dlp.py` but are not re-exported, meaning no other module can import them from the canonical DI entrypoint. Coverage on `di/dlp.py` is 0%.
- **`dlp_node` uses `asyncio.run()` at line 106**, which will raise `RuntimeError: This event loop is already running` when called inside an async LangGraph runner, silently breaking the DLP layer.
- **Three major components are hollow stubs:** CLI (`process_report`, `dashboard`, `train_model`), and the three adapter directories (`llm/`, `notification/`, `persistence/`) contain zero implementation code; the CLI is also at 0% test coverage.

---

## Findings Table

### Phase 6 Issues

| # | Severity | File:Line | Issue | Recommended Fix |
|---|----------|-----------|-------|-----------------|
| 1 | CRITICAL | `application/orchestration/nodes/dlp_node.py:106` | `asyncio.run(_run_dlp_for_vulns(...))` — will raise `RuntimeError: This event loop is already running` when `dlp_node` is called inside an async LangGraph execution context. Two test warnings confirm the coroutine is never awaited correctly. | Replace with `await _run_dlp_for_vulns(...)` and make `dlp_node` an `async def`. Mirror pattern from `enrich_node`. |
| 2 | HIGH | `infrastructure/di/__init__.py` (entire file) | `get_dlp_port()` and `get_dual_layer_dlp_port()` are defined in `di/dlp.py` but NOT imported or exported from `di/__init__.py`. The canonical DI entrypoint exports only authentication and authorization symbols. Any code attempting `from siopv.infrastructure.di import get_dlp_port` will raise `ImportError`. | Add import block to `di/__init__.py`: `from siopv.infrastructure.di.dlp import (get_dlp_port, get_dual_layer_dlp_port)` and add both to `__all__`. |
| 3 | HIGH | `infrastructure/di/dlp.py:1-128` | 0% test coverage (33 statements, 33 missed per coverage report). No test file exists for DLP DI. The DI wiring that connects Settings → PresidioAdapter → DLPPort has never been exercised. | Create `tests/unit/infrastructure/di/test_dlp_di.py` covering `get_dlp_port()`, `get_dual_layer_dlp_port()`, `create_presidio_adapter()`, and `create_dual_layer_dlp_adapter()`. |
| 4 | MEDIUM | `adapters/dlp/presidio_adapter.py:232` | `haiku_model: str = "claude-haiku-4-5-20251001"` — hardcoded model ID as constructor default. If the model is retired or renamed, every `PresidioAdapter` instantiated without an explicit override will silently use a stale model. | Default should be `""` or `None`; require callers to supply the model from `settings.claude_haiku_model`. The DI factory (`di/dlp.py:37`) already reads from Settings — the fix is to eliminate the hardcoded default at the constructor level. |
| 5 | MEDIUM | `adapters/dlp/haiku_validator.py:63` | `model: str = "claude-haiku-4-5-20251001"` — same hardcoded model ID in `HaikuSemanticValidatorAdapter.__init__`. | Same fix as #4: remove default or source from settings constant. |
| 6 | MEDIUM | `adapters/dlp/dual_layer_adapter.py:79,282` | Two hardcoded occurrences: `_HaikuDLPAdapter.__init__` (line 79) and `create_dual_layer_adapter()` factory signature (line 282) both default to `"claude-haiku-4-5-20251001"`. | Same pattern: source from settings constant or make required. |
| 7 | LOW | `application/use_cases/sanitize_vulnerability.py` | `SanitizeVulnerabilityUseCase` is fully implemented and tested (100% coverage per report) but is **dead code in the graph** — `dlp_node` calls `dlp_port.sanitize()` directly, bypassing the use case entirely. The use case is not imported or called from any graph node, graph wiring, or DI container. | Either wire `SanitizeVulnerabilityUseCase` into `dlp_node` (replacing the inline `_run_dlp_for_vulns` logic), or delete the use case and its tests. Current state is maintained duplication. |

### CLI / Cross-cutting Issues

| # | Severity | File:Line | Issue | Recommended Fix |
|---|----------|-----------|-------|-----------------|
| 8 | HIGH | `interfaces/cli/main.py:59,72,98` | `process_report()`, `dashboard()`, and `train_model()` are pure stubs with `# TODO` comments. None call `run_pipeline()`, any use case, or any DI factory. The CLI is the primary user entry point for the system; it is entirely non-functional. Coverage is 0% (34 statements, 34 missed). | Implement Phase 7/8 wiring: `process_report` should call `run_pipeline()`, `dashboard` should launch Streamlit, `train_model` should call the ML training use case. |
| 9 | HIGH | `adapters/llm/__init__.py`, `adapters/notification/__init__.py`, `adapters/persistence/__init__.py` | All three adapter directories contain only an empty `__init__.py`. `adapters/llm/` should contain a real Claude adapter (the current "LLM confidence" is pure math per the audit memory). `adapters/notification/` should have email/Slack. `adapters/persistence/` should have SQLite polling. None have any implementation. | Implement as planned for Phases 7–8. Mark clearly as "not yet implemented" in any Phase 6-or-earlier documentation. |
| 10 | MEDIUM | `infrastructure/logging/setup.py:31` | `structlog.processors.format_exc_info` is a deprecated function-based processor. structlog raises `UserWarning: Remove format_exc_info from your processor chain if you want pretty exceptions.` on every test run (confirmed in warnings output). | Replace line 31 with `structlog.processors.ExceptionRenderer()` (class-based, current API). |
| 11 | MEDIUM | `infrastructure/di/__init__.py` | **DI export coverage audit:** The DI package exports only Phase 5 (authentication, authorization) components. Missing: `get_dlp_port`, `get_dual_layer_dlp_port` (Phase 6). There are no DI factories for ingestion, enrichment, classification, or ML (Phases 1–3). This is a structural gap that will surface as the graph builder needs to wire all nodes. | Add DLP exports immediately (see #2). Plan DI factories for remaining phases before Phase 8. |
| 12 | LOW | `application/orchestration/nodes/authorization_node.py:194` and `nodes/enrich_node.py:73` | Both nodes also use `asyncio.run()` (same pattern as `dlp_node`). Not in scope for this Phase 6 audit, but the same `RuntimeError` risk applies to all three nodes. | Confirmed existing HIGH finding from prior audit — track together with #1 above. |

---

## Test Health Summary

**Test run:** `uv run pytest tests/ -q --tb=no`

| Metric | Value |
|--------|-------|
| Passed | **1,404** |
| Skipped | **12** |
| Failed | **0** |
| Warnings | **5** |
| Duration | ~67 seconds |

**Overall coverage:** 83%

**Key coverage gaps:**

| Module | Coverage | Notes |
|--------|----------|-------|
| `infrastructure/di/dlp.py` | **0%** | 33/33 statements uncovered. No test file exists. |
| `interfaces/cli/main.py` | **0%** | 34/34 statements uncovered. CLI is hollow stubs. |
| `adapters/llm/__init__.py` | 100% | Trivially — file is empty (0 statements). |
| `adapters/notification/__init__.py` | 100% | Trivially — file is empty (0 statements). |
| `adapters/persistence/__init__.py` | 100% | Trivially — file is empty (0 statements). |
| `application/use_cases/sanitize_vulnerability.py` | 100% | Use case is fully tested but dead in the graph. |

**Warnings detail:**

1. `RuntimeWarning: coroutine '_run_dlp_for_vulns' was never awaited` — direct consequence of `asyncio.run()` in `dlp_node` (Finding #1). Tests are patching around it but the runtime warning leaks through.
2. `RuntimeWarning: coroutine '_run_enrichment' was never awaited` — same pattern in `enrich_node`.
3. `UserWarning: Remove format_exc_info from your processor chain` — structlog deprecation in `setup.py` (Finding #10).

---

## Detailed Evidence

### Finding #1: asyncio.run() in dlp_node (CRITICAL)

`/Users/bruno/siopv/src/siopv/application/orchestration/nodes/dlp_node.py`, line 106:
```python
per_cve = asyncio.run(_run_dlp_for_vulns(vulnerabilities, dlp_port))
```
`_run_dlp_for_vulns` is an `async def`. LangGraph runs nodes inside an async event loop. Calling `asyncio.run()` from within a running event loop raises `RuntimeError: This event loop is already running`. The test warning "coroutine '_run_dlp_for_vulns' was never awaited" confirms the mock is bypassing this but production will fail.

### Finding #2: DI __init__.py missing DLP exports

`/Users/bruno/siopv/src/siopv/infrastructure/di/__init__.py` exports:
- `create_authorization_adapter` ✅
- `create_oidc_adapter` ✅
- `create_oidc_middleware` ✅
- `get_authorization_model_port` ✅
- `get_authorization_port` ✅
- `get_authorization_store_port` ✅
- `get_oidc_authentication_port` ✅
- `get_dlp_port` ❌ MISSING
- `get_dual_layer_dlp_port` ❌ MISSING

Both functions exist fully implemented in `di/dlp.py` (lines 56 and 105) but are not surfaced.

### Finding #4–6: Hardcoded model IDs

| File | Line | Hardcoded default |
|------|------|-------------------|
| `adapters/dlp/presidio_adapter.py` | 232 | `haiku_model: str = "claude-haiku-4-5-20251001"` |
| `adapters/dlp/haiku_validator.py` | 63 | `model: str = "claude-haiku-4-5-20251001"` |
| `adapters/dlp/dual_layer_adapter.py` | 79 | `model: str = "claude-haiku-4-5-20251001"` |
| `adapters/dlp/dual_layer_adapter.py` | 282 | `haiku_model: str = "claude-haiku-4-5-20251001"` (factory sig) |

Note: `settings.claude_haiku_model` in `infrastructure/config/settings.py:33` ALSO hardcodes `"claude-haiku-4-5-20251001"` as the default — this is the actual single source of truth that the DI factory reads, but the adapters bypass it with independent defaults.

### Finding #7: SanitizeVulnerabilityUseCase orphaned

Grep confirms `SanitizeVulnerabilityUseCase` is referenced only in its own file:
- `application/use_cases/sanitize_vulnerability.py` (definition + `__all__`)
- `tests/unit/application/test_sanitize_vulnerability.py` (test file)

It is NOT imported in: `di/__init__.py`, `di/dlp.py`, `nodes/dlp_node.py`, `graph.py`, or any other graph wiring code. The graph uses `dlp_node` which calls `dlp_port.sanitize()` directly via `_run_dlp_for_vulns()`.

### Finding #8: CLI hollow stubs

Lines with `# TODO`:
- `main.py:59` — `# TODO: Implement ingestion pipeline`
- `main.py:71` — `# TODO: Implement Streamlit launcher`
- `main.py:97` — `# TODO: Implement model training`

None of the three commands call any use case, DI factory, or `run_pipeline()`.

### Finding #10: structlog format_exc_info deprecation

`infrastructure/logging/setup.py:31`:
```python
structlog.processors.format_exc_info,
```
This is the deprecated function-based form. The warning from structlog itself reads:
> `UserWarning: Remove format_exc_info from your processor chain if you want pretty exceptions.`
Confirmed firing on every test run.

---

## Summary by Priority

| Priority | Count | Items |
|----------|-------|-------|
| CRITICAL | 1 | asyncio.run() in dlp_node (#1) |
| HIGH | 4 | DLP DI not exported (#2), DLP DI 0% coverage (#3), CLI hollow (#8), empty adapter dirs (#9) |
| MEDIUM | 4 | Hardcoded model IDs (#4, #5, #6), structlog deprecation (#10), DI export audit (#11) |
| LOW | 2 | SanitizeVulnerabilityUseCase orphaned (#7), asyncio.run() in other nodes (#12) |

**Must fix before Phase 7:** #1 (asyncio.run), #2 (DI exports), #8 (CLI) — these block any production-grade execution.
