# STAGE-2 Final Report — Hexagonal Quality Audit

## Date: 2026-03-11

## Scope: Phases 0–6 ONLY

## Executive Summary

STAGE-2 audited the SIOPV hexagonal architecture across two rounds: Round 1 examined layer boundary purity (domain imports, application imports, port definitions, adapter conformance) while Round 2 examined DI wiring integrity (DI containers, node injection, graph wiring). A total of **34 files** were audited across **7 specialized agents**.

The audit found **7 violations total**: 2 CRITICAL, 1 HIGH, 2 MEDIUM, 1 MEDIUM (partial conformance), and 1 LOW. The **domain layer is pristine** — zero outward imports across all 20 files. All **6 port definitions are pure abstract interfaces** with no concrete dependencies. The **DI container design is sound** — factory functions return port types, use `@lru_cache` singletons, and inject settings cleanly.

However, two systemic issues undermine the architecture: (1) **two application use cases bypass the port pattern** by importing adapters directly (`TrivyParser`, `FeatureEngineer`), and (2) **the CLI entry point does not wire any DI adapters**, leaving all 8 ports as `None` at runtime. This means the pipeline runs structurally but performs no real enrichment, authorization, DLP, or classification. These two issues are the highest priority fixes before Phase 7.

**Key strengths:** Domain purity, port abstraction quality, adapter encapsulation of external SDKs, and the `PipelineGraphBuilder` constructor injection pattern. **Key weaknesses:** Incomplete port coverage for 2 adapters and total DI bypass at the CLI entry point.

## Full Violation List

| # | Severity | File | Issue | Layer | For REMEDIATION-HARDENING |
|---|----------|------|-------|-------|--------------------------|
| 1 | CRITICAL | `application/use_cases/ingest_trivy.py:17` | Direct import of `TrivyParser` from `siopv.adapters` — bypasses port abstraction | Application | Create `TrivyParserPort`, inject via DI |
| 2 | CRITICAL | `application/use_cases/classify_risk.py:18` | Direct import of `FeatureEngineer` from `siopv.adapters` — bypasses port abstraction | Application | Create `FeatureEngineerPort`, inject via DI |
| 3 | HIGH | `interfaces/cli/main.py` | CLI calls `run_pipeline()` without wiring any of the 8 DI adapter ports — all default to `None` | Interfaces/CLI | Wire DI factories (`get_*_port()`) in CLI before calling `run_pipeline()` |
| 4 | MEDIUM | `adapters/dlp/dual_layer_adapter.py` | No explicit `DLPPort` inheritance — relies on implicit structural subtyping (PEP 544) | Adapters | Add explicit `DLPPort` inheritance for contract visibility |
| 5 | MEDIUM | `infrastructure/di/authorization.py` | 3 separate `OpenFGAAdapter` instances created (uncached factory) — separate HTTP pools and circuit breaker state | Infrastructure/DI | Cache `create_authorization_adapter()` with `@lru_cache` |
| 6 | MEDIUM | `application/orchestration/ingest_node.py` | `IngestTrivyReportUseCase()` directly instantiated without DI — breaks consistent injection pattern | Application/Nodes | Inject use case or its port dependencies via node closure |
| 7 | LOW | `application/orchestration/edges.py` | `calculate_batch_discrepancies()` contains domain-level adaptive threshold policy — design smell | Application/Nodes | Extract threshold logic to a domain service (non-blocking) |

## Layer Health Assessment

| Layer | Status | Notes |
|-------|--------|-------|
| Domain | ✅ CLEAN | 20/20 files pure. Zero outward imports. Fully self-contained. |
| Application/Ports | ✅ CLEAN | 6/6 ports are pure abstract interfaces. No concrete imports. `TYPE_CHECKING` guards used correctly. |
| Application/Use Cases | ⚠️ ISSUES | 2 CRITICAL violations — `ingest_trivy.py` and `classify_risk.py` import adapters directly. |
| Application/Nodes | ⚠️ ISSUES | 4/5 nodes follow DI pattern. `ingest_node.py` directly instantiates use case. `edges.py` has domain logic leak. |
| Adapters | ⚠️ MINOR | 4/5 adapters explicitly inherit ports. `dual_layer_adapter.py` uses implicit subtyping. External SDK encapsulation is excellent. |
| Infrastructure/DI | ⚠️ MINOR | Well-designed factories. One uncached factory creates redundant `OpenFGAAdapter` instances. |
| Interfaces/CLI | ⚠️ ISSUES | `process_report` implemented but completely bypasses DI wiring — no adapters connected at runtime. |

