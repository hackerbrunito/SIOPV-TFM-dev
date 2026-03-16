# Audit Report: SIOPV Skill Files

> **Date:** 2026-03-16
> **Auditor:** skill-auditor agent
> **Reference:** `research-16march2026/01-skill-files-best-practices.md`
> **Scope:** All `.claude/skills/` SKILL.md files in project and global locations

---

## Executive Summary

| Skill File | Lines | Desc Chars | Verdict |
|------------|------:|----------:|---------|
| `verify/SKILL.md` | **1,370** | 93 | **CRITICAL FAIL** — 2.7x over 500-line hard limit |
| `openfga-patterns/SKILL.md` | 310 | 268 | **WARN** — over 100-line best practice; all content is reference material |
| `langraph-patterns/SKILL.md` | 295 | 275 | **WARN** — over 100-line best practice; all content is reference material |
| `presidio-dlp/SKILL.md` | 286 | 285 | **WARN** — over 100-line best practice; all content is reference material |
| `coding-standards-2026/SKILL.md` | 214 | 250 | **WARN** — over 100-line best practice; all content is reference material |
| `siopv-remediate/SKILL.md` | 60 | 265 | **PASS** — well-structured, process-focused |

- **Global skills (`~/.claude/skills/`):** Directory does not exist. No global skills.
- **Legacy commands (`.claude/commands/`):** None found.
- **Total skill count:** 6 — well within the 20-30 recommended limit.
- **Total description budget consumed:** ~1,436 chars of ~16,000 — excellent headroom.

### Overall Assessment

5 of 6 skill files violate the **"Process in SKILL.md, context in reference files"** golden rule. The `verify` skill is a critical offender at 1,370 lines (2.7x the official 500-line max). The 4 "pattern" skills (langraph, openfga, presidio, coding-standards) are pure reference documentation masquerading as skill files — they contain no process steps, only code examples. Only `siopv-remediate` follows best practices.

---

## Per-File Findings

### 1. `verify/SKILL.md` — CRITICAL FAIL

**Lines:** 1,370 (limit: 500 official, 100 community ideal)

#### Structural Breakdown

| Section | Lines | Should Be In SKILL.md? |
|---------|------:|:---:|
| Frontmatter | 1-8 | Yes |
| Usage | 10-19 | Yes |
| EXECUTION MODEL overview | 22-62 | Yes (abbreviated) |
| Output Directory structure | 65-92 | **No** → reference file |
| Pipeline Overview diagram | 96-112 | Yes |
| 3-Tier Hierarchy | 116-133 | Yes (abbreviated) |
| UNIVERSAL AGENT RULES (4 rules) | 136-179 | **No** → reference file |
| SECTION 1: Team-Lead Protocol | 183-253 | Yes (this IS the process) |
| SECTION 2: Orchestrator Protocol | 256-394 | **No** → reference file |
| PRE-WAVE prompt | 333-394 | **No** → reference file |
| WAVE 1 (3 scanner prompts) | 397-579 | **No** → reference file |
| WAVE 1B judge prompt | 583-654 | **No** → reference file |
| WAVE 2 (reviewer + testgen) | 657-754 | **No** → reference file |
| WAVE 3 (fixer prompts) | 758-857 | **No** → reference file |
| WAVE 3B validator prompt | 860-910 | **No** → reference file |
| WAVE 4 (integration + async) | 913-985 | **No** → reference file |
| WAVE 5 (semantic + circular) | 988-1053 | **No** → reference file |
| WAVE 6 (imports + deps) | 1057-1123 | **No** → reference file |
| WAVE 7 config validator | 1126-1161 | **No** → reference file |
| WAVE 8 hex-arch remediator | 1164-1199 | **No** → reference file |
| WAVE 9 smoke test | 1202-1253 | **No** → reference file |
| Wave Timeout Policy | 1256-1266 | **No** → reference file |
| Pass Thresholds table | 1269-1291 | **No** → reference file |
| Post-Wave Actions | 1294-1321 | **No** → reference file |
| JSONL Logging format | 1324-1357 | **No** → reference file |
| Marker System | 1360-1369 | Borderline (keep as 2-line summary) |

