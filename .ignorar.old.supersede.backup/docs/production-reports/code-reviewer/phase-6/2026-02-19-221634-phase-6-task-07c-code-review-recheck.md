# Code Review Report — Phase 6 DLP (Re-check after Fixes)

**Status:** ✅ PASS
**Final Score:** 9.3 / 10
**Timestamp:** 2026-02-19-221634
**Task:** Task 07c — Code Reviewer Re-check
**Phase:** 6
**Wave:** Wave 2 (re-run)

---

## Executive Summary

All 3 previously blocking issues have been confirmed resolved. The codebase now scores 9.3/10, exceeding the PASS threshold of ≥ 9.0/10. The DLP layer demonstrates clean hexagonal architecture, proper async patterns, and good DRY discipline.

---

## Score Breakdown

| Dimension | Available | Score | Notes |
|-----------|-----------|-------|-------|
| Complexity & Maintainability | 4 | 3.5 | 2 long functions, but both clearly structured |
| DRY & Duplication | 2 | 2.0 | `_haiku_utils.py` extraction eliminates all duplication |
| Naming & Clarity | 2 | 1.9 | Excellent throughout; minor: `raw` variable name in `dual_layer_adapter.py` |
| Performance | 1 | 1.0 | All async antipatterns fixed |
| Testing | 1 | 0.9 | Highly testable design; slight penalty for `lru_cache` test isolation |
| **TOTAL** | **10** | **9.3** | **PASS** |

---

## Confirmation: 3 Previously Blocking Issues

### Issue 1 — `asyncio.get_event_loop()` → `asyncio.get_running_loop()` ✅ RESOLVED

All three files have been corrected:

- **`presidio_adapter.py` line 233:**
  ```python
  loop = asyncio.get_running_loop()
  ```
  Confirmed. Uses `get_running_loop()` — raises `RuntimeError` if called outside a coroutine (correct behavior for an async adapter).

- **`haiku_validator.py` line 104:**
  ```python
  loop = asyncio.get_running_loop()
  ```
  Confirmed. `validate()` is an `async def`, so `get_running_loop()` is always valid here.

- **`dual_layer_adapter.py` line 116:**
  ```python
  loop = asyncio.get_running_loop()
  ```
  Confirmed in `_HaikuDLPAdapter.sanitize()` — `async def` context, correct usage.

**Assessment:** Issue fully resolved. The deprecated `get_event_loop()` (which silently creates a new event loop in Python 3.10+ when none exists) has been replaced in all three sites.

---

### Issue 2 — DRY Violation: Shared Haiku Utility Extracted to `_haiku_utils.py` ✅ RESOLVED

The new `_haiku_utils.py` module consolidates:

```python
# _haiku_utils.py
MAX_TEXT_LENGTH: int = 4_000

def create_haiku_client(api_key: str) -> anthropic.Anthropic: ...
def truncate_for_haiku(text: str) -> str: ...
def extract_text_from_response(response: Message) -> str: ...
```

Both consuming adapters import cleanly:

- **`haiku_validator.py` lines 19-24:**
  ```python
  from siopv.adapters.dlp._haiku_utils import (
      MAX_TEXT_LENGTH,
      create_haiku_client,
      extract_text_from_response,
      truncate_for_haiku,
  )
  ```

- **`dual_layer_adapter.py` lines 27-32:**
  ```python
  from siopv.adapters.dlp._haiku_utils import (
      MAX_TEXT_LENGTH,
      create_haiku_client,
      extract_text_from_response,
      truncate_for_haiku,
  )
  ```

The backward-compatible alias in `haiku_validator.py` line 27:
```python
_MAX_TEXT_LENGTH = MAX_TEXT_LENGTH
```
is acceptable — it preserves existing test compatibility without re-introducing duplication.

**Assessment:** Issue fully resolved. Zero code duplication remains for Haiku client creation, text truncation, constant definition, or response extraction.

---

### Issue 3 — Sequential `for/await` → `asyncio.gather()` in `sanitize_vulnerability.py` ✅ RESOLVED

`SanitizeVulnerabilityUseCase.execute()` lines 85-87:

```python
results: list[tuple[VulnerabilityRecord, DLPResult]] = list(
    await asyncio.gather(*[self._sanitize_one(vuln) for vuln in vulnerabilities])
)
```

**Assessment:** Issue fully resolved. All vulnerability records are now processed concurrently. The previous sequential `for vuln in vulnerabilities: await self._dlp_port.sanitize(...)` pattern has been replaced with `asyncio.gather()` which fans out all sanitization coroutines concurrently. For a list of N vulnerabilities, latency is now O(max_single_item) instead of O(N × single_item).

---

## Detailed File-by-File Review

### 1. `domain/privacy/entities.py`

**Lines:** 113
**Complexity:** All methods ≤ 2. `safe_text()` factory is 7 lines. `computed_field` properties are one-liners.

**Positives:**
- Pydantic v2 `ConfigDict(frozen=True)` — correct immutability pattern.
- `@computed_field` with `# type: ignore[prop-decorator]` comment explains the known mypy incompatibility — honest and non-suppressive.
- `DLPResult.safe_text()` factory method is a well-named convenience constructor that reduces boilerplate at call sites throughout the codebase.
- Field docstrings are clear and precise.

**Issues:** None.

**Score contribution:** Excellent.

---

### 2. `domain/privacy/value_objects.py`

**Lines:** 134
**Complexity:** `from_presidio()` = 2 (one conditional).

**Positives:**
- `PIIEntityType(str, Enum)` — correctly inherits from `str` for JSON serialization compatibility.
- `from_presidio()` type_map is large but justified — it's a complete Presidio-to-domain entity mapping with sensible fallback defaults (e.g., `DATE_TIME → NRP`, `ORGANIZATION → PERSON`).
- The mapping comment annotations (`# National Registration/ID number`) add clarity.
- Fallback `type_map.get(entity_type, PIIEntityType.SECRET_TOKEN)` is a safe default.

**Issues:**
- Minor: `DATE_TIME → NRP` and `LOCATION → NRP` are debatable semantic mappings, but these are domain decisions that belong in a separate design review, not a code quality flag.

**Score contribution:** Excellent.

---

### 3. `domain/privacy/exceptions.py`

**Lines:** 30
**Complexity:** 0 (pure exception hierarchy).

**Positives:**
- Clean 3-level hierarchy: `DLPError → SanitizationError / PresidioUnavailableError / SemanticValidationError`.
- Each exception has a clear, specific purpose.
- Naming is self-documenting.

**Issues:** None.

**Score contribution:** Excellent.

---

### 4. `application/ports/dlp.py`

**Lines:** 71
**Complexity:** 0 (Protocol interfaces, no logic).

**Positives:**
- `@runtime_checkable` enables `isinstance()` checks without inheritance — compatible with structural subtyping adapters.
- `TYPE_CHECKING` guard for imports prevents circular imports at runtime.
- Docstrings clearly document the fail-open contract: `"True on validator errors (fail-open — Presidio already ran)"`.
- Both protocols are minimal (1 method each) — single responsibility.

**Issues:** None.

**Score contribution:** Excellent.

---

### 5. `adapters/dlp/presidio_adapter.py`

**Lines:** 272
**Complexity:** `sanitize()` = 3, `_run_presidio()` = 3, `_build_analyzer()` = 2.

**Positives:**
- Lazy import fallback pattern for Presidio (`_presidio_analyzer_err`) is clean — defers `PresidioUnavailableError` to first use rather than import time.
- Custom `PatternRecognizer` for API keys/tokens adds meaningful detection beyond Presidio defaults.
- `_run_presidio()` is a pure function (takes inputs, returns outputs) — easily testable without adapter state.
- `asyncio.get_running_loop()` ✅ (confirmed fixed).
- `functools.partial()` usage is correct for passing bound arguments to `run_in_executor`.
- Per-entity `OperatorConfig` map with `DEFAULT` fallback is robust.
- Structured log keys are consistent: `dlp_sanitization_complete`, `presidio_adapter_initialized`.