## STAGE-1 Known Issues — Updated Status

| # | Issue | STAGE-2 Status |
|---|-------|----------------|
| 1 | CLI hollow / stubs | **PARTIALLY RESOLVED** — `process_report` is implemented but doesn't wire DI adapters; `dashboard` remains Phase 7 stub |
| 2 | SanitizeVulnerabilityUseCase orphaned | **Not examined** — outside STAGE-2 scope (no agent covered this use case) |
| 3 | LLM confidence heuristic | **Not examined** — deferred to Phase 7 (EXPECTED-MISSING per scope rule) |
| 4 | run_pipeline drops enrichment clients | **RESOLVED** — signature now accepts all 8 ports and forwards to `PipelineGraphBuilder` |
| 5 | DLP DI not exported | **RESOLVED** — both `get_dlp_port` and `get_dual_layer_dlp_port` present in `__init__.py` exports and `__all__` |
| 6 | Hardcoded Haiku model IDs | **Outside DI scope** — DI reads from `settings.claude_haiku_model`; defaults may be hardcoded in `Settings` class. Needs Phase 7 review. |
| 7 | asyncio.run() in sync nodes | **CLARIFIED** — no node file uses `asyncio.run()`; issue resides in CLI entry point, not in orchestration nodes |
| 8 | No tests for Phase 2 adapters | **Not examined** — outside STAGE-2 scope |
| 9 | structlog deprecation | **Not examined** — outside STAGE-2 scope |

## REMEDIATION-HARDENING Priority List

1. **[CRITICAL] Create `TrivyParserPort`** — Define port in `application/ports/`, refactor `ingest_trivy.py` to accept it via constructor injection, add DI factory in `infrastructure/di/`
2. **[CRITICAL] Create `FeatureEngineerPort`** — Define port in `application/ports/`, refactor `classify_risk.py` to accept it via constructor injection, add DI factory in `infrastructure/di/`
3. **[HIGH] Wire DI in CLI** — Modify `cli/main.py:process_report` to call all `get_*_port()` factories and pass the 8 adapters to `run_pipeline()`. This is the single highest-impact fix: without it, the entire pipeline runs with `None` adapters.
4. **[MEDIUM] Add explicit `DLPPort` inheritance** — Modify `dual_layer_adapter.py` to explicitly inherit from `DLPPort` for contract visibility and stronger mypy enforcement
5. **[MEDIUM] Cache OpenFGA adapter factory** — Add `@lru_cache(maxsize=1)` to `create_authorization_adapter()` in `authorization.py` to prevent 3 redundant adapter instances
6. **[MEDIUM] Fix `ingest_node.py` DI** — Refactor to inject `IngestTrivyReportUseCase` dependencies through the node closure, matching the pattern used by the other 4 nodes
7. **[LOW] Extract threshold logic from `edges.py`** — Move `calculate_batch_discrepancies()` adaptive threshold policy to a domain service. Non-blocking; design smell only.

## What is Working Well

- **Domain layer purity is exemplary** — 20 files with zero outward dependencies, fully self-contained value objects and entities
- **Port definitions are textbook hexagonal** — all 6 ports are pure abstract interfaces with `TYPE_CHECKING` guards, clean `__all__` exports, and no concrete imports
- **Adapter SDK encapsulation is excellent** — no external library types leak into public method signatures; all adapters properly wrap third-party SDKs behind clean interfaces
- **`PipelineGraphBuilder` follows constructor injection perfectly** — accepts all 8 ports, creates node closures that capture injected dependencies, and `run_pipeline()` signature matches the builder 1:1
- **DI container design is sound** — factory functions consistently return port types, use `@lru_cache` singletons, and read configuration from `Settings` without hardcoded values