**~1,100 lines (80%) should be extracted** to reference files.

#### Specific Issues

1. **P0 — 1,370 lines (2.7x hard limit):** When this skill is triggered, ~55KB of text is injected into context. This wastes tokens and may degrade performance on smaller models.

2. **P0 — All 14+ agent prompt templates embedded inline:** Each wave's agent prompt (lines 347-1253) is a complete, multi-paragraph template. These should be in separate reference files that the orchestrator reads on demand (progressive disclosure Level 3).

3. **P1 — Orchestrator protocol embedded:** The orchestrator reads this file at spawn time. Section 2 (lines 256-394) should be a standalone file the orchestrator is pointed to, not embedded in SKILL.md.

4. **P1 — Universal Agent Rules embedded:** Lines 136-179 define rules injected into every agent prompt. Should be a standalone file agents reference.

5. **P2 — Output directory structure (lines 65-92):** Static reference info. Extract to reference file.

6. **P2 — JSONL logging format (lines 1324-1357):** Implementation detail for orchestrator. Extract.

7. **P2 — Pass thresholds table (lines 1269-1291):** Reference data. Extract.

#### Frontmatter Assessment

```yaml
name: verify                    # GOOD — 6 chars, lowercase
description: "Runs the 14..."  # GOOD — 93 chars, concise
context: fork                   # GOOD — runs in isolated context
agent: general-purpose          # GOOD
argument-hint: "[--fix]"        # GOOD
allowed-tools: [...]            # GOOD
```

**Missing:** `disable-model-invocation: true` — this skill makes destructive changes (clears markers, writes files). Should be user-only.

---

### 2. `langraph-patterns/SKILL.md` — WARN

**Lines:** 295 | **Desc chars:** 275

#### Issues

1. **P1 — Pure reference material, no process steps:** The entire body (lines 7-295) is code examples: State Graph, Node Functions, Parallel Execution, Checkpointing, Human-in-the-Loop, Error Handling, Streaming, Testing. There are zero process instructions ("When building a LangGraph graph, follow these steps: ...").

2. **P1 — Description too long (275 chars):** Exceeds the 200-char recommended max. The "TRIGGER when / DO NOT TRIGGER" pattern is good but verbose. Should be trimmed to ~150 chars.
   - **Current:** `"LangGraph 0.2+ implementation patterns (state graphs, nodes, checkpointing, human-in-the-loop). TRIGGER when: code imports \`langgraph\` or user asks about building LangGraph graphs, nodes, state machines, or checkpointing. DO NOT TRIGGER for non-LangGraph orchestration tools."`
   - **Suggested:** `"LangGraph 0.2+ patterns: state graphs, nodes, checkpointing, HITL. USE WHEN code imports langgraph or user asks about LangGraph."`

3. **P2 — user-invocable: false:** Correct — this is background knowledge, not a task skill.

4. **P2 — No progressive disclosure:** All 8 sections (State Graph, Nodes, Parallel, Checkpointing, HITL, Error Handling, Streaming, Testing) are in one file. Should be split into `SKILL.md` (brief overview + links) and `reference.md` (code examples).

#### What's Good
- Frontmatter present with all key fields
- name field valid (lowercase, hyphens, <64 chars)
- Code examples are SIOPV-specific (uses PipelineState, vulnerability, LangGraph patterns from this project)
- No nested @imports

---

### 3. `openfga-patterns/SKILL.md` — WARN

**Lines:** 310 | **Desc chars:** 268

#### Issues

1. **P1 — Pure reference material, no process steps:** 100% code examples: Auth Model, Client Setup, Check Permission, Write/Delete Relationship, List Objects, Decorator, Example Model, Docker Compose, Testing.

