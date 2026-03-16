# Truth-02: SIOPV CLAUDE.md + CLAUDE.local.md
**Generated:** 2026-03-13
**Authority:** Round 1 best practices (§6) + Round 3 gap analysis (§3) + truth-00 structure
**Scope:** Complete content for `siopv/CLAUDE.md` and `siopv/.claude/CLAUDE.local.md`

---

## 1. CLAUDE.md — Complete Content

Save to: `siopv/CLAUDE.md`

**Line count: 97 lines** (well under 200-line target)

```markdown
# SIOPV — Guía de Implementación

## CRITICAL RULES

**YOU MUST** at session start:
1. Read @.claude/workflow/briefing.md — current phase, open violations, gating conditions
2. Read @.claude/workflow/compaction-log.md (last 5 lines) — cross-session continuity

**YOU MUST** when writing code:
3. Query Context7 MCP BEFORE using any external library — NEVER rely on training data
4. Enforce hexagonal architecture: domain → ports → adapters; NO cross-layer imports
5. NEVER import adapter classes directly in use cases (Stage 2 violations #1 and #2)
6. Follow `.claude/docs/python-standards.md` (read on demand)

**YOU MUST** before commit:
7. Execute `/verify` — runs 15 verification agents; coverage floor ≥ 83%
8. ruff format && ruff check && mypy src — all must pass clean

**IMPORTANT** — Human checkpoints:
9. PAUSE for human approval: new phase start, destructive actions, changes to >3 modules
10. After ALL verification agents report: present summary → wait for approval → then commit

---

## SIOPV Project State

| Phase | Name | Status |
|-------|------|--------|
| 0–6   | Setup through DLP | ✅ Complete |
| 7     | Human-in-the-Loop (Streamlit) | ⏳ PENDING — see gating conditions |
| 8     | Output (Jira + PDF) | ⏳ PENDING |

**Graph flow:** START → authorize → ingest → dlp → enrich → classify → [escalate] → END
**Checkpointer:** SQLite (`siopv_checkpoints.db`) — required for `interrupt()` to work
**Metrics baseline:** 1,404 tests passing · 83% coverage · 0 mypy · 0 ruff errors

---

## Phase 7 Gating Conditions

ALL of these must be resolved before starting Phase 7 (check briefing.md for current status):
1. 5 Phase-0 MISSING: Dockerfile · detect-secrets hook · .env.example · Conventional Commits · structlog masking
2. REQ-P6-006: DLP must be pre-logging filter (not audit-only post-logging)
3. Stage 2 hexagonal violations #1–#7 all resolved → use `/siopv-remediate`

---

## Key File Paths

| Component | Path |
|-----------|------|
| Graph | `src/siopv/application/orchestration/graph.py` |
| State | `src/siopv/application/orchestration/state.py` |
| CLI entry | `src/siopv/interfaces/cli/main.py` |
| Settings | `src/siopv/infrastructure/config/settings.py` |
| DI root | `src/siopv/infrastructure/di/__init__.py` |
| DI: DLP | `src/siopv/infrastructure/di/dlp.py` |
| Constants | `src/siopv/domain/constants.py` |
| Logging setup | `src/siopv/infrastructure/logging/setup.py` |

---

## References (read on demand — NOT auto-loaded)

| Topic | File |
|-------|------|
| Phase 7/8 library patterns | `.claude/docs/siopv-phase7-8-context.md` |
| Verification thresholds + coverage | `.claude/docs/verification-thresholds.md` |
| Model selection (sonnet/opus/haiku) | `.claude/docs/model-selection-strategy.md` |
| Python 2026 standards | `.claude/docs/python-standards.md` |
| SIOPV error log | `.claude/docs/errors-to-rules.md` |
| Tech stack versions | `.claude/rules/tech-stack.md` |
| Agent report naming convention | `.claude/rules/agent-reports.md` |

---

## Skills (invoke via `/skill-name`)

| Skill | When to use |
|-------|-------------|
| `/verify` | Before every commit — runs 15 agents |
| `/siopv-remediate` | Fix Stage 2 hex-arch violations #1–#7 |
| `/coding-standards-2026` | Python standards quick reference |
| `/langraph-patterns` | LangGraph interrupt/checkpoint patterns |
| `/openfga-patterns` | OpenFGA auth gate patterns |
| `/presidio-dlp` | Presidio PII/DLP patterns |

---

## Compact Instructions

> **IMPLEMENTING AGENT:** Use the Compact Instructions block from `truth-11-compaction-proof-session-continuity.md` Section 5 verbatim — NOT this placeholder. The canonical block is defined there (Conflict #3 resolution). Do not use the list below.
```

---

## 2. CLAUDE.local.md — Complete Content

Save to: `siopv/.claude/CLAUDE.local.md`
(Not committed to git — add to `.gitignore`)

**Line count: 37 lines**

