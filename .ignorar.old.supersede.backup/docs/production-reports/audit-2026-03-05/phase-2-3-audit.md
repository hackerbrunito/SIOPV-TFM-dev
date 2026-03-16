# SIOPV Audit Report — Phase 2 (Enrichment / CRAG) and Phase 3 (Classification / XGBoost)

**Date:** 2026-03-05
**Auditor:** Senior Code Auditor (automated, read-only)
**Scope:** Phase 2 adapters, Phase 3 adapters, orchestration nodes, and use cases
**Mode:** READ-ONLY — no changes made

---

## Executive Summary

- **asyncio.run() anti-pattern is confirmed** in `enrich_node.py` at line 73, and also present in `authorization_node.py` and `dlp_node.py`. The graph uses the **sync** `enrich_node` (not `enrich_node_async`) in `graph.py:194`, making all pipeline runs vulnerable to "asyncio event loop already running" errors in any async runner (FastAPI, Streamlit, Jupyter, pytest-asyncio).

- **`_estimate_llm_confidence()` is confirmed a pure math heuristic** with no LLM involvement whatsoever (classify_node.py:147–185). The function is explicitly documented as a placeholder ("In production, this would be replaced by actual LLM evaluation"). The `llm_confidence` field in LangGraph state is therefore a misleading name — it is a computed score, not an LLM output.

- **`run_pipeline()` silently drops all enrichment clients** (graph.py:439–444). The function accepts `nvd_client`, `epss_client`, `github_client`, `osint_client`, and `vector_store` via `create_pipeline_graph()`, but `run_pipeline()` does not expose or pass these parameters, causing the enrichment node to always fall back to minimal placeholder enrichments in production.

---

## Findings Table

### ERRORS

| # | Severity | File:Line | Issue | Recommended Fix |
|---|----------|-----------|-------|-----------------|
| E1 | CRITICAL | `src/siopv/application/orchestration/graph.py:403–444` | `run_pipeline()` never passes `nvd_client`, `epss_client`, `github_client`, `osint_client`, `vector_store` to `create_pipeline_graph()`. All 5 enrichment clients default to `None`. The `enrich_node` detects missing clients at runtime and silently falls back to minimal placeholder enrichments (relevance_score=0.5, no NVD/EPSS/GitHub data). This is a silent data quality failure — no error is raised. | Add the 5 enrichment client parameters to `run_pipeline()` signature and pass them through to `create_pipeline_graph()`. |
| E2 | HIGH | `src/siopv/adapters/ml/xgboost_classifier.py:368,558` | `use_label_encoder=False` is passed to `XGBClassifierBase` in both `train()` (line 368) and `_optimize_hyperparams()` (line 558). This parameter was removed in XGBoost 2.0+. Current installed version is 3.1.3. Testing confirms this does NOT raise at import time (XGBoost silently ignores unknown kwargs in 3.x), but it is dead code and documents incorrect API usage for future maintainers. | Remove `use_label_encoder=False` from both `XGBClassifierBase` constructor calls. |
| E3 | HIGH | `src/siopv/application/orchestration/nodes/enrich_node.py:73` | `asyncio.run()` is called from a synchronous function `enrich_node()`, which is what the LangGraph graph uses (graph.py:194 uses `enrich_node`, not `enrich_node_async`). `asyncio.run()` fails with `RuntimeError: This event loop is already running` in any async context (FastAPI routes, Streamlit, Jupyter, pytest-asyncio). The async-safe variant `enrich_node_async` exists but is not wired into the graph. | In `graph.py`, replace `enrich_node` with `enrich_node_async` in the `add_node("enrich", ...)` call, OR use `nest_asyncio` / `asyncio.get_event_loop().run_until_complete()` as a bridge. |

---

### GAPS (Forgotten Tasks / Placeholders)

