<!-- COMPACT-SAFE: SIOPV master briefing — read this file immediately after any compaction or session start -->

# SIOPV Master Briefing — Compaction-Proof Recovery Document

> **If you just compacted:** Read this file top to bottom before doing anything else.
> Last updated: 2026-03-19T09:41:02Z

---

## 1. PROJECT IDENTITY

**SIOPV** (Sistema Inteligente de Observabilidad de Privacidad de Vulnerabilidades) is a master's
thesis Python application: LangGraph pipeline + hexagonal architecture for intelligent vulnerability
analysis with privacy, authorization, and human-in-the-loop controls.

- **Quality standard:** Precision over speed — target 9.5/10 across all dimensions
- **Project root:** `/Users/bruno/siopv/`
- **Spec:** `/Users/bruno/siopv/docs/SIOPV_Propuesta_Tecnica_v2.txt`
- **State file:** `/Users/bruno/siopv/projects/siopv.json`
- **Backup:** `/Users/bruno/siopv/.ignorar/siopv-backup-phase6-complete-2026-03-07.tar.gz`
- **Thesis context:** Final deliverable must be production-quality; no shortcuts, no TODOs, no stubs

---

## 2. CURRENT STATUS

### Phase Completion

| Phase | Name | Status |
|-------|------|--------|
| 0 | Setup | ✅ Complete |
| 1 | Ingesta y Preprocesamiento | ✅ Complete |
| 2 | Enriquecimiento (CRAG / RAG) | ✅ Complete |
| 3 | Clasificación ML (XGBoost) | ✅ Complete |
| 4 | Orquestación (LangGraph) | ✅ Complete |
| 5 | Autorización (OpenFGA) | ✅ Complete |
| 6 | Privacidad (DLP / Presidio) | ✅ Complete |
| 7 | Human-in-the-Loop (Streamlit) | ✅ Complete — commit 36db797 |
| 8 | Output (Jira + PDF) | ✅ Complete — commit 83d9b3d |

### Post-Phase 8 Work (2026-03-17 session)

| Commit | What | Status |
|--------|------|--------|
| `83d9b3d` | Phase 8 build (Jira, PDF, CSV/JSON, output node) | ✅ Solid |
| `911a685` | LLM remediation (CRAG LLM, classify confidence, DI enrichment/ML wiring) | ✅ Solid |
| `reverted 46f8eee` | Had hex-arch fixes BUT wrongly deleted 8 settings — REVERTED | ⚠️ Reverted |
| `latest` | Revert of 46f8eee + some low-severity fixes from subagent | ⚠️ Needs /verify |

### ⚠️ KNOWN ISSUES — Verified 2026-03-18T09:40+08:00

#### Issue 1: Hardcoded values not wired to settings (HIGH)

**ThresholdConfig** (`state.py:137-140`) — hardcoded defaults, NO settings fields exist:
- `base_threshold=0.3`, `confidence_floor=0.7`, `percentile=90`, `history_size=500`
- Fallback `0.3` also hardcoded in `state.py:174`

**Escalation timeouts** (`escalate_node.py:22-27`) — hardcoded `(24,3), (8,2), (4,1)`:
- Settings fields were DELETED in revert commit `94c442b` — must re-add + wire
- Also hardcodes 24h review deadline at line 119

**Rate limits** (`rate_limiter.py`) — settings field exists for NVD but is IGNORED:
- NVD: hardcodes `50/5` at line 263 (settings has `nvd_rate_limit=5` unused)
- GitHub: hardcodes `5000/60` at line 281 (no setting exists)
- EPSS: hardcodes `10.0 req/s, burst 20` at line 298 (no setting exists)
- `max_queue_size=100` at line 117 (no setting exists)

**Deleted settings** (commit `94c442b` removed these — must re-add + wire):
- `model_base_path`, `model_max_size_bytes`, `model_signing_key` — were never wired, need implementation
- `database_url` — was never wired, checkpointer uses SQLite path directly

