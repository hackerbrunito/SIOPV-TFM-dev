# Code Reviewer — Phase 6 Batch 3 of 3

**Agent:** code-reviewer
**Phase:** 6 (DLP — Presidio + Haiku dual-layer)
**Batch:** 3 of 3 — adapters/dlp module
**Timestamp:** 2026-02-20-181256
**Wave:** Wave 2
**SIOPV Threshold Override:** PASS requires score >= 9.5/10

---

## Scope

| File | Lines |
|------|-------|
| src/siopv/adapters/dlp/presidio_adapter.py | 278 |
| src/siopv/adapters/dlp/haiku_validator.py | 140 |
| src/siopv/adapters/dlp/dual_layer_adapter.py | 297 |
| src/siopv/adapters/dlp/_haiku_utils.py | 36 |

---

## Review Criteria Applied

- Cyclomatic complexity > 10 per function (flag for simplification)
- Duplicate code patterns (DRY violations)
- Naming consistency and clarity
- Function/method length > 30 lines (suggest extraction)
- Missing docstrings for public functions (advisory)
- Performance bottlenecks
- Test coverage implications

---

## File-by-File Analysis

### 1. `src/siopv/adapters/dlp/_haiku_utils.py` (36 lines)

**Cyclomatic Complexity:**
- `create_haiku_client`: CC = 1 ✅
- `truncate_for_haiku`: CC = 1 ✅
- `extract_text_from_response`: CC = 1 (ternary is not a branch) ✅

**Function Length:**
All functions are 1–2 lines. ✅

**DRY / Duplication:**
This module exists specifically to eliminate duplication between `haiku_validator.py` and `dual_layer_adapter.py`. Purpose well-served. ✅

**Naming Consistency:**
- `create_haiku_client`, `truncate_for_haiku`, `extract_text_from_response`: clear, verb-noun ✅
- `MAX_TEXT_LENGTH` module constant: clear UPPER_CASE constant ✅

**Docstrings:**
- `create_haiku_client`: one-line docstring ✅
- `truncate_for_haiku`: one-line docstring ✅
- `extract_text_from_response`: multi-line docstring explaining empty-string fallback ✅

**Performance:**
No issues. `next(..., None)` with generator is O(n) over response content blocks, which is always tiny in practice. ✅

**Issues Found:** None. This is a model utility module.

---

### 2. `src/siopv/adapters/dlp/haiku_validator.py` (140 lines)

**Cyclomatic Complexity:**
- `__init__`: CC = 1 ✅
- `validate` (lines 74–137): Branches: `if not text.strip() or (len(text) < MIN_SHORT_TEXT_LENGTH and not detections)`, `if len(text) > MAX_TEXT_LENGTH`, `try/except`. **CC = 4** ✅ (well under 10)

**Function Length:** ⚠️ ADVISORY
- `validate` (lines 74–137): **63 lines** — exceeds 30-line threshold by 110%.

  The length breaks down as:
  - Lines 90–93: short-circuit guard (4 lines)
  - Lines 95–102: truncation logic + warning log (8 lines)
  - Lines 104–115: executor invocation of Haiku API (12 lines)
  - Lines 117–126: response parsing + result logging (10 lines)
  - Lines 128–137: except + else return paths (9 lines)
  - Docstring: 20 lines

  **Suggestion:** Extract the API invocation into a private method:
  ```python
  async def _call_haiku(self, text: str) -> str:
      """Call Haiku API via executor. Returns raw text response."""
      loop = asyncio.get_running_loop()
      response = await loop.run_in_executor(
          None,
          functools.partial(
              self._client.messages.create,
              model=self._model, max_tokens=10,
              messages=[{"role": "user", "content": _VALIDATION_PROMPT.format(text=text)}],
          ),
      )
      return extract_text_from_response(response).upper()
  ```
  This reduces `validate` to ~30 lines.

**Backward-Compat Alias:** ⚠️ CODE SMELL
- Line 29: `_MAX_TEXT_LENGTH = MAX_TEXT_LENGTH` — comment says "Backward-compatible alias used by existing tests."
  - If tests import a private symbol from this module rather than from `_haiku_utils`, that's a test design problem. Tests should be updated to import `MAX_TEXT_LENGTH` from `_haiku_utils` directly.
  - The alias is harmless but indicates test coupling to implementation internals.

**DRY / Duplication:**
- Truncation check + warning log (lines 96–102) is near-identical to the same pattern in `dual_layer_adapter.py` lines 108–114. Both call `truncate_for_haiku()` and log a warning. Since the warning log is only 1 extra line, this is minor — but could be consolidated into `truncate_for_haiku` itself if it returned `(truncated, was_truncated)`.

