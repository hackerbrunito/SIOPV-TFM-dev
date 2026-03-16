# Comparison Report: Gaps, Errors, and Incongruences

**Date:** 2026-03-09
**Agent:** comparator
**Sources compared:**
1. Transcript Extraction Report (499 lines, 15 DDs, 32-item checklist)
2. File Inventory Report (376 lines, 28 files inventoried)

---

## 1. MISSING HOOK SCRIPTS (3 planned, 0 created)

The transcript (Section 5.1) explicitly planned 3 new hook scripts. **None of them exist.**

| Planned Hook | Purpose | Status |
|-------------|---------|--------|
| `.claude/hooks/block-write-commands.sh` | PreToolUse:Bash — block `rm`, `mv`, `cp`, `chmod`, `chown`, `dd`, write redirects | **MISSING** |
| `.claude/hooks/block-dangerous-commands.sh` | PreToolUse:Bash — block `sudo`, `curl \| bash`, `eval`, `exec` | **MISSING** |
| `.claude/hooks/run-linter.sh` | PostToolUse:Edit\|Write — run `ruff check` + `ruff format --check` after edits | **MISSING** |

**Impact:** These hooks are the backbone of DD-009 (PreToolUse is the ONLY blocking hook) and the Guardrail Tier Matrix (Section 13). Without them:
- Scanner agents have NO deterministic read-only enforcement (only `disallowedTools` in frontmatter, which doesn't block destructive Bash commands)
- No dangerous command blocking for ANY agent
- No automatic linting after edits

**Checklist reference:** Phase B (3 items) — 0% complete.

---

## 2. MISSING RULES FILES (5 planned, 0 created)

The transcript (Section 6.1) planned 5 rules files. **None of them exist.** The 4 rules files that DO exist (`errors-to-rules.md`, `agent-reports.md`, `naming-conventions.md`, `tech-stack.md`) are different files that weren't in the transcript's planned list.

| Planned Rule | Purpose | Status |
|-------------|---------|--------|
| `.claude/rules/scanner-read-only.md` | Global rule enforcing read-only behavior for scanner agents | **MISSING** |
| `.claude/rules/report-template.md` | Global rule with mandatory report structure (Section 8 template) | **MISSING** |
| `.claude/rules/anti-improvisation.md` | Global DO NOT list + todo recitation requirement (DD-004, DD-006) | **MISSING** |
| `.claude/rules/security.md` | Path-targeted to `src/siopv/infrastructure/**` | **MISSING** |
| `.claude/rules/orchestration.md` | Path-targeted to `src/siopv/application/orchestration/**` | **MISSING** |

**Impact:** DD-014 (path-targeted rules) is completely unimplemented. DD-004 (anti-improvisation) relies on each agent having its own DO NOT section but the global enforcement rule is missing. DD-006 (todo recitation) has no global rule enforcing it.

**Checklist reference:** Phase E (4 items) — 0% complete.

---

## 3. MISSING SETTINGS.JSON HOOK CONFIGURATION

The transcript (Section 7.1) defined an explicit `settings.json` hook configuration block that wires `block-dangerous-commands.sh` to PreToolUse:Bash and `run-linter.sh` to PostToolUse:Edit|Write. The inventory does NOT include `settings.json` among its 28 files, and there is no evidence this configuration was applied.

**Impact:** Even if the hook scripts were created, they wouldn't be active without settings.json registration.

**Checklist reference:** Phase C (1 item) — 0% complete.

---

## 4. MISSING STAGE BRIEFING FILES (4 planned, 0 created)

The transcript (Section 3.3) planned 4 stage briefing files:

| Planned Briefing | Status |
|-----------------|--------|
| `.ignorar/agent-persona-research-2026-03-09/stage-1-briefing.md` | **MISSING** |
| `.ignorar/agent-persona-research-2026-03-09/stage-2-briefing.md` | **MISSING** |
| `.ignorar/agent-persona-research-2026-03-09/stage-3-briefing.md` | **MISSING** |
| `.ignorar/agent-persona-research-2026-03-09/stage-4-briefing.md` | **MISSING** |

**Impact:** The orchestrator agent's workflow requires reading a briefing file to know what to do in each stage. Without briefings, stages cannot be executed.

**Note:** The inventory confirms the parent directory `.ignorar/agent-persona-research-2026-03-09/` doesn't exist at all (Section 2.9 notes this). However, the inventory treats this as "expected to be created at runtime." The briefing files are a different matter — they must exist BEFORE stage execution, not be created at runtime.

---

## 5. MISSING STAGE REPORT DIRECTORIES (5 planned, 0 created)

The transcript (Section 3.1) planned:
```
.ignorar/agent-persona-research-2026-03-09/
  stage-1/
  stage-2/
  stage-3/
  stage-4/
  stage-5/
```

None exist. While report directories could be created at runtime by the orchestrator, the inventory acknowledges this across 6+ files that reference them.

**Checklist reference:** Phase A (5 items) — 0% complete.

---

## 6. AGENT NAMING CONVENTION DISCREPANCY

The transcript (Section 15) defined agent naming as:
```
.claude/agents/siopv-{role}-{domain}.md
```

Examples from templates: `siopv-scanner-[domain]`, `siopv-researcher-[topic]`, `siopv-summarizer-[stage]-[round]`, `siopv-orchestrator-[stage]`.

**Actual names in inventory:**

| Planned Pattern | Actual Name | Match? |
|----------------|-------------|--------|
| `siopv-scanner-[domain]` | `codebase-scanner` | No `siopv-` prefix |
| `siopv-scanner-[domain]` | `spec-mapper` | No prefix, different role name |
| `siopv-scanner-[domain]` | `hexagonal-auditor` | No prefix, different role name |
| `siopv-scanner-[domain]` | `security-auditor` | No prefix |
| `siopv-scanner-[domain]` | `best-practices-enforcer` | No prefix |
| `siopv-scanner-[domain]` | `test-coverage-auditor` | No prefix |
| `siopv-researcher-[topic]` | `sota-researcher` | No prefix |
| `siopv-summarizer-[stage]-[round]` | `wave-summarizer` | No prefix, no stage/round |
| `siopv-orchestrator-[stage]` | `orchestrator` | No prefix, no stage |
| (not templated) | `report-generator` | Not in transcript templates |

**Impact:** None of the 10 agents follow the planned `siopv-{role}-{domain}` naming convention. This is an incongruence but may be intentional simplification. The `naming-conventions.md` rule file doesn't enforce the `siopv-` prefix either.

---

## 7. TOOL ASSIGNMENT APPROACH DISCREPANCY

The transcript (Section 4) defined tools as an **allowlist** per role:
```yaml
tools: [Read, Grep, Glob, Bash]  # Scanner
tools: [Read, Grep, Glob, WebSearch, WebFetch]  # Researcher
```

The inventory shows agents use a **denylist** approach instead:
```yaml
disallowedTools: [Write, Edit]  # Scanner (codebase-scanner)
disallowedTools: [Write, Edit, Bash]  # Researcher (sota-researcher)
```

**Differences in effective tool access:**

| Role | Planned Tools (allowlist) | Actual Tools (denylist of Write/Edit) | Extra Access? |
|------|--------------------------|---------------------------------------|---------------|
| Scanner | Read, Grep, Glob, Bash | Everything except Write/Edit (includes WebSearch, WebFetch, Agent, SendMessage) | **YES** — scanners get web tools and Agent/SendMessage |
| Researcher | Read, Grep, Glob, WebSearch, WebFetch | Everything except Write/Edit/Bash | **YES** — researchers get Agent, SendMessage |
| Summarizer | Read, Grep, Glob, Write | Everything except Bash/Edit | **YES** — summarizers get WebSearch, WebFetch, Agent, SendMessage |

**Impact:** DD-007 (Scoped Tool Assignment) is partially violated. Agents have broader tool access than planned. Scanners should NOT have web access; summarizers should NOT be able to spawn agents.

---

## 8. maxTurns DISCREPANCY

The transcript (DD-008) set: Scanner: 25, Researcher: 30, Summarizer: 15, Orchestrator: 50.

| Agent | Planned maxTurns | Actual maxTurns | Match? |
|-------|-----------------|-----------------|--------|
| codebase-scanner | 25 | 25 | Yes |
| spec-mapper | 25 | 25 | Yes |
| hexagonal-auditor | 25 | **30** | **NO** — 5 extra turns |
| sota-researcher | 30 | 30 | Yes |
| security-auditor | 25 | 25 | Yes |
| best-practices-enforcer | 25 | 25 | Yes |
| test-coverage-auditor | 25 | 25 | Yes |
| wave-summarizer | 15 | 15 | Yes |
| orchestrator | 50 | 50 | Yes |
| report-generator | 15 | 15 | Yes |

**Impact:** `hexagonal-auditor` has maxTurns 30 instead of 25. Since it's classified as a scanner (uses sonnet, read-only, produces scan report), it should follow the scanner template limit of 25.

---

## 9. BROKEN REFERENCE: `docs/SIOPV_Propuesta_Tecnica_v2.txt`

Both reports identify this. The file is referenced by **4 config files**:
1. `CLAUDE.md` (line reference to tech spec)
2. `spec-mapper.md` (agent reads this file as primary input)
3. `01-session-start.md` (Key Paths table)
4. `MEMORY.md` (briefing file path)

The `docs/` directory does not exist at all in the SIOPV project.

**Impact:** The `spec-mapper` agent is **non-functional** — its entire purpose is to read this spec file and compare against implementation. This is a blocking issue for Stage 1 execution.

---

## 10. DESIGN DECISIONS NOT REFLECTED IN CONFIG

### DD-002: 150-Instruction Ceiling
No config file counts or enforces the total instruction count. No verification mechanism exists.

### DD-003: Lost-in-the-Middle Mitigation
The transcript requires: "front-load 3 critical rules and repeat the most important one as a REMINDER at the very end." The inventory confirms agents have REMINDER sections, but there is no systematic verification that the first 3 lines after frontmatter contain critical rules across all 10 agents.

### DD-006: Todo Recitation
"Agents must recite their task list after each step." No global rule enforces this (the planned `anti-improvisation.md` would have included this requirement). Individual agent bodies may or may not include this instruction.

### DD-010: Four Persona Patterns
The transcript defines Pattern A (Role+Checklist for scanners), B (Domain Expert+Workflow for researchers), C (Behavioral Boundaries for summarizers), D (Cognitive Personas). There is no documentation or rule file that maps which agents use which pattern or verifies compliance.

### DD-012: Round/Batch Management
The orchestrator agent (82 lines per inventory) is generic — it doesn't encode specific round plans for any stage. The transcript says "Orchestrator definitions must encode round plans with batch limits." The stage-specific round plans exist only in `02-audit-stages.md` workflow file, not in the orchestrator agent definition.

### DD-013: Compaction Survival
The transcript requires COMPACT-SAFE markers. The inventory shows workflow files have these markers (from the meta-project), but there's no evidence the SIOPV-specific workflow files (01-04) include them.

---

## 11. EXTRA FILES (created but not in transcript plan)

These files exist in the inventory but were NOT part of the transcript's planned deliverables:

| File | Category | Notes |
|------|----------|-------|
| `naming-conventions.md` | Rules | Useful but not in transcript Section 6.1 list |
| `tech-stack.md` | Rules | Useful but not in transcript Section 6.1 list |
| `agent-reports.md` | Rules | Partially covers transcript Section 8 (report template) but is NOT `report-template.md` |
| `errors-to-rules.md` | Rules | Empty SIOPV-specific error log; not in planned deliverables |
| `model-selection-strategy.md` | Docs | Useful but not in transcript plan |
| `agent-tool-schemas.md` | Docs | Covers transcript Section 4 but as a doc rather than enforcement |
| `verification-thresholds.md` | Docs | Useful but not in transcript plan |
| `report-generator.md` | Agents | Not one of the 4 templated roles; appears to be an elaboration of the summarizer pattern |
| `test-coverage-auditor.md` | Agents | Mentioned in stage descriptions but not explicitly templated |

**Assessment:** These extras are beneficial additions. However, they were created INSTEAD OF the planned files, not in addition to them. The planned enforcement files (hooks, rules) are missing while documentation files were created.

---

## 12. REPORT TEMPLATE DISCREPANCY

The transcript (Section 8) defines a mandatory report template with specific fields:
- `Stage:`, `Round:`, `Batch:`, `Sequence:`, `Timestamp:`, `Duration:`
- `Mandate` section
- `Finding F-NNN` format with Severity, Location, Description, Evidence, Recommendation

The inventory confirms agents use this format, but the global `report-template.md` rules file that would enforce it is **missing** (see Section 2 above). The existing `agent-reports.md` rules file covers report persistence (directory structure, naming, timing) but NOT the report content template itself.

---

## 13. WORKFLOW FILE NUMBERING DISCREPANCY

The transcript references existing meta-project workflow files from `sec-llm-workbench`:
- `01-session-start.md`
- `02-reflexion-loop.md`
- `03-human-checkpoints.md`
- `05-before-commit.md`

The SIOPV project created its own workflow files with DIFFERENT numbering:
- `01-session-start.md` (SIOPV-specific, not the meta-project version)
- `02-audit-stages.md` (NEW — replaces the meta-project `02-reflexion-loop.md`)
- `03-human-checkpoints.md` (SIOPV-specific version)
- `04-before-commit.md` (was `05` in meta-project, now `04`)

**Impact:** The CLAUDE.md references these correctly for SIOPV. No functional issue, but the numbering shift from the meta-project may cause confusion if both projects are worked on in the same session.

---

## 14. IMPLEMENTATION CHECKLIST COMPLETION SUMMARY

From the transcript's 32-item checklist (Section 14):

| Phase | Items | Status |
|-------|-------|--------|
| A: Directory Structure (5 items) | Stage directories | **0% — not created** |
| B: Hook Scripts (3 items) | 3 new hooks | **0% — not created** |
| C: Settings Configuration (1 item) | settings.json | **0% — not applied** |
| D: Agent Definitions (8 items) | 4 templates + 4 briefings | **50% — 10 agents created (more than planned), 0 briefings** |
| E: Rules Files (4 items) | 5 rules files | **0% — different files created instead** |
| F: Validation and Testing (4 items) | Hook/agent testing | **0% — nothing to test (hooks don't exist)** |
| G: Stage Execution (6 items) | Run stages 1-5 | **0% — prerequisites not met** |
| H: Final Audit Record (1 item) | Final report | **0% — stages not executed** |

**Overall: ~15% complete** (agent definitions exist but most infrastructure is missing).

---

## 15. SUMMARY OF ALL FINDINGS

| # | Category | Finding | Severity |
|---|----------|---------|----------|
| 1 | Missing hooks | 3 planned hook scripts not created | **CRITICAL** — no deterministic enforcement |
| 2 | Missing rules | 5 planned rules files not created | **HIGH** — no global behavioral enforcement |
| 3 | Missing settings | settings.json hook wiring not applied | **HIGH** — hooks wouldn't work even if created |
| 4 | Missing briefings | 4 stage briefing files not created | **HIGH** — stages cannot execute |
| 5 | Missing directories | 5 stage report directories not created | **MEDIUM** — can be created at runtime |
| 6 | Naming convention | Agents don't use `siopv-{role}-{domain}` pattern | **LOW** — functional but inconsistent |
| 7 | Tool access | Denylist approach gives broader access than planned allowlist | **MEDIUM** — agents have unintended capabilities |
| 8 | maxTurns | hexagonal-auditor has 30 instead of 25 | **LOW** — minor deviation |
| 9 | Broken reference | `docs/SIOPV_Propuesta_Tecnica_v2.txt` missing, blocks spec-mapper | **CRITICAL** — agent non-functional |
| 10 | Design decisions | DD-002, DD-006, DD-010, DD-012, DD-013 not enforced | **MEDIUM** — compliance relies on prompt only |
| 11 | Extra files | 9 files created that weren't planned | **INFO** — beneficial but replaced planned files |
| 12 | Report template | Global enforcement rule missing | **MEDIUM** — template exists in agents but no global rule |
| 13 | Workflow numbering | Different from meta-project numbering | **INFO** — intentional SIOPV adaptation |
| 14 | Checklist progress | ~15% of 32-item checklist completed | **INFO** — status summary |

**Critical blockers for stage execution:**
1. No hook scripts (Tier 3 guardrails completely absent)
2. No stage briefing files (orchestrator has no instructions per stage)
3. `docs/SIOPV_Propuesta_Tecnica_v2.txt` missing (spec-mapper non-functional)

---

**END OF COMPARISON REPORT**
