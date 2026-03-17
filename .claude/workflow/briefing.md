<!-- COMPACT-SAFE: SIOPV master briefing — read this file immediately after any compaction or session start -->

# SIOPV Master Briefing — Compaction-Proof Recovery Document

> **If you just compacted:** Read this file top to bottom before doing anything else.
> Last updated: 2026-03-17T09:08:37Z

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
| 8 | Output (Jira + PDF) | ⏳ NEXT |

### Metrics (as of Phase 7 /verify complete)

| Metric | Value |
|--------|-------|
| Tests passing | 1,558 |
| Coverage | 92% |
| mypy errors | 0 |
| ruff errors | 0 |

### ⚡ NEXT IMMEDIATE ACTION

> /verify pipeline COMPLETE — ALL 9 WAVES PASSED. Human approved commit. Ready to execute.
>
> COMPLETED VERIFY RUN:
> - Team: siopv-verify-20260317-095148 (ALL agents shut down including orchestrator)
> - Verify dir: /Users/bruno/siopv/.verify-17-03-2026
>
> PIPELINE STATUS (2026-03-17T04:40Z) — ALL DONE:
> | Wave | Status |
> |------|--------|
> | Pre-wave | ✅ PASS |
> | Wave 1 (5 scanners) | ✅ PASS — 0 findings |
> | Wave 1B (judge) | ✅ PASS — 1 LOW non-blocking |
> | Wave 2 (reviewer+testgen) | ✅ PASS — 9/10, 92% cov, 1558 tests |
> | Wave 3 (fixers) | ⏭ SKIPPED |
> | Wave 4 (integration+async) | ✅ PASS — 6 MEDIUM non-blocking |
> | Wave 5 (semantic+circular) | ✅ PASS — 2 MEDIUM non-blocking, 0 cycles |
> | Wave 6 (imports+deps) | ✅ PASS — 3 HIGH CVEs fixed (pyjwt→2.12.1, pillow→12.1.1, langgraph→1.0.10) |
> | Wave 7 (config-validator) | ✅ PASS — 0 docker mismatches |
> | Wave 8 (hex-arch) | ✅ PASS — findings 1+3 fixed; finding 2 → TODO(phase-8) |
> | Wave 9 (smoke-test) | ✅ PASS — import OK, pipeline OK (8 CVEs), Streamlit OK |
>
> ⚡ NEXT IMMEDIATE ACTION: Spawn Phase 8 build team — briefing is WRITTEN and APPROVED
>
> Phase 7 is DONE. Commit: 36db797
> Phase 8 orchestrator briefing: `/Users/bruno/siopv/.ignorar/research-phase8/orchestrator-phase8-build.md`
> Metrics baseline: 1,558 tests · 92% coverage · 0 mypy · 0 ruff
>
> SPAWN INSTRUCTIONS:
> 1. TeamCreate(team_name="siopv-phase8-{timestamp}", description="Phase 8 Output Layer build")
> 2. Spawn orchestrator: Agent(prompt="Read and follow briefing at: /Users/bruno/siopv/.ignorar/research-phase8/orchestrator-phase8-build.md", name="orchestrator", run_in_background=True)
> 3. Name yourself "team-lead" — orchestrator will SendMessage(to="team-lead") for SPAWN REQUESTs
> 4. DO NOT re-plan — briefing is fully approved, execute immediately

---

## 3. ARCHITECTURE

### Graph Flow
```
START → authorize → ingest → dlp → enrich → classify → [escalate] → END
```
Phase 8 adds: `→ output → END`

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