**Naming Consistency:**
- `HaikuSemanticValidatorAdapter`: clear, matches `SemanticValidatorPort` naming convention ✅
- `MIN_SHORT_TEXT_LENGTH`: clear constant ✅
- `validate`: matches `SemanticValidatorPort.validate` interface ✅

**Docstrings:**
- Class docstring ✅
- `__init__` with Args ✅
- `validate` with full Args/Returns including short-circuit and fail-open semantics ✅

**Performance:**
- `run_in_executor` correctly offloads the synchronous Anthropic client to a thread pool, keeping the event loop non-blocking. ✅

**Issues Found:**

| Severity | Type | Location | Description |
|----------|------|----------|-------------|
| ⚠️ ADVISORY | Length | haiku_validator.py:74–137 | `validate` is 63 lines (threshold: 30). Extract `_call_haiku()` helper. |
| ℹ️ MINOR | Code Smell | haiku_validator.py:29 | `_MAX_TEXT_LENGTH` backward-compat alias for tests. Update tests to import from `_haiku_utils`. |
| ℹ️ ADVISORY | DRY | haiku_validator.py:96–102 | Truncation + warning log pattern duplicated in dual_layer_adapter.py. |

---

### 3. `src/siopv/adapters/dlp/presidio_adapter.py` (278 lines)

**Cyclomatic Complexity:**
- `_build_analyzer`: CC = 2 (if AnalyzerEngine is None) ✅
- `_build_anonymizer`: CC = 2 (if AnonymizerEngine is None) ✅
- `_run_presidio`: CC = 4 (try/except, if not analyzer_results, set comp, list comp) ✅
- `__init__`: CC = 2 (if enable_semantic_validation and api_key) ✅
- `sanitize`: CC = 3 (if not context.text.strip(), if self._haiku_validator is not None) ✅

All functions under CC = 10. ✅

**Function Length:** ⚠️ MULTIPLE FUNCTIONS OVER THRESHOLD

| Function | Lines | Status |
|----------|-------|--------|
| `_build_analyzer` (56–87) | 31 | ⚠️ Marginally over (by 1 line) |
| `_build_anonymizer` (90–104) | 14 | ✅ |
| `_run_presidio` (107–172) | 65 | ⚠️ Over by 116% |
| `PresidioAdapter.__init__` (185–217) | 32 | ⚠️ Marginally over |
| `PresidioAdapter.sanitize` (219–275) | 56 | ⚠️ Over by 86% |

The two significant oversizes are `_run_presidio` and `sanitize`.

**`_run_presidio` (65 lines):**
The function is well-structured with Step 1–4 comments:
1. Detect PII (analyzer.analyze)
2. Build per-entity operators
3. Anonymize
4. Convert to domain value objects

**Suggestion:** Extract steps 3+4 into a helper:
```python
def _anonymize_and_convert(
    anonymizer, analyzer_results, operators, original_text
) -> tuple[str, list[PIIDetection]]:
    """Step 3+4: Run anonymization and convert to domain objects."""
    ...
```
This reduces `_run_presidio` to ~35 lines.

**`PresidioAdapter.sanitize` (56 lines):**
The length is inflated by the large `functools.partial` call block and the logging call with 5 keyword args.

**Suggestion:** Extract the executor call into a private method:
```python
async def _run_presidio_async(self, context: SanitizationContext) -> tuple[str, list[PIIDetection]]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, functools.partial(_run_presidio, self._analyzer, self._anonymizer, context)
    )
```
This reduces `sanitize` to ~20 lines.

**DRY / Duplication:**
- The lazy import pattern with triple try/except blocks at module level (lines 23–45) is not technically duplication but is verbose. However, this is the correct approach for optional dependencies. ✅
- `_build_analyzer` and `_build_anonymizer` share the same error-if-none pattern. Minor — the functions are short and distinct enough.

**Naming Consistency:**
- Module-level functions `_build_analyzer`, `_build_anonymizer`, `_run_presidio`: consistent underscore prefix ✅
- Constants `_API_KEY_REGEX`, `_API_KEY_ENTITY`: consistent prefix ✅
- Class `PresidioAdapter`: matches protocol expectation ✅

**Docstrings:**
- All public and private functions have docstrings ✅
- `_run_presidio` explicitly documents thread-pool intent ✅

**Performance:**
- `run_in_executor(None, functools.partial(...))` correctly offloads sync Presidio calls to the default thread-pool executor. ✅
- Presidio `AnalyzerEngine` built once in `__init__` (not per-call). ✅

**Issues Found:**

