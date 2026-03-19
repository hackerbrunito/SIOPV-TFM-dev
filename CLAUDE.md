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

**YOU MUST** when writing or reviewing code:
11. NEVER hardcode configurable values in code. This includes: numeric literals (thresholds, timeouts, rate limits, sizes, delays, ports), paths, URLs, credentials, and API model identifiers. ALL such values must be defined as fields in `settings.py` (read from env vars via `.env`). Dataclass defaults, module-level constants, and constructor parameter defaults are NOT exceptions — if the value could differ between environments or deployments, it belongs in `settings.py`. Violations: `base_threshold=0.3` in a dataclass, `requests=50` in a factory function, `timedelta(hours=24)` in a node. Correct: `settings.uncertainty_threshold` read via DI or `get_settings()`.

---

## SIOPV Project State

| Phase | Name | Status |
|-------|------|--------|
| 0 | Setup | ✅ Complete |
| 1 | Ingesta y Preprocesamiento | ✅ Complete |
| 2 | Enriquecimiento (CRAG/RAG) | ✅ Complete |
| 3 | Clasificación ML (XGBoost) | ✅ Complete |
| 4 | Orquestación (LangGraph) | ✅ Complete |
| 5 | Autorización (OpenFGA) | ✅ Complete |
| 6 | Privacidad (DLP/Presidio) | ✅ Complete |
| 7 | Human-in-the-Loop (Streamlit) | ✅ Complete |
| 8 | Output (Jira + PDF) | ✅ Complete |

**Graph flow:** START → authorize → ingest → dlp → enrich → classify → [escalate] → output → END
**Checkpointer:** SQLite (`siopv_checkpoints.db`) — required for `interrupt()` to work
**Metrics (verified 2026-03-18):** 1,782 tests passing · 92% coverage · 3 mypy (pre-existing fpdf2) · 0 ruff errors
**Current work:** Post-Phase 8 hardening — see briefing.md for active plan and checklist.

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
