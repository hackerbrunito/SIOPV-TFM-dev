# R2 — Phase 3 Gap Analysis: Clasificación y Score de Riesgo (ML)

> Analyst: gap-analyzer-phase-3 | Date: 2026-03-11
> Source: R1 requirements matrix (REQ-P3-001 through REQ-P3-012)

---

## Summary

| Status | Count |
|--------|-------|
| IMPLEMENTED | 8 |
| PARTIAL | 2 |
| MISSING | 2 |

---

## Requirement-by-Requirement Assessment

### REQ-P3-001 — Module name: `ML_Risk_Classifier`
- **Status:** IMPLEMENTED
- **Evidence:** `src/siopv/application/use_cases/classify_risk.py:73` — `ClassifyRiskUseCase` class. The classify node at `src/siopv/application/orchestration/nodes/classify_node.py:1` wraps it as `classify_node` for LangGraph integration. Adapter at `src/siopv/adapters/ml/xgboost_classifier.py:120` (`XGBoostClassifier`).
- **Notes:** Module is named via class names rather than a literal `ML_Risk_Classifier` string, but the functional role is fully covered.

### REQ-P3-002 — Primary algorithm: XGBoost with Optuna hyperparameter tuning
- **Status:** IMPLEMENTED
- **Evidence:** `src/siopv/adapters/ml/xgboost_classifier.py:29` imports `XGBClassifier`; line 19 imports `optuna`. Training method at line 296 uses Optuna optimization (lines 521-589) with TPE sampler and configurable `n_trials`.
- **Notes:** Full XGBoost + Optuna pipeline with train/evaluate/save/load lifecycle.

### REQ-P3-003 — Baseline algorithm: Random Forest for comparison/ensemble
- **Status:** MISSING
- **Evidence:** Grep for `RandomForest`, `random_forest`, `ensemble` across `src/` returns zero matches. No `sklearn.ensemble.RandomForestClassifier` import exists anywhere.
- **Notes:** The spec requires Random Forest as a baseline comparator or ensemble member. This is completely absent. No adapter, no port method, no ensemble logic.

### REQ-P3-004 — XAI framework: SHAP (global analysis) + LIME (local explanations)
- **Status:** IMPLEMENTED
- **Evidence:**
  - SHAP: `src/siopv/adapters/ml/shap_explainer.py:24` — `SHAPExplainer` using `shap.TreeExplainer` (line 54). Global importance via `get_global_importance()` (line 143).
  - LIME: `src/siopv/adapters/ml/lime_explainer.py:29` — `LIMEExplainer` using `lime.lime_tabular.LimeTabularExplainer` (line 71). Per-prediction explanations via `explain()` (line 89).
- **Notes:** Both SHAP and LIME are fully integrated into the prediction pipeline via `XGBoostClassifier.predict()` (lines 183-202).

### REQ-P3-005 — Training data: CISA KEV (positive class, ~1200 CVEs)
- **Status:** IMPLEMENTED
- **Evidence:** `src/siopv/infrastructure/ml/dataset_loader.py:109` — `CISAKEVLoader` implements `DatasetLoaderPort`. Downloads from official CISA KEV URL (line 31). `load_kev_catalog()` at line 148 returns list of CVE IDs.
- **Notes:** Pydantic validation of KEV schema (`KEVVulnerability` model at line 43, `KEVCatalog` at line 85). Caching implemented.

### REQ-P3-006 — Secondary source: EPSS historical data correlated with confirmed exploitation
- **Status:** PARTIAL
- **Evidence:** `src/siopv/infrastructure/ml/dataset_loader.py:258` — `sample_negative_class()` uses `max_epss` parameter to filter by EPSS score. EPSS data is used as a feature (`epss_score`, `epss_percentile` in `MLFeatureVector`).
- **Notes:** EPSS is used for negative class filtering and as ML features, but there is no explicit "EPSS historical data" correlation module. The spec implies using EPSS time-series data correlated with confirmed exploitation events — this deeper correlation is not implemented. The current approach uses snapshot EPSS scores, not historical trends.

