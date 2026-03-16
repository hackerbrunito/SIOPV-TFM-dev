# STAGE-3.5 — Aggregated Brief for STAGE-4 Input

**Generated:** 2026-03-12
**Agent:** reports-summarizer-n-aggregator
**Sources:**
- `2026-03-12-10.21.23-stage3.5-extractor-stage1-delta.md`
- `2026-03-12-10.21.23-stage3.5-extractor-stage2-violations.md`
- `2026-03-12-10.21.14-stage3.5-extractor-stage3-patterns.md`

---

## Part 1: Stage 1 Deltas

### 1.1 Overall Requirements Counts

| Metric | Value |
|--------|-------|
| Total requirements extracted | 112 |
| Phase-specific assessed | 77 |
| Cross-cutting defined | 35 |
| Cross-cutting assessed in-depth | 8 |
| IMPL (phase-specific) | 45 (58%) |
| PARTIAL (phase-specific) | 21 (27%) |
| MISSING (phase-specific) | 9 (12%) |
| AMBIGUOUS (phase-specific) | 2 (3%) |
| Cross-cutting IMPL | 2 |
| Cross-cutting PARTIAL | 6 |
| Cross-cutting MISSING | 0 |

### 1.2 Phase Breakdown

| Phase | Total | IMPL | PARTIAL | MISSING | AMBIGUOUS |
|-------|-------|------|---------|---------|-----------|
| 0 — Setup | 17 | 7 | 5 | 5 | 0 |
| 1 — Ingesta | 9 | 5 | 3 | 1 | 0 |
| 2 — Enriquecimiento | 13 | 9 | 3 | 0 | 1 |
| 3 — Clasificación ML | 12 | 9 | 2 | 1 | 0 |
| 4 — Orquestación | 11 | 6 | 4 | 0 | 1 |
| 5 — Autorización | 7 | 6 | 1 | 0 | 0 |
| 6 — Privacidad/DLP | 8 | 3 | 3 | 2 | 0 |

### 1.3 MISSING Requirements — Full Catalog (9 items)

| # | ID | Phase | Description | Severity | Effort |
|---|-----|-------|-------------|----------|--------|
| 1 | REQ-P0-007 | 0 | `.env.example` template with all required env vars | HIGH | Quick |
| 2 | REQ-P0-008 | 0 | `detect-secrets` in pre-commit hooks | HIGH | Quick |
| 3 | REQ-P0-012 | 0 | Dockerfile (multi-stage, python:3.12-slim, non-root UID 1000) | HIGH | Significant |
| 4 | REQ-P0-014 | 0 | Conventional Commits + semantic-release config | MEDIUM | Moderate |
| 5 | REQ-P0-017 | 0 | Structlog sensitive data masking processor | HIGH | Moderate |
| 6 | REQ-P1-005 | 1 | Map-Reduce chunking (max 50 vulns/chunk) | MEDIUM | Moderate |
| 7 | REQ-P3-003 | 3 | Random Forest baseline/ensemble comparator | LOW | High |
| 8 | REQ-P6-007 | 6 | LangSmith integration (tracing with sanitized data) | HIGH | High |
| 9 | REQ-P6-008 | 6 | Dual-channel logging (sanitized public + restricted unsanitized) | MEDIUM | Moderate |

> **MEMORY.md correction:** REQ-P6-007 and REQ-P6-008 are absent from MEMORY.md's "Top MISSING Items." MEMORY.md item #8 (XGBoost scale_pos_weight) is actually PARTIAL, not MISSING. MEMORY.md item #9 (DLP architecture mismatch) maps to REQ-P6-006 (PARTIAL), not a MISSING item.

### 1.4 PARTIAL Requirements — Full Catalog (21 items)

