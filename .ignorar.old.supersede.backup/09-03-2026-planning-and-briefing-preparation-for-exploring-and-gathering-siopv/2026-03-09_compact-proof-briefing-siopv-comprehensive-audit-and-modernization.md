# Compact-Proof Briefing: SIOPV Comprehensive Audit and Modernization

<!-- COMPACT-SAFE: This is the SINGLE SOURCE OF TRUTH for the SIOPV audit/modernization project. After any compaction, re-read this file in full. It contains: project overview, audit findings, five-stage plan, naming conventions, agent design principles, team lifecycle, 15 design decisions (DD-001 to DD-015), directory structure, three-layer guardrails, constraints/rules, current status, and 12 SIOPV-specific technical recommendations. -->

**Document type:** Compact-proof orchestration briefing
**Created:** 2026-03-09
**Project:** SIOPV Comprehensive Audit, Scanning, and Modernization
**Author:** Bruno (principal investigator)
**Source documents:**
- Full conversation transcript: `~/siopv/.ignorar/09-03-2026-planning-and-briefing-preparation-for-exploring-and-gathering-siopv/2026-03-09_16.02.58_full-conversation-transcript-march-9-planning-session.md`
- Merged dual-purpose record: `~/siopv/.ignorar/09-03-2026-planning-and-briefing-preparation-for-exploring-and-gathering-siopv/2026-03-09_definitive-dual-purpose-record-merged-comprehensive.md`
- Project state file: `~/sec-llm-workbench/projects/siopv.json`

---

## 1. PROJECT OVERVIEW

### What SIOPV Is

SIOPV stands for **Sistema Inteligente de Orquestacion y Priorizacion de Vulnerabilidades** (Intelligent Vulnerability Orchestration and Prioritization System). It is a master's thesis project implementing a hybrid ML + GenAI pipeline for CI/CD vulnerability management. The system ingests Trivy scan reports, enriches them via RAG/CRAG against multiple data sources (NVD, EPSS, GitHub Security Advisories, Tavily), classifies vulnerabilities using XGBoost with SHAP/LIME explainability, orchestrates the pipeline via LangGraph, enforces fine-grained authorization via OpenFGA, sanitizes data via Presidio DLP, presents escalated cases to humans via Streamlit, and outputs Jira tickets + PDF audit reports.

### Full Tech Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Runtime |
| uv | latest | Package manager |
| LangGraph | >=0.2.0 | AI orchestration (state machine pipeline) |
| Claude (Haiku 4.5 + Sonnet 4.5) | -- | LLM reasoning |
| XGBoost | >=2.0.0 | ML classification |
| SHAP / LIME | latest | Explainability (XAI) |
| ChromaDB | >=0.5.0 | Vector database (RAG) |
| Presidio | >=2.2.0 | DLP sanitization |
| OpenFGA | latest | Fine-grained authorization |
| Streamlit | >=1.40.0 | Dashboard (HITL) |
| PostgreSQL | 16 | Database (checkpointing) |

### Architecture

Hexagonal (ports and adapters) architecture with the following layers:
- `src/siopv/domain/` -- entities, value objects, constants
- `src/siopv/application/` -- use cases, orchestration (LangGraph graph)
- `src/siopv/adapters/` -- external service clients (NVD, EPSS, GitHub, Tavily, Chroma, LLM, notification, persistence)
- `src/siopv/infrastructure/` -- config (Settings), DI container, logging
- `src/siopv/interfaces/` -- CLI (Typer), future API/dashboard

Graph flow: `START -> authorize -> ingest -> dlp -> enrich -> classify -> [escalate] -> END`

### Current State

- Phases 0-6: COMPLETED
- Phase 7 (Human-in-the-Loop -- Streamlit): PENDING
- Phase 8 (Output -- Jira + PDF): PENDING
- Tests: 1,404 passed, 12 skipped (as of 2026-03-05 audit)
- Coverage: 83% overall
- mypy: 0 errors
- ruff: 0 errors

### Two-Repo Architecture

The **meta-project** `sec-llm-workbench` lives at `~/sec-llm-workbench/`. It contains the Claude Code configuration, project state files, workflow definitions, and agent infrastructure. It GENERATES and MANAGES the SIOPV project.

The **generated project** `siopv` lives at `~/siopv/`. It contains the actual application code. It must remain clean and exportable -- no `.claude/` or `CLAUDE.md` committed to its git repo.

These are separate git repositories. The meta-project tracks SIOPV's state via `~/sec-llm-workbench/projects/siopv.json`.

### Key File Paths in SIOPV

| Component | Path |
|-----------|------|
| Graph (LangGraph pipeline) | `src/siopv/application/orchestration/graph.py` |
| State (TypedDict) | `src/siopv/application/orchestration/state.py` |
| CLI entry point | `src/siopv/interfaces/cli/main.py` |
| Settings (Pydantic) | `src/siopv/infrastructure/config/settings.py` |
| DI container | `src/siopv/infrastructure/di/__init__.py` |
| DLP DI | `src/siopv/infrastructure/di/dlp.py` |
| Constants | `src/siopv/domain/constants.py` |
| Logging setup | `src/siopv/infrastructure/logging/setup.py` |

