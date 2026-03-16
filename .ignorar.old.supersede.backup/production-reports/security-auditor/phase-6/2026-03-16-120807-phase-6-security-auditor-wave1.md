# Security Audit Report — Phase 6 (Wave 1)

- **Agent:** security-auditor
- **Wave:** 1 (parallel)
- **Start:** 2026-03-16T12:00:00Z
- **End:** 2026-03-16T12:08:07Z
- **Duration:** ~8 minutes
- **Files audited:** 31 (17 source + 14 test)
- **Verdict:** PASS (0 CRITICAL, 0 HIGH, 3 MEDIUM warnings)

---

## Scope

All 31 pending Python files from `.build/checkpoints/pending/`.

### Source Files (17)
1. `src/siopv/adapters/dlp/dual_layer_adapter.py`
2. `src/siopv/adapters/dlp/haiku_validator.py`
3. `src/siopv/adapters/dlp/presidio_adapter.py`
4. `src/siopv/application/orchestration/edges.py`
5. `src/siopv/application/orchestration/nodes/enrich_node.py`
6. `src/siopv/application/orchestration/nodes/ingest_node.py`
7. `src/siopv/application/ports/__init__.py`
8. `src/siopv/application/ports/feature_engineering.py`
9. `src/siopv/application/ports/parsing.py`
10. `src/siopv/application/use_cases/classify_risk.py`
11. `src/siopv/application/use_cases/ingest_trivy.py`
12. `src/siopv/domain/authorization/value_objects.py`
13. `src/siopv/domain/services/discrepancy.py`
14. `src/siopv/infrastructure/di/authentication.py`
15. `src/siopv/infrastructure/di/authorization.py`
16. `src/siopv/infrastructure/di/dlp.py`
17. `src/siopv/infrastructure/logging/setup.py`
18. `src/siopv/interfaces/cli/main.py`

### Test Files (14)
1. `tests/unit/adapters/dlp/test_dual_layer_adapter.py`
2. `tests/unit/adapters/dlp/test_haiku_validator.py`
3. `tests/unit/adapters/dlp/test_presidio_adapter.py`
4. `tests/unit/adapters/external_apis/test_epss_client.py`
5. `tests/unit/adapters/external_apis/test_github_advisory_client.py`
6. `tests/unit/adapters/external_apis/test_nvd_client.py`
7. `tests/unit/adapters/external_apis/test_tavily_client.py`
8. `tests/unit/adapters/vectorstore/test_chroma_adapter.py`
9. `tests/unit/application/test_classify_risk.py`
10. `tests/unit/application/test_ingest_trivy.py`
11. `tests/unit/domain/privacy/test_privacy_domain.py`
12. `tests/unit/infrastructure/di/test_authentication_di.py`
13. `tests/unit/infrastructure/di/test_authorization_di.py`
14. `tests/integration/test_authorization_integration.py`

---

## OWASP Top 10 Audit Results

### CWE-798: Hardcoded Credentials — PASS

- No hardcoded API keys, passwords, or tokens in any source file.
- All API keys flow through Pydantic `SecretStr` fields via `get_secret_value()`.
- `ANTHROPIC_API_KEY` read from environment variable (dual_layer_adapter.py line 305).
- DI factories use `get_settings()` — no inline secrets.
- Test files use clearly fake values: `"test-key"`, `"ghp_test_token"`, `"tvly-test-key"`.

### CWE-89: SQL Injection — PASS

- No raw SQL statements anywhere in the codebase.
- CSV parsing uses `csv.DictReader` (not SQL).
- SQLite checkpointer handled by LangGraph library (not custom SQL).

### CWE-78: OS Command Injection — PASS

- Single `subprocess.run` in `cli/main.py` uses list form `[sys.executable, "-m", "streamlit", "run", ...]`.
- No `shell=True`, `os.system()`, `os.popen()`, or `eval()`.

### CWE-79: Cross-Site Scripting — N/A

- CLI application with no HTML output. Streamlit (Phase 7) not yet implemented.

### CWE-502: Insecure Deserialization — PASS

- JSON parsing uses `json.loads()` with Pydantic model validation downstream.
- No `pickle.loads()`, `yaml.unsafe_load()`, or `marshal.loads()`.
- Pydantic v2 frozen models with field validators provide schema-enforced deserialization.

### CWE-22: Path Traversal — PASS

- File paths come from pipeline state (trusted internal source), not user input.

### CWE-287/CWE-862: Authentication/Authorization Bypass — PASS

- OpenFGA authorization check runs as first graph node (`authorize`).
- OIDC authentication via Keycloak with RS256 JWT validation.
- Authorization value objects validate IDs with regex patterns.
- Generic error messages on validation failure — avoids disclosing validation rules.

### CWE-327: Weak Cryptography — PASS

- No custom cryptographic implementations.
- JWT validation delegated to OIDC library (RS256 algorithm).

### CWE-200: Information Exposure — MEDIUM (see findings)

### CWE-943: LLM-Specific (Prompt Injection) — MEDIUM (see findings)

---

## Findings

### M-1: CLI Error Message Information Disclosure (MEDIUM)

**File:** `src/siopv/interfaces/cli/main.py`
**Description:** `typer.echo(f"Pipeline failed: {exc}", err=True)` exposes raw exception details.
**Risk:** Information leakage to CLI users. Standard practice for CLI tools.
**Severity:** MEDIUM (non-blocking)

### M-2: LLM Prompt Injection Vector in DLP Haiku (MEDIUM)

**File:** `src/siopv/adapters/dlp/haiku_validator.py`, `src/siopv/adapters/dlp/dual_layer_adapter.py`
**Description:** User-supplied text embedded directly into Haiku validation prompt via format string.
**Mitigating factors:**
  1. Haiku output constrained to JSON schema — non-JSON responses rejected.
  2. Fail-open design means worst case equals Haiku being unavailable.
  3. Presidio (rule-based) runs independently as first layer.
  4. Input comes from Trivy reports (machine-generated), not direct user text.
**Severity:** MEDIUM (non-blocking)

### M-3: Fail-Open DLP Design (MEDIUM)

**File:** `src/siopv/adapters/dlp/dual_layer_adapter.py`, `src/siopv/adapters/dlp/haiku_validator.py`
**Description:** When Haiku API fails, DLP returns "no PII found" rather than blocking.
**Mitigating factors:**
  1. Documented architectural decision (availability over strictness).
  2. Presidio (local, rule-based) always runs regardless of Haiku status.
  3. Dual-layer design ensures at least one layer always operates.
**Severity:** MEDIUM (non-blocking)

---

## Test File Security Review

All 14 test files reviewed. No security concerns:
- No real credentials (all obvious fakes)
- No real network calls (all mocked)
- No writes to production paths

---

## Summary

| Severity | Count | Blocking? |
|----------|-------|-----------|
| CRITICAL | 0 | — |
| HIGH | 0 | — |
| MEDIUM | 3 | No |
| LOW | 0 | — |

**VERDICT: PASS**

All MEDIUM findings have adequate mitigations. No code changes required for Phase 6 gate.