2. **P1 — Description too long (268 chars):** Same verbose TRIGGER/DO NOT TRIGGER pattern.
   - **Suggested:** `"OpenFGA ReBAC authorization patterns: tuples, permission checks, decorators. USE WHEN code imports openfga_sdk or user asks about OpenFGA."`

3. **P1 — Hardcoded localhost URL (line 53):** `api_url: str = "http://localhost:8080"` — this is a code example but could mislead. Add comment noting this is an example only.

4. **P1 — Hardcoded credentials in Docker Compose (line 278):** `postgresql://postgres:postgres@postgres:5432/openfga` — violates the global errors-to-rules rule about never hardcoding credentials, even in examples.

5. **P2 — No progressive disclosure.** Same structural issue as langraph-patterns.

#### What's Good
- Frontmatter correct
- name field valid
- SIOPV-specific examples (vulnerability management auth model)
- No nested @imports

---

### 4. `presidio-dlp/SKILL.md` — WARN

**Lines:** 286 | **Desc chars:** 285

#### Issues

1. **P1 — Pure reference material, no process steps:** All code examples: Setup, Detect PII, Anonymize PII, Custom Recognizers, Report Sanitization, Audit Log, LangGraph Integration, Testing, Configuration.

2. **P1 — Description too long (285 chars):** Longest description of all skills.
   - **Suggested:** `"Presidio DLP patterns: PII detection, anonymization, custom recognizers. USE WHEN code imports presidio_analyzer/anonymizer or user asks about PII/DLP."`

3. **P2 — No progressive disclosure.** Same structural issue.

#### What's Good
- Frontmatter correct
- name field valid
- SIOPV-specific examples (vulnerability report sanitization, LangGraph DLP node)
- Includes Configuration section with Pydantic v2 Settings pattern

---

### 5. `coding-standards-2026/SKILL.md` — WARN

**Lines:** 214 | **Desc chars:** 250

#### Issues

1. **P1 — Pure reference material, no process steps:** "Checklist" at line 203 is the closest to a process step, but it's a bulleted list, not an actionable workflow.

2. **P1 — Description too long (250 chars).**
   - **Suggested:** `"Python 2026 coding standards: modern type hints, Pydantic v2, httpx, structlog, pathlib. USE WHEN writing or reviewing Python code."`

3. **P2 — Duplicates information Claude already knows:** Much of this content (type hints, pathlib, f-strings) is common Python knowledge that Claude has natively. Only the "PROHIBIDO" patterns (what NOT to do) and SIOPV-specific conventions add value.

4. **P2 — Contains things that should NOT be in a skill:** The research best practices say: "Explanations of things Claude already knows" should not be in SKILL.md.

#### What's Good
- Frontmatter correct
- name field valid
- Clear ✅/❌ visual markers for correct/prohibited patterns
- Checklist at end is useful

---

### 6. `siopv-remediate/SKILL.md` — PASS

**Lines:** 60 | **Desc chars:** 265

#### Assessment

This is the only skill that follows the golden rule: **process in SKILL.md, context in reference files.**

- Clear "DO NOT TRIGGER" conditions (lines 16-19)
- Violation table for context (lines 22-31) — compact, justified
- Invocation protocol with exact agent prompt (lines 34-55)
- Checkpoint reminder (lines 57-60)

#### Minor Issues

1. **P2 — Description too long (265 chars).** Could trim to ~150 chars.
   - **Suggested:** `"Fix SIOPV Stage 2 hex-arch violations #1-7. USE WHEN user asks to fix hexagonal violations or runs /siopv-remediate."`

2. **P2 — Uses `disable-model-invocation: true`:** Correct — this is destructive and should be user-only.

3. **P2 — Uses `context: fork` + `agent: general-purpose`:** Correct — runs in isolated context.

---

## Cross-Cutting Findings

### F1. Description Budget (P1)

