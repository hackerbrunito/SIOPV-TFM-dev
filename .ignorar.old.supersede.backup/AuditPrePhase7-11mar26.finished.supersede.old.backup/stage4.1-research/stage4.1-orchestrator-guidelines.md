# STAGE 4.1 — Orchestrator Guidelines
# Claude Code Configuration Research & Truth Document

> **Read this file completely before writing your plan or spawning any agent.**
> Generated: 2026-03-13
> Purpose: Authoritative instructions for the Stage 4.1 orchestrator. No improvisation. Follow exactly.

---

## 1. WHAT STAGE 4.1 IS

Stage 4.1 is a **research-only stage**. Nothing is implemented. Nothing is created in `siopv/.claude/`.

**Goal:** Produce a set of truth document files (the "truth document") that Stage 4.2 will use to implement the full Claude Code configuration for the SIOPV project. The truth document must be so precise and complete that Stage 4.2 agents need no additional context beyond their assigned truth file.

**Output directory:** `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/`

---

## 2. INPUT FILES — READ BEFORE WRITING YOUR PLAN

The orchestrator must read all of these before producing its execution plan:

| # | File | Purpose |
|---|------|---------|
| 1 | `/Users/bruno/sec-llm-workbench/.claude/workflow/briefing.md` | Overall project context, SIOPV architecture, known issues |
| 2 | `/Users/bruno/sec-llm-workbench/.claude/workflow/orchestrator-briefing.md` | General orchestration protocol: round structure, aggregation rules, file naming, human checkpoints |
| 3 | `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage3.5/stage3.5-final-reports-summarizer-n-aggregator-for-stage4-input-brief.md` | Aggregated findings from Stages 1, 2, 3 — primary SIOPV context |
| 4 | `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4/2026-03-12-11.56.25-stage4-pre-task-inventory-and-classification-of-meta-project-agents-and-hooks-for-siopv-reuse.md` | Full classification of 23 meta-project agents and 9 hooks (COPY / ADAPT / DO NOT INCLUDE) |
| 5 | `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/team-management-best-practices.md` | Agent team architecture, spawning constraints, communication patterns, anti-patterns |
| 6 | `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/compaction-proof-handoff-best-practices.md` | Session continuity: hook system, handoff file structure, known bugs, SIOPV implementation template |

---

## 3. FOUR ROUNDS — OVERVIEW

| Round | Name | Focus | Output directory |
|-------|------|-------|-----------------|
| 1 | Online Research | Current Claude Code best practices up to March 2026 | `round1-online-research/` |
| 2 | Meta-Project Scan | Current state of meta-project + user-level Claude Code config | `round2-metaproject-scan/` |
| 3 | Gap Analysis & Comparison | Compare Round 1 findings vs Round 2 current state | `round3-gap-analysis/` |
| 4 | Truth Document Production | Produce all truth files for Stage 4.2 | `round4-truth-document/` |

Each round must complete fully before the next round begins. Human approves at each round checkpoint.

---

## 4. ROUND 1 — ONLINE RESEARCH

### Objective
Research current Claude Code best practices, advanced techniques, and new features up to March 2026. Training data is stale — everything must be verified online. Do not rely on training knowledge for any Claude Code feature.

### Key topics to cover (distribute across agents)
- Agent definition format: frontmatter fields, required fields, model options, memory types, valid values as of March 2026
- Hook system: all hook types (PreToolUse, PostToolUse, PreCompact, PostCompact, SessionStart, SessionEnd), script format, `additionalContext` vs blocking behavior, registration in `settings.json`
- `settings.json` full schema: all valid keys, permissions format, hook registration format, model configuration
- Skills 2.0: new format, changes from previous skill format, how skills are defined and invoked
- Memory system: `memory: project` vs `memory: user`, MEMORY.md format, auto-memory patterns, memory file structure
- Workflow methodology: current recommended workflow file structure and content patterns
- Agent communication and team patterns: TeamCreate, SendMessage, agent coordination patterns
- CLAUDE.md best practices: structure, `@` references, what belongs at global vs project level
- Any new Claude Code features released in early 2026 not covered by the above

### Agent count
3–5 parallel research agents. Each agent covers a distinct topic cluster. No two agents cover the same topic.

### Summarization
- Each research agent saves a persistent report to `round1-online-research/`
- After all research agents complete: assess total line count across all reports
  - If total < 2,000 lines: spawn 1 summarizer agent
  - If total 2,000–5,000 lines: spawn 2 summarizer agents, each covering half the reports
  - If total > 5,000 lines: spawn 3 summarizer agents
- After all summarizers complete: spawn 1 final Round 1 aggregator that merges all summaries into one `round1-final-summary.md` in `round1-online-research/`

### Report naming
`{TIMESTAMP}-r1-{agent-slug}.md` — example: `2026-03-13-14.22.00-r1-researcher-hooks-settings.md`

---

## 5. ROUND 2 — META-PROJECT SCAN

### Objective
Inventory and document the current state of Claude Code configuration at:
1. Meta-project level: `/Users/bruno/sec-llm-workbench/.claude/`
2. User level: `/Users/bruno/.claude/`

