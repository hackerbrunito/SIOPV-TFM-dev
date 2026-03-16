# SIOPV Handoff: Worktree + Team Agent Orchestration Plan

**Date:** 2026-02-11
**Author:** Auto-generated handoff document
**Purpose:** Complete guide for finishing SIOPV Phases 6–8 using parallel Claude Code Team Agents with git worktrees

---

## SECTION 1: Project Status Summary

### Overview

**SIOPV** (Sistema Inteligente de Orquestación y Priorización de Vulnerabilidades) is a vulnerability orchestration and prioritization system located at:

```
/Users/bruno/siopv/
```

The project implements an intelligent pipeline that ingests, enriches, classifies, and prioritizes software vulnerabilities using ML models, LLM-powered enrichment, and a human-in-the-loop review workflow.

### Current Progress

- **Phases completed:** 6 of 9 (Phases 0–5) — **67% complete**
- **Full audit and fix cycle done:** ruff, mypy, and test suites have been audited and cleaned
- **Current metrics:**
  - **1,091 tests** passing
  - **81% code coverage**
  - **0 ruff errors**
  - **17 mypy errors remaining** (trivial — unused `type: ignore` comments + LangGraph type annotations)
- **Git:** Initialized with 20+ commits on `main` branch, remote `origin` configured
- **CI/CD:** GitHub Actions configured and operational
- **Codebase:** Up-to-date with all Python best practices as of February 2026

### Architecture

The project follows **hexagonal architecture** (ports & adapters):

```
src/siopv/
├── domain/           # Entities, value objects, domain services
├── application/      # Use cases, ports (interfaces), orchestration
├── adapters/         # Concrete implementations of ports
├── infrastructure/   # Cross-cutting concerns (logging, config, DB)
└── interfaces/       # CLI, API, dashboard entry points
```

### Tech Stack

| Category | Technology |
|----------|-----------|
| Language | Python 3.12 |
| Package manager | uv |
| Orchestration | LangGraph |
| ML | XGBoost, SHAP, LIME, Optuna |
| API | FastAPI |
| Dashboard | Streamlit |
| Vector DB | ChromaDB |
| Validation | Pydantic v2 |
| HTTP | httpx |
| Logging | structlog |
| Auth | OpenFGA (ReBAC) |

### Completed Phases

| Phase | Name | Description |
|-------|------|-------------|
| **Phase 0** | Setup | Project structure, dependencies, CLI entry points |
| **Phase 1** | Ingestion | Trivy JSON parsing, deduplication, Pydantic validation |
| **Phase 2** | Enrichment | NVD, GitHub, EPSS, Tavily APIs; ChromaDB vector store; CRAG pattern |
| **Phase 3** | ML Classification | XGBoost classifier, SHAP/LIME explainability, CISA KEV dataset, Optuna hyperparameter tuning |
| **Phase 4** | Orchestration | LangGraph state machine, uncertainty trigger, SQLite checkpointing |
| **Phase 5** | Authorization | OpenFGA integration, ReBAC model, hexagonal architecture enforcement |

### Remaining Phases

| Phase | Name | Description | Status |
|-------|------|-------------|--------|
| **Phase 6** | Privacy/DLP | Presidio PII detection + Claude Haiku semantic validation | NOT STARTED |
| **Phase 7** | Human-in-the-Loop | Streamlit dashboard, evidence triad, timeout escalation | NOT STARTED |
| **Phase 8** | Output | Jira ticket creation + PDF audit report generation | NOT STARTED |

### Deadline

> **Thesis deadline: March 1, 2026**

---

## SECTION 2: New Development Plan — Team Agents + Git Worktrees

### Approach

The remaining 3 phases (6, 7, 8) will be developed **in PARALLEL** using **Claude Code Team Agents**. Each agent works in its own **git worktree** — a separate working directory checked out to a dedicated feature branch.

**Why worktrees?**
- Eliminates file conflicts between agents working simultaneously
- Allows true parallel development (no lock contention on files)
- Each agent has a clean, isolated environment
- Branches merge cleanly back to `main` when complete