All 5 non-verify skills have descriptions >250 chars. The verbose `TRIGGER when / DO NOT TRIGGER` pattern is well-intentioned but too long. With 6 skills, total description budget consumed is ~1,436 chars (9% of ~16,000 limit) — currently fine, but will become a problem if skills are added.

**Recommendation:** Trim all descriptions to 130-150 chars. Move trigger conditions into the SKILL.md body instead.

### F2. No Reference Files Anywhere (P1)

None of the 6 skills use reference files. The `verify/` directory contains only `SKILL.md`. The pattern skills contain only `SKILL.md`. This means:
- Zero progressive disclosure (Level 3 never used)
- All content loaded on trigger, wasting tokens
- The 4 pattern skills inject ~250-310 lines of code examples every time they activate

### F3. Background Knowledge Skills Are All Code Dumps (P1)

The 4 `user-invocable: false` skills (langraph, openfga, presidio, coding-standards) are all structured identically: header → code examples → more code examples. None has:
- A brief overview explaining when/how to use the patterns
- Links to reference files
- Process steps

These would be better structured as:
```
SKILL.md (20-30 lines): overview + when to use + links to reference.md
reference.md (200-300 lines): code examples
```

### F4. Missing `allowed-tools` on Pattern Skills (P2)

The 4 pattern skills (`user-invocable: false`) don't specify `allowed-tools`. Since they're background knowledge and shouldn't trigger tool use, this is fine. But if they ever switch to `user-invocable: true`, they should add `allowed-tools: ["Read", "Grep", "Glob"]`.

### F5. No Hooks Used (P2)

None of the skills use the `hooks` frontmatter field. The `verify` skill could benefit from a pre-invocation hook that checks for pending markers before spawning the full pipeline.

---

## Prioritized Fix List

### P0 — Critical (must fix before Phase 7)

| # | Skill | Fix | Effort |
|---|-------|-----|--------|
| 1 | `verify` | **Extract ~1,100 lines to reference files.** Split into: `SKILL.md` (~80-100 lines), `orchestrator-protocol.md`, `agent-rules.md`, `wave-prompts.md`, `thresholds.md`. See detailed rewrite plan below. | High |
| 2 | `verify` | **Add `disable-model-invocation: true`** to prevent accidental auto-triggering of a 14-agent pipeline. | Trivial |

### P1 — Important (should fix soon)

| # | Skill | Fix | Effort |
|---|-------|-----|--------|
| 3 | ALL (5 of 6) | **Trim descriptions to 130-150 chars.** Move TRIGGER conditions into body. | Low |
| 4 | `langraph-patterns` | **Split into SKILL.md (overview) + reference.md (code examples).** | Medium |
| 5 | `openfga-patterns` | **Split into SKILL.md (overview) + reference.md (code examples).** | Medium |
| 6 | `presidio-dlp` | **Split into SKILL.md (overview) + reference.md (code examples).** | Medium |
| 7 | `coding-standards-2026` | **Split into SKILL.md (checklist only) + reference.md (code examples).** | Medium |
| 8 | `openfga-patterns` | **Remove hardcoded `postgres:postgres` from Docker Compose example** (line 278). | Trivial |

### P2 — Nice to Have

| # | Skill | Fix | Effort |
|---|-------|-----|--------|
| 9 | `coding-standards-2026` | Remove content Claude already knows natively. Keep only SIOPV-specific conventions and "PROHIBIDO" anti-patterns. | Low |
| 10 | `verify` | Add pre-invocation hook to check pending markers exist before spawning pipeline. | Low |
| 11 | `siopv-remediate` | Trim description to ~130 chars. | Trivial |

---

## Verify Skill Rewrite Plan

### Current State
- 1 file: `SKILL.md` (1,370 lines)

