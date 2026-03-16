# Audit 05 — Memory System & Context Management

> **Date:** 2026-03-16
> **Auditor:** Memory & Context Agent
> **Reference:** `research-16march2026/06-memory-and-context.md`
> **Scope:** Auto-memory files, MEMORY.md index, compaction hooks, workflow files, context optimization

---

## Executive Summary

The SIOPV memory system is **functional but has structural issues**. The MEMORY.md index violates the "index only" principle by embedding substantial content (phase tables, metrics, file paths) instead of linking to topic files. Topic files exist and have correct frontmatter, but `project` type memories lack the required `**Why:**` / `**How to apply:**` structure. Several memories contain stale data (resolved violations, outdated metrics). The compaction setup is solid (PreCompact + SessionStart hooks), but the compaction log is growing unbounded (114 lines) and is loaded via `@import` at startup — wasting ~500+ tokens every session. No PostCompact hook is configured despite being available since January 2026.

**Scores:**
- Memory index structure: 5/10
- Topic file quality: 7/10
- Compaction setup: 7/10
- Context optimization: 6/10

---

## 1. MEMORY.md Index Findings

**Line count:** 53 lines (well under 200 limit ✅)

### Violations

| Issue | Severity | Detail |
|-------|----------|--------|
| **Content in index** | P0 | MEMORY.md contains full phase status table (11 lines), metrics section, key file paths table (7 lines), pre-phase-7 blockers, and Claude config status — all of this is *content*, not links. Per best practices: "MEMORY.md is an index, not a memory — it should contain only links to memory files with brief descriptions." |
| **Duplication with CLAUDE.md** | P1 | Phase status, key file paths, metrics baseline, and graph flow are duplicated between MEMORY.md, CLAUDE.md, and briefing.md. Per best practices: "Don't duplicate between CLAUDE.md and auto memory" and "Code patterns, conventions, architecture, file paths — derivable from current project state" should NOT be in memory. |
| **Metrics inconsistency** | P1 | MEMORY.md says "1,476 tests · 92.02% coverage" but CLAUDE.md says "1,404 tests · 83% coverage". The briefing.md has the correct values (1,476 / 92.02%). CLAUDE.md is stale. |

### Structure Assessment

Current MEMORY.md has these sections:
- `## Identity` — mixes links with inline content (project name, stack, state file)
- `## Phase Status` — full table inline (should be in briefing.md, not memory)
- `## Metrics` — inline (should be in briefing.md only)
- `## Pre-Phase 7 Blockers` — stale (all resolved), should be removed
- `## Key File Paths` — inline table (duplicated from CLAUDE.md, derivable from code)
- `## Topic Files` — correct format with links ✅
- `## Preferences` — correct format with link ✅
- `## Claude Config Status` — inline (stale, stage 4.2 pending status)

**Recommended structure** (pure index):
```markdown
# SIOPV Project Memory

## User
(none yet — should capture Bruno's role/expertise)

## Feedback
- [TeamCreate visibility](feedback_teamcreate_visibility.md) — always use TeamCreate for multi-agent visibility

## Project
- [Architecture Notes](siopv-architecture.md) — graph flow, DI pattern, LangGraph state
- [Phase 7/8 Context](siopv-phase7-8-context.md) — readiness checklist, open questions, integration risks
- [Stage Audit Results](siopv-stage-results.md) — Stage 1–4 findings, requirements summary
- [Violations + Library Facts](siopv-violations.md) — Stage 2 hex violations + Stage 3 verified facts

## References
(none yet — should capture external system pointers)
```

---

## 2. Per-Memory-File Findings

### `feedback_teamcreate_visibility.md` ✅ GOOD
- **Frontmatter:** name ✅, description ✅, type: feedback ✅
- **Body:** Has `**Why:**` and `**How to apply:**` ✅
- **Content:** Current and actionable
- **Issues:** None