```markdown
# SIOPV — Local Configuration (not committed to git)

## Local Preferences

- Language: Spanish or English (both accepted)
- Model default: claude-sonnet-4-6 (cost/quality balance for implementation tasks)
- Use `mode: acceptEdits` in agent spawns — bypassPermissions does NOT work without
  `--dangerously-skip-permissions` session flag (see global errors-to-rules #10)

## Local Paths

| Resource | Path |
|----------|------|
| Audit reports | `~/siopv/AuditPrePhase7-11mar26/` |
| Production reports | `~/siopv/.ignorar/production-reports/` |
| Checkpoints DB | `~/siopv/siopv_checkpoints.db` |

## Excluded CLAUDE.md Files

If the testing-kit CLAUDE.md conflicts with project rules, exclude via `claudeMdExcludes`
in `settings.local.json`:
```json
{
  "claudeMdExcludes": ["testing-kit/claude/CLAUDE.md"]
}
```

## Local Debug Flags (set in shell before `claude`)

```bash
# LangGraph verbose tracing
export SIOPV_LOG_LEVEL=DEBUG

# LangSmith tracing (Phase 7/8)
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=<your-key>
export LANGCHAIN_PROJECT=siopv-phase7
```
```

---

## 3. Design Decisions

### Why each section is included

| Section | Rationale |
|---------|-----------|
| Critical rules (lines 1–20) | R1 §6: front-load with `YOU MUST` / `IMPORTANT` emphasis. Rules 1–10 cover the three mandatory workflows (session start, code writing, commit). |
| SIOPV Project State | Eliminates the need to query briefing.md for phase status — always visible. Graph flow prevents Claude from misrouting nodes. Metrics baseline anchors coverage gate. |
| Phase 7 Gating Conditions | Stage 3.5 found these absent from both reference docs. Without them, Phase 7 would start with hexagonal violations and DLP defect still live. |
| Key File Paths | Eight paths that are touched in every phase — avoids redundant Glob calls at session start. |
| References (on-demand) | R1 §6: use `@` imports only for files loaded every session; everything else is a path reference read on demand. Keeps CLAUDE.md under 200 lines. |
| Skills table | Surfaces the six task-specific skills — avoids agents re-implementing patterns already in skills. |
| Compact Instructions | R1 §6: `## Compact Instructions` section is preserved verbatim through `/compact` — the six items listed are the minimum context needed to resume either phase. |

### What was removed vs. meta-project version and why

| Removed | Why |
|---------|-----|
| `@.claude/workflow/01-session-start.md` reference | Meta-project session start handles multi-project routing via `.build/active-project`. SIOPV is a single project — briefing.md replaces it with direct state. |
| `@.claude/workflow/05-before-commit.md` | Inlined the commit rules directly (only 2 lines) — adding a file hop for 2 lines violates the under-200 target without benefit. |
| `@.claude/workflow/03-human-checkpoints.md` | Checkpoint rule is 2 lines in CLAUDE.md (rules 9–10). The detailed flow diagram is in briefing.md. No separate file needed. |
| Reflexion Loop reference | Meta-project-specific orchestration pattern. SIOPV uses standard verification loop via `/verify` skill. |
| Techniques catalog / orchestrator-protocol | META-ONLY skills — excluded per truth-00 §4. |
| `.build/active-project` mechanism | Multi-project routing only. SIOPV is a single project — adds indirection with no benefit. |
| `02-reflexion-loop.md`, `04-agents.md`, `06-decisions.md`, `07-orchestrator-invocation.md` | Meta-project workflow files not applicable to SIOPV implementation work. |

### How @ references are used

Only **two** `@` references are used in SIOPV CLAUDE.md (vs. four in the meta-project):
- `@.claude/workflow/briefing.md` — loaded every session (replaces multi-file session start)
- `@.claude/workflow/compaction-log.md` — loaded every session (cross-session continuity)

All other files are listed in the References table as plain paths, read on demand. This
follows R1 §6: `@`-imports inline content at session start and consume context budget;
on-demand references are fetched only when the specific topic is needed.

### Target line count

| File | Lines | Limit | Status |
|------|-------|-------|--------|
| `CLAUDE.md` | 97 | 200 | ✅ Well under |
| `CLAUDE.local.md` | 37 | N/A | ✅ Minimal |
| This truth document | ~200 | 300 | ✅ Within |

### SIOPV-specific additions vs. any generic project CLAUDE.md

1. **Phase 7 Gating Conditions** — explicitly blocks premature Phase 7 start (Stage 3.5 finding: these conditions were absent from all reference docs)
2. **Graph flow one-liner** — prevents node routing errors in Phase 7/8 implementation
3. **Checkpointer note** — Stage 3 confirmed: `interrupt()` silently fails without checkpointer at compile time; this is the #1 Phase 7 footgun
4. **Hexagonal arch rules** — rules 4 and 5 directly address Stage 2 violations #1 and #2 (CRITICAL severity: adapter imports in use cases)
5. **Coverage baseline comment** — 83% is the non-regression floor; must not drop below it
6. **CLAUDE.local.md `mode: acceptEdits` note** — surfaces the bypassPermissions error (#10 in global errors-to-rules) at the project level so it can't be forgotten

---

*End of truth-02-claude-md.md*
