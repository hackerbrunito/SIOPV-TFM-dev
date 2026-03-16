# STAGE 4.1 — Execution Plan

**Generated:** 2026-03-13
**Orchestrator:** claude-opus-4-6
**Status:** AWAITING HUMAN APPROVAL

---

## ROUND 1 — ONLINE RESEARCH

### Objective
Research current Claude Code best practices up to March 2026. All findings verified online — no training data reliance.

### Agents (4 parallel workers, all claude-sonnet-4-6)

| Agent | Slug | Topic Cluster | Output File |
|-------|------|---------------|-------------|
| R1-A | `r1-agent-definitions-memory` | Agent definition format (frontmatter fields, required fields, model options, valid values), Memory system (`memory: project` vs `memory: user`, MEMORY.md format, auto-memory patterns, memory file structure) | `round1-online-research/{TS}-r1-agent-definitions-memory.md` |
| R1-B | `r1-hooks-settings` | Hook system (all hook types: PreToolUse, PostToolUse, PreCompact, PostCompact, SessionStart, SessionEnd — script format, additionalContext vs blocking, registration), `settings.json` full schema (all valid keys, permissions format, hook registration, model configuration) | `round1-online-research/{TS}-r1-hooks-settings.md` |
| R1-C | `r1-skills-claudemd-workflow` | Skills 2.0 (new format, definition, invocation), CLAUDE.md best practices (structure, `@` references, global vs project level), Workflow methodology (recommended file structure, content patterns) | `round1-online-research/{TS}-r1-skills-claudemd-workflow.md` |
| R1-D | `r1-teams-new-features` | Agent communication and team patterns (TeamCreate, SendMessage, coordination), Any new Claude Code features released in early 2026 (new hooks, new tool types, new settings keys, new agent capabilities) | `round1-online-research/{TS}-r1-teams-new-features.md` |

### Summarization
- After all 4 agents complete: assess total line count
- If < 2,000 lines → 1 summarizer
- If 2,000–5,000 lines → 2 summarizers
- If > 5,000 lines → 3 summarizers
- After summarizers complete → 1 final Round 1 aggregator producing `round1-final-summary.md`

### Round 1 Checkpoint File
`round1-online-research/round1-checkpoint.md`

---

## ROUND 2 — META-PROJECT SCAN

### Objective
Read-only inventory of current Claude Code configuration at meta-project and user levels.

### Agents (2 parallel workers, all claude-sonnet-4-6)

| Agent | Slug | Scope | Output File |
|-------|------|-------|-------------|
| R2-A | `r2-metaproject-scanner` | `/Users/bruno/sec-llm-workbench/.claude/` — all agent definitions, hooks, workflow files, settings.json, rules, docs, skills | `round2-metaproject-scan/{TS}-r2-metaproject-scanner.md` |
| R2-B | `r2-user-level-scanner` | `/Users/bruno/.claude/` — CLAUDE.md, rules, settings.json, memory, projects | `round2-metaproject-scan/{TS}-r2-user-level-scanner.md` |

### Summarization
- 1 summarizer producing `round2-final-summary.md`

### Round 2 Checkpoint File
`round2-metaproject-scan/round2-checkpoint.md`

---

## ROUND 3 — GAP ANALYSIS & COMPARISON

### Objective
Compare Round 2 current state against Round 1 best practices. Single comprehensive gap analysis report.

### Agent (1 worker, claude-sonnet-4-6)

| Agent | Slug | Input | Output File |
|-------|------|-------|-------------|
| R3-A | `r3-gap-analyst` | `round1-final-summary.md` + `round2-final-summary.md` | `round3-gap-analysis/round3-gap-analysis-report.md` |

### Required Sections (from guidelines)
1. What is correct
2. What is stale or incorrect
3. What must be added (new)
4. What must be modified
5. What to DO NOT INCLUDE
6. Directory structure (proposed `siopv/.claude/` tree)
7. User-level changes

### Constraints
- Maximum 500 lines
- Be specific — name every file and every change

### Round 3 Checkpoint File
`round3-gap-analysis/round3-checkpoint.md`

---

## ROUND 4 — TRUTH DOCUMENT PRODUCTION

### Objective
Produce all 11+ truth files for Stage 4.2 implementation.

### Wave A (1 agent, claude-sonnet-4-6)