### Key File Paths in Meta-Project (sec-llm-workbench)

| Component | Path |
|-----------|------|
| Project state | `~/sec-llm-workbench/projects/siopv.json` |
| CLAUDE.md | `~/sec-llm-workbench/CLAUDE.md` |
| Workflow files | `~/sec-llm-workbench/.claude/workflow/` |
| Session start | `~/sec-llm-workbench/.claude/workflow/01-session-start.md` |
| Before commit | `~/sec-llm-workbench/.claude/workflow/05-before-commit.md` |
| Human checkpoints | `~/sec-llm-workbench/.claude/workflow/03-human-checkpoints.md` |
| Agent reports rule | `~/sec-llm-workbench/.claude/rules/agent-reports.md` |

---

## 2. AUDIT FINDINGS (from 2026-03-05 audit of Phases 0-6)

### CRITICAL (must fix before Phase 7)

1. **CLI hollow** -- `interfaces/cli/main.py` has 3 TODO stubs. Pipeline unreachable from CLI.
2. **SanitizeVulnerabilityUseCase orphaned** -- dead code, never called. `dlp_node` is the real path.
3. **LLM confidence is a heuristic** -- `_estimate_llm_confidence()` is pure math, not an LLM call. `adapters/llm/` is empty.
4. **`run_pipeline()` drops enrichment clients** -- `graph.py:439-444` does not pass nvd/epss/github/osint/vector_store to `create_pipeline_graph()`.

### HIGH

5. **DLP DI not exported** -- `infrastructure/di/__init__.py` missing `get_dlp_port`, `get_dual_layer_dlp_port`.
6. **Hardcoded Haiku model IDs** -- 4 DLP files hardcode `"claude-haiku-4-5-20251001"` instead of reading from Settings.
7. **`asyncio.run()` in sync nodes** -- `dlp_node`, `enrich_node`, `authorization_node` will break inside async runners.
8. **No tests for Phase 2 adapters** -- NVD, EPSS, GitHub, Tavily, ChromaAdapter all at 0-20% coverage.
9. **structlog `format_exc_info` deprecation** -- triggers UserWarning every test run. Fix: use `ExceptionRenderer`.

### MEDIUM

10. **Hardcoded `openfga:openfga` in docker-compose** -- lines 113, 201.
11. **Magic numbers in classify_node** -- bypass `domain/constants.py` (0.7, 0.3, 0.4, 0.6 hardcoded inline).
12. **`output_node` missing from graph** -- Phase 8 requires graph topology change, not just new files.
13. **Empty adapter dirs** -- `adapters/llm/`, `adapters/notification/`, `adapters/persistence/` are stubs.

### LOW

14. **Integration tests always skip** -- fixed only by running Docker (OpenFGA + Keycloak).
15. **coverage.json stale** -- dated 2026-02-24, needs regeneration.

---

## 3. FIVE-STAGE PLAN

### STAGE-1: Discovery & Spec Mapping

**Objective:** Map the SIOPV codebase structure, identify all modules, verify alignment with the project specification, and produce a comprehensive inventory.

**Agent types:**
- Scanner agents (3-4): Scan directory structure, imports, dependencies, test coverage per module. Read-only tools (Read, Grep, Glob, Bash with write-blocking hook).
- Summarizer (1): Consolidates scanner findings into a unified spec-vs-implementation matrix.
- Orchestrator (1): Manages scanner rounds, collects reports, triggers summarizer.

**Expected rounds:** 2 rounds. Round 1: parallel scanners cover different codebase areas. Round 2: summarizer consolidates.

**Outputs:** Spec-vs-implementation matrix, module inventory, dependency map, test coverage map. Saved to `stage-1-discovery-and-spec-mapping/reports/`.

### STAGE-2: Hexagonal Quality Audit

**Objective:** Audit code quality against hexagonal architecture principles. Check layer violations, dependency direction, port/adapter compliance, and DI patterns.

**Agent types:**
- Scanner agents (4-6): Each audits a specific hexagonal layer or cross-cutting concern (domain, application, infrastructure, interfaces, DI, testing). Read-only tools.
- Summarizer (1): Consolidates findings into a severity-ranked finding list with file-level detail.
- Orchestrator (1): Manages scanner rounds.

**Expected rounds:** 2-3 rounds. Round 1: domain + application layers. Round 2: infrastructure + interfaces layers. Round 3 (if needed): cross-cutting concerns (DI, testing).

**Outputs:** Severity-ranked findings, layer violation map, DI audit results. Saved to `stage-2-hexagonal-quality-audit/reports/`.

### STAGE-3: SOTA Research & Deep Scan

**Objective:** Research state-of-the-art techniques for each SIOPV component. Compare current implementation against best practices from academic literature, framework documentation, and production patterns.

**Agent types:**
- Researcher agents (4-6): Each researches a specific domain (LangGraph patterns, DLP/Presidio best practices, vulnerability classification SOTA, OpenFGA patterns, Streamlit HITL patterns). Tools: Read, Grep, Glob, WebSearch, WebFetch, Context7.
- Summarizer (1): Consolidates research into actionable recommendations ranked by impact.
- Orchestrator (1): Manages researcher rounds.

