# STAGE-3 Deep Scan: OpenFGA Authorization Integration
**Agent:** scanner-openfga
**Timestamp:** 2026-03-11-180630
**Wave:** R2-B

---

## 1. Files Scanned

| File | Lines | Role |
|------|-------|------|
| `application/orchestration/nodes/authorization_node.py` | 385 | LangGraph auth gatekeeper node |
| `application/ports/authorization.py` | ~160 | Port interface definitions |
| `infrastructure/di/authorization.py` | 213 | DI factory functions |
| `adapters/authorization/__init__.py` | ~10 | Package exports |
| `adapters/authorization/openfga_adapter.py` | 1207 | Concrete OpenFGA implementation |

---

## 2. OpenFGAAdapter Instantiation Audit

### Finding F-01 (MEDIUM — CONFIRMED STAGE-2 #5): 3 Independent Adapter Instances

**Root cause:**
`create_authorization_adapter()` at `di/authorization.py:52` is **NOT decorated with `@lru_cache`**.
Each of the 3 port getter functions calls it independently:

```python
# di/authorization.py:100-132
@lru_cache(maxsize=1)
def get_authorization_port(settings: Settings) -> AuthorizationPort:
    adapter = create_authorization_adapter(settings)   # NEW instance
    ...

@lru_cache(maxsize=1)
def get_authorization_store_port(settings: Settings) -> AuthorizationStorePort:
    adapter = create_authorization_adapter(settings)   # ANOTHER new instance

@lru_cache(maxsize=1)
def get_authorization_model_port(settings: Settings) -> AuthorizationModelPort:
    adapter = create_authorization_adapter(settings)   # THIRD new instance
```

**Effect:**
- Each port getter is individually cached via `@lru_cache(maxsize=1)`, but the adapter factory itself is not
- 3 `OpenFGAAdapter` objects → 3 independent `OpenFgaClient` connections → 3 circuit breakers → 3 `_cached_model_id` states
- If the same model ID is retrieved by one adapter, the other two remain unaware
- `initialize()` must be called on each separately — the DI docstring explicitly warns callers to call it, but no shared lifecycle management exists

**Locations:**
- `di/authorization.py:52` — `create_authorization_adapter()` (uncached)
- `di/authorization.py:100` — `get_authorization_port()` (cached, but instantiates fresh adapter)
- `di/authorization.py:135` — `get_authorization_store_port()` (idem)
- `di/authorization.py:174` — `get_authorization_model_port()` (idem)

---

## 3. Port Purity Verification

**PASS — Port is a pure abstract interface.**

`application/ports/authorization.py` uses `typing.Protocol` with `@runtime_checkable`:

```python
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from siopv.domain.authorization import (
        AuthorizationContext, AuthorizationResult, ...
    )

@runtime_checkable
class AuthorizationPort(Protocol):
    async def check(self, context: AuthorizationContext) -> AuthorizationResult: ...
```

- Zero runtime concrete imports (all under `TYPE_CHECKING` guard)
- No ABC/base class inheritance required from implementors
- Structural subtyping: any class with matching methods satisfies the port
- `@runtime_checkable` allows `isinstance()` checks at runtime

**STAGE-2 assessment confirmed: port is clean.**

---

## 4. Authorization Node Pattern

**PASS — Fully async, no asyncio.run() anywhere.**

```python
# authorization_node.py:290-294
async def authorization_node(
    state: PipelineState,
    *,
    authorization_port: AuthorizationPort | None = None,
) -> dict[str, object]:
```

- Node function is `async def` — native LangGraph async node ✅
- Port call chain: `authorization_node` → `_execute_authorization_check` → `_run_authorization_check` → `await port.check(context)` — all async throughout
- `asyncio.run()` is **absent** from the file ✅
- Fail-secure implemented correctly:
  - No user_id + no `system_execution` flag → deny (`authorization_node.py:147`)
  - `authorization_port is None` → deny (`authorization_node.py:333`)
  - `AuthorizationCheckError` exception → deny (`authorization_node.py:348`)
  - Any unexpected exception → deny (`authorization_node.py:354`)
- PII protection: user_id pseudonymized via SHA-256 hash in all log events (`_pseudonymize()` at line 108)

**Authorization check performed:**
- Relation: `Action.VIEW` → mapped to first entry of `ActionPermissionMapping.default_mappings()[Action.VIEW].required_relations`
- Object: `ResourceType.PROJECT` with `project_id` from state (default: `"default"` if absent)
- Tuple format: `check(user:X, relation:viewer, object:project:Y)` — per spec section 3.5 ✅

---

## 5. OpenFGA Configuration Audit

**Configuration is fully settings-driven (clean):**

| Setting | Where read | Method |
|---------|-----------|--------|
| `openfga_api_url` | `adapter.py:114` | `settings.openfga_api_url` |
| `openfga_store_id` | `adapter.py:115` | `settings.openfga_store_id` |
| `openfga_authorization_model_id` | `adapter.py:116` | `getattr(settings, ..., None)` |
| `openfga_auth_method` | `adapter.py:117` | `getattr(settings, ..., "none")` |
| `openfga_api_token` | `adapter.py:118` | `getattr(settings, ..., None)` |
| `openfga_client_id` / `_secret` | `adapter.py:119-120` | `getattr(settings, ..., None)` |
| `openfga_api_audience` | `adapter.py:121` | `getattr(settings, ..., None)` |
| `openfga_api_token_issuer` | `adapter.py:122` | `getattr(settings, ..., None)` |

