# Constants Extractor Report
**Date:** 2026-02-10
**Task:** Extract magic values to constants.py
**Agent:** constants-extractor
**Status:** ✅ COMPLETED

---

## Summary

Successfully extracted all magic values from source code to a centralized constants module and configured per-file-ignores for ML naming conventions.

### Metrics
- **PLR2004 violations fixed:** 8 → 0
- **N803/N806 violations fixed:** 19 → 0 (via per-file-ignores)
- **Files created:** 1 (`src/siopv/domain/constants.py`)
- **Files modified:** 3 (pyproject.toml, enrichment.py, risk_score.py)

---

## Changes Made

### 1. Created Constants Module

**File:** `src/siopv/domain/constants.py`

Defined domain-level constants with semantic names:

```python
# EPSS Score Thresholds
EPSS_HIGH_RISK_THRESHOLD = 0.1

# Relevance Score Thresholds
RELEVANCE_SCORE_OSINT_FALLBACK_THRESHOLD = 0.6

# Risk Probability Thresholds
RISK_PROBABILITY_CRITICAL_THRESHOLD = 0.8
RISK_PROBABILITY_HIGH_THRESHOLD = 0.6
RISK_PROBABILITY_MEDIUM_THRESHOLD = 0.4
RISK_PROBABILITY_LOW_THRESHOLD = 0.2

# Confidence Calculation
CONFIDENCE_CENTER_PROBABILITY = 0.5
CONFIDENCE_SCALE_FACTOR = 2
```

### 2. Updated pyproject.toml

Added per-file-ignores for ML-specific naming conventions (uppercase X, y variables):

```toml
[tool.ruff.lint.per-file-ignores]
"src/domain/learning/*.py" = ["N803", "N806"]
"src/siopv/adapters/ml/*.py" = ["N803", "N806"]  # ML convention: X, y for features/labels
"src/siopv/application/ports/ml_classifier.py" = ["N803", "N806"]  # ML interface matches adapters
```

**Rationale:** In ML code, uppercase `X` for features and lowercase `y` for labels is a universal convention (from scikit-learn, NumPy, academic papers). Forcing lowercase would harm readability.

### 3. Updated enrichment.py

**Violations Fixed:** 2

- `EPSSScore.is_high_risk`: Replaced `0.1` with `EPSS_HIGH_RISK_THRESHOLD`
- `VulnerabilityEnrichment.needs_osint_fallback`: Replaced `0.6` with `RELEVANCE_SCORE_OSINT_FALLBACK_THRESHOLD`

**Imports Added:**
```python
from siopv.domain.constants import (
    EPSS_HIGH_RISK_THRESHOLD,
    RELEVANCE_SCORE_OSINT_FALLBACK_THRESHOLD,
)
```

### 4. Updated risk_score.py

**Violations Fixed:** 6

- `RiskScore.from_prediction`: Replaced all threshold values (0.8, 0.6, 0.4, 0.2) with named constants
- `RiskScore.from_prediction`: Replaced confidence calculation magic values (0.5, 2) with named constants
- `RiskScore.is_high_risk`: Replaced `0.6` with `RISK_PROBABILITY_HIGH_THRESHOLD`
- `RiskScore.requires_immediate_action`: Replaced `0.8` with `RISK_PROBABILITY_CRITICAL_THRESHOLD`

**Imports Added:**
```python
from siopv.domain.constants import (
    CONFIDENCE_CENTER_PROBABILITY,
    CONFIDENCE_SCALE_FACTOR,
    RISK_PROBABILITY_CRITICAL_THRESHOLD,
    RISK_PROBABILITY_HIGH_THRESHOLD,
    RISK_PROBABILITY_LOW_THRESHOLD,
    RISK_PROBABILITY_MEDIUM_THRESHOLD,
)
```

---

## Verification

### Final Ruff Check
```bash
$ uv run ruff check --select PLR2004,N803,N806 src/
All checks passed!
```

### Before vs After

| Check | Before | After |
|-------|--------|-------|
| PLR2004 (magic values) | 8 errors | 0 errors ✅ |
| N803 (argument naming) | 7 errors | 0 errors ✅ |
| N806 (variable naming) | 12 errors | 0 errors ✅ |

---

## Benefits

1. **Maintainability:** All threshold values centralized in one file
2. **Tunability:** Easy to adjust system behavior by changing constants
3. **Documentation:** Semantic names explain purpose (e.g., `EPSS_HIGH_RISK_THRESHOLD` vs `0.1`)
4. **ML Conventions:** Preserved standard ML naming (X, y) via per-file-ignores
5. **Type Safety:** All constants remain type-checked

---

## Files Modified

1. **Created:** `src/siopv/domain/constants.py` (30 lines)
2. **Modified:** `pyproject.toml` (added 2 lines in per-file-ignores)
3. **Modified:** `src/siopv/domain/value_objects/enrichment.py` (imports + 2 replacements)
4. **Modified:** `src/siopv/domain/value_objects/risk_score.py` (imports + 6 replacements)

---

## Next Steps

Task #2 complete. Ready for:
- Task #3: Fix pytest violations PT006/PT011 (already in progress by another agent)
- Task #4: Fix datetime DTZ007 + Typer decorators + Tenacity
- Task #5: Fix remaining mypy errors
- Task #6: Run full validation

---

**Completion Time:** ~5 minutes
**Agent Model:** Sonnet (appropriate for multi-file pattern replacement)
**Exit Code:** 0 (success)
