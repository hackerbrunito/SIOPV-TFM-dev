# Truth-11: Compaction-Proof Session Continuity
**Generated:** 2026-03-13
**Authority:** compaction-proof-handoff-best-practices.md + round3-gap-analysis §2–§3 + meta-project hooks
**Scope:** `siopv/.claude/workflow/briefing.md` + `siopv/.claude/workflow/compaction-log.md`

---

## 1. Compaction-Proof Architecture for SIOPV

### The Chain (3 components, all required)
```
briefing.md ──(read by)──▶ session-start.sh ──(stdout)──▶ Claude context at start
     ▲                                                               │
     │         pre-compact.sh updates timestamp + log entry         │
     │         session-end.sh updates timestamp + log entry         │
     └───────────────────── compaction-log.md ◀─────────────────────┘
```

### Bug Workarounds (active March 2026)

| Bug # | Description | Workaround Applied |
|-------|-------------|-------------------|
| **#15174** / **#13650** | SessionStart `compact` matcher stdout NOT injected post-compaction | Add `## Compact Instructions` block to `CLAUDE.md` — this is the ONLY reliable mechanism |
| **#13668** | PreCompact `transcript_path` can be null/empty | Add fallback in pre-compact.sh: `ls -t ~/.claude/projects/*/*.jsonl \| head -1` |
| **#14281** | `additional_context` (underscore) causes duplicate injection | Use `additionalContext` (camelCase) if switching to JSON format |
| **double-fire** | `claude --continue` fires both `startup` AND `resume` | Use lock file guard in session-start.sh |

### What the Meta-Project Does Correctly (keep in SIOPV)
- PreCompact: timestamp update + log entry — lightweight, always exits 0 ✅
- SessionEnd: timestamp update + log entry — within 1.5s timeout ✅
- SessionStart: `cat briefing.md` plain stdout — verified working for `startup`/`resume` ✅
- briefing.md has recovery header, phase table, ordered plan, NEXT IMMEDIATE ACTION ✅

