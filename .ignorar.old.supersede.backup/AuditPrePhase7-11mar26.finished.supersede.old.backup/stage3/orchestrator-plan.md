# STAGE-3 Execution Plan: SOTA Research & Deep Scan

> Produced by: orchestrator
> Date: 2026-03-11
> Status: AWAITING HUMAN APPROVAL

---

## Scope (from briefing.md Section 3, STAGE-3)

Three workstreams:
1. **SOTA Research** — Current best practices for Streamlit 1.x, Jira API v3, PDF generation (fpdf2)
2. **Library API Verification** — Verify all library APIs via Context7 → Docfork → WebSearch chain
3. **Codebase Deep Scan** — Asyncio patterns, LangGraph state management, OpenFGA integration points

## Scope Constraint
- All analysis limited to **Phases 0–6 ONLY** (per orchestrator-briefing rules)
- Phase 7/8 dependencies appearing as MISSING are EXPECTED-MISSING, not defects
- Deep scan examines existing code patterns to inform REMEDIATION-HARDENING and Phase 7/8 implementation

## Report Output Directory
All reports saved to: `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage3/`

## Totals
- **10 agents** (6 task agents + 3 round aggregators + 1 final aggregator)
- **3 rounds** + final aggregation
- **4 human checkpoints** (after each round + final)

---

## ROUND 1 — SOTA Research + API Verification (3 agents, parallel, web-only)

No source file access — all agents use Context7 → Docfork → WebSearch only. No file conflicts.

### Agent R1-A: researcher-streamlit-lime

- **Task:** Research Streamlit 1.x best practices for HITL dashboards + LIME visualization patterns
- **Specifics:**
  - Streamlit 1.x patterns for polling SQLite (not websockets, per spec-findings.md)
  - LIME bar chart visualization for per-feature ML score contributions
  - Dashboard port binding via env var (`$DASHBOARD_PORT`)
  - Timeout escalation cascade UI patterns (4h/8h/24h — spec-findings.md)
  - Verify Streamlit API via Context7 → Docfork → WebSearch chain
  - Verify LIME API via Context7 → Docfork → WebSearch chain
- **Output:** `{TIMESTAMP}-stage3-researcher-streamlit-lime-sota.md`

### Agent R1-B: researcher-jira-pdf

- **Task:** Research Jira API v3 integration patterns + fpdf2 2.7+ PDF generation for compliance reports
- **Specifics:**
  - Jira REST API v3 ticket creation with enriched schema (spec-findings.md Phase 8: Summary, Description, Priority, Labels, Custom Fields)
  - Auth via API Token + Email (`JIRA_API_TOKEN`, `JIRA_EMAIL`, `JIRA_BASE_URL`)
  - fpdf2 >=2.7.0 for ISO 27001 / SOC 2 audit-ready PDF reports (NOT reportlab, NOT weasyprint — spec explicitly names fpdf2)
  - PDF content: vulnerability list, LIME justifications, escalated cases, optional CoT
  - Verify Jira client library API via Context7 → Docfork → WebSearch chain
  - Verify fpdf2 API via Context7 → Docfork → WebSearch chain
- **Output:** `{TIMESTAMP}-stage3-researcher-jira-pdf-sota.md`

### Agent R1-C: researcher-infra

- **Task:** Research LangGraph 0.2+, LangSmith, Redis, FastAPI, and OpenTelemetry integration patterns
- **Specifics:**
  - LangGraph 0.2+ state management patterns with TypedDict state and SQLite checkpointing
  - LangGraph interrupt/resume pattern for HITL (Phase 7 integration point)
  - LangSmith as CoT audit trail — how `output_node` pulls from LangSmith traces for PDF (spec-findings.md LangSmith section)
  - Redis as EPSS cache layer (`REDIS_URL`, optional local, required full stack)
  - FastAPI REST interface patterns (`interfaces/api/`, port `$PORT`)
  - OpenTelemetry distributed tracing for FastAPI, httpx, SQLAlchemy
  - Verify each library API via Context7 → Docfork → WebSearch chain
- **Output:** `{TIMESTAMP}-stage3-researcher-infra-sota.md`

### Round 1 Aggregator
- Reads all 3 R1 reports
- Produces: `{TIMESTAMP}-stage3-round1-aggregated.md`

**[HUMAN CHECKPOINT after Round 1 aggregator completes]**

---

## ROUND 2 — Codebase Deep Scan Part 1 (2 agents, parallel)

Source file access — agents read existing SIOPV code. File assignments prevent overlap.

### Agent R2-A: scanner-asyncio

- **Task:** Scan all asyncio patterns in Phases 0–6 codebase
- **Files to read (max 5):**
  1. `src/siopv/application/orchestration/nodes/dlp_node.py`
  2. `src/siopv/application/orchestration/nodes/enrich_node.py`
  3. `src/siopv/interfaces/cli/main.py`
  4. `src/siopv/adapters/llm/` (any files present)
  5. `src/siopv/application/orchestration/nodes/ingest_node.py`
