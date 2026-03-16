# Code Review Report — Phase 6 DLP
**Agent:** code-reviewer
**Phase:** 6
**Task:** 07 (Wave 2)
**Timestamp:** 2026-02-19-181007
**Wave:** Wave 2
**Start:** 2026-02-19T18:10:07Z
**End:** 2026-02-19T18:12:45Z

---

## STATUS: FAIL

**Final Score: 8.2 / 10.0** (threshold: >= 9.0)

---

## Score Breakdown

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| Complexity & Maintainability | 3.5 | 4 | Mostly excellent; deprecated `get_event_loop()` in 3 files |
| DRY & Duplication | 1.4 | 2 | Haiku client setup + truncation pattern duplicated across 2 adapters |
| Naming & Clarity | 1.8 | 2 | Excellent naming; minor `presidio_passed` semantics confusion |
| Performance | 0.6 | 1 | Sequential use case; `type_map` rebuilt per-call; deprecated loop API |
| Testing | 0.9 | 1 | Protocol-based design is highly testable; private `_HaikuDLPAdapter` minor friction |
| **TOTAL** | **8.2** | **10** | |

---

## Files Reviewed

1. `src/siopv/domain/privacy/entities.py` (114 lines)
2. `src/siopv/domain/privacy/value_objects.py` (134 lines)
3. `src/siopv/domain/privacy/exceptions.py` (30 lines)
4. `src/siopv/application/ports/dlp.py` (71 lines)
5. `src/siopv/adapters/dlp/presidio_adapter.py` (272 lines)
6. `src/siopv/adapters/dlp/haiku_validator.py` (134 lines)
7. `src/siopv/adapters/dlp/dual_layer_adapter.py` (295 lines)
8. `src/siopv/application/use_cases/sanitize_vulnerability.py` (98 lines)
9. `src/siopv/infrastructure/di/dlp.py` (128 lines)

**Total:** 1,176 lines reviewed

---

## Blocking Issues (causing FAIL)

### ISSUE-01 [HIGH] Deprecated `asyncio.get_event_loop()` in 3 files

`asyncio.get_event_loop()` is deprecated in Python 3.10+ when called from a coroutine or when there is already a running event loop. The correct pattern in async code is `asyncio.get_running_loop()`.

**Files and lines:**

- `src/siopv/adapters/dlp/presidio_adapter.py`, line 233:
  ```python
  loop = asyncio.get_event_loop()
  ```
- `src/siopv/adapters/dlp/haiku_validator.py`, line 99:
  ```python
  loop = asyncio.get_event_loop()
  ```
- `src/siopv/adapters/dlp/dual_layer_adapter.py`, line 113:
  ```python
  loop = asyncio.get_event_loop()
  ```

**Impact:** DeprecationWarning on Python 3.10+; will raise RuntimeError in future Python versions when no current event loop exists in certain thread contexts.

**Fix:** Replace all three occurrences with:
```python
loop = asyncio.get_running_loop()
```

This is safe here because all three callers are `async def` methods, so a running loop is always present.

---

### ISSUE-02 [MEDIUM] DRY Violation: Haiku client infrastructure duplicated across 2 adapters

`HaikuSemanticValidatorAdapter` (`haiku_validator.py`) and `_HaikuDLPAdapter` (`dual_layer_adapter.py`) share significant boilerplate:

1. **Identical Anthropic client initialization:**
   ```python
   # haiku_validator.py:64
   self._client = anthropic.Anthropic(api_key=api_key)
   self._model = model

   # dual_layer_adapter.py:85
   self._client = anthropic.Anthropic(api_key=api_key)
   self._model = model
   ```

2. **Identical text truncation constant** (same value, different names):
   - `haiku_validator.py:42`: `_MAX_TEXT_LENGTH = 4000`
   - `dual_layer_adapter.py:58`: `_MAX_HAIKU_TEXT_LENGTH = 4_000`

3. **Identical truncation + warning pattern:**
   ```python
   # haiku_validator.py:89-95
   text_to_validate = text[:_MAX_TEXT_LENGTH]
   if len(text) > _MAX_TEXT_LENGTH:
       logger.warning("haiku_validator_text_truncated", ...)

   # dual_layer_adapter.py:105-111
   text_to_check = text[:_MAX_HAIKU_TEXT_LENGTH]
   if len(text) > _MAX_HAIKU_TEXT_LENGTH:
       logger.warning("haiku_dlp_text_truncated", ...)
   ```

4. **Identical TextBlock extraction pattern:**
   ```python
   # haiku_validator.py:110
   text_block = next((b for b in response.content if isinstance(b, TextBlock)), None)
   answer = text_block.text.strip().upper() if text_block else ""

   # dual_layer_adapter.py:127
   text_block = next((b for b in response.content if isinstance(b, TextBlock)), None)
   raw = text_block.text.strip() if text_block else ""
   ```

5. **Identical `run_in_executor` boilerplate with `functools.partial`** (lines 100-108 vs 116-125).

