# R2 — Round 2 Aggregated Gap Analysis (Phases 0–6)

> Aggregator: round2-aggregator | Date: 2026-03-11
> Sources: 5 individual R2 gap reports (phases-0-1, phase-2, phase-3, phase-4, phases-5-6)

---

## 1. Consolidated Gap Table by Phase

| Phase | IMPL | PARTIAL | MISSING | AMBIGUOUS | Total |
|-------|------|---------|---------|-----------|-------|
| 0 — Setup | 7 | 5 | 5 | 0 | 17 |
| 1 — Ingesta | 5 | 3 | 1 | 0 | 9 |
| 2 — Enriquecimiento | 9 | 3 | 0 | 1 | 13 |
| 3 — Clasificación ML | 9 | 2 | 1 | 0 | 12 |
| 4 — Orquestación | 6 | 4 | 0 | 1 | 11 |
| 5 — Autorización | 6 | 1 | 0 | 0 | 7 |
| 6 — Privacidad/DLP | 3 | 3 | 2 | 0 | 8 |
| **TOTAL** | **45** | **21** | **9** | **2** | **77** |

**Implementation rate:** 58% fully implemented, 27% partial, 12% missing, 3% ambiguous.

> **Note (Phase 3):** The individual report summary stated 8/2/2 but individual requirement assessments yield 9 IMPL / 2 PARTIAL / 1 MISSING. This aggregation uses the corrected count from line-item review.

---

## 2. AMBIGUOUS Requirements (scope unclear — excluded from MISSING count)

| ID | Description | Issue |
|----|-------------|-------|
| REQ-P2-012 | Claude Sonnet evaluates document relevance (score 0–1) | Sonnet LLM integration may be a Phase 7 concern. Currently a heuristic formula (`_calculate_relevance()`). Model ID configured but unused. |
| REQ-P4-002 | Claude Sonnet 4.5 for state orchestration | Same LLM integration gap. `_estimate_llm_confidence()` is pure math. Flagged in prior audit as CRITICAL #3. |

**Rationale:** Both requirements involve the same underlying gap (Claude Sonnet integration). Whether this belongs in Phase 2/4 scope or is deferred to Phase 7 (where the LLM adapter would be wired) is a design decision requiring human clarification.

---

## 3. All MISSING Requirements (9 total)

| # | ID | Phase | Description | Effort |
|---|-----|-------|-------------|--------|
| 1 | REQ-P0-007 | 0 | `.env.example` template | Quick |
| 2 | REQ-P0-008 | 0 | `detect-secrets` in pre-commit | Quick |
| 3 | REQ-P0-012 | 0 | Dockerfile (multi-stage, python:3.12-slim, non-root UID 1000) | Significant |
| 4 | REQ-P0-014 | 0 | Conventional Commits + semantic-release config | Moderate |
| 5 | REQ-P0-017 | 0 | Structlog sensitive data masking processor | Moderate |
| 6 | REQ-P1-005 | 1 | Map-Reduce chunking (50 vulns/chunk) | Moderate |
| 7 | REQ-P3-003 | 3 | Random Forest baseline/ensemble comparator | High |
| 8 | REQ-P6-007 | 6 | LangSmith integration (tracing with sanitized data) | High |
| 9 | REQ-P6-008 | 6 | Dual-channel logging (sanitized public + restricted unsanitized) | Moderate |

**Phase 0 dominates:** 5 of 9 MISSING items are infrastructure/setup gaps.

---

## 4. All PARTIAL Requirements (21 total)

### Phase 0 (5 PARTIAL)

| ID | Description | Gap |
|----|-------------|-----|
| REQ-P0-003 | CISA KEV dataset download | No automation script; dataset assumed pre-existing |
| REQ-P0-009 | Pre-commit hooks | Missing `detect-secrets`, `trailing-whitespace` |
| REQ-P0-013 | CI pipeline | Missing Security (SAST) and Build (Docker) stages |
| REQ-P0-015 | GitHub Flow | Uses `develop` branch (not GitHub Flow); branch protection unverifiable |
| REQ-P0-016 | Structlog JSON + correlation IDs | Missing `run_id`/`thread_id` correlation ID injection |

### Phase 1 (3 PARTIAL)

| ID | Description | Gap |
|----|-------------|-----|
| REQ-P1-002 | Claude Haiku for Phase 1 | Model configured but ingestion uses no LLM at all |
| REQ-P1-009 | Batch by package before LLM | `group_by_package()` computed but dropped at node boundary |
| REQ-P0-003 | *(see Phase 0)* | *(cross-ref only)* |

### Phase 2 (3 PARTIAL)

| ID | Description | Gap |
|----|-------------|-----|
| REQ-P2-001 | Module name `Dynamic_RAG_Researcher` | Functional equivalent exists but no spec-matching name |
| REQ-P2-002 | Claude Sonnet model for Phase 2 | Configured in settings but never invoked |
| REQ-P2-013 | ChromaDB: 1000-query LRU + 4GB eviction | No hard 1000-query cap; no on-disk 4GB eviction logic |

### Phase 3 (2 PARTIAL)

| ID | Description | Gap |
|----|-------------|-----|
| REQ-P3-006 | EPSS historical data correlation | Uses snapshot EPSS scores, not historical time-series |
| REQ-P3-008 | SMOTE + class weighting in loss | SMOTE implemented; `scale_pos_weight` not set in XGBoost |

