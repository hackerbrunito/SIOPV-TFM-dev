<!-- version: 2026-02 -->
# Verification Thresholds - Single Source of Truth

**Purpose:** Centralized definition of all verification pass/fail criteria across the project.

**Last Updated:** 2026-03-13
**Status:** Active
**Referenced by:**
- `siopv/.claude/workflow/05-before-commit.md` (before-commit checklist)
- `siopv/.claude/hooks/pre-git-commit.sh` (commit blocking logic)
- `siopv/.claude/workflow/04-agents.md` (agent verification outcomes)

---

## Verification Thresholds Table

| Check | Category | PASS Criteria | FAIL Criteria | Blocking | Agent |
|-------|----------|---------------|--------------|---------:|--------|
| **ruff check (errors)** | Code Quality | 0 errors | Any error | ✅ Yes | N/A |
| **ruff check (warnings)** | Code Quality | 0 warnings | Any warning | ✅ Yes | N/A |
| **ruff format** | Code Style | No changes needed | Changes required | ✅ Yes | N/A |
| **mypy errors** | Type Safety | 0 errors | Any error | ✅ Yes | N/A |
| **pytest** | Testing | All tests pass | Any test fails | ✅ Yes | test-generator |
| **pytest coverage (overall)** | Testing | >= 83% | < 83% | ✅ Yes | test-generator |
| **best-practices-enforcer** | Standards | 0 violations | Any violation | ✅ Yes | best-practices-enforcer |
| **security-auditor** | Security | 0 CRITICAL/HIGH | Any CRITICAL/HIGH | ✅ Yes | security-auditor |
| **security-auditor (MEDIUM)** | Security | Warning level | N/A | ❌ No | security-auditor |
| **hallucination-detector** | Correctness | 0 hallucinations | Any hallucination | ✅ Yes | hallucination-detector |
| **code-reviewer score** | Code Quality | >= 9.0/10 | < 9.0/10 | ✅ Yes | code-reviewer |
| **integration-tracer** | Integration | 0 integration gaps | Any gap | ✅ Yes | integration-tracer |
| **async-safety-auditor** | Async Safety | 0 asyncio.run() in async paths | Any violation | ✅ Yes | async-safety-auditor |
| **semantic-correctness-auditor** | Semantic Correctness | 0 semantic no-ops | Any no-op | ✅ Yes | semantic-correctness-auditor |
| **smoke-test-runner** | Runtime Verification | 0 crashes, all required fields present | Any crash, timeout, or missing field | ✅ Yes | smoke-test-runner |
| **config-validator** | Configuration | All env vars documented, services consistent | Any undocumented env var or mismatched service | ✅ Yes | config-validator |
| **regression-guard** | Regression | 0 previously-passing tests failing | Any test regression in affected modules | ✅ Yes | regression-guard |
| **dependency-scanner** | Dependency Security | 0 CRITICAL CVEs, 0 HIGH CVEs | Any CRITICAL or HIGH CVE in dependencies | ✅ Yes | dependency-scanner |
| **circular-import-detector** | Import Graph | 0 circular import cycles | Any circular import cycle detected | ✅ Yes | circular-import-detector |
| **import-resolver** | Import Safety | 0 unresolvable absolute imports | Any ImportError outside safe blocks | ✅ Yes | import-resolver |
| **per-module coverage floor** | Testing | All modules >= 90% line-rate | Any module < 90% | ✅ Yes | N/A (script) |

---

## Details by Agent

### 1. best-practices-enforcer

**Scope:** Modern Python standards (Pydantic v2, httpx, structlog, pathlib, type hints)

**Violations:**
- Using `typing.List` instead of `list[str]`
- Using `typing.Dict` instead of `dict[str, Any]`
- Using `typing.Optional[X]` instead of `X | None`
- Using Pydantic v1 `class Config:` instead of `ConfigDict`
- Using `requests` instead of `httpx`
- Using `print()` instead of `structlog`
- Using `os.path` instead of `pathlib.Path`
- Missing type hints on function parameters/returns

**Pass:** 0 violations
**Fail:** Any violation found

---

### 2. security-auditor

**Scope:** OWASP Top 10, secrets, injection attacks, authentication/authorization

