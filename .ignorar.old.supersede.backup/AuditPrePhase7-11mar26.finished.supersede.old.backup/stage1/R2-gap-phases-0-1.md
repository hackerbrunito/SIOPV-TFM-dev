# R2 — Gap Analysis: Phase 0 & Phase 1

> Analyst: gap-analyzer-phases-0-1 | Date: 2026-03-11
> Source: R1 requirements matrix vs. implemented code

---

## Phase 0: Setup & Environment

| ID | Description | Status | Evidence / Notes |
|----|-------------|--------|------------------|
| REQ-P0-001 | Dev environment with all dependencies | **IMPLEMENTED** | `pyproject.toml:19-58` declares all deps (langgraph, anthropic, chromadb, xgboost, shap, lime, presidio, openfga, etc.) |
| REQ-P0-002 | API keys: Anthropic, NVD, GitHub, Tavily | **IMPLEMENTED** | `settings.py:32` `anthropic_api_key: SecretStr`, `:37` `nvd_api_key`, `:42` `github_token`, `:49` `tavily_api_key` |
| REQ-P0-003 | CISA KEV dataset for ML training | **PARTIAL** | CLI `train_model` command exists (`main.py:155-249`) but no script/automation to download CISA KEV. Dataset assumed pre-existing. |
| REQ-P0-004 | Git repo with project structure + basic CI | **IMPLEMENTED** | Git repo active; `.github/workflows/ci.yml` present with lint/typecheck/test jobs |
| REQ-P0-005 | `pyproject.toml` PEP 517/518/621 | **IMPLEMENTED** | `pyproject.toml:1-8` uses `[project]` table (PEP 621), hatchling build backend (PEP 517) |
| REQ-P0-006 | Lock file versioned in Git | **IMPLEMENTED** | `uv.lock` exists at repo root |
| REQ-P0-007 | `.env.example` template | **MISSING** | No `.env.example` file found anywhere in repo |
| REQ-P0-008 | `detect-secrets` in pre-commit | **MISSING** | `.pre-commit-config.yaml` has ruff + mypy only. No `detect-secrets` hook. |
| REQ-P0-009 | Pre-commit: ruff, black, mypy, detect-secrets, trailing-whitespace | **PARTIAL** | ruff (linter+formatter) ✅, mypy ✅. Missing: `detect-secrets`, `trailing-whitespace`. Black replaced by ruff-format (acceptable). |
| REQ-P0-010 | Hexagonal architecture dirs | **IMPLEMENTED** | `src/siopv/` contains: `domain/`, `application/`, `adapters/`, `infrastructure/`, `interfaces/` — matches hex arch |
| REQ-P0-011 | Pydantic Settings, never hardcoded | **IMPLEMENTED** | `settings.py` uses `pydantic_settings.BaseSettings` with `SecretStr` for secrets, env vars via `SIOPV_` prefix |
| REQ-P0-012 | Docker multi-stage, python:3.12-slim, non-root UID 1000 | **MISSING** | No `Dockerfile` found in repo |
| REQ-P0-013 | GitHub Actions CI: Lint, Test, Security, Build | **PARTIAL** | `ci.yml` has Lint, TypeCheck, Test stages. Missing: **Security** stage (SAST/secrets scan) and **Build** stage (Docker image) |
| REQ-P0-014 | Conventional Commits + semantic-release | **MISSING** | No `commitlint`, `semantic-release`, or conventional-commit config found in pyproject.toml or any config file |
| REQ-P0-015 | GitHub Flow: main protected, feature/*, PRs | **PARTIAL** | CI triggers on `main` + `develop` branches. Branch protection rules not verifiable from code (GitHub settings). `develop` branch not part of GitHub Flow spec (should be `main` + `feature/*` only). |
| REQ-P0-016 | Structlog JSON, ISO 8601, correlation IDs | **PARTIAL** | `logging/setup.py:29` has `TimeStamper(fmt="iso")` ✅, `JSONRenderer` for production ✅. **Missing: correlation ID injection** — no `run_id`/`thread_id` bound to structlog context. |
| REQ-P0-017 | Sensitive data masking in structlog | **MISSING** | No masking processor in `logging/setup.py`. No grep hits for `mask`/`sanitize`/`sensitive` in logging module. |

### Phase 0 Summary
| Status | Count |
|--------|-------|
| IMPLEMENTED | 7 |
| PARTIAL | 5 |
| MISSING | 5 |

---

## Phase 1: Ingesta y Preprocesamiento

| ID | Description | Status | Evidence / Notes |
|----|-------------|--------|------------------|
| REQ-P1-001 | Module name: `Ingestion_Engine` | **IMPLEMENTED** | Module implemented as `application/use_cases/ingest_trivy.py` (class `IngestTrivyReportUseCase`) + `orchestration/nodes/ingest_node.py`. Name differs but function matches. |
| REQ-P1-002 | Model: Claude Haiku 4.5 | **PARTIAL** | `settings.py:33` declares `claude_haiku_model = "claude-haiku-4-5-20251001"` but Phase 1 ingestion code **does not use any LLM call**. The parser is pure Python, no Claude invocation. Spec says Haiku should be the model for this phase. |
| REQ-P1-003 | Input: Trivy JSON (`Results[].Vulnerabilities[]`) | **IMPLEMENTED** | `trivy_parser.py:24-30` handles Trivy schema v2, iterates `Results[].Vulnerabilities[]` |
| REQ-P1-004 | Output: validated, deduplicated `VulnerabilityRecord` list | **IMPLEMENTED** | `ingest_trivy.py:61-77` returns `IngestionResult.records` (list of Pydantic-validated, deduplicated `VulnerabilityRecord`) |
| REQ-P1-005 | Map-Reduce: chunk max 50 vulns per chunk | **MISSING** | No chunking logic found. `batch_size` CLI param exists (`main.py:58-61`) but is **never passed** to the use case or parser. No 50-vuln chunking in `IngestTrivyReportUseCase` or `TrivyParser`. |
| REQ-P1-006 | Pydantic schema: `cve_id`, `package_name`, `installed_version`, `fixed_version`, `severity`, `cvss_v3_score` | **IMPLEMENTED** | `domain/entities/__init__.py:30-37` — all 6 fields present with strict types via value objects (`CVEId`, `PackageVersion`, `SeverityLevel`, `CVSSScore`) |
| REQ-P1-007 | `severity`: `Literal["CRITICAL","HIGH","MEDIUM","LOW","UNKNOWN"]` | **IMPLEMENTED** | `domain/value_objects/__init__.py:25` defines `SeverityLevel = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]` exactly as spec |
| REQ-P1-008 | Dedup by `(cve_id, package_name, installed_version)` — keep first, aggregate locations | **IMPLEMENTED** | `domain/entities/__init__.py:117-122` `dedup_key` returns the 3-tuple. `domain/services/__init__.py:19-57` deduplicates and merges locations via `merge_location()`. |
| REQ-P1-009 | Batch processing by `package_name` before LLM invocation | **PARTIAL** | `domain/services/__init__.py` has `group_by_package()` function. `ingest_trivy.py:152` calls it. But `by_package` result is **not propagated to LangGraph state** — `ingest_node.py:60-63` only returns `vulnerabilities` list, drops `by_package`. No downstream LLM batching uses it. |

### Phase 1 Summary
| Status | Count |
|--------|-------|
| IMPLEMENTED | 5 |
| PARTIAL | 3 |
| MISSING | 1 |

---

## Combined Totals (Phase 0 + Phase 1)

| Status | Phase 0 | Phase 1 | Total |
|--------|---------|---------|-------|
| IMPLEMENTED | 7 | 5 | **12** |
| PARTIAL | 5 | 3 | **8** |
| MISSING | 5 | 1 | **6** |
| **Total** | **17** | **9** | **26** |

---

## Top Gaps (ordered by severity)

### MISSING (must create from scratch)
1. **REQ-P0-007** — `.env.example` template (quick fix)
2. **REQ-P0-008** — `detect-secrets` pre-commit hook (quick fix)
3. **REQ-P0-012** — Dockerfile (multi-stage, non-root) — significant effort
4. **REQ-P0-014** — Conventional Commits + semantic-release config — moderate effort
5. **REQ-P0-017** — Structlog sensitive data masking processor — moderate effort
6. **REQ-P1-005** — Map-Reduce chunking (50 vulns/chunk) — moderate effort

### PARTIAL (needs completion)
1. **REQ-P0-009** — Add `detect-secrets` + `trailing-whitespace` to pre-commit
2. **REQ-P0-013** — Add Security + Build stages to CI
3. **REQ-P0-016** — Add correlation ID binding to structlog
4. **REQ-P1-002** — Phase 1 doesn't use Claude Haiku (no LLM call at all)
5. **REQ-P1-009** — `by_package` grouping computed but dropped at node boundary

---

*End of R2 report — 26 requirements assessed (12 IMPLEMENTED, 8 PARTIAL, 6 MISSING)*
