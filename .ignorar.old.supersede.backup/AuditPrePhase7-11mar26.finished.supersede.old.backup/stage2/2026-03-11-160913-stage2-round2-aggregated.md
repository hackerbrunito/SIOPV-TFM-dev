# STAGE-2 Round 2 Aggregated Report — DI & Wiring Audit

## Executive Summary

Round 2 audited 14 files across DI containers, orchestration nodes, and graph wiring. The audit found **1 VIOLATION** (CLI does not wire DI adapters — all 8 ports default to `None`), **2 PARTIAL** findings (multiple OpenFGA adapter instances in DI, domain logic in edge routing), and **10 CORRECT** assessments. The DI infrastructure is well-designed but the entry point (CLI) completely bypasses it, meaning the pipeline runs structurally with no real adapters connected.

## Findings by Agent

### di-container-auditor — 3 CORRECT, 1 PARTIAL

- **4 DI files audited** (`__init__.py`, `authentication.py`, `authorization.py`, `dlp.py`)
- All factory functions return port interfaces, use `@lru_cache(maxsize=1)` singletons, and inject settings without hardcoded values
- **PARTIAL:** `authorization.py` creates up to **3 separate `OpenFGAAdapter` instances** (one per port function) because `create_authorization_adapter()` is not cached — separate HTTP pools, separate circuit breaker state
- Finding #5 (DLP exports): **RESOLVED** — both `get_dlp_port` and `get_dual_layer_dlp_port` present in `__init__.py` exports
- Finding #6 (Hardcoded model IDs): **Not in DI scope** — DI reads `settings.claude_haiku_model`, defaults may be in `Settings` class

### node-injection-auditor — 4 INJECTED, 1 DIRECT_INSTANTIATION

- **5 node files audited** — 4/5 follow consistent DI pattern (ports as `Optional` keyword args)
- **DIRECT_INSTANTIATION:** `ingest_node.py` instantiates `IngestTrivyReportUseCase()` directly with no injected dependencies — breaks the consistent DI pattern
- **Import hygiene is clean** across all 5 nodes: only `siopv.domain` and `siopv.application` imports, no adapter/infrastructure imports
- Finding #7 (asyncio.run() in sync nodes): **NOT PRESENT** in any node file — the issue resides in the CLI, not in nodes
- Use case instantiation within nodes (classify, enrich) is acceptable since injected ports are passed through

### graph-wiring-auditor — 3 CORRECT, 1 PARTIAL, 1 VIOLATION

- **`graph.py` — CORRECT:** `PipelineGraphBuilder` uses constructor injection for all 8 ports; node closures capture injected dependencies; `run_pipeline()` signature matches builder 1:1
- **`edges.py` — PARTIAL:** Routing functions are correctly placed, but `calculate_batch_discrepancies()` contains domain-level adaptive threshold logic that would be better in a domain service
- **`cli/main.py` — VIOLATION:** `process_report` calls `run_pipeline()` with only 3 args (`report_path`, `user_id`, `project_id`), leaving **all 8 adapter ports as `None`**. The DI container exists but the CLI completely bypasses it
- Finding #1 (CLI stubs): **PARTIALLY RESOLVED** — `process_report` is implemented but doesn't wire adapters; `dashboard` remains Phase 7 stub
- Finding #4 (run_pipeline drops clients): **RESOLVED** — signature now accepts all 8 ports and forwards to builder

## Consolidated Violation List

| # | Severity | File | Issue | Agent |
|---|----------|------|-------|-------|
| 1 | **HIGH** | `cli/main.py` | CLI calls `run_pipeline()` without wiring any of the 8 DI adapter ports — all default to `None`, no real enrichment/auth/DLP/classification occurs | graph-wiring-auditor |
| 2 | **MEDIUM** | `authorization.py` | 3 separate `OpenFGAAdapter` instances created (uncached factory) — separate HTTP pools and circuit breaker state | di-container-auditor |
| 3 | **MEDIUM** | `ingest_node.py` | `IngestTrivyReportUseCase()` directly instantiated without DI — breaks consistent injection pattern across nodes | node-injection-auditor |
| 4 | **LOW** | `edges.py` | `calculate_batch_discrepancies()` contains domain-level adaptive threshold policy — design smell, not broken dependency | graph-wiring-auditor |

## STAGE-1 Known Issue Status Updates

| Finding # | Description | Status |
|-----------|-------------|--------|
| #1 | CLI hollow / stubs | **PARTIALLY RESOLVED** — `process_report` implemented but doesn't wire DI adapters; `dashboard` remains Phase 7 stub |
| #4 | run_pipeline drops enrichment clients | **RESOLVED** — signature accepts all 8 ports and forwards to `PipelineGraphBuilder` |
| #5 | DLP DI not exported | **RESOLVED** — both factories in `__init__.py` imports and `__all__` |
| #6 | Hardcoded Haiku model IDs | **Outside DI scope** — DI reads from settings; defaults may be hardcoded in `Settings` class |
| #7 | asyncio.run() in sync nodes | **NOT in nodes** — no node uses `asyncio.run()`; issue confirmed to reside in CLI entry point |
