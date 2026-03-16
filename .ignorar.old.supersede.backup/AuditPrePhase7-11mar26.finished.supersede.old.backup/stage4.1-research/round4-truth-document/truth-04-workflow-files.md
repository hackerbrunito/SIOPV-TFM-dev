# Truth-04: SIOPV Workflow Files
**Generated:** 2026-03-13
**Authority:** truth-00 directory structure + Round 3 gap analysis
**Scope:** `siopv/.claude/workflow/` — what goes there and why

---

## 1. Workflow Files Assigned to truth-04

**truth-04 has ZERO files assigned.**

From truth-00 §3 (Truth File Responsibility Matrix):
> truth-04 — *(reserved — no workflow/*.md beyond briefing/compaction-log)*

The `siopv/.claude/workflow/` directory contains exactly two files, both assigned to **truth-11**:

| File | Action | Truth File |
|------|--------|------------|
| `workflow/briefing.md` | NEW | **truth-11** |
| `workflow/compaction-log.md` | NEW | **truth-11** |

**Why truth-11 and not truth-04?**
These files are tightly coupled to `hooks/session-start.sh` (which injects briefing.md at session start) and `hooks/pre-compact.sh` / `hooks/session-end.sh` (which maintain compaction-log.md). truth-11 co-locates the workflow state files with the hook wiring that drives them, providing a single place to specify the complete injection lifecycle. truth-04 was pre-allocated but no files remained after that assignment.

---

## 2. Meta-Project Workflow Files: Complete Inventory and Disposition

The meta-project (`sec-llm-workbench/.claude/workflow/`) has 12 files. None go to SIOPV as-is. Their disposition:

### 2a. NOT INCLUDED — Meta-Only State Files (4 files)

These are meta-project audit/orchestration state files. They must NOT be copied to SIOPV.

| File | Why Excluded |
|------|--------------|
| `workflow/briefing.md` | Contains meta-project audit stage state (Stages 1–4); SIOPV gets its own `briefing.md` via truth-11 |
| `workflow/orchestrator-briefing.md` | Meta-project audit orchestration briefing for Stages 1–4; irrelevant to SIOPV implementation |
| `workflow/setup-checklist.md` | Meta-project project setup checklist; wrong context for SIOPV development |
| `workflow/spec-findings.md` | Meta-project specification tracker; SIOPV findings live in Stage 1–3 reports |

These are listed in truth-00 §4 (Excluded Items) under the META-ONLY category.

### 2b. NOT INCLUDED — Numbered Workflow Guides (7 files)

The meta-project's `01-07` numbered workflow guides are **reference-only session guides** for the meta-project. SIOPV's equivalent guidance is embedded in:
- `CLAUDE.md` (truth-02) — which @-imports the guides Claude Code needs per session
- `docs/siopv-phase7-8-context.md` (truth-05) — which carries the Phase 7/8-specific guidance
- Agent definition files (truth-03) — which embed relevant workflow steps directly

| Meta File | Content | SIOPV Equivalent |
|-----------|---------|------------------|
| `01-session-start.md` | Session triggers, state detection | Embedded in `CLAUDE.md` @-imports + `briefing.md` (truth-11) |
| `02-reflexion-loop.md` | PRA pattern, agent wave timing | Referenced from `CLAUDE.md`; wave timing in `agents/*.md` (truth-03) |
| `03-human-checkpoints.md` | When to pause vs. auto-continue | Embedded in `CLAUDE.md` @-import block |
| `04-agents.md` | Agent invocation patterns, hexagonal layer order | Embedded in `code-implementer.md` agent (truth-03) |
| `05-before-commit.md` | /verify checklist, hook interaction | Referenced from `CLAUDE.md`; hook logic in truth-01 |
| `06-decisions.md` | Automatic code quality fixes, model routing | Embedded in `code-implementer.md` + `docs/model-selection-strategy.md` (truth-05) |
| `07-orchestrator-invocation.md` | One-task-per-layer, invocation structure, MCP fallback | Embedded in `code-implementer.md` agent prompt template |

**Key distinction:** Meta-project workflow guides are loaded on-demand via @-imports in CLAUDE.md. SIOPV's CLAUDE.md (truth-02) will @-import only the guides relevant to SIOPV phases. The numbered files themselves are NOT copied — they live in `sec-llm-workbench/.claude/workflow/` and are referenced by the user-level ~/.claude/CLAUDE.md (truth-08) when working on the meta-project.

### 2c. Compaction-Log and Briefing (2 files) → truth-11

| File | Action | Target in SIOPV | Truth File |
|------|--------|-----------------|------------|
| `workflow/compaction-log.md` (meta version) | NOT COPIED — NEW content created | `siopv/.claude/workflow/compaction-log.md` | truth-11 |
| `workflow/briefing.md` (meta version) | NOT COPIED — NEW content created | `siopv/.claude/workflow/briefing.md` | truth-11 |

These are structurally equivalent but contain different content. The meta versions reference audit stages; the SIOPV versions reference Phase 7/8 state, open violations, and gating conditions.

---

## 3. Summary: Where Workflow-Adjacent Content Lives in SIOPV

| Workflow Concern | SIOPV Location | Truth File |
|------------------|----------------|------------|
| Session state injection | `workflow/briefing.md` | truth-11 |
| Cross-session continuity log | `workflow/compaction-log.md` | truth-11 |
| Session start triggers | `hooks/session-start.sh` + `CLAUDE.md` | truth-01, truth-02 |
| Compaction preservation | `hooks/pre-compact.sh` | truth-01 |
| Phase 7/8 library patterns | `docs/siopv-phase7-8-context.md` | truth-05 |
| Agent invocation patterns | `agents/code-implementer.md` | truth-03 |
| Before-commit checklist | `CLAUDE.md` @-import | truth-02 |
| Human checkpoint rules | `CLAUDE.md` @-import | truth-02 |

---

## 4. Conclusion

truth-04 is intentionally empty. The `workflow/` directory in SIOPV contains only two files (`briefing.md` and `compaction-log.md`), both fully specified in truth-11. No meta-project numbered workflow guides (01–07) are copied to SIOPV — their content is distributed across CLAUDE.md, agent definitions, docs, and hooks per the SIOPV architecture.