### Target State
```
verify/
├── SKILL.md                    # ~80-100 lines (process only)
├── orchestrator-protocol.md    # ~180 lines (Section 2 + pre-checks + post-wave)
├── agent-rules.md              # ~50 lines (4 universal rules)
├── wave-prompts.md             # ~700 lines (all agent prompt templates, PRE-WAVE through WAVE 9)
├── thresholds.md               # ~40 lines (pass thresholds table + timeout policy)
└── output-structure.md         # ~50 lines (directory structure + JSONL logging + marker system)
```

### What Stays in SKILL.md (~80-100 lines)

```markdown
---
name: verify
description: "Runs 14 verification agents (Pre-wave + Waves 1-9), clears pending markers. USE WHEN pre-commit."
disable-model-invocation: true
context: fork
agent: general-purpose
argument-hint: "[--fix]"
allowed-tools: ["Read", "Grep", "Glob", "Bash", "Task"]
---

# /verify

Runs verification agents and clears pending file markers.

## Usage
/verify         # Full verification pipeline
/verify --fix   # Auto-fix issues after verification

## Pipeline Overview
PRE-WAVE  → library-researcher (1 sequential)
WAVE 1    → scanner-bpe + scanner-security + scanner-hallucination (3 parallel)
WAVE 1B   → wave1-judge (1 sequential)
WAVE 2    → code-reviewer + test-generator (2 parallel)
WAVE 3    → N parallel fixers (dynamic, file-level partitioned)
WAVE 3B   → fix-validator (1 sequential)
WAVE 4    → integration-tracer + async-safety-auditor (2 parallel)
WAVE 5    → semantic-correctness-auditor + circular-import-detector (2 parallel)
WAVE 6    → import-resolver + dependency-scanner (2 parallel)
WAVE 7    → config-validator (1 agent)
WAVE 8    → hex-arch-remediator (1 agent)
WAVE 9    → smoke-test-runner (1 agent, last)

## 3-Tier Hierarchy
human → team-lead → orchestrator → agents
- agents report ONLY to orchestrator
- orchestrator requests spawns from team-lead
- team-lead interfaces with human for approvals

## Team-Lead Protocol (YOUR PROCESS)

### Step 1: Set Variables
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
TEAM_NAME="siopv-verify-${TIMESTAMP}"
VERIFY_DIR="/Users/bruno/siopv/.verify-$(date +%d-%m-%Y)"

### Step 2: Create Verify Directory
mkdir -p "$VERIFY_DIR"/{context7-cache,scans,fixes,reports,handoffs}

### Step 3: Create Team
TeamCreate(team_name="${TEAM_NAME}", ...)

### Step 4: Spawn Orchestrator
Agent(name="orchestrator", prompt="Read orchestrator-protocol.md at ${CLAUDE_SKILL_DIR}/orchestrator-protocol.md ...")

### Step 5: You are "team-lead". Wait for orchestrator messages.

### Step 6: Ongoing Duties
1. SPAWN REQUEST → present to human → wait for approval → spawn → SPAWN CONFIRMED
2. WAVE REPORT → present to human → wait for approval → WAVE APPROVED
3. Never fix issues yourself.

### Step 7: Cleanup
TeamDelete()

## Reference Files (read on demand)
- Agent universal rules: [agent-rules.md](agent-rules.md)
- Orchestrator protocol: [orchestrator-protocol.md](orchestrator-protocol.md)
- All wave agent prompts: [wave-prompts.md](wave-prompts.md)
- Pass thresholds + timeouts: [thresholds.md](thresholds.md)
- Output directory structure + logging: [output-structure.md](output-structure.md)
```

### What Goes to `orchestrator-protocol.md` (~180 lines)

- Current Section 2: Orchestrator Protocol (lines 256-330)
- Pre-checks (lines 298-330)
- File batch computation (lines 319-329)
- Post-wave actions (lines 1294-1321)
- JSONL logging specification (lines 1324-1357)

### What Goes to `agent-rules.md` (~50 lines)

