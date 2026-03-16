# Pre-commit Hook Installation and Test Report

**Agent:** ci-implementer
**Date:** 2026-02-10
**Task:** Install and test pre-commit hooks locally

---

## Summary

✅ Pre-commit hooks installed successfully
❌ Initial run on all files: **FAILED** (74 ruff errors, 36 mypy errors)

---

## Installation Result

```bash
$ uv run pre-commit install
[WARNING] top-level `default_stages` uses deprecated stage names (commit) which will be removed in a future version.
pre-commit installed at .git/hooks/pre-commit
```

**Status:** ✅ Installed successfully

**Note:** Warning about deprecated `default_stages: [commit]` → recommend migrating to `default_stages: [pre-commit]`

---

## Test Run Results (`pre-commit run --all-files`)

### Ruff Linter: ❌ FAILED
- **Errors found:** 376 total (302 auto-fixed, 74 remaining)
- **Files modified:** Multiple files auto-formatted
- **Key issues:**
  - N806/N803: ML variable names (`X` should be lowercase per PEP8)
  - PLR2004: Magic values (0.1, 0.6, 0.8) need constants
  - ARG002/ARG003: Unused function arguments in tests
  - PT006: Wrong type in `@pytest.mark.parametrize`
  - PT011: `pytest.raises()` too broad, needs `match` parameter
  - TRY301: Abstract `raise` to inner function
  - DTZ007: Naive datetime without timezone
  - E501: Line too long (1 occurrence)

### Ruff Format: ❌ FAILED
- **Files reformatted:** 1 file
- **Warning:** ISC001 rule conflicts with formatter (recommend disabling)

### MyPy: ❌ FAILED
- **Errors found:** 36 errors in 12 files
- **Key issues:**
  - Unused `# type: ignore` comments (9 occurrences)
  - Decorators on `@property` not supported (5 occurrences)
  - Untyped decorators (`@retry`, `@app.command`) (10 occurrences)
  - `no-any-return` violations (5 occurrences)

---

## Issues Breakdown

### Critical Issues (Block Commits)
1. **MyPy errors:** 36 strict mode violations
2. **Ruff errors:** 74 unfixed violations

### ML Variable Naming Convention Conflict
- **Issue:** sklearn/xgboost use `X` (uppercase) by convention
- **Ruff rule:** N806/N803 requires lowercase variables
- **Recommendation:** Add per-file ignore for ML modules:
  ```yaml
  [tool.ruff.lint.per-file-ignores]
  "src/siopv/adapters/ml/*.py" = ["N803", "N806"]
  "tests/unit/adapters/ml/*.py" = ["N803", "N806"]
  ```

### Decorator Type Hints
- **Issue:** Typer/tenacity decorators are untyped
- **Solution:** Add `# type: ignore[misc]` where needed

---

## Next Steps (Required Before First Commit)

1. **Fix ML variable naming:** Add per-file ignores for N803/N806
2. **Fix magic values:** Extract to constants in domain/value_objects
3. **Fix unused arguments:** Remove or add `_` prefix
4. **Fix pytest.mark.parametrize:** Convert strings to tuples
5. **Fix mypy unused ignores:** Remove obsolete `# type: ignore`
6. **Fix decorator typing:** Add proper ignores or type stubs
7. **Migrate pre-commit config:** Run `pre-commit migrate-config`
8. **Disable ISC001:** Add to ruff ignore list

---

## Commands for Quick Fix

```bash
# Migrate pre-commit config
cd /Users/bruno/siopv
uv run pre-commit migrate-config

# Run auto-fixes
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/

# Re-test
uv run pre-commit run --all-files
```

---

**Status:** INSTALLATION COMPLETE, VALIDATION FAILED (expected for first run)
**Recommendation:** Fix issues in batches, re-run pre-commit after each fix