**Critical/High Issues:**
- Hardcoded API keys, passwords, or tokens (CWE-798)
- SQL injection patterns (CWE-89)
- Cross-site scripting (XSS) patterns (CWE-79)
- Command injection patterns (CWE-78)
- Authentication/authorization bypasses
- Insecure deserialization (CWE-502)
- Insufficient input validation
- Cryptographic weaknesses

**Medium Issues:**
- Weak hashing algorithms
- Missing security headers (advisory)
- Suspicious patterns (informational)

**Pass:** 0 CRITICAL or HIGH severity findings
**Fail:** Any CRITICAL or HIGH severity finding
**Warning (Non-blocking):** MEDIUM severity findings allowed (logged but not blocking)

---

### 3. hallucination-detector

**Scope:** Library syntax verification against Context7 MCP

**Hallucinations:**
- Using deprecated library APIs
- Incorrect function/method signatures
- Wrong parameter names or types
- Missing imports
- Version mismatches (e.g., using Pydantic v2 syntax with v1)
- Non-existent library functions

**Pass:** 0 hallucinations detected
**Fail:** Any hallucination found

---

### 4. code-reviewer

**Scope:** Code quality, maintainability, complexity, DRY principle

**Review Criteria:**
- Cyclomatic complexity > 10 per function (flag for simplification)
- Duplicate code patterns (DRY violations)
- Naming consistency and clarity
- Function/method length > 30 lines (suggest extraction)
- Missing docstrings for public functions (advisory)
- Performance bottlenecks
- Test coverage < 83%

**Pass:** Code reviewer score >= 9.0/10
**Fail:** Code reviewer score < 9.0/10

**Score Breakdown (Out of 10):**
- Complexity & Maintainability: 0-4 points
- DRY & Duplication: 0-2 points
- Naming & Clarity: 0-2 points
- Performance: 0-1 point
- Testing: 0-1 point

---

### 5. test-generator

**Scope:** Test coverage, edge cases, mock management

**Coverage Criteria:**
- Overall coverage >= 83%
- Critical paths covered (happy path + error path)
- Edge cases tested (None, empty, boundary values)
- External dependencies mocked
- Test naming follows convention: `test_<function>_<scenario>`

**Pass:** All tests pass + coverage >= 83%
**Fail:** Any test fails OR coverage < 83%

---

### 6. integration-tracer

**Scope:** End-to-end execution path integrity — from entry points to leaf implementations

**Integration Gaps:**
- Hollow entry points (CLI/graph nodes terminating in stubs)
- Parameter dropping (accepted but not forwarded)
- Dead exports (in `__all__` but never imported in execution paths)
- Unreachable code (defined but never called from any entry point)
- Broken call chains (intermediate functions not calling expected next step)

**Pass:** 0 CRITICAL + 0 HIGH integration gaps
**Fail:** Any CRITICAL or HIGH finding
**Warning (Non-blocking):** MEDIUM findings (unreachable code) allowed

---

### 7. async-safety-auditor

**Scope:** Async/sync boundary violations that cause runtime crashes or deadlocks

**Violations:**
- `asyncio.run()` inside async contexts (causes `RuntimeError: This event loop is already running`)
- Missing `await` on coroutine calls (coroutine never executes)
- Sync blocking calls (`time.sleep`, `requests.get`, synchronous DB) inside `async def`
- Event loop nesting via `nest_asyncio` (workaround, not proper fix)

**Pass:** 0 CRITICAL + 0 HIGH findings (0 asyncio.run() in async paths)
**Fail:** Any CRITICAL or HIGH finding
**Warning (Non-blocking):** MEDIUM findings (nest_asyncio usage) allowed

---

### 8. semantic-correctness-auditor

**Scope:** Code that is syntactically valid and passes linters but is semantically wrong — body does not match stated intent

**Semantic No-ops:**
- No-op validators: `@field_validator` / `@model_validator` / `@validator` body returns `v` unchanged without any condition or transformation
- Hollow functions: docstring describes behavior X but body is `pass`, `return None`, `return []`, `return {}`, or `...`
- Swallowed exceptions: `except` branch that neither logs, re-raises, nor stores the exception
- Wrong fallback returns: `except` block returns empty collection (`[]`, `{}`) when caller expects real data

