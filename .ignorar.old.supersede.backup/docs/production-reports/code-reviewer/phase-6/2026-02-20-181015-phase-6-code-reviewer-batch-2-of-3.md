# Code Reviewer — Phase 6 Batch 2 of 3

**Agent:** code-reviewer
**Phase:** 6 (DLP — Presidio + Haiku dual-layer)
**Batch:** 2 of 3 — application layer + infrastructure/di
**Timestamp:** 2026-02-20-181015
**Wave:** Wave 2
**SIOPV Threshold Override:** PASS requires score >= 9.5/10

---

## Scope

| File | Lines |
|------|-------|
| src/siopv/application/use_cases/sanitize_vulnerability.py | 99 |
| src/siopv/application/orchestration/nodes/dlp_node.py | 108 |
| src/siopv/infrastructure/di/dlp.py | 128 |

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

### 1. `src/siopv/application/use_cases/sanitize_vulnerability.py` (99 lines)

**Cyclomatic Complexity:**
- `__init__`: CC = 1 ✅
- `_sanitize_one`: 2 if-branches → CC = 3 ✅ (well under 10)
- `execute`: no explicit branches → CC = 1 ✅

**Function Length:**
- `__init__`: 1 line body ✅
- `_sanitize_one` (lines 39–66): 27 lines total ✅ (just under threshold)
- `execute` (lines 68–96): 28 lines total ✅ (just under threshold)

No functions exceed 30 lines.

**DRY / Duplication:**
No duplication within this file. The concurrent-gather pattern (`asyncio.gather` over `_sanitize_one`) is the correct approach.

**Naming Consistency:**
- `SanitizeVulnerabilityUseCase`: follows use case naming convention ✅
- `_sanitize_one`: clear private helper indicating single-record processing ✅
- `execute`: consistent with use case interface convention ✅
- Log keys: `dlp_skip_empty_description`, `dlp_redactions_applied`, `dlp_no_pii_found`, `sanitize_vulnerability_use_case_complete` — all well-structured structured-log keys ✅

**Docstrings:**
- Class docstring present ✅
- `__init__` docstring with Args ✅
- `_sanitize_one` one-line docstring ✅
- `execute` full docstring with Args/Returns ✅

**Performance:**
- `asyncio.gather(*[self._sanitize_one(vuln) for vuln in vulnerabilities])` — correct concurrent pattern. All records are processed in parallel under a single event loop. ✅

**Test Coverage Implications:**
Clean architecture. DLPPort is injected, easily mockable. Both branches in `_sanitize_one` (empty description, non-empty description with/without redactions) are straightforward to cover.

**Issues Found:** None

---

### 2. `src/siopv/application/orchestration/nodes/dlp_node.py` (108 lines)

**Cyclomatic Complexity:**
Counting branches in `dlp_node` (lines 23–105):
- `if dlp_port is None` → +1
- `if not vulnerabilities` → +1
- `for vuln in vulnerabilities` → +1
- `isinstance(v, dict)` in generator → +1
- `v.get("redactions", 0) > 0` in generator → +1
- Base: 1

**Total CC = 6** — under threshold of 10. ✅

**Function Length:** ⛔ FAIL
- `dlp_node` (lines 23–105): **82 lines** — exceeds 30-line threshold by **173%**.

  The function handles multiple distinct concerns in sequence:
  1. Guard clause: no DLP port configured (lines 47–56)
  2. Guard clause: empty vulnerability list (lines 58–68)
  3. Vulnerability iteration with DLP calls (lines 70–86)
  4. Summary logging (lines 88–95)
  5. Result dict construction (lines 97–104)

  **Suggestion:** Extract at minimum two helpers:
  ```python
  def _run_dlp_for_vulns(vulnerabilities, dlp_port) -> dict[str, object]:
      """Run DLP for each vulnerability, return per_cve dict."""
      ...

  def _build_dlp_result(per_cve: dict) -> dict[str, object]:
      """Construct the DLP result state dict."""
      ...
  ```
  This would reduce `dlp_node` itself to ~25 lines of guard clauses + delegation.

