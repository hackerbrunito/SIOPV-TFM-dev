# Stage 4.2 — Batch 6 Agents Group A

**Agent:** batch6-agents-group-a
**Date:** 2026-03-13
**Worker:** claude-sonnet-4-6

---

## Files Created

| File | Lines | Action |
|------|-------|--------|
| `siopv/.claude/agents/best-practices-enforcer.md` | 320 | ADAPT |
| `siopv/.claude/agents/security-auditor.md` | 352 | ADAPT |
| `siopv/.claude/agents/hallucination-detector.md` | 295 | ADAPT |
| `siopv/.claude/agents/code-reviewer.md` | 370 | ADAPT |
| `siopv/.claude/agents/test-generator.md` | 362 | ADAPT |
| `siopv/.claude/agents/code-implementer.md` | 436 | ADAPT |
| `siopv/.claude/agents/async-safety-auditor.md` | 239 | ADAPT |
| `siopv/.claude/agents/semantic-correctness-auditor.md` | 238 | ADAPT |
| `siopv/.claude/agents/hex-arch-remediator.md` | 66 | NEW |

**Total lines:** 2,678

---

## Corrections Applied

### C2 — permissionMode (camelCase)
Applied to ALL 9 agents. Used `permissionMode` throughout — NOT `permission_mode`. No snake_case variant appears in any frontmatter.

### C3 — permissionMode values
Applied the complete override list from Section 5:

| Agent | Source permissionMode | Applied permissionMode | Changed? |
|-------|----------------------|----------------------|---------|
| best-practices-enforcer | plan | plan | No |
| security-auditor | plan | plan | No |
| hallucination-detector | plan | plan | No |
| code-reviewer | plan | plan | No |
| test-generator | acceptEdits | **plan** | **YES** |
| code-implementer | acceptEdits | acceptEdits | No |
| async-safety-auditor | plan | **acceptEdits** | **YES** |
| semantic-correctness-auditor | plan | **acceptEdits** | **YES** |
| hex-arch-remediator | N/A (NEW) | acceptEdits | N/A |

### C10 — hex-arch-remediator placement
Created in `siopv/.claude/agents/hex-arch-remediator.md` (agents/ directory, not docs/).

---

## Universal Changes Applied (All 8 ADAPT Agents)

| Check | Status | Notes |
|-------|--------|-------|
| Project Context block replaced | ✅ ALL 8 | Replaced meta-project block with SIOPV hardcoded block |
| `memory: true` → `memory: project` | ✅ ALL 8 | Fixed in best-practices-enforcer, security-auditor, code-reviewer (had `true`); others already had `project` |
| `model: sonnet` | ✅ ALL 8 | Confirmed in all frontmatter |
| Report directory paths updated | ✅ ALL 8 | Changed from `.ignorar/` relative → `/Users/bruno/siopv/.ignorar/` absolute |
| Bash commands updated | ✅ ALL 8 | Removed `.build/active-project` lookup; hardcoded `/Users/bruno/siopv/` |
| `permissionMode` camelCase | ✅ ALL 9 | Applied everywhere |

### New Project Context Block Applied (identical for all 8 ADAPT agents):
```markdown
## Project Context (CRITICAL)

You are working directly on the **SIOPV project** (`~/siopv/`).

- **Target project path:** `~/siopv/` (absolute: `/Users/bruno/siopv/`)
- All file operations (Read, Write, Edit, Glob, Grep) target `/Users/bruno/siopv/`
- All `uv run` commands must run from the project root:
  ```bash
  cd /Users/bruno/siopv && uv run <command>
  ```
- Reports go to `/Users/bruno/siopv/.ignorar/production-reports/`
- No `.build/active-project` lookup — path is hardcoded
```

---

## Agent-Specific Changes

### best-practices-enforcer
- Universal changes only
- Fixed `memory: true` → `memory: project`

### security-auditor
- Universal changes + fixed `memory: true` → `memory: project`
- Added `## SIOPV-Specific Security Checks` section after OWASP section:
  - OpenFGA tuples hardcoding check
  - Presidio config check
  - Hardcoded model IDs check (Issue #6)
  - Streamlit input validation (Phase 7)
  - Jira credentials log exposure (Phase 8)
- Removed experimental self-consistency-voting script reference (sec-llm-workbench internal path)

### hallucination-detector
- Universal changes (memory was already `project`)
- Added `## SIOPV Phase 7/8 Critical Library Facts` table with 5 entries
- Applied C5: Fixed duplicate `fname=` in fpdf2 row
  - Wrong: `add_font(fname=name, style=style, fname=path)` (Python syntax error — duplicate kwarg)
  - Fixed: `add_font(fname=path, style=style)` (single `fname=` parameter)

### code-reviewer
- Universal changes + fixed `memory: true` → `memory: project`
- Added `## Phase 7/8 Additional Review Criteria` section with 6 checks:
  Streamlit polling, st.cache_resource, LangGraph interrupt, Jira ADF, fpdf2 fname=, async bridge

### test-generator
- Universal changes (memory was already `project`)
- Changed `permissionMode: acceptEdits` → `permissionMode: plan` (C3 override)
- Added `## SIOPV Coverage Floor` section: 83% floor, 1,404 tests baseline, Phase 7/8 regression guard
- Updated coverage command from `--cov-fail-under=80` to `--cov-fail-under=83`
- Updated Coverage Target row in report format table from `80%` to `83%`
- Updated result line from "Target 80%" to "Target 83%"

### code-implementer
- Universal changes (memory was already `project`)
- Added `## SIOPV Phase 7/8 Context (Required for Phase 7/8 tasks)` section:
  - Reference to `docs/siopv-phase7-8-context.md`
  - Requirement to add "Stage 3 Library Facts Applied" to Sources Consulted
- Updated step 10 report path from relative to absolute `/Users/bruno/siopv/.ignorar/...`

### async-safety-auditor
- Universal changes (memory was already `project`)
- Changed `permissionMode: plan` → `permissionMode: acceptEdits` (C3 override)
- Added `### 7. Streamlit Async Bridge Verification (Phase 7 Critical)` section with ThreadPoolExecutor pattern
- Updated all grep commands from `"$TARGET/src"` to `/Users/bruno/siopv/src` (hardcoded)

### semantic-correctness-auditor
- Universal changes only (memory was already `project`)
- Changed `permissionMode: plan` → `permissionMode: acceptEdits` (C3 override)
- Updated all grep commands from `"$TARGET/src"` to `/Users/bruno/siopv/src` (hardcoded)

### hex-arch-remediator (NEW)
- Full content from truth-03 Section 3 spec (~65 lines)
- Written verbatim per truth-03
- Placed in `agents/` directory per C10 / Conflict #1

---

## Deviations

### security-auditor: experimental script section removed
The source contained a full self-consistency voting section referencing `.ignorar/experimental-scripts/self-consistency-voting/self-consistency-vote.py` — a path that exists only in sec-llm-workbench, not in siopv. The section was removed from the SIOPV version to avoid dangling path references. The decision criteria table was retained as it provides useful guidance without requiring the script.

No other deviations from truth document specs.

---

## Summary

COMPLETE — 9 agent files created (8 ADAPT + 1 NEW). All corrections C2, C3, C10 applied. Universal changes confirmed for all 8 ADAPT agents. Agent-specific additions per truth-03 applied to all 6 agents with specific changes. hex-arch-remediator created verbatim in agents/ directory.