**Pass:** 0 semantic no-ops (0 HIGH findings)
**Fail:** Any HIGH finding
**Warning (Non-blocking):** MEDIUM findings (wrong fallback returns) allowed

---

### 9. smoke-test-runner

**Scope:** End-to-end pipeline execution with synthetic input — the only agent that actually runs the project

**Runtime Checks:**
- Pipeline imports cleanly (`uv run python -c "import [project]"`)
- Pipeline runs start-to-end with CVE-2024-1234 without unhandled exception
- Pipeline completes within 120 seconds (timeout = CRITICAL)
- Output contains all required fields: `classification`/`category`, `severity`/`cvss_score`, `cve_id`/`id`

**Pass:** Pipeline runs without exception, all required fields present
**Fail:** Any unhandled exception, timeout, empty output, or missing required field

---

### Phase 7 Health Check

**Check:** Streamlit app starts without exception: `uv run streamlit run src/siopv/interfaces/ui/app.py --headless`
**Pass:** Process starts, no ImportError or RuntimeError in first 5 seconds
**Fail:** Any crash, ImportError, or async boundary violation at startup

---

### 10. config-validator

**Scope:** Environment variable documentation and Docker service consistency

**Checks:**
- All `settings.*` attribute accesses have corresponding entry in `.env.example`
- All `os.getenv(` calls reference a var documented in `.env.example`
- All `Settings` fields with no default are in `.env.example`
- All Docker service names referenced in code exist in `docker-compose.yml`
- All Docker service ports in code match `docker-compose.yml` definitions

**Pass:** All required env vars documented, all docker service references consistent
**Fail:** Any undocumented required env var OR any mismatched service name/port

---

### 11. regression-guard

**Scope:** Cross-phase regression detection via reverse dependency analysis and targeted pytest

**Checks:**
- Uses `git diff HEAD~1 --name-only` to identify recently changed Python files
- Builds reverse dependency map: which modules import from changed files
- Runs pytest on test files corresponding to reverse-dependent modules only
- Flags any test that was passing before and is now FAILED or ERROR

**Pass:** 0 FAILED, 0 ERROR in all reverse-dependent test modules
**Fail:** Any FAILED or ERROR in affected test modules

---

### 12. dependency-scanner

**Scope:** Known CVE detection in Python package dependencies via uv pip audit

**Checks:**
- Runs `uv pip audit` against all packages installed in the target project virtual environment
- Falls back to `pip-audit --format=json` if uv pip audit is unavailable
- Reports CRITICAL (CVSS >= 9.0), HIGH (CVSS 7.0-8.9), MEDIUM, and LOW findings
- MEDIUM and LOW are non-blocking warnings

**Pass:** 0 CRITICAL CVEs, 0 HIGH CVEs in any dependency
**Fail:** Any CRITICAL or HIGH severity CVE in any installed package

---

### 13. circular-import-detector

**Scope:** Python circular import cycle detection using AST-based import graph analysis

**Checks:**
- Parses all .py files in src/ using Python's `ast` module
- Builds a directed import graph (module A -> modules that A imports)
- Runs DFS cycle detection on the full graph
- Reports each cycle as a chain: module.a -> module.b -> module.c -> module.a
- Provides exact import lines in each file that form the cycle

**Pass:** 0 circular import cycles detected in src/
**Fail:** Any circular import cycle detected (even one causes potential ImportError at runtime)

---

### 14. import-resolver

**Agent:** `import-resolver`
**Wave:** Wave 3 (parallel)
**Checks:** All absolute `import X` and `from X import Y` statements in `src/`

| Result | Criteria |
|--------|----------|
| PASS | 0 unresolvable absolute imports |
| FAIL | Any `ModuleNotFoundError` or `ImportError` from an absolute import outside `try/except ImportError` and outside `TYPE_CHECKING` blocks |
| SKIP | If `src/` directory does not exist in target project |

**Severity:** CRITICAL — an unresolvable import causes `ImportError` at runtime, crashing the application.

**What is skipped:**
- Relative imports (`.module`, `..module`) — covered by circular-import-detector
- `TYPE_CHECKING` blocks — imports never executed at runtime
- `try/except ImportError` blocks — conditional imports, safe to skip