**Expected rounds:** 2-3 rounds. Round 1: core pipeline research (LangGraph, classification, DLP). Round 2: supporting systems research (OpenFGA, Streamlit, output generation). Round 3 (if needed): gap-filling research.

**Outputs:** SOTA comparison matrix, actionable recommendations ranked by impact. Saved to `stage-3-sota-research-and-deep-scan/reports/`.

### STAGE-4: Claude Code Configuration Setup

**Objective:** Create the actual agent definition files, hook scripts, rules files, and settings.json configuration needed to operate SIOPV's agent team.

**Agent types:**
- Scanner agents (2): Audit existing `.claude/` configuration against research findings. Identify gaps and misconfigurations.
- Summarizer (1): Produces a configuration gap analysis and implementation plan.
- Orchestrator (1): Manages the audit and produces the final configuration blueprint.

**Expected rounds:** 2 rounds. Round 1: configuration audit scanners. Round 2: gap analysis summarizer.

**Outputs:** Configuration blueprint, gap analysis, implementation plan. Saved to `stage-4-claude-code-configuration-setup/reports/`.

### REMEDIATION-HARDENING (Separate Project -- Designed AFTER Stages 1-4)

**Objective:** Apply corrections and fixes identified in STAGE-1 through STAGE-4. This stage is designed AFTER stages 1-4 complete, based on their actual findings.

**Agent types:** To be determined based on findings. Expected to include code-implementer agents (write-capable), verification agents (5-agent pipeline: best-practices-enforcer, security-auditor, hallucination-detector, code-reviewer, test-generator), and a remediation orchestrator.

**Expected rounds:** Variable, determined by finding volume and severity.

**Outputs:** Fixed code, verification reports, final consolidated audit report. Saved to `remediation-hardening-apply-fixes-and-hardening/reports/`.

---

## 4. NAMING CONVENTIONS

These naming conventions were explicitly decided during the March 9 planning session. They are non-negotiable.

### Term Definitions

| Term | Meaning | Example |
|------|---------|---------|
| **Phase** | SIOPV pipeline phases ONLY (0-8) | Phase 6 = DLP/Presidio |
| **Stage** | Audit stages (1-4 + remediation) | Stage 2 = Hexagonal Quality Audit |
| **Round** | Sequential units WITHIN a stage | Round 1, Round 2 within Stage-1 |
| **Batch** | Parallel groups WITHIN a round | Batch A = agents 1-4 running in parallel |

**NEVER use "phase" for audit stages.** "Phase" is reserved exclusively for SIOPV pipeline phases 0 through 8.

### File Naming Pattern

```
NNN_YYYY-MM-DD_HH.MM.SS_descriptive-name-ten-to-fifteen-words.md
```

- `NNN` = zero-padded sequence number within the stage (001, 002, ...)
- Dots for time separators (HH.MM.SS), NOT colons (filesystem-safe, human-readable)
- 10-15 word descriptive kebab-case name
- Each stage has its own sequence counter starting at 001
- Agents receive their sequence number from the orchestrator at spawn time

Example: `001_2026-03-09_14.30.45_hexagonal-layer-scan-domain-application-layers.md`

---

## 5. AGENT DESIGN PRINCIPLES

### Size and Instruction Limits

- **150-instruction ceiling:** Frontier models max out at approximately 150-200 instructions. Beyond this threshold, more rules correlate with WORSE overall compliance across ALL rules. (Jaroslawicz et al., 2025)
- **20-rule sweet spot:** Maximum 20 core rules per agent body. This is the practical limit for reliable compliance.
- **200-line body max:** Agent bodies capped at 200 lines. Shorter system prompts get more uniform attention. Non-critical content moved to skills loaded on demand.
- **CLAUDE.md under 300 lines:** Bloated CLAUDE.md files cause Claude to ignore actual instructions.

### 4-Element Persona Pattern

Every SIOPV agent follows this standardized pattern:
1. **Identity:** "You are a [role] specialized in [domain]."
2. **Expertise:** Background, domain knowledge, specific capabilities.
3. **Constraints:** "You are NOT [anti-persona list]." + DO NOT list (5 items minimum).
4. **Output format:** Exact template structure the agent must follow.

### Anti-Improvisation: Explicit DO NOT Lists

Every agent includes a DO NOT list with a minimum of 5 items. Examples:
- DO NOT modify files outside your scope
- DO NOT skip files because they "look fine"
- DO NOT speculate about business impact
- DO NOT suggest fixes when your role is analysis
- DO NOT proceed without updating your todo list

Additionally, every agent includes "You are NOT" constraints to prevent persona leakage. Example: "You are NOT a code implementer. You are NOT a fixer. You are NOT an advisor on business strategy."

### Context Positioning

- **Front-load 3 critical rules** at the top of every agent body (first 10 lines).
- **Repeat rule #1 at the end** of the body (last 3 lines), exploiting both primacy and recency effects.
- Information in the middle of long contexts gets deprioritized (>30% performance drop). This is architectural in transformers (U-shaped attention curve), not a bug.
- Use `IMPORTANT`, `YOU MUST`, `NEVER` markers sparingly -- add to the 20 most critical instructions only.

### 60% Context Soft Limit with Save/Restore

