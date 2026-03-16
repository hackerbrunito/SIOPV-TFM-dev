# Best-Practices-Enforcer — Remediation Final Audit v2

**Date:** 2026-03-16
**Agent:** best-practices-enforcer
**Phase:** 6 (remediation-hardening outputs)
**Scope:** Recently modified files under src/ and new test files

---

## Tool Results

### ruff check src tests

```
ARG002 Unused method argument: `settings`
  --> tests/unit/infrastructure/di/test_authentication_di.py:72:48

ARG002 Unused method argument: `mock_settings`
  --> tests/unit/infrastructure/di/test_authorization_di.py:86:55

Found 2 errors.
```

### mypy src

```
Success: no issues found in 99 source files
```

---

## Findings

### 1. Unused fixture argument in test (ARG002)

- **File:** `tests/unit/infrastructure/di/test_authentication_di.py:72`
- **Severity:** MEDIUM
- **Pattern:** `test_create_oidc_adapter_logging(self, settings: Settings)` declares `settings` as a parameter but never references it directly. The `autouse` fixture `patch_get_settings` already injects the settings via the patched `get_settings` call. The `settings` parameter here is superfluous — it's requested from the fixture system but unused inside the function body.
- **Fix:** Either remove `settings: Settings` from the signature (the `autouse` fixture is sufficient) or use `_settings: Settings` (underscore prefix) to signal intentional non-use. The cleaner fix is to remove it, since the test body only patches `logger` and calls `create_oidc_adapter()`.

---

### 2. Unused fixture argument in test (ARG002)

- **File:** `tests/unit/infrastructure/di/test_authorization_di.py:86`
- **Severity:** MEDIUM
- **Pattern:** `test_adapter_circuit_breaker_configured(self, mock_settings: MagicMock)` declares `mock_settings` but only calls `create_authorization_adapter()` and asserts on its return value. The `autouse` fixture `patch_get_settings` already patches `get_settings` globally; there is no need to request `mock_settings` here.
- **Fix:** Remove `mock_settings: MagicMock` from the test signature. The test calls `create_authorization_adapter()` internally through the autouse patch, which provides the correct values.

---

### 3. Stale docstring in DI __init__ (documentation drift)

- **File:** `src/siopv/infrastructure/di/__init__.py:20-31`
- **Severity:** LOW
- **Pattern:** The module docstring in `__init__.py` still shows the old API calling pattern that passes `settings` as an argument to each factory (`authz = get_authorization_port(settings)`, `create_oidc_middleware(settings)`). This contradicts the actual zero-argument factory functions. The docstring is stale after the refactor that moved settings retrieval inside the factories.
- **Fix:** Update the module docstring example to use the no-argument form: `authz = get_authorization_port()`, `middleware = create_oidc_middleware()`.

---

### 4. assert statement in production use case code

- **File:** `src/siopv/application/use_cases/classify_risk.py:122`
- **Severity:** MEDIUM
- **Pattern:** `assert self._feature_engineer is not None, "feature_engineer must be injected"` — using `assert` for mandatory invariant checking in a production code path is a 2026 anti-pattern. Python `assert` statements are silently stripped when running with the `-O` (optimize) flag, which means the guard disappears in optimized deployments. The check is correct logically but should use a proper runtime guard.
- **Fix:** Replace with an explicit check:
  ```python
  if self._feature_engineer is None:
      msg = "feature_engineer must be injected before calling execute()"
      raise ValueError(msg)
  ```

---

### 5. Hardcoded literal string `"SIOPV v0.1.0"` in CLI

- **File:** `src/siopv/interfaces/cli/main.py:265`
- **Severity:** LOW
- **Pattern:** `typer.echo("SIOPV v0.1.0")` — version string is hardcoded inside the function body rather than sourced from `domain/constants.py` or `importlib.metadata`. Per project rules, the app name and version must come from a single source of truth.
- **Fix:** Use `importlib.metadata.version("siopv")` or read from `domain/constants.py` where the version is defined. Alternatively, use the `__version__` pattern from the package root.

---

### 6. Docstring incomplete on `create_dual_layer_adapter` fallback warning

- **File:** `src/siopv/adapters/dlp/dual_layer_adapter.py:305`
- **Severity:** LOW
- **Pattern:** The docstring for `create_dual_layer_adapter` documents that `api_key` falls back to `ANTHROPIC_API_KEY` env var but does not mention the security implication — if neither `api_key` param nor env var is set, `resolved_key` becomes `""` (empty string) and Haiku calls will fail at runtime. This is acceptable (fail-open per design) but should be explicitly documented.
- **Fix:** Add a note: `If neither is provided, Haiku will be initialized with an empty key and Layer 2 calls will fail silently (fail-open per design).`

---

## Patterns Checked (All OK)

The following 2026 Python best practice categories were audited and found compliant across all target files:

| Category | Status | Notes |
|---|---|---|
| `from __future__ import annotations` | PASS | Present in all production files |
| Type hints — complete coverage | PASS | All public methods fully annotated; `TYPE_CHECKING` blocks used correctly |
| Pydantic v2 patterns | PASS | `ConfigDict(frozen=True)`, `@field_validator` with `@classmethod`, `Field(...)`, no v1 patterns |
| `structlog` usage | PASS | `structlog.get_logger(__name__)` at module level; structured key=value calls; no positional format strings |
| `pathlib.Path` instead of `os.path` | PASS | All path operations use `pathlib` |
| httpx usage | N/A | No direct httpx calls in audited files |
| `from __future__ import annotations` in test files | PASS | Present in all new test files |
| `@pytest.fixture` typing | PASS | All fixtures properly typed; `Generator[None, None, None]` used for yield fixtures |
| Async test patterns | PASS | `@pytest.mark.asyncio` used correctly; `AsyncMock` for coroutines |
| No banned imports (`os.path`, `typing.Dict`, `typing.List`) | PASS | Modern `dict[...]`, `list[...]` used throughout |
| `lru_cache(maxsize=1)` singleton pattern | PASS | Consistent across all DI factory functions |
| `__all__` declarations | PASS | All modules export `__all__` |
| Pydantic `SecretStr` for secrets | PASS | `anthropic_api_key` handled as `SecretStr`; `.get_secret_value()` called in DI layer |
| No bare `except Exception` without `exc_info=True` | PASS | All error paths log `exc_info=True` or re-raise |
| Ruff E501 line length | PASS | No violations found |

---

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 3 |
| LOW | 3 |
| **Total** | **6** |

**Breakdown by type:**
- 2 ruff ARG002 violations in test files (unused fixture arguments)
- 1 `assert` used as runtime guard in production code
- 1 stale docstring (API signature mismatch in DI `__init__`)
- 2 minor documentation gaps

---

## Verdict

**PASS** (0 CRITICAL + 0 HIGH)

The codebase is in excellent shape. mypy reports zero errors across 99 source files. All source files correctly apply Python 2026 standards: `from __future__ import annotations`, complete type annotations, Pydantic v2 patterns, structlog structured logging, and pathlib usage. The 3 MEDIUM findings are test-quality issues (unused fixtures, 1 assert guard) that should be fixed before the next commit, but they do not represent CRITICAL or HIGH violations.

### Recommended Fixes (prioritized)

1. **Immediate (before next commit):** Fix the 2 ruff ARG002 errors — remove unused `settings` and `mock_settings` parameters from the two test methods. These will block ruff CI.
2. **Short-term:** Replace the `assert` in `classify_risk.py:122` with an explicit `if ... raise ValueError(...)` guard.
3. **Low priority:** Fix stale docstring in `di/__init__.py` and add missing failure note in `create_dual_layer_adapter`.
