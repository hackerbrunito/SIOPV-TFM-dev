# Config Changes — Task #3

**File:** `pyproject.toml` `[tool.mypy]` section

## Changes Made

### Removed (redundant with `strict = true`):
- `warn_return_any = true`
- `warn_unused_ignores = true`
- `disallow_untyped_defs = true`

### Removed (too broad):
- `ignore_missing_imports = true` (global)

### Added:
- `enable_error_code = ["ignore-without-code"]` — enforces error codes on all `type: ignore`
- `show_error_codes = true` — always shows error codes in output

### Added per-module overrides:
```toml
[[tool.mypy.overrides]]
module = ["imblearn.*", "lime.*", "openfga_sdk.*", "shap.*", "sklearn.*"]
ignore_missing_imports = true
```

Only these 5 packages lack `py.typed` markers. All other dependencies (tenacity, chromadb, xgboost, pydantic, httpx, etc.) now get full import checking.

## Mypy Results After Change

- **8 errors** — all `[unused-ignore]`, same as before
- **No new import errors** from per-module switch
- **No @retry errors** — tenacity `@retry` does NOT trigger `[untyped-decorator]`
- **Conclusion:** Scenario A confirmed. All 8 stale comments can be safely removed in Phase 2.
