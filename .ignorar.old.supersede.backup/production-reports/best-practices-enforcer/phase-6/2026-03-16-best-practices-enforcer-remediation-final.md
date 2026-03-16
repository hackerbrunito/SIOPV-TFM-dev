# Best Practices Enforcer — Remediation-Hardening Final Audit
**Date:** 2026-03-16
**Agent:** best-practices-enforcer
**Phase:** 6 (DLP / Presidio)
**Scope:** 20 Python files modified in the last 14 days under `src/`
**Standards:** Python 2026 — type hints, Pydantic v2, httpx, structlog, pathlib

---

## Files Audited (20 total)

| File | Modified |
|------|----------|
| `src/siopv/adapters/dlp/dual_layer_adapter.py` | recent |
| `src/siopv/adapters/dlp/haiku_validator.py` | recent |
| `src/siopv/adapters/dlp/presidio_adapter.py` | recent |
| `src/siopv/application/orchestration/edges.py` | recent |
| `src/siopv/application/orchestration/graph.py` | recent |
| `src/siopv/application/orchestration/nodes/authorization_node.py` | recent |
| `src/siopv/application/orchestration/nodes/dlp_node.py` | recent |
| `src/siopv/application/orchestration/nodes/enrich_node.py` | recent |
| `src/siopv/application/orchestration/nodes/ingest_node.py` | recent |
| `src/siopv/application/ports/__init__.py` | recent |
| `src/siopv/application/ports/feature_engineering.py` | recent |
| `src/siopv/application/ports/parsing.py` | recent |
| `src/siopv/application/use_cases/classify_risk.py` | recent |
| `src/siopv/application/use_cases/ingest_trivy.py` | recent |
| `src/siopv/domain/authorization/value_objects.py` | recent |
| `src/siopv/domain/services/discrepancy.py` | recent |
| `src/siopv/infrastructure/di/__init__.py` | recent |
| `src/siopv/infrastructure/di/authorization.py` | recent |
| `src/siopv/infrastructure/logging/setup.py` | recent |
| `src/siopv/interfaces/cli/main.py` | recent |

---

## Tool Verification Results

| Tool | Result |
|------|--------|
| `ruff check src/` | ✅ All checks passed |
| `uv run mypy src/` | ✅ Success: no issues found in 99 source files |

---

## Findings

### 1. `assert` Used as Runtime Guard in Production Use Case

- **File:** `src/siopv/application/use_cases/classify_risk.py:122`
- **Severity:** MEDIUM
- **Pattern:** `assert` statement used for runtime validation, not just testing.
- **Current:**
  ```python
  assert self._feature_engineer is not None, "feature_engineer must be injected"
  ```
- **Expected:**
  ```python
  if self._feature_engineer is None:
      msg = "feature_engineer must be injected"
      raise RuntimeError(msg)
  ```
- **Fix:** Replace with explicit `if` guard + `raise RuntimeError`. The `assert` statement is stripped when Python runs with `-O` (optimize) flag, making this a silent failure in optimized production deployments.

---

### 2. `os.environ.get` Bypass of Settings/SecretStr in Factory Function

- **File:** `src/siopv/adapters/dlp/dual_layer_adapter.py:305`
- **Severity:** LOW
- **Pattern:** Direct `os.environ.get` access in a factory function instead of requiring the caller to pass the resolved secret from Pydantic `SecretStr`.
- **Current:**
  ```python
  resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
  ```
- **Expected:** Factory should require `api_key` be passed explicitly from DI layer (no env fallback in adapters). The `Settings` class is the canonical env var reader.
- **Fix:** The DI module (`infrastructure/di/dlp.py`) already correctly calls `settings.anthropic_api_key.get_secret_value()` and passes it to `create_dual_layer_adapter()`. The fallback is a minor smell but is not reachable through the normal production path. Document intent or remove env fallback to enforce strict hexagonal boundaries.
- **Note:** This is LOW severity because the production code path goes through `infrastructure/di/dlp.py` which uses SecretStr correctly. The `os.environ` path is only reachable from tests or direct ad-hoc instantiation.

---

### 3. Hardcoded Version String in CLI

- **File:** `src/siopv/interfaces/cli/main.py:266`
- **Severity:** LOW
- **Pattern:** Version string `"SIOPV v0.1.0"` hardcoded in `version` command instead of reading from `pyproject.toml` via `importlib.metadata`.
- **Current:**
  ```python
  typer.echo("SIOPV v0.1.0")
  ```
- **Expected:**
  ```python
  from importlib.metadata import version as _pkg_version
  typer.echo(f"SIOPV v{_pkg_version('siopv')}")
  ```
- **Fix:** Use `importlib.metadata.version()` to avoid version drift. Low priority since it matches `pyproject.toml` `version = "0.1.0"` currently.

---

### 4. `structlog` PII Masking Not Configured (Pre-existing Phase-0 Gap)