### `siopv-architecture.md` — NEEDS WORK
- **Frontmatter:** name ✅, description ✅, type: project ✅
- **Body:** Missing `**Why:**` and `**How to apply:**` lines (required for project type per best practices)
- **Content:** Mix of current facts and future-phase planning
- **Issues:**
  - P2: No `**Why:**` / `**How to apply:**` structure
  - P2: "Phase 7 State Additions" and "Phase 8 Topology Changes" are planning notes — should be in phase7-8-context or removed after implementation

### `siopv-phase7-8-context.md` — PARTIALLY STALE
- **Frontmatter:** name ✅, description ✅, type: project ✅
- **Body:** Missing `**Why:**` / `**How to apply:**` (required for project type)
- **Content:** Phase 7 prerequisites show unchecked boxes `[ ]` for items marked resolved in briefing.md
- **Issues:**
  - P1: Stale prerequisites — briefing says "All violations resolved in remediation-hardening (2026-03-15)" but this file shows `[ ] Stage 2 violations #1, #2, #3 remediated`
  - P2: No `**Why:**` / `**How to apply:**` structure

### `siopv-stage-results.md` — PARTIALLY STALE
- **Frontmatter:** name ✅, description ✅, type: project ✅
- **Body:** Missing `**Why:**` / `**How to apply:**`
- **Content:** "STAGE-4.2: ⏳ PENDING" — may be stale if Stage 4.2 is complete
- **Issues:**
  - P2: Verify if Stage 4.2 is still pending or was completed in remediation-hardening
  - P2: References absolute path to audit reports that may have been moved

### `siopv-violations.md` — PARTIALLY STALE
- **Frontmatter:** name ✅, description ✅, type: project ✅
- **Body:** Missing `**Why:**` / `**How to apply:**`
- **Content:** Lists 7 violations all marked resolved in briefing.md. The "Stage 3 Verified Library Facts" section remains valuable.
- **Issues:**
  - P1: Violation table is stale (all resolved) — should be archived or removed
  - P2: Split into two files: archive violations, keep library facts as active reference
  - P2: No `**Why:**` / `**How to apply:**`

### Missing Memory Types
- **No `user` type memories** — who is Bruno? Master's student? Security professional? What's his expertise level? This would help Claude tailor responses.
- **No `reference` type memories** — no external system pointers (where are Jira boards, GitHub repos, documentation sites, OpenFGA admin UIs?)

---

## 3. Compaction Setup Findings

### Hooks Configuration

| Hook | Status | Notes |
|------|--------|-------|
| **PreCompact** | ✅ Configured | Two handlers: (1) inline context echo, (2) async `pre-compact.sh` that spawns `claude -p` for recovery brief |
| **SessionStart** | ✅ Configured | Three handlers: (1) general briefing injection, (2) daily checkpoint reminder, (3) `compact` matcher for post-compaction context |
| **SessionEnd** | ✅ Configured | Logs to JSONL + updates briefing timestamp |
| **PostCompact** | ❌ NOT configured | Available since January 2026. Could inject `compact_summary` into a log or trigger recovery actions. Currently missing. |

### PreCompact Hook Analysis (`pre-compact.sh`)
- **Strengths:**
  - Handles bug #13668 (null transcript_path) with fallback ✅
  - Generates recovery brief from transcript tail (spawned async) ✅
  - Updates briefing.md timestamp ✅
  - Appends to compaction log ✅
- **Issues:**
  - P2: Recovery brief files (`pre-compact-brief-*.md`) accumulate in `.claude/workflow/` — no cleanup mechanism
  - P2: The `claude -p` subprocess uses default model (potentially Opus) for a 30-line summary — should specify `--model haiku` for cost efficiency

### SessionStart Hook Analysis (`session-start.sh`)
- **Strengths:**
  - Idempotency guard with lock file ✅ (handles `--continue` double-fire bug)
  - Injects full briefing.md content via stdout ✅
  - Shows last 5 compaction log entries ✅
- **Issues:**
  - P2: Lock file at `/tmp/siopv-session-start-*.lock` is never cleaned up — accumulates stale lock files. Should be cleaned in SessionEnd.
  - P1: No `compact` matcher on this handler — it fires on ALL session starts (startup, resume, compact, clear). The separate `compact` matcher in settings.json handles the post-compact case, but the main handler also fires during compaction, injecting briefing.md twice (once from this handler, once from the `@import` in CLAUDE.md).

