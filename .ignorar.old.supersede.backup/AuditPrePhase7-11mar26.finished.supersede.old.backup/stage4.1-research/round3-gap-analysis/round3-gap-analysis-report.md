# Round 3 — Gap Analysis Report: SIOPV Claude Code Configuration
**Generated:** 2026-03-13
**Sources:** Round 1 (online best practices) + Round 2 (meta-project inventory scan)
**Target:** `siopv/.claude/` — Phases 7 and 8 implementation

---

## Current State of `siopv/.claude/`

One file exists: `settings.local.json` (7 lines, single curl allow rule). No CLAUDE.md, no agents, no hooks, no skills, no rules, no docs. All configuration must be built.

---

## Section 1: What Is Correct (COPY / ADAPT)

### Agents (15 of 23 meta-agents are applicable)

| Agent File | Action | Rationale |
|-----------|--------|-----------|
| `agents/best-practices-enforcer.md` | ADAPT | Core verifier — change `.build/active-project` path to hardcoded `siopv/` |
| `agents/security-auditor.md` | ADAPT | Same path adaptation; SIOPV-specific: check OpenFGA tuples, Presidio config |
| `agents/hallucination-detector.md` | ADAPT | Path adaptation only |
| `agents/code-reviewer.md` | ADAPT | Path adaptation; add Phase 7/8 patterns (Streamlit fragments, ADF format) |
| `agents/test-generator.md` | ADAPT | Path + coverage floor (83% current baseline from MEMORY.md) |
| `agents/async-safety-auditor.md` | ADAPT | Critical for Phase 7 — Streamlit requires sync bridge; add `asyncio.run()` detection |
| `agents/semantic-correctness-auditor.md` | ADAPT | Path adaptation only |
| `agents/integration-tracer.md` | ADAPT | Path adaptation; add LangGraph node → port tracing |
| `agents/smoke-test-runner.md` | ADAPT | Path adaptation |
| `agents/config-validator.md` | ADAPT | Path adaptation; add Streamlit env var checks |
| `agents/code-implementer.md` | ADAPT | Path adaptation; add SIOPV Phase 7/8 library patterns (Stage 3 findings) |
| `agents/dependency-scanner.md` | ADAPT | Path adaptation only |
| `agents/circular-import-detector.md` | ADAPT | Path adaptation only |
| `agents/import-resolver.md` | ADAPT | Path adaptation only |
| `agents/xai-explainer.md` | ADAPT | Already SIOPV-applicable per Stage 4 pre-task inventory |

**R1 Evidence:** Round 1 §1 confirms agent files load from `.claude/agents/` — project-level wins over user-level conflicts.

### Hooks (6 active meta-hooks are correct patterns)

| Hook | Action | Rationale |
|------|--------|-----------|
| `hooks/session-start.sh` | ADAPT | Inject SIOPV briefing.md; remove `.build/active-project` lookup logic |
| `hooks/session-end.sh` | ADAPT | Update SIOPV briefing.md timestamp; remove meta-project paths |
| `hooks/pre-compact.sh` | ADAPT | Preserve SIOPV Phase 7/8 context; update paths |
| `hooks/post-code.sh` | COPY | Checkpoint marker creation is universal (ruff + pending marker) |
| `hooks/pre-git-commit.sh` | COPY | Commit gate is universal; works on any Python project |
| `hooks/pre-write.sh` | COPY | Daily checkpoint reminder is universal |