- **File:** `src/siopv/infrastructure/logging/setup.py`
- **Severity:** MEDIUM (pre-existing, tracked in CLAUDE.md Phase-0 MISSING list)
- **Pattern:** The `configure_logging()` function does not include a custom structlog processor to mask/redact sensitive field values (e.g., `user_id`, `api_key`, `email`). This is listed in CLAUDE.md as one of 5 Phase-0 MISSING items.
- **Current:** No masking processor in the shared_processors chain.
- **Expected:** A custom processor that redacts or hashes sensitive fields before emission (e.g., a `SensitiveMaskingProcessor` added to `shared_processors`).
- **Fix:** Implement and add a masking processor to `configure_logging()`. This is a known tracked gap — not introduced by remediation-hardening, but remains unresolved.
- **Note:** The authorization node already pseudonymizes `user_id` before logging (via `_pseudonymize()`), which partially mitigates this for the most sensitive field. Full masking at the logging layer is still needed for defense-in-depth.

---

## Compliant Areas (No Issues Found)

The following best practices areas are **fully compliant** across all 20 audited files:

| Category | Status | Evidence |
|----------|--------|---------|
| Type hints — all function signatures typed | ✅ PASS | All public functions annotated; `from __future__ import annotations` used where needed |
| `|` union syntax (Python 3.10+ native) | ✅ PASS | No legacy `Optional[X]` — all use `X \| None` |
| Pydantic v2 patterns | ✅ PASS | `model_config = ConfigDict(frozen=True)`, `@field_validator` with `@classmethod`, `Annotated` fields |
| No Pydantic v1 patterns | ✅ PASS | No `@validator`, `orm_mode`, `.dict()`, `schema_extra` |
| `structlog` usage | ✅ PASS | All modules use `structlog.get_logger(__name__)`, structured key-value logging |
| `pathlib.Path` usage | ✅ PASS | No bare `open()`; graph.py and ingest use `Path` throughout |
| `httpx` for HTTP clients | ✅ PASS | All HTTP adapters use `httpx`; no `requests` library found |
| `from __future__ import annotations` | ✅ PASS | Present in all files with forward references; not needed in Python 3.10+ base files |
| `SecretStr.get_secret_value()` | ✅ PASS | DI layer uses `settings.anthropic_api_key.get_secret_value()` correctly |
| Protocol-based ports | ✅ PASS | All ports use `Protocol` with `@runtime_checkable` |
| `dataclass(frozen=True)` for value objects | ✅ PASS | `ClassificationResult`, `IngestionResult`, `ClassificationStats` all frozen |
| `StrEnum` for enumerations | ✅ PASS | `ResourceType`, `Relation`, `Action` use `StrEnum` |
| Async correctness | ✅ PASS | Sync Presidio/Haiku calls wrapped in `loop.run_in_executor()`; no blocking in event loop |
| Lambda only for synchronous nodes | ✅ PASS | `classify_node` is `def` (not `async`); lambda wrapping is correct |
| Exception handling | ✅ PASS | Specific exceptions caught before broad `Exception`; fail-open/fail-secure patterns documented |
| No legacy `Optional`, `List`, `Dict` | ✅ PASS | All use built-in generics (`list[...]`, `dict[...]`) |
| `__all__` defined | ✅ PASS | All public modules define `__all__` |
| Docstrings | ✅ PASS | All public classes, methods, and functions have complete Google-style docstrings |
| Magic numbers extracted | ✅ PASS | `_HAIKU_MAX_TOKENS`, `MIN_SHORT_TEXT_LENGTH`, `MAX_TEXT_LENGTH` as named constants |

---

## Summary

| Severity | Count | Details |
|----------|-------|---------|
| CRITICAL | 0 | — |
| HIGH | 0 | — |
| MEDIUM | 2 | `assert` guard (#1), missing structlog masking (#4, pre-existing Phase-0 gap) |
| LOW | 2 | `os.environ` fallback in factory (#2), hardcoded version string (#3) |
| **Total** | **4** | |

---

## Verdict

**PASS** — 0 CRITICAL, 0 HIGH violations.

The remediation-hardening changes to 20 files are compliant with 2026 Python best practices. All tool checks pass cleanly (`ruff`: 0 errors, `mypy`: 0 errors across 99 source files).

The 2 MEDIUM findings are:
1. A single `assert` in `classify_risk.py` that should be replaced with an explicit raise (low-effort fix, safe to defer to Phase 7 cleanup).
2. Absence of structlog PII masking in `logging/setup.py` — a pre-existing Phase-0 gap tracked in CLAUDE.md, not introduced by this remediation cycle.

The 2 LOW findings are minor code style issues with no security or correctness impact in the current production path.

**Recommendation:** Address finding #1 (`assert` → `raise RuntimeError`) before Phase 7 starts. Findings #2 and #3 can be deferred. Finding #4 (structlog masking) is already tracked and must be addressed before production deployment.