| # | ID | Phase | Description | What Is Incomplete |
|---|-----|-------|-------------|--------------------|
| 1 | REQ-P0-003 | 0 | CISA KEV dataset download | No automation script; dataset assumed pre-existing |
| 2 | REQ-P0-009 | 0 | Pre-commit hooks | Missing `detect-secrets`, `trailing-whitespace` hooks |
| 3 | REQ-P0-013 | 0 | CI pipeline (GitHub Actions) | Missing Security (SAST) and Build (Docker) stages |
| 4 | REQ-P0-015 | 0 | GitHub Flow branching | Uses `develop` branch (not GitHub Flow); branch protection unverifiable |
| 5 | REQ-P0-016 | 0 | Structlog JSON + correlation IDs | Missing `run_id`/`thread_id` correlation ID injection |
| 6 | REQ-P1-002 | 1 | Claude Haiku for Phase 1 | Model configured but ingestion uses no LLM at all |
| 7 | REQ-P1-009 | 1 | Batch by package before LLM | `group_by_package()` computed but dropped at node boundary |
| 8 | REQ-P2-001 | 2 | Module name `Dynamic_RAG_Researcher` | Functional equivalent exists but no spec-matching name |
| 9 | REQ-P2-002 | 2 | Claude Sonnet model for Phase 2 | Configured in settings but never invoked |
| 10 | REQ-P2-013 | 2 | ChromaDB: 1000-query LRU + 4GB eviction | No hard 1000-query cap; no on-disk 4GB eviction logic |
| 11 | REQ-P3-006 | 3 | EPSS historical data correlation | Uses snapshot EPSS scores, not historical time-series |
| 12 | REQ-P3-008 | 3 | SMOTE + class weighting in loss | SMOTE implemented; `scale_pos_weight` not set in XGBoost |
| 13 | REQ-P4-004 | 4 | Adaptive threshold (not fixed) | Uses fixed `base_threshold` instead of adaptive percentile_90 |
| 14 | REQ-P4-006 | 4 | Persistent discrepancy history + weekly recalc | In-memory only; no persistence; recalculated per-batch not weekly |
| 15 | REQ-P4-008 | 4 | Checkpoint resumption + post-mortem audit | Checkpointing works but no `resume_pipeline()` API; no audit query |
| 16 | REQ-P4-009 | 4 | 8-phase pipeline as nodes | 6/8 nodes wired (Phase 7/8 nodes pending — expected) |
| 17 | REQ-P5-007 | 5 | 403 Forbidden + audit log on denial | Audit log works; no HTTP 403 (acceptable until FastAPI layer) |
| 18 | REQ-P6-004 | 6 | Presidio entity detection | Missing recognizers for internal URLs and filesystem paths |
| 19 | REQ-P6-005 | 6 | Haiku semantic detection categories | Prompts miss: project names, client names, trade secrets, architecture info |
| 20 | REQ-P6-006 | 6 | DLP before all logging | DLP node is audit-only; downstream nodes log unsanitized data |
| 21 | REQ-P4-009 | 4 | *(6/8 nodes is expected pre-Phase 7)* | Phase 7/8 nodes will complete this |

### 1.5 AMBIGUOUS Requirements (2 items)

| ID | Description | Issue |
|----|-------------|-------|
| REQ-P2-012 | Claude Sonnet evaluates document relevance (score 0–1) | Heuristic formula (`_calculate_relevance()`). Model ID configured but unused. May be Phase 7 concern. |
| REQ-P4-002 | Claude Sonnet 4.5 for state orchestration | `_estimate_llm_confidence()` is pure math, not an LLM call. |

> **Human decision required:** If LLM calls belong in Phases 2/4, gap count rises from 9 to 11.

### 1.6 Cross-Cutting Assessment (8 of 35 assessed)

| ID | Description | Status | Gap Detail |
|----|-------------|--------|------------|
| REQ-XC-001 | Circuit breaker per API | IMPL | Fully implemented in Phase 2 |
| REQ-XC-003 | NVD fallback: 24h local cache | PARTIAL | In-memory only, no 24h TTL enforcement |
| REQ-XC-004 | GitHub fallback: degrade to no-auth | PARTIAL | Not explicitly implemented |
| REQ-XC-005 | EPSS fallback: stale_data flag | PARTIAL | Not implemented |
| REQ-XC-006 | Tavily fallback: omit OSINT | IMPL | Fully implemented |
| REQ-XC-007 | ML fallback → CVSS+EPSS heuristic | PARTIAL | Uses severity map but no `degraded_confidence` flag |
| REQ-XC-008 | ChromaDB OOM: evict LRU | PARTIAL | LRU exists but no OOM detection/trigger |
| REQ-XC-011 | ML quality gates (5 metrics) | PARTIAL | 4/5 metrics present; Calibration Error (≤0.05) missing |

> **27 cross-cutting requirements NOT assessed:** REQ-XC-002, XC-009, XC-010, XC-012–035 (OWASP, SOLID, 12-Factor, OpenTelemetry, health endpoints, testing coverage gates, Docker Compose, SLSA Level 2, documentation standards). The cross-cutting picture is incomplete entering STAGE-4.