### Compact Instructions in CLAUDE.md
- ✅ Has "Compact Instructions" section at the end
- ✅ Specifies what to preserve (phase, NEXT ACTION, file paths, metrics)
- ❌ Does not mention preserving "current task in progress" or "uncommitted changes"

---

## 4. Workflow File Findings

### `briefing.md`
- **Line count:** ~93 lines — compact and efficient ✅
- **COMPACT-SAFE header:** Has `> If you just compacted:` instruction at top ✅ (functional equivalent)
- **Content:** Well-structured with clear sections for identity, status, architecture, violations, known issues
- **Issues:**
  - P2: No explicit `<!-- COMPACT-SAFE -->` marker (cosmetic, the functional instruction exists)
  - P0: Section "4. OPEN VIOLATIONS" and "5. KNOWN ISSUES" both say "All resolved... See .ignorar/production-reports/remediation/" — these sections can be collapsed to a single line each to save ~6 lines of context

### `compaction-log.md`
- **Line count:** 114 lines — **growing unbounded** ❌
- **Content:** Pure timestamp entries with no pruning mechanism
- **Issues:**
  - P0: This file is loaded via `@.claude/workflow/compaction-log.md` in CLAUDE.md at EVERY session start, consuming ~500+ tokens for historical timestamps that are never useful. Only the last 5 entries matter (and the session-start hook already shows those separately).
  - P0: CLAUDE.md says "Read @.claude/workflow/compaction-log.md (last 5 lines)" but `@import` loads the ENTIRE file. There is NO partial/lazy loading for `@imports`.
  - P1: No rotation/pruning — will continue growing. Should prune to last 20 entries periodically.
  - P1: Many duplicate/burst entries (e.g., 2026-03-16T07:51:24Z through 07:51:38Z shows 15 SessionEnd events in 14 seconds — likely from mass session cleanup)

---

## 5. Context Optimization Findings

### @import Analysis in CLAUDE.md

| Import | Lines | Loaded At | Issue |
|--------|-------|-----------|-------|
| `@.claude/workflow/briefing.md` | ~93 | Every session start | Acceptable — critical recovery doc |
| `@.claude/workflow/compaction-log.md` | 114 | Every session start | **P0: Wasteful** — only last 5 lines matter, but all 114 load. Remove `@import`, rely on session-start hook which already shows `tail -n 5` |

### Duplication Map

| Content | MEMORY.md | CLAUDE.md | briefing.md | Cost |
|---------|-----------|-----------|-------------|------|
| Phase status table | ✅ inline | ✅ inline | ✅ inline | 3x redundancy |
| Key file paths | ✅ inline | ✅ inline | ✅ inline | 3x redundancy |
| Metrics baseline | ✅ inline | ✅ inline | ✅ inline | 3x redundancy (with inconsistent values!) |
| Graph flow | ✅ inline | ✅ inline | ✅ inline | 3x redundancy |
| Gating conditions | ❌ | ✅ inline | ✅ inline | 2x redundancy |

**Total wasted context from duplication:** ~50+ lines × 3 locations ≈ 100+ unnecessary lines loaded at startup.

### Token Budget Assessment

Estimating startup context cost:
- CLAUDE.md: ~98 lines → ~600 tokens
- briefing.md (via @import): ~93 lines → ~550 tokens
- compaction-log.md (via @import): ~114 lines → ~500 tokens (⚠️ wasteful)
- MEMORY.md: ~53 lines → ~350 tokens
- Rules (unconditional): agent-reports.md + placeholder-conventions.md + errors-to-rules.md → ~200+ tokens
- CLAUDE.local.md: ~40 lines → ~250 tokens
- Total: ~2,450+ tokens before any conversation starts

The compaction log alone accounts for ~20% of the memory/docs budget and provides near-zero value (session-start hook already shows the relevant tail).

---

## 6. Prioritized Fix List

### P0 — Critical (fix immediately)

