# Truth-07: Memory System for SIOPV
**Generated:** 2026-03-13
**Authority:** Round 1 §2 (Memory System) + Round 3 §7 (User-Level Changes) + truth-00 §2 (File-to-Truth Mapping)
**Scope:** `~/.claude/projects/-Users-bruno-siopv/memory/` — SIOPV project memory design

---

## 1. Memory System Architecture for SIOPV

### How Memory Works (Round 1 §2)

| System | Scope | Loaded | Limit |
|--------|-------|--------|-------|
| `MEMORY.md` | Per git worktree path | Every session start | **First 200 lines — hard cut** |
| Topic files | Same directory as MEMORY.md | On demand (when explicitly read) | No limit |
| Subagent memory | `project` scope → `.claude/agent-memory/<name>/` | Per-agent per-session | No limit |

**Key rule:** MEMORY.md is an *index only*. Detail lives in topic files. MEMORY.md pointers tell Claude where to look.

### SIOPV Memory Location

```
~/.claude/projects/-Users-bruno-siopv/memory/
├── MEMORY.md                          ← index, loaded every session (< 200 lines)
├── siopv-stage-results.md             ← Stage 1–4 audit findings (topic file)
├── siopv-architecture.md              ← Key file paths + architecture notes (topic file)
├── siopv-violations.md                ← Stage 2 hex violations + Stage 3 library facts (topic file)
└── siopv-phase7-8-context.md          ← Phase 7/8 readiness + open questions (topic file)
```

**Note:** This is distinct from the meta-project memory at `~/.claude/projects/-Users-bruno-sec-llm-workbench/memory/`.
The SIOPV project memory is populated when Claude Code is run from `~/siopv/`.

---

## 2. MEMORY.md Template

**Target:** `~/.claude/projects/-Users-bruno-siopv/memory/MEMORY.md`
**Constraint:** Must stay well under 150 lines (buffer below 200-line session-load limit)

```markdown
# SIOPV Project Memory

## Identity
- **Project:** SIOPV — AI Security Vulnerability Intelligence Platform
- **Path:** `~/siopv/`
- **Stack:** Python 3.11, FastAPI, LangGraph, OpenFGA, Presidio, XGBoost, Streamlit, Jira, fpdf2
- **State file:** `projects/siopv.json`

## Phase Status
| Phase | Name | Status |
|-------|------|--------|
| 0 | Setup | ✅ Completed |
| 1 | Ingesta y Preprocesamiento | ✅ Completed |
| 2 | Enriquecimiento (CRAG / RAG) | ✅ Completed |
| 3 | Clasificación ML (XGBoost) | ✅ Completed |
| 4 | Orquestación (LangGraph) | ✅ Completed |
| 5 | Autorización (OpenFGA) | ✅ Completed |
| 6 | Privacidad (DLP / Presidio) | ✅ Completed |
| 7 | Human-in-the-Loop (Streamlit) | ⏳ PENDING |
| 8 | Output (Jira + PDF) | ⏳ PENDING |

## Metrics (as of 2026-03-05)
- Tests: 1,404 passed, 12 skipped
- Coverage: 83% (floor — must not regress)
- mypy: 0 errors | ruff: 0 errors

## Pre-Phase 7 Blockers (must fix before Phase 7 starts)
1. Stage 2 hex violation #1 CRITICAL: `ingest_trivy.py:17` imports `TrivyParser` from adapters
2. Stage 2 hex violation #2 CRITICAL: `classify_risk.py:18` imports `FeatureEngineer` from adapters
3. Stage 2 hex violation #3 HIGH: CLI `main.py` — all 8 adapter ports = None, DI never wired
4. `@lru_cache` missing on shared OpenFGA adapter factory (P1 hardening)
5. Remove dead `enrich_node_async` (P2 hardening)
6. Authorization initialization lifecycle helper (P3 — Phase 7 prerequisite)
7. `st.cache_resource` + `ThreadPoolExecutor` async bridge (P4 — Phase 7 prerequisite)

## Key File Paths
| Component | Path |
|-----------|------|
| Graph | `src/siopv/application/orchestration/graph.py` |
| State | `src/siopv/application/orchestration/state.py` |
| CLI | `src/siopv/interfaces/cli/main.py` |
| Settings | `src/siopv/infrastructure/config/settings.py` |
| DI container | `src/siopv/infrastructure/di/__init__.py` |
| Constants | `src/siopv/domain/constants.py` |

## Topic Files (read on demand)
- [Stage Audit Results](siopv-stage-results.md) — Stage 1–4 findings, requirements summary
- [Architecture Notes](siopv-architecture.md) — graph flow, DI pattern, violation details
- [Violations + Library Facts](siopv-violations.md) — Stage 2 hex violations + Stage 3 verified facts
- [Phase 7/8 Context](siopv-phase7-8-context.md) — readiness checklist, open questions, integration risks

## Claude Config Status (as of 2026-03-13)
- `siopv/.claude/` built in Stage 4.2 (pending)
- Pre-Phase-7 remediation in Stage 4.2 (pending)
- Audit stages: 1 ✅ 2 ✅ 3 ✅ 3.5 ✅ 4.1 ✅ 4.2 ⏳
```