Agents should aim to complete their work within 60% of the context window. PreCompact hook saves state to disk as a safety net before auto-compaction triggers at 95% of 200K tokens.

### Rules vs Hooks

"Rules are requests (~80% compliance at best), hooks are laws (100% compliance)." For anything that MUST happen, implement it as a hook or tool restriction. For preferences and guidance, use prompts. Never rely on prompts alone for safety-critical rules.

### Todo List Recitation

Agents constantly rewrite a todo list after each step: `[x] Completed` / `[ ] Remaining` / `Current focus: [step]`. This pushes the global plan into the END of the context window (high-attention zone), combating lost-in-the-middle degradation.

### Scoped Tool Access

Default to read-only and add write tools only when the agent's mandate requires modification. Tool restrictions are the most reliable anti-improvisation mechanism because they are deterministic -- an agent without the Write tool cannot create files regardless of how persuasive its reasoning is.

| Agent Type | Tools | Enforcement |
|-----------|-------|-------------|
| Scanner | Read, Grep, Glob, Bash | PreToolUse hook blocks write commands |
| Researcher | Read, Grep, Glob, WebSearch, WebFetch | No Bash, no Write |
| Summarizer | Read, Grep, Glob, Write | Write only to report directory |
| Orchestrator | Read, Grep, Glob, Bash, Write, Agent, SendMessage | Full coordination tools |

---

## 6. TEAM LIFECYCLE

### Execution Flow

```
claude-main
  |
  +--> TeamCreate(team_name="siopv-stage-N", agent_type="orchestrator")
  |
  +--> Agent(name="orchestrator", prompt="Read briefing at: {path}", ...)
  |
  +--> claude-main names itself "claude-main" in the team
  |
  +--> claude-main WAITS. Orchestrator handles everything from here.
       |
       +--> Orchestrator reads briefing file
       |
       +--> Round 1: spawns 4-6 parallel agents (Batch A)
       |      |
       |      +--> Each agent: clean context, reads assigned scope, writes report to disk,
       |      |    returns condensed summary (1,000-2,000 tokens), terminates
       |      |
       |      +--> Wave summarizer: reads ONLY round reports, produces round summary
       |
       +--> Orchestrator sends round summary to claude-main via SendMessage
       |
       +--> HUMAN CHECKPOINT: human reviews, approves next round or requests corrections
       |
       +--> Round 2: repeats pattern
       |
       +--> Final summarizer: reads ONLY round summaries (NOT individual reports)
       |
       +--> Orchestrator sends final summary to claude-main
       |
       +--> HUMAN CHECKPOINT: human approves stage deliverable
```

### Pre/Post-Compaction Hooks

- **PreCompact hook:** Saves current todo state and accumulated findings to disk before auto-compaction triggers.
- **External memory:** Orchestrator maintains a `todo.md` file updated after each round. Agents write findings to disk immediately, not held in memory.
- **No cross-agent context bleeding:** Each agent starts fresh. The only shared state is on disk (reports, todo.md, progress tracker).

### Context7 Local JSON Cache Pattern

Before using any library, agents verify current API/patterns using the 3-tier lookup chain:
1. **Tier 1 -- Context7:** `resolve-library-id` then `query-docs`
2. **Tier 2 -- Docfork:** `query_docs` + `fetch_url` if Context7 is rate-limited
3. **Tier 3 -- WebSearch:** Always, as cross-check

Training data is stale by definition -- NEVER rely on it for library APIs, security practices, or framework patterns.

---

## 7. DESIGN DECISIONS (DD-001 through DD-015)

### DD-001: Agent Definition File Structure
- **What:** Every SIOPV agent uses `.md` files in `.claude/agents/` with YAML frontmatter containing at minimum: `name`, `description`, `tools`. Body contains the complete system prompt.
- **Why:** Subagents receive ONLY the body content plus environment details. Four-field minimum is the irreducible set for controlled behavior.
- **How:** Create `.claude/agents/` directory structure. Each agent file follows the template: frontmatter (name, description, tools, model, maxTurns, hooks) + body (identity, mandate, workflow, boundaries, output format, critical rule repetition).

### DD-002: Persona Template
- **What:** All SIOPV agents follow a standardized 4-element persona pattern: identity + domain expertise + constraints + output format.
- **Why:** Direct persona assignment ("You are an X") outperforms imagination framing ("Imagine you are...") empirically. Explicit "You are NOT" constraints prevent persona leakage.
- **How:** Every agent body begins with: `You are a [role] specialized in [domain]. Your mandate is [single sentence]. You are NOT [anti-persona list]. YOU MUST [top 3 rules]. DO NOT [5-item list].` Followed by workflow steps, then output format, then critical rule repetition at end.

### DD-003: Per-Agent Rule Limit
- **What:** Maximum 20 core rules per agent body. Maximum 200 lines per agent body.
- **Why:** The 150-instruction ceiling applies within agent bodies too. Beyond 20 rules, compliance degrades measurably.
- **How:** Count rules during agent creation. If a body exceeds 20 rules or 200 lines, split into core rules (in body) and supplementary knowledge (in skills loaded on demand).