**Performance:** ⛔ ISSUE
- Lines 77–78: `asyncio.run(dlp_port.sanitize(ctx))` is called **inside a `for` loop**.

  ```python
  for vuln in vulnerabilities:          # N iterations
      result = asyncio.run(dlp_port.sanitize(ctx))  # NEW event loop per iteration
  ```

  Each `asyncio.run()` call creates and tears down a complete asyncio event loop. For N vulnerabilities, this means N sequential event loops instead of one loop running N concurrent tasks.

  The use case (`sanitize_vulnerability.py`) correctly solves this with:
  ```python
  await asyncio.gather(*[self._sanitize_one(vuln) for vuln in vulnerabilities])
  ```

  **The node should do the same:**
  ```python
  async def _sanitize_all(vulns, dlp_port):
      contexts = [SanitizationContext(text=v.description or "") for v in vulns]
      return await asyncio.gather(*[dlp_port.sanitize(ctx) for ctx in contexts])

  results = asyncio.run(_sanitize_all(vulnerabilities, dlp_port))
  ```

  This reduces N event loop creations to 1, and processes all vulnerabilities concurrently.

  This is a **notable performance defect**, especially relevant when the pipeline ingests batches of CVEs.

**DRY / Duplication:**
- The vulnerability iteration + DLP invocation pattern partially duplicates `SanitizeVulnerabilityUseCase._sanitize_one`. The node and use case serve different architectural roles (LangGraph sync node vs async use case), but the logic of "iterate vulns, call DLP, collect results" is repeated.
- Minor concern — the overlap is acceptable given architectural role separation, but the node could delegate to the use case:
  ```python
  use_case = SanitizeVulnerabilityUseCase(dlp_port)
  paired = asyncio.run(use_case.execute(vulnerabilities))
  ```
  This would eliminate duplication entirely.

**Naming Consistency:**
- `dlp_node`: appropriate LangGraph node naming ✅
- `per_cve`: clear dict key naming ✅
- Return dict keys (`current_node`, `dlp_result`, `skipped`, `processed`, `total_redactions`, `per_cve`): consistent ✅

**Docstrings:**
- Full docstring with Args/Returns present ✅
- Documents the "skips gracefully if no DLP port" behavior ✅

**Test Coverage Implications:**
- `asyncio.run()` inside sync function with async mock port creates test complexity. Test must mock `dlp_port.sanitize` as an async coroutine (using `AsyncMock`), which is non-obvious.
- Three distinct branches (no port, empty vulns, normal path) need separate test cases.

**Issues Found:**

| Severity | Type | Location | Description |
|----------|------|----------|-------------|
| ⛔ HIGH-ADVISORY | Length | dlp_node.py:23–105 | `dlp_node` is 82 lines (threshold: 30). Multiple concerns should be extracted into helpers. |
| ⚠️ MEDIUM | Performance | dlp_node.py:77–78 | `asyncio.run()` called in a for-loop creates N event loops sequentially. Should use one `asyncio.run(asyncio.gather(...))`. |
| ℹ️ ADVISORY | DRY | dlp_node.py:73–86 | Vulnerability iteration + DLP pattern duplicates use case logic. Consider delegating to `SanitizeVulnerabilityUseCase`. |

---

### 3. `src/siopv/infrastructure/di/dlp.py` (128 lines)

**Cyclomatic Complexity:**
All functions are linear (CC = 1):
- `create_presidio_adapter`: CC = 1 (bool() expressions are not branches) ✅
- `get_dlp_port`: CC = 1 ✅
- `create_dual_layer_dlp_adapter`: CC = 1 ✅
- `get_dual_layer_dlp_port`: CC = 1 ✅

**Function Length:**
- `create_presidio_adapter` (lines 25–52): 27 lines ✅
- `get_dlp_port` (lines 55–71): 16 lines ✅
- `create_dual_layer_dlp_adapter` (lines 74–101): 27 lines ✅
- `get_dual_layer_dlp_port` (lines 104–120): 16 lines ✅

All functions within threshold. ✅

**DRY / Duplication:** ℹ️ ADVISORY
- `create_presidio_adapter` and `create_dual_layer_dlp_adapter` share an identical preamble:
  ```python
  api_key = settings.anthropic_api_key.get_secret_value()
  haiku_model = settings.claude_haiku_model
  logger.debug(...)
  ```
  A private helper `_extract_adapter_settings(settings)` returning `(api_key, haiku_model)` would eliminate the repetition. However, at this scale (2 occurrences) this is advisory, not a blocking concern.

- `get_dlp_port` and `get_dual_layer_dlp_port` are structurally parallel by design — both are `@lru_cache(maxsize=1)` factory functions. This is intentional DI module structure.

**Naming Consistency:**
- `create_*` vs `get_*` naming is semantically precise: `create_*` always builds a new instance; `get_*` is cached (singleton). This distinction is meaningful and well-maintained. ✅
- All names are self-documenting and consistent. ✅

**Docstrings:**
- All 4 functions have full docstrings with Args/Returns ✅
- `get_dual_layer_dlp_port` explicitly documents preferred-over note vs `get_dlp_port` ✅