| # | Severity | File:Line | Issue | Recommended Fix |
|---|----------|-----------|-------|-----------------|
| G1 | HIGH | `src/siopv/application/orchestration/nodes/classify_node.py:147–185` | `_estimate_llm_confidence()` is a pure arithmetic formula — no LLM call, no model invocation, no external API. Comments explicitly state: "In production, this would be replaced by actual LLM evaluation. For now, we estimate based on risk probability extremeness and enrichment relevance." The `llm_confidence` dict in LangGraph state is therefore mis-named and misleading to Phase 7 (Streamlit UI) and Phase 8 (reporting) developers. | Either implement a real LLM confidence evaluation (calling the LLM via an adapter), or rename `llm_confidence` to `ml_confidence_estimate` throughout the state and classify_node, and document it as a mathematical proxy. |
| G2 | HIGH | `src/siopv/application/orchestration/nodes/enrich_node.py:130–141` | When any enrichment client is `None`, `_run_enrichment()` logs a warning and returns `_create_minimal_enrichments()` with `relevance_score=0.5` for every vulnerability. This fallback is silent from the caller's perspective — no exception, no error in state. In production this means Phase 3 classification runs on stub data. | Raise a `ConfigurationError` (or populate `state["errors"]`) when critical enrichment clients are absent. Do not silently degrade. |
| G3 | MEDIUM | `src/siopv/application/orchestration/nodes/classify_node.py:188–237` | `_create_mock_classifications()` provides a mock fallback when `classifier is None`. This is appropriate for testing but the "mock" path emits only a `WARNING` log, not an error. In production, a missing classifier would silently produce mock risk scores. | Add a configuration guard: if `classifier is None` in a non-test context, raise `ConfigurationError` or populate `state["errors"]` instead of silently mocking. |
| G4 | MEDIUM | `src/siopv/application/use_cases/enrich_context.py:42` | `RELEVANCE_THRESHOLD = 0.6` is defined as a local constant in `enrich_context.py` — duplicating the value already defined in `siopv.domain.constants.RELEVANCE_SCORE_OSINT_FALLBACK_THRESHOLD = 0.6`. Two sources of truth for the same value. | Remove the local `RELEVANCE_THRESHOLD` definition and import `RELEVANCE_SCORE_OSINT_FALLBACK_THRESHOLD` from `siopv.domain.constants`. |
| G5 | LOW | `src/siopv/infrastructure/ml/dataset_loader.py` | Coverage: 0%. File has 121 lines, all uncovered. Not under Phase 2/3 scope directly, but the ML training pipeline requires training data and this loader is the only path to feed `XGBoostClassifier.train()`. No model training is possible without it, and 0% test coverage means it has never been exercised in CI. | Add tests for `DatasetLoader` covering happy path, file-not-found, and malformed CSV scenarios. |
| G6 | LOW | `src/siopv/infrastructure/ml/model_persistence.py` | Coverage: 0%. File has 167 lines. Model saving/loading from disk is a critical operation for Phase 3 (the model must exist at startup, loaded via `model_path`). Zero test coverage means save/load round-trip has never been validated. | Add tests for the persistence save/load cycle. |

---

### INCONSISTENCIES

| # | Severity | File:Line | Issue | Recommended Fix |
|---|----------|-----------|-------|-----------------|
| I1 | HIGH | `classify_node.py:213–220` vs `domain/constants.py` | Magic numbers in `_create_mock_classifications()`: `{"CRITICAL": 0.9, "HIGH": 0.7, "MEDIUM": 0.5, "LOW": 0.3, "UNKNOWN": 0.4}` and the fallback `0.4` on line 220. These severity-to-probability mappings are not in `domain/constants.py` and not imported from there. The real constants (`RISK_PROBABILITY_CRITICAL_THRESHOLD = 0.8`, `RISK_PROBABILITY_HIGH_THRESHOLD = 0.6`) define different thresholds, creating an inconsistency between mock behavior and real classification logic. | Define `SEVERITY_RISK_MAP` in `domain/constants.py` and import it in `classify_node.py`. Align mock probabilities with real thresholds. |
| I2 | HIGH | `classify_node.py:168–185` vs `domain/constants.py` | `_estimate_llm_confidence()` uses hardcoded values: `base_confidence = 0.7`, `confidence_boost = extremeness * 0.2`, `relevance_boost = enrichment.relevance_score * 0.1`, default uncertainty `0.5`. `domain/constants.py` defines `CONFIDENCE_CENTER_PROBABILITY = 0.5` and `CONFIDENCE_SCALE_FACTOR = 2` but these are NOT imported in `classify_node.py`. | Import confidence constants from `domain.constants` or add the missing ones (`BASE_CONFIDENCE`, `CONFIDENCE_BOOST_FACTOR`, `RELEVANCE_BOOST_FACTOR`) and use them. |
| I3 | MEDIUM | `classify_node.py:234` | Mock LLM confidence formula: `0.6 + (risk_probability * 0.3)` uses two magic numbers inline (`0.6`, `0.3`). Neither is defined in `domain/constants.py`. | Extract to named constants. |
| I4 | MEDIUM | `adapters/external_apis/tavily_client.py:59` | `MIN_RELEVANCE_SCORE = 0.3` is a class-level constant in `TavilyClient`. The same concept (result relevance filtering) is in scope of `domain/constants.py` which already has `RELEVANCE_SCORE_OSINT_FALLBACK_THRESHOLD`. These are different thresholds for different purposes, but neither references the other, making the relevance scoring logic fragmented across 3 files. | Document the distinction clearly. Consider adding `TAVILY_MIN_RESULT_RELEVANCE = 0.3` to `domain/constants.py` for discoverability. |
| I5 | LOW | `enrich_node.py` exports vs graph.py usage | `enrich_node.py` exports both `enrich_node` (sync, uses `asyncio.run`) and `enrich_node_async` (async, uses `await`). The graph uses `enrich_node` (sync). The async variant is exported in `__all__` but never used in production. This creates dead code at the module interface level. | Either use `enrich_node_async` in the graph and remove `enrich_node` from `__all__`, or document which variant is canonical. |

