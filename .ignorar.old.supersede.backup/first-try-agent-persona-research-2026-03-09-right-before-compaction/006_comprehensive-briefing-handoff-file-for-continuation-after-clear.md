# Comprehensive Briefing and Handoff File

**Purpose:** This file is the single source of truth for continuing the SIOPV audit and modernization project after a `/clear` command. It contains the full context, every decision, every nuance, and every reasoning from the planning session on 2026-03-09. It was created by reading the full conversation transcript and all supporting documents.

**Date of planning session:** 2026-03-09 (morning, approximately 01:00 to 07:00 UTC)
**Created by:** Subagent reading the full conversation transcript
**Files referenced:** conversation JSONL, file 005 (dual-purpose document), files 001-004 (research reports and checkpoint extractions)

---

## TABLE OF CONTENTS

1. [Project Context: What is SIOPV](#1-project-context-what-is-siopv)
2. [The Meta-Project Relationship](#2-the-meta-project-relationship)
3. [Why This Audit Exists: The Problem Being Solved](#3-why-this-audit-exists-the-problem-being-solved)
4. [The Five Stages: What They Are and Why](#4-the-five-stages-what-they-are-and-why)
5. [Naming Conventions and Why They Matter](#5-naming-conventions-and-why-they-matter)
6. [Directory Structure and File Naming](#6-directory-structure-and-file-naming)
7. [Team Design: The Reusable Template](#7-team-design-the-reusable-template)
8. [Agent Behavioral Control: The Full Design](#8-agent-behavioral-control-the-full-design)
9. [What Agents Assess: The Exact Scope](#9-what-agents-assess-the-exact-scope)
10. [STAGE-1 Specific Agent Design](#10-stage-1-specific-agent-design)
11. [The everything-claude-code GitHub Analysis](#11-the-everything-claude-code-github-analysis)
12. [Claude Code Features Planned for STAGE-4](#12-claude-code-features-planned-for-stage-4)
13. [REMEDIATION-HARDENING: Why It Is Separate](#13-remediation-hardening-why-it-is-separate)
14. [Research Conducted and Files Created](#14-research-conducted-and-files-created)
15. [What Has NOT Been Created Yet](#15-what-has-not-been-created-yet)
16. [User Preferences and Non-Negotiable Requirements](#16-user-preferences-and-non-negotiable-requirements)
17. [Next Steps: Exact Execution Order](#17-next-steps-exact-execution-order)

---

## 1. PROJECT CONTEXT: WHAT IS SIOPV

**SIOPV** = Sistema Inteligente de Orquestacion y Priorizacion de Vulnerabilidades (Intelligent Vulnerability Orchestration and Prioritization System).

This is a **master's thesis project**. The deadline is approximately **10 days from 2026-03-09**, meaning around 2026-03-19. The thesis examiners will read the audit files produced by this process -- methodological rigor matters.

### Project Location and Size

- **Path:** `~/siopv/`
- **188 project-relevant files** (this count excludes `.venv`, `__pycache__`, `.git`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, coverage reports, `.build/`, `.ignorar/`, `.claude/`)
- **170 Python files** (97 source in `src/`, 71 tests in `tests/`, 2 setup scripts in `scripts/`)
- **18 non-Python project files:** 10 JSON, 3 YAML, 1 TOML (`pyproject.toml`), 1 OpenFGA model (`.fga`), 3 env files (`.env`, `.env.example`, `.env.bckp`)

The user explicitly clarified: "project-relevant files" means files that make the project work -- Python code, configuration, settings, inter-technology communication files. NOT handoff markdown files, NOT `.claude/` configuration, NOT coverage HTML reports, NOT `.build/` checkpoints. Those exist in the repo but are internal tooling, not part of SIOPV itself.

### Architecture

- **Hexagonal architecture** (ports and adapters pattern)
- **LangGraph** for pipeline orchestration
- **CRAG judge pattern** (Corrective RAG) for LLM-based analysis
- **TypedDict state** (not Pydantic) -- by design choice in LangGraph
- **DI pattern:** `lru_cache` factory functions in `infrastructure/di/`
- **Docker:** `docker-compose.yml` runs OpenFGA + Keycloak + Postgres
- **Checkpointing:** SQLite (`siopv_checkpoints.db`)

### Phases 0-8

| Phase | Name | Status |
|-------|------|--------|
| 0 | Setup | COMPLETED |
| 1 | Ingesta y Preprocesamiento | COMPLETED |
| 2 | Enriquecimiento (CRAG/RAG) | COMPLETED |
| 3 | Clasificacion ML (XGBoost) | COMPLETED |
| 4 | Orquestacion (LangGraph) | COMPLETED |
| 5 | Autorizacion (OpenFGA) | COMPLETED |
| 6 | Privacidad (DLP/Presidio) | COMPLETED |
| 7 | Human-in-the-Loop (Streamlit) | PENDING |
| 8 | Output (Jira + PDF) | PENDING |

Graph flow: `START -> authorize -> ingest -> dlp -> enrich -> classify -> [escalate] -> END`

### Quality Metrics (as of 2026-03-05 audit)

- Tests: 1,404 passed, 12 skipped
- Coverage: 83% overall
- mypy: 0 errors
- ruff: 0 errors

### Known Issues (from 2026-03-05 audit)

There are 15 known findings (4 CRITICAL, 5 HIGH, 3 MEDIUM, 3 LOW) documented in `memory/siopv-audit-2026-03-05.md` in the MEMORY.md. These are pre-existing and well-documented. The audit we are planning now is a DIFFERENT, more comprehensive exercise.

### Key File Paths

| What | Path |
|------|------|
| Project spec | `~/sec-llm-workbench/docs/SIOPV_Propuesta_Tecnica_v2.txt` (806 lines) |
| Project state | `~/sec-llm-workbench/projects/siopv.json` (518 lines) |
| Graph | `src/siopv/application/orchestration/graph.py` |
| State | `src/siopv/application/orchestration/state.py` |
| CLI | `src/siopv/interfaces/cli/main.py` |
| Settings | `src/siopv/infrastructure/config/settings.py` |
| DI container | `src/siopv/infrastructure/di/__init__.py` |
| Constants | `src/siopv/domain/constants.py` |
| Logging | `src/siopv/infrastructure/logging/setup.py` |
| Analysis files | `~/sec-llm-workbench/.ignorar/siopv-*.md` (6 files, 2,838 lines total) |

---

## 2. THE META-PROJECT RELATIONSHIP

There are TWO directories involved:

1. **`~/sec-llm-workbench/`** -- The meta-project. This is a framework for vibe coding that contains workflows, agent definitions, skills, hooks, and project management files. It was used as the orchestration environment during SIOPV development (phases 0-6). The SIOPV project state file (`projects/siopv.json`), the project spec, and analysis files live here. The current Claude Code session is running FROM this directory.

2. **`~/siopv/`** -- The actual SIOPV project. This is where all the Python code, tests, configurations, and Docker files live.

**The key decision:** The user wants to MOVE AWAY from developing SIOPV through the meta-project. Going forward, development should happen DIRECTLY in `~/siopv/`. This means the Claude Code configuration (`.claude/` directory with agents, hooks, rules, settings) needs to be set up INSIDE `~/siopv/` as part of STAGE-4. Currently, `~/siopv/` has a `.claude/` directory but it was set up for the meta-project's workflow. The new setup will be purpose-built for SIOPV's needs.

This context is critical: the entire audit and STAGE-4 Claude Code configuration setup exists because the user wants the SIOPV project to be self-contained and independent from the meta-project.

---

## 3. WHY THIS AUDIT EXISTS: THE PROBLEM BEING SOLVED

The audit is NOT about "finding bugs to fix." The user was very explicit about this:

> "I am not actually looking for checking the project to see what's there to fix or if it's anything there to fix. We have been developing from phase 0 to phase 6, and I'm pretty sure that most of the files have a high professional standard and are well developed."

The project was developed phase by phase with the `/verify` command running 5 verification agents (best-practices-enforcer, security-auditor, hallucination-detector, code-reviewer, test-generator) after each phase. The code is believed to be high quality.

**The REAL purpose is a three-way comparison:**

1. **What the spec says should exist** -- The project specification (`SIOPV_Propuesta_Tecnica_v2.txt`, 806 lines) defines what was planned. Every requirement needs to be checked: is it in the code?

2. **What actually exists in the code** -- The full inventory of 188 project files. Many of these implement spec requirements. Some go beyond the spec.

3. **What exists beyond the spec** -- During development, the team added security hardening, resilience patterns, DLP layers, circuit breakers, rate limiters, and other professional additions that were NOT in the original spec. These are STRENGTHS that add value and must be cataloged.

**Additional purposes:**

- **Stale/orphaned items:** Files, libraries, or imports that were relevant during early development but are now unused because the project evolved past them. Even if they don't break anything, they could be dead weight or a vulnerability surface.

- **Importance rating:** For anything missing from the spec, rate its importance 0-100. Is it a must-have for the thesis? Or a future enhancement?

- **Obsolete spec items:** If the project improved or replaced something from the spec, note that the original spec item is superseded and explain why.

The user wants this to feed into the orchestrator briefing for phases 7-8 development. The audit gives complete awareness of what exists before building the remaining phases.

### The "Incidental Findings" Nuance

The user explicitly clarified the relationship between scanning and bug-finding:

> "If while scanning everything the agent realized that there is a bug or there is something broken or any of this matters, that is also an addition that we can add."

This means: agents should NOT actively hunt for bugs. Their primary job is spec mapping and inventory. BUT if during their scanning they notice something obviously broken -- a broken import, a dead link, a clear vulnerability, a stale library -- they should note it in an "Incidental Findings" section. The distinction is: **not actively hunting, but not ignoring what they see.** An agent scanning the domain layer for spec coverage might notice that a function references a non-existent module. That goes into incidental findings. But the agent does NOT run security scanners or write test cases -- that is a different activity.

---

## 4. THE FIVE STAGES: WHAT THEY ARE AND WHY

The audit evolved significantly during the planning conversation. It started as a simple "Batch 0 discovery" and grew into a comprehensive five-stage project. The user drove this expansion, wanting thoroughness over speed.

### How the stages evolved

The conversation started with "Phase A" and "Phase B" names, but the user pointed out that "phase" conflicts with SIOPV's own Phase 0-8 system. Multiple alternative terms were proposed (Stage, Track, Sprint, Wave, Cycle, Layer). The user chose **Stage** because it is clear, sequential, and does not clash with any existing term in the project.

The user initially proposed five numbered stages, then renamed Stage 5.

### Final stage definitions

| Stage | Full Name | Purpose |
|-------|-----------|---------|
| **STAGE-1** | Discovery and Spec Mapping | Scan the entire project. Read the spec. Produce a three-way comparison: what's implemented per spec, what's missing from the spec (with 0-100 importance rating), what's been added beyond the spec. Catalog stale/orphaned items. Note incidental findings. |
| **STAGE-2** | Hexagonal Quality Audit | Deep architecture audit. Check layer separation integrity. Verify adapters don't leak into domain. Check port/adapter compliance. Verify DI wiring. Assess inter-layer communication patterns. Check end-to-end data flow through the graph. |
| **STAGE-3** | SOTA Research and Deep Scan | Go online and research state-of-the-art techniques (March 2026) for every SIOPV component: LangGraph patterns, DLP/Presidio best practices, vulnerability classification, OpenFGA patterns, Streamlit HITL, output generation. Then compare the current implementation against these best practices. |
| **STAGE-4** | Claude Code Configuration Setup | Based on findings from Stages 1-3, create the complete Claude Code configuration for `~/siopv/`: agent definitions, hook scripts, rules files, settings.json, contexts directory, skills. This is when development moves from meta-project to SIOPV directly. |
| **REMEDIATION-HARDENING** | Apply Corrections and Fixes | Apply all corrections identified in Stages 1-4. This stage is fundamentally different from Stages 1-4 (code writing vs. scanning/reading). Gets its own orchestrator briefing. Designed AFTER Stages 1-4 complete, based on their findings. |

### Why Stage 4 comes after Stage 3

This was explicitly discussed. The user initially considered having Claude Code setup as "Stage 3.5" (between research and fixes), but the decision was:

- **After Stage 1** -- too early. Don't know the architecture's health or SOTA best practices yet.
- **After Stage 2** -- still too early. Have architecture picture but not latest SOTA for Claude Code itself.
- **After Stage 3** -- perfect. Know: (1) what the project contains, (2) where architecture is strong/weak, (3) what March 2026 best practices are. Can write Claude Code config with full awareness.

---

## 5. NAMING CONVENTIONS AND WHY THEY MATTER

The user was very deliberate about terminology to avoid confusion. Four distinct terms are used:

| Term | Scope | Examples |
|------|-------|---------|
| **Phase** | SIOPV project phases ONLY | Phase 0 (Setup), Phase 1 (Ingesta), ..., Phase 8 (Output) |
| **Stage** | The audit/modernization stages | STAGE-1 (Discovery), STAGE-2 (Hexagonal), ..., STAGE-4 (Claude Code), REMEDIATION-HARDENING |
| **Round** | Sequential units within a stage | Round 1 (first batch of agents), Round 2 (second batch), Round 3 (summarizer) |
| **Batch** | Parallel groups within a round | Batch A (agents 1-4 running simultaneously) |

**Why this matters:** The SIOPV project already uses "Phase" extensively. Using "Phase" for the audit would create confusion. "Wave" was considered but was already used in the meta-project for agent execution waves. "Stage" was clean and unambiguous.

"Round" was chosen for within-stage sequential units because it implies orderly progression. "Batch" was chosen for parallel groups because it implies simultaneous processing.

---

## 6. DIRECTORY STRUCTURE AND FILE NAMING

### Root Directory

The main audit directory will be created inside `~/siopv/`. The name follows the user's requirements:
- Human-readable timestamp with dots (NOT colons, because colons are invalid in filenames)
- Long descriptive name (10-15 words)

```
~/siopv/2026-03-09_HH.MM.SS_siopv-comprehensive-audit-scanning-and-modernization/
```

The exact timestamp will be set when the directory is created. The HH.MM.SS uses dots as separators because colons are not valid in directory names on macOS/Linux.

### Internal Structure

```
~/siopv/2026-03-09_HH.MM.SS_siopv-comprehensive-audit-scanning-and-modernization/
+-- README.md
+-- stages-1-to-4-discovery-research-and-configuration/
|   +-- README.md
|   +-- shared/
|   |   +-- team-template.md
|   |   +-- report-template.md
|   |   +-- agent-persona-scanner.md
|   |   +-- agent-persona-researcher.md
|   |   +-- agent-persona-summarizer.md
|   |   +-- agent-persona-orchestrator.md
|   +-- stage-1-discovery-and-spec-mapping/
|   |   +-- stage-1-overview.md
|   |   +-- orchestrator-briefing.md
|   |   +-- agent-definitions/
|   |   +-- reports/
|   +-- stage-2-hexagonal-quality-audit/
|   |   +-- (same structure)
|   +-- stage-3-sota-research-and-deep-scan/
|   |   +-- (same structure)
|   +-- stage-4-claude-code-configuration-setup/
|       +-- (same structure)
+-- remediation-hardening-apply-fixes-and-hardening/
    +-- README.md (placeholder)
    +-- orchestrator-briefing.md (placeholder -- designed after stages 1-4)
    +-- agent-definitions/
    +-- reports/
```

### File Naming Convention

All files follow: `NNN_YYYY-MM-DD_HH.MM.SS_descriptive-name-ten-to-fifteen-words.md`

- `NNN` = zero-padded sequence number within the stage (001, 002, 003...)
- `YYYY-MM-DD` = date
- `HH.MM.SS` = time with dots (human readable, filesystem safe)
- `descriptive-name` = 10-15 word kebab-case description

Example: `001_2026-03-09_14.30.45_spec-extractor-requirements-checklist-from-project-specification.md`

**Why sequential numbering works here:** Unlike the meta-project (which uses timestamps only to avoid race conditions), within a stage the orchestrator assigns sequence numbers at spawn time. This gives a clear reading order for summarizers and examiners.

**Why dots in timestamps:** The user specifically said timestamps must be "human-readable" -- not just a bunch of digits run together like `20260309143045`. The format `14.30.45` is readable as "14 hours, 30 minutes, 45 seconds." Colons (`14:30:45`) would be ideal but are invalid in filenames on macOS.

---

## 7. TEAM DESIGN: THE REUSABLE TEMPLATE

The same team template applies to STAGE-1, STAGE-2, STAGE-3, and STAGE-4. What changes between stages is the briefing file content and the specific agents spawned. The structure is identical.

### Team Lifecycle

1. **claude-main** creates a team with `TeamCreate` and spawns an orchestrator via `Agent`.
2. claude-main names itself "claude-main" in the team so the orchestrator can send messages back.
3. claude-main delegates everything to the orchestrator. **claude-main does NOT manage agents, does NOT read code, does NOT do analysis.** It is a coordinator only.
4. The orchestrator reads its briefing file and manages all rounds.
5. The orchestrator spawns rounds of **4-6 parallel agents maximum** per batch.
6. Each agent operates with a **clean context window** (fresh context, no inherited conversation).
7. Agents write their reports to disk, return a condensed summary (1,000-2,000 tokens) to the orchestrator, and **terminate** (shut down completely).
8. A **wave summarizer** is spawned to read ONLY that round's reports (not raw agent conversations) and produce a round summary.
9. The orchestrator sends the round summary to claude-main via `SendMessage`.
10. **Human checkpoint:** The human reviews and approves the next round or requests corrections.
11. After all rounds complete, a **final summarizer** reads ONLY round summaries (NOT individual agent reports) and produces the stage deliverable.
12. Human approves the stage deliverable.

### Why Agents Shut Down After Each Round

This is not just a preference -- it is grounded in the research findings:

- Fresh context by default maximizes per-agent performance (research finding AH-09)
- Persistent agents accumulate context rot -- the progressive degradation of instruction compliance as conversation length grows
- File-based reports survive agent termination because they exist outside context (finding CS-06)
- A clean session with a good prompt outperforms a long session with accumulated corrections (finding CP-ANT-03)

### Why 4-6 Agents Per Batch

This is the practical limit for token budget management. Multi-agent systems consume up to 15x more tokens than single-agent chat (finding MA-05). More than 6 parallel agents creates coordination overhead and token costs that become unwieldy.

### The Human Checkpoint Pattern

The user wants to see results between rounds. This is not optional. The orchestrator MUST pause after each round's summarizer completes and wait for human approval before proceeding. The pattern is:

```
Round 1 agents spawned (4-6 parallel) -> agents report and terminate
-> Round 1 wave summarizer consolidates reports
-> Orchestrator sends summary to claude-main
-> [HUMAN CHECKPOINT] -- human reviews, approves next round
-> Round 2 agents spawned...
```

---

## 8. AGENT BEHAVIORAL CONTROL: THE FULL DESIGN

Two research agents were spawned on 2026-03-09 to investigate best practices for agent behavior. Their reports are saved in the research directory (files 001 and 002). Key findings were extracted into checkpoint files (003 and 004, containing 132 total checkpoints). These were synthesized into the dual-purpose document (file 005).

### The 60% Context Soft Limit

The initial proposal was a hard 50% context limit. The user changed this to a **soft 60% limit** based on the realization that compaction hooks can save state. The reasoning:

> "I think we can make it 60%, but flexible, so that if the agent still needs to continue a little bit longer, we can make it last longer."

The 60% is a TARGET, not a wall. Agents should aim to complete within 60% of context. If they go above, the pre-compaction hook (which triggers at ~95%) saves their state to disk. But the design goal is lean agents that finish well within 60%.

### Pre-Compaction and Post-Compaction Hooks

- **Pre-compaction hook:** A shell script that triggers when compaction is about to happen. It saves the agent's current state (what files have been read, what findings have been recorded, what remains in the todo list) to a persistent file on disk. This is code, not a suggestion -- it executes automatically.

- **Post-compaction hook:** A `SessionStart` hook that forces the agent to read the saved state file and resume from where it left off. This is the safety net that makes the 60% limit "soft" rather than "hard."

**Critical nuance the user identified:** Hooks control what happens around tool calls. They CANNOT force the model to think in a certain way. But when the model loads up everything that it's supposed to load (via the post-compaction hook reading state files), it will naturally follow the loaded context. The hook ensures the right information is in the context window; the persona and rules guide how the model uses that information.

### Behavioral Personas / Personality Files

The user and assistant agreed that agent personas are different from rules or instructions. A persona is a **foundational framing** that conditions the model from the first token -- like the agent's "DNA."

**What works (research-backed):**
- Direct persona assignment ("You are an X") outperforms imagination framing ("Imagine you are...")
- The 4-element pattern: identity + domain expertise + constraints + output format
- Explicit "You are NOT" constraints prevent persona leakage (Claude infers personality traits beyond specification; a "security auditor" may start suggesting fixes unless told "DO NOT fix code")
- Personas control style, format, and tone -- but NOT factual accuracy or reasoning quality

**What does NOT work:**
- Persona alone does not control accuracy -- must combine with task constraints
- Personas without explicit constraints leak inferred behaviors
- "Imagine you are..." framing is consistently worse

### The 150-Instruction Ceiling and 20-Rule Sweet Spot

Research finding: total instructions across all loaded contexts (system prompt + CLAUDE.md + rules + skills) should stay under 150. Beyond this threshold, compliance degrades measurably.

**Per agent:** Maximum 20 core rules in the body. Maximum 200 lines total for the agent body.

**The user initially misunderstood this** -- thinking it meant 20 rules total across the entire project. The assistant clarified: it is 20 rules **per agent definition file**. The dual-purpose document can have 100+ checkpoints. Each individual agent just loads ~20 of the most relevant rules for its specific task. The rest is handled by hooks (100% enforcement) and tool restrictions (100% enforcement).

**Pruning heuristic:** Remove any rule that does not change behavior when removed. If removing a rule causes no observable difference, it wastes attention budget.

### "Rules Are Requests, Hooks Are Laws"

This is a key design principle from the research:

- **Prompt-based rules** (in agent body, CLAUDE.md, rules files): ~80% compliance. The model might ignore them under pressure, when context is long, or when they conflict with strong patterns in the training data.
- **Hooks** (PreToolUse, PostToolUse, etc.): ~100% compliance because they are deterministic shell scripts that execute BEFORE/AFTER tool calls. They cannot be overridden by the model.
- **Tool restrictions** (allowlists in frontmatter): ~100% compliance because the tool simply is not available.

**Practical implication:** For any constraint that MUST be enforced (security, read-only behavior, report format), use hooks or tool restrictions. For constraints that should USUALLY be followed (style, analysis depth, report quality), use rules.

### PreToolUse: The Only Blocking Hook

Of all hook events, **PreToolUse is the only one that can block a tool call.** Two blocking mechanisms:
1. Exit code 2 from the shell script
2. JSON output with `permissionDecision: "deny"`

Other hooks (PostToolUse, SessionStart, Stop, etc.) can observe and react but cannot prevent actions.

### Anti-Improvisation Constraints

The user was very specific: agents should NOT improvise, create workarounds, or find their own solutions. They should follow their instructions exactly.

Techniques from research:
- **Explicit DO NOT list:** 5 items minimum per agent. Example: "DO NOT modify files outside your scope, DO NOT skip files because they look fine, DO NOT speculate about business impact, DO NOT suggest fixes when your role is analysis, DO NOT proceed without updating your todo list."
- **Todo list recitation:** Agent rewrites a todo list after each step, pushing the global plan into the high-attention end zone of the context window.
- **Scoped tool access:** The most reliable anti-improvisation mechanism. An agent without the Write tool cannot create files regardless of its reasoning.
- **maxTurns limit:** Prevents runaway execution. Scanner: 25 turns. Researcher: 30 turns. Summarizer: 15 turns. Orchestrator: 50 turns.
- **Fresh context between unrelated tasks:** A clean session with a better prompt outperforms a long session with accumulated corrections.

### Context Positioning Strategy

**Lost-in-the-middle effect:** LLMs pay most attention to tokens at the START and END of the context window. Performance drops >30% when key information sits in the middle.

**Strategy for agent bodies:**
1. Front-load the 3 most critical rules at the TOP of the agent body (first 10 lines)
2. Full workflow in the middle
3. Boundaries and DO NOT list
4. Output format
5. **Repeat the #1 most critical rule at the very END** (last 3 lines)

Use emphasis markers (`IMPORTANT`, `YOU MUST`, `NEVER`) sparingly -- only on the top 20 rules. Overuse dilutes the effect.

---

## 9. WHAT AGENTS ASSESS: THE EXACT SCOPE

### Primary Assessment (Active Goal)

1. **Spec coverage:** For every requirement in the project specification, check if it exists in the code. If it does, note which files implement it. If it does not, rate its importance 0-100 and classify: must-have for thesis vs. future enhancement.

2. **Spec items made obsolete:** If the project improved or replaced something from the spec, note that the original spec item is superseded. Explain why the new approach is better. Nothing is deleted from the assessment -- it is documented as "superseded by [improvement]."

3. **Beyond-spec additions:** Catalog everything in the code that is NOT in the original spec. These are strengths: resilience patterns, security hardening, DLP layers, circuit breakers, rate limiters, etc. They add value and demonstrate that the project exceeds the specification.

4. **Stale/orphaned files:** Files, libraries, or imports that were relevant during early development but are now unused. Even unused libraries can be a vulnerability surface.

5. **Quality level:** For everything that exists, assess its quality. Not "is it broken?" but "how close to March 2026 SOTA is it?" This is an assessment, not a debugging session.

### Incidental Findings (Passive -- See It, Note It)

This nuance was explicitly discussed and clarified by the user. Agents should NOT actively hunt for bugs, run security scanners, or write test cases to find issues. That is a different activity (covered partially by STAGE-2 and STAGE-3).

However, if during the normal course of scanning files for spec mapping, an agent notices something obviously wrong -- a broken import, a dead reference, a clear vulnerability, an unused variable that shadows something important -- it should note this in an "Incidental Findings" section of its report.

The analogy: if you are inventorying the contents of a house and you notice a broken window, you note "broken window in bedroom" even though your job is inventory, not home inspection. You do NOT go looking for broken windows -- but you do not ignore them either.

---

## 10. STAGE-1 SPECIFIC AGENT DESIGN

Stage 1 uses the "Hybrid contract mapping" strategy (Option C from the planning discussion):

### Round 1: Parallel Agents (5 agents)

**Agent A -- Spec Extractor:**
- Reads ONLY the project specification file (`~/sec-llm-workbench/docs/SIOPV_Propuesta_Tecnica_v2.txt`, 806 lines)
- Produces a numbered requirements checklist organized by phase (0-8)
- Every requirement gets an ID like `SPEC-P2-03` (Phase 2, requirement 3)
- Output: structured checklist with IDs, descriptions, and phase assignments

**Agent B1 -- Project Config and Infrastructure Scanner (~15 files):**
- Scope: `pyproject.toml`, `docker-compose.yml`, `settings.py`, `di/`, `logging/`, `resilience/`, `middleware/`, `.env*`, `.pre-commit-config.yaml`, `ci.yml`
- For each file: purpose, what spec requirement it implements (or if it is beyond-spec), quality assessment, incidental findings

**Agent B2 -- Domain Layer Scanner (~20 files):**
- Scope: `domain/entities/`, `domain/value_objects/`, `domain/services/`, `domain/authorization/`, `domain/privacy/`, `domain/oidc/`, `domain/constants.py`
- Same assessment approach as B1

**Agent B3 -- Application Layer Scanner (~20 files):**
- Scope: `application/orchestration/` (graph, nodes, state, edges, utils), `application/use_cases/`, `application/ports/`, `application/services/`
- Same assessment approach

**Agent B4 -- Adapters and Interfaces Scanner (~25 files):**
- Scope: `adapters/dlp/`, `adapters/external_apis/`, `adapters/authorization/`, `adapters/authentication/`, `adapters/ml/`, `adapters/vectorstore/`, `interfaces/cli/`, `interfaces/dashboard/` + stub directories assessment
- Same assessment approach

### Round 2: Comparator (1 agent)

**Agent C -- Comparator:**
- Reads Agent A's spec checklist + B1-B4's tagged reports
- Cross-references: which spec requirements are marked as implemented? Which are missing? Which are superseded?
- Produces the three-way comparison: implemented, missing (with 0-100 importance), beyond-spec
- Flags any inconsistencies between scanner reports

### Round 3: Final Summarizer (1 agent)

**Agent D -- Final Summarizer:**
- Reads A's checklist + B1-B4's reports + C's comparison
- Produces the consolidated STAGE-1 deliverable: the complete map of SIOPV's current state
- This file is the primary input for STAGE-2 planning

### Why 4 B-Agents Instead of 2

The user asked: "Do you think just splitting into B1 and B2 agents is going to be enough?" The answer was no. With 188 files, two agents would each need to read 40-50 files, risking context exhaustion. Splitting by architectural layer (config/infrastructure, domain, application, adapters/interfaces) keeps each agent to ~15-25 files -- well within safe context limits. The user explicitly approved this split.

---

## 11. THE EVERYTHING-CLAUDE-CODE GITHUB ANALYSIS

The user shared a link to `https://github.com/affaan-m/everything-claude-code` -- a massive open-source project (50K+ stars, 65+ skills, 16 agents, 40+ commands) for Claude Code configuration.

### Assessment: Should We Install It?

**No.** The reasons:
1. It is generic and multi-language (TypeScript, Python, Go, Java, C++, Swift) -- SIOPV only needs Python
2. It has extensive overhead for features SIOPV does not need (package manager detection, PM2 orchestration, Node.js scripts, plugin/marketplace system)
3. SIOPV's hexagonal architecture needs domain-specific rules that a generic framework cannot provide
4. The security model is different -- SIOPV handles CVE data, has DLP/Presidio, and needs specific security rules

### What Was Adopted (Ideas, Not Code)

| Feature | What We Take | Why |
|---------|-------------|-----|
| Separate rules per concern | Instead of one massive rules file, have `hexagonal.md`, `security.md`, `testing.md`, `llm.md`, `data-flow.md`, `error-handling.md`, `dependencies.md` | Cleaner organization, agents load only relevant rules |
| Contexts directory | Mode-switching files: `scanning.md`, `developing.md`, `reviewing.md`, `fixing.md` | Different modes need different tool access and rules |
| Memory persistence hooks | Pre/post compaction hooks saving state to disk | Survive context loss across compaction |
| Strategic compaction suggestions | Hook that detects context growth and suggests good compaction points | Proactive context management |
| Verification loops with checkpoints | Micro-verification during development (not just /verify at end) | Catch issues earlier, smaller fix surface |
| Report template enforcement | Structural validation of agent reports | Consistency across all agents |

### What Was Skipped

- PM2 orchestration (not relevant)
- Node.js scripts (pure Python project)
- Multi-language rules (Python only)
- Package manager detection (we use uv exclusively)
- Plugin/marketplace system (unnecessary complexity)

---

## 12. CLAUDE CODE FEATURES PLANNED FOR STAGE-4

STAGE-4 is when the Claude Code configuration gets built inside `~/siopv/`. These are the specific features planned:

### Contexts Directory
- `scanning.md` -- loaded when agents are in read-only audit mode
- `developing.md` -- loaded when agents are writing code (phases 7-8)
- `reviewing.md` -- loaded when agents are reviewing code
- `fixing.md` -- loaded when agents are applying fixes (REMEDIATION-HARDENING)

### Rules Per Concern
Individual rule files, each focused on one concern:
- `hexagonal.md` -- hexagonal architecture rules (layer separation, dependency direction)
- `security.md` -- security rules (no hardcoded credentials, input validation)
- `testing.md` -- testing standards (coverage floors, test naming)
- `llm.md` -- LLM-specific rules (prompt safety, CRAG judge patterns)
- `data-flow.md` -- data flow rules (state management, TypedDict patterns)
- `error-handling.md` -- error handling patterns
- `dependencies.md` -- dependency management rules

### Hooks
- Pre-compaction hook: saves current state to disk
- Post-compaction hook: forces reload of saved state
- Strategic compaction suggestions: detects context growth, suggests compaction points
- PreToolUse blocking hooks for security (block dangerous commands)
- PostToolUse hooks for auto-formatting (run ruff after edits)

### Context7 Local JSON Cache
- Cache file at `~/siopv/.context7-cache/cache.json`
- Agents check the cache BEFORE calling the Context7 API
- Avoids duplicate API calls for the same library documentation
- Cache entries have TTL (time-to-live) to prevent staleness

### Micro-Verification
Instead of running `/verify` only at the end of a phase:
- After each node/module is written: quick check (ruff + mypy + pytest on that file only)
- After a logical group of components is done: focused verification
- Full `/verify` (5 agents): only at the end of the complete phase

### Continuous Learning / Pattern Extraction
For phases 7-8 development:
- After each verification cycle, extract patterns that failed
- Add them to rules files so the same mistake is not repeated
- This creates a feedback loop: develop -> verify -> extract lessons -> develop better

### Hook Runtime Controls
Environment variables to enable/disable specific hooks:
- Useful during development when a hook might be too strict
- Can be toggled without modifying the hook script itself

---

## 13. REMEDIATION-HARDENING: WHY IT IS SEPARATE

The user explicitly decided that what was originally "STAGE-5: Apply corrections and fixes" should be separated from STAGE-1 through STAGE-4 and given a different name and structure. The reasons:

1. **Different nature:** STAGE-1 through STAGE-4 are scanning/reading/analyzing activities. REMEDIATION-HARDENING is code writing. The agent types, tool access, verification requirements, and risk profiles are fundamentally different.

2. **Cannot be designed until Stages 1-4 complete:** The scope of REMEDIATION-HARDENING depends entirely on what Stages 1-4 find. Designing it upfront would be speculative. It gets its own orchestrator briefing file, written AFTER all scanning results are in.

3. **Different orchestrator:** The REMEDIATION-HARDENING orchestrator needs write-capable agents, verification pipelines, and the full `/verify` workflow. This is much more complex than the read-only orchestrators for Stages 1-4.

4. **Separate project/directory:** REMEDIATION-HARDENING lives in its own subdirectory (`remediation-hardening-apply-fixes-and-hardening/`) with placeholder README and briefing files that get filled in later.

The name "REMEDIATION-HARDENING" was the user's choice -- combining both concepts (fixing what is wrong AND hardening what is good to be better).

---

## 14. RESEARCH CONDUCTED AND FILES CREATED

All research files are in `~/siopv/.ignorar/agent-persona-research-2026-03-09/`:

| File | What It Contains | Status |
|------|-----------------|--------|
| `001_claude-code-agent-persona-guardrails-behavioral-control.md` | Research report from Agent 1: Claude Code-specific agent personas, hooks, rules, frontmatter fields, tool restrictions, subagent mechanics | COMPLETED |
| `002_llm-agent-behavioral-control-guardrails-techniques.md` | Research report from Agent 2: Cross-platform LLM behavioral control science, anti-drift, context rot, guardrail frameworks, prompt engineering | COMPLETED |
| `003_checkpoints-extracted-from-claude-code-report.md` | 58 checkpoints extracted from report 001 by a checkpoint extraction agent | COMPLETED |
| `004_checkpoints-extracted-from-llm-behavioral-report.md` | 74 checkpoints extracted from report 002 by a checkpoint extraction agent | COMPLETED |
| `005_dual-purpose-technical-record-and-checklist-for-agent-design.md` | 7-part document synthesizing all 132 checkpoints into 15 design decisions (DD-001 to DD-015), 4 persona templates, stage architecture, and 32 implementation checklist items. Serves dual purpose: (a) technical record for thesis examiners, (b) checklist for agent design | COMPLETED |
| `006_comprehensive-briefing-handoff-file-for-continuation-after-clear.md` | THIS FILE | BEING CREATED |

### About the Dual-Purpose Document (File 005)

The user explicitly requested that this document serve TWO purposes:

1. **Record for examiners:** The thesis examiners will read these files. They must show methodological rigor -- what was researched, what sources were consulted, what decisions were made and why, backed by specific empirical findings.

2. **Checklist for implementation:** When Claude creates the agents, this document provides a structured checklist of everything that must be implemented. Each design decision (DD-001 through DD-015) has a checkbox.

The user initially wanted just a record for examiners. Claude proposed the dual-purpose approach, arguing that without a checklist, details from the research could be missed during implementation (especially after a `/clear` when the conversation context is gone). The user agreed to the dual-purpose approach.

---

## 15. WHAT HAS NOT BEEN CREATED YET

The following items exist only as plans. They have NOT been created on disk:

1. **The main audit directory structure** -- `~/siopv/2026-03-09_HH.MM.SS_siopv-comprehensive-audit-scanning-and-modernization/` does not exist yet. Only the research directory (`~/siopv/.ignorar/agent-persona-research-2026-03-09/`) exists.

2. **Stage subdirectories** -- `stage-1/`, `stage-2/`, etc. do not exist.

3. **Shared files** -- `team-template.md`, `report-template.md`, persona files -- not created.

4. **Orchestrator briefing files** -- Not created for any stage.

5. **Agent definition files** -- Not created in `.claude/agents/`.

6. **Hook scripts** -- `block-write-commands.sh`, `block-dangerous-commands.sh`, `run-linter.sh` -- not created.

7. **Rules files** -- `scanner-read-only.md`, `report-template.md`, `anti-improvisation.md` -- not created.

8. **The STAGE-1 team** -- Not spawned. No agents have been launched for the actual audit.

---

## 16. USER PREFERENCES AND NON-NEGOTIABLE REQUIREMENTS

These were stated explicitly during the conversation and must be followed:

### Quality Standard
The user said: "I want everything to be at a 9.5/10 professional level" and "state-of-the-art March 2026." The project is a master's thesis -- it must demonstrate professional-grade engineering.

### Overhead Tolerance
The user explicitly said: **"I don't care about overhead."** Precision and robustness over speed. If more agents are needed, spawn more agents. If the process takes longer but produces better results, that is acceptable.

### No Compaction for Agents
Agents should ideally never compact. The 60% soft limit with pre-compaction hooks is a safety net, not a design target. Lean agents that finish within 60% are the goal.

### Human Checkpoints Are Mandatory
Between every round, the human must see results and approve. This is NOT optional and NOT something the orchestrator can skip "because everything looks fine."

### Everything in Persistent Files
Nothing should exist only in agent context. Every finding, every report, every decision goes to disk. If an agent terminates unexpectedly, the work done so far is not lost.

### Thesis Examiners Will Read These Files
The reports, the dual-purpose document, the audit results -- all of these may be shown to thesis examiners. They must demonstrate:
- Methodological rigor (not ad-hoc scanning)
- Traceability (requirement IDs, file paths, evidence)
- Completeness (nothing skipped or glossed over)
- Professional presentation (structured, consistent, well-organized)

### The User's Communication Style
- Spanish or English, both accepted
- Direct and concise
- Does not want to be asked for confirmation on standard tasks
- Will interrupt if Claude goes off-track (happened multiple times in this session)
- Expects Claude to investigate first rather than guess

---

## 17. NEXT STEPS: EXACT EXECUTION ORDER

After the user does `/clear` and reads this briefing file, the execution order is:

### Step 1: Create the Directory Structure
Create the main audit directory and all subdirectories as specified in Section 6.

### Step 2: Create Shared Files
Write the team template, report template, and agent persona files in the `shared/` directory. These are based on the templates in file 005 (Part 5 and Part 6) but refined with the specific SIOPV context from this briefing.

### Step 3: Create the STAGE-1 Orchestrator Briefing
Write the complete briefing file for the STAGE-1 orchestrator. This includes:
- The exact round plan (Round 1: A + B1-B4, Round 2: C, Round 3: D)
- Specific file assignments for each B-agent (which files in which directories)
- The spec file path for Agent A
- Report output paths for each agent
- The human checkpoint protocol
- The shut-down-after-round protocol

### Step 4: Spawn the STAGE-1 Team
Use `TeamCreate` to create the "siopv-discovery" team, then spawn the orchestrator with the briefing file. The orchestrator takes over from there.

### Step 5: Wait for STAGE-1 Results
Claude-main waits for the orchestrator to send round summaries and the final STAGE-1 deliverable.

### Steps 6-8: Stages 2-4
Repeat the pattern: create briefing, spawn orchestrator, wait for results, human approval, proceed.

### Step 9: Design REMEDIATION-HARDENING
Based on all findings from Stages 1-4, design the REMEDIATION-HARDENING orchestrator briefing.

### Step 10: Execute REMEDIATION-HARDENING
Apply fixes and hardening.

### Step 11: Begin Phases 7-8 Development
With the full audit complete and the Claude Code configuration set up in `~/siopv/`, begin developing Phase 7 (Streamlit HITL) and Phase 8 (Jira + PDF output).

---

## APPENDIX A: FULL LIST OF AGREED-UPON ITEMS (CHECKLIST FORMAT)

This is the compressed checklist from the conversation, kept here for quick reference. The full explanations are in the sections above.

### Project Context
- [x] SIOPV path: `~/siopv/`
- [x] 188 project-relevant files (170 .py + 18 config)
- [x] Phases 0-6 completed, 7-8 pending
- [x] ~10 days to thesis deadline
- [x] Moving from meta-project to developing in `~/siopv/` directly

### Naming
- [x] "Phase" = SIOPV only (0-8)
- [x] "Stage" = audit stages (STAGE-1 to STAGE-4 + REMEDIATION-HARDENING)
- [x] "Round" = sequential within a stage
- [x] "Batch" = parallel within a round

### Stages
- [x] STAGE-1: Discovery and spec mapping
- [x] STAGE-2: Hexagonal quality audit
- [x] STAGE-3: SOTA research and deep scan
- [x] STAGE-4: Claude Code configuration setup
- [x] REMEDIATION-HARDENING: Apply corrections and fixes (separate, designed later)

### Team Design
- [x] claude-main delegates to orchestrator, stays hands-off
- [x] 4-6 parallel agents per batch
- [x] 60% context soft limit with pre-compaction hooks
- [x] Agents shut down after each round
- [x] Wave summarizer after each round
- [x] Final summarizer reads only round summaries
- [x] Human checkpoint between every round

### Agent Behavior
- [x] 150-instruction ceiling, 20 rules per agent, 200-line body limit
- [x] "Rules are requests, hooks are laws"
- [x] PreToolUse is the only blocking hook
- [x] 4-element persona: identity + expertise + constraints + output
- [x] Front-load top 3 rules, repeat #1 at end
- [x] Explicit "You are NOT" and "DO NOT" lists
- [x] Todo list recitation after each step
- [x] maxTurns limits: scanner 25, researcher 30, summarizer 15, orchestrator 50

### Assessment Scope
- [x] Spec coverage with 0-100 importance for missing items
- [x] Obsolete spec items (superseded by improvements)
- [x] Beyond-spec additions (strengths catalog)
- [x] Stale/orphaned files
- [x] Incidental findings (NOT active bug hunting)
- [x] Quality level assessment

### File Naming
- [x] Directories: `YYYY-MM-DD_HH.MM.SS_descriptive-name`
- [x] Files: `NNN_YYYY-MM-DD_HH.MM.SS_descriptive-name.md`
- [x] Dots in timestamps (filesystem safe)
- [x] 10-15 word descriptive names

### Research Completed
- [x] File 001: Claude Code agent personas and guardrails
- [x] File 002: LLM behavioral control science
- [x] File 003: 58 checkpoints from report 001
- [x] File 004: 74 checkpoints from report 002
- [x] File 005: Dual-purpose document (15 DDs, 4 personas, 32 checklist items)
- [x] File 006: This briefing file

### Not Yet Created
- [ ] Main audit directory structure
- [ ] Shared template files
- [ ] Orchestrator briefing files (per stage)
- [ ] Agent definition files
- [ ] Hook scripts
- [ ] Rules files
- [ ] Any actual audit agents

---

## APPENDIX B: KEY PATHS REFERENCE

| Item | Absolute Path |
|------|---------------|
| SIOPV project | `/Users/bruno/siopv/` |
| Meta-project | `/Users/bruno/sec-llm-workbench/` |
| Project spec | `/Users/bruno/sec-llm-workbench/docs/SIOPV_Propuesta_Tecnica_v2.txt` |
| Project state | `/Users/bruno/sec-llm-workbench/projects/siopv.json` |
| Research directory | `/Users/bruno/siopv/.ignorar/agent-persona-research-2026-03-09/` |
| File 001 (Claude Code research) | `/Users/bruno/siopv/.ignorar/agent-persona-research-2026-03-09/001_claude-code-agent-persona-guardrails-behavioral-control.md` |
| File 002 (LLM behavioral research) | `/Users/bruno/siopv/.ignorar/agent-persona-research-2026-03-09/002_llm-agent-behavioral-control-guardrails-techniques.md` |
| File 003 (Claude Code checkpoints) | `/Users/bruno/siopv/.ignorar/agent-persona-research-2026-03-09/003_checkpoints-extracted-from-claude-code-report.md` |
| File 004 (LLM behavioral checkpoints) | `/Users/bruno/siopv/.ignorar/agent-persona-research-2026-03-09/004_checkpoints-extracted-from-llm-behavioral-report.md` |
| File 005 (Dual-purpose document) | `/Users/bruno/siopv/.ignorar/agent-persona-research-2026-03-09/005_dual-purpose-technical-record-and-checklist-for-agent-design.md` |
| File 006 (This briefing) | `/Users/bruno/siopv/.ignorar/agent-persona-research-2026-03-09/006_comprehensive-briefing-handoff-file-for-continuation-after-clear.md` |
| Analysis files | `/Users/bruno/sec-llm-workbench/.ignorar/siopv-*.md` (6 files) |
| Audit findings (2026-03-05) | See MEMORY.md in project memory |

---

**END OF BRIEFING FILE**

This document contains everything needed to continue the SIOPV audit and modernization project without asking any questions. The next action is: create the directory structure (Step 1 in Section 17), then proceed sequentially through the remaining steps.
