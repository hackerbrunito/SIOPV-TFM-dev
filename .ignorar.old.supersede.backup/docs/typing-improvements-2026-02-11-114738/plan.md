# Typing Improvements Plan — 2026-02-11

**Scope:** Mypy config upgrade + explanatory comments on `type: ignore` statements
**Based on:** Audit report (`.ignorar/siopv-python-typing-audit-2026-02-11.md`), research (`research-python-typing-best-practices-2026.md`), live mypy 1.19.1 run

---

## Current State (Verified)

### Mypy Errors: 8 (all `[unused-ignore]`)

| # | File | Line | Current Comment | Status |
|---|------|------|-----------------|--------|
| 1 | `adapters/external_apis/tavily_client.py` | 132 | `# type: ignore[untyped-decorator]` | Stale |
| 2 | `adapters/external_apis/nvd_client.py` | 126 | `# type: ignore[untyped-decorator]` | Stale |
| 3 | `adapters/external_apis/github_advisory_client.py` | 204 | `# type: ignore[untyped-decorator]` | Stale |
| 4 | `adapters/external_apis/epss_client.py` | 111 | `# type: ignore[untyped-decorator]` | Stale |
| 5 | `adapters/external_apis/epss_client.py` | 205 | `# type: ignore[untyped-decorator]` | Stale |
| 6 | `adapters/authorization/openfga_adapter.py` | 267 | `# type: ignore[untyped-decorator]` | Stale |
| 7 | `adapters/ml/xgboost_classifier.py` | 589 | `# type: ignore[no-any-return]` | Stale |
| 8 | `application/orchestration/graph.py` | 317 | `# type: ignore[no-any-return]` | Stale |

### `type: ignore` Comments: 73 in src/ (21 files)

### Mypy Config Issues:
- **Global `ignore_missing_imports = true`** — hides import errors for well-typed packages
- **No `enable_error_code`** — bare `type: ignore` (without error code) is allowed
- **3 redundant settings** — `warn_return_any`, `warn_unused_ignores`, `disallow_untyped_defs` already enabled by `strict = true`
- **No `show_error_codes`** — error codes not always shown in output

### Packages Without `py.typed` (need `ignore_missing_imports`):
- `imblearn` (imbalanced-learn)
- `lime`
- `openfga_sdk`
- `shap`
- `sklearn` (scikit-learn)

### Packages WITH `py.typed` (should NOT be ignored):
tenacity, chromadb, xgboost, pydantic, httpx, sqlalchemy, structlog, langgraph, langchain, langchain_core, typer, rich, numpy, optuna, streamlit, presidio_analyzer, presidio_anonymizer, anthropic, aiosqlite, respx

---

## Execution Plan

### Phase 1: Update mypy configuration (Task #3)

**File:** `pyproject.toml` `[tool.mypy]` section

**Changes:**

```toml
# BEFORE
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true          # redundant (strict=true enables this)
warn_unused_ignores = true      # redundant (strict=true enables this)
disallow_untyped_defs = true    # redundant (strict=true enables this)
ignore_missing_imports = true   # TOO BROAD — hides ALL import errors

# AFTER
[tool.mypy]
python_version = "3.11"
strict = true
enable_error_code = ["ignore-without-code"]
show_error_codes = true

# Per-module overrides: only packages without py.typed / incomplete stubs
[[tool.mypy.overrides]]
module = [
    "imblearn.*",
    "lime.*",
    "openfga_sdk.*",
    "shap.*",
    "sklearn.*",
]
ignore_missing_imports = true
```

**Rationale:**
1. `enable_error_code = ["ignore-without-code"]` — enforces specific error codes on ALL `type: ignore` comments (Adam Johnson best practice)
2. `show_error_codes = true` — always shows error codes in output for faster debugging
3. Per-module `ignore_missing_imports` — only silences imports for 5 truly untyped packages; well-typed packages (pydantic, httpx, tenacity, etc.) get full import checking
4. Redundant settings removed — `strict = true` already enables `warn_return_any`, `warn_unused_ignores`, `disallow_untyped_defs`

**CRITICAL:** After this change, run `mypy` to check if new errors appear. The global → per-module switch may reveal:
- Previously hidden import errors for packages with incomplete stubs
- Previously hidden `[untyped-decorator]` errors (e.g., tenacity `@retry` may need `type: ignore` again)