---

### TEST COVERAGE GAPS

| # | Severity | File | Coverage | Missing Tests |
|---|----------|------|----------|---------------|
| T1 | CRITICAL | `src/siopv/adapters/vectorstore/chroma_adapter.py` | **0%** (142/142 lines uncovered) | NO tests exist for `ChromaDBAdapter`. Missing: `store_enrichment`, `get_by_cve_id`, `query_similar`, `exists`, `delete`, `count`, `clear`, LRU cache eviction, persistence round-trip, error handling when ChromaDB unavailable. |
| T2 | HIGH | `src/siopv/adapters/external_apis/epss_client.py` | **17%** (lines 64–294 mostly uncovered) | No unit test file exists for `EPSSClient`. Missing: `get_score()` (happy path, cache hit, API error, circuit breaker open), `get_scores_batch()` (chunking at 100, partial failures), `_fetch_epss_batch()` (HTTP retry logic). Tests in `test_enrich_context.py` use `AsyncMock` and never exercise the real client. |
| T3 | HIGH | `src/siopv/adapters/external_apis/github_advisory_client.py` | **17%** (lines 145–401 mostly uncovered) | No unit test file exists for `GitHubAdvisoryClient`. Missing: `get_advisory_by_cve()` (happy path, not found, GraphQL errors, circuit breaker), `get_advisories_for_package()` (ecosystem mapping, empty result), `ECOSYSTEM_MAP` coverage, HTTP 403 rate limit handling. |
| T4 | HIGH | `src/siopv/adapters/external_apis/nvd_client.py` | **19%** (lines 70–286 mostly uncovered) | No unit test file exists for `NVDClient`. Missing: `get_cve()` (happy path, 404, 403 rate limit, timeout, cache hit), `get_cves_batch()` (semaphore limiting, partial errors), `health_check()`, `_fetch_cve()` retry behavior. |
| T5 | HIGH | `src/siopv/adapters/external_apis/tavily_client.py` | **20%** (lines 73–322 mostly uncovered) | No unit test file exists for `TavilyClient`. Missing: `search()` (no API key, circuit breaker, timeout), `search_exploit_info()` (domain filtering, score filtering), `_execute_search()` (429 rate limit, 401 unauthorized), retry exhaustion. |
| T6 | HIGH | `src/siopv/adapters/ml/xgboost_classifier.py` | **20%** (lines 94–589 mostly uncovered) | Tests exist but coverage is 20%. Missing: `train()` with SMOTE (unit-tested with real numpy arrays), `evaluate()` with actual predictions, `save_model()` / `load_model()` round-trip, `get_feature_importance()`, `_optimize_hyperparams()`, production random state generation path (`SIOPV_ENVIRONMENT=production`), `predict_batch()`. |
| T7 | MEDIUM | `src/siopv/adapters/ml/shap_explainer.py` | **21%** (lines 44–206 mostly uncovered) | Tests exist but coverage is 21%. Missing: `explain()` with real XGBoost model, `explain_batch()`, `get_global_importance()`, `generate_summary_data()`, binary classification SHAP value extraction path. |
| T8 | MEDIUM | `src/siopv/adapters/ml/lime_explainer.py` | **35%** (lines 64–223 partly uncovered) | Tests exist but coverage is 35%. Missing: `explain()` with real predictor, `explain_batch()` with failure fallback, `from_model()` class method, `local_pred` and `intercept` attribute handling when `hasattr` returns False. |
| T9 | MEDIUM | `src/siopv/adapters/ml/feature_engineer.py` | **21%** (lines 86–263 mostly uncovered) | Tests exist (`test_feature_engineer.py`) but coverage is 21%. Missing: `extract_features()` with various `VulnerabilityRecord` configurations, CVSS vector parsing, CWE encoding lookup (known CWE, unknown CWE → DEFAULT). |
| T10 | LOW | `src/siopv/application/orchestration/nodes/enrich_node.py` | Partial (only basic path tested) | `test_enrich_node.py` exists under `tests/unit/application/orchestration/nodes/`. Missing: test that confirms `asyncio.run()` fails when called from an async context (pytest-asyncio), test for `enrich_node_async()` with all clients provided, test for the minimal enrichment fallback when all clients are `None`. |

