# STAGE 1 — Final Report: SIOPV Phases 0–6 Gap Analysis

> Date: 2026-03-11 | Audit: Pre-Phase 7 | Sources: R1 (Spec Extractor) + R2 (Round 2 Aggregated Gap Analysis)

---

## 1. Executive Summary

This report consolidates the STAGE-1 audit of SIOPV Phases 0–6, comparing the implemented codebase against the 112 requirements extracted from `SIOPV_Propuesta_Tecnica_v2.txt`. Of these, 77 phase-specific requirements and 8 cross-cutting requirements were assessed in depth.

**Key Numbers:**
- **112 requirements** extracted (77 phase-specific + 35 cross-cutting)
- **45 (58%)** fully implemented
- **21 (27%)** partially implemented
- **9 (12%)** missing entirely
- **2 (3%)** ambiguous scope (LLM integration — requires human decision)
- **8 cross-cutting** requirements assessed: 2 IMPL, 6 partial

**Overall Health:** The project has a solid foundation — hexagonal architecture, OpenFGA authorization, DLP pipeline, ML classification with XGBoost, and LangGraph orchestration are all functional. Phase 5 (Authorization) is the strongest at 86% full implementation. However, three systemic issues threaten Phase 7 readiness:

1. **LLM Integration Gap (CRITICAL):** Phases 1, 2, and 4 all configure Claude model IDs in settings but never invoke them. The `adapters/llm/` directory is empty. Only Phase 6 (DLP) actually calls Claude Haiku. This is the single largest architectural gap — the project is "LLM-ready" in config but "LLM-absent" in execution for 3 of 4 LLM-dependent phases.

2. **Phase 0 Infrastructure Debt (HIGH):** 5 of 9 MISSING items are foundational setup gaps — no Dockerfile, no `detect-secrets`, no `.env.example`, no conventional commits, no structlog masking. Adding Phase 7 surface area without resolving these compounds technical debt.

3. **DLP Architecture Mismatch (HIGH):** The spec requires DLP as a pre-logging filter for ALL output (REQ-P6-006), but the implementation is an audit-only pass within the pipeline. Downstream nodes log unsanitized data. This is an architectural fix, not a code patch.

**Pre-Phase 7 Verdict:** Phase 7 can begin only after the 5 Phase 0 MISSING items and the DLP logging gap are resolved. The LLM integration question (items REQ-P2-012, REQ-P4-002) requires a human scope decision — if LLM calls are deferred to Phase 7, that phase's scope expands significantly. The 21 PARTIAL items represent polish and hardening work that can proceed in parallel with Phase 7 development.

---

## 2. Requirements Catalog Summary

| Phase | Total | IMPL | PARTIAL | MISSING | AMBIGUOUS |
|-------|-------|------|---------|---------|-----------|
| 0 — Setup | 17 | 7 | 5 | 5 | 0 |
| 1 — Ingesta | 9 | 5 | 3 | 1 | 0 |
| 2 — Enriquecimiento | 13 | 9 | 3 | 0 | 1 |
| 3 — Clasificación ML | 12 | 9 | 2 | 1 | 0 |
| 4 — Orquestación | 11 | 6 | 4 | 0 | 1 |
| 5 — Autorización | 7 | 6 | 1 | 0 | 0 |
| 6 — Privacidad/DLP | 8 | 3 | 3 | 2 | 0 |
| **Phase Totals** | **77** | **45** | **21** | **9** | **2** |
| Cross-Cutting (8 assessed) | 8 | 2 | 6 | 0 | 0 |

> 35 cross-cutting requirements defined in R1; 8 were assessed in-depth during R2 gap analysis. The remaining 27 (REQ-XC-002, XC-009, XC-010, XC-012–035) require STAGE-2 deep-dive.

---

## 3. MISSING Requirements (9 total)

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

**Severity rationale:** Items blocking security posture (detect-secrets, structlog masking, DLP logging) or deployment readiness (Dockerfile, .env.example) are HIGH. Academic requirements (Random Forest comparator) are LOW.

---

## 4. PARTIAL Requirements (21 total)

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
| 21 | REQ-P4-009 | 4 | *(note: 6/8 nodes is expected pre-Phase 7)* | Phase 7/8 nodes will complete this |

---

## 5. AMBIGUOUS Requirements (2 items — scope unclear)