### REQ-P3-007 — Negative class: stratified NVD sample (EPSS < 0.1, age > 2 years, not in KEV) — ratio 1:3
- **Status:** IMPLEMENTED
- **Evidence:** `src/siopv/application/ports/ml_classifier.py:191-210` — `DatasetLoaderPort.sample_negative_class()` accepts `exclude_cves` (KEV exclusion), `max_epss=0.1`, `min_age_days=730` (2 years), `sample_size=3600` (3x ~1200 KEV = 1:3 ratio). Implementation at `src/siopv/infrastructure/ml/dataset_loader.py:258`.
- **Notes:** All four criteria (EPSS threshold, age, KEV exclusion, ratio) are parameterized with correct defaults matching the spec.

### REQ-P3-008 — Balancing: SMOTE + class weighting in loss function
- **Status:** PARTIAL
- **Evidence:** `src/siopv/adapters/ml/xgboost_classifier.py:21` imports `SMOTE` from `imblearn`. Applied at line 342: `SMOTE(sampling_strategy="auto", random_state=random_state)`.
- **Notes:** SMOTE is implemented. However, **class weighting in the XGBoost loss function is NOT configured**. The spec says "SMOTE + class weighting in loss function" — XGBoost supports `scale_pos_weight` parameter for this, but it is not set in `_default_params()` (line 506) nor in the Optuna search space (line 546). Only SMOTE is used; the loss function weighting half of the requirement is missing.

### REQ-P3-009 — Feature vector: 14 features (cvss_base_score, attack_vector, ...)
- **Status:** IMPLEMENTED
- **Evidence:** `src/siopv/domain/entities/ml_feature_vector.py:16` — `MLFeatureVector` Pydantic model with all 14 features:
  1. `cvss_base_score` (line 33)
  2. `attack_vector` (line 37)
  3. `attack_complexity` (line 41)
  4. `privileges_required` (line 45)
  5. `user_interaction` (line 49)
  6. `scope` (line 52)
  7. `confidentiality_impact` (line 57)
  8. `integrity_impact` (line 61)
  9. `availability_impact` (line 65)
  10. `epss_score` (line 71)
  11. `epss_percentile` (line 75)
  12. `days_since_publication` (line 81)
  13. `has_exploit_ref` (line 87)
  14. `cwe_category` (line 93)

  Feature engineering at `src/siopv/adapters/ml/feature_engineer.py:56` — `FeatureEngineer` extracts all 14 features from `VulnerabilityRecord` + `EnrichmentData`. CWE target encoding at lines 25-53.
- **Notes:** Exact match with spec. Validated with Pydantic constraints (ge/le bounds). `to_array()` at line 134 produces numpy array in correct order.

### REQ-P3-010 — SHAP global analysis: feature importance charts
- **Status:** IMPLEMENTED
- **Evidence:** `src/siopv/adapters/ml/shap_explainer.py:143` — `get_global_importance()` calculates mean absolute SHAP values across samples. `generate_summary_data()` at line 179 returns data for `shap.summary_plot()`.
- **Notes:** Data generation for charts is implemented. Actual chart rendering would happen in Phase 7 (Streamlit dashboard).

### REQ-P3-011 — LIME local explanations: per-vulnerability feature contributions
- **Status:** IMPLEMENTED
- **Evidence:** `src/siopv/adapters/ml/lime_explainer.py:89` — `explain()` generates per-prediction LIME explanations. Returns `LIMEExplanation` value object (defined at `src/siopv/domain/value_objects/risk_score.py:71`) with `feature_contributions`, `prediction_local`, `intercept`, and `model_score` (fidelity).
- **Notes:** `explain_top_factors()` at `risk_score.py:111` provides human-readable explanation strings. Batch support at `lime_explainer.py:144`.

### REQ-P3-012 — Output tuple: `(risk_probability, shap_values, lime_explanation)` propagated to LangGraph state
- **Status:** IMPLEMENTED
- **Evidence:** `src/siopv/domain/value_objects/risk_score.py:237` — `RiskScore.to_output_tuple()` returns `(risk_probability, shap_values, lime_explanation)`. Called from `ClassificationResult.to_output_tuple()` at `src/siopv/application/use_cases/classify_risk.py:42`. The classify node at `classify_node.py:97-101` returns `classifications` and `llm_confidence` dicts to LangGraph state.
- **Notes:** The output tuple method exists and matches spec. State propagation is functional through the classify node.