### 1.7 Pre-Requisite Fix Order (before Phase 7)

| Priority | ID(s) | Description | Rationale |
|----------|--------|-------------|-----------|
| P0 | REQ-P0-007 | Create `.env.example` | Unblocks Dockerfile and CI; quick win |
| P0 | REQ-P0-008 | Add `detect-secrets` to pre-commit | Security baseline; quick win |
| P0 | REQ-P0-017 | Structlog sensitive data masking | Security: prevents credential leaks in logs |
| P1 | REQ-P0-012 | Dockerfile (multi-stage, non-root) | Required for Phase 7 Streamlit deployment |
| P1 | REQ-P6-006 | DLP as pre-logging filter (not audit-only) | Architectural fix; prevents unsanitized data in Phase 7 logs |
| P1 | REQ-P6-004 + P6-005 | Presidio + Haiku detection gaps | DLP completeness before adding Phase 7 output channels |
| P2 | REQ-P0-016 | Structlog correlation ID injection | Enables traceability across Phase 7 dashboard interactions |
| P2 | REQ-P0-013 | CI: add SAST + Docker build stages | Hardens pipeline before Phase 7 increases surface area |
| P2 | REQ-P0-014 | Conventional Commits + semantic-release | Process improvement; lower urgency |
| P3 | AMBIGUOUS | Resolve REQ-P2-012 + REQ-P4-002 scope | Human decision: LLM integration in Phase 2/4 now or defer to Phase 7 |
| P3 | REQ-P6-007 | LangSmith integration | Can proceed in parallel with Phase 7; needed for Phase 8 |
| P3 | REQ-P1-005 | Map-Reduce chunking | Performance optimization; not blocking |
| P4 | REQ-P3-003 | Random Forest baseline | Academic requirement; lowest urgency |

> **CRITICAL GATING CONDITION:** Phase 7 can begin ONLY after the 5 Phase 0 MISSING items and the DLP logging gap (REQ-P6-006) are resolved, plus human scope decision on REQ-P2-012 + REQ-P4-002.

> **ORDER MISMATCH:** briefing.md Section 5 orders fixes as CRITICAL (1–4) then HIGH (5–9). STAGE-1 Section 8 orders by dependency: P0 (security baseline) → P1 (Dockerfile + DLP arch fix) → P2 (CI hardening). These differ — use STAGE-1 ordering.

### 1.8 Phase 7/8 Library Inventory (forward-looking)

| Library / Integration | Phase | Role |
|-----------------------|-------|------|
| Streamlit (≥1.40.0) | 7 | Human-in-the-loop review dashboard |
| SQLite polling | 7 | Dashboard detects escalated cases |
| LIME visualization | 7 | Per-feature ML score contribution charts |
| Email/Slack notifications | 7 | Timeout escalation cascade (4h/8h/24h) |
| Jira REST API v3 | 8 | Ticket creation with enriched schema |
| fpdf2 (≥2.7.0) | 8 | PDF audit report (ISO 27001 / SOC 2) |
| LangSmith | 8 | CoT audit trail for PDF Chain-of-Thought section |
| Redis | 7–8 | EPSS cache layer |
| FastAPI | 7–8 | REST interface / dashboard API |
| OpenTelemetry | 7–8 | Distributed tracing |

### 1.9 Stage 1 Deltas — Gaps Not Captured in MEMORY.md or briefing.md

- **GAP-01:** REQ-P6-007 (LangSmith, HIGH severity, MISSING) absent from both MEMORY.md and briefing.md Section 5
- **GAP-02:** REQ-P6-008 (dual-channel logging, MEDIUM severity, MISSING) absent from both summaries
- **GAP-03:** Full 21-item PARTIAL catalog entirely absent from MEMORY.md; only 1 of 21 items appears in briefing.md Section 5
- **GAP-04:** Full cross-cutting assessment (6 PARTIAL items) absent from both summaries
- **GAP-05:** Pre-Requisite Fix Order (P0–P4 with rationale) absent from both summaries; briefing.md ordering diverges from STAGE-1 ordering
- **GAP-06:** Severity and effort ratings for MISSING items absent from MEMORY.md

### 1.10 Notes