This is a read-only scan. No files are modified. No files are deleted.

### Agent count
1–2 agents. If the directory structure is large, split: one agent covers meta-project level, one covers user level.

### What each agent documents per file
- Full path
- File type (agent definition / hook / workflow / settings / rules / docs / skill / memory)
- Current contents summary
- Key sections and headings
- Any patterns or conventions used

### Summarization
1 Round 2 summarizer agent producing `round2-final-summary.md` in `round2-metaproject-scan/`

### Report naming
`{TIMESTAMP}-r2-{agent-slug}.md`

---

## 6. ROUND 3 — GAP ANALYSIS & COMPARISON

### Objective
Compare the current state (Round 2) against the March 2026 best practices (Round 1) and produce one comprehensive gap analysis report.

### Input
- `round1-online-research/round1-final-summary.md`
- `round2-metaproject-scan/round2-final-summary.md`

### Agent count
1 dedicated gap analysis agent.

### Output
One file: `round3-gap-analysis/round3-gap-analysis-report.md`

### Required sections in the report
1. **What is correct** — current patterns that match March 2026 best practices, no changes needed
2. **What is stale or incorrect** — current patterns that conflict with March 2026 best practices
3. **What must be added (new)** — features, files, or patterns that exist in March 2026 but are absent from the current config
4. **What must be modified** — current files that need changes but are not wholesale replacements
5. **What to DO NOT INCLUDE** — meta-project files/patterns that exist but should not be carried into SIOPV
6. **Directory structure** — proposed `siopv/.claude/` directory tree, including any new subdirectories identified by research
7. **User-level changes** — what (if anything) needs to change at `~/.claude/`

### Constraints
- Maximum 500 lines. Shorter is better. Every line must earn its place.
- Nothing is optional. If it is new and confirmed by research, it is mandatory.
- Be specific. Vague statements ("improve the hooks") are not acceptable — name the file, name the change.

---

## 7. ROUND 4 — TRUTH DOCUMENT PRODUCTION

### Objective
Produce the complete set of truth document files that Stage 4.2 will implement from. Each file covers one category. Stage 4.2 agents read only their assigned file — each file must be fully self-contained for its category.

