# SIOPV — Guía de Implementación

## CRITICAL RULES

**YOU MUST** at session start:
1. Read @.claude/workflow/briefing.md — current phase, open violations, gating conditions
2. Check `.claude/workflow/compaction-log.md` (last 5 lines) if resuming after compaction

**YOU MUST** when writing code:
3. Query Context7 MCP BEFORE using any external library — NEVER rely on training data
4. Enforce hexagonal architecture: domain → ports → adapters; NO cross-layer imports
5. NEVER import adapter classes directly in use cases (Stage 2 violations #1 and #2)
6. Follow `.claude/docs/python-standards.md` (read on demand)

**YOU MUST** before commit:
7. Execute `/verify` — runs 14 verification agents; coverage floor ≥ 92%
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
**Metrics baseline:** 1,476 tests passing · 92.02% coverage · 0 mypy · 0 ruff errors

---

## Phase 7 Gating Conditions

✅ All gating conditions resolved (2026-03-15 remediation-hardening). Phase 7 ready to start.
See briefing.md for key file paths and full phase status.

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
| `/verify` | Before every commit — runs 14 agents |
| `/siopv-remediate` | Fix Stage 2 hex-arch violations #1–#7 |
| `/coding-standards-2026` | Python standards quick reference |
| `/langraph-patterns` | LangGraph interrupt/checkpoint patterns |
| `/openfga-patterns` | OpenFGA auth gate patterns |
| `/presidio-dlp` | Presidio PII/DLP patterns |

---

## Compact Instructions

When compacting, always preserve:
- Current SIOPV phase and status (e.g., "Phase 7 — Human-in-the-Loop: IN PROGRESS")
- The NEXT IMMEDIATE ACTION sentence verbatim
- All absolute file paths from briefing.md Section 3 (Key File Paths)
- Phase completion table with ✅/⏳/❌ markers
- Last known metrics: tests passing, coverage %, mypy/ruff error counts