---

## Cross-Cutting Requirements Relevant to Phase 3

### REQ-XC-007 — Fallback: ML model → CVSS+EPSS heuristic, mark `degraded_confidence`
- **Status:** PARTIAL (assessed here for Phase 3 context)
- **Evidence:** `classify_node.py:62-72` — when `classifier is None`, falls back to `_create_mock_classifications()` (line 188) which uses a severity-based heuristic mapping. However, there is no `degraded_confidence` flag set on the result.
- **Notes:** The fallback exists but uses severity mapping instead of CVSS+EPSS formula, and does not mark results with `degraded_confidence`.

### REQ-XC-011 — ML quality gates: Precision ≥ 0.85, Recall ≥ 0.90, F1 ≥ 0.87, AUC-ROC ≥ 0.92, Cal. Error ≤ 0.05
- **Status:** PARTIAL (assessed here for Phase 3 context)
- **Evidence:** `xgboost_classifier.py:63-66` — target constants defined for precision (0.85), recall (0.90), F1 (0.87), AUC-ROC (0.92). `evaluate()` at line 409 checks `meets_*_target` flags. However, **Calibration Error (≤ 0.05) is completely missing** — no import of `calibration_curve` or `expected_calibration_error`, no computation anywhere.
- **Notes:** 4/5 quality gate metrics implemented. Calibration Error is absent.

---

## Gap Priority Summary

| # | Requirement | Status | Severity | Action Needed |
|---|-------------|--------|----------|---------------|
| 1 | REQ-P3-003 (Random Forest) | MISSING | HIGH | Implement `RandomForestClassifier` adapter + comparison/ensemble logic |
| 2 | REQ-P3-008 (class weighting) | PARTIAL | MEDIUM | Add `scale_pos_weight` to XGBoost params and Optuna search space |
| 3 | REQ-P3-006 (EPSS historical) | PARTIAL | LOW | EPSS snapshot is functional; historical correlation is nice-to-have |
| 4 | REQ-XC-011 (Cal. Error) | PARTIAL | MEDIUM | Add `sklearn.calibration.calibration_curve` + ECE metric to `evaluate()` |
| 5 | REQ-XC-007 (degraded flag) | PARTIAL | LOW | Add `degraded_confidence=True` flag to mock fallback results |

---

## Files Analyzed

| File | Lines | Role |
|------|-------|------|
| `src/siopv/adapters/ml/xgboost_classifier.py` | 593 | XGBoost + Optuna + SMOTE training pipeline |
| `src/siopv/adapters/ml/shap_explainer.py` | 210 | SHAP TreeExplainer wrapper |
| `src/siopv/adapters/ml/lime_explainer.py` | 232 | LIME TabularExplainer wrapper |
| `src/siopv/adapters/ml/feature_engineer.py` | 267 | 14-feature extraction from enrichments |
| `src/siopv/domain/entities/ml_feature_vector.py` | 227 | Pydantic model for 14-feature vector |
| `src/siopv/domain/value_objects/risk_score.py` | 257 | RiskScore, SHAPValues, LIMEExplanation VOs |
| `src/siopv/application/use_cases/classify_risk.py` | 292 | ClassifyRiskUseCase orchestration |
| `src/siopv/application/orchestration/nodes/classify_node.py` | 243 | LangGraph classify node |
| `src/siopv/application/ports/ml_classifier.py` | 218 | MLClassifierPort, ModelTrainerPort, DatasetLoaderPort |
| `src/siopv/infrastructure/ml/dataset_loader.py` | 345 | CISAKEVLoader implementation |
| `src/siopv/infrastructure/ml/model_persistence.py` | 491 | Model save/load with integrity checks |
| `src/siopv/domain/constants.py` | 27 | Risk thresholds and confidence constants |

---

*End of Phase 3 gap analysis — 8 IMPLEMENTED, 2 PARTIAL, 2 MISSING out of 12 core requirements.*