- **NOTE-01:** 27 cross-cutting requirements unassessed entering STAGE-4. Do not assume cross-cutting compliance.
- **NOTE-02:** `group_by_package()` data loss (REQ-P1-009) is a separate bug from LLM-not-invoked (REQ-P1-002) — both in Phase 1, require different fixes.
- **NOTE-03:** ChromaDB has two separate gaps: REQ-P2-013 (no hard LRU cap, no 4GB eviction) and REQ-XC-008 (LRU exists but no OOM trigger). Both must be addressed.
- **NOTE-04:** REQ-P3-008 (scale_pos_weight) is PARTIAL, not MISSING — small fix (one XGBoost constructor parameter).
- **NOTE-05:** Phase 5 is the strongest phase (6/7 IMPL, 86%). Only gap is HTTP 403 — include in Phase 7 FastAPI scope.
- **NOTE-06:** LangSmith is both MISSING in Phase 6 (REQ-P6-007) and in Phase 7/8 inventory — remediation in Phase 6 must be designed for Phase 8 usage.

---

## Part 2: Stage 2 Violations Fix List

### 2.1 All 7 Hexagonal Architecture Violations

**Violation #1**
- Severity: CRITICAL
- File: `application/use_cases/ingest_trivy.py:17`
- Issue: Directly imports `TrivyParser` from `siopv.adapters`, bypassing port abstraction
- Fix: Create `TrivyParserPort` in `application/ports/`; refactor `ingest_trivy.py` to accept via constructor injection; add DI factory in `infrastructure/di/`

**Violation #2**
- Severity: CRITICAL
- File: `application/use_cases/classify_risk.py:18`
- Issue: Directly imports `FeatureEngineer` from `siopv.adapters`, bypassing port abstraction
- Fix: Create `FeatureEngineerPort` in `application/ports/`; refactor `classify_risk.py` to accept via constructor injection; add DI factory in `infrastructure/di/`

**Violation #3**
- Severity: HIGH
- File: `interfaces/cli/main.py`
- Issue: CLI calls `run_pipeline()` without wiring any of the 8 DI adapter ports — all ports default to `None`. Pipeline runs structurally but performs no real enrichment, authorization, DLP, or classification. Silent failure — no crash.
- Fix: Modify `cli/main.py:process_report` to call all `get_*_port()` factories and pass 8 adapters to `run_pipeline()`.
- Note: Highest-impact single fix.

**Violation #4**
- Severity: MEDIUM
- File: `adapters/dlp/dual_layer_adapter.py`
- Issue: No explicit `DLPPort` inheritance — relies on implicit structural subtyping (PEP 544), weakening mypy enforcement
- Fix: Add explicit `DLPPort` inheritance declaration

**Violation #5**
- Severity: MEDIUM
- File: `infrastructure/di/authorization.py`
- Issue: `create_authorization_adapter()` is uncached — creates 3 separate `OpenFGAAdapter` instances with separate HTTP pools AND separate circuit breaker state machines (correctness issue, not just resource waste)
- Fix: Add `@lru_cache(maxsize=1)` (exact form) to `create_authorization_adapter()`

**Violation #6**
- Severity: MEDIUM
- File: `application/orchestration/ingest_node.py` ⚠️ (verify path — MEMORY.md says `nodes/ingest_node.py`; full report says no `nodes/` subdirectory — **glob before fixing**)
- Issue: `IngestTrivyReportUseCase()` directly instantiated inside node without DI
- Fix: Inject `IngestTrivyReportUseCase` (or its port dependencies) via node closure, matching pattern of other 4 nodes

**Violation #7**
- Severity: LOW
- File: `application/orchestration/edges.py`
- Specific target: `calculate_batch_discrepancies()` — contains adaptive threshold policy (domain logic leak)
- Fix: Extract threshold logic to a domain service (non-blocking; design smell)
- Note: Fix before Phase 7 — Phase 7 Streamlit will interact with escalation logic, compounding this leak over time

### 2.2 Layer Health Assessment

| Layer | Status | Violations |
|-------|--------|------------|
| Domain | CLEAN | 0 — 20/20 files clean, zero outward imports |
| Application/Ports | CLEAN | 0 — 6/6 pure abstract interfaces with `TYPE_CHECKING` guards |
| Application/Use Cases | ISSUES | #1, #2 (CRITICAL) |
| Application/Nodes | ISSUES | #6 (MEDIUM), #7 (LOW) |
| Adapters | MINOR | #4 (MEDIUM) |
| Infrastructure/DI | MINOR | #5 (MEDIUM) |
| Interfaces/CLI | ISSUES | #3 (HIGH) |