**Auth methods supported:** `none`, `api_token`, `client_credentials`
**Secrets handling:** `SecretStr.get_secret_value()` used at `adapter.py:181,189` — no plaintext exposure ✅

**Finding F-02 (LOW): `getattr()` fallback pattern hides missing settings**

`getattr(settings, "openfga_authorization_model_id", None)` silently returns `None` if the setting is absent from the `Settings` class definition. This prevents startup-time validation errors for optional-but-important config like model ID. Not a security issue, but reduces observability.

**Finding F-03 (LOW): `initialize()` lifecycle not enforced by DI**

The DI docstring warns: *"The port is not automatically initialized"*. There is no `asyncio.run()` or `await adapter.initialize()` call in `di/authorization.py`. The burden is on the caller (e.g., `graph.py` startup) to call `initialize()` on each adapter. If multiple adapters exist (F-01), all three must be initialized separately.

---

## 6. Phase 7 Reuse Assessment

**PARTIAL READY — Adapter is reusable; async bridging required for Streamlit.**

**What works for Phase 7:**
- `AuthorizationPort.check()` can gate Streamlit page access with same relation checks
- `AuthorizationPort.batch_check()` available for multi-resource checks (useful if UI shows multiple projects)
- Port is a Protocol — Streamlit session can hold an `AuthorizationPort` reference without any changes to adapter
- Circuit breaker + retry already handles transient failures

**Blockers for Phase 7:**

| Blocker | Severity | Detail |
|---------|----------|--------|
| Streamlit sync context | HIGH | Streamlit runs in a sync thread by default; `await port.check()` cannot be called directly — need `asyncio.run()` wrapper or `asyncio.get_event_loop().run_until_complete()` in session callbacks |
| `initialize()` lifecycle | MEDIUM | Streamlit has no async startup hook — adapter must be initialized once per session or globally via `st.cache_resource` with async bridge |
| 3 adapter instances | MEDIUM | If Phase 7 uses `get_authorization_port(settings)` alongside Phase 5's usage, they share the same cached instance (same `settings` object) — but only if the same `settings` singleton is used |
| No Streamlit-specific relation | LOW | Current model only has `Action.VIEW` on `ResourceType.PROJECT` — may need `Action.EDIT` or UI-specific roles for admin views |

**Recommended Phase 7 pattern:**
```python
# In Streamlit app initialization
import asyncio
from siopv.infrastructure.di.authorization import get_authorization_port
from siopv.infrastructure.config import get_settings

@st.cache_resource
def get_authz_port():
    settings = get_settings()
    port = get_authorization_port(settings)
    asyncio.run(port.initialize())  # One-time async init
    return port
```

---

## 7. Recommended Fix Patterns for REMEDIATION-HARDENING

### Fix RH-01: Consolidate to single shared adapter instance (addresses F-01)

```python
# infrastructure/di/authorization.py

@lru_cache(maxsize=1)
def _get_shared_adapter(settings: Settings) -> OpenFGAAdapter:
    """Single cached adapter shared across all ports."""
    return create_authorization_adapter(settings)

@lru_cache(maxsize=1)
def get_authorization_port(settings: Settings) -> AuthorizationPort:
    return _get_shared_adapter(settings)

@lru_cache(maxsize=1)
def get_authorization_store_port(settings: Settings) -> AuthorizationStorePort:
    return _get_shared_adapter(settings)

@lru_cache(maxsize=1)
def get_authorization_model_port(settings: Settings) -> AuthorizationModelPort:
    return _get_shared_adapter(settings)
```

**Effect:** 1 adapter, 1 OpenFGA connection, 1 circuit breaker, 1 model ID cache.

### Fix RH-02: Enforce settings-level validation for optional OpenFGA fields (addresses F-02)

Add Pydantic field validators in `Settings` for `openfga_authorization_model_id` and `openfga_auth_method` to emit startup warnings rather than silently defaulting.

### Fix RH-03: Add async lifecycle manager for DI (addresses F-03)

Create an `async def initialize_authorization(settings: Settings)` function in `di/authorization.py` that calls `_get_shared_adapter(settings).initialize()` — to be called once at graph startup.

---

## 8. Summary

1. **F-01 (MEDIUM — CONFIRMED):** 3 independent `OpenFGAAdapter` instances due to uncached `create_authorization_adapter()` factory — each port getter (`get_authorization_port`, `get_authorization_store_port`, `get_authorization_model_port`) creates its own adapter despite individual `@lru_cache`. Fix: add `@lru_cache` to a shared `_get_shared_adapter()` function.

2. **Port is clean:** `AuthorizationPort` is a pure `typing.Protocol` with all concrete imports under `TYPE_CHECKING` — zero leakage into domain layer. No action needed.

3. **Node is fully async:** `authorization_node` is `async def`, calls `await port.check()`, no `asyncio.run()` anywhere — correct LangGraph integration. Fail-secure on all error paths confirmed.

4. **Configuration is safe:** All credentials via `Settings` + `SecretStr.get_secret_value()`, no hardcoded URLs or tokens. Minor risk: `getattr()` fallbacks silently accept missing settings without startup errors.

5. **Phase 7 reusable but needs async bridge:** The adapter and port are architecturally ready for Streamlit — same `check()` semantics work for UI gating — but Streamlit's sync context requires an `asyncio.run()` wrapper or `st.cache_resource` async initialization pattern. The 3-instance issue (F-01) should be fixed before Phase 7 to avoid triple connection overhead in the UI layer.
