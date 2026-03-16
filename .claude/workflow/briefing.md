<!-- COMPACT-SAFE: SIOPV master briefing — read this file immediately after any compaction or session start -->

# SIOPV Master Briefing — Compaction-Proof Recovery Document

> **If you just compacted:** Read this file top to bottom before doing anything else.
> Last updated: 2026-03-16T09:57:54Z

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
| 7 | Human-in-the-Loop (Streamlit) | ⏳ PENDING |
| 8 | Output (Jira + PDF) | ⏳ PENDING |

### Metrics (as of 2026-03-15 remediation-hardening)

| Metric | Value |
|--------|-------|
| Tests passing | 1,476 |
| Coverage | 92.02% |
| mypy errors | 0 |
| ruff errors | 0 |

### ⚡ NEXT IMMEDIATE ACTION

> Remediation-hardening complete. Review Phase 7 gating conditions before starting Phase 7.

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