**R1 Evidence:** Round 1 §3 confirms `PreCompact` is the correct hook (not `PostCompact` — doesn't exist). `SessionStart` with `compact` matcher is unreliable (bug #15174) — `PreCompact` is the right approach.

### Settings, Rules, Docs, Skills

| File | Action | Rationale |
|------|--------|-----------|
| `settings.json` (structure/patterns) | ADAPT | Security deny list, compaction override, agent teams enable, sandbox — all correct |
| `rules/agent-reports.md` | COPY | Timestamp UUID naming is universal; prevents race conditions |
| `rules/placeholder-conventions.md` | COPY | Syntax standards apply to SIOPV |
| `docs/model-selection-strategy.md` | COPY | sonnet/haiku/opus routing is universal |
| `docs/python-standards.md` | COPY | Python 3.11+, uv, Pydantic v2, httpx, structlog — exact SIOPV stack |
| `docs/verification-thresholds.md` | ADAPT | Add SIOPV coverage floor: 83% minimum baseline |
| `skills/verify/` | ADAPT | Reduce to 9 agents (drop 3 meta-only haiku utilities); update paths |
| `skills/langraph-patterns/` | COPY | Verified correct patterns for Phase 7 (Stage 3 confirmed) |
| `skills/openfga-patterns/` | COPY | Used in Phase 5; needed for Phase 7 auth gate |
| `skills/presidio-dlp/` | COPY | Used in Phase 6; needed for Phase 7 DLP node |

---

## Section 2: What Is Stale or Incorrect

| # | Severity | File | Issue | Evidence |
|---|----------|------|-------|----------|
| 1 | HIGH | `~/.claude/CLAUDE.md` lines 133 | `mode="bypassPermissions"` in orchestrator spawn protocol | R2 §4 #6: documented as broken. R2 §2: `errors-to-rules.md` rule #10 explicitly says it doesn't work without `--dangerously-skip-permissions`. Fix: change to `mode="acceptEdits"` |
| 2 | HIGH | `~/.claude/projects/.../memory/MEMORY.md` | 217 lines — lines 201–217 silently truncated every session. Hook Classification section (Stage 4 reuse data) is invisible | R1 §2: hard cut at 200 lines. R2 §4 #1: confirmed live defect |
| 3 | MEDIUM | `hooks/pre-commit.sh`, `hooks/test-framework.sh`, `hooks/verify-best-practices.sh` | Not registered in `settings.json` — orphaned scripts | R2 §4 #2: confirmed unregistered. Audit or delete |
| 4 | MEDIUM | `agents/researcher-1.md`, `researcher-2.md`, `researcher-3.md` | No `## Project Context (CRITICAL)` block — cannot auto-determine target project path | R2 §4 #3: confirmed. All other 20 agents have this block |
| 5 | LOW | `settings.json.back` | Orphaned backup file — confusing if referenced | R2 §4 #4 |
| 6 | LOW | Any agent/doc referencing `claude-opus-4` or `claude-opus-4-1` | Model IDs removed in v2.1.68 — auto-migrated but references are stale | R1 §9: "Opus 4 / 4.1 models: removed v2.1.68, auto-migrated to Opus 4.6" |

---

## Section 3: What Must Be Added (NEW)

| File | Content Description | Justification |
|------|---------------------|---------------|
| `siopv/.claude/CLAUDE.md` | SIOPV project instructions: Context7 mandate, /verify mandate, Phase 7/8 current state, @-imports for session-start + before-commit + human-checkpoints, Compact Instructions block | R1 §6: CLAUDE.md survives /compact. Must be < 200 lines |
| `siopv/.claude/agents/hex-arch-remediator.md` | Specialized agent to fix Stage 2 hexagonal violations (#1–#7): move adapter imports, wire DI ports, extract domain logic from edges | Stage 2 found 2 CRITICAL + 5 HIGH violations. No existing agent targets hex-arch fixes |
| `siopv/.claude/agents/phase7-builder.md` | Phase 7 (Streamlit) builder: `@st.fragment(run_every="15s")`, `ThreadPoolExecutor` async bridge, `st.cache_resource`, `interrupt()` with checkpointer, LIME `plt.close(fig)` | Stage 3 verified library facts: all 9 Streamlit/LangGraph patterns confirmed |
| `siopv/.claude/agents/phase8-builder.md` | Phase 8 (Jira+PDF) builder: ADF format for Jira descriptions, `httpx.AsyncClient` (not sync), `fpdf2` with `fname` in `add_font()`, exact 3 topology changes in `graph.py._add_edges()` | Stage 3 confirmed: plain Jira strings rejected; fpdf2 `fname` is breaking change since 2.7 |
| `siopv/.claude/hooks/coverage-gate.sh` | PostToolUse hook: after pytest, check coverage ≥ 83%. Block if below. Creates pending marker same as `post-code.sh` | R1 §3: `PostToolUse` hook fires after tool success. Current coverage is 83% — must not regress |
| `siopv/.claude/docs/siopv-phase7-8-context.md` | Distilled Stage 3 library facts: Streamlit patterns, LangGraph interrupt, Jira ADF, fpdf2 API, Redis key conventions, OTel ordering, LIME memory leak prevention, LangSmith integration | Stage 3 found 12 gaps vs MEMORY.md. code-implementer needs this loaded at context start |
| `siopv/.claude/docs/errors-to-rules.md` | SIOPV-specific error log (separate from global). Seed with Stage 2 violation patterns | R2 §1: meta-project has project-specific errors-to-rules.md in `.claude/docs/`. Global one is cross-project only |
| `siopv/.claude/workflow/briefing.md` | SIOPV session briefing: current phase (7 pending), last checkpoint, open Stage 2 violations, Phase 7 gating conditions (5 Phase-0 items + REQ-P6-006). Injected by session-start.sh | R2 §1: briefing injection system is the compaction-proof continuity mechanism. Stage 3.5 found 6 gaps in reference docs |
| `siopv/.claude/workflow/compaction-log.md` | Auto-maintained log of compaction events (updated by pre-compact.sh + session-end.sh). Provides cross-session continuity | R2 §1: session-start.sh injects last 5 lines of this file on every session start |
| `siopv/.claude/skills/siopv-remediate/` | Skill: triggers hex-arch-remediator agent for Stage 2 violation fixes. `disable-model-invocation: true` so user must invoke explicitly | R1 §5: skills with `disable-model-invocation: true` prevent accidental auto-invocation of destructive operations |
| `~/.claude/projects/.../memory/siopv-hooks-stage4.md` | New topic file: Hook Classification section content (16 agents SIOPV-APPLICABLE, 4 ADAPTABLE, 3 META-ONLY) | Fixes MEMORY.md truncation — moves lines 201–217 to a topic file, referenced from MEMORY.md index |

---

## Section 4: What Must Be Modified

| File | Change | Evidence |
|------|--------|---------|
| `~/.claude/CLAUDE.md` | Line 133: change `mode="bypassPermissions"` → `mode="acceptEdits"` in orchestrator spawn protocol | R2 §4 #6 + errors-to-rules rule #10 |
| `~/.claude/projects/.../memory/MEMORY.md` | Trim to ≤ 200 lines. Move "Hook Classification" block (lines 201–217) to new topic file `siopv-hooks-stage4.md`. Add pointer line in MEMORY.md index | R1 §2: hard 200-line limit. R2 §4 #1: confirmed truncation |
| `agents/researcher-1.md`, `researcher-2.md`, `researcher-3.md` | Add `## Project Context (CRITICAL)` block matching other agents. Include `.build/active-project` read + fallback path | R2 §4 #3: confirmed missing |
| `siopv/.claude/settings.local.json` (existing) | Replace curl-only allow with proper project-level permissions: add uv, ruff, mypy, pytest, git subcommands, ls, tree, jq, date; deny .env*, credentials*; sandbox | R2 §1: current file has only one rule. R1 §4: permissions merge across scopes — project adds to user-level |
| `siopv/.claude/docs/verification-thresholds.md` (when created) | Add SIOPV-specific floor: `pytest --cov ≥ 83%` (current baseline). Add Phase 7 threshold: Streamlit app health check passes | R2 §5: current coverage 83% from MEMORY.md metrics |

---

## Section 5: What to DO NOT INCLUDE

| File | Why Meta-Only | Risk if Included |
|------|---------------|-----------------|
| `workflow/briefing.md` (meta-project version) | Contains SIOPV audit stage state for meta-orchestration — references meta-project paths and stage execution, not SIOPV app development | Confusion between meta audit context and SIOPV implementation context |
| `workflow/orchestrator-briefing.md` | Meta-project orchestrator spawn briefing for running audit stages (1, 2, 3, 3.5, 4.x) | SIOPV doesn't need stage orchestration — it needs phase implementation |
| `workflow/setup-checklist.md` | Meta-project project setup checklist | Would add irrelevant setup requirements to SIOPV sessions |
| `workflow/spec-findings.md` | Meta-project specification findings tracker | SIOPV findings are in Stage 1–3 reports, not this file |
| `agents/final-report-agent.md` | Stage 4 inventory classified META-ONLY. Generates audit-stage summaries, not SIOPV code | Would be auto-delegated incorrectly for SIOPV coding tasks |
| `agents/report-summarizer.md` | Stage 4 inventory classified META-ONLY. Aggregates audit reports | Same as above |
| `agents/vulnerability-researcher.md` | Stage 4 inventory classified META-ONLY. CVE/OSINT research for meta-project audits | SIOPV has `cve-research` skill for CVE lookups — separate concern |
| `scripts/` (12 files) | Cost tracking, MCP health, parallel verification scripts are meta-project infrastructure | Would add non-functional scripts with wrong paths |
| `handoffs/` (9 files) | Dated session handoff briefs for meta-project continuity | SIOPV gets its own `briefing.md` — these are irrelevant |
| `.build/active-project` mechanism | Multi-project routing for meta-project's target switching | SIOPV is a single project — `active-project` indirection adds complexity with no benefit |

---

## Section 6: Directory Structure

```
siopv/.claude/
├── CLAUDE.md                                    [NEW]
├── settings.json                                [NEW]   ← full project config
├── settings.local.json                          [ADAPT] ← expand from current 7-line file
├── agents/
│   ├── best-practices-enforcer.md               [ADAPT]
│   ├── security-auditor.md                      [ADAPT]
│   ├── hallucination-detector.md                [ADAPT]
│   ├── code-reviewer.md                         [ADAPT]
│   ├── test-generator.md                        [ADAPT]
│   ├── async-safety-auditor.md                  [ADAPT] ← add Streamlit sync-bridge checks
│   ├── semantic-correctness-auditor.md          [ADAPT]
│   ├── integration-tracer.md                    [ADAPT]
│   ├── smoke-test-runner.md                     [ADAPT]
│   ├── config-validator.md                      [ADAPT]
│   ├── dependency-scanner.md                    [ADAPT]
│   ├── circular-import-detector.md              [ADAPT]
│   ├── import-resolver.md                       [ADAPT]
│   ├── code-implementer.md                      [ADAPT] ← embed Phase 7/8 library patterns
│   ├── xai-explainer.md                         [ADAPT]
│   ├── hex-arch-remediator.md                   [NEW]   ← Stage 2 violations
│   ├── phase7-builder.md                        [NEW]   ← Streamlit/LangGraph Phase 7
│   └── phase8-builder.md                        [NEW]   ← Jira+PDF Phase 8
├── hooks/
│   ├── session-start.sh                         [ADAPT] ← inject siopv briefing.md
│   ├── session-end.sh                           [ADAPT] ← update siopv briefing.md
│   ├── pre-compact.sh                           [ADAPT] ← preserve Phase 7/8 context
│   ├── post-code.sh                             [COPY]
│   ├── pre-git-commit.sh                        [COPY]
│   ├── pre-write.sh                             [COPY]
│   └── coverage-gate.sh                         [NEW]   ← pytest cov ≥ 83% gate
├── rules/
│   ├── agent-reports.md                         [COPY]
│   ├── placeholder-conventions.md               [COPY]
│   └── tech-stack.md                            [ADAPT] ← add Streamlit, fpdf2, redis.asyncio, LangSmith
├── docs/
│   ├── verification-thresholds.md               [ADAPT] ← add coverage floor
│   ├── model-selection-strategy.md              [COPY]
│   ├── python-standards.md                      [COPY]
│   ├── errors-to-rules.md                       [NEW]   ← SIOPV-specific log
│   └── siopv-phase7-8-context.md                [NEW]   ← Stage 3 library facts
├── skills/
│   ├── verify/                                  [ADAPT] ← 15 agents (drop 3 meta-only)
│   ├── langraph-patterns/                       [COPY]
│   ├── openfga-patterns/                        [COPY]
│   ├── presidio-dlp/                            [COPY]
│   ├── coding-standards-2026/                   [COPY]
│   └── siopv-remediate/                         [NEW]   ← triggers hex-arch-remediator
└── workflow/
    ├── briefing.md                              [NEW]   ← SIOPV current state
    └── compaction-log.md                        [NEW]   ← session continuity log
```

**Total: 39 files** — 15 ADAPT, 15 COPY, 9 NEW

---

## Section 7: User-Level Changes

| File | Change | Why |
|------|--------|-----|
| `~/.claude/projects/.../memory/MEMORY.md` | **URGENT:** Trim to ≤ 200 lines. Move lines 201–217 ("Hook Classification" block) to new topic file `siopv-hooks-stage4.md`. Add one pointer line: `- [Stage 4 Hook Classification](siopv-hooks-stage4.md)` | R1 §2: 200-line hard cut. R2 §4 #1: Stage 4 reuse data invisible every session — live defect |
| `~/.claude/projects/.../memory/siopv-hooks-stage4.md` | **NEW topic file:** Full hook classification table (23 agents: 16 SIOPV-APPLICABLE, 4 ADAPTABLE, 3 META-ONLY). 9 hooks classification. | Extracted from MEMORY.md to respect 200-line limit |
| `~/.claude/CLAUDE.md` | Line with `mode="bypassPermissions"` in orchestrator spawn protocol → `mode="acceptEdits"` | errors-to-rules rule #10: `bypassPermissions` only works with `--dangerously-skip-permissions` session flag. Using wrong mode silently fails |
| `~/.claude/settings.json` | Add `"attribution": {"commit": "none"}` if not present at user level | R2 §3: currently only in meta-project settings.json. Should be global for all projects |
| `~/.claude/agents/researcher-1.md`, `researcher-2.md`, `researcher-3.md` | Add `## Project Context (CRITICAL)` block with `.build/active-project` read + fallback | R2 §4 #3: all other 20 agents have this block; these 3 are broken without it |

---

## Summary

| Category | Count |
|----------|-------|
| Correct patterns to COPY | 15 files |
| Meta-project items to ADAPT | 15 files |
| New files to create for SIOPV | 9 files |
| Stale/broken items to fix | 6 issues |
| User-level changes required | 5 items |
| DO NOT INCLUDE (meta-only) | 10 items |

**Critical path for Stage 4.2:**
1. Fix MEMORY.md truncation (live defect — data loss every session)
2. Fix `bypassPermissions` in `~/.claude/CLAUDE.md`
3. Create `siopv/.claude/CLAUDE.md` + `settings.json` (no project config exists)
4. Adapt 9 core verification agents + hooks for SIOPV paths
5. Create `phase7-builder.md` + `phase8-builder.md` + `hex-arch-remediator.md`
6. Create `siopv-phase7-8-context.md` (Stage 3 library facts for code-implementer)