### 2.3 Certified Clean Areas (Stage 4 agents must NOT touch unless fix requires it)

- Domain layer purity: 20/20 files clean, zero outward imports
- Port definitions: 6/6 pure abstract interfaces
- Adapter SDK encapsulation: no external library types leak into public method signatures
- `PipelineGraphBuilder` constructor injection: accepts all 8 ports, creates closures correctly
- DI container design: factory functions return port types, use `@lru_cache`, read from `Settings`

### 2.4 Gaps / Deltas vs. MEMORY.md and briefing.md

- **Gap 1:** Line numbers for violations #1 (`ingest_trivy.py:17`) and #2 (`classify_risk.py:18`) absent from MEMORY.md — critical anchors for fix agents
- **Gap 2:** File path for Violation #6 differs between MEMORY.md (`nodes/ingest_node.py`) and full report (no `nodes/` subdir) — must be verified before fix
- **Gap 3:** Violation #7 imprecise in MEMORY.md — full report specifies `calculate_batch_discrepancies()` function name
- **Gap 4:** Violations #1, #2, #4, #5, #6, #7 entirely absent from briefing.md Section 5 (which covers only STAGE-1 issues)
- **Gap 5:** STAGE-1 Known Issues updated status not in MEMORY.md — `asyncio.run()` issue is only in `cli/main.py:87` (correct CLI usage); CLI #1 is "PARTIALLY RESOLVED" (`process_report` exists but DI not wired); hardcoded Haiku model IDs status "Outside DI scope" — needs Phase 7 review
- **Gap 6:** Layer Health Assessment table entirely absent from both MEMORY.md and briefing.md

### 2.5 Notes