#### Issue 2: Cross-adapter hex-arch violation (HIGH) — CONFIRMED
- `adapters/llm/anthropic_adapter.py:17` imports `create_haiku_client`, `extract_text_from_response` from `adapters/dlp/_haiku_utils`
- Fix: move `_haiku_utils` to `infrastructure/clients/haiku_client.py`

#### Issue 3: Domain→Application import (MEDIUM) — mitigated but present
- `domain/services/discrepancy.py` uses deferred imports + TYPE_CHECKING to break circular dep
- Not a hard runtime violation, but types should live in domain layer
- Lower priority — functional workaround in place

#### Issue 4: No XGBoost trained model (LOW) — project constraint
- `models/` dir empty, ML uses fallback. Not a code bug.

#### ~~Issue 5: No `.env.example`~~ — FALSE
- File exists since 2026-02-14 (3046 bytes, 101 lines)
- Already documents: UNCERTAINTY_THRESHOLD, HITL_TIMEOUT_LEVEL1/2/3, MODEL_PATH, DATABASE_URL
- May need updating if new settings are added in Step 2

### Metrics (verified 2026-03-19 after Wave 9-fix)

| Metric | Value |
|--------|-------|
| Tests passing | 1,814 |
| Coverage | 92.68% |
| mypy errors | 0 |
| ruff errors | 0 |

### ⚡ CURRENT PLAN — Post-Phase 8 Hardening (2026-03-18)

**Goal:** Fix all known issues, improve `/verify` to catch functional completeness gaps, run single improved verification pass.

**Why this order:** Running `/verify` twice (before and after improvements) wastes 6+ hours. Improve first, run once.

**CRITICAL RULE:** Never delete settings or code that appears "unused" — wire the code to use it instead.

#### Step 1: Targeted File Check (~10 min)
> Read the ~5 files referenced in known issues. Confirm which are real, which aren't. No agents needed.

- [x] Read `edges.py` — delegates to ThresholdConfig in state.py, hardcoded defaults
- [x] Read `escalate_node.py` — HITL timeouts hardcoded, settings fields DELETED in revert
- [x] Read `rate_limiter.py` — NVD/GitHub/EPSS all hardcoded, nvd setting exists but ignored
- [x] Read `anthropic_adapter.py` — cross-adapter import CONFIRMED at line 17
- [x] Read `discrepancy.py` — deferred import workaround, not hard violation
- [x] Check `model_base_path`, `model_max_size_bytes`, `model_signing_key` — DELETED in revert, never wired
- [x] Check `database_url` — DELETED in revert, never wired
- [x] Confirm/update known issues list — updated with corrected details + new findings
- [x] **CHECKPOINT: Findings presented and approved. Permission rules fixed (12 deny rules removed).**

#### Step 1.5: Add no-hardcoding rule to CLAUDE.md (~2 min)
> Details: `.claude/workflow/steps/step-1.5-no-hardcoding-rule.md`

- [x] Add Critical Rule #11 to CLAUDE.md
- [x] Verify text matches step file specification

#### Step 2: Fix Confirmed Issues (~30-60 min)
> Details: `.claude/workflow/steps/step-2-fix-confirmed-issues.md`

- [x] 2a: Read DI container + utils files — pattern: factory functions receive `settings: Settings`, extract values, pass to constructors
- [x] 2b: Wire ThresholdConfig to settings.py
- [x] 2c: Wire HITL timeouts to settings.py
- [x] 2d: Wire rate limits to settings.py
- [x] 2e: Re-add deleted settings (model_base_path, model_max_size_bytes, model_signing_key, database_url)
- [x] 2f: Move `_haiku_utils` to infrastructure/clients/
- [x] 2g: Moved types to domain layer (Option A — circular dep eliminated)
- [x] 2h: Update `.env.example` — 61/61 fields in sync with settings.py
- [x] 2i: Update `.env` file — all new vars added, 6 existing credentials verified intact
- [x] 2j: 1782 passed, 0 failed, 92% coverage. ruff clean. mypy 3 pre-existing fpdf2 errors only.
- [x] **CHECKPOINT: Fixes presented and approved.**

