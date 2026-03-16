# domain-import-auditor Report

**Auditor:** domain-import-auditor
**Team:** siopv-stage2
**Timestamp:** 2026-03-11 15:59:35
**Scope:** All Python files in `src/siopv/domain/`

## Summary: 0 violations found

The domain layer is clean. No prohibited imports from `siopv.adapters`, `siopv.infrastructure`, `siopv.interfaces`, or non-ports `siopv.application` were found in any of the 20 domain files.

## Violations

| File | Line | Import | Severity |
|------|------|--------|----------|
| *(none)* | — | — | — |

## Searches Performed

| Pattern | Result |
|---------|--------|
| `from siopv.adapters` | No matches |
| `from siopv.infrastructure` | No matches |
| `from siopv.interfaces` | No matches |
| `import siopv.adapters` | No matches |
| `import siopv.infrastructure` | No matches |
| `import siopv.interfaces` | No matches |
| `from siopv.application` (non-ports) | No matches |

## Clean Files (no violations)

All 20 files in `src/siopv/domain/` are clean:

- `__init__.py`
- `constants.py`
- `exceptions.py`
- `services/__init__.py`
- `entities/__init__.py`
- `entities/ml_feature_vector.py`
- `value_objects/__init__.py`
- `value_objects/enrichment.py`
- `value_objects/risk_score.py`
- `authorization/__init__.py`
- `authorization/entities.py`
- `authorization/exceptions.py`
- `authorization/value_objects.py`
- `oidc/__init__.py`
- `oidc/exceptions.py`
- `oidc/value_objects.py`
- `privacy/__init__.py`
- `privacy/entities.py`
- `privacy/exceptions.py`
- `privacy/value_objects.py`

## Conclusion

The domain layer correctly follows hexagonal architecture principles — it has zero dependencies on outer layers (adapters, infrastructure, interfaces) and no imports from application layer (not even ports). The domain is fully self-contained.
