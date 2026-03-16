# Stage 4.2 Pre-Compact Handoff Document

**Created:** 2026-03-13
**Purpose:** Capture all decisions and work completed in the Stage 4.2 pre-planning brainstorming session, before `stage4.2-orchestrator-guidelines.md` was written.

---

## 1. SESSION PURPOSE

Pre-planning brainstorming for Stage 4.2 (Claude Code Configuration Implementation). Stage 4.1 is complete. Stage 4.2 is next.

---

## 2. DECISIONS MADE (all final, no re-discussion needed)

### Architecture

- **Document of truth** = 12 truth files in `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/` (truth-00 through truth-11)
- **Orchestrator reads ALL 12 truth files** + `team-management-best-practices.md` + `compaction-proof-handoff-best-practices.md` to plan
- **Each worker agent reads ONLY its assigned truth file** (context efficiency)
- `truth-00` and `truth-09` are the "orchestration backbone" files
- `stage4.2-implementation/` is the output directory for all agent reports

### Execution Mode

Sub-agents with `mode: acceptEdits` (NOT `bypassPermissions` — never works without `--dangerously-skip-permissions`)

### REMEDIATION-HARDENING Decision (Option C)

- NOT part of Stage 4.2
- After Stage 4.2 completes, open fresh SIOPV session
- First task of that SIOPV session: read all directories in `/Users/bruno/siopv/AuditPrePhase7-11mar26/` (stage1 through stage4.2), then produce REMEDIATION-HARDENING orchestrator guidelines
- `truth-11` briefing.md NEXT IMMEDIATE ACTION already updated to reflect this

### User-Level Changes (~/.claude/)

Apply ALL. Mandatory human checkpoint before Batch 7 — orchestrator stops, lists all changes, waits for explicit approval.

### settings.local.json

Deleted. Treat as NEW in implementation (`truth-00` still says ADAPT — disregard, it is NEW).

### No-Improvisation Rule

Added to `team-management-best-practices.md` Section 9. Applies to team lead, orchestrator, and all agents. Any ambiguity → stop → SendMessage to team lead → wait for human approval.

---

## 3. FILES MODIFIED THIS SESSION

| File | Change |
|------|--------|
| `team-management-best-practices.md` | Added Section 9 (mandatory no-improvisation rule); renumbered Anti-Patterns to Section 10 |
| `truth-00-directory-structure.md` | `post-code.sh` changed COPY→ADAPT in 3 places: directory tree, mapping table, implementation order batch 2 item 9 |
| `truth-10-verification-checklist.md` | Agent count corrected: "15 agents (Wave 1:3, Wave 2:2, Wave 3:10)" → "14 agents (Wave 1:3, Wave 2:2, Wave 3:9)" with conflict resolution note |
| `truth-11-compaction-proof-session-continuity.md` | NEXT IMMEDIATE ACTION updated to: "Read all directories in /Users/bruno/siopv/AuditPrePhase7-11mar26/ (stage1 through stage4.2) and produce the REMEDIATION-HARDENING orchestrator guidelines." |
| `/Users/bruno/siopv/.claude/settings.local.json` | DELETED |

All modified files reside in: `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/` (except settings.local.json which was in the SIOPV project root).

---

## 4. FILES CREATED THIS SESSION

| File | Path | Purpose |
|------|------|---------|
| `stage4.2-final-report-spec.md` | `stage4.2-implementation/` | 9 mandatory sections for the final report |
| `stage4.2-naming-and-output-conventions.md` | `stage4.2-implementation/` | Naming convention `{TIMESTAMP}-s42-{agent-slug}.md`, 4 allowed write paths, 9 batch slugs |

---

## 5. WHAT THE ORCHESTRATOR GUIDELINES MUST CONTAIN (not yet written)

The following is the complete specification for `stage4.2-orchestrator-guidelines.md`. All items are final decisions — no brainstorming needed.

1. **Stage 4.2 purpose:** Implementation only, no research, no new decisions.

2. **Input files list:** All 12 truth files (`truth-00` and `truth-09` flagged as orchestration backbone) + `team-management-best-practices.md` + `compaction-proof-handoff-best-practices.md` + `stage4.2-naming-and-output-conventions.md` + `stage4.2-final-report-spec.md`.

3. **Pre-loaded conflict resolutions (all 5, closed facts — no re-analysis):**
   - #1 CRITICAL: `hex-arch-remediator` → automatic in `/verify` Wave 3 (human decision, mandatory)
   - #2 HIGH: add `async: true` to `pre-compact.sh` hook registration in `settings.json`
   - #3 HIGH: use `truth-11` version of Compact Instructions block in `CLAUDE.md` (not `truth-02`)
   - #4 MEDIUM: replace `siopv-remediate` workflow file reference with inline `CLAUDE.md` rules 9-10 reference
   - #5 LOW: agent count is 14 (not 15); Wave 3 has 9 agents

4. **Known discrepancies (pre-resolved, no re-analysis):**
   - `settings.local.json`: `truth-00` says ADAPT but file was deleted → treat as NEW
   - `post-code.sh`: `truth-00` said COPY, corrected to ADAPT (remove META_PROJECT_DIR guard)
   - `.build/` directories: not in `truth-00` batches → assign to Batch 1 alongside foundation files (`mkdir -p .build/checkpoints/pending .build/checkpoints/daily .build/logs/agents .build/logs/sessions`)
   - Hook scripts must be `chmod +x` immediately after creation
   - `truth-10` agent count was 15 → corrected to 14 (already fixed in file)
   - `truth-00` superseded by truth-files where action tags conflict: `truth-01` wins on `post-code.sh`

5. **Implementation:** 8 batches per `truth-00` Section 5 (reference it, don't repeat it).

6. **`.build/` directory creation:** Assign to Batch 1 explicitly.

7. **`chmod +x`:** Required for ALL `.sh` files in `hooks/` immediately after creation.

8. **Source file reading:** For every COPY or ADAPT operation, agent reads source from `/Users/bruno/sec-llm-workbench/.claude/` first.

9. **Execution plan gate:** Orchestrator produces execution plan → saves to disk → sends to team lead via SendMessage → waits for human approval → only then starts Batch 1.

10. **Human checkpoint after EACH batch:** Orchestrator sends batch summary to team lead, team lead confirms to human, human approves before next batch begins (same pattern as Stage 4.1 round checkpoints).

11. **Mandatory human checkpoint before Batch 7 (user-level changes):** Orchestrator lists ALL `~/.claude/` changes in one message, waits for explicit approval.

12. **No-improvisation rule:** Any ambiguity → stop → SendMessage → wait (reference `team-management-best-practices.md` Section 9).

13. **Old briefing.md "copy from meta-project" instruction superseded:** Truth files take priority, do not copy meta-project workflow files — create NEW per `truth-11`.

14. **Output directory and naming:** Reference `stage4.2-naming-and-output-conventions.md`.

15. **Final report:** Reference `stage4.2-final-report-spec.md` — written last, after Batch 8 verification passes, named `stage4.2-final-report.md`.

16. **Model assignment:** Orchestrator = `claude-opus-4-6`, all workers = `claude-sonnet-4-6`.

17. **Spawning architecture:** Orchestrator sends agent specs via SendMessage, team lead spawns all agents.

18. **Agent reports:** Save to disk BEFORE sending SendMessage summary.

---

## 6. NEXT STEP AFTER COMPACT

Write `stage4.2-orchestrator-guidelines.md` at:

```
/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.2-implementation/stage4.2-orchestrator-guidelines.md
```

Use Section 5 of this document as the complete specification. All decisions are final. No brainstorming needed. Just write it.