**Line count:** ~78 lines — well within 200-line limit.

---

## 3. Recommended Topic Files

### 3.1 `siopv-stage-results.md`
**Stores:** Stage 1–4 audit findings, requirements implementation summary, stage status table.

```markdown
---
name: siopv-stage-results
description: SIOPV Stage 1-4 audit findings — requirements status, PARTIAL/MISSING items, stage completion
type: project
---

## Requirements Summary (Stage 1 — 77 assessed)
- IMPLEMENTED: 45 (58%) | PARTIAL: 21 (27%) | MISSING: 9 (12%) | AMBIGUOUS: 2 (3%)

## Scope Rule
Phase 7/8 dependencies appearing as MISSING in Phases 0–6 are EXPECTED-MISSING.
LLM integration (REQ-P2-012, REQ-P4-002) deferred to Phase 7 — modifies Phases 2 and 4 by design.

## Top MISSING Items (Phases 0–6)
1. No Dockerfile | 2. No detect-secrets pre-commit hook | 3. No .env.example
4. No Conventional Commits + semantic-release | 5. No structlog sensitive data masking
6. No Map-Reduce chunking (Ph1) | 7. No Random Forest baseline (Ph3)
8. XGBoost scale_pos_weight (Ph3 — PARTIAL, not fully absent) | 9. DLP arch mismatch (Ph6)

## Stage Status
| Stage | Description | Status |
|-------|-------------|--------|
| STAGE-1 | Phases 0–6 Discovery | ✅ 2026-03-11 |
| STAGE-2 | Hexagonal Quality Audit | ✅ 2026-03-11 |
| STAGE-3 | SOTA Research & Deep Scan | ✅ 2026-03-11 |
| STAGE-3.5 | Final Reports Aggregation | ✅ 2026-03-12 |
| STAGE-4.1 | Truth Document Research | ✅ 2026-03-13 |
| STAGE-4.2 | Implementation | ⏳ PENDING |

Full reports: `/Users/bruno/siopv/AuditPrePhase7-11mar26/`
Stage 4 input brief: `stage3.5/stage3.5-final-reports-summarizer-n-aggregator-for-stage4-input-brief.md`
```

### 3.2 `siopv-architecture.md`
**Stores:** Graph flow, DI pattern, graph state fields, Docker services.

```markdown
---
name: siopv-architecture
description: SIOPV architecture — graph flow, DI pattern, LangGraph state, key design decisions
type: project
---

## Graph Flow
START → authorize → ingest → dlp → enrich → classify → [escalate] → END

## Design Decisions
- DLP uses `dlp_node` (NOT `SanitizeVulnerabilityUseCase`) — use case is orphaned
- LangGraph uses TypedDict state (not Pydantic) — by design, backward-compatible
- Checkpointing: SQLite (`siopv_checkpoints.db`)
- DI pattern: `lru_cache` factory functions in `infrastructure/di/`
- `asyncio.run()`: only at `cli/main.py:87` — correct CLI boundary
- Docker: `docker-compose.yml` runs OpenFGA + Keycloak + Postgres

## Phase 7 State Additions (not yet implemented)
- `human_decision: str | None` — escalation outcome
- `escalation_reason: str | None` — why escalation triggered
- `reviewer_id: str | None` — Streamlit reviewer identity

## Phase 8 Topology Changes (exactly 3 in `graph.py._add_edges()`)
- Add `output` node after `classify`
- Wire `output → jira_create` (conditional on severity)
- Wire `output → pdf_generate`
```

### 3.3 `siopv-violations.md`
**Stores:** Stage 2 hex violations with line refs, Stage 3 verified library facts.