#### Step 2.5: Verify Agent and Skill Files Are Current (~20-30 min)
> Details: `.claude/workflow/steps/step-2.5-verify-agent-files.md`

- [x] Audited all 14 agent files, 5 skill files, 7 hook scripts
- [x] SUPERSEDED — `.claude/` excluded from git. Hardcoded paths are local-only, won't reach repo.
- [x] **CHECKPOINT: Superseded — no fixes needed for repo deliverable.**

#### Step 3: Improve `/verify` (~1-2 hours)
> Details: `.claude/workflow/steps/step-3-improve-verify.md`

- [x] 3a: Design doc saved to `.ignorar/verify-improvements-design.md`
- [x] 3b: Created `wiring-auditor.md` agent
- [x] 3c: Created `stub-detector.md` agent
- [x] 3d: Created `config-cross-checker.md` agent
- [x] 3e: Added Hardcoding Check section to all 14 agent files (verified 14/14)
- [x] 3f: Added Pre-Write Hardcoding Prevention to code-implementer, hex-arch-remediator, test-generator
- [x] 3g: Added Wave 10 to wave-prompts.md, orchestrator-protocol.md, thresholds.md
- [x] **CHECKPOINT: Improvements presented and approved.**

#### Step 4: Run Improved `/verify` and validate (few hours)
> Details: `.claude/workflow/steps/step-4-run-verify-and-validate.md`

- [x] 4a: Run improved `/verify` — Waves PRE through 3 complete (41/41 findings fixed)
- [x] 4b: Fix any CRITICAL/HIGH issues flagged — Wave 3 fixers fixed all 41 findings (2 HIGH, 20 MED, 11 LOW + 8 code-review)
- [ ] 4c: Re-run `/verify` if fixes applied (max 2 iterations)
- [ ] **CHECKPOINT: Present `/verify` results to human**
- [ ] 4d: Commit all changes
- [ ] 4e: Real pipeline run with Trivy data
- [ ] **CHECKPOINT: Present pipeline results to human**

#### Step 5: Final Repo Cleanup (after project is fully finished)
> Do this LAST — when all development, testing, and verification is complete.

- [ ] Rename current GitHub repo `SIOPV-TFM` → `SIOPV-TFM-dev`
- [ ] Create new repo `SIOPV-TFM`
- [ ] `git init` fresh, `git add .` (`.gitignore` excludes `.claude/`, `CLAUDE.md`, `.env`, etc.)
- [ ] Single commit, push — zero history, zero Claude traces
- [ ] Verify: no `.claude/`, no `CLAUDE.md`, no `testing-kit/claude/`, no `.env` visible on GitHub

#### Checkpoint Discipline (MANDATORY)

> **After completing each sub-task** (e.g., 2a, 2b, 3a):
> 1. Mark the checkbox `- [x]` in THIS briefing file immediately
> 2. Update "Current Position" below with the next sub-task
>
> **After completing each CHECKPOINT** (human approval points):
> 1. Mark the CHECKPOINT checkbox `- [x]` in this file
> 2. Update "Active step" to the next step
> 3. Update the step detail file's "Done criteria" checkboxes
>
> **NEVER start a new sub-task without first marking the previous one as done in this file.**
> This ensures any compaction or session restart recovers to the exact correct position.