| ID | Description | Issue |
|----|-------------|-------|
| REQ-P2-012 | Claude Sonnet evaluates document relevance (score 0–1) | Currently a heuristic formula (`_calculate_relevance()`). Model ID configured but unused. May be a Phase 7 concern. |
| REQ-P4-002 | Claude Sonnet 4.5 for state orchestration | `_estimate_llm_confidence()` is pure math, not an LLM call. Flagged in prior audit as CRITICAL #3. |

**Human decision required:** Both items share the same underlying gap — Claude Sonnet integration. If LLM calls belong in Phases 2/4, they are MISSING (not AMBIGUOUS) and the gap count rises to 11. If deferred to Phase 7, Phase 7 scope expands to include LLM adapter implementation.

---

## 6. Cross-Cutting Assessment (8 assessed of 35 defined)

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

**Remaining 27 cross-cutting requirements** (REQ-XC-002, XC-009, XC-010, XC-012–035) were not assessed in Round 2 and require STAGE-2 deep-dive. These include: OWASP mitigations, SOLID compliance, 12-Factor adherence, OpenTelemetry, health endpoints, testing coverage gates, Docker Compose, SLSA Level 2, and documentation standards.

---

## 7. Forward-Looking Phase 7/8 Library Inventory

These libraries are **planned future work** extracted from the spec. Not assessed for implementation status.

| Library / Integration | Phase | Role |
|-----------------------|-------|------|
| Streamlit (≥1.40.0) | 7 | Human-in-the-loop review dashboard |
| SQLite polling | 7 | Dashboard detects escalated cases (not websockets) |
| LIME visualization | 7 | Per-feature ML score contribution charts |
| Email/Slack notifications | 7 | Timeout escalation cascade (4h/8h/24h) |
| Jira REST API v3 | 8 | Ticket creation with enriched schema |
| fpdf2 (≥2.7.0) | 8 | PDF audit report (ISO 27001 / SOC 2) |
| LangSmith | 8 | CoT audit trail for PDF Chain-of-Thought section |
| Redis | 7–8 | EPSS cache layer (optional local, required full stack) |
| FastAPI | 7–8 | REST interface / dashboard API |
| OpenTelemetry | 7–8 | Distributed tracing (intensifies in production) |

---

## 8. Pre-Requisite Fix Order (before Phase 7 starts)

Ordered by severity and dependency chain. Items higher in the list unblock items below.

| Priority | ID(s) | Description | Rationale |
|----------|--------|-------------|-----------|
| **P0** | REQ-P0-007 | Create `.env.example` template | Unblocks Dockerfile and CI; quick win |
| **P0** | REQ-P0-008 | Add `detect-secrets` to pre-commit | Security baseline; quick win |
| **P0** | REQ-P0-017 | Structlog sensitive data masking processor | Security: prevents credential leaks in logs |
| **P1** | REQ-P0-012 | Dockerfile (multi-stage, non-root) | Required for Phase 7 Streamlit deployment |
| **P1** | REQ-P6-006 | DLP as pre-logging filter (not audit-only) | Architectural fix; prevents unsanitized data in Phase 7 logs |
| **P1** | REQ-P6-004 + P6-005 | Presidio + Haiku detection gaps | DLP completeness before adding Phase 7 output channels |
| **P2** | REQ-P0-016 | Structlog correlation ID injection | Enables traceability across Phase 7 dashboard interactions |
| **P2** | REQ-P0-013 | CI: add SAST + Docker build stages | Hardens pipeline before Phase 7 increases surface area |
| **P2** | REQ-P0-014 | Conventional Commits + semantic-release | Process improvement; lower urgency |
| **P3** | AMBIGUOUS decision | Resolve REQ-P2-012 + REQ-P4-002 scope | Human decision: LLM integration in Phase 2/4 now or defer to Phase 7 |
| **P3** | REQ-P6-007 | LangSmith integration | Can proceed in parallel with Phase 7; needed for Phase 8 |
| **P3** | REQ-P1-005 | Map-Reduce chunking | Performance optimization; not blocking |
| **P4** | REQ-P3-003 | Random Forest baseline | Academic requirement; lowest urgency |

---

*End of STAGE-1 Final Report — 112 requirements cataloged, 77+8 assessed, 9 MISSING, 21 PARTIAL, 2 AMBIGUOUS.*