### DD-004: Agent Body Size Limit
- **What:** Agent bodies capped at 200 lines. Non-critical content moved to skills or external reference files.
- **Why:** Shorter system prompts get more uniform attention. The 200-line limit ensures the full body fits within the high-attention zone.
- **How:** Bodies exceeding 200 lines trigger a mandatory refactoring into body (core) + skill (supplementary).

### DD-005: Hook Configuration
- **What:** Three hook types deployed: (1) PreToolUse blocking hooks for security enforcement. (2) PreCompact hooks to save agent state before compaction. (3) PostToolUse hooks for auto-formatting after edits.
- **Why:** "Rules are requests, hooks are laws." PreToolUse is the ONLY blocking hook. PreCompact preserves state that would be lost to auto-compaction.
- **How:** In `.claude/settings.json`: PreToolUse matcher "Bash" runs `block-dangerous-commands.sh` (exit code 2 to block). PostToolUse matcher "Edit|Write" runs `run-linter.sh`. PreCompact hook saves current todo state to disk.

### DD-006: Tool Restriction Strategy
- **What:** Tool allowlists per agent type. Default to read-only; add write tools only when the agent's mandate requires modification.
- **Why:** Scoped tool access is the most reliable anti-improvisation mechanism -- deterministic prevention.
- **How:** Scanner agents: `Read, Grep, Glob, Bash` (Bash with PreToolUse blocking writes). Researcher agents: `Read, Grep, Glob, WebSearch, WebFetch`. Summarizer agents: `Read, Grep, Glob, Write` (write only to report directory). Orchestrator agents: `Read, Grep, Glob, Bash, Write, Agent, SendMessage`.

### DD-007: Report Template Enforcement
- **What:** Every agent produces reports following an exact template. Reports are validated structurally before acceptance.
- **Why:** Template constraints on output are one of the four anti-drift techniques for verification agents. Structured payloads prevent context loss.
- **How:** Each agent's body includes an exact report template with required sections: agent name, stage/round/batch IDs, timestamp, execution duration, findings (structured with severity, location, description, evidence, recommendation), and a summary. PostToolUse hook validates report structure.

### DD-008: Context Positioning Strategy
- **What:** Front-load the 3 most critical rules at the top of every agent body. Repeat the single most important rule at the end.
- **Why:** >30% performance drop when key information sits in the middle vs. beginning/end. Repetition at both positions exploits primacy and recency.
- **How:** Agent body structure: (1) Identity + top 3 rules (first 10 lines). (2) Full workflow. (3) Boundaries and DO NOT list. (4) Output format. (5) Repeat of the #1 most critical rule (last 3 lines).

### DD-009: Anti-Improvisation Constraints
- **What:** Every agent includes: (a) explicit DO NOT list (5 items minimum), (b) todo list recitation after each step, (c) fresh context between unrelated tasks.
- **Why:** Per-step constraint design prevents both over-constraining creative steps and under-constraining critical steps. Todo recitation pushes global plan into high-attention zone. Fresh context outperforms accumulated corrections.
- **How:** DO NOT list template: `DO NOT: (1) modify files outside your scope, (2) skip files because they "look fine", (3) speculate about business impact, (4) suggest fixes when your role is analysis, (5) proceed without updating your todo list.`

### DD-010: Compaction-Safe Markers
- **What:** All workflow files and agent briefings include `<!-- COMPACT-SAFE: summary -->` markers. Critical values are literal, not references.
- **Why:** Auto-compaction at ~95% of 200K tokens summarizes conversation content. Markers and literal values survive compression.
- **How:** Every workflow file header includes a COMPACT-SAFE marker. All thresholds, paths, and constraints use literal values ("threshold is 0.7") never references ("threshold is defined in constants.py"). Triple storage for non-negotiable rules: system prompt + external file + runtime re-injection.

### DD-011: Round and Batch Management
- **What:** Within each stage, work is organized as Rounds (sequential units) containing Batches (parallel groups). Maximum 4-6 parallel agents per batch.
- **Why:** Sub-agent context isolation prevents cross-contamination. 4-6 parallel agents is the practical limit for token budget management. Sequential rounds allow human checkpoints.
- **How:** Stage execution: Round 1 (Batch A: agents 1-4 in parallel) -> wave summarizer -> human checkpoint -> Round 2 (Batch A: agents 5-8 in parallel) -> wave summarizer -> human checkpoint -> final summarizer reads only round summaries.

### DD-012: Human Checkpoint Protocol
- **What:** Human approval required between rounds, after final summaries, and before any destructive action. Automatic continuation for agent delegation, file reads, and report generation.
- **Why:** Human-in-the-loop at boundaries catches systemic issues before they propagate. Automatic continuation within rounds prevents bottlenecks.
- **How:** Orchestrator pauses and presents a summary after each round's wave summarizer completes. Human reviews findings, approves next round or requests corrections. No commit without human approval of consolidated verification results.

### DD-013: Agent Shutdown Protocol
- **What:** Agents shut down after completing their round. Reports are written to disk before shutdown. No persistent agent state in memory.
- **Why:** Fresh context by default maximizes per-agent performance. Persistent agents accumulate context rot. File-based reports survive agent termination.
- **How:** Agent workflow ends with: (1) write report to assigned path, (2) update progress tracker, (3) return condensed summary (1,000-2,000 tokens) to orchestrator, (4) terminate. SubagentStop hook cleans up temp resources.