- **N1:** Two systemic root causes underlie all 7 violations: (1) use cases bypass port pattern, (2) CLI wires zero DI adapters. Treat as systemic, not 3 independent bugs.
- **N2:** Violation #3 consequence is silent and invisible to test suites that mock or skip pipeline execution. Stage 4 must include integration test validating non-None adapters at runtime.
- **N3:** Violation #5 is a correctness issue — under load, 3 separate circuit breakers cause inconsistent authorization behavior (one may open while others stay closed).
- **N4:** `SanitizeVulnerabilityUseCase` orphan (STAGE-1 #2) still unexamined — STAGE-2 explicitly deferred it. Stage 4 must confirm dead code status and remove or re-integrate.
- **N5:** Violations #1 and #2 are multi-file changes — new port files in `application/ports/` AND new DI factories in `infrastructure/di/`.

---

## Part 3: Stage 3 Verified Patterns

### 3.1 Streamlit 1.x

| Fact | Correct Pattern | Wrong Pattern |
|------|----------------|---------------|
| Polling | `@st.fragment(run_every="15s")` | `time.sleep() + st.rerun()` — blocks sync thread |
| Port env var | Translate `DASHBOARD_PORT` → `STREAMLIT_SERVER_PORT` in launch script | Expecting `DASHBOARD_PORT` to be read natively |
| Auth gate (bearer) | `token = st.context.headers.get("Authorization")` | — |
| Auth gate (OIDC) | `st.login("keycloak")` + `.streamlit/secrets.toml` | — |
| Session state keys | `stage`, `current_thread_id`, `decision` tracked in `st.session_state`; call `st.rerun()` on transitions | — |
| Async bridge (cache) | `@st.cache_resource` on `get_authz_port()` with `asyncio.run(port.initialize())` | — |

**Open question:** `st.context.headers` vs `st.user` — which integrates better with Keycloak + OpenFGA? Verify `.streamlit/secrets.toml` OIDC config for Keycloak.

**Full async bridge pattern (both required together for Phase 7):**
```python
# Streamlit app module
_executor = ThreadPoolExecutor(max_workers=1)

def run_pipeline_sync(report_path, user_id, project_id):
    return _executor.submit(asyncio.run, run_pipeline(...)).result()

@st.cache_resource
def get_authz_port():
    port = get_authorization_port(get_settings())
    asyncio.run(port.initialize())
    return port
```

### 3.2 LIME (lime-ml)

| Fact | Correct Pattern | Wrong Pattern |
|------|----------------|---------------|
| Memory leak | `plt.close(fig)` after every `st.pyplot()` | `st.pyplot(fig)` without `plt.close(fig)` — memory leak |
| Constructor | `LimeTabularExplainer(training_data, mode, feature_names, class_names, categorical_features, discretize_continuous=True, random_state=42)` | — |
| Explain call | `explainer.explain_instance(row, predict_fn, labels=(1,), num_features=10, num_samples=5000)` | — |
| Docs source | lime-ml.readthedocs.io (NOT Context7 — LIME not indexed) | — |

**Open question:** `num_samples=3000` vs `num_samples=5000` — is 3000 sufficient for XGBoost with ~30 features?

### 3.3 Jira REST API v3

| Fact | Correct Pattern | Wrong Pattern |
|------|----------------|---------------|
| Description field | ADF format: `{"version": 1, "type": "doc", "content": [...]}` | `"description": "plain string"` — rejected with 400 at runtime |
| Auth | Basic `base64(JIRA_EMAIL:JIRA_API_TOKEN)` | OAuth or username+password |
| HTTP client | `httpx.AsyncClient` directly against `POST {JIRA_BASE_URL}/rest/api/3/issue` | `from jira import JIRA` or `atlassian-python-api` — sync, blocks event loop |
| CVSS → priority | ≥9.0 → Highest / 7.0–8.9 → High / 4.0–6.9 → Medium / 0.1–3.9 → Low | — |
| Docs source | developer.atlassian.com (NOT Context7) | — |

> **Integration risk:** Jira ADF rejection is silent at runtime — fails at API call time (400 response), not at construction time. Must include ADF validation in integration tests.

### 3.4 fpdf2 2.8.7

| Fact | Correct Pattern | Wrong Pattern |
|------|----------------|---------------|
| `add_font()` | `pdf.add_font(fname="path/to/font.ttf")` | `pdf.add_font()` without `fname` — error in ≥2.7 |
| Removed methods | Do not call `.open()` or `.close()` | `pdf.open()` / `pdf.close()` — AttributeError |
| Table API | `pdf.table(col_widths=(...))` as context manager | — |
| TOC | `pdf.insert_toc_placeholder(toc.render_toc, allow_extra_pages=True)` | — |
| Page count alias | `pdf.alias_nb_pages()` BEFORE any `add_page()`; use `{nb}` in footer | Calling after pages are added — count wrong/broken |
| In-memory image | `pdf.image(io.BytesIO(image_bytes))` | Writing image to temp file then loading path |
| Version pin | `fpdf2>=2.7.0` in pyproject.toml | — |

> **Integration risk:** `alias_nb_pages()` ordering must be enforced as the first call in PDF generation function — no safeguard at runtime.

### 3.5 LangGraph 0.2+

| Fact | Correct Pattern | Wrong Pattern |
|------|----------------|---------------|
| `interrupt()` requires checkpointer | Always compile with `checkpointer=AsyncSqliteSaver.from_conn_string(...)` | `graph.compile()` without checkpointer — raises at runtime |
| Resume pattern | `graph.invoke(Command(resume={...}), config=config)` | — |
| Streaming | `graph.astream(input, stream_mode=["messages","updates"])` | — |
| SQLite threading | `SqliteSaver(sqlite3.connect("db.db", check_same_thread=False))` | `sqlite3.connect("db.db")` without flag — threading error |
| State serialization | Primitive types only in PipelineState (str, int, List[str], etc.) | Storing `httpx.AsyncClient`, file handles, non-serializable objects in state |

### 3.6 Redis asyncio

| Fact | Correct Pattern | Wrong Pattern |
|------|----------------|---------------|
| Import | `import redis.asyncio as redis` | `import aioredis` — deprecated |
| Connection | `client = redis.from_url(REDIS_URL)` — pooling automatic | — |
| Set with expiry | `await client.setex(key, ttl_seconds, json.dumps(data))` | — |
| Key naming | `epss:score:{CVE_ID_UPPERCASE}` with 24h TTL | — |
| Close | `await client.aclose()` | `await client.close()` — wrong method, silently leaks connection |

> **Integration risk:** `client.close()` silently fails in newer redis-py — no error, connection leak. Needs explicit grep before Phase 8 builds.

### 3.7 OpenTelemetry (FastAPI)

| Fact | Correct Pattern | Wrong Pattern |
|------|----------------|---------------|
| HTTPXClientInstrumentor scope | Covers `httpx.AsyncClient` instances only (issue #1742) | Assuming it covers module-level `httpx.get()` calls |
| Instrumentation order (mandatory) | 1. TracerProvider setup → 2. `FastAPI()` → 3. `FastAPIInstrumentor.instrument_app(app)` | Any other order |
| Noise exclusion | `excluded_urls="healthz,readyz,metrics"` in instrumentor config | — |

**Open question:** OTel + LangSmith span correlation — W3C trace context propagation pattern not yet specified.

### 3.8 LangSmith SDK

| Fact | Correct Pattern | Wrong Pattern |
|------|----------------|---------------|
| Init | Set `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGSMITH_TRACING_V2=true`; then `Client()` | — |
| Run listing | `client.list_runs(project_name=..., filter='eq(status,"success")', is_root=True, limit=50)` | — |
| Thread tagging | `config={"metadata": {"thread_id": ...}}` at invocation | — |
| CoT extraction | Extract `llm_calls` with `name`, `start_time`, `end_time`, `inputs`, `outputs`, `total_tokens` | — |

> **LangSmith is entirely absent from MEMORY.md.** It is not indexed in Context7.

> **Integration risk:** Phase 8 PDF depends on LangSmith `list_runs`. If `LANGSMITH_TRACING_V2=true` is not set at pipeline invocation, CoT data is unavailable for PDF. Must be validated at Phase 8 startup.

### 3.9 Library Docs Source Reference

| Library | Use Context7? | Use Official Docs |
|---------|--------------|-------------------|
| Streamlit | Yes | streamlit.io |
| LangGraph | Yes | — |
| fpdf2 | Yes | — |
| LIME | ❌ Not indexed | lime-ml.readthedocs.io |
| Jira REST API v3 | ❌ Not a Python lib | developer.atlassian.com |
| Redis asyncio | ❌ Not indexed | redis-py docs |
| LangSmith | — | docs.smith.langchain.com |

### 3.10 Phase 7/8 State Field Additions

**Phase 7 — fields to add to `PipelineState`:**
- `human_decision: Literal["approve", "reject", "escalate"] | None`
- `human_review_comment: str | None`
- `hitl_requested_at: str | None`
- `hitl_resolved_at: str | None`

**Phase 8 — fields to add to `PipelineState`:**
- `jira_ticket_url: str | None`
- `pdf_report_path: str | None`
- `output_generated_at: str | None`

### 3.11 Phase 8 Topology Changes (exact steps)

1. Remove: `escalate → conditional → END` (remove `route_after_escalate` edge)
2. Add: `escalate → output` (direct edge)
3. Change: classify `"continue"` path → `output` (was `END`)
4. Add node: `output → END` + `self._graph.add_node("output", output_node)` in `_add_nodes()`

> **Note:** Report calls these "exactly 3 topology changes" but lists 4 items — the node addition (#4) may be the count discrepancy. All 4 must be applied.

### 3.12 OpenFGA Additional Findings (F-02, F-03)

- **F-02:** `getattr(settings, "openfga_authorization_model_id", None)` silently defaults to None — needs Pydantic validator to fail-fast at boot
- **F-03:** `initialize()` lifecycle not enforced by DI — must be called manually on each of the 3 instances

### 3.13 Positive Codebase Scan Findings (confirmed, do not re-audit)

- `asyncio.get_event_loop()` calls: 0 in orchestration layer
- `nest_asyncio` usage: 0 anywhere
- Graph invocation: `graph.ainvoke()` only (correct async path throughout)
- `asyncio.run()` usage: only in `cli/main.py:87` (correct CLI boundary)

### 3.14 Open Questions (from STAGE-3, unresolved)

1. `st.context.headers` vs `st.user` — which integrates better with Keycloak + OpenFGA?
2. LIME: `num_samples=3000` vs `num_samples=5000` — is 3000 sufficient for ~30 XGBoost features?
3. LangSmith filter DSL exact syntax — confirm against current SDK version
4. Redis pool size from `redis.from_url()` — verify sufficiency for concurrent graph threads
5. OTel + LangSmith span correlation — W3C trace context propagation pattern needed
6. Does `graph.py` call `initialize()` on authorization adapter at startup? (Needs grep)
7. Is `enrich_node_async` referenced in any test file? (Must grep before removing)
8. Phase 7 OpenFGA relation model — does it need `EDIT`/`ADMIN` relations beyond current `VIEW`?
9. Does `dashboard` CLI subprocess share event loop with parent? (Assessed as safe — subprocess isolation — but not fully confirmed)

---

## Part 4: Cross-cutting Recommendations

### CR-01: DLP is a systemic architectural risk, not a single bug

- STAGE-1: REQ-P6-006 (PARTIAL) — DLP node is audit-only; downstream nodes log unsanitized data
- STAGE-1: REQ-P6-004 + REQ-P6-005 — Presidio and Haiku detection gaps compound this
- STAGE-1: REQ-P6-007 (MISSING) — LangSmith integration must use sanitized data traces
- STAGE-3: LangSmith CoT → PDF dependency means unsanitized data in LangSmith will appear in audit PDFs
- **Action:** Fix DLP architectural position (P1 priority) before adding any Phase 7/8 output channels

### CR-02: CLI DI wiring failure (Violation #3) invalidates all existing pipeline tests

- STAGE-2: CLI passes `None` for all 8 adapter ports — pipeline runs without real enrichment, authorization, DLP, or classification
- STAGE-3: Graph invocation is `graph.ainvoke()` only (confirmed correct) — but the ports fed to the graph are all `None`
- **Action:** Fix Violation #3 first. Then run full integration test suite with non-None adapters to discover previously hidden failures.

### CR-03: LangSmith appears in 3 different contexts — must be planned holistically

- STAGE-1: REQ-P6-007 (MISSING, HIGH severity) — Phase 6 tracing requirement
- STAGE-1: Phase 7/8 library inventory — CoT audit trail for Phase 8 PDF
- STAGE-3: Full verified API patterns (init, list_runs, thread tagging, CoT extraction)
- **Action:** LangSmith implementation must be designed to serve both Phase 6 tracing (sanitized data) and Phase 8 PDF CoT extraction in one integration

### CR-04: OpenFGA has 3 compounding issues that interact

- STAGE-2 Violation #5: 3 uncached adapter instances → 3 separate circuit breakers → inconsistent authorization under load
- STAGE-3 F-02: `openfga_authorization_model_id` silently defaults to None → authorization silently fails
- STAGE-3 F-03: `initialize()` not enforced by DI → 3 instances, each manually initialized (or not)
- **Action:** Apply `@lru_cache(maxsize=1)` + Pydantic validator + DI lifecycle helper in one coordinated fix

### CR-05: 27 unassessed cross-cutting requirements are a blind spot entering STAGE-4

- STAGE-1 explicitly deferred REQ-XC-002, XC-009, XC-010, XC-012–035 to STAGE-2
- STAGE-2 was the hexagonal audit — it did not cover these cross-cutting requirements
- These include: OWASP mitigations, SOLID compliance, 12-Factor adherence, OpenTelemetry gates, health endpoints, testing coverage gates, Docker Compose, SLSA Level 2, documentation standards
- **Action:** STAGE-4 REMEDIATION-HARDENING must either explicitly scope these 27 items or acknowledge they remain unassessed

### CR-06: Phase 7 has 4 explicit prerequisites that must be sequenced

1. Fix Violation #5 + F-02 + F-03 (OpenFGA) — P1 from STAGE-1, prerequisite from STAGE-3
2. Implement async bridge `@st.cache_resource` + `ThreadPoolExecutor` — P4 from STAGE-3
3. Fix REQ-P6-006 (DLP architectural position) — P1 from STAGE-1
4. Create Dockerfile (REQ-P0-012) — P1 from STAGE-1
- **Action:** Block Phase 7 build until all 4 are green

### CR-07: Three library lookups must NOT use Context7 — go to official docs directly

- LIME: not indexed in Context7
- Jira REST API v3: not a Python library in Context7
- Redis asyncio: not indexed in Context7
- **Action:** All STAGE-4 builder agents must use official docs for these three (see Section 3.9)

### CR-08: Silent runtime failures are the common failure mode across all three reports

- STAGE-1 REQ-P4-002/REQ-P2-012: LLM confidence heuristic — no error, just wrong result
- STAGE-2 Violation #3: `None` adapters — no error, just no-op pipeline
- STAGE-2 Violation #5: 3 circuit breakers — no error, inconsistent authorization
- STAGE-3 OpenFGA F-02: `None` model ID — no error at boot, silent auth failure at runtime
- STAGE-3 Redis `close()` vs `aclose()`: no error, connection leak
- STAGE-3 Jira ADF: 400 at call time, not construction time
- **Action:** All STAGE-4 integration tests must validate actual behavior (not just absence of exceptions). Each adapter port must have an integration test that confirms real behavior, not `None`-or-pass.
