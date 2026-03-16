# Audit 02 — CLAUDE.md Best Practices Compliance

> **Date:** 2026-03-16
> **Auditor:** claude-md-audit agent
> **Reference:** `research-16march2026/03-claude-md-best-practices.md`
> **Verdict:** FAIL — significant restructuring needed

---

## Executive Summary

| File | Lines | Limit | Status |
|------|-------|-------|--------|
| `~/.claude/CLAUDE.md` | 57 | 200 | PASS (individually) |
| `~/.claude/rules/errors-to-rules.md` | 117 | — | WARNING — verbose |
| `~/.claude/rules/deterministic-execution-protocol.md` | 66 | — | FAIL — 90% duplicate |
| `siopv/CLAUDE.md` | 97 | 200 | PASS (individually) |
| `siopv/.claude/CLAUDE.local.md` | 38 | — | PASS |
| `siopv/.claude/rules/agent-reports.md` | 49 | — | WARNING — no path scope |
| `siopv/.claude/rules/placeholder-conventions.md` | 14 | — | PASS |
| `siopv/.claude/rules/tech-stack.md` | 27 | — | PASS |
| `siopv/.claude/workflow/briefing.md` (@imported) | 114 | — | WARNING — duplication |
| `siopv/.claude/workflow/compaction-log.md` (@imported) | 114 | — | FAIL — pure noise |
| **TOTAL AUTO-LOADED** | **~693** | **200** | **FAIL — 3.5x over budget** |