---

### 15. Per-Module Coverage Floor

**Script:** `.claude/scripts/check-module-coverage.py`
**When:** Runs after `pytest --cov --cov-report=xml` in the coverage step
**Input:** `coverage.xml` in the target project root

| Result | Criteria |
|--------|----------|
| PASS | All non-`__init__.py` modules in coverage.xml have line-rate >= 90% |
| FAIL | Any module with line-rate < 90% |
| WARNING | `coverage.xml` not found — run `pytest --cov --cov-report=xml` first |

**Floor:** 90% per module (in addition to the existing 83% project-wide gate)

**What is excluded:**
- `__init__.py` files (intentionally sparse, aggregates imports)
- `<string>` and `<unknown>` entries (eval'd code, not real modules)

**Note:** A project can pass the 83% project-wide gate while having individual modules
at 0%. This floor prevents new modules from being silently uncovered.

---

## Command Blockers

These checks are automatically applied by `.claude/hooks/pre-git-commit.sh`:

1. **Git commit command** is intercepted
2. **Check pending directory:** `.build/checkpoints/pending/`
   - If pending files exist: **BLOCK** with message
   - If no pending files: **ALLOW** (proceed to next check)
3. **Check code-reviewer score:** Via `.claude/scripts/check-reviewer-score.sh`
   - If score < 9.0/10: **BLOCK** with message
   - If score >= 9.0/10: **ALLOW** (all verified)
   - If no report found: **WARN** but allow (graceful degradation)
   - If parsing fails: **WARN** but allow (graceful degradation)

**Blocking Message Format (Pending Files):**
```
COMMIT BLOQUEADO: Hay {N} archivo(s) Python sin verificar por agentes.
Archivos pendientes: {LIST}
ACCION REQUERIDA: Ejecuta /verify para correr los agentes de verificacion, despues intenta commit de nuevo.
```

**Blocking Message Format (Code Reviewer Score):**
```
COMMIT BLOQUEADO: Code reviewer score no cumple con threshold >= 9.0/10.

[Score output from check-reviewer-score.sh]

ACCION REQUERIDA: Corrige los problemas de calidad identificados y ejecuta /verify nuevamente.
```

**Helper Script:** `.claude/scripts/check-reviewer-score.sh`
- Searches for most recent code-reviewer report in `.ignorar/production-reports/code-reviewer/`
- Extracts score using multiple pattern matching strategies
- Returns exit code 0 (PASS) if score >= 9.0/10
- Returns exit code 1 (FAIL) if score < 9.0/10
- Returns exit code 0 with WARNING if no report found (first-time setup)
- Returns exit code 0 with WARNING if score parsing fails (graceful degradation)

---

## Workflow Integration

### Before Commit Checklist
```
1. ✅ Ejecutar /verify (5 agentes de verificación)
2. ✅ ruff format + ruff check
3. ✅ mypy src
4. ✅ pytest (si hay tests)
```

### /verify Command
Runs automatically:
- best-practices-enforcer
- security-auditor
- hallucination-detector
- code-reviewer
- test-generator

Cleans markers in `.build/checkpoints/pending/`

### If Verification Fails
1. DO NOT commit
2. Fix errors
3. Run `/verify` again
4. Only then commit

---

## Threshold History & Changes

### Version 2026-02 (Original)
- Extracted from `.claude/workflow/05-before-commit.md`
- Centralized for consistency
- Added detail columns for each agent
- Added command blocker documentation

### Version 2026-03 (SIOPV)
- Coverage threshold updated: 80% → 83% (SIOPV current baseline)
- Added `pytest coverage (overall)` row to table
- Added Phase 7 Health Check section
- Removed meta-project-specific sections

---

## Adding New Thresholds

When adding new verification checks:

1. Update this file with new row in table
2. Add detailed section below
3. Update relevant workflow files to reference this file
4. Update `.claude/hooks/pre-git-commit.sh` if it's a blocking check
5. Document in `.claude/docs/errors-to-rules.md` if threshold was controversial

---

**Maintained by:** Orchestrator + Code Implementer
**Reviewed by:** best-practices-enforcer + security-auditor
**Last verified:** 2026-03-13