### Worktree Layout

```
Main repo:
  /Users/bruno/siopv/                    → branch: main

Worktrees created:
  /Users/bruno/siopv-phase6-dlp/         → branch: feature/phase-6-dlp
  /Users/bruno/siopv-phase7-dashboard/   → branch: feature/phase-7-dashboard
  /Users/bruno/siopv-phase8-output/      → branch: feature/phase-8-output
```

### Worktree Setup Commands

```bash
# Create worktrees from main repo
cd /Users/bruno/siopv
git worktree add ../siopv-phase6-dlp -b feature/phase-6-dlp
git worktree add ../siopv-phase7-dashboard -b feature/phase-7-dashboard
git worktree add ../siopv-phase8-output -b feature/phase-8-output

# Each worktree needs its own virtual environment and .env
cd /Users/bruno/siopv-phase6-dlp && uv sync && cp /Users/bruno/siopv/.env .env
cd /Users/bruno/siopv-phase7-dashboard && uv sync && cp /Users/bruno/siopv/.env .env
cd /Users/bruno/siopv-phase8-output && uv sync && cp /Users/bruno/siopv/.env .env
```

### Post-Completion Merge Procedure

```bash
# Merge all feature branches back to main (in order)
cd /Users/bruno/siopv
git merge feature/phase-6-dlp --no-ff
git merge feature/phase-7-dashboard --no-ff
git merge feature/phase-8-output --no-ff

# Clean up worktrees
git worktree remove ../siopv-phase6-dlp
git worktree remove ../siopv-phase7-dashboard
git worktree remove ../siopv-phase8-output
```

### Prerequisites (Must Be Done on `main` BEFORE Creating Worktrees)

1. **Fix 17 remaining mypy errors** — trivial fixes: unused `type: ignore` comments and LangGraph type annotations
2. **Add missing dependency:** `atlassian-python-api>=4.0.7` (needed for Phase 8 Jira integration)
3. **Pre-prepare shared state fields** in `application/orchestration/state.py` — add placeholder fields that Phase 6, 7, and 8 will use, so all branches start from the same base
4. **Commit these fixes to `main`** — all worktrees branch from this clean state

---

## SECTION 3: Orchestrator Role — STRICT RULES

> **This is the most critical section. These rules are NON-NEGOTIABLE.**

---

### YOU ARE THE ORCHESTRATOR

**Your ONLY job is to orchestrate. You do NOT do any work yourself.**

---

### Rules (NON-NEGOTIABLE)

1. **DELEGATE EVERYTHING.** You do not write code. You do not read files. You do not plan. You do not investigate. You delegate ALL of this to agents.

2. **Spawn a team using `TeamCreate`.** Create a team and define tasks for every piece of work. Every single task gets its own agent.

3. **Give instructions, then WAIT.** After spawning agents and assigning tasks, your only job is to wait for them to finish. Do not intervene. Do not micromanage.

4. **You can only ask agents: "What is your status?"** You cannot ask them to explain their work, show their code, or verbatim describe their findings. You just ask for status updates.

5. **You do NOT receive individual reports.** Each agent saves its findings/work to a file. You never read these files yourself.

6. **A Reporter Agent reads all individual reports and creates ONE summary final report.** This is the ONLY document that gets presented to you as the orchestrator.

7. **The summary final report is your ONLY output.** You receive it, present it to the user, and that's it.

---

### Team Structure