### DD-014: File Naming Convention
- **What:** All reports follow the pattern: `NNN_YYYY-MM-DD_HH.MM.SS_descriptive-name.md` where NNN is a zero-padded sequence number within the stage.
- **Why:** Timestamp-based naming prevents race conditions under parallel execution. Sequential prefix preserves reading order.
- **How:** Example: `001_2026-03-09_14.30.45_hexagonal-layer-scan.md`. Each stage has its own sequence counter starting at 001. Agents receive their sequence number from the orchestrator at spawn time.

### DD-015: Directory Structure for the Audit Project
- **What:** All audit artifacts stored under `~/siopv/2026-03-09_14.26.42_siopv-comprehensive-audit-scanning-and-modernization/` with per-stage subdirectories.
- **Why:** Directory lives inside `~/siopv/` (not `.ignorar/`). Per-stage directories enable clean navigation and stage-level auditing.
- **How:** See Section 8 for the full directory tree.

---

## 8. DIRECTORY STRUCTURE

The audit project directory has already been created at:

```
~/siopv/2026-03-09_14.26.42_siopv-comprehensive-audit-scanning-and-modernization/
├── stages-1-to-4-discovery-research-and-configuration/
│   ├── shared/
│   │   ├── team-template.md                    (created)
│   │   ├── report-template.md                  (created)
│   │   ├── agent-persona-scanner.md            (created)
│   │   ├── agent-persona-summarizer.md         (created)
│   │   └── agent-persona-orchestrator.md       (created)
│   ├── stage-1-discovery-and-spec-mapping/
│   │   ├── agent-definitions/                  (empty, to be populated)
│   │   └── reports/                            (empty, to be populated)
│   ├── stage-2-hexagonal-quality-audit/
│   │   ├── agent-definitions/                  (empty, to be populated)
│   │   └── reports/                            (empty, to be populated)
│   ├── stage-3-sota-research-and-deep-scan/
│   │   ├── agent-definitions/                  (empty, to be populated)
│   │   └── reports/                            (empty, to be populated)
│   └── stage-4-claude-code-configuration-setup/
│       ├── agent-definitions/                  (empty, to be populated)
│       └── reports/                            (empty, to be populated)
└── remediation-hardening-apply-fixes-and-hardening/
    ├── agent-definitions/                      (empty, to be populated)
    └── reports/                                (empty, to be populated)
```

### Planning & Research Directory (separate from audit execution)

```
~/siopv/.ignorar/09-03-2026-planning-and-briefing-preparation-for-exploring-and-gathering-siopv/
├── 2026-03-09_16.02.58_full-conversation-transcript-march-9-planning-session.md
├── 2026-03-09_comparison-report-new-dual-purpose-vs-old-005.md
├── 2026-03-09_dual-purpose-record-comprehensive-checklist-and-technical-reference.md
├── 2026-03-09_definitive-dual-purpose-record-merged-comprehensive.md
└── 2026-03-09_compact-proof-briefing-siopv-comprehensive-audit-and-modernization.md  (THIS FILE)
```

---

## 9. THREE-LAYER GUARDRAILS

### Input Layer
- **Injection detection:** Filter malicious prompts and adversarial inputs before they reach agents.
- **PII screening:** Presidio-based PII detection on all inputs before LLM processing.
- **Format validation:** Pydantic validation on all structured inputs.
- **Rate limits:** Token budget per interaction, maximum 20 tool calls per invocation.

### Interaction Layer
- **Tool restriction:** Allowlist/denylist per agent type. An agent without the Write tool cannot create files regardless of its reasoning.
- **Token budget:** Track per-agent and per-wave token usage. Multi-agent systems consume up to 15x more tokens than standard chat.
- **State-machine tool availability:** Tools available to agents change based on execution state.
- **maxTurns limit:** Cap agentic turns per agent type (scanner: 25, researcher: 30, summarizer: 15, orchestrator: 50).

### Output Layer
- **Pydantic validation:** Structured output enforcement on all agent reports and handoff payloads.
- **Hallucination detection:** Cross-reference claims against source material.
- **Content safety:** Llama Guard or equivalent for safety classification.
- **Schema compliance:** Reports validated against mandatory template structure.
- **DLP scan:** Presidio scan on all outputs before delivery.

### Guardrail Mapping to Hexagonal Architecture

| Layer | Hexagonal Location | Guardrails |
|-------|-------------------|------------|
| Input Port | Ingest adapters | PII/Presidio, Pydantic validation, rate limiting |
| Processing | Application use cases | Tool state machine, token budget, timeout/retry, LLM judge on classify_node |
| Output Port | Output adapters | Pydantic validation, DLP scan, hallucination detection, schema version enforcement |

---

## 10. CONSTRAINTS AND RULES

### Subagent Prompt Design
- Subagent prompts must be SIMPLE and FOCUSED. The body IS the entire behavioral context -- subagents receive ONLY the body plus basic environment details (working directory), NOT the full Claude Code system prompt.
- Maximum 20 core rules in the body, maximum 200 lines total.
- Front-load the 3 most critical rules. Repeat rule #1 at the end.

