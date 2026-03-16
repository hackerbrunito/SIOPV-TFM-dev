# application-import-auditor Report

**Date:** 2026-03-11 15:59:38
**Scope:** `/Users/bruno/siopv/src/siopv/application/**/*.py`
**Prohibited patterns:** `from siopv.adapters`, `from siopv.infrastructure`, `import siopv.adapters`, `import siopv.infrastructure`

## Summary: 2 violations found

Both violations are direct imports from `siopv.adapters` in application use cases — the application layer directly depends on adapter implementations instead of going through ports.

## Violations

| # | File | Line | Import | Severity |
|---|------|------|--------|----------|
| 1 | `application/use_cases/ingest_trivy.py` | 17 | `from siopv.adapters.external_apis.trivy_parser import TrivyParser` | CRITICAL — application directly instantiates adapter class |
| 2 | `application/use_cases/classify_risk.py` | 18 | `from siopv.adapters.ml.feature_engineer import FeatureEngineer` | CRITICAL — application directly instantiates adapter class |

### Violation 1: `ingest_trivy.py:17`

```python
from siopv.adapters.external_apis.trivy_parser import TrivyParser
```

The use case imports `TrivyParser` directly from the adapters layer. This should be abstracted behind a port (e.g., `TrivyParserPort` in `application/ports/`) and injected via dependency inversion.

### Violation 2: `classify_risk.py:18`

```python
from siopv.adapters.ml.feature_engineer import FeatureEngineer
```

The use case imports `FeatureEngineer` directly from the adapters layer. Notably, the same file already uses a port correctly for the ML classifier (`MLClassifierPort` under `TYPE_CHECKING`), but `FeatureEngineer` bypasses this pattern. This should also be abstracted behind a port.

## Clean files (no violations)

All other `.py` files under `application/` have no prohibited imports from `siopv.adapters` or `siopv.infrastructure`. No `infrastructure` imports were found anywhere in the application layer.

## Notes

- Zero `siopv.infrastructure` imports found — infrastructure coupling is clean.
- Both violations are `siopv.adapters` imports in use case files, both CRITICAL severity.
- `classify_risk.py` is inconsistent: it correctly uses a port for `MLClassifierPort` but directly imports `FeatureEngineer` from adapters.