- **What to scan for:**
  - `asyncio.run()` usage in sync contexts (STAGE-1 known issue #7)
  - `async def` vs `def` patterns in nodes
  - Event loop nesting risks
  - Recommended fix patterns for REMEDIATION-HARDENING
- **Output:** `{TIMESTAMP}-stage3-scanner-asyncio-deep.md`

### Agent R2-B: scanner-openfga

- **Task:** Scan OpenFGA integration points in Phases 0–6 codebase
- **Files to read (max 5):**
  1. `src/siopv/application/orchestration/nodes/authorization_node.py`
  2. `src/siopv/adapters/authorization/` (adapter files)
  3. `src/siopv/infrastructure/di/authorization.py`
  4. `src/siopv/application/ports/authorization_port.py`
  5. `src/siopv/domain/` (any auth-related entities/constants)
- **What to scan for:**
  - How OpenFGA adapter is wired and used
  - STAGE-2 violation #5 (3 uncached `OpenFGAAdapter` instances)
  - Port abstraction quality for authorization
  - Integration readiness for Phase 7 (Streamlit auth via OpenFGA)
  - Recommended fix patterns for REMEDIATION-HARDENING
- **Output:** `{TIMESTAMP}-stage3-scanner-openfga-deep.md`

### File Overlap Verification
- R2-A reads: dlp_node, enrich_node, cli, llm/, ingest_node
- R2-B reads: authorization_node, auth adapter, auth DI, auth port, domain/
- **Zero shared files — safe to run in parallel**

### Round 2 Aggregator
- Reads both R2 reports
- Produces: `{TIMESTAMP}-stage3-round2-aggregated.md`

**[HUMAN CHECKPOINT after Round 2 aggregator completes]**

---

## ROUND 3 — Codebase Deep Scan Part 2 (1 agent)

Separated from Round 2 because this agent reads `enrich_node.py` which R2-A also reads. Per orchestrator-briefing rules, no two agents in the same round can access the same file.

### Agent R3-A: scanner-langgraph

- **Task:** Scan LangGraph state management patterns in Phases 0–6 codebase
- **Files to read (max 5):**
  1. `src/siopv/application/orchestration/graph.py`
  2. `src/siopv/application/orchestration/state.py`
  3. `src/siopv/application/orchestration/edges.py`
  4. `src/siopv/application/orchestration/nodes/classify_node.py`
  5. `src/siopv/application/orchestration/nodes/enrich_node.py`
- **What to scan for:**
  - TypedDict state structure and field usage
  - SQLite checkpointing configuration
  - `PipelineGraphBuilder` injection pattern (confirmed clean by STAGE-2)
  - Graph topology: START → authorize → ingest → dlp → enrich → classify → [escalate] → END
  - STAGE-2 violation #7 (domain logic in `edges.py`)
  - Integration points for Phase 7 interrupt/resume and Phase 8 `output_node`
  - `run_id` / correlation ID propagation (spec-findings.md Correlation ID section)
  - Recommended patterns for REMEDIATION-HARDENING
- **Output:** `{TIMESTAMP}-stage3-scanner-langgraph-deep.md`

### Round 3 Aggregator
- Reads the R3 report
- Produces: `{TIMESTAMP}-stage3-round3-aggregated.md`

**[HUMAN CHECKPOINT after Round 3 aggregator completes]**

---

## FINAL AGGREGATOR

After all 3 rounds complete:
- Reads all 3 round aggregated reports
- Produces: `{TIMESTAMP}-stage3-final-report.md`
- Summary <= 500 words sent to orchestrator → team-lead → human

**[FINAL HUMAN CHECKPOINT]**

---

## Agent Summary Table

| Round | Agent Name | Type | File Access | Parallel With |
|-------|-----------|------|-------------|---------------|
| R1 | researcher-streamlit-lime | Web research | None | R1-B, R1-C |
| R1 | researcher-jira-pdf | Web research | None | R1-A, R1-C |
| R1 | researcher-infra | Web research | None | R1-A, R1-B |
| R1 | round1-aggregator | Report merge | R1 reports only | — |
| R2 | scanner-asyncio | Code scan | dlp_node, enrich_node, cli, llm/, ingest_node | R2-B |
| R2 | scanner-openfga | Code scan | auth_node, auth adapter, auth DI, auth port, domain/ | R2-A |
| R2 | round2-aggregator | Report merge | R2 reports only | — |
| R3 | scanner-langgraph | Code scan | graph.py, state.py, edges.py, classify_node, enrich_node | — |
| R3 | round3-aggregator | Report merge | R3 report only | — |
| — | final-aggregator | Final merge | All round reports | — |

**Total: 10 agents** (6 task agents + 3 round aggregators + 1 final aggregator)

---

## Compliance with Orchestrator Briefing Rules

- ✅ Plan produced before any execution
- ✅ Round-based execution with human checkpoints between rounds
- ✅ No file conflicts within any round (verified per-agent file assignments)
- ✅ Max 5 files per agent
- ✅ Reports saved incrementally to `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage3/`
- ✅ Timestamp-based report naming (`{TIMESTAMP}-stage3-{agent}-{slug}.md`)
- ✅ Context safety: each agent has a small, focused task within 50-60% context limit
- ✅ Aggregator per round + final aggregator
- ✅ Scope: Phases 0–6 only; Phase 7/8 dependencies are EXPECTED-MISSING

---

**AWAITING HUMAN APPROVAL BEFORE ANY EXECUTION BEGINS.**