**Impact:** Changes to shared logic (e.g., truncation limit, executor pattern) must be made in two places, creating drift risk.

**Fix:** Extract a shared `_HaikuBaseAdapter` or `_AnthropicExecutorMixin` that provides:
- `__init__` with `api_key`, `model`, `_client`
- `_truncate_text(text, max_length)` method
- `_call_haiku(prompt, system_prompt, max_tokens)` async method

The concrete adapters then differ only in prompt and response parsing logic.

---

### ISSUE-03 [MEDIUM] Sequential processing in `SanitizeVulnerabilityUseCase.execute()`

`sanitize_vulnerability.py:57` processes vulnerabilities sequentially with `for vuln in vulnerabilities`. Each iteration `await`s `self._dlp_port.sanitize(ctx)`, blocking until the previous call completes.

```python
for vuln in vulnerabilities:
    description = vuln.description or ""
    # ...
    dlp_result = await self._dlp_port.sanitize(ctx)  # Sequential!
    results.append((vuln, dlp_result))
```

**Impact:** Processing N vulnerabilities takes N × (Presidio time + optional Haiku time). With 100 records and ~500ms per call, that's ~50s. Parallel execution would take ~500ms.

**Fix:**
```python
async def _sanitize_single(
    self, vuln: VulnerabilityRecord
) -> tuple[VulnerabilityRecord, DLPResult]:
    description = vuln.description or ""
    if not description.strip():
        return vuln, DLPResult.safe_text(description)
    ctx = SanitizationContext(text=description)
    return vuln, await self._dlp_port.sanitize(ctx)

async def execute(self, vulnerabilities: list[VulnerabilityRecord]) -> ...:
    results = await asyncio.gather(
        *(_sanitize_single(v) for v in vulnerabilities)
    )
    ...
```

Note: If DLP port is not thread-safe for parallel Presidio calls, use a semaphore to limit concurrency.

---

## Non-Blocking Issues (observations)

### ISSUE-04 [LOW] `type_map` rebuilt on every `PIIDetection.from_presidio()` call

`value_objects.py:95–116`: The `type_map` dictionary is constructed inside the `from_presidio()` classmethod and rebuilt on every invocation.

```python
@classmethod
def from_presidio(cls, entity_type: str, ...) -> PIIDetection:
    type_map: dict[str, PIIEntityType] = {
        "PERSON": PIIEntityType.PERSON,
        # ... 15 more entries
    }
```

**Impact:** Minor allocation overhead per call. In a hot path processing many vulnerabilities, this adds unnecessary GC pressure.

**Fix:** Move `type_map` to module-level constant:
```python
_PRESIDIO_TYPE_MAP: dict[str, PIIEntityType] = {
    "PERSON": PIIEntityType.PERSON,
    # ...
}
```

---

### ISSUE-05 [LOW] Semantic mapping of `ORGANIZATION` → `PERSON`

`value_objects.py:115`:
```python
"ORGANIZATION": PIIEntityType.PERSON,
```

Mapping `ORGANIZATION` to `PERSON` is semantically incorrect (organizations are not persons). The replacement placeholder will render as `<PERSON>` for an organization name, which may mislead consumers.

**Suggestion:** Add `ORGANIZATION = "ORGANIZATION"` to `PIIEntityType` enum, or map to `NRP` (which already handles other non-person entities) with a comment explaining the decision.

---

### ISSUE-06 [LOW] `presidio_passed=True` when Haiku finds sensitive content

`dual_layer_adapter.py:148–154`:
```python
return DLPResult(
    original_text=text,
    sanitized_text=sanitized_text,
    detections=[],
    presidio_passed=True,     # Presidio ran OK (no detections)
    semantic_passed=False,    # Haiku found issues
)
```

The flag name `presidio_passed` means "Presidio ran successfully," not "no PII found." When Haiku finds content that Presidio missed, setting `presidio_passed=True` is technically correct per the docstring but is counterintuitive — callers may interpret it as "Presidio cleared this text."

**Suggestion:** Add a comment at this site:
```python
presidio_passed=True,   # Presidio ran without errors (found 0 entities)
semantic_passed=False,  # Haiku semantic check identified remaining PII
```

---

### ISSUE-07 [INFO] `asyncio.get_event_loop()` in Python 3.12+ will raise RuntimeError

Building on ISSUE-01: In Python 3.12, `asyncio.get_event_loop()` raises `DeprecationWarning` and in 3.14 is expected to raise `RuntimeError` when no running loop is present. Since all usages are inside `async def` methods, `asyncio.get_running_loop()` is the safe and idiomatic replacement.

---

## Per-File Assessment

### `domain/privacy/entities.py` — EXCELLENT
- Pydantic v2 `ConfigDict(frozen=True)` correctly applied.
- `@computed_field` + `@property` pattern with `# type: ignore[prop-decorator]` comment — appropriate handling of known mypy limitation.
- `DLPResult.safe_text()` factory method is a clean, convenient pattern.
- No issues.

