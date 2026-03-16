# STAGE-2 Round 1 Aggregated Report — Layer Boundary Violation Detection

## Executive Summary

Round 1 audited the SIOPV hexagonal architecture across 4 dimensions: domain purity, application imports, port definitions, and adapter conformance. **2 CRITICAL violations** were found in the application layer (direct adapter imports), plus **1 PARTIAL conformance** in the adapters layer (implicit Protocol subtyping). The domain layer and all 6 port definitions are fully clean.

## Findings by Agent

### domain-import-auditor — PASS (0 violations)

- All 20 files in `src/siopv/domain/` are clean
- Zero imports from `siopv.adapters`, `siopv.infrastructure`, or `siopv.interfaces`
- No imports from `siopv.application` (not even ports)
- Domain layer is fully self-contained per hexagonal architecture principles

### application-import-auditor — FAIL (2 CRITICAL violations)

- `application/use_cases/ingest_trivy.py:17` imports `TrivyParser` directly from `siopv.adapters.external_apis.trivy_parser` — should be behind a port
- `application/use_cases/classify_risk.py:18` imports `FeatureEngineer` directly from `siopv.adapters.ml.feature_engineer` — should be behind a port
- `classify_risk.py` is inconsistent: correctly uses `MLClassifierPort` for the classifier but bypasses port pattern for `FeatureEngineer`
- Zero `siopv.infrastructure` imports found — infrastructure coupling is clean
- Both violations are the same pattern: application use case directly instantiating an adapter class

### ports-purity-auditor — PASS (6/6 ports PURE)

- All 6 port files are pure abstract interfaces with no concrete imports
- 3 ports use `Protocol` (authorization, dlp, oidc_authentication), 3 use `ABC` (enrichment_clients, ml_classifier, vector_store)
- All domain-type imports are guarded behind `TYPE_CHECKING` (zero runtime cost)
- No imports from `siopv.adapters`, `siopv.infrastructure`, or any third-party library
- All `__all__` exports are correctly defined

### adapters-conformance-auditor — PASS with 1 PARTIAL (4 CONFORMANT, 1 PARTIAL)

- **CONFORMANT:** `openfga_adapter.py`, `nvd_client.py`, `xgboost_classifier.py`, `chroma_adapter.py` — all explicitly inherit from their ports
- **PARTIAL:** `dual_layer_adapter.py` — does NOT explicitly inherit from `DLPPort`; relies on structural subtyping (valid per PEP 544 but weakens contract visibility and mypy enforcement)
- No cross-adapter-package dependencies found in any of the 5 files
- External library encapsulation is excellent — no SDK types leak into public method signatures
- Infrastructure imports (`CircuitBreaker`, `Settings`, rate limiters) are used appropriately

## Consolidated Violation List

| # | Severity | File | Issue | Agent |
|---|----------|------|-------|-------|
| 1 | CRITICAL | `application/use_cases/ingest_trivy.py:17` | Direct import of `TrivyParser` from `siopv.adapters` — bypasses port abstraction | application-import-auditor |
| 2 | CRITICAL | `application/use_cases/classify_risk.py:18` | Direct import of `FeatureEngineer` from `siopv.adapters` — bypasses port abstraction | application-import-auditor |
| 3 | MEDIUM | `adapters/dlp/dual_layer_adapter.py` | No explicit `DLPPort` inheritance — relies on implicit structural subtyping | adapters-conformance-auditor |

## Items Requiring Round 2 Investigation

1. **DI wiring for TrivyParser** — How is `TrivyParser` currently injected into `IngestTrivyUseCase`? Is it instantiated inside the use case or passed from the DI container? The fix (creating a `TrivyParserPort`) will require DI container changes.

2. **DI wiring for FeatureEngineer** — Same question for `FeatureEngineer` in `ClassifyRiskUseCase`. Need to verify whether the DI container (`infrastructure/di/`) already has a factory for this or if it's hardcoded.

3. **DLPPort structural subtyping** — Verify whether mypy currently catches `DualLayerDLPAdapter` as satisfying `DLPPort`. Check if there's a `runtime_checkable` assertion or DI registration that validates conformance. If not, the implicit contract could silently break on port changes.

4. **Missing ports gap** — The 2 CRITICAL violations suggest there may be missing port definitions (`TrivyParserPort`, `FeatureEngineerPort`). Round 2 should verify whether these ports need to be created.