**Performance:**
- `@lru_cache(maxsize=1)` is the correct singleton pattern for expensive adapter initialization. ✅
- Comment noting structural subtyping satisfaction (`# PresidioAdapter satisfies DLPPort via structural subtyping (Protocol)`) is well-placed. ✅

**Test Coverage Implications:**
- `@lru_cache` requires `get_dlp_port.cache_clear()` and `get_dual_layer_dlp_port.cache_clear()` between tests to avoid state leakage.
- `settings.anthropic_api_key.get_secret_value()` requires mocking `SecretStr` — non-obvious but standard.

**Issues Found:**

| Severity | Type | Location | Description |
|----------|------|----------|-------------|
| ℹ️ ADVISORY | DRY | dlp.py:36–37, 87–88 | Settings extraction duplicated across `create_presidio_adapter` and `create_dual_layer_dlp_adapter`. Minor. |

---

## Cross-File Analysis

### DRY Violations (cross-file)
- The vulnerability processing loop pattern (`for vuln in vulnerabilities: ... dlp_port.sanitize(...)`) exists in both `dlp_node.py` and `sanitize_vulnerability.py`. The node could delegate to the use case to eliminate this duplication entirely (see above).

### Architecture Concerns
- `dlp_node.py` mixes synchronous LangGraph node interface with async DLP port via `asyncio.run()`. This is architecturally necessary but creates sequential processing under load. The `SanitizeVulnerabilityUseCase` was designed specifically to handle concurrent async DLP invocation — the node should reuse it.

### Dependency Directions
- `di/dlp.py` imports concrete adapters (`PresidioAdapter`, `DualLayerDLPAdapter`) — correct for infrastructure layer ✅
- `dlp_node.py` imports from domain (`SanitizationContext`) and application ports — correct ✅
- Use case imports from domain only — correct hexagonal direction ✅

---

## Score Breakdown

| Criterion | Max | Score | Notes |
|-----------|-----|-------|-------|
| Complexity & Maintainability | 4.0 | 3.5 | `dlp_node` is 82 lines (2.7× the 30-line threshold). CC=6, acceptable. DI module and use case are clean. |
| DRY & Duplication | 2.0 | 1.75 | Settings extraction repeated in DI (advisory). Vulnerability processing logic duplicated between node and use case (advisory-medium). |
| Naming & Clarity | 2.0 | 2.0 | All names are clear, precise, and consistent. Structured log keys well-formed. |
| Performance | 1.0 | 0.5 | `asyncio.run()` called in a for-loop in `dlp_node` creates N sequential event loops. Notable defect for batch processing scenarios. |
| Testing | 1.0 | 0.75 | Use case clean and testable. Node has `asyncio.run()` + async mock complexity. DI module needs `cache_clear()` between tests. |
| **TOTAL** | **10.0** | **8.5** | |

---

## Findings Summary

| # | Severity | File | Line(s) | Type | Description |
|---|----------|------|---------|------|-------------|
| 1 | ⛔ HIGH-ADVISORY | dlp_node.py | 23–105 | Length | `dlp_node` is 82 lines (threshold: 30). Extract `_run_dlp_for_vulns` and/or delegate to `SanitizeVulnerabilityUseCase`. |
| 2 | ⚠️ MEDIUM | dlp_node.py | 77–78 | Performance | `asyncio.run()` inside for-loop creates N event loops sequentially. Use `asyncio.run(asyncio.gather(...))` instead. |
| 3 | ℹ️ ADVISORY | dlp_node.py | 73–86 | DRY | Vulnerability iteration + DLP logic duplicates `SanitizeVulnerabilityUseCase`. Consider delegating. |
| 4 | ℹ️ ADVISORY | di/dlp.py | 36–37, 87–88 | DRY | Settings extraction (`api_key`, `haiku_model`) duplicated across two create functions. |

---

## Verdict

**BATCH 2 SCORE: 8.5/10**

**RESULT: ❌ FAIL**
*(Does NOT meet SIOPV threshold of >= 9.5/10)*

**Primary Blocking Issue:** `dlp_node.py` has two structural defects:
1. Single function of 82 lines (should be < 30 per threshold)
2. `asyncio.run()` inside a for-loop creates sequential event loops instead of batching with `asyncio.gather` — a meaningful performance regression under load

**Required Fixes Before PASS:**
1. Refactor `dlp_node` into smaller helpers (or delegate to `SanitizeVulnerabilityUseCase`)
2. Replace `asyncio.run()` in for-loop with `asyncio.run(asyncio.gather(...))`