### Anti-Improvisation
- Agents must NOT improvise -- explicit DO NOT lists with 5 items minimum.
- Every agent includes "You are NOT" constraints to prevent persona leakage.
- Tool restrictions are the primary enforcement mechanism (deterministic).
- Todo list recitation after each step (anti-drift).

### Library Verification
- All library usage must be verified via Context7 (or Docfork/WebSearch fallback) before coding.
- Training data is stale by definition. NEVER rely on it for library APIs.
- Builder agents must verify before coding. Gate agents must verify that builders performed the check.

### Verification Workflow
- Never bypass the verification workflow. The pre-commit hook exists for a reason.
- If the hook blocks, execute `/verify` to run all 5 agents, wait for human approval at checkpoints, and only then commit.
- NEVER manually clear pending markers to bypass the system.

### Human Checkpoints
- PAUSE for: stage transitions, round transitions, destructive actions, post-verification synthesis.
- CONTINUE automatically for: agent delegation, Context7 queries, file reads, report generation.
- No commit without human approval of consolidated verification results.

### Error Handling
- If an agent fails or times out: log the failure, report to claude-main, ask whether to retry or skip.
- If 2+ agents in a batch fail: STOP the stage and escalate to claude-main.
- After two failed corrections of the same agent, mark it as FAILED and report.

---

## 11. CURRENT STATUS AND NEXT ACTIONS

### What Has Been Completed (as of 2026-03-09)

1. **Research phase complete:**
   - Two comprehensive research reports produced (Claude Code agent configuration + LLM behavioral control science)
   - 132 checkpoints extracted (58 from Report 001, 74 from Report 002)
   - Definitive merged dual-purpose record created (21 sections, 1,455 lines)

2. **Planning phase complete:**
   - 15 design decisions documented (DD-001 through DD-015)
   - Five-stage plan designed with round/batch structure
   - Naming conventions established (Phase vs Stage vs Round vs Batch)
   - Agent persona templates created (scanner, researcher, summarizer, orchestrator)
   - Team lifecycle defined with human checkpoint protocol

3. **Directory structure created:**
   - Audit project directory at `~/siopv/2026-03-09_14.26.42_siopv-comprehensive-audit-scanning-and-modernization/`
   - All stage subdirectories created with `agent-definitions/` and `reports/` folders
   - Shared templates created (team-template, report-template, agent personas)

4. **This briefing file created:**
   - Compact-proof single source of truth for the entire audit project

### What Comes Next

1. **Create `.claude/` configuration for SIOPV audit project:**
   - Hook scripts: `block-write-commands.sh`, `block-dangerous-commands.sh`, `run-linter.sh`
   - Update `.claude/settings.json` with hook configurations
   - Agent definition files based on templates
   - Rules files (scanner-read-only, report-template, anti-improvisation)
   - Path-targeted rules for domain-specific constraints

2. **Execute Stage-1 (Discovery & Spec Mapping):**
   - Create Stage-1 orchestrator briefing
   - Spawn orchestrator team
   - Run rounds with human checkpoints

3. **Execute Stages 2-4 sequentially**, each with its own orchestrator briefing

4. **Design and execute Remediation-Hardening** based on findings from Stages 1-4

### File Inventory (all relevant files)

| File | Location | Purpose |
|------|----------|---------|
| Conversation transcript | `.ignorar/09-03-2026.../2026-03-09_16.02.58_full-conversation-transcript-march-9-planning-session.md` | Raw planning session |
| Comparison report | `.ignorar/09-03-2026.../2026-03-09_comparison-report-new-dual-purpose-vs-old-005.md` | Comparison between new and old dual-purpose records |
| Initial dual-purpose record | `.ignorar/09-03-2026.../2026-03-09_dual-purpose-record-comprehensive-checklist-and-technical-reference.md` | First draft |
| Merged dual-purpose record | `.ignorar/09-03-2026.../2026-03-09_definitive-dual-purpose-record-merged-comprehensive.md` | DEFINITIVE version (1,455 lines) |
| This briefing | `.ignorar/09-03-2026.../2026-03-09_compact-proof-briefing-siopv-comprehensive-audit-and-modernization.md` | Compact-proof single source of truth |
| Team template | `2026-03-09.../stages-1-to-4.../shared/team-template.md` | Reusable team lifecycle |
| Report template | `2026-03-09.../stages-1-to-4.../shared/report-template.md` | Mandatory report structure |
| Scanner persona | `2026-03-09.../stages-1-to-4.../shared/agent-persona-scanner.md` | Scanner agent template |
| Summarizer persona | `2026-03-09.../stages-1-to-4.../shared/agent-persona-summarizer.md` | Summarizer agent template |
| Orchestrator persona | `2026-03-09.../stages-1-to-4.../shared/agent-persona-orchestrator.md` | Orchestrator agent template |
| Project state | `~/sec-llm-workbench/projects/siopv.json` | SIOPV phase tracking |

---

## 12. SIOPV-SPECIFIC TECHNICAL RECOMMENDATIONS

These 12 recommendations come from the merged dual-purpose record (Section 15) and are specific to SIOPV's architecture and implementation.

### REC-01: Agent Tool Assignments

