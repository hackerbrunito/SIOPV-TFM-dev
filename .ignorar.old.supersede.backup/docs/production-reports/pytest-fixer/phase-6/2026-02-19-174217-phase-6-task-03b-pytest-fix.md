# pytest-fixer Report — Phase 6 Task 03b

**STATUS: PASS**
**Date:** 2026-02-19
**Agent:** pytest-fixer
**Scope:** Fix 7 failing tests in ~/siopv/

---

## Summary

All 7 target failures fixed. Final run: **1 failed, 1239 passed, 12 skipped** (the 1 remaining failure is pre-existing in `test_dual_layer_adapter.py`, outside scope).

**Coverage: 80% (TOTAL)**

---

## Root Causes & Fixes

### Failure Group 1 — 4 failures in `test_authentication_di.py`

**Error:** `TypeError: id() takes exactly one argument (0 given)`

**Root Cause:**
Commit `c1a7754` changed the `_make_settings_hashable` autouse fixture from:
```python
monkeypatch.setattr(Settings, "__hash__", lambda self: id(self))
```
to:
```python
monkeypatch.setattr(Settings, "__hash__", id)
```

`id` is a C-level builtin function. When set as a class attribute, it does NOT act as a descriptor (unlike Python `def` functions). Python's `slot_tp_hash` looks up `__hash__` and calls it — but without binding the instance as `self`. This results in `id()` being invoked with 0 arguments.

**Fix:** Reverted to `lambda self: id(self)` in `tests/unit/infrastructure/di/test_authentication_di.py` line 54. A Python lambda does implement the descriptor protocol, so `self` is properly bound when called via the type.

**Tests fixed:**
- `TestGetOIDCAuthenticationPort::test_get_oidc_authentication_port_cached`
- `TestGetOIDCAuthenticationPort::test_get_oidc_authentication_port_returns_adapter`
- `TestCreateOIDCMiddleware::test_create_oidc_middleware_success`
- `TestCreateOIDCMiddleware::test_create_oidc_middleware_logging`

---

### Failure Group 2 — 2 failures in `test_oidc_middleware.py`

**Error:** `AttributeError: 'AuthorizationContext' object has no attribute 'user_id'`

**Root Cause:**
`AuthorizationContext` (domain entity in `entities.py`) stores the user as `user: UserId` (a Pydantic model). The tests incorrectly asserted `context.user_id == "..."` — this attribute does not exist. The correct path is `context.user.value`.

**Fix:** Changed two assertions in `tests/unit/infrastructure/middleware/test_oidc_middleware.py`:
- Line 301: `context.user_id` → `context.user.value`
- Line 336: `context.user_id` → `context.user.value`

**Tests fixed:**
- `TestAuthenticateAndAuthorize::test_authenticate_and_authorize_success`
- `TestAuthenticateAndAuthorize::test_authenticate_and_authorize_maps_identity_to_user_id`

---

### Failure Group 3 — 1 failure in `test_oidc_middleware.py`

**Error:** `AssertionError: assert ('siopv-client' in '' or 'client_id' in '')`

**Root Cause:**
`test_authenticate_logs_only_metadata` configures structlog with:
```python
structlog.configure(
    processors=[structlog.processors.add_log_level, structlog.processors.KeyValueRenderer()],
)
```
Without `logger_factory`, structlog defaults to `PrintLogger` which writes to stdout/stderr. `pytest`'s `caplog` fixture only captures Python stdlib `logging` records. So `caplog.records` was always empty, and the assertion on `log_output` failed.

**Fix:** Updated the test to configure structlog with stdlib routing and set the caplog level:
```python
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.KeyValueRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=False,
)
# ...
with caplog.at_level(logging.INFO):
    await middleware.authenticate("Bearer token")
```
`cache_logger_on_first_use=False` ensures the new config applies to the already-imported module-level logger in `oidc_middleware.py`.

**Tests fixed:**
- `TestSecurityNoTokenLogging::test_authenticate_logs_only_metadata`

---

## Pre-existing Failure (Out of Scope)

`tests/unit/adapters/dlp/test_dual_layer_adapter.py::TestHaikuDLPAdapterJSONParsing::test_sensitive_found_returns_sanitized_text`

This failure was present before my changes (not in the 7 identified failures). It asserts `DLPResult.semantic_passed is False` but the adapter returns `True`. Not related to OIDC or DI changes.

---

## Files Modified

| File | Change |
|------|--------|
| `tests/unit/infrastructure/di/test_authentication_di.py` | Line 54: `id` → `lambda self: id(self)` |
| `tests/unit/infrastructure/middleware/test_oidc_middleware.py` | Lines 301, 336: `context.user_id` → `context.user.value` |
| `tests/unit/infrastructure/middleware/test_oidc_middleware.py` | `test_authenticate_logs_only_metadata`: add stdlib logging config + `caplog.at_level` |

---

## Final Test Results

```
1 failed, 1239 passed, 12 skipped
Coverage: 80% (TOTAL)
```

Target failures: **0/7 remaining** ✅
Coverage threshold (>=80%): **MET** ✅