If tenacity `@retry` triggers `[untyped-decorator]` after config change → KEEP those comments (they were correct all along). If not → REMOVE them as stale.

---

### Phase 2: Handle stale `type: ignore` comments

**DEPENDS ON Phase 1 mypy results.** Two scenarios:

#### Scenario A: No new errors from config change

Remove all 8 stale comments:

| File | Line | Action |
|------|------|--------|
| `tavily_client.py:132` | `# type: ignore[untyped-decorator]` | Delete |
| `nvd_client.py:126` | `# type: ignore[untyped-decorator]` | Delete |
| `github_advisory_client.py:204` | `# type: ignore[untyped-decorator]` | Delete |
| `epss_client.py:111` | `# type: ignore[untyped-decorator]` | Delete |
| `epss_client.py:205` | `# type: ignore[untyped-decorator]` | Delete |
| `openfga_adapter.py:267` | `# type: ignore[untyped-decorator]` | Delete |
| `xgboost_classifier.py:589` | `# type: ignore[no-any-return]` | Delete |
| `graph.py:317` | `# type: ignore[no-any-return]` | Delete |

#### Scenario B: Tenacity `@retry` triggers errors after config change

Keep the 6 `@retry` comments, remove 2 others:

| File | Line | Action |
|------|------|--------|
| `tavily_client.py:132` | `# type: ignore[untyped-decorator]` | **KEEP** + add comment |
| `nvd_client.py:126` | `# type: ignore[untyped-decorator]` | **KEEP** + add comment |
| `github_advisory_client.py:204` | `# type: ignore[untyped-decorator]` | **KEEP** + add comment |
| `epss_client.py:111` | `# type: ignore[untyped-decorator]` | **KEEP** + add comment |
| `epss_client.py:205` | `# type: ignore[untyped-decorator]` | **KEEP** + add comment |
| `openfga_adapter.py:267` | `# type: ignore[untyped-decorator]` | **KEEP** + add comment |
| `xgboost_classifier.py:589` | `# type: ignore[no-any-return]` | Delete |
| `graph.py:317` | `# type: ignore[no-any-return]` | Delete |

---

### Phase 3: Add explanatory comments to ALL remaining `type: ignore` (Task #2)

**Pattern (Adam Johnson best practice):**
```python
# BEFORE
value = client.method()  # type: ignore[attr-defined]

# AFTER
value = client.method()  # type: ignore[attr-defined]  # chromadb API lacks stubs
```

**Complete file-by-file list (65 remaining comments after Phase 2):**

#### Group 1: ChromaDB adapter — 13 comments
**File:** `src/siopv/adapters/vectorstore/chroma_adapter.py`
**Reason:** `# chromadb incomplete stubs`

| Line | Current | Explanatory Comment |
|------|---------|-------------------|
| 135 | `# type: ignore[attr-defined]` | `# chromadb.Client missing get_or_create_collection` |
| 188 | `# type: ignore[arg-type]` | `# chromadb metadata is dict[str, str\|int\|float\|bool]` |
| 205 | `# type: ignore[list-item]` | `# chromadb expects untyped list` |
| 206 | `# type: ignore[list-item]` | `# chromadb expects untyped list` |
| 207 | `# type: ignore[list-item]` | `# chromadb expects untyped list` |
| 214 | `# type: ignore[return-value]` | `# chromadb doc["id"] is str at runtime` |
| 245 | `# type: ignore[arg-type]` | `# chromadb expects broader types` |
| 246 | `# type: ignore[arg-type]` | `# chromadb expects broader types` |
| 247 | `# type: ignore[arg-type]` | `# chromadb expects broader types` |
| 251 | `# type: ignore[return-value]` | `# ids are str at runtime` |
| 290 | `# type: ignore[arg-type]` | `# chromadb metadata broader than typed` |
| 324 | `# type: ignore[arg-type]` | `# chromadb metadata broader than typed` |
| 393 | `# type: ignore[attr-defined]` | `# chromadb.Client missing delete_collection` |

#### Group 2: LangGraph orchestration — edges.py (10 comments)
**File:** `src/siopv/application/orchestration/edges.py`
**Reason:** `# LangGraph state returns union types`