- Rule 1: Handoff Protocol (lines 140-155)
- Rule 2: Tool Output Offloading (lines 157-166)
- Rule 3: Explicit Scope Only (lines 168-172)
- Rule 4: No Live Context7 Calls (lines 174-179)

### What Goes to `wave-prompts.md` (~700 lines)

- PRE-WAVE library-researcher prompt (lines 333-394)
- WAVE 1 scanner prompts (lines 397-579)
- WAVE 1B judge prompt (lines 583-654)
- WAVE 2 reviewer + testgen prompts (lines 657-754)
- WAVE 3 fixer prompts + formula (lines 758-857)
- WAVE 3B validator prompt (lines 860-910)
- WAVE 4 integration + async prompts (lines 913-985)
- WAVE 5 semantic + circular prompts (lines 988-1053)
- WAVE 6 imports + deps prompts (lines 1057-1123)
- WAVE 7 config prompt (lines 1126-1161)
- WAVE 8 hex-arch prompt (lines 1164-1199)
- WAVE 9 smoke test prompt (lines 1202-1253)

### What Goes to `thresholds.md` (~40 lines)

- Pass thresholds table (lines 1269-1291)
- Wave timeout and retry policy (lines 1256-1266)

### What Goes to `output-structure.md` (~50 lines)

- Output directory structure (lines 65-92)
- Marker system (lines 1360-1369)

### What Gets Deleted Entirely

Nothing needs to be deleted — all content is meaningful. It just needs to be redistributed into reference files for progressive disclosure.

### Migration Steps

1. Create the 5 reference files by extracting content from current SKILL.md
2. Rewrite SKILL.md to ~80-100 lines (process only + links)
3. Update orchestrator spawn prompt to point to `${CLAUDE_SKILL_DIR}/orchestrator-protocol.md`
4. Add `disable-model-invocation: true` to frontmatter
5. Test: invoke `/verify` and confirm orchestrator can read reference files
6. Verify total SKILL.md is under 100 lines

---

## Pattern Skills Rewrite Template

For each of the 4 pattern skills (langraph, openfga, presidio, coding-standards), apply this structure:

### Before (current)
```
skill-name/
└── SKILL.md (200-310 lines of code examples)
```

### After (target)
```
skill-name/
├── SKILL.md       (~25-40 lines: overview + when to apply + checklist + link to reference)
└── reference.md   (~200-280 lines: all code examples)
```

### SKILL.md Template
```yaml
---
name: {skill-name}
description: "{130-150 char description with USE WHEN trigger keywords}"
user-invocable: false
---

# {Skill Title}

Brief 2-3 sentence description of what this skill covers and when it applies.

## Key Patterns (quick reference)

- Pattern 1: one-line summary
- Pattern 2: one-line summary
- Pattern 3: one-line summary

## Checklist

- [ ] Check 1
- [ ] Check 2
- [ ] Check 3

## Full Reference

For complete code examples and detailed patterns, see [reference.md](reference.md).
```

---

## Appendix: Frontmatter Audit Matrix

| Field | verify | langraph | openfga | presidio | coding-std | remediate |
|-------|:------:|:--------:|:-------:|:--------:|:----------:|:---------:|
| `name` | OK | OK | OK | OK | OK | OK |
| `description` | OK (93) | LONG (275) | LONG (268) | LONG (285) | LONG (250) | LONG (265) |
| `user-invocable` | - | false | false | false | false | - |
| `disable-model-invocation` | **MISSING** | - | - | - | - | true |
| `context` | fork | - | - | - | - | fork |
| `agent` | general-purpose | - | - | - | - | general-purpose |
| `allowed-tools` | Yes | - | - | - | - | Yes |
| `argument-hint` | Yes | - | - | - | - | - |
| `hooks` | - | - | - | - | - | - |
| `model` | - | - | - | - | - | - |

**Legend:** OK = meets best practice | LONG = exceeds recommended length | MISSING = should have but doesn't | `-` = not applicable/not set
