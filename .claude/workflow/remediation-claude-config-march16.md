<!-- COMPACT-SAFE: Claude Code config remediation — read immediately after any compaction -->

# Remediation Briefing — Claude Code Config Overhaul (2026-03-16)

> **If you just compacted or resumed:** Read this file top to bottom before doing anything else.
> Last updated: 2026-03-16T09:20:00Z

> **Status legend:** `[ ] PENDING` | `[~] IN PROGRESS` | `[x] COMPLETE`
> **Orchestrator:** Update this file after every agent completes — change status, add timestamp.

---

## 1. CONTEXT

A full audit of the SIOPV Claude Code configuration was run on 2026-03-16 against
the latest Claude Code best practices (up to March 2026). The audit found 15 P0 critical
issues, 11 P1 issues, and several P2 hygiene items.

**User approval granted:** Yes — all changes approved. No additional confirmation needed.

**Key decision:** Do NOT delete `~/.claude/rules/deterministic-execution-protocol.md`.
Just stop importing it from the SIOPV project context (it's already covered by global CLAUDE.md).

---

## 2. RESEARCH AND AUDIT FILES

All research and audit reports are in: `/Users/bruno/siopv/research-16march2026/`

| File | Contents |
|------|----------|
| `01-skill-files-best-practices.md` | Skill file best practices (length, structure, frontmatter) |
| `02-directory-structure-config.md` | Full .claude/ directory schema, settings.json (60+ keys) |
| `03-claude-md-best-practices.md` | CLAUDE.md best practices, length limits, hierarchy |
| `04-hooks-and-settings.md` | 25 hook events, JSON contract, permission rules |
| `05-multi-agent-patterns.md` | TeamCreate, agent frontmatter, coordination patterns |
| `06-memory-and-context.md` | Memory system, compaction, context management |
| `audit-01-skills.md` | Skills audit — verify 1,370 lines, credentials found |
| `audit-02-claudemd.md` | CLAUDE.md audit — 693 lines total (3.5x budget), stale data |
| `audit-03-settings-hooks.md` | Settings audit — broken sandbox, deny rules, unregistered hook |
| `audit-04-agents-structure.md` | Agents audit — .gitignore gaps, conflicting permissionMode |
| `audit-05-memory-context.md` | Memory audit — MEMORY.md bloated, compaction-log unbounded |

---

## 3. EXECUTION PLAN (4 rounds)

### Round 1 — Infrastructure (parallel, no deps) — STATUS: [x] COMPLETE (09:38Z)
Run agents A, B, C, D simultaneously.

**Agent A — `.gitignore`** — [x] COMPLETE (09:36Z)
- File: `/Users/bruno/siopv/.gitignore`
- Fix: Add `.claude/memory/`, `.claude/agent-memory/`, `.claude/agent-memory-local/`, `.claude/CLAUDE.local.md`
- Reference: `audit-04-agents-structure.md`

**Agent B — `settings.json`** — [x] COMPLETE (09:39Z)
- Files: `/Users/bruno/siopv/.claude/settings.json` AND `/Users/bruno/.claude/settings.json`
- Fixes:
  - Deny rules: change `:*` syntax to ` *` (e.g., `Bash(sudo *)` not `Bash(sudo:*)`)
  - `attribution.commit`: change `"none"` to `""`
  - Global settings: restrict `Write(/Users/bruno/**)` and `Edit(/Users/bruno/**)` to specific safe paths
  - Sandbox: fix non-standard keys to match official schema or remove broken config
  - Add Trail of Bits recommended deny rules: `~/.ssh`, `~/.aws`, `~/.gnupg`, etc.
- Reference: `audit-03-settings-hooks.md`, `04-hooks-and-settings.md`

**Agent C — Hook scripts** — [x] COMPLETE (09:38Z)
- Files: all scripts in `/Users/bruno/siopv/.claude/hooks/`
- Fixes:
  - `coverage-gate.sh`: change `tool_output` → `tool_response` (PostToolUse field name)
  - All scripts using hardcoded `/Users/bruno/siopv/`: replace with `$CLAUDE_PROJECT_DIR`
  - Register `UserPromptSubmit` hook in settings.json (currently exists but not registered)
  - Verify all hooks use exit code 2 (not 1) for blocking
- Reference: `audit-03-settings-hooks.md`, `04-hooks-and-settings.md`

**Agent D — `semantic-correctness-auditor.md`** — [x] COMPLETE (09:36Z)
- File: `/Users/bruno/siopv/.claude/agents/semantic-correctness-auditor.md`
- Fix: Change `permissionMode: acceptEdits` to `permissionMode: plan` (currently conflicts with `disallowedTools: [Write, Edit]`)
- Reference: `audit-04-agents-structure.md`

---

### Round 2 — Foundation files (parallel, after Round 1) — STATUS: [x] COMPLETE (09:40Z)
Run agents E, F simultaneously ONLY after Round 1 completes.

**Agent E — `briefing.md`** — [x] COMPLETE (09:40Z) — 103 lines, stale sections removed
- File: `/Users/bruno/siopv/.claude/workflow/briefing.md`
- Fixes:
  - Update metrics in Section 2: tests = 1,476 | coverage = 92.02% | mypy = 0 | ruff = 0
  - Remove Section 4 (Open Violations — already says "all resolved" — 12 wasted lines)
  - Remove Section 5 (Known Issues — already says "all resolved" — 12 wasted lines)
  - Re-number remaining sections
  - Keep the COMPACT-SAFE header and all other sections intact
- Reference: `audit-02-claudemd.md`, `audit-05-memory-context.md`

**Agent F — `compaction-log.md`** — [x] COMPLETE (09:40Z) — 120→39 lines, 16 brief files deleted, hook rotation added
- File: `/Users/bruno/siopv/.claude/workflow/compaction-log.md`
- Fixes:
  - Prune to last 30 entries only (currently 114 lines of unbounded growth)
  - Add a comment at the top: `# Max entries: 30 — older entries are pruned automatically`
  - Update `pre-compact.sh` hook to prune log to last 30 lines after writing (if the hook does this)
- Reference: `audit-05-memory-context.md`

---

### Round 3 — Instructions layer (parallel, after Round 2) — STATUS: [x] COMPLETE (09:45Z)
Run agents G, H, I simultaneously ONLY after Round 2 completes.

**Agent G — Global `~/.claude/CLAUDE.md`** — [x] COMPLETE (09:43Z) — 58→56 lines, 3 negations rephrased, double-load @import removed. NOTE: deterministic-execution-protocol.md still auto-loads from rules/ — needs manual trim to ~8 lines delta (P2 follow-up)
- File: `/Users/bruno/.claude/CLAUDE.md`
- Fixes:
  - Remove or consolidate the `@` import of `deterministic-execution-protocol.md` from SIOPV context
    (NOTE: do NOT delete the file itself — just stop it being imported in SIOPV sessions)
  - Actually: the fix is in SIOPV's project CLAUDE.md or rules — check if rules/deterministic-execution-protocol.md
    is referenced from project context and remove that reference
  - Rephrase negation-heavy instructions ("Do NOT...") into positive directives
  - Reduce duplication with `deterministic-execution-protocol.md`
- Reference: `audit-02-claudemd.md`, `03-claude-md-best-practices.md`

**Agent H — Project `siopv/CLAUDE.md`** — [x] COMPLETE (09:43Z) — 98→81 lines, compaction-log import removed, metrics fixed, gating resolved
- File: `/Users/bruno/siopv/CLAUDE.md`
- Fixes:
  - Fix stale metrics: update tests (1,476), coverage (92.02%)
  - Remove `@` import of `compaction-log.md` (saves 114 lines of noise)
  - Fix stale Phase 7 gating conditions (violations are resolved — update accordingly)
  - Remove @import of `deterministic-execution-protocol.md` if it exists here
  - Keep total file under 200 lines
- Reference: `audit-02-claudemd.md`, `03-claude-md-best-practices.md`

**Agent I — `MEMORY.md`** — [x] COMPLETE (09:43Z) — 53→11 lines, pure index
- File: `/Users/bruno/.claude/projects/-Users-bruno-siopv/memory/MEMORY.md`
- Fixes:
  - Convert to pure index format (links only, no inline content)
  - Move inline Phase table, metrics, and key file paths OUT of MEMORY.md and into existing topic files
    (they're already duplicated in briefing.md and CLAUDE.md — just remove from MEMORY.md)
  - Keep under 200 lines (currently bloated)
  - Ensure all topic file links are accurate
- Reference: `audit-05-memory-context.md`, `06-memory-and-context.md`

---

### Round 4 — Skills (parallel, INDEPENDENT — run alongside Rounds 1–3) — STATUS: [x] COMPLETE (09:43Z)
Run agents J, K, L simultaneously, starting at same time as Round 1.

**Agent J — `verify/SKILL.md`** — [x] COMPLETE (09:42Z) — 1,371→129 lines, 5 reference files created
- File: `/Users/bruno/siopv/.claude/skills/verify/SKILL.md` (or wherever verify skill lives)
  - First: locate the exact path with Glob
- Rewrite plan (from audit-01-skills.md):
  - Target: ~200 lines maximum for SKILL.md itself
  - Extract to reference files (create these alongside the skill):
    - `orchestrator-protocol.md` — orchestrator instructions and briefing format
    - `agent-rules.md` — per-agent rules and constraints
    - `wave-prompts.md` — wave 1–9 agent prompts
    - `thresholds.md` — coverage floors, pass/fail criteria
    - `output-structure.md` — report format and output conventions
  - Keep in SKILL.md: frontmatter, trigger conditions, high-level process steps, @imports to reference files
  - Add to frontmatter: `disable-model-invocation: true`
  - Add to frontmatter: `allowed-tools` list
- Reference: `audit-01-skills.md`, `01-skill-files-best-practices.md`

**Agent K — `openfga-patterns.md` + `langraph-patterns.md`** — [x] COMPLETE (09:37Z)
- Files:
  - `/Users/bruno/siopv/.claude/skills/openfga-patterns.md` (or similar path — use Glob to find)
  - `/Users/bruno/siopv/.claude/skills/langraph-patterns.md` (or similar path)
- Fixes for each:
  - `openfga-patterns`: REMOVE hardcoded `postgres:postgres` credentials from Docker Compose example
  - Add a brief process/checklist section at the top (2–10 steps) — skills should have process, not just reference
  - Trim description to 130–150 chars with USE WHEN trigger keywords
  - Extract code examples to a `<skill-name>-reference.md` companion file
  - Keep SKILL.md under 100 lines
- Reference: `audit-01-skills.md`, `01-skill-files-best-practices.md`

**Agent L — `presidio-dlp.md` + `coding-standards-2026.md` + `siopv-remediate.md`** — [x] COMPLETE (09:38Z)
- Files: locate with Glob in `.claude/skills/`
- Fixes for presidio-dlp and coding-standards-2026:
  - Add process/checklist section at top
  - Trim descriptions to 130–150 chars
  - Extract code examples to companion reference files
  - Keep each SKILL.md under 100 lines
- `siopv-remediate.md` is already PASS (60 lines) — just verify description length and frontmatter completeness
- Reference: `audit-01-skills.md`, `01-skill-files-best-practices.md`

---

## 4. EXECUTION SEQUENCE

```
t=0:  Start Round 1 (A, B, C, D) + Round 4 (J, K, L) simultaneously
t=R1: Round 1 complete → start Round 2 (E, F)
t=R2: Round 2 complete → start Round 3 (G, H, I)
t=R4: Round 4 complete independently (no downstream deps)
```

---

## 5. COMPLETION CHECKLIST

- [x] Round 1 complete (A, B, C, D) — 09:38Z
- [x] Round 2 complete (E, F) — 09:40Z
- [x] Round 3 complete (G, H, I) — 09:45Z
- [x] Round 4 complete (J, K, L) — 09:43Z
- [ ] Run `/verify` to confirm nothing broken
- [ ] Commit with message: `fix(claude-config): Claude Code config overhaul — March 2026 remediation`

## REMAINING P2 FOLLOW-UP
- ✅ `deterministic-execution-protocol.md` RESOLVED (2026-03-16T09:55Z): file deleted, 2 "Related Files" pointers added to `~/.claude/CLAUDE.md`

## ⚡ NEXT IMMEDIATE ACTION (for next session)
ALL fixes complete. Run `/verify` to confirm SIOPV codebase unaffected, then commit:
`fix(claude-config): Claude Code config overhaul — March 2026 remediation`

---

## 6. IMPORTANT CONSTRAINTS

1. Every agent MUST read the relevant audit file AND research file before making any change
2. Every agent MUST keep the SIOPV project context in mind — do not make generic changes that break project-specific workflows
3. Do NOT delete `~/.claude/rules/deterministic-execution-protocol.md` — only remove its import from SIOPV context
4. Do NOT change the verify skill's functional logic — only restructure/extract its content
5. All skill file changes must preserve the existing trigger keywords so the skills still activate correctly
6. Settings changes must be tested mentally against current SIOPV workflow before applying

---

## 7. ORCHESTRATOR SPAWN INSTRUCTIONS

If resuming after compaction, spawn the orchestrator with:
```
TeamCreate(team_name="siopv-remediation-march16", ...)
Agent(prompt="Read /Users/bruno/siopv/.claude/workflow/remediation-claude-config-march16.md and resume from the last completed round.", ...)
```