### `domain/privacy/value_objects.py` — GOOD (minor issues)
- Clean `str, Enum` pattern for `PIIEntityType`.
- `PIIDetection.from_presidio()` factory is well-documented.
- **ISSUE-04**: `type_map` dict rebuilt per call (minor).
- **ISSUE-05**: `ORGANIZATION → PERSON` mapping is semantically questionable.

### `domain/privacy/exceptions.py` — EXCELLENT
- Minimal, clean exception hierarchy.
- All 4 exceptions clearly named.
- No issues.

### `application/ports/dlp.py` — EXCELLENT
- `@runtime_checkable` Protocol for structural subtyping is the correct pattern.
- `TYPE_CHECKING` guard for import efficiency.
- Docstring clearly explains fail-open semantics for `SemanticValidatorPort`.
- No issues.

### `adapters/dlp/presidio_adapter.py` — GOOD (blocking issue)
- Clean separation: `_build_analyzer()`, `_build_anonymizer()`, `_run_presidio()` as pure functions + `PresidioAdapter` class.
- Optional import handling with graceful error capture is a solid pattern.
- `_run_presidio()` is 45 lines — borderline but has a clear 4-step flow.
- **ISSUE-01**: `asyncio.get_event_loop()` on line 233.
- Cyclomatic complexity: 5 in `_run_presidio()`, 3 in `sanitize()` — acceptable.

### `adapters/dlp/haiku_validator.py` — GOOD (blocking issue)
- Fail-open design is correct and well-documented.
- Short-circuit conditions on line 84 are clear and tested.
- **ISSUE-01**: `asyncio.get_event_loop()` on line 99.
- **ISSUE-02**: Duplicates Haiku client setup and truncation pattern.
- `validate()` is 50 lines — acceptable.

### `adapters/dlp/dual_layer_adapter.py` — GOOD (blocking issues)
- Dual-layer composition pattern is clean and well-documented.
- Module docstring explains the architectural decision (Haiku only on Presidio miss) clearly.
- `create_dual_layer_adapter()` factory function is clean.
- **ISSUE-01**: `asyncio.get_event_loop()` on line 113.
- **ISSUE-02**: `_HaikuDLPAdapter` duplicates infrastructure from `haiku_validator.py`.
- **ISSUE-06**: `presidio_passed=True` when Haiku finds content (minor).
- JSON markdown fence stripping (lines 131–134) is a pragmatic pattern worth keeping.

### `application/use_cases/sanitize_vulnerability.py` — GOOD (performance issue)
- Single responsibility: sanitize descriptions of vulnerability records.
- Correct short-circuit for empty descriptions.
- Aggregate summary log at end is good observability practice.
- **ISSUE-03**: Sequential processing with `for` loop instead of `asyncio.gather()`.

### `infrastructure/di/dlp.py` — EXCELLENT
- `@lru_cache(maxsize=1)` singleton pattern for Presidio engines is correct.
- `get_secret_value()` for API key extraction — good security practice.
- Clear separation between `PresidioAdapter`-backed and `DualLayerDLPAdapter`-backed singletons.
- `create_*` vs `get_*` naming convention is consistent.
- No issues.

---

## Architecture Assessment

The overall architecture is well-designed:

1. **Hexagonal architecture** is correctly applied: domain entities, value objects, and ports are free of adapter concerns.
2. **Protocol-based structural subtyping** avoids concrete inheritance coupling.
3. **Dual-layer DLP** with cost optimization (Haiku only on Presidio miss) is a sound design.
4. **Fail-open design** at every Haiku boundary is correct and consistently applied.
5. **Dependency injection** through constructors + factory functions enables full testability.

The codebase demonstrates strong engineering fundamentals. The failing score is driven by three fixable issues:
- Deprecated async API (1 line fix per file, 3 files)
- DRY violation in Haiku adapter infrastructure (extractable base class)
- Sequential use case processing (asyncio.gather() refactor)

---

## Summary

| # | Severity | Issue | Files | Fix Effort |
|---|----------|-------|-------|-----------|
| 01 | HIGH | `asyncio.get_event_loop()` deprecated | presidio_adapter.py:233, haiku_validator.py:99, dual_layer_adapter.py:113 | Trivial (1 line each) |
| 02 | MEDIUM | DRY: Haiku client infrastructure duplicated | haiku_validator.py + dual_layer_adapter.py | Small (extract base class) |
| 03 | MEDIUM | Sequential use case processing | sanitize_vulnerability.py:57 | Small (asyncio.gather) |
| 04 | LOW | `type_map` rebuilt per call | value_objects.py:95 | Trivial (module constant) |
| 05 | LOW | ORGANIZATION→PERSON mapping | value_objects.py:115 | Trivial (enum or comment) |
| 06 | LOW | Misleading `presidio_passed` flag | dual_layer_adapter.py:148 | Trivial (comment) |

**VERDICT: FAIL (8.2/10)**
Fix ISSUE-01, ISSUE-02, ISSUE-03 → re-verify for PASS.