**Issues:**
- `_run_presidio()` is 65 lines total (including docstring) / ~45 lines of code. Slightly exceeds the 30-line advisory threshold. However, the function's 4-step flow (analyze → early-return → operators → anonymize → convert) is clearly commented and there's no obvious extraction point that wouldn't create artificial helper functions.
- `# type: ignore[attr-defined]` on `analyzer.analyze()` and `anonymizer.anonymize()` — necessary given the optional import pattern, but slightly reduces static analysis coverage.

**Score contribution:** Very good. Minor length advisory only.

---

### 6. `adapters/dlp/haiku_validator.py`

**Lines:** 138
**Complexity:** `validate()` = 4 (2 short-circuits + try/except + is_safe conditional).

**Positives:**
- Clean import from `_haiku_utils` — all shared logic is delegated ✅.
- `_MAX_TEXT_LENGTH = MAX_TEXT_LENGTH` backward alias is documented with a comment — transparent.
- Short-circuit logic is well-ordered: empty text check first (cheapest), then length check.
- Fail-open `except Exception:` with `exc_info=True` preserves stack trace in structured logs.
- `max_tokens=10` is appropriately minimal for a SAFE/UNSAFE response.
- The `answer.upper()` normalization is defensive but cheap.

**Issues:**
- `validate()` body is ~45 lines of code (excluding docstring). Slightly long, but the structure is sequential and not complex.
- The `detections` parameter is accepted but only used for the short-circuit condition (`not detections`). If the intent is to provide context to Haiku, it's currently not included in the prompt. This is a design consideration, not a code quality issue per se.

**Score contribution:** Very good.

---

### 7. `adapters/dlp/_haiku_utils.py`

**Lines:** 36
**Complexity:** All functions = 1.

**Positives:**
- Module underscore prefix (`_haiku_utils.py`) correctly signals internal/private status.
- All 4 utilities are pure functions (no side effects, no state).
- `extract_text_from_response()` uses `next()` with a default `None` guard — Pythonic and safe.
- `MAX_TEXT_LENGTH` is a typed constant (`int`), not a magic number.
- `__all__` explicitly declares the public API.

**Issues:** None. This is the ideal utility module.

**Score contribution:** Excellent.

---

### 8. `adapters/dlp/dual_layer_adapter.py`

**Lines:** 297
**Complexity:** `_HaikuDLPAdapter.sanitize()` = 4, `DualLayerDLPAdapter.sanitize()` = 2, `create_dual_layer_adapter()` = 1.