| Agent | Output File |
|-------|-------------|
| R4-00 | `round4-truth-document/truth-00-directory-structure.md` |

### Wave B (9 agents in parallel, claude-sonnet-4-6)

| Agent | Output File | Dependencies |
|-------|-------------|-------------|
| R4-01 | `truth-01-settings-and-hooks.md` | truth-00 |
| R4-02 | `truth-02-claude-md.md` | truth-00 |
| R4-03 | `truth-03-agent-definitions.md` | truth-00 |
| R4-04 | `truth-04-workflow-files.md` | truth-00 |
| R4-05 | `truth-05-docs-and-rules.md` | truth-00 |
| R4-06 | `truth-06-skills.md` | truth-00 |
| R4-07 | `truth-07-memory.md` | truth-00 |
| R4-08 | `truth-08-user-level.md` | truth-00 |
| R4-11 | `truth-11-compaction-proof-session-continuity.md` | truth-00 |

**Wave B will be split into sub-waves of max 5 agents each:**
- Wave B1: R4-01, R4-02, R4-03, R4-04, R4-05
- Wave B2: R4-06, R4-07, R4-08, R4-11

### Wave C (2 agents in parallel, claude-sonnet-4-6)

| Agent | Output File | Dependencies |
|-------|-------------|-------------|
| R4-09 | `truth-09-cross-file-wiring.md` | All Wave B files |
| R4-10 | `truth-10-verification-checklist.md` | All Wave B files |

### Round 4 Checkpoint File
`round4-truth-document/round4-checkpoint.md`

---

## AGENT SPECIFICATIONS — DETAIL

### Common rules for ALL agents
- Model: `claude-sonnet-4-6`
- Save full output to the specified file path
- Send only a 3–5 line summary via SendMessage back to team lead
- Max 300 lines output per agent
- Max 5 files read per agent
- Complete within 60% context window

### R1 Agent prompts (summary)
- R1-A: Search online for "Claude Code agent definition format 2026", "Claude Code memory system project user", "Claude Code MEMORY.md format". Document all frontmatter fields, required vs optional, valid model values, memory types, memory file structure.
- R1-B: Search online for "Claude Code hooks 2026", "Claude Code settings.json schema", "PreToolUse PostToolUse PreCompact PostCompact SessionStart SessionEnd hook". Document all hook types, registration format, blocking vs non-blocking, additionalContext, settings.json full key list.
- R1-C: Search online for "Claude Code Skills 2.0 format 2026", "Claude Code CLAUDE.md best practices", "Claude Code workflow files structure". Document Skills 2.0 format, CLAUDE.md structure, @ references, global vs project level, workflow patterns.
- R1-D: Search online for "Claude Code TeamCreate 2026", "Claude Code agent teams", "Claude Code new features 2026". Document TeamCreate API, SendMessage patterns, new features, new hook types, new settings keys.

### R2 Agent prompts (summary)
- R2-A: Read and inventory every file in `/Users/bruno/sec-llm-workbench/.claude/` — document path, type, contents summary, sections, patterns.
- R2-B: Read and inventory every file in `/Users/bruno/.claude/` — document path, type, contents summary, sections, patterns.

### R3 Agent prompt (summary)
- R3-A: Read `round1-final-summary.md` and `round2-final-summary.md`. Produce gap analysis with the 7 required sections. Max 500 lines.

### R4 Agent prompts (summary)
- Each R4 agent reads `round3-gap-analysis-report.md` + its specific source materials and produces the truth file per the guidelines Section 7 specifications.

---

## TOTAL AGENT COUNT

| Round | Workers | Summarizers | Aggregator | Total |
|-------|---------|-------------|------------|-------|
| 1 | 4 | 1–3 | 1 | 6–8 |
| 2 | 2 | 1 | 0 | 3 |
| 3 | 1 | 0 | 0 | 1 |
| 4 | 12 (3 waves) | 0 | 0 | 12 |
| **Total** | | | | **22–24** |

---

## HUMAN CHECKPOINTS

1. ✋ **NOW** — Approve this plan before Round 1 begins
2. ✋ After Round 1 final summary — approve before Round 2
3. ✋ After Round 2 final summary — approve before Round 3
4. ✋ After Round 3 gap analysis — approve before Round 4
5. ✋ After Round 4 all truth files — final approval of Stage 4.1

---

*End of execution plan.*