| Severity | Type | Location | Description |
|----------|------|----------|-------------|
| ⚠️ ADVISORY | Length | presidio_adapter.py:107–172 | `_run_presidio` is 65 lines (threshold: 30). Extract anonymize+convert step into helper. |
| ⚠️ ADVISORY | Length | presidio_adapter.py:219–275 | `PresidioAdapter.sanitize` is 56 lines (threshold: 30). Extract executor call into `_run_presidio_async`. |
| ℹ️ MINOR | Length | presidio_adapter.py:56–87 | `_build_analyzer` is 31 lines (1 line over threshold). Marginal. |
| ℹ️ MINOR | Length | presidio_adapter.py:185–217 | `PresidioAdapter.__init__` is 32 lines (2 lines over threshold). Marginal. |

---

### 4. `src/siopv/adapters/dlp/dual_layer_adapter.py` (297 lines)

**Cyclomatic Complexity:**
- `_HaikuDLPAdapter.__init__`: CC = 1 ✅
- `_HaikuDLPAdapter.sanitize` (91–173): Branches: `if not text.strip()`, `if len(text) > MAX_TEXT_LENGTH`, `try/except`, `if "```" in raw`, `if len(parts) > 1`, `if contains_sensitive`. **CC = 7** ✅ (under 10)
- `DualLayerDLPAdapter.__init__`: CC = 1 ✅
- `DualLayerDLPAdapter.sanitize` (210–248): CC = 2 (if presidio_result.total_redactions > 0) ✅
- `create_dual_layer_adapter` (251–291): CC = 1 (no explicit branches; `or` in `api_key or os.environ.get(...)` is not a flow branch) ✅

All under CC = 10. ✅

**Function Length:** ⚠️ MULTIPLE FUNCTIONS OVER THRESHOLD

| Function | Lines | Status |
|----------|-------|--------|
| `_HaikuDLPAdapter.sanitize` (91–173) | 82 | ⚠️ Over by 173% — most significant |
| `DualLayerDLPAdapter.sanitize` (210–248) | 38 | ⚠️ Over by 26% |
| `create_dual_layer_adapter` (251–291) | 40 | ⚠️ Over by 33% |

**`_HaikuDLPAdapter.sanitize` (82 lines) — most significant:**
This is the longest function in the entire batch. Concerns break down as:

1. Lines 104–114: Empty text guard + truncation logic (11 lines)
2. Lines 116–128: Executor invocation of Haiku API (13 lines)
3. Lines 130–141: JSON parsing + markdown fence stripping (12 lines)
4. Lines 142–163: Sensitive-found branch (21 lines)
5. Lines 165–173: Exception handler (9 lines)

The markdown-fence stripping logic (lines 132–136) is an important but obscure edge case handling:
```python
if "```" in raw:
    parts = raw.split("```")
    raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
```
This should be extracted into a named helper `_strip_markdown_fences(raw: str) -> str` to:
1. Give it a descriptive name
2. Make it independently testable
3. Reduce `sanitize` length

**Suggested refactoring outline:**
```python
async def _call_haiku_dlp(self, text: str) -> str:
    """Invoke Haiku API and return raw text response."""
    ...  # Lines 116-130

def _parse_haiku_response(self, raw: str, original_text: str) -> DLPResult:
    """Parse Haiku JSON response into DLPResult."""
    ...  # Lines 132-164

async def sanitize(self, context: SanitizationContext) -> DLPResult:
    """Orchestrate: guard → call → parse."""
    # Guard (5 lines) + delegation (5 lines) = 10 lines total
