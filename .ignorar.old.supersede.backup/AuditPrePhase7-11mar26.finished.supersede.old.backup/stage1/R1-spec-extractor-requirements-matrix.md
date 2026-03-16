# R1 — SIOPV Requirements Matrix (Phases 0–6)

> Extracted: 2026-03-11 | Source: `docs/SIOPV_Propuesta_Tecnica_v2.txt` (806 lines)
> Scope: Phases 0–6 only. Phase 7/8 libraries listed as forward-looking inventory.

---

## Section 1 — Requirements Catalog (Phases 0–6)

### Phase 0: Setup & Environment

| ID | Description | Spec Reference |
|----|-------------|----------------|
| REQ-P0-001 | Configure dev environment with all listed dependencies | §10.1 (L800) |
| REQ-P0-002 | Obtain API keys: Anthropic, NVD, GitHub, Tavily | §10.1 (L801) |
| REQ-P0-003 | Download CISA KEV dataset for ML training data construction | §10.1 (L802) |
| REQ-P0-004 | Establish Git repo with project structure and basic CI | §10.1 (L804) |
| REQ-P0-005 | `pyproject.toml` with all dependencies declared (PEP 517/518/621) | §8.5 (L621-624) |
| REQ-P0-006 | Lock file (`uv.lock` or `poetry.lock`) versioned in Git | §8.5 (L623) |
| REQ-P0-007 | `.env.example` template with all required env vars (no real values) | §8.8 (L692) |
| REQ-P0-008 | `detect-secrets` in pre-commit hooks | §8.8 (L695) |
| REQ-P0-009 | Pre-commit hooks: ruff, black, mypy, detect-secrets, trailing-whitespace | §8.4 (L613) |
| REQ-P0-010 | Hexagonal architecture directory structure (domain/application/adapters/infrastructure/interfaces/tests) | §8.2 (L575-582) |
| REQ-P0-011 | Pydantic Settings for all configuration (never hardcoded) | §8.1 Factor III (L546) |
| REQ-P0-012 | Docker multi-stage build: python:3.12-slim, non-root user (UID 1000) | §8.6 (L628-632) |
| REQ-P0-013 | GitHub Actions CI pipeline: Lint, Test, Security, Build stages | §8.6 (L633-654) |
| REQ-P0-014 | Conventional Commits enforced with semantic-release | §8.9 (L697-709) |
| REQ-P0-015 | GitHub Flow branching: main (protected), feature/* branches, PRs required | §8.9 (L705-709) |
| REQ-P0-016 | Structlog with JSON format, ISO 8601 timestamps, correlation IDs | §8.7 (L658-661) |
| REQ-P0-017 | Sensitive data masking processor in structlog (API keys, tokens, PII) | §8.7 (L661) |

### Phase 1: Ingesta y Preprocesamiento

| ID | Description | Spec Reference |
|----|-------------|----------------|
| REQ-P1-001 | Module name: `Ingestion_Engine` | §3.1 (L147) |
| REQ-P1-002 | Model: Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) | §3.1 (L148) |
| REQ-P1-003 | Input: Trivy JSON report (`Results[].Vulnerabilities[]`) | §3.1 (L149) |
| REQ-P1-004 | Output: List of validated, deduplicated `VulnerabilityRecord` objects | §3.1 (L150) |
| REQ-P1-005 | Map-Reduce pattern: chunk JSON into max 50 vulnerabilities per chunk | §3.1 (L152-155) |
| REQ-P1-006 | Pydantic schema validation with strict types: `cve_id`, `package_name`, `installed_version`, `fixed_version`, `severity`, `cvss_v3_score` | §3.1 (L156-163) |
| REQ-P1-007 | `severity` field: `Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]` | §3.1 (L161) |
| REQ-P1-008 | Deduplication by tuple `(cve_id, package_name, installed_version)` — keep first, aggregate locations | §3.1 (L163) |
| REQ-P1-009 | Batch processing by `package_name` before LLM invocation | §3.1 (L164) |

### Phase 2: Enriquecimiento de Contexto (Dynamic RAG)

| ID | Description | Spec Reference |
|----|-------------|----------------|
| REQ-P2-001 | Module name: `Dynamic_RAG_Researcher` | §3.2 (L168) |
| REQ-P2-002 | Model: Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) | §3.2 (L169) |
| REQ-P2-003 | Data sources: NVD API, GitHub Security Advisories, FIRST EPSS, Tavily Search | §3.2 (L170) |
| REQ-P2-004 | Storage: ChromaDB hybrid (SQLite persistence + in-memory cache) | §3.2 (L171) |
| REQ-P2-005 | NVD endpoint: `/cves/2.0?cveId={CVE-ID}` | §3.2 (L173) |
| REQ-P2-006 | NVD rate limits: 5 req/30s (no key), 50 req/30s (with `NVD_API_KEY`) | §3.2 (L174-175) |
| REQ-P2-007 | GitHub Security Advisories via GraphQL API (not REST) | §3.2 (L176) |
| REQ-P2-008 | GitHub rate limits: 60/hr (no auth), 5000/hr (with `GITHUB_TOKEN`) | §3.2 (L177-178) |
| REQ-P2-009 | EPSS endpoint: `https://api.first.org/data/v1/epss?cve={CVE-ID}` — fields: `epss`, `percentile` | §3.2 (L180-181) |
| REQ-P2-010 | Tavily as OSINT fallback when structured sources insufficient | §3.2 (L182) |
| REQ-P2-011 | CRAG pattern: parallel query NVD+GitHub+EPSS → relevance eval → conditional Tavily if < 0.6 → consolidate in ChromaDB | §3.2 (L183-188) |
| REQ-P2-012 | Claude Sonnet evaluates document relevance (score 0-1); Tavily triggered if < 0.6 | §3.2 (L186-187) |
| REQ-P2-013 | ChromaDB: SQLite persistence, LRU cache (1000 queries), eviction if > 4GB | §3.2 (L190-193) |

### Phase 3: Clasificación y Score de Riesgo (ML)

| ID | Description | Spec Reference |
|----|-------------|----------------|
| REQ-P3-001 | Module name: `ML_Risk_Classifier` | §3.3 (L196) |
| REQ-P3-002 | Primary algorithm: XGBoost with Optuna hyperparameter tuning | §3.3 (L197) |
| REQ-P3-003 | Baseline algorithm: Random Forest for comparison/ensemble | §3.3 (L198) |
| REQ-P3-004 | XAI framework: SHAP (global analysis) + LIME (local explanations) | §3.3 (L199) |
| REQ-P3-005 | Training data: CISA KEV (positive class, ~1200 CVEs) | §3.3 (L202-204) |
| REQ-P3-006 | Secondary source: EPSS historical data correlated with confirmed exploitation | §3.3 (L205) |
| REQ-P3-007 | Negative class: stratified NVD sample (EPSS < 0.1, age > 2 years, not in KEV) — ratio 1:3 | §3.3 (L206) |
| REQ-P3-008 | Balancing: SMOTE + class weighting in loss function | §3.3 (L207-209) |
| REQ-P3-009 | Feature vector: 14 features (cvss_base_score, attack_vector, attack_complexity, privileges_required, user_interaction, scope, confidentiality/integrity/availability_impact, epss_score, epss_percentile, days_since_publication, has_exploit_ref, cwe_category) | §3.3 (L210-257) |
| REQ-P3-010 | SHAP global analysis: feature importance charts | §3.3 (L258-259) |
| REQ-P3-011 | LIME local explanations: per-vulnerability feature contributions | §3.3 (L260) |
| REQ-P3-012 | Output tuple: `(risk_probability, shap_values, lime_explanation)` propagated to LangGraph state | §3.3 (L261) |

### Phase 4: Orquestación y Gestión de Incertidumbre

| ID | Description | Spec Reference |
|----|-------------|----------------|
| REQ-P4-001 | Module name: `LangGraph_Orchestrator` | §3.4 (L264) |
| REQ-P4-002 | Model: Claude Sonnet 4.5 for state orchestration | §3.4 (L265) |
| REQ-P4-003 | Persistence: SQLite for graph state checkpointing | §3.4 (L266) |
| REQ-P4-004 | Uncertainty Trigger: adaptive threshold, NOT fixed value | §3.4 (L267-273) |
| REQ-P4-005 | Discrepancy formula: `|ml_score - llm_confidence|` | §3.4 (L269) |
| REQ-P4-006 | Dynamic threshold: `percentile_90(historical_discrepancies)` recalculated weekly from last 500 evaluations | §3.4 (L270, 272) |
| REQ-P4-007 | Escalation rule: `discrepancy > threshold OR llm_confidence < 0.7` → escalate to human | §3.4 (L271) |
| REQ-P4-008 | Checkpoint after each node transition — enables resumption, async human review, post-mortem audit | §3.4 (L275-278) |
| REQ-P4-009 | 8-phase pipeline as LangGraph nodes with conditional branching | §3 (L143-144) |
| REQ-P4-010 | Each node = pure function transforming typed state (TypedDict or Pydantic) | §2.2 (L142) |
| REQ-P4-011 | Correlation ID (UUID4) in `PipelineState.run_id`, propagated through all nodes | §spec-findings (L98-100) |

### Phase 5: Control de Acceso (Zero Trust)

| ID | Description | Spec Reference |
|----|-------------|----------------|
| REQ-P5-001 | Module name: `Authorization_Gatekeeper` | §3.5 (L281) |
| REQ-P5-002 | Technology: OpenFGA for fine-grained authorization | §3.5 (L282) |
| REQ-P5-003 | Methodology: ReBAC (Relationship-Based Access Control), not RBAC | §3.5 (L283-285) |
| REQ-P5-004 | Policies: owner→view, analyst→remediate, auditor→export | §3.5 (L286-288) |
| REQ-P5-005 | Authorization query format: `check(user:X, relation:R, object:O)` | §3.5 (L291) |
| REQ-P5-006 | Intercept every request before sensitive operations | §3.5 (L290) |
| REQ-P5-007 | Return 403 Forbidden with audit log on denied access | §3.5 (L293) |

### Phase 6: Privacidad y DLP

| ID | Description | Spec Reference |
|----|-------------|----------------|
| REQ-P6-001 | Module name: `Data_Privacy_Guardrail` | §3.6 (L296) |
| REQ-P6-002 | Layer 1 (deterministic): Microsoft Presidio (Regex + NLP) | §3.6 (L297, 300) |
| REQ-P6-003 | Layer 2 (semantic): Claude Haiku 4.5 for contextual validation | §3.6 (L298, 306) |
| REQ-P6-004 | Presidio detects: IPs, emails, API tokens, PII (phone, SSN, CC), internal URLs, filesystem paths | §3.6 (L301-305) |
| REQ-P6-005 | Haiku detects: internal project names, client names, trade secrets, internal architecture info | §3.6 (L307-310) |
| REQ-P6-006 | All pipeline output passes through DLP BEFORE any logging operation | §3.6 (L313) |
| REQ-P6-007 | LangSmith logs contain only sanitized data | §3.6 (L314) |
| REQ-P6-008 | Optional local logging for unsanitized traces with restricted access | §3.6 (L315) |

### Cross-Cutting Requirements (apply to Phases 0–6)

| ID | Description | Spec Reference |
|----|-------------|----------------|
| REQ-XC-001 | Circuit breaker per external API: CLOSED→OPEN (5 failures)→HALF-OPEN (60s timeout) | §4.1 (L353-357) |
| REQ-XC-002 | Fallback: Claude API → retry w/ exponential backoff (max 3), then manual review | §4.2 (L362-364) |
| REQ-XC-003 | Fallback: NVD → use 24h local cache; on miss, enqueue for retry | §4.2 (L365-367) |
| REQ-XC-004 | Fallback: GitHub → degrade to no-auth (60 req/hr), alert admin | §4.2 (L368-370) |
| REQ-XC-005 | Fallback: EPSS → use last known score with `stale_data=True` flag | §4.2 (L371-373) |
| REQ-XC-006 | Fallback: Tavily → omit OSINT, proceed with NVD/GitHub only | §4.2 (L374-376) |
| REQ-XC-007 | Fallback: ML model → CVSS+EPSS heuristic, mark `degraded_confidence` | §4.2 (L377-379) |
| REQ-XC-008 | Fallback: ChromaDB OOM → evict LRU; if persists, no-cache mode | §4.2 (L380-382) |
| REQ-XC-009 | Rate limiter: Token Bucket algorithm, centralized across all APIs | §4.3 (L384-386) |
| REQ-XC-010 | Priority scheduling: CVEs with CVSS ≥ 9.0 get priority in request queue | §4.3 (L388) |
| REQ-XC-011 | ML quality gates: Precision ≥ 0.85, Recall ≥ 0.90, F1 ≥ 0.87, AUC-ROC ≥ 0.92, Cal. Error ≤ 0.05 | §5.1 (L392-410) |
| REQ-XC-012 | Operational KPIs: triage < 5 min/CVE, FP reduction ≥ 60%, escalation < 15%, p95 < 30s, avail ≥ 99.5% | §5.2 (L412-430) |
| REQ-XC-013 | XAI targets: LIME fidelity ≥ 0.80, SHAP consistency ≥ 0.90, user trust ≥ 4.0/5.0 | §5.3 (L432-444) |
| REQ-XC-014 | 100% type hints (PEP 484/604), mypy strict mode | §8.4 (L607-608) |
| REQ-XC-015 | Pydantic v2 for all data models, DTOs, configuration | §8.4 (L609) |
| REQ-XC-016 | Ruff linter + Black formatter (line-length=100, target py312) | §8.4 (L611-612) |
| REQ-XC-017 | Testing: pytest + pytest-asyncio + pytest-cov + pytest-mock + pytest-xdist | §8.4 (L615) |
| REQ-XC-018 | Coverage: ≥ 80% global, ≥ 90% domain layer | §8.4 (L616) |
| REQ-XC-019 | Unit + Integration (SQLite + API mocks) + E2E (Testcontainers) test layers | §8.4 (L617-619) |
| REQ-XC-020 | OWASP Top 10 mitigations demonstrably addressed | §8.8 (L667-689) |
| REQ-XC-021 | SSRF mitigation: allowlist of permitted external API domains | §8.8 (L689) |
| REQ-XC-022 | SOLID principles applied throughout (SRP, OCP, LSP, ISP, DIP) | §8.3 (L583-602) |
| REQ-XC-023 | 12-Factor App compliance (all 12 factors) | §8.1 (L533-573) |
| REQ-XC-024 | Google Style docstrings on all public functions, validated with pydocstyle | §8.10 (L711) |
| REQ-XC-025 | ADRs in `docs/adr/` for important technical decisions | §8.10 (L713) |
| REQ-XC-026 | SLSA Level 2 compliance: artifact checksums, signed commits (GPG) | §8.8 (L685) |
| REQ-XC-027 | OpenTelemetry instrumentation for FastAPI, httpx, SQLAlchemy | §8.7 (L663) |
| REQ-XC-028 | Health endpoints: `/health` (liveness), `/ready` (readiness) with dependency checks | §8.7 (L665) |
| REQ-XC-029 | FastAPI REST interface in `interfaces/api/`, port via `$PORT` env var | §8.1 Factor VII (L557) |
| REQ-XC-030 | CLI via Typer in `interfaces/cli/` for admin/migration tasks | §8.1 Factor XII (L573) |
| REQ-XC-031 | Docker Compose: local replicates cloud services (PostgreSQL, Redis, ChromaDB) | §8.1 Factor X (L567) |
| REQ-XC-032 | HEALTHCHECK in Dockerfile for orchestrators | §8.6 (L632) |
| REQ-XC-033 | Dependency separation: [dependencies], [dev-dependencies], [test-dependencies] | §8.5 (L624) |
| REQ-XC-034 | Dependabot/Renovate for automated weekly dependency updates | §8.5 (L625) |
| REQ-XC-035 | Hardware target: MacBook Air M3 16GB — ChromaDB max 4GB RAM, ~2GB storage | §9.3 (L743-747) |

---

## Summary: Requirements Count by Phase

| Phase | Count |
|-------|-------|
| Phase 0 (Setup) | 17 |
| Phase 1 (Ingesta) | 9 |
| Phase 2 (RAG/Enriquecimiento) | 13 |
| Phase 3 (ML Clasificación) | 12 |
| Phase 4 (Orquestación) | 11 |
| Phase 5 (Autorización) | 7 |
| Phase 6 (DLP/Privacidad) | 8 |
| Cross-Cutting (XC) | 35 |
| **Total** | **112** |

---

## Section 2 — Forward-Looking Phase 7/8 Library Inventory

| Library / Integration | Phase | Role |
|-----------------------|-------|------|
| **Streamlit** (≥1.40.0) | 7 | Dashboard for human-in-the-loop review of escalated vulnerabilities |
| **SQLite polling** | 7 | Mechanism for dashboard to detect escalated cases (not websockets) |
| **LIME visualization** | 7 | Bar charts showing per-feature ML score contributions in Tríada de Evidencia |
| **Email/Slack notifications** | 7 | Timeout escalation cascade (4h/8h/24h levels) |
| **Jira REST API v3** | 8 | Ticket creation with enriched schema (Summary, Description, Priority, Labels, Custom Fields) |
| **fpdf2** (≥2.7.0) | 8 | PDF audit report generation (ISO 27001 / SOC 2 compliant) |
| **LangSmith** | 8 | CoT audit trail — traces populate PDF Chain-of-Thought section |
| **Redis** | 7-8 | EPSS cache layer (optional local dev, required full stack) |
| **FastAPI** | 7-8 | REST interface already required cross-cutting; serves dashboard API |
| **OpenTelemetry** | 7-8 | Distributed tracing for FastAPI, httpx, SQLAlchemy (cross-cutting, intensifies in prod) |

---

*End of report — 112 requirements extracted across Phases 0–6, plus 10 forward-looking library entries for Phases 7–8.*
