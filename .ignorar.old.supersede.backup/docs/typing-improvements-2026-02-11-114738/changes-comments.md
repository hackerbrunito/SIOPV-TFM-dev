# Comment Changes — Task #2

**Agent:** comment-enhancer
**Date:** 2026-02-11

## Summary

- **8 stale `type: ignore` comments removed** (all `[unused-ignore]`)
- **65 explanatory comments added** to remaining `type: ignore` statements
- **0 line-length violations** introduced (ruff E501 passes)

---

## Phase 1: Stale Comments Removed (8)

All 8 were `[unused-ignore]` — Scenario A confirmed by config-updater.

| # | File | Line | Removed Comment |
|---|------|------|-----------------|
| 1 | `adapters/external_apis/tavily_client.py` | 132 | `# type: ignore[untyped-decorator]` |
| 2 | `adapters/external_apis/nvd_client.py` | 126 | `# type: ignore[untyped-decorator]` |
| 3 | `adapters/external_apis/github_advisory_client.py` | 204 | `# type: ignore[untyped-decorator]` |
| 4 | `adapters/external_apis/epss_client.py` | 111 | `# type: ignore[untyped-decorator]` |
| 5 | `adapters/external_apis/epss_client.py` | 205 | `# type: ignore[untyped-decorator]` |
| 6 | `adapters/authorization/openfga_adapter.py` | 267 | `# type: ignore[untyped-decorator]` |
| 7 | `adapters/ml/xgboost_classifier.py` | 589 | `# type: ignore[no-any-return]` |
| 8 | `application/orchestration/graph.py` | 317 | `# type: ignore[no-any-return]` |

## Phase 2: Explanatory Comments Added (65)

### Pattern Used

```python
# Brief explanation of why suppression is needed
code  # type: ignore[error-code]
```

### By File

| File | Comments | Category |
|------|----------|----------|
| `adapters/vectorstore/chroma_adapter.py` | 13 | chromadb client typed as object; stubs incomplete |
| `application/orchestration/edges.py` | 10 | LangGraph state returns `dict[str, object]` |
| `application/orchestration/nodes/enrich_node.py` | 11 | Optional port narrowing + state typing |
| `application/orchestration/nodes/classify_node.py` | 10 | State typing + return type narrowing |
| `application/orchestration/utils.py` | 6 | ClassificationResult accessed via object type |
| `application/use_cases/enrich_context.py` | 4 | _safe_fetch returns object; awaitable coroutine |
| `domain/authorization/entities.py` | 3 | Pydantic @computed_field + @property |
| `domain/entities/ml_feature_vector.py` | 1 | Pydantic @computed_field + @property |
| `infrastructure/logging/setup.py` | 1 | structlog.get_logger typed as Any |
| `infrastructure/resilience/circuit_breaker.py` | 1 | ParamSpec wrapper return type |
| `infrastructure/ml/model_persistence.py` | 1 | xgboost.Booster typed as object |
| `adapters/ml/lime_explainer.py` | 1 | sklearn API predict_proba via object |
| `adapters/external_apis/trivy_parser.py` | 1 | Trivy JSON Results attr access |
| `application/orchestration/nodes/escalate_node.py` | 2 | State typing + lambda sort |
| **Total** | **65** | |

### Recurring Patterns

1. **LangGraph state `dict[str, object]`** (33 comments): State values typed as `object` but are typed domain objects at runtime. This is inherent to LangGraph's `TypedDict` → dict serialization.

2. **ChromaDB incomplete stubs** (13 comments): `client` typed as `object`; `PersistentClient` methods exist at runtime but not in type stubs.

3. **Pydantic `@computed_field` + `@property`** (4 comments): Known mypy incompatibility with Pydantic's decorator composition.

4. **`_safe_fetch` / generic object returns** (4 comments): Functions returning `object` for flexibility; typed results at runtime.

5. **Return type narrowing** (6 comments): Functions returning typed dicts narrower than declared `dict[str, object]` return type.

6. **Runtime-only attributes** (5 comments): Domain objects accessed via `object` type; actual attrs exist at runtime (cve_id, severity, etc.).

---

## Files Modified (14 total)

1. `src/siopv/adapters/external_apis/tavily_client.py`
2. `src/siopv/adapters/external_apis/nvd_client.py`
3. `src/siopv/adapters/external_apis/github_advisory_client.py`
4. `src/siopv/adapters/external_apis/epss_client.py`
5. `src/siopv/adapters/authorization/openfga_adapter.py`
6. `src/siopv/adapters/ml/xgboost_classifier.py`
7. `src/siopv/application/orchestration/graph.py`
8. `src/siopv/adapters/vectorstore/chroma_adapter.py`
9. `src/siopv/application/orchestration/edges.py`
10. `src/siopv/application/orchestration/nodes/enrich_node.py`
11. `src/siopv/application/orchestration/nodes/classify_node.py`
12. `src/siopv/application/orchestration/utils.py`
13. `src/siopv/application/use_cases/enrich_context.py`
14. `src/siopv/domain/authorization/entities.py`
15. `src/siopv/domain/entities/ml_feature_vector.py`
16. `src/siopv/infrastructure/logging/setup.py`
17. `src/siopv/infrastructure/resilience/circuit_breaker.py`
18. `src/siopv/infrastructure/ml/model_persistence.py`
19. `src/siopv/adapters/ml/lime_explainer.py`
20. `src/siopv/adapters/external_apis/trivy_parser.py`
21. `src/siopv/application/orchestration/nodes/escalate_node.py`