```
ORCHESTRATOR (you)
│
├── Planning Agent
│   └── Creates the detailed execution plan for all phases
│   └── Defines task breakdown, file assignments, dependencies
│   └── Saves plan to a file
│
├── Prerequisites Agent
│   └── Fixes 17 mypy errors on main
│   └── Adds atlassian-python-api dependency
│   └── Pre-prepares shared state fields
│   └── Commits fixes to main
│   └── Creates worktrees
│   └── Sets up venvs and .env in each worktree
│
├── Phase 6 Agent (DLP) — Works in /Users/bruno/siopv-phase6-dlp/
│   └── Implements full DLP module following hexagonal architecture
│   └── Domain: PIIEntity, SanitizedVulnerability, services
│   └── Application: DLPPort, SemanticValidatorPort, use cases
│   └── Adapters: PresidioDLPAdapter, ClaudeSemanticValidatorAdapter
│   └── Orchestration: sanitize_node for LangGraph
│   └── Tests: unit + integration
│   └── Commits to feature/phase-6-dlp
│   └── Saves report to file
│
├── Phase 7 Agent (Dashboard) — Works in /Users/bruno/siopv-phase7-dashboard/
│   └── Implements full HITL dashboard following hexagonal architecture
│   └── Domain: HumanReviewCase, ReviewStatus
│   └── Application: HITLPort, use cases, timeout handling
│   └── Interfaces: Streamlit app with evidence triad
│   └── Orchestration: hitl_node with interrupt() for LangGraph
│   └── Tests: unit + integration
│   └── Commits to feature/phase-7-dashboard
│   └── Saves report to file
│
├── Phase 8 Agent (Output) — Works in /Users/bruno/siopv-phase8-output/
│   └── Implements full output layer following hexagonal architecture
│   └── Domain: JiraTicket, PDFReport
│   └── Application: JiraPort, PDFGeneratorPort, use cases
│   └── Adapters: JiraAdapter (cloud=True), FPDFAdapter
│   └── Orchestration: output_node for LangGraph
│   └── Tests: unit + integration
│   └── Commits to feature/phase-8-output
│   └── Saves report to file
│
├── Merge Agent
│   └── Runs AFTER all phase agents complete
│   └── Merges all branches to main in order (6 → 7 → 8)
│   └── Resolves any conflicts
│   └── Runs full test suite + mypy + ruff
│   └── Saves merge report to file
│
└── Reporter Agent (FINAL)
    └── Reads ALL individual reports from all agents
    └── Creates ONE comprehensive summary final report
    └── This summary is the ONLY thing presented to the orchestrator
```

### Workflow

```
Step  1: Orchestrator spawns team (TeamCreate)
Step  2: Orchestrator creates tasks and assigns to agents
Step  3: Orchestrator says "Go" and WAITS
Step  4: Planning Agent plans → saves report
Step  5: Prerequisites Agent fixes main → creates worktrees
Step  6: Phase 6, 7, 8 Agents work IN PARALLEL in their worktrees
Step  7: Each phase agent saves its report when done
Step  8: Merge Agent merges all branches, runs verification
Step  9: Merge Agent saves merge report
Step 10: Reporter Agent reads ALL reports → creates summary
Step 11: Orchestrator receives ONLY the summary final report
Step 12: Orchestrator presents summary to user
```

### What the Orchestrator CANNOT Do

| | Action |
|---|--------|
| :x: | Read source code files |
| :x: | Write or edit code |
| :x: | Run tests or linters |
| :x: | Make git commits |
| :x: | Create plans or strategies |
| :x: | Investigate or research |
| :x: | Ask agents to explain their work in detail |
| :x: | Read individual agent reports |
| :x: | Intervene in agent work |

### What the Orchestrator CAN Do

| | Action |
|---|--------|
| :white_check_mark: | Spawn teams (`TeamCreate`) |
| :white_check_mark: | Create and assign tasks (`TaskCreate`, `TaskUpdate`) |
| :white_check_mark: | Ask agents "What is your status?" (`SendMessage`) |
| :white_check_mark: | Receive the final summary report from the Reporter Agent |
| :white_check_mark: | Present the final summary to the user |

---

## SECTION 4: Reference Information

### Key Files and Locations