| Agent | Tools | Enforcement |
|-------|-------|-------------|
| security-auditor | Read-only + Bash | PreToolUse hook blocks write commands |
| code-implementer | All tools | PostToolUse runs ruff/mypy after every edit |
| test-generator | All tools | PostToolUse runs pytest after test file creation |
| hallucination-detector | Read-only only | NO Bash |
| best-practices-enforcer | Read-only + Bash | For running linters |

### REC-02: Hook Enforcement Configuration

- PreToolUse matcher "Bash" -> `.claude/hooks/block-dangerous-commands.sh`
- PostToolUse matcher "Edit|Write" -> `.claude/hooks/run-linter.sh`
- Add to `.claude/settings.json` under `hooks` key.

### REC-03: Path-Targeted Rules for SIOPV Domains

- `security.md` targeted to `src/siopv/infrastructure/**`
- `orchestration.md` targeted to `src/siopv/application/orchestration/**`
- Additional domain-specific rules files as needed.

### REC-04: Pipeline State File

Have each graph node update a persistent `pipeline_state.md` with current progress, remaining steps, accumulated findings. Serves as both external memory and attention anchor for the orchestrator.

### REC-05: Node-Level Context Isolation in LangGraph

Each node receives only the TypedDict fields relevant to its function. Restrict to only the fields it reads/writes. Flag nodes accessing >5 state fields for review.

### REC-06: PostgresSaver for Production Checkpointing

Migrate from SQLite to PostgresSaver. Enable time-travel debugging on classify_node and enrich_node. Currently uses SqliteSaver with path validation + extension whitelist.

### REC-07: Three-Layer Guardrails Mapped to Hexagonal Architecture

- **Input Port Guardrails:** PII/Presidio, Pydantic validation, rate limiting.
- **Processing Guardrails:** Tool state machine, token budget, timeout/retry, LLM judge on classify_node.
- **Output Port Guardrails:** Pydantic validation, DLP scan, hallucination detection, schema version enforcement.

### REC-08: Anti-Drift for classify_node (5 Mitigations)

1. Runtime reinforcement -- append classification constraints at end of every LLM prompt.
2. Structured output -- Pydantic models with strict JSON Schema.
3. Behavioral anchoring -- 3-5 canonical classification examples.
4. Output validation -- confidence scores within expected ranges.
5. LLM judge -- lightweight secondary model for consistency verification.

### REC-09: Compaction-Safe Architecture for Multi-Session Pipeline

- Pin critical constraints in system prompts.
- Use COMPACT-SAFE markers on all workflow files.
- External state files per phase.
- Instruction redundancy -- every critical rule in system prompt, node-level prompt, AND external config.

### REC-10: Verification Pipeline Guardrails

- Pydantic-validated report schemas for all 5 agents.
- Tripwire pattern -- CRITICAL finding = immediate halt.
- Wave timing: Wave 1 max 7 min, Wave 2 max 5 min.
- Clean context per verification agent.
- Drift detection -- compare against historical baselines.

### REC-11: Deterministic Behavior Where Possible

- Deterministic graph flow for non-LLM logic.
- Reproducibility logging: model ID, temperature, seed, full prompts for every LLM call.
- Constrained decoding for all LLM calls.
- Note: true determinism is impossible (temperature=0 is not fully deterministic due to floating-point arithmetic and MoE routing).

### REC-12: Inter-Phase Handoff Protocol

- `projects/siopv.json` as canonical state transfer.
- Pydantic models for inter-phase state.
- Validation on resume -- validate all accumulated state against schemas.
- Audit trail -- log inputs, outputs, verification results per phase transition.

---

## QUICK REFERENCE: SIZE LIMITS

| Component | Maximum | Notes |
|-----------|---------|-------|
| Agent body | 200 lines | Front-load critical rules |
| CLAUDE.md | 300 lines | Shorter is better |
| Total instructions (all loaded contexts) | 150 | Beyond this, compliance drops for ALL rules |
| Critical rules in prompts | 20 | The rest go to hooks/tool restrictions |
| Sub-agent return to orchestrator | 1,000-2,000 tokens | Condensed summaries only |
| Parallel agents per batch | 4-6 | Token budget management limit |

## QUICK REFERENCE: REPORT TEMPLATE

Every agent report must follow this structure:

```markdown
# [Agent Name] Report

**Stage:** STAGE-N
**Round:** N, Batch: A
**Sequence:** NNN
**Timestamp:** YYYY-MM-DD HH:MM:SS
**Duration:** N minutes

## Mandate
[One sentence: what this agent was asked to do]

## Findings
### Finding F-NNN: [Title]
- **Severity:** CRITICAL | HIGH | MEDIUM | LOW | INFO
- **Location:** [file path:line number]
- **Description:** [what was found]
- **Evidence:** [grep output, code snippet, or reference]
- **Recommendation:** [what should be done]

## Summary
- Total findings: N
- By severity: CRITICAL: N, HIGH: N, MEDIUM: N, LOW: N, INFO: N
- Files examined: N
- Files with findings: N

## Self-Verification
- [ ] All sections filled
- [ ] Every file path verified to exist
- [ ] Every finding has evidence
- [ ] Severity assignments are consistent
```

---

**END OF COMPACT-PROOF BRIEFING**