| Line | Current | Explanatory Comment |
|------|---------|-------------------|
| 50 | `# type: ignore[arg-type]` | `# LangGraph state values are union types` |
| 77 | `# type: ignore[arg-type]` | `# LangGraph state values are union types` |
| 145 | `# type: ignore[attr-defined]` | `# ClassificationResult union lacks risk_score` |
| 151 | `# type: ignore[arg-type]` | `# LangGraph state values are union types` |
| 158 | `# type: ignore[attr-defined]` | `# ClassificationResult union lacks risk_score` |
| 177 | `# type: ignore[attr-defined]` | `# ClassificationResult union lacks risk_score` |
| 181 | `# type: ignore[attr-defined]` | `# ClassificationResult union lacks risk_score` |
| 187 | `# type: ignore[arg-type]` | `# LangGraph state values are union types` |
| 215 | `# type: ignore[arg-type]` | `# LangGraph state int conversion` |
| 239 | `# type: ignore[arg-type]` | `# LangGraph state.get returns union type` |

#### Group 3: Enrich node — 11 comments
**File:** `src/siopv/application/orchestration/nodes/enrich_node.py`

| Line | Current | Explanatory Comment |
|------|---------|-------------------|
| 75 | `# type: ignore[arg-type]` | `# LangGraph state values are union types` |
| 143-147 | `# type: ignore[arg-type]` (5) | `# port is Optional but validated non-None at startup` |
| 151 | `# type: ignore[arg-type]` | `# LangGraph state values are union types` |
| 161 | `# type: ignore[return-value]` | `# dict narrower than LangGraph state return` |
| 178 | `# type: ignore[attr-defined]` | `# VulnerabilityRecord has cve_id at runtime` |
| 184 | `# type: ignore[return-value]` | `# dict narrower than LangGraph state return` |
| 228 | `# type: ignore[arg-type]` | `# LangGraph state values are union types` |

#### Group 4: Classify node — 10 comments
**File:** `src/siopv/application/orchestration/nodes/classify_node.py`

| Line | Current | Explanatory Comment |
|------|---------|-------------------|
| 69-70 | `# type: ignore[arg-type]` (2) | `# LangGraph state values are union types` |
| 74-75 | `# type: ignore[arg-type]` (2) | `# LangGraph state values are union types` |
| 120 | `# type: ignore[arg-type]` | `# LangGraph state values are union types` |
| 136 | `# type: ignore[arg-type]` | `# enrichments.get returns Optional` |
| 139 | `# type: ignore[return-value]` | `# tuple return narrower than state type` |
| 203 | `# type: ignore[attr-defined]` | `# VulnerabilityRecord has cve_id at runtime` |
| 213 | `# type: ignore[attr-defined]` | `# VulnerabilityRecord has severity at runtime` |
| 229 | `# type: ignore[return-value]` | `# tuple return narrower than state type` |

#### Group 5: Utils — 6 comments
**File:** `src/siopv/application/orchestration/utils.py`

| Line | Current | Explanatory Comment |
|------|---------|-------------------|
| 87 | `# type: ignore[attr-defined]` | `# ClassificationResult union lacks risk_score` |
| 90 | `# type: ignore[attr-defined]` | `# ClassificationResult union lacks risk_score` |
| 112 | `# type: ignore[attr-defined]` | `# ClassificationResult union lacks risk_score` |
| 113 | `# type: ignore[attr-defined]` | `# ClassificationResult union lacks risk_score` |
| 152 | `# type: ignore[attr-defined]` | `# ClassificationResult union lacks risk_score` |
| 153 | `# type: ignore[attr-defined]` | `# ClassificationResult union lacks risk_score` |

#### Group 6: Enrich context — 4 comments
**File:** `src/siopv/application/use_cases/enrich_context.py`

| Line | Current | Explanatory Comment |
|------|---------|-------------------|
| 260 | `# type: ignore[arg-type]` | `# Optional result assembly, validated before use` |
| 261 | `# type: ignore[arg-type]` | `# Optional result assembly, validated before use` |
| 262 | `# type: ignore[arg-type]` | `# Optional result assembly, validated before use` |
| 276 | `# type: ignore[misc]` | `# async coroutine type inference limitation` |

#### Group 7: Other files — 7 comments

