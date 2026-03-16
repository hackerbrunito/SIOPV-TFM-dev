# Stage 4.2 — Naming and Output Conventions

All agents working in Stage 4.2 MUST follow these conventions without exception.

---

## 1. Output Directory

All agent reports go to:

```
/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.2-implementation/
```

This is the only location for reports. Do not create subdirectories.

---

## 2. Agent Report Naming Convention

Format: `{TIMESTAMP}-s42-{agent-slug}.md`

- **TIMESTAMP:** `YYYY-MM-DD-HHmmss` (24-hour clock, no separators in time portion)
- **agent-slug:** lowercase, hyphen-separated, descriptive

| Agent / Batch | slug |
|---------------|------|
| Batch 1 — Foundation | `batch1-foundation` |
| Batch 2 — Settings & Hooks | `batch2-settings-hooks` |
| Batch 3 — CLAUDE.md | `batch3-claude-md` |
| Batch 4 — Rules & Docs | `batch4-rules-docs` |
| Batch 5 — Skills | `batch5-skills` |
| Batch 6 — Agents | `batch6-agents` |
| Batch 7 — User-level | `batch7-user-level` |
| Batch 8 — Verification | `batch8-verification` |
| Final Report | `final-report` |

**Example:** `2026-03-13-143022-s42-batch2-settings-hooks.md`

Generate TIMESTAMP at the moment the agent begins writing its report:

```bash
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
REPORT="/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.2-implementation/${TIMESTAMP}-s42-{slug}.md"
```

---

## 3. Required Report Contents

Each agent report MUST contain all of the following sections:

```
## Agent
Slug: {slug}
Batch: {N}

## Files Created/Modified
- /absolute/path/to/file — CREATED
- /absolute/path/to/file — MODIFIED
- /absolute/path/to/file — CHMOD 755

## Deviations from Truth File
No deviations.
(OR: list each deviation with justification)

## Verification Steps
- JSON syntax check: PASS (or FAIL + detail)
- chmod confirmation: PASS
- File exists check: PASS for all N files
- (any additional checks specific to this batch)

## Summary (for SendMessage)
3–5 lines max. State: batch number, files created, any issues, pass/fail status.
```

---

## 4. Final Report

Named exactly (no timestamp prefix):

```
stage4.2-final-report.md
```

Produced last — after all 8 batches complete and Batch 8 verification passes. Written to the same output directory.

---

## 5. Mandatory Rules

**Rule A — Save before send:** Every agent saves its report to disk before calling SendMessage. No exceptions. SendMessage must reference the report path.

**Rule B — Write scope:** No agent writes implementation files outside these four paths:

| Scope | Allowed Path |
|-------|-------------|
| Implementation files | `/Users/bruno/siopv/.claude/` |
| Build directories | `/Users/bruno/siopv/.build/` |
| Agent reports | `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.2-implementation/` |
| User-level (Batch 7 only) | `/Users/bruno/.claude/` |

Any write outside these paths is a violation. Stop and report to the orchestrator.