**Positives:**
- Architecture comment at module level clearly explains the dual-layer design rationale.
- `_HaikuDLPAdapter` is correctly private (`_` prefix) — public API is `DualLayerDLPAdapter` + factory.
- `asyncio.get_running_loop()` ✅ (confirmed fixed).
- Markdown fence stripping for JSON responses (`if "```" in raw:`) is a practical guard against LLM formatting quirks.
- `json.loads(raw)` with typed extraction (`bool(...)`, `str(...)`) is defensive.
- `DualLayerDLPAdapter.sanitize()`: The `total_redactions > 0` gate (not `contains_pii`) is correct since it uses the domain's computed property.
- Fail-open on `json.JSONDecodeError` and all other exceptions.
- `create_dual_layer_adapter()` factory reads from env var fallback — follows 12-factor app pattern.

**Issues:**
- `_HaikuDLPAdapter.sanitize()` is ~65 lines of code — the most complex function in the codebase. It handles truncation, executor call, JSON parsing, fence stripping, result construction, and error handling. Extracting JSON parsing into a `_parse_haiku_response()` helper would reduce this to ~35 lines, but the current structure is still readable.
- `raw` variable name (line 130) could be `raw_response_text` or `response_text` for clarity. Minor.

**Score contribution:** Good. One long method, one minor naming note.

---

### 9. `application/use_cases/sanitize_vulnerability.py`

**Lines:** 99
**Complexity:** `_sanitize_one()` = 2, `execute()` = 1.

**Positives:**
- `asyncio.gather()` ✅ (confirmed fixed — was the critical sequential for/await antipattern).
- `_sanitize_one()` correctly handles `None` description (`vuln.description or ""`).
- Use case depends on `DLPPort` interface, not concrete adapter — correct hexagonal architecture.
- `TYPE_CHECKING` import guard for `DLPPort` and `VulnerabilityRecord` prevents circular imports.
- Logging distinguishes `dlp_redactions_applied` (INFO) vs `dlp_no_pii_found` (DEBUG) — appropriate log levels.
- Summary log at end of `execute()` provides observability for batch operations.

**Issues:** None. This is the cleanest file in the batch — simple, focused, no surprises.

**Score contribution:** Excellent.

---

### 10. `infrastructure/di/dlp.py`

**Lines:** 128
**Complexity:** All functions = 1-2.

**Positives:**
- `@lru_cache(maxsize=1)` correctly creates singletons per settings object — cost-effective since Presidio engine initialization is heavy.
- `get_dual_layer_dlp_port()` vs `get_dlp_port()` distinction is well-documented ("Preferred over get_dlp_port() for production use").
- `settings.anthropic_api_key.get_secret_value()` — correct Pydantic `SecretStr` handling (never logs the raw key).
- Returns `DLPPort` (interface type) from `get_dlp_*` functions — callers see the port, not the adapter implementation.
- Comment `# PresidioAdapter satisfies DLPPort via structural subtyping (Protocol)` explains the implicit protocol satisfaction.

**Issues:**
- `lru_cache` on module-level functions can complicate test isolation (need `get_dlp_port.cache_clear()` between tests). This is a common pattern with known tradeoffs, documented by many Python projects. Not a blocking issue.

**Score contribution:** Very good.

---

## Summary of Findings

### Blocking Issues: 0

All previously blocking issues have been resolved. No new blocking issues found.

### Advisory Findings (Non-blocking)

| # | File | Finding | Severity |
|---|------|---------|---------|
| A1 | `presidio_adapter.py` | `_run_presidio()` is ~45 code lines (>30 advisory threshold) | Advisory |
| A2 | `dual_layer_adapter.py` | `_HaikuDLPAdapter.sanitize()` is ~65 code lines (longest in codebase) | Advisory |
| A3 | `dual_layer_adapter.py` | `raw` variable name could be more descriptive (`response_text`) | Advisory |
| A4 | `infrastructure/di/dlp.py` | `lru_cache` functions require `cache_clear()` in tests | Advisory |

No advisory findings are blocking. All are stylistic observations.

---

## Architecture Assessment

The DLP layer implements hexagonal architecture correctly:

```
domain/privacy/
  entities.py          ← Pure domain models (no external dependencies)
  value_objects.py     ← Immutable value objects
  exceptions.py        ← Domain exception hierarchy

application/ports/
  dlp.py               ← Protocol interfaces (contracts)

application/use_cases/
  sanitize_vulnerability.py  ← Orchestrates via port interface only

adapters/dlp/
  _haiku_utils.py        ← Shared private utilities
  presidio_adapter.py    ← Implements DLPPort via Presidio
  haiku_validator.py     ← Implements SemanticValidatorPort via Haiku
  dual_layer_adapter.py  ← Composes both adapters

infrastructure/di/
  dlp.py               ← Wiring/factory functions with singleton caching
```

The dependency flow is correct: domain has no external dependencies, adapters depend on domain, infrastructure wires everything together.

---

## Final Verdict

| Criterion | Result |
|-----------|--------|
| Score ≥ 9.0/10 | ✅ 9.3/10 |
| Blocking issues | ✅ 0 |
| Issue 1 resolved (get_running_loop) | ✅ All 3 sites fixed |
| Issue 2 resolved (_haiku_utils.py DRY) | ✅ Extracted and imported correctly |
| Issue 3 resolved (asyncio.gather) | ✅ Concurrent processing confirmed |

**STATUS: PASS**

---

*Report generated by code-reviewer agent*
*Wave: 2 (re-check)*
*Report path: ~/siopv/.ignorar/production-reports/code-reviewer/phase-6/2026-02-19-221634-phase-6-task-07c-code-review-recheck.md*