#### Current Position
> **Active step:** Step 4 — `/verify` in progress, Wave 10 next (2026-03-19)
> **Completed waves:** PRE-WAVE, 1a, 1b, 1c, 1B, 2, 3 (41/41 fixed), 3B (validator PASS), 4 (PASS), 4-fix (7/7 MEDIUM fixed), 5 (PASS, 1 MEDIUM), 5-fix (1/1 fixed), 5 re-run (PASS, 0 findings), 6 (PASS imports, 6 CVEs), 6-fix (5 deps upgraded, 0 CVEs), 6-mypy (18/18 fixed, 0 mypy errors), 7 (FAIL, 5 MED + 2 LOW), 7-fix (7/7 fixed), 8 (PASS, 0 violations + 2 INFO), 8-fix (2/2 INFO fixed, 100% hex-arch), 9 (PASS, 1 MED + 2 INFO), 9-fix (3/3 fixed)
> **Next:** Wave 10 (Wiring Auditor + Stub Detector + Config Cross-Checker) → Post-wave → Pre-production tests
> **Team:** siopv-verify-20260318-163627, orchestrator-2 (1M context)
> **Verify dir:** /Users/bruno/siopv/.verify-18-03-2026/
> **Metrics post-Wave 9:** 1,814 tests, 92.68% coverage, ruff clean, mypy 0 errors
> **Max parallel agents:** 5-6 (Anthropic best practice)
> **Rule:** Shut down agents from each wave before spawning next
> **Rule:** Fix ALL findings including MEDIUM, LOW, and INFO — professional execution
> **Rule:** After any wave with findings, orchestrator includes fix sub-wave SPAWN REQUEST automatically
> **Rule:** Re-run validation wave after fixes to confirm clean (as done with Wave 5)
> **Rule:** Never delete, always rewire — use 4-step decision framework (Understand → Diagnose → Decide → Justify)
> **Rule:** All fixer prompts must include mypy in per-file validation
> **Planned:** After Wave 10, run 5 pre-production smoke tests (data-flow, error-path, config, isolation, idempotency)

---

## 3. ARCHITECTURE

### Graph Flow
```
START → authorize → ingest → dlp → enrich → classify → [escalate] → output → END
```

### Hexagonal Layers
```
domain/          — entities, ports (interfaces), constants
application/     — use cases, orchestration (LangGraph graph + nodes + state)
adapters/        — inbound (CLI, Streamlit) + outbound (NVD, EPSS, ChromaDB, etc.)
infrastructure/  — DI container, config/settings, logging, persistence
interfaces/      — CLI entry point, future HTTP interface
```

### Key File Paths

| Component | Path |
|-----------|------|
| Graph | `src/siopv/application/orchestration/graph.py` |
| State | `src/siopv/application/orchestration/state.py` |
| CLI | `src/siopv/interfaces/cli/main.py` |
| Settings | `src/siopv/infrastructure/config/settings.py` |
| DI container | `src/siopv/infrastructure/di/__init__.py` |
| DLP DI | `src/siopv/infrastructure/di/dlp.py` |
| Constants | `src/siopv/domain/constants.py` |
| Logging | `src/siopv/infrastructure/logging/setup.py` |

---

## 4. COMPACTION PROTOCOL

**How it works:**
- `PreCompact` (`/Users/bruno/siopv/.claude/hooks/pre-compact.sh`) — updates timestamp, writes brief
- `SessionEnd` (`/Users/bruno/siopv/.claude/hooks/session-end.sh`) — updates timestamp, logs event
- `SessionStart` (`/Users/bruno/siopv/.claude/hooks/session-start.sh`) — cats this file to stdout

**If you just resumed after compaction:**
1. This file was already injected (SessionStart hook ran)
2. Check `/Users/bruno/siopv/.claude/workflow/compaction-log.md` for last compaction timestamp
3. Orient yourself using Section 2 (Current Status) and the NEXT IMMEDIATE ACTION block
4. Do NOT start new work until you have confirmed your position in the phase plan

Hook scripts: `/Users/bruno/siopv/.claude/hooks/`
Compaction log: `/Users/bruno/siopv/.claude/workflow/compaction-log.md`