**Key finding:** While no single file exceeds 200 lines, the **combined auto-loaded context is ~693 lines** — 3.5x the recommended budget. Research shows the effective instruction budget is ~100-150 items (after Claude's system prompt consumes ~50). This setup is severely overloaded, causing instruction dilution.

---

## Per-File Findings

### 1. `~/.claude/CLAUDE.md` (57 lines) — PASS with issues

**Strengths:**
- Under 200 lines
- Good use of @import for errors-to-rules
- Clear section headers
- Critical rules at top (error prevention)

**Issues:**

| Line | Issue | Severity |
|------|-------|----------|
| 15 | `"Don't ask for confirmation"` — negation phrasing | P2 |
| 33-57 | TeamCreate protocol is 100% duplicated in `deterministic-execution-protocol.md` | P0 |
| 10 | `@~/.claude/rules/errors-to-rules.md` — imports 117 lines into every session. Rules files are already auto-loaded by Claude Code, so this may cause double-loading | P1 |

**Missing:**
- No `# About` or project-agnostic identity section (WHO is this user?)

### 2. `~/.claude/rules/errors-to-rules.md` (117 lines) — WARNING

**Strengths:**
- Good template format
- Useful historical record

**Issues:**

| Line | Issue | Severity |
|------|-------|----------|
| 1-117 | Every entry has verbose "Error:" paragraph (5-8 lines each). Only the "Rule:" line drives behavior. The error descriptions consume ~60 lines of context that don't affect Claude's actions | P1 |
| 51-61 | Entry #6 (hardcoded credentials) is 11 lines with a 5-item sub-list — could be 2 lines: "Extract all literals to constants/Settings. No hardcoded credentials, URLs, magic numbers, or strings." | P1 |
| 72-77 | Entry #8 (stale training data) is 6 lines — the 3-tier lookup chain is important but could be a separate rule file | P2 |
| — | Some entries are project-specific (Strava app in #6, SlowAPI in #8) but loaded globally | P2 |
| — | 11 entries × ~10 lines each = filling the entire instruction budget with past mistakes. Research recommends max ~50 entries with periodic pruning | P2 |

**Recommendation:** Trim each entry to 2-3 lines (rule only, drop error narrative). Move the full history to a separate non-auto-loaded archive file.

### 3. `~/.claude/rules/deterministic-execution-protocol.md` (66 lines) — FAIL

**Issues:**

| Line | Issue | Severity |
|------|-------|----------|
| 1-66 | **90% duplication with `~/.claude/CLAUDE.md` lines 33-57.** The TeamCreate announcement, override protocol, and orchestrator spawn protocol are stated in both files. This wastes ~50 lines of context and risks contradictions if one is updated without the other | P0 |
| 33-52 | Code blocks showing TeamCreate/Agent tool call syntax — 20 lines of examples that Claude already knows from its tool definitions | P1 |
| — | No `paths:` frontmatter — loads for every session in every project | P2 |

**Recommendation:** DELETE this file entirely. Its content is already in `~/.claude/CLAUDE.md`. If the protocol needs more detail than CLAUDE.md provides, keep ONLY the delta in this file and remove all duplicated text.

### 4. `siopv/CLAUDE.md` (97 lines) — PASS with issues

**Strengths:**
- Under 200 lines individually
- Critical rules at top with `YOU MUST` emphasis
- Good use of @imports for briefing and compaction-log
- References section correctly marks files as "read on demand"
- Skills table is useful

**Issues:**

| Line | Issue | Severity |
|------|-------|----------|
| 7 | `@.claude/workflow/compaction-log.md` — imports 114 lines of pure timestamps that provide zero behavioral guidance | P0 |
| 10 | `"NEVER rely on training data"` — negation phrasing | P2 |
| 12 | `"NEVER import adapter classes"` — negation phrasing. Better: "Use cases receive dependencies via ports (interfaces) only" | P2 |
| 35 | **STALE DATA:** "1,404 tests passing · 83% coverage" — but briefing.md says 1,476 tests · 92.02% coverage. Contradictory instructions confuse Claude | P0 |
| 39-44 | **STALE DATA:** Phase 7 gating conditions listed as open, but briefing.md Section 4 says "All violations resolved in remediation-hardening (2026-03-15)". Direct contradiction | P0 |
| 48-59 | Key File Paths table — duplicated verbatim in briefing.md Section 3 (lines ~70-85). 12 wasted lines | P1 |
| 63-73 | References table — 11 lines listing files that could be discovered by Claude reading the directory. Marginal value | P2 |

**Missing:**
- No `# Project` one-liner (WHY section from WHY/WHAT/HOW framework)
- No build/test commands (e.g., `uv run pytest`, `uv run ruff check`) — these are in tech-stack.md rules but not in the main CLAUDE.md where they'd have highest visibility

### 5. `siopv/.claude/CLAUDE.local.md` (38 lines) — PASS

**Strengths:**
- Correct usage — personal, non-committed config
- Contains local paths, debug flags
- References the bypassPermissions lesson from errors-to-rules

**Issues:**

| Line | Issue | Severity |
|------|-------|----------|
| 5 | `"Language: Spanish or English"` — duplicated from global CLAUDE.md line 17 | P2 |
| 36-37 | `LANGCHAIN_API_KEY=<your-key>` — placeholder is fine, but the instruction to set it could be a gotcha if copied literally | P2 |

### 6. `siopv/.claude/rules/agent-reports.md` (49 lines) — WARNING

**Issues:**

| Line | Issue | Severity |
|------|-------|----------|
| — | No `paths:` frontmatter — loads for every session even when no agents are being spawned | P1 |
| 31-43 | Wave timing section (13 lines) describes verification workflow internals. This belongs in the `/verify` skill or a workflow file, not an always-loaded rule | P1 |

**Recommendation:** Add `paths:` frontmatter scoped to `.ignorar/production-reports/**` or move to a skill/workflow file.

### 7. `siopv/.claude/rules/placeholder-conventions.md` (14 lines) — PASS

Short, focused, useful. No issues.

Minor note: no `paths:` frontmatter, but at 14 lines the cost is negligible.

### 8. `siopv/.claude/rules/tech-stack.md` (27 lines) — PASS

**Strengths:**
- Uses `paths:` frontmatter correctly (`**/*.py`, `pyproject.toml`)
- Concise
- Includes actionable pre/post-write reminders

No issues.

### 9. `siopv/.claude/workflow/briefing.md` (114 lines, @imported) — WARNING

**Strengths:**
- Comprehensive project state document
- Good compaction-proof design

**Issues:**

| Line | Issue | Severity |
|------|-------|----------|
| — | Duplicates Key File Paths table from CLAUDE.md | P1 |
| — | Duplicates Phase Completion table from CLAUDE.md | P1 |
| 74-97 | Sections 4 and 5 ("Open Violations", "Known Issues") both say "All resolved" — 24 lines that say nothing. Remove and replace with a single line | P1 |

### 10. `siopv/.claude/workflow/compaction-log.md` (114 lines, @imported) — FAIL

**Issues:**

| Line | Issue | Severity |
|------|-------|----------|
| 1-114 | **This file is 114 lines of timestamps.** None of this content provides behavioral guidance to Claude. It consumes ~114 lines of the instruction budget every session for zero benefit. The @import in CLAUDE.md says "read last 5 lines" but @import loads the ENTIRE file — there is no line-range import syntax | P0 |

**Recommendation:** Remove the @import from CLAUDE.md. If Claude needs to check the log, it can read it on demand. The instruction "check compaction-log.md if you just compacted" is sufficient without importing the entire file.

---

## Cross-File Analysis

### Duplication Map

| Content | Location 1 | Location 2 | Wasted Lines |
|---------|-----------|-----------|-------------|
| TeamCreate protocol | `~/.claude/CLAUDE.md:33-57` | `deterministic-execution-protocol.md:1-66` | ~50 |
| Key File Paths table | `siopv/CLAUDE.md:48-59` | `briefing.md:~70-85` | ~12 |
| Phase Completion table | `siopv/CLAUDE.md:27-31` | `briefing.md:~30-45` | ~6 |
| Language preference | `~/.claude/CLAUDE.md:17` | `CLAUDE.local.md:5` | 1 |
| Metrics baseline | `siopv/CLAUDE.md:35` | `briefing.md:~52-57` | 1 (contradictory!) |
| **Total wasted** | | | **~70 lines** |

### Contradiction Map

| Topic | File A says | File B says |
|-------|------------|------------|
| Test count | CLAUDE.md: 1,404 | briefing.md: 1,476 |
| Coverage | CLAUDE.md: 83% | briefing.md: 92.02% |
| Gating conditions | CLAUDE.md: "ALL must be resolved" (implies open) | briefing.md: "All resolved" |

### Negation Inventory

Best practices say to use positive phrasing. These negation-heavy instructions should be rephrased:

| File | Line | Negation | Positive alternative |
|------|------|----------|---------------------|
| CLAUDE.md | 10 | "NEVER rely on training data" | "Always verify library APIs via Context7 before coding" |
| CLAUDE.md | 12 | "NEVER import adapter classes directly" | "Use cases receive dependencies via port interfaces only" |
| CLAUDE.md | 11 | "NO cross-layer imports" | "Imports follow domain → ports → adapters direction only" |
| global CLAUDE.md | 15 | "Don't ask for confirmation" | "Proceed directly on standard tasks" |

### @Import Chain Depth

```
~/.claude/CLAUDE.md
  └─ @~/.claude/rules/errors-to-rules.md  (depth 1) ← also auto-loaded as rules/ file

siopv/CLAUDE.md
  ├─ @.claude/workflow/briefing.md  (depth 1)
  └─ @.claude/workflow/compaction-log.md  (depth 1)
```

Max depth: 1 hop. Well within the 5-hop limit. However, the @import of errors-to-rules.md may cause double-loading since `.claude/rules/*.md` files are auto-loaded independently.

---

## Context Budget Analysis

| Category | Lines | % of budget |
|----------|-------|-------------|
| Global CLAUDE.md | 57 | 8% |
| Global rules (errors + protocol) | 183 | 26% |
| Project CLAUDE.md | 97 | 14% |
| Project CLAUDE.local.md | 38 | 5% |
| Project rules (3 files) | 90 | 13% |
| @imported files (briefing + compaction log) | 228 | 33% |
| **Total** | **693** | **100%** |
| **Recommended maximum** | **200** | — |
| **Overage** | **493 lines (3.5x)** | — |

The research shows that instruction adherence degrades significantly above 200 lines. At 693 lines, critical rules are likely being diluted by noise.

---

## Prioritized Fix List

### P0 — Critical (fix immediately)

| # | Issue | Action |
|---|-------|--------|
| 1 | **compaction-log.md @imported** (114 lines of noise) | Remove `@.claude/workflow/compaction-log.md` from `siopv/CLAUDE.md`. Replace with: "After compaction, read `.claude/workflow/compaction-log.md` (last 5 lines)" — no @import |
| 2 | **deterministic-execution-protocol.md is 90% duplicate** of global CLAUDE.md | DELETE `~/.claude/rules/deterministic-execution-protocol.md` entirely. Content is already in `~/.claude/CLAUDE.md` |
| 3 | **Stale metrics in CLAUDE.md** (1,404 tests / 83%) contradict briefing.md (1,476 / 92.02%) | Update `siopv/CLAUDE.md` line 35 to match briefing.md. Better: remove the metrics line from CLAUDE.md and keep it ONLY in briefing.md |
| 4 | **Stale gating conditions** say violations are open but they're resolved | Update or remove `siopv/CLAUDE.md` lines 39-44 to reflect current state |

### P1 — Important (fix this week)

| # | Issue | Action |
|---|-------|--------|
| 5 | **errors-to-rules.md is 117 verbose lines** loaded globally | Trim each entry to rule-only (2-3 lines). Drop "Error:" narratives. Target: 40 lines |
| 6 | **Key File Paths duplicated** in CLAUDE.md and briefing.md | Remove from CLAUDE.md; keep only in briefing.md (which is @imported anyway) |
| 7 | **Phase table duplicated** in CLAUDE.md and briefing.md | Remove from CLAUDE.md; briefing.md is the source of truth |
| 8 | **agent-reports.md loads every session** without path scope | Add `paths:` frontmatter or move wave timing content to `/verify` skill |
| 9 | **briefing.md Sections 4-5** are 24 lines saying "all resolved" | Collapse to single line: "All Stage 2 violations and Stage 1/3 issues resolved (2026-03-15)" |
| 10 | **@import of errors-to-rules.md may double-load** since rules/ files auto-load | Remove the `@` import from `~/.claude/CLAUDE.md`; the file is already auto-loaded as a rule. Keep the reference as plain text: "Review `~/.claude/rules/errors-to-rules.md` before starting tasks" |

### P2 — Nice to have

| # | Issue | Action |
|---|-------|--------|
| 11 | Negation-heavy phrasing (4 instances) | Rephrase as positive directives |
| 12 | Language preference duplicated in global + local | Remove from CLAUDE.local.md |
| 13 | References table in CLAUDE.md (11 lines) | Remove — Claude can discover files by reading .claude/docs/ |
| 14 | No `# Project` one-liner in siopv/CLAUDE.md | Add 1-line description: "SIOPV: LangGraph vulnerability analysis pipeline with privacy controls (master's thesis)" |
| 15 | No explicit build/test commands in siopv/CLAUDE.md | Add: `uv run pytest -x`, `uv run ruff check && ruff format`, `uv run mypy src/` |

---

## Concrete Restructuring Recommendations

### Target State After Fixes

| File | Current Lines | Target Lines | Reduction |
|------|--------------|-------------|-----------|
| `~/.claude/CLAUDE.md` | 57 | 35 | -22 (remove duplicated protocol) |
| `~/.claude/rules/errors-to-rules.md` | 117 | 40 | -77 (rule-only, no narratives) |
| `~/.claude/rules/deterministic-execution-protocol.md` | 66 | 0 | -66 (DELETE) |
| `siopv/CLAUDE.md` | 97 | 55 | -42 (remove duplicated tables, stale data) |
| `siopv/.claude/rules/agent-reports.md` | 49 | 20 | -29 (trim or move to skill) |
| `siopv/.claude/workflow/compaction-log.md` (@import removed) | 114 | 0 | -114 |
| Other files | 193 | 180 | -13 |
| **TOTAL** | **693** | **~330** | **-363 (52% reduction)** |

330 lines is still above the 200-line ideal, but represents a significant improvement. Further reductions would require moving the errors-to-rules to an on-demand read pattern (not auto-loaded).

### Proposed `siopv/CLAUDE.md` (Restructured, ~55 lines)

```markdown
# SIOPV

LangGraph vulnerability analysis pipeline with privacy controls (master's thesis).
Python 3.11, hexagonal architecture, phases 0-6 complete, phase 7 (Streamlit HITL) next.

## Critical Rules

**YOU MUST** at session start:
1. Read @.claude/workflow/briefing.md — current phase, metrics, gating status
2. Check `.claude/workflow/compaction-log.md` last 5 lines if resuming after compaction

**YOU MUST** when writing code:
3. Verify library APIs via Context7 MCP before coding
4. Use cases receive dependencies via port interfaces only (hexagonal architecture)
5. Follow `.claude/docs/python-standards.md` (read on demand)

**YOU MUST** before commit:
6. Run `/verify` — 14 verification agents; coverage floor >= current baseline
7. `ruff format && ruff check && mypy src` — all must pass clean

**Human checkpoints:**
8. PAUSE for human approval: new phase start, destructive actions, changes to >3 modules
9. After all verification agents report: present summary → wait for approval → commit

## Commands
- `uv run pytest -x` — run tests
- `uv run ruff check && uv run ruff format` — lint and format
- `uv run mypy src/` — type checking

## Graph Flow
START → authorize → ingest → dlp → enrich → classify → [escalate] → END

## Skills (invoke via `/skill-name`)
| Skill | When |
|-------|------|
| `/verify` | Before every commit |
| `/coding-standards-2026` | Python standards |
| `/langraph-patterns` | LangGraph interrupt/checkpoint |
| `/openfga-patterns` | OpenFGA auth gates |
| `/presidio-dlp` | Presidio PII/DLP |

## Compact Instructions
Preserve: current phase + status, NEXT IMMEDIATE ACTION, key file paths, metrics
```

---

## Summary

The CLAUDE.md configuration suffers from **context overload** (693 lines vs 200 recommended) caused primarily by:

1. **Full @import of compaction-log.md** (114 lines of timestamps with zero behavioral value)
2. **Complete duplication of TeamCreate protocol** across two files (66 wasted lines)
3. **Verbose error narratives** in errors-to-rules.md (77 lines of story vs actionable rules)
4. **Tables duplicated** between CLAUDE.md and briefing.md (18 wasted lines)
5. **Stale data** in CLAUDE.md contradicting the briefing.md source of truth

Applying all P0 and P1 fixes would reduce the total to ~330 lines — a 52% reduction. The most impactful single change is removing the compaction-log.md @import (saves 114 lines instantly).