### What SIOPV Upgrades vs. Meta-Project
- SIOPV pre-compact.sh: adds `claude -p` transcript summary (medium priority fix from best-practices §6)
- SIOPV pre-compact.sh: adds `transcript_path` null guard (bug #13668)
- SIOPV session-start.sh: removes `.build/active-project` lookup (meta-only mechanism)
- SIOPV CLAUDE.md: adds Compact Instructions block (bug #15174 workaround — CRITICAL)

---

## 2. briefing.md — Complete Content

**Target file:** `/Users/bruno/siopv/.claude/workflow/briefing.md`
**Inject via:** `session-start.sh` at every startup/resume/compact SessionStart event
**Size limit:** ≤ 200 lines (always injected — consumes context budget)

```markdown
<!-- COMPACT-SAFE: SIOPV master briefing — read this file immediately after any compaction or session start -->

# SIOPV Master Briefing — Compaction-Proof Recovery Document

> **If you just compacted:** Read this file top to bottom before doing anything else.
> Last updated: 2026-03-13T00:00:00Z

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

### Metrics (as of 2026-03-05 audit)

| Metric | Value |
|--------|-------|
| Tests passing | 1,404 |
| Coverage | 83% overall |
| mypy errors | 0 |
| ruff errors | 0 |

### ⚡ NEXT IMMEDIATE ACTION

> Read all directories in `/Users/bruno/siopv/AuditPrePhase7-11mar26/` (stage1 through stage4.2) and produce the REMEDIATION-HARDENING orchestrator guidelines.

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

## 4. OPEN VIOLATIONS (Stage 2 Hexagonal Audit)

### CRITICAL
| # | File | Issue |
|---|------|-------|
| 1 | `application/use_cases/ingest_trivy.py:17` | Imports `TrivyParser` from adapters layer |
| 2 | `application/use_cases/classify_risk.py:18` | Imports `FeatureEngineer` from adapters layer |
| 3 | `interfaces/cli/main.py` | All 8 adapter ports = None; DI never wired |

### HIGH
| # | File | Issue |
|---|------|-------|
| 4 | `adapters/dlp/dual_layer_adapter.py` | No explicit `DLPPort` inheritance |
| 5 | `infrastructure/di/authorization.py` | 3 uncached `OpenFGAAdapter` instances |
| 6 | `application/orchestration/nodes/ingest_node.py` | Directly instantiates use case |
| 7 | `application/orchestration/edges.py` | Domain logic in `calculate_batch_discrepancies()` |

---

## 5. KNOWN ISSUES (Stage 1 + STAGE-3 findings)

### CRITICAL (fix before Phase 7)
| # | Issue | File |
|---|-------|------|
| 1 | CLI hollow — 3 TODO stubs, pipeline unreachable | `interfaces/cli/main.py` |
| 2 | `SanitizeVulnerabilityUseCase` orphaned — `dlp_node` is the real path | use case file |
| 3 | LLM confidence is pure math heuristic — `_estimate_llm_confidence()` not LLM | `adapters/llm/` empty |
| 4 | `run_pipeline()` drops enrichment clients | `graph.py:439-444` |

### HIGH (fix in REMEDIATION-HARDENING)
| # | Issue | File |
|---|-------|------|
| 5 | DLP DI not exported — missing `get_dlp_port`, `get_dual_layer_dlp_port` | `infrastructure/di/__init__.py` |
| 6 | Hardcoded Haiku model IDs in 4 DLP files | DLP adapter files |
| 7 | `asyncio.run()` in sync nodes — breaks inside async runners | dlp_node, enrich_node, authorization_node |
| 8 | No tests for Phase 2 adapters (NVD, EPSS, GitHub, Tavily, ChromaAdapter at 0–20%) | `adapters/` |
| 9 | `structlog` `format_exc_info` deprecation — warning every test run | `infrastructure/logging/setup.py` |

---

## 6. COMPACTION PROTOCOL

**How it works:**
- `PreCompact` (`/Users/bruno/siopv/.claude/hooks/pre-compact.sh`) — updates timestamp, writes brief
- `SessionEnd` (`/Users/bruno/siopv/.claude/hooks/session-end.sh`) — updates timestamp, logs event
- `SessionStart` (`/Users/bruno/siopv/.claude/hooks/session-start.sh`) — cats this file to stdout

**If you just resumed after compaction:**
1. This file was already injected (SessionStart hook ran)
2. Check `/Users/bruno/siopv/.claude/workflow/compaction-log.md` for last compaction timestamp
3. Orient yourself using Section 2 (Current Status) and Section 5 (NEXT IMMEDIATE ACTION)
4. Do NOT start new work until you have confirmed your position in the phase plan

Hook scripts: `/Users/bruno/siopv/.claude/hooks/`
Compaction log: `/Users/bruno/siopv/.claude/workflow/compaction-log.md`
```

---

## 3. compaction-log.md — Initial Content

**Target file:** `/Users/bruno/siopv/.claude/workflow/compaction-log.md`
**Written by:** pre-compact.sh (PreCompact events) + session-end.sh (SessionEnd events)
**Read by:** session-start.sh (injects last 5 lines at session start)

```markdown
# SIOPV Compaction Log

Entries added automatically by pre-compact.sh and session-end.sh.
Format: `- {ISO_TIMESTAMP} — {event_type}`

---

- 2026-03-13T00:00:00Z — Log initialized (Stage 4.2 setup)
```

---

## 4. Hook Adaptations for SIOPV

Cross-reference: truth-01 specifies hook registration in settings.json; this section specifies content.

### session-start.sh (ADAPT from meta-project)

**Changes from meta-project:**
- Replace `/Users/bruno/sec-llm-workbench/.claude/workflow/briefing.md` → `/Users/bruno/siopv/.claude/workflow/briefing.md`
- Replace `/Users/bruno/sec-llm-workbench/.claude/workflow/compaction-log.md` → `/Users/bruno/siopv/.claude/workflow/compaction-log.md`
- Remove `.build/active-project` lookup (meta-only, single-project SIOPV has no use for it)
- Add idempotency lock guard (bug workaround for `claude --continue` double-firing)

```bash
#!/usr/bin/env bash
# session-start.sh — Inject SIOPV briefing at every session start/resume/compact
trap 'exit 0' ERR

BRIEFING="/Users/bruno/siopv/.claude/workflow/briefing.md"
COMPACT_LOG="/Users/bruno/siopv/.claude/workflow/compaction-log.md"

# Idempotency guard: --continue fires both startup AND resume (bug workaround)
SESSION_ID="${CLAUDE_SESSION_ID:-default}"
LOCK="/tmp/siopv-session-start-${SESSION_ID}.lock"
if [[ -f "$LOCK" ]]; then exit 0; fi
touch "$LOCK"

if [[ -f "$BRIEFING" ]]; then
  echo "========================================================"
  echo "  SIOPV SESSION START — Loading master briefing"
  echo "========================================================"
  cat "$BRIEFING"
  echo ""
fi

if [[ -f "$COMPACT_LOG" ]]; then
  echo "========================================================"
  echo "  COMPACTION LOG — Last 5 entries"
  echo "========================================================"
  tail -n 5 "$COMPACT_LOG"
  echo ""
fi

exit 0
```

### session-end.sh (ADAPT from meta-project)

**Changes:** Replace all meta-project paths with SIOPV paths. Logic identical.

```bash
#!/usr/bin/env bash
# session-end.sh — Timestamp update + log entry on session exit
# Hard limit: 1.5 second timeout — keep this minimal
trap 'exit 0' ERR

BRIEFING="/Users/bruno/siopv/.claude/workflow/briefing.md"
COMPACT_LOG="/Users/bruno/siopv/.claude/workflow/compaction-log.md"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ -f "$BRIEFING" ]] && grep -q "^> Last updated:" "$BRIEFING"; then
  perl -i -pe "s|^> Last updated:.*|> Last updated: ${TIMESTAMP}|" "$BRIEFING"
fi

[[ ! -f "$COMPACT_LOG" ]] && echo "# SIOPV Compaction Log" > "$COMPACT_LOG"
echo "- ${TIMESTAMP} — SessionEnd fired (normal exit)" >> "$COMPACT_LOG"
exit 0
```

### pre-compact.sh (ADAPT from meta-project — upgraded)

**Changes from meta-project:**
- Replace all meta-project paths with SIOPV paths
- Add `transcript_path` null guard (bug #13668 workaround)
- Add `claude -p` transcript summary generation (medium-priority upgrade)

```bash
#!/usr/bin/env bash
# pre-compact.sh — Fires before compaction; updates timestamp, generates brief
trap 'exit 0' ERR

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty')
BRIEFING="/Users/bruno/siopv/.claude/workflow/briefing.md"
COMPACT_LOG="/Users/bruno/siopv/.claude/workflow/compaction-log.md"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Bug #13668: transcript_path can be null/empty — fallback to most recent JSONL
if [[ -z "$TRANSCRIPT" || "$TRANSCRIPT" == "null" ]]; then
  TRANSCRIPT=$(ls -t ~/.claude/projects/*/*.jsonl 2>/dev/null | head -1)
fi

# Generate recovery brief from transcript tail (async: true in settings.json)
if [[ -f "$TRANSCRIPT" ]]; then
  BRIEF_PATH="/Users/bruno/siopv/.claude/workflow/pre-compact-brief-${TIMESTAMP}.md"
  tail -100 "$TRANSCRIPT" | claude -p \
    "Generate compact SIOPV recovery brief: current task, key decisions, next action, files modified. Max 30 lines." \
    --print > "$BRIEF_PATH" 2>/dev/null &
fi

# Update timestamp in briefing.md
if [[ -f "$BRIEFING" ]] && grep -q "^> Last updated:" "$BRIEFING"; then
  perl -i -pe "s|^> Last updated:.*|> Last updated: ${TIMESTAMP}|" "$BRIEFING"
fi

# Append to compaction log
[[ ! -f "$COMPACT_LOG" ]] && echo "# SIOPV Compaction Log" > "$COMPACT_LOG"
echo "- ${TIMESTAMP} — PreCompact fired" >> "$COMPACT_LOG"

echo "PreCompact: timestamp updated, brief spawned" >&2
exit 0
```

**settings.json registration for pre-compact.sh:**
```json
"PreCompact": [
  { "hooks": [{ "type": "command", "command": "/Users/bruno/siopv/.claude/hooks/pre-compact.sh", "async": true }] }
]
```
Note: `async: true` — does not block compaction.

---

## 5. CLAUDE.md Compact Instructions Block

**Target section to add to `siopv/.claude/CLAUDE.md` (cross-reference truth-02):**

This block is the ONLY reliable workaround for bug #15174 (SessionStart `compact` matcher stdout not injected).

```markdown
## Compact Instructions

When compacting, always preserve:
- Current SIOPV phase and status (e.g., "Phase 7 — Human-in-the-Loop: IN PROGRESS")
- The NEXT IMMEDIATE ACTION sentence verbatim
- All absolute file paths from briefing.md Section 3 (Key File Paths)
- Phase completion table with ✅/⏳/❌ markers
- Last known metrics: tests passing, coverage %, mypy/ruff error counts
- Open violations from Stage 2 hexagonal audit (CRITICAL #1–#3, HIGH #4–#7)
- SIOPV project path: /Users/bruno/siopv/

When a phase, stage, or major task completes, immediately update briefing.md:
- Change status from ⏳ PENDING to ✅ COMPLETE
- Update "NEXT IMMEDIATE ACTION" to the next concrete step
- Add the absolute path to the final report in Section 6 (Reference Files)
```

---

## 6. Triple Storage Verification

Per best-practices §3 — critical context must exist in all 3 locations simultaneously.

| Location | File | What It Carries | Reliability |
|----------|------|-----------------|-------------|
| **System prompt** | `siopv/.claude/CLAUDE.md` | Compact Instructions block — survives compaction guaranteed | ✅ Most reliable |
| **External file** | `siopv/.claude/workflow/briefing.md` | Full project state, phases, paths, violations, next action | ✅ Reliable (injected by hook at startup/resume) |
| **Periodic re-injection** | `session-start.sh` → briefing.md stdout | Every session start injects full briefing + last 5 log lines | ⚠️ Reliable for `startup`/`resume`; use CLAUDE.md for `compact` |

**Verification checklist (run at Stage 4.2 completion):**
- [ ] briefing.md exists at `/Users/bruno/siopv/.claude/workflow/briefing.md`
- [ ] compaction-log.md exists at `/Users/bruno/siopv/.claude/workflow/compaction-log.md`
- [ ] session-start.sh registered in settings.json for `startup`, `resume`, and `compact` matchers
- [ ] pre-compact.sh registered with `async: true` in settings.json
- [ ] session-end.sh registered in settings.json
- [ ] `## Compact Instructions` block present in `siopv/.claude/CLAUDE.md`
- [ ] All paths in hooks reference `/Users/bruno/siopv/` (not `/Users/bruno/sec-llm-workbench/`)
- [ ] `transcript_path` null guard present in pre-compact.sh
- [ ] Idempotency lock guard present in session-start.sh