### Input
- `round3-gap-analysis/round3-gap-analysis-report.md` — primary input
- All Round 1 and Round 2 final summaries — for detail lookup
- Stage 4 agent/hook catalog (Input File #4 above) — for action tags

### Baseline truth files (mandatory — produce all 11)

| File | Contents |
|------|----------|
| `truth-00-directory-structure.md` | Full `siopv/.claude/` directory tree + `.build/` structure + creation sequence + action tag for every file (`COPY`, `ADAPT`, `NEW`, `DO NOT INCLUDE`) |
| `truth-01-settings-and-hooks.md` | `settings.json` full skeleton + every hook script (file name, trigger event, full script body) + hook registration in `settings.json` |
| `truth-02-claude-md.md` | `CLAUDE.md` full skeleton — all sections, headings, `@` references, contents, what to include vs adapt from meta-project |
| `truth-03-agent-definitions.md` | All agent `.md` files — frontmatter, description, full body, action tag per file, SIOPV-specific substitutions per file |
| `truth-04-workflow-files.md` | All `workflow/*.md` files — file name, sections, headings, full contents per file |
| `truth-05-docs-and-rules.md` | All `docs/*.md` and `rules/*.md` files — file name, sections, headings, full contents per file |
| `truth-06-skills.md` | All skills — `SKILL.md` format per March 2026 Skills 2.0 spec, trigger conditions, full body per skill |
| `truth-07-memory.md` | `memory/MEMORY.md` for SIOPV — structure, initial sections, what carries over from meta-project vs SIOPV-specific |
| `truth-08-user-level.md` | All `~/.claude/` changes — which files to update, what to add or change, what to leave untouched |
| `truth-09-cross-file-wiring.md` | All cross-file dependencies + full SIOPV-specific substitutions list (paths, model names, project names, thresholds) + enforced creation order |
| `truth-10-verification-checklist.md` | Step-by-step self-validation checklist for Stage 4.2 after all files are created |
| `truth-11-compaction-proof-session-continuity.md` | Full implementation spec for SIOPV session continuity: hook scripts (pre-compact.sh, session-start.sh, session-end.sh), CLAUDE.md compact instructions, briefing.md structure, known bug workarounds |

### Additional truth files
If Round 3 uncovers new Claude Code features or patterns that do not fit cleanly into any baseline file, create additional files continuing the numbering sequence: `truth-12-...`, `truth-13-...`, etc. Each new category gets its own file. Never merge new categories into existing baseline files.

### Agent count for Round 4
One agent per truth file, spawned in parallel where there are no dependencies. Exception: `truth-00` (directory structure) must be produced first — all other agents depend on it. `truth-09` (cross-file wiring) must be produced last — it depends on all other files being defined.

Suggested parallel waves:
- **Wave A:** `truth-00` alone (unblocks everything)
- **Wave B:** `truth-01` through `truth-08` + `truth-11` in parallel
- **Wave C:** `truth-09` and `truth-10` in parallel (both depend on Wave B)

### Report naming
Files are named exactly as listed above (no timestamp prefix — these are the final deliverables, not intermediate reports).

---

## 8. ACTION TAGS — DEFINITIONS

Every file listed in the truth document must carry one of these tags:

| Tag | Meaning |
|-----|---------|
| `COPY` | Take from meta-project as-is, copy to SIOPV with path substitutions only |
| `ADAPT` | Take from meta-project as starting point, modify content for SIOPV before use |
| `NEW` | Does not exist in meta-project; create from scratch based on research findings |
| `DO NOT INCLUDE` | Exists in meta-project but must not be carried into SIOPV (meta-project-specific) |

---

## 9. ABSOLUTE RULES

- **Research has priority.** Where online findings conflict with meta-project patterns, follow the research.
- **Meta-project is reference only.** It is not the target. Nothing in `/Users/bruno/sec-llm-workbench/` is modified or deleted under any circumstance.
- **No improvisation.** If an agent is unclear on a decision, it stops and reports to the orchestrator. The orchestrator escalates to the human if needed.
- **No implementation.** Stage 4.1 produces documents only. No files are created in `siopv/.claude/`.
- **All paths are absolute.** No `$HOME`, no relative paths, no `~` in any report or truth file.
- **Model assignment:** Orchestrator uses `claude-opus-4-6`. All worker agents use `claude-sonnet-4-6`. Never use Opus for research or scanning workers — only for the orchestrator itself.
- **Spawning architecture:** The orchestrator does NOT spawn agents directly. It requests spawning via `SendMessage` to the team lead, specifying agent name, model, task, and output path. The team lead (main session) executes all `Agent()` calls.
- **Delegate mode:** The team lead activates delegate mode (Shift+Tab) after spawning the orchestrator. This restricts the team lead to coordination-only tools for the duration of the run.
- **No `/compact` mid-run:** Do not run `/compact` while a round is in progress. Between rounds only: `/rewind → Summarize from here`. After all rounds complete, normal `/compact` is safe.
- **Round checkpoint files:** After each round completes and the final summary is written, the orchestrator writes a `round{N}-checkpoint.md` file to the round's output directory. This file contains: round number, files produced, key findings (max 20 lines), and status (COMPLETE). This file survives compaction and is the source of truth for round state — not the conversation history.
- **Manual compact at 50%:** The team lead monitors context usage in the status bar. Between rounds, if context is at or above 50%, the team lead runs `/compact` before proceeding to the next round. Do not wait for auto-compact at 83.5% — that is too late for safe multi-round recovery. The orchestrator cannot self-monitor context and must never be relied upon to report it.
- **Orchestrator cannot run slash commands.** `/rewind`, `/compact`, `/clear` are human-only commands. The orchestrator requests these from the team lead via `SendMessage`. The team lead (human) executes them.
- **Human approves at every round checkpoint** before the next round begins. Orchestrator's silence is not approval.
- **Every agent saves a persistent report.** No agent produces output only in memory.

---

## 10. HUMAN CHECKPOINT PROTOCOL

After each round completes and the round final summary is written:
1. Orchestrator sends a message to `team-lead` with: round number, files produced, key findings summary (max 20 lines), and explicit request for approval to proceed to the next round
2. Team lead relays the checkpoint to the human and waits for approval
3. Human reads and approves (or requests corrections)
4. Only after explicit human approval does the team lead relay approval to the orchestrator, which then sends the next round's agent specifications via `SendMessage`
5. Team lead spawns next-round agents per the orchestrator's specifications

---

## 11. OUTPUT SUMMARY

At the end of Stage 4.1, the following must exist:

```
stage4.1-research/
├── stage4.1-orchestrator-guidelines.md        ← this file
├── round1-online-research/
│   ├── {TIMESTAMP}-r1-{agent-slug}.md         ← 3-5 research reports
│   ├── {TIMESTAMP}-r1-summarizer-*.md         ← 1-3 summarizer reports
│   └── round1-final-summary.md                ← single round 1 output
├── round2-metaproject-scan/
│   ├── {TIMESTAMP}-r2-{agent-slug}.md         ← 1-2 scan reports
│   └── round2-final-summary.md                ← single round 2 output
├── round3-gap-analysis/
│   └── round3-gap-analysis-report.md          ← single round 3 output (≤500 lines)
└── round4-truth-document/
    ├── truth-00-directory-structure.md
    ├── truth-01-settings-and-hooks.md
    ├── truth-02-claude-md.md
    ├── truth-03-agent-definitions.md
    ├── truth-04-workflow-files.md
    ├── truth-05-docs-and-rules.md
    ├── truth-06-skills.md
    ├── truth-07-memory.md
    ├── truth-08-user-level.md
    ├── truth-09-cross-file-wiring.md
    ├── truth-10-verification-checklist.md
    ├── truth-11-compaction-proof-session-continuity.md
    └── truth-12-...md                         ← additional files if research requires
```