---

## asyncio.run() Anti-Pattern — Full Picture

The pattern appears in 3 of 5 sync nodes:

```
enrich_node.py:73    →  asyncio.run(_run_enrichment(...))
dlp_node.py:106      →  asyncio.run(_run_dlp_for_vulns(...))
authorization_node.py:194  →  asyncio.run(port.check(context))
```

`graph.py` calls `graph.invoke()` (sync LangGraph) which calls each node in sequence on the same thread. When the caller runs inside an existing event loop (e.g., a Streamlit async context, FastAPI route, or pytest-asyncio test), `asyncio.run()` raises:

```
RuntimeError: This event loop is already running.
```

The `enrich_node_async` alternative exists and is correctly implemented, but is not wired into the graph.

---

## _estimate_llm_confidence() — Confirmed Heuristic

```python
# classify_node.py:147-185
def _estimate_llm_confidence(...) -> float:
    base_confidence = 0.7  # Magic number
    risk_prob = classification.risk_score.risk_probability
    extremeness = abs(risk_prob - 0.5) * 2
    confidence_boost = extremeness * 0.2  # Magic number
    relevance_boost = enrichment.relevance_score * 0.1  # Magic number
    confidence = min(1.0, base_confidence + confidence_boost + relevance_boost)
    return round(confidence, 3)
```

This is purely arithmetic. No LLM is invoked. The function's docstring explicitly states "In production, this would be replaced by actual LLM evaluation." The field name `llm_confidence` in the LangGraph state is therefore misleading. This function was known from the previous audit (2026-03-05 findings, item #3), and is confirmed here.

---

## run_pipeline() Client Drop — Confirmed

`run_pipeline()` signature (graph.py:403–412) accepts only:
- `report_path`, `thread_id`, `user_id`, `project_id`, `checkpoint_db_path`
- `authorization_port`, `dlp_port`, `classifier`

It does NOT accept or pass: `nvd_client`, `epss_client`, `github_client`, `osint_client`, `vector_store`.

`create_pipeline_graph()` (graph.py:358–400) does accept all 5 enrichment clients, but `run_pipeline()` calls it without them (line 439–445):

```python
graph = create_pipeline_graph(
    checkpoint_db_path=checkpoint_db_path,
    authorization_port=authorization_port,
    dlp_port=dlp_port,
    classifier=classifier,
    with_checkpointer=checkpoint_db_path is not None,
    # nvd_client, epss_client, github_client, osint_client, vector_store → ALL MISSING
)
```

Result: every pipeline invocation via `run_pipeline()` runs with minimal stub enrichments.

---

## What Is Implemented Correctly (Phase 2 and 3)

- All 4 external API clients implement retry (tenacity, 3 attempts, exponential backoff) and circuit breaker (configurable threshold/recovery). This is correct.
- `ChromaDBAdapter` correctly uses `PersistentClient` with upsert semantics and LRU cache — the implementation is sound, just untested.
- `enrich_context.py` correctly implements the CRAG pattern (parallel fetch → relevance score → OSINT fallback below 0.6 threshold → store in ChromaDB).
- `XGBoostClassifier` correctly handles production vs dev random state, and SHAP/LIME explainers are properly integrated.
- `FeatureEngineer` extracts the full 14-feature vector as per spec. CWE target encoding is pre-computed and reasonable.
- ruff check passes on all Phase 2 and 3 files (0 errors, 0 warnings).

---

## Priority Order for Fixes

1. **E1 + G1/G2** — `run_pipeline()` dropping enrichment clients + silent fallbacks. Production data quality.
2. **E3** — `asyncio.run()` anti-pattern. Will crash in Phase 7 (Streamlit).
3. **T1** — ChromaDB at 0% coverage. Critical persistence layer untested.
4. **T2–T5** — External API adapters at 17–20% coverage. No dedicated test files exist.
5. **I1–I3** — Magic numbers in classify_node not using domain constants.
6. **G4** — Duplicate RELEVANCE_THRESHOLD constant.
7. **E2** — Deprecated `use_label_encoder` parameter (low risk, cosmetic).
8. **T6–T9** — ML adapter tests exist but coverage is low. Extend existing suites.