| Reference | Path |
|-----------|------|
| **Full project spec / previous handoff** | `/Users/bruno/siopv/.claude/handoff-2026-02-10-session3.md` |
| **Phase 6 validator** | `/Users/bruno/siopv/testing-kit/claude/agents/validators/phase-6-validator.md` |
| **Phase 7 validator** | `/Users/bruno/siopv/testing-kit/claude/agents/validators/phase-7-validator.md` |
| **Phase 8 validator** | `/Users/bruno/siopv/testing-kit/claude/agents/validators/phase-8-validator.md` |
| **Feasibility analysis** | `~/2026-02-11_SIOPV_Worktree_Multi_Agent_Team_Workflow_Investigation_And_Feasibility_Analysis/` |
| **Project tech spec (thesis)** | `/Users/bruno/VIBE_CODING_JAN_2026/.private/docs/SIOPV_Propuesta_Tecnica_v2.txt` |

### Quick Reference: Branch Names

| Phase | Branch | Worktree Path |
|-------|--------|---------------|
| 6 - DLP | `feature/phase-6-dlp` | `/Users/bruno/siopv-phase6-dlp/` |
| 7 - Dashboard | `feature/phase-7-dashboard` | `/Users/bruno/siopv-phase7-dashboard/` |
| 8 - Output | `feature/phase-8-output` | `/Users/bruno/siopv-phase8-output/` |

### Dependency Graph

```
Prerequisites Agent
    │
    ├──→ Phase 6 Agent (DLP)        ─┐
    ├──→ Phase 7 Agent (Dashboard)   ├──→ Merge Agent ──→ Reporter Agent
    └──→ Phase 8 Agent (Output)     ─┘
```

---

## SECTION 5: Report File Convention

Each agent saves its report to `.ignorar/` in the main project directory:

```
/Users/bruno/siopv/.ignorar/
├── team-plan-2026-02-11.md                    ← Planning Agent
├── prerequisites-report-2026-02-11.md         ← Prerequisites Agent
├── phase6-dlp-report-2026-02-11.md            ← Phase 6 Agent
├── phase7-dashboard-report-2026-02-11.md      ← Phase 7 Agent
├── phase8-output-report-2026-02-11.md         ← Phase 8 Agent
├── merge-report-2026-02-11.md                 ← Merge Agent
└── FINAL-SUMMARY-REPORT-2026-02-11.md         ← Reporter Agent (THE ONLY ONE THE ORCHESTRATOR READS)
```

---

## SECTION 6: Critical Technical Notes for Agents

These corrections were identified during Context7 validation and MUST be followed:

### Phase 6 (DLP)
- Use `AsyncAnthropic` (NOT sync `Anthropic`) for async context
- Full model ID: `claude-haiku-4-5-20251001` (NOT `claude-haiku-4.5`)
- Custom Presidio recognizers needed for API keys and database URLs

### Phase 7 (Dashboard)
- Use LangGraph `interrupt()` pattern from `langgraph.pregel` for HITL blocking
- Checkpoint polling via `AsyncSqliteSaver`
- Streamlit session state for persistent data across reruns
- Timeout escalation: 4h → 8h → 24h auto-approval

### Phase 8 (Output)
- **CRITICAL:** `atlassian-python-api>=4.0.7` MISSING from dependencies (Prerequisites Agent must add it)
- `cloud=True` parameter REQUIRED for Jira Cloud initialization
- fpdf2 `.table()` method for structured data in PDF reports
- SHAP/LIME plot embedding in PDF requires matplotlib figure export

---

## SECTION 7: Task Dependencies (for Orchestrator to set up)

```
Planning Agent ───────────┐
                          ├──→ Prerequisites Agent ──┬──→ Phase 6 Agent ──┐
                          │                          ├──→ Phase 7 Agent ──├──→ Merge Agent ──→ Reporter Agent
                          │                          └──→ Phase 8 Agent ──┘
                          │
Planning MUST finish before Prerequisites starts.
Prerequisites MUST finish before ANY Phase agent starts.
Phase 6, 7, 8 run IN PARALLEL (no dependencies between them).
ALL Phase agents MUST finish before Merge Agent starts.
Merge Agent MUST finish before Reporter Agent starts.
```

Use `TaskCreate` with `addBlockedBy` to enforce this order.

---

*End of handoff document.*
