# Remediation Report: Hex #2 — classify_risk.py FeatureEngineer Adapter Import

**Date:** 2026-03-15
**Issue:** Stage 2 Hexagonal Violation #2 — `application/use_cases/classify_risk.py:18` imported `FeatureEngineer` directly from `siopv.adapters.ml.feature_engineer`
**Status:** ✅ RESOLVED

---

## Changes Made

### 1. Created `src/siopv/application/ports/feature_engineering.py`
New `@runtime_checkable` Protocol port:
- `FeatureEngineerPort.extract_features(vulnerability, enrichment) -> MLFeatureVector`
- Uses `TYPE_CHECKING` guard for domain imports
- Follows `dlp.py` Protocol pattern

### 2. Updated `src/siopv/application/ports/__init__.py`
- Added `from siopv.application.ports.feature_engineering import FeatureEngineerPort`
- Added `"FeatureEngineerPort"` to `__all__`

### 3. Modified `src/siopv/application/use_cases/classify_risk.py`
- Removed module-level `from siopv.adapters.ml.feature_engineer import FeatureEngineer`
- Added `FeatureEngineerPort` to `TYPE_CHECKING` guard
- Changed `feature_engineer: FeatureEngineer | None = None` → `feature_engineer: FeatureEngineerPort | None = None`
- Removed `or FeatureEngineer()` fallback — now requires explicit injection
- Added `assert self._feature_engineer is not None` guard in `execute()` (mypy compliance)
- Factory `create_classify_risk_use_case()` updated with same type change

### 4. Updated `tests/unit/application/test_classify_risk.py`
- Added `mock_feature_engineer` fixture (MagicMock spec=FeatureEngineerPort)
- Updated 4 test methods to inject `feature_engineer=mock_feature_engineer`

---

## Verification

| Check | Result |
|-------|--------|
| `grep "from siopv.adapters" classify_risk.py` | ✅ 0 matches |
| `ruff check` | ✅ All checks passed |
| `mypy classify_risk.py ports/feature_engineering.py` | ✅ Success: no issues |
| `pytest tests/unit/application/test_classify_risk.py` | ✅ 34 passed |
| `pytest tests/unit/application/` (excl. pre-existing edge failure) | ✅ 207 passed |

**Pre-existing failure:** `test_edges.py::TestCalculateDiscrepancy::test_calculate_basic_discrepancy` — `ThresholdConfig` NameError in `discrepancy.py`. Unrelated to this fix.