```markdown
---
name: siopv-violations
description: Stage 2 hexagonal violations (#1-7) + Stage 3 verified library facts for Phase 7/8
type: project
---

## Stage 2 Hex Violations
| # | Severity | File | Line | Issue |
|---|----------|------|------|-------|
| 1 | CRITICAL | `application/use_cases/ingest_trivy.py` | :17 | Imports TrivyParser from adapters |
| 2 | CRITICAL | `application/use_cases/classify_risk.py` | :18 | Imports FeatureEngineer from adapters |
| 3 | HIGH | `interfaces/cli/main.py` | all | 8 adapter ports = None, DI never wired |
| 4 | MEDIUM | `adapters/dlp/dual_layer_adapter.py` | — | No explicit DLPPort inheritance |
| 5 | MEDIUM | `infrastructure/di/authorization.py` | — | 3 uncached OpenFGAAdapter instances |
| 6 | MEDIUM | `application/orchestration/nodes/ingest_node.py` | — | Directly instantiates use case |
| 7 | LOW | `application/orchestration/edges.py` | — | Domain logic in `calculate_batch_discrepancies()` |

## Stage 3 Verified Library Facts (critical — training data is stale)
| Library | Verified Fact |
|---------|--------------|
| Streamlit | `@st.fragment(run_every="15s")` — not sleep+rerun |
| Streamlit | Port via `STREAMLIT_SERVER_PORT` env var |
| Streamlit | Requires `st.cache_resource` + `ThreadPoolExecutor` for async bridge |
| Jira v3 | Description MUST be ADF format — plain strings silently rejected |
| Jira client | Use `httpx.AsyncClient` — sync libs block event loop |
| fpdf2 | `fname` required in `add_font()` since 2.7 — breaking change |
| LangGraph | `interrupt()` requires checkpointer at compile time |
| LangGraph | Main thread only — never call `graph.invoke()` from thread pool |
| Redis | Use `redis.asyncio` — aioredis merged into redis-py ≥4.2 |
| Redis | Always `await client.aclose()` on shutdown |
| OTel | `HTTPXClientInstrumentor` does NOT cover module-level `httpx.get()` — instrument before first use |
| LIME | Always `plt.close(fig)` after `st.pyplot()` — memory leak |
| LangSmith | Set `LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY` for LangGraph tracing |

## Context7 Coverage Warning
Context7 has NO coverage for: LIME, Jira v3, Redis. Use official docs directly for these.
```

### 3.4 `siopv-phase7-8-context.md`
**Stores:** Phase 7/8 readiness checklist, open questions, integration risks.

```markdown
---
name: siopv-phase7-8-context
description: Phase 7/8 readiness, open questions, integration risks, and implementation checklist
type: project
---

## Phase 7 Prerequisites (must be done first)
- [ ] P3: Authorization initialization lifecycle helper (OpenFGA)
- [ ] P4: `st.cache_resource` + `ThreadPoolExecutor` async bridge
- [ ] Stage 2 violations #1, #2, #3 remediated

## Phase 8 Prerequisites
- Phase 7 complete + all topology changes in graph tested

## Open Questions (from Stage 3.5 — Stage 4 must address)
1. Should LangSmith tracing be gated behind a feature flag?
2. Redis key convention for SIOPV scan results — TTL strategy?
3. Jira ADF schema version to target (v1 vs v2)?
4. fpdf2 font file bundling strategy (embed vs system lookup)?
5. LIME sample count for Phase 7 explainability panel?

## Integration Risks
| Risk | Mitigation |
|------|-----------|
| LIME memory leak in Streamlit | `plt.close(fig)` after every `st.pyplot()` |
| LangSmith tracing adds latency | Gate with `LANGCHAIN_TRACING_V2` env var |
| fpdf2 font ordering | Load fonts before first `add_page()` |
| Redis `aclose()` on restart | Register in FastAPI `lifespan` shutdown handler |
| Jira ADF silent rejection | Test with Jira sandbox before Phase 8 integration |
```

---

## 4. Current MEMORY.md Truncation Fix

**Problem:** `~/.claude/projects/-Users-bruno-sec-llm-workbench/memory/MEMORY.md` is 217 lines.
Lines 201–217 (Hook Classification section) are silently cut every session — live data loss.

**Exact content currently truncated (lines 201–217):**
```
### Hook Classification (9 total)
| Classification | Count | Notes |
| ADAPTABLE | 4 | pre-commit.sh, verify-best-practices.sh, post-code.sh, pre-git-commit.sh |
| META-ONLY | 5 | pre-write.sh, test-framework.sh, pre-compact.sh, session-start.sh, session-end.sh |
| SIOPV-APPLICABLE | 0 | All hooks need path adaptation |

### P1 Agents for SIOPV (deploy first)
- code-implementer, async-safety-auditor, integration-tracer, hallucination-detector

### SIOPV Needs New Hooks From Scratch
- session-start.sh, pre-compact.sh, session-end.sh
```

**Fix (two steps):**

**Step 1 — Create topic file** `~/.claude/projects/-Users-bruno-sec-llm-workbench/memory/siopv-hooks-stage4.md`:

```markdown
---
name: siopv-hooks-stage4
description: Stage 4 hook and agent classification for SIOPV reuse — from pre-task inventory
type: project
---

Catalog: `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4/2026-03-12-11.56.25-stage4-pre-task-inventory...`

## Agent Classification (23 total)
| Classification | Count | Notes |
|----------------|-------|-------|
| SIOPV-APPLICABLE | 16 | Ready to use as-is |
| ADAPTABLE | 4 | xai-explainer, researcher-1, researcher-2, researcher-3 |
| META-ONLY | 3 | final-report-agent, report-summarizer, vulnerability-researcher — discard |

## Hook Classification (9 total)
| Classification | Count | Notes |
|----------------|-------|-------|
| ADAPTABLE | 4 | pre-commit.sh, verify-best-practices.sh, post-code.sh, pre-git-commit.sh |
| META-ONLY | 5 | pre-write.sh, test-framework.sh, pre-compact.sh, session-start.sh, session-end.sh |
| SIOPV-APPLICABLE | 0 | All hooks need path adaptation |

## P1 Agents for SIOPV (deploy first)
- `code-implementer` — primary builder
- `async-safety-auditor` — Issue #7 + Phase 7 event loop safety
- `integration-tracer` — Issue #1 + Issue #4 (parameter dropping)
- `hallucination-detector` — Phase 7/8 library API verification

## SIOPV Hooks — Build From Scratch
- `session-start.sh` — load SIOPV briefing.md
- `pre-compact.sh` — update SIOPV briefing.md timestamp
- `session-end.sh` — log session exit to compaction-log.md
```

**Step 2 — Trim current MEMORY.md:** Remove lines 201–217 (the Hook Classification section).
Add one pointer line at the end of the `## STAGE-4 Pre-Task` section:

```markdown
Full classification details → [siopv-hooks-stage4.md](siopv-hooks-stage4.md)
```

**Result:** MEMORY.md drops from 217 → ~202 lines. With the Hook Classification section removed and replaced by one pointer line: ~192 lines — safely under 200.

**Implementation slot:** truth-00 Batch 7, item #50–51.

---

## 5. Auto-Memory Configuration

### For SIOPV Project

**Should auto-memory be enabled?** Yes — default behavior is correct. No special configuration needed.

| Setting | Value | Where |
|---------|-------|-------|
| `autoMemoryEnabled` | `true` (default, v2.1.59+) | Not needed unless disabling |
| `autoMemoryDirectory` | Not set — use default path | **Cannot go in `.claude/settings.json`** — user/local/policy scope only |

**Why not configure `autoMemoryDirectory`?**
Round 1 §2 confirms: `autoMemoryDirectory` is user/local/policy scope only. Setting it in `siopv/.claude/settings.json` has no effect. The default path (`~/.claude/projects/<encoded-path>/memory/`) is correct and requires no override.

### Memory Types to Use for SIOPV

| Type | Use for |
|------|---------|
| `project` | Phase status, audit findings, stage results, architecture decisions |
| `feedback` | When user corrects Claude's approach during SIOPV sessions |
| `reference` | Pointers to audit reports in `AuditPrePhase7-11mar26/` |
| `user` | Not applicable at project level — user preferences go in global memory |

### Subagent Memory (for SIOPV agents)

Agents that need persistent cross-session memory (e.g., `hex-arch-remediator` tracking violation fix progress):

```yaml
# In agent frontmatter (.claude/agents/hex-arch-remediator.md)
memory: project
```

This writes to `.claude/agent-memory/hex-arch-remediator/` within the SIOPV repo.
Appropriate for: tracking which of the 7 violations have been fixed across sessions.

---

## Summary

| Action | File | Priority |
|--------|------|----------|
| CREATE | `~/.claude/projects/-Users-bruno-siopv/memory/MEMORY.md` | Stage 4.2 Batch 7 |
| CREATE | `~/.claude/projects/-Users-bruno-siopv/memory/siopv-stage-results.md` | Stage 4.2 Batch 7 |
| CREATE | `~/.claude/projects/-Users-bruno-siopv/memory/siopv-architecture.md` | Stage 4.2 Batch 7 |
| CREATE | `~/.claude/projects/-Users-bruno-siopv/memory/siopv-violations.md` | Stage 4.2 Batch 7 |
| CREATE | `~/.claude/projects/-Users-bruno-siopv/memory/siopv-phase7-8-context.md` | Stage 4.2 Batch 7 |
| CREATE | `~/.claude/projects/-Users-bruno-sec-llm-workbench/memory/siopv-hooks-stage4.md` | Stage 4.2 Batch 7 (#51) |
| TRIM | `~/.claude/projects/-Users-bruno-sec-llm-workbench/memory/MEMORY.md` | Stage 4.2 Batch 7 (#50) — URGENT live defect |
