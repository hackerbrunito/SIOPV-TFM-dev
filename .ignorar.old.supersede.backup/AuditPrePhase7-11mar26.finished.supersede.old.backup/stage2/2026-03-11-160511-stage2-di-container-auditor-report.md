# di-container-auditor Report

**Agent:** di-container-auditor
**Team:** siopv-stage2
**Timestamp:** 2026-03-11-160511
**Files Audited:** 4

## Summary: 3 CORRECT, 1 PARTIAL, 0 VIOLATION

---

## Per-File Assessment

### `__init__.py` — CORRECT

- **Exports:** All 9 factory functions from the 3 submodules are imported and re-exported via `__all__`.
- **DLP exports:** `get_dlp_port` and `get_dual_layer_dlp_port` are both present in imports (line 47-48) and `__all__` (lines 58-59).
- **No logic:** This file is purely a re-export facade — no wiring logic, no instantiation. Appropriate.

### `authentication.py` — CORRECT

- **Port return types:**
  - `create_oidc_adapter()` → `KeycloakOIDCAdapter` (concrete factory, expected)
  - `get_oidc_authentication_port()` → `OIDCAuthenticationPort` (port type, correct)
- **Singleton:** `get_oidc_authentication_port` uses `@lru_cache(maxsize=1)` — correct.
- **Middleware factory:** `create_oidc_middleware` is NOT cached — acceptable since middleware instances may need separate lifecycle. It correctly obtains the port via `get_oidc_authentication_port(settings)`, reusing the singleton adapter.
- **Settings injection:** All configuration (issuer URL, audience, JWKS TTL, clock skew) comes from `settings`. No hardcoded values.
- **Adapter wiring:** `KeycloakOIDCAdapter` implements `OIDCAuthenticationPort` — wiring is correct.

### `authorization.py` — PARTIAL

- **Port return types:**
  - `create_authorization_adapter()` → `OpenFGAAdapter` (concrete factory, expected)
  - `get_authorization_port()` → `AuthorizationPort` (correct)
  - `get_authorization_store_port()` → `AuthorizationStorePort` (correct)
  - `get_authorization_model_port()` → `AuthorizationModelPort` (correct)
- **Singleton behavior:** Each `get_*` function has `@lru_cache(maxsize=1)` — correct per-function.
- **ISSUE — Multiple adapter instances:** Each of the 3 `get_*` functions independently calls `create_authorization_adapter(settings)`, which is NOT cached. This means up to **3 separate `OpenFGAAdapter` instances** are created (one per port function). Since `OpenFGAAdapter` implements all three ports, a single shared instance would be more correct and efficient. Separate instances mean:
  - Separate HTTP connection pools to OpenFGA
  - Separate circuit breaker state (one could be open while another is closed)
  - Separate `initialize()` calls needed
  - This is not a hard violation (each instance works), but it's a DI design flaw that could cause subtle state inconsistencies.
- **Settings injection:** All configuration comes from `settings`. No hardcoded values in DI file.
- **Adapter wiring:** `OpenFGAAdapter` implements all three port interfaces — wiring is correct per-port.

**Recommendation:** Cache `create_authorization_adapter` with `@lru_cache(maxsize=1)` or have all three `get_*` functions share a single adapter instance.

### `dlp.py` — CORRECT

- **Port return types:**
  - `create_presidio_adapter()` → `PresidioAdapter` (concrete factory, expected)
  - `get_dlp_port()` → `DLPPort` (port type, correct)
  - `create_dual_layer_dlp_adapter()` → `DualLayerDLPAdapter` (concrete factory, expected)
  - `get_dual_layer_dlp_port()` → `DLPPort` (port type, correct)
- **Singleton:** Both `get_dlp_port` and `get_dual_layer_dlp_port` use `@lru_cache(maxsize=1)` — correct.
- **Settings injection:** `api_key` from `settings.anthropic_api_key.get_secret_value()`, `haiku_model` from `settings.claude_haiku_model`. No hardcoded values in DI file.
- **Structural subtyping:** Comments on lines 70 and 119 note that adapters satisfy `DLPPort` via Protocol — appropriate for duck-typed compliance.
- **Adapter wiring:** `PresidioAdapter` and `DualLayerDLPAdapter` both satisfy `DLPPort` Protocol — correct.

---

## Known Issue Status

### Finding #5 (DLP exports): RESOLVED

Both `get_dlp_port` and `get_dual_layer_dlp_port` are:
- Imported in `__init__.py` (lines 47-48)
- Listed in `__all__` (lines 58-59)
- Fully functional factory functions in `dlp.py`

### Finding #6 (Hardcoded model IDs): NOT FOUND in DI files

The DI files read `settings.claude_haiku_model` (dlp.py line 37) rather than hardcoding model IDs. If hardcoded defaults exist, they would be in the `Settings` class definition (`settings.py`), not in the DI container. This finding is outside DI scope — defer to settings auditor.

---

## Ambiguities Noted

1. **authorization.py multi-instance pattern:** Whether the 3 separate `OpenFGAAdapter` instances is intentional (isolation) or accidental (oversight) cannot be determined from DI files alone. The authentication module avoids this issue because only one port function exists.
2. **DLPPort Protocol compliance:** The comments state adapters satisfy `DLPPort` via structural subtyping (Protocol). This is not verified at the DI layer — runtime or mypy would catch mismatches. Noted but not actionable here.