| # | Finding | Fix |
|---|---------|-----|
| 1 | **compaction-log.md @import wastes ~500 tokens every session** | Remove `@.claude/workflow/compaction-log.md` import from CLAUDE.md line 7. The session-start hook already injects last 5 entries via `tail -n 5`. Change instruction to: "Check compaction-log.md if you need session history (read on demand)." |
| 2 | **MEMORY.md contains content instead of being a pure index** | Refactor: move Identity/Phase Status/Metrics/File Paths/Config Status into topic files or remove (already in briefing.md). Keep only links. |
| 3 | **compaction-log.md growing unbounded (114 lines, no pruning)** | Add rotation to session-end.sh: `tail -n 30 "$COMPACT_LOG" > "$COMPACT_LOG.tmp" && mv "$COMPACT_LOG.tmp" "$COMPACT_LOG"`. Or add a weekly cron. |

### P1 — Important (fix soon)

| # | Finding | Fix |
|---|---------|-----|
| 4 | **Metrics inconsistency** — CLAUDE.md says 1,404/83%, briefing says 1,476/92% | Update CLAUDE.md metrics baseline to match current briefing values |
| 5 | **Stale violation data in siopv-violations.md** | Archive the resolved violations table; keep the "Stage 3 Verified Library Facts" section as its own file |
| 6 | **Stale prerequisites in siopv-phase7-8-context.md** | Update checkbox items to reflect remediation-hardening resolution |
| 7 | **No PostCompact hook configured** | Add PostCompact hook to settings.json that logs `compact_summary` for debugging and optionally injects context |
| 8 | **Double briefing injection on compact** | SessionStart hook fires on ALL matchers including `compact`, AND the separate `compact` matcher also fires. Briefing.md is also loaded via @import. Triple injection. Add `compact` exclusion to the general SessionStart handler OR remove the @import for briefing.md (since the hook already injects it). |
| 9 | **Lock files never cleaned up** | Add cleanup of `/tmp/siopv-session-start-*.lock` to session-end.sh |

### P2 — Nice to have

| # | Finding | Fix |
|---|---------|-----|
| 10 | **No `user` type memory** | Create `user_bruno.md` capturing: master's student, security/ML focus, thesis project, Spanish/English bilingual |
| 11 | **No `reference` type memory** | Create reference memories for external systems (Jira instance, GitHub repo, OpenFGA admin, documentation locations) |
| 12 | **Project-type memories missing Why/How structure** | Add `**Why:**` and `**How to apply:**` to siopv-architecture.md, siopv-phase7-8-context.md, siopv-stage-results.md, siopv-violations.md |
| 13 | **Pre-compact recovery briefs accumulate** | Add cleanup of old `pre-compact-brief-*.md` files (keep last 3) |
| 14 | **pre-compact.sh uses default model for summary** | Add `--model haiku` to the `claude -p` call for cost efficiency |
| 15 | **briefing.md resolved sections waste space** | Collapse "OPEN VIOLATIONS" and "KNOWN ISSUES" sections to one-liners |

---

## 7. Cross-Project Observations

Other project memory directories found:
- `-Users-bruno-sec-llm-workbench` (427 items — heavily used)
- `-Users-bruno-MySportStats-app-frontend` (63 items)
- `-Users-bruno-SIOPV` (122 items — this project, case-sensitive variant)
- `-Users-bruno-siopv` (separate from `-Users-bruno-SIOPV`)

**Note:** There appear to be TWO project directories: `-Users-bruno-SIOPV` and `-Users-bruno-siopv`. This may indicate case sensitivity issues or a git remote rename. Both should be checked for orphaned memory.

---

## Summary

The memory system is **functional but structurally non-compliant** with best practices. The three highest-impact fixes are:
1. Remove the compaction-log `@import` (saves ~500 tokens/session)
2. Refactor MEMORY.md to be a pure index (eliminate 3x content duplication)
3. Add log rotation to prevent unbounded growth

The compaction hooks are well-designed (especially the PreCompact recovery brief generator and SessionStart idempotency guard) but need minor tuning (PostCompact hook, lock cleanup, double-injection). Memory files need staleness review and structural compliance (Why/How lines for project type).