### Phase 4 (4 PARTIAL)

| ID | Description | Gap |
|----|-------------|-----|
| REQ-P4-004 | Adaptive threshold (not fixed) | `check_any_escalation_needed()` uses fixed `base_threshold` instead of adaptive |
| REQ-P4-006 | Persistent discrepancy history + weekly recalc | In-memory only; no persistence; recalculated per-batch not weekly |
| REQ-P4-008 | Checkpoint resumption + post-mortem audit | Checkpointing works but no `resume_pipeline()` API; no audit query |
| REQ-P4-009 | 8-phase pipeline as nodes | 6/8 nodes wired (Phase 7/8 nodes pending — expected) |

### Phase 5 (1 PARTIAL)

| ID | Description | Gap |
|----|-------------|-----|
| REQ-P5-007 | 403 Forbidden + audit log on denial | Audit log ✅; no HTTP 403 (pipeline-level denial only; acceptable until FastAPI layer) |

### Phase 6 (3 PARTIAL)

| ID | Description | Gap |
|----|-------------|-----|
| REQ-P6-004 | Presidio entity detection | Missing recognizers for internal URLs and filesystem paths |
| REQ-P6-005 | Haiku semantic detection categories | Prompts miss: project names, client names, trade secrets, architecture info |
| REQ-P6-006 | DLP before all logging | DLP node is audit-only; downstream nodes log unsanitized data |

---

## 5. Cross-Cutting Requirements (assessed in phase context, not double-counted)

| ID | Description | Status | Phase Context |
|----|-------------|--------|---------------|
| REQ-XC-001 | Circuit breaker per API | IMPL | Phase 2 |
| REQ-XC-003 | NVD fallback: 24h local cache | ⚠️ Partial | Phase 2 — in-memory only, no 24h TTL |
| REQ-XC-004 | GitHub fallback: degrade to no-auth | ⚠️ Partial | Phase 2 — not explicitly implemented |
| REQ-XC-005 | EPSS fallback: stale_data flag | ⚠️ Partial | Phase 2 — not implemented |
| REQ-XC-006 | Tavily fallback: omit OSINT | IMPL | Phase 2 |
| REQ-XC-007 | ML fallback → CVSS+EPSS heuristic | ⚠️ Partial | Phase 3 — uses severity map, no `degraded_confidence` flag |
| REQ-XC-008 | ChromaDB OOM: evict LRU | ⚠️ Partial | Phase 2 — LRU exists, no OOM detection |
| REQ-XC-011 | ML quality gates (5 metrics) | ⚠️ Partial | Phase 3 — 4/5 metrics; Calibration Error missing |

---

## 6. Cross-Phase Patterns and Observations

### Pattern 1: LLM Integration Gap (systemic)
Phases 1, 2, and 4 all configure Claude model IDs in `settings.py` but **never invoke them**. The `adapters/llm/` directory is empty. Only Phase 6 (DLP) actually calls Claude Haiku. This is the single largest architectural gap — the project is "LLM-ready" in config but "LLM-absent" in execution for 3 of 4 phases that specify a model.

### Pattern 2: Phase 0 Infrastructure Debt
5 of 9 MISSING items are Phase 0 setup/DevOps gaps (Dockerfile, detect-secrets, .env.example, conventional commits, structlog masking). These are foundational and should be resolved before Phase 7 adds more surface area.

### Pattern 3: Persistence Gaps
Multiple components use in-memory-only storage where the spec requires persistence:
- `DiscrepancyHistory` (Phase 4) — lost between pipeline runs
- NVD cache (XC-003) — no 24h TTL
- ChromaDB eviction (Phase 2) — no disk monitoring

### Pattern 4: Spec Naming vs. Implementation Naming
Phases 1–4 all have module naming deviations (e.g., `IngestTrivyReportUseCase` vs. `Ingestion_Engine`). These are cosmetic and follow Python conventions — low priority.

### Pattern 5: Phase 5 is the Strongest
Authorization (OpenFGA/ReBAC) is the most complete phase: 6/7 IMPL, 1 PARTIAL (HTTP 403 deferred to FastAPI layer). No MISSING items.

### Pattern 6: DLP Scope Mismatch
Phase 6 DLP is positioned as an audit pass within the pipeline but the spec requires it as a pre-logging filter for ALL output. This is an architectural mismatch, not a simple code fix.

---

## 7. Summary Statistics

- **77 requirements** assessed across Phases 0–6
- **45 (58%)** fully implemented
- **21 (27%)** partially implemented
- **9 (12%)** missing entirely
- **2 (3%)** ambiguous scope (Claude Sonnet LLM integration — REQ-P2-012, REQ-P4-002)
- **8 cross-cutting** requirements assessed (2 IMPL, 6 partial/warning)

**Top 3 remediation priorities:**
1. LLM adapter integration (REQ-P2-012 / REQ-P4-002 — if in scope for pre-Phase 7)
2. Phase 0 infrastructure debt (5 MISSING items — foundational)
3. DLP architecture alignment (REQ-P6-006 — audit-only vs. pre-logging filter)

---

*End of Round 2 aggregated report — 77 phase requirements + 8 cross-cutting assessed.*