```

**`DualLayerDLPAdapter.sanitize` (38 lines):**
Oversize is mainly due to logging statements (4 log calls) and docstring. Core logic is 4 lines. The length is not a quality concern, but could be tightened.

**`create_dual_layer_adapter` (40 lines):**
Much of the length is the detailed docstring (14 lines) and doctest example. The actual logic is 10 lines. Docstring contributes to clarity, so this is acceptable.

**DRY / Duplication:**

1. **Truncation + warning log pattern** (lines 108–114 in `_HaikuDLPAdapter.sanitize`) is near-identical to the same in `haiku_validator.py` (lines 95–102). Both files import from `_haiku_utils` — a `truncate_with_warning(text, logger)` utility would eliminate the repeated log call.

2. **`run_in_executor` + `functools.partial` pattern** appears 3 times across the batch:
   - `presidio_adapter.py:240–248` (Presidio)
   - `haiku_validator.py:106–115` (Haiku validate)
   - `dual_layer_adapter.py:119–128` (Haiku DLP)

   This is idiomatic asyncio and there is no clean common abstraction that would improve readability. Acceptable as-is.

3. **Fail-open exception handler** duplicated in `haiku_validator.validate` and `_HaikuDLPAdapter.sanitize`. Both catch `Exception` broadly, log with `exc_info=True`, and return a safe result. Advisory.

**Naming Consistency:**
- `_HaikuDLPAdapter` (private, underscore prefix): appropriate ✅
- `DualLayerDLPAdapter`, `create_dual_layer_adapter`: clear ✅
- `_HAIKU_SYSTEM_PROMPT`, `_HAIKU_USER_PROMPT`, `_HAIKU_MAX_TOKENS`: consistent module-level constants ✅
- Log keys: `haiku_dlp_text_truncated`, `haiku_dlp_sensitive_found`, `haiku_dlp_clean`, `dual_layer_dlp_presidio_redacted`, `dual_layer_dlp_complete`: descriptive and consistent ✅

**Docstrings:**
- All classes and public functions have complete docstrings ✅
- `_HaikuDLPAdapter` documented as private implementation detail ✅
- `DualLayerDLPAdapter` includes architecture diagram in docstring ✅
- Module-level docstring explains the dual-layer design with rationale ✅

**Performance:**
- Haiku invoked only on Presidio misses (zero-entity results). Cost optimization correctly implemented. ✅
- `run_in_executor` correctly used for sync Anthropic client. ✅

**Issues Found:**

| Severity | Type | Location | Description |
|----------|------|----------|-------------|
| ⚠️ ADVISORY | Length | dual_layer_adapter.py:91–173 | `_HaikuDLPAdapter.sanitize` is 82 lines (threshold: 30). Extract `_call_haiku_dlp`, `_parse_haiku_response`, and `_strip_markdown_fences` helpers. |
| ⚠️ ADVISORY | Length | dual_layer_adapter.py:251–291 | `create_dual_layer_adapter` is 40 lines. Mostly docstring — acceptable if docstring retained. |
| ⚠️ ADVISORY | Length | dual_layer_adapter.py:210–248 | `DualLayerDLPAdapter.sanitize` is 38 lines (mainly logging). Core logic is 4 lines. |
| ℹ️ ADVISORY | DRY | dual_layer_adapter.py:108–114 | Truncation + warning log duplicated in haiku_validator.py. |
| ℹ️ ADVISORY | DRY | dual_layer_adapter.py:166–173 | Fail-open handler pattern repeated vs haiku_validator.py. |

---

## Cross-File Analysis

### Summary of Long Functions Across Batch 3

| Function | File | Lines | Over Threshold By |
|----------|------|-------|------------------|
| `_HaikuDLPAdapter.sanitize` | dual_layer_adapter.py | 82 | +173% |
| `_run_presidio` | presidio_adapter.py | 65 | +116% |
| `HaikuSemanticValidatorAdapter.validate` | haiku_validator.py | 63 | +110% |
| `PresidioAdapter.sanitize` | presidio_adapter.py | 56 | +86% |
| `create_dual_layer_adapter` | dual_layer_adapter.py | 40 | +33% |
| `DualLayerDLPAdapter.sanitize` | dual_layer_adapter.py | 38 | +26% |
| `PresidioAdapter.__init__` | presidio_adapter.py | 32 | +6% |
| `_build_analyzer` | presidio_adapter.py | 31 | +3% |

**8 of 13 functions across 3 files exceed the 30-line threshold.** This is a systemic pattern, not isolated incidents. The root cause is that complex adapter logic (executor pattern + logging + guard clauses + error handling) requires ~5–10 extra lines per concern, compounding across multi-step functions.

### DRY Summary (Cross-File)

| Pattern | Files | Count | Severity |
|---------|-------|-------|----------|
| Truncation + warning log | haiku_validator.py, dual_layer_adapter.py | 2 | ADVISORY |
| run_in_executor + functools.partial | presidio_adapter.py, haiku_validator.py, dual_layer_adapter.py | 3 | INFO (idiomatic) |
| Fail-open exception handler | haiku_validator.py, dual_layer_adapter.py | 2 | ADVISORY |
| `_MAX_TEXT_LENGTH` alias for tests | haiku_validator.py | 1 | CODE SMELL |

### Architecture Quality Observations (Positive)

1. **_haiku_utils.py** correctly centralizes shared Haiku utilities, demonstrating intentional DRY architecture.
2. **Fail-open design** is consistently applied and documented across all LLM calls — critical for a safety guardrail system.
3. **Executor pattern** is consistently used to keep sync Anthropic/Presidio calls off the event loop.
4. **Layered design** in `DualLayerDLPAdapter` is clean: Presidio always runs first; Haiku runs only on misses. Cost optimization is structural, not an afterthought.
5. **Module-level constants** for prompts and thresholds keep adapter methods free of magic strings.

---

## Score Breakdown

| Criterion | Max | Score | Notes |
|-----------|-----|-------|-------|
| Complexity & Maintainability | 4.0 | 3.0 | 8 of 13 functions exceed 30-line threshold. 4 significantly (56–82 lines). CC is consistently low (max 7) — length is the only structural concern. |
| DRY & Duplication | 2.0 | 1.5 | Truncation+log pattern duplicated; fail-open pattern repeated; `_MAX_TEXT_LENGTH` backward-compat alias. `_haiku_utils.py` correctly centralizes the core utilities. |
| Naming & Clarity | 2.0 | 2.0 | Excellent naming throughout. Consistent conventions. Module docstring explains architecture. Step comments in long functions aid readability. |
| Performance | 1.0 | 1.0 | All executor usage correct. Haiku invoked sparingly (cost optimization). No event-loop blocking. |
| Testing | 1.0 | 0.75 | Well-structured adapters. Private `_HaikuDLPAdapter` harder to test directly. Markdown-fence stripping (dual_layer_adapter.py:132–136) requires dedicated test case. `_MAX_TEXT_LENGTH` alias reveals test coupling to internals. |
| **TOTAL** | **10.0** | **8.25** | |

---

## Findings Summary

| # | Severity | File | Line(s) | Type | Description |
|---|----------|------|---------|------|-------------|
| 1 | ⚠️ ADVISORY | dual_layer_adapter.py | 91–173 | Length | `_HaikuDLPAdapter.sanitize` 82 lines — extract `_call_haiku_dlp`, `_parse_haiku_response`, `_strip_markdown_fences`. |
| 2 | ⚠️ ADVISORY | presidio_adapter.py | 107–172 | Length | `_run_presidio` 65 lines — extract anonymize+convert step. |
| 3 | ⚠️ ADVISORY | haiku_validator.py | 74–137 | Length | `validate` 63 lines — extract `_call_haiku()` API helper. |
| 4 | ⚠️ ADVISORY | presidio_adapter.py | 219–275 | Length | `PresidioAdapter.sanitize` 56 lines — extract `_run_presidio_async()`. |
| 5 | ⚠️ ADVISORY | dual_layer_adapter.py | 251–291 | Length | `create_dual_layer_adapter` 40 lines (mainly docstring — acceptable if docstring kept). |
| 6 | ⚠️ ADVISORY | dual_layer_adapter.py | 210–248 | Length | `DualLayerDLPAdapter.sanitize` 38 lines (mainly logging). |
| 7 | ℹ️ ADVISORY | haiku_validator.py, dual_layer_adapter.py | 95–102, 108–114 | DRY | Truncation + warning log pattern duplicated. |
| 8 | ℹ️ ADVISORY | haiku_validator.py, dual_layer_adapter.py | 128–135, 166–173 | DRY | Fail-open exception handler pattern repeated. |
| 9 | ℹ️ MINOR | haiku_validator.py | 29 | Code Smell | `_MAX_TEXT_LENGTH` backward-compat alias. Update tests to import from `_haiku_utils`. |
| 10 | ℹ️ MINOR | presidio_adapter.py | 56–87, 185–217 | Length | `_build_analyzer` (31 lines) and `__init__` (32 lines) marginally over threshold. |

**CRITICAL/HIGH findings:** 0
**ADVISORY findings:** 8
**MINOR findings:** 2

---

## Verdict

**BATCH 3 SCORE: 8.25/10**

**RESULT: ❌ FAIL**
*(Does NOT meet SIOPV threshold of >= 9.5/10)*

**Root cause:** Systemic function length issue across 3 files — 8 of 13 functions exceed the 30-line threshold, with 4 exceeding it significantly (56–82 lines). The underlying logic quality is good (CC ≤ 7 throughout, correct executor usage, consistent fail-open design), but the adapter layer functions are not decomposed into sufficiently small units.

**Required Fixes Before PASS:**
1. Extract helpers in `_HaikuDLPAdapter.sanitize` (`_call_haiku_dlp`, `_parse_haiku_response`, `_strip_markdown_fences`)
2. Extract helpers in `_run_presidio` (anonymize+convert step)
3. Extract `_run_presidio_async` from `PresidioAdapter.sanitize`
4. Extract `_call_haiku()` from `HaikuSemanticValidatorAdapter.validate`
5. Update tests to import `MAX_TEXT_LENGTH` from `_haiku_utils` directly (remove `_MAX_TEXT_LENGTH` alias)