| File | Line | Current | Explanatory Comment |
|------|------|---------|-------------------|
| `domain/authorization/entities.py` | 434 | `# type: ignore[prop-decorator]` | `# Pydantic computed_field + @property known issue` |
| `domain/authorization/entities.py` | 515 | `# type: ignore[prop-decorator]` | `# Pydantic computed_field + @property known issue` |
| `domain/authorization/entities.py` | 521 | `# type: ignore[prop-decorator]` | `# Pydantic computed_field + @property known issue` |
| `domain/entities/ml_feature_vector.py` | 112 | `# type: ignore[prop-decorator]` | `# Pydantic computed_field + @property known issue` |
| `infrastructure/logging/setup.py` | 91 | `# type: ignore[no-any-return]` | `# structlog.get_logger returns BoundLogger at runtime` |
| `infrastructure/resilience/circuit_breaker.py` | 205 | `# type: ignore[return]` | `# ParamSpec wrapper, return always reached via decorated fn` |
| `infrastructure/ml/model_persistence.py` | 197 | `# type: ignore[attr-defined]` | `# xgboost.Booster.save_model exists at runtime` |
| `adapters/ml/lime_explainer.py` | 219 | `# type: ignore[attr-defined]` | `# model.predict_proba exists at runtime (sklearn API)` |
| `adapters/external_apis/trivy_parser.py` | 127 | `# type: ignore[attr-defined]` | `# trivy JSON results have Results attr at runtime` |
| `escalate_node.py` | 56 | `# type: ignore[arg-type]` | `# LangGraph state values are union types` |
| `escalate_node.py` | 162 | `# type: ignore[arg-type, return-value]` | `# lambda key sort with optional discrepancy` |

#### Group 8: Tenacity `@retry` — 6 comments (Scenario B only)

If kept after Phase 1 verification:

| File | Line | Explanatory Comment |
|------|------|-------------------|
| `tavily_client.py:132` | `# tenacity @retry lacks complete type stubs (typeshed#5786)` |
| `nvd_client.py:126` | `# tenacity @retry lacks complete type stubs (typeshed#5786)` |
| `github_advisory_client.py:204` | `# tenacity @retry lacks complete type stubs (typeshed#5786)` |
| `epss_client.py:111` | `# tenacity @retry lacks complete type stubs (typeshed#5786)` |
| `epss_client.py:205` | `# tenacity @retry lacks complete type stubs (typeshed#5786)` |
| `openfga_adapter.py:267` | `# tenacity @retry lacks complete type stubs (typeshed#5786)` |

---

### Phase 4: Verify (Task #4)

1. Run `mypy src/siopv/ --config-file pyproject.toml` — expect 0 errors
2. Run `ruff check src/` — expect 0 errors (line length check on added comments)
3. Run pre-commit hooks if available

---

## Task Assignment Summary

| Task | Agent | Phase | Estimated Changes |
|------|-------|-------|-------------------|
| #3: Update mypy config | config-agent | Phase 1 | 1 file (`pyproject.toml`) |
| #2: Add explanatory comments | comments-agent | Phase 3 | ~21 files |
| #4: Verify | verifier-agent | Phase 4 | Read-only |
| #5: Final report | report-agent | After Phase 4 | 1 file |

**Dependency chain:** Task #3 → (mypy run) → Task #2 → Task #4 → Task #5

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Per-module overrides reveal new import errors | Medium | Low | Add package to override list if truly untyped |
| Comments exceed 100-char line limit (ruff) | Medium | Low | Shorten explanatory comments |
| `enable_error_code = ["ignore-without-code"]` flags existing bare ignores | Low | Low | All existing comments already have error codes |
| Tenacity stubs change in future update | Low | Low | Comments explain why ignore exists |

---

## References

- [Adam Johnson — Specific type: ignore](https://adamj.eu/tech/2021/05/25/python-type-hints-specific-type-ignore/)
- [Professional-grade MyPy Configuration (Wolt)](https://careers.wolt.com/en/blog/tech/professional-grade-mypy-configuration)
- [Mypy docs — Error codes](https://mypy.readthedocs.io/en/stable/error_codes.html)
- [typeshed issue #5786 — tenacity stubs](https://github.com/python/typeshed/issues/5786)
- Audit report: `.ignorar/siopv-python-typing-audit-2026-02-11.md`
