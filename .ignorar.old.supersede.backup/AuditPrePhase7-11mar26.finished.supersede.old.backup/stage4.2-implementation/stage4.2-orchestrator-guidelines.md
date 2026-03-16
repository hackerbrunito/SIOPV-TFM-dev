# Stage 4.2 Orchestrator Guidelines

**Stage:** 4.2 — Implementation
**Orchestrator model:** `claude-opus-4-6` | **Worker model:** `claude-sonnet-4-6`
**Date:** 2026-03-13

---

## 1. Purpose and Scope

Implementation only. No research. No new decisions. All decisions are encoded in the 12
truth files and in this document. Follow truth files exactly, applying the corrections and
overrides in Section 5 where they conflict with truth file content.

**Required environment variable** (confirm before starting):
```
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```
If this is not set, TeamCreate will not work. Stop and alert the user immediately.

---

## 2. Input Files (orchestrator reads ALL before planning)

| File | Role |
|------|------|
| `truth-00-directory-structure.md` | **Backbone** — directory tree, batch order, file inventory |
| `truth-09-cross-file-wiring.md` | **Backbone** — dependency graph, conflict registry |
| `truth-01-settings-and-hooks.md` | settings.json + 7 hook specs |
| `truth-02-claude-md.md` | CLAUDE.md for siopv |
| `truth-03-agent-definitions.md` | All 18 agent definitions |
| `truth-04-rules.md` | rules/ directory contents |
| `truth-05-docs.md` | docs/ directory contents |
| `truth-06-skills.md` | skills/ directory + /verify skill |
| `truth-07-memory.md` | SIOPV memory topic file templates |
| `truth-08-user-level.md` | ~/.claude/ changes (9 items) |
| `truth-10-verification-checklist.md` | Acceptance checklist — Batch 8 |
| `truth-11-compaction-proof-session-continuity.md` | Hook script bodies + SIOPV briefing.md content |
| `team-management-best-practices.md` | Orchestration behavior rules |
| `compaction-proof-handoff-best-practices.md` | Context preservation patterns |
| `stage4.2-naming-and-output-conventions.md` | Report naming + write scope |
| `stage4.2-final-report-spec.md` | Final report structure (9 required sections) |

Truth files path: `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/`
Support files path: `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.2-implementation/`
Source (COPY/ADAPT) files path: `/Users/bruno/sec-llm-workbench/.claude/`

**Worker agents read ONLY their assigned truth file per the table in Section 6.**

---

## 3. Pre-Loaded Conflict Resolutions (CLOSED — no re-analysis, implement as stated)

| # | Conflict | Resolution |
|---|----------|-----------|
| #1 CRITICAL | `hex-arch-remediator` placement | In `/verify` Wave 3 — human decision, mandatory. truth-06 is authoritative. truth-03 "on-demand" listing is superseded. |
| #2 HIGH | `async: true` on pre-compact.sh hook | Add to PreCompact entry in settings.json at the **outer entry object level** per truth-01 JSON structure. truth-11's inner-object placement is non-authoritative for JSON structure. |
| #3 HIGH | Compact Instructions block in CLAUDE.md | Use **truth-11 §5 exactly**. truth-02 Compact Instructions section is a redirect placeholder — do NOT copy truth-02's block verbatim. |
| #4 MEDIUM | `siopv-remediate` workflow file reference | Replace `03-human-checkpoints.md` reference with inline reference to CLAUDE.md rules 9–10. File does not exist in siopv. |
| #5 LOW | Agent count | **14 total: Wave 1=3, Wave 2=2, Wave 3=9.** Any "15" in truth files is stale. |

truth-09 §6 lists Conflicts #2/3/4 as open recommendations. **Ignore** — they are pre-resolved above.

---

## 4. Pre-Resolved Discrepancies (apply silently — no decisions needed)

| Discrepancy | Resolution |
|-------------|-----------|
| `settings.local.json`: truth-00 says ADAPT, file was deleted | **NEW** — create from scratch per truth-01 spec |
| `post-code.sh`: truth-00 says COPY | **ADAPT** — remove META_PROJECT_DIR guard; truth-01 wins |
| `.build/` directories: absent from truth-00 batches | Create in **Batch 1** (see Section 6) |
| truth-10 agent count was 15 | Corrected to 14 in truth-10 — no action needed |
| truth-00 action tags vs. truth-files | Truth-files win; truth-00 action tags superseded |

---

## 5. Implementation Corrections (post-Stage-4.1 errors — apply silently)

**C1 — Agent count everywhere:** Write `14` (not 15). Wave 3=9. Arithmetic: 3+2+9=14.

**C2 — CLAUDE.md Compact Instructions block:** truth-02's block is a redirect. Copy verbatim from **truth-11 §5**.

**C3 — `permissionMode: plan` — complete list:** The following agents get `permissionMode: plan` (overrides any `default` found in truth-03 for these names):
`dependency-scanner`, `smoke-test-runner`, `best-practices-enforcer`, `security-auditor`,
`hallucination-detector`, `code-reviewer`, `test-generator`. All other agents: `permissionMode: acceptEdits`.

**C4 — `memory: project` is universal:** Every one of the 15 ADAPT agents gets `memory: project`. Replace any `memory: true` found in source files.

**C5 — hallucination-detector fpdf2 code example:** Agent body has a duplicate `fname=` parameter (Python syntax error). When writing this agent file, remove the duplicate so only one `fname=` appears in the `add_font()` call.

**C6 — verify/SKILL.md META-ONLY refs to remove:** Before writing verify/SKILL.md, delete any line referencing:
- `04-agents.md` (does not exist in siopv)
- `agent-tool-schemas.md` (does not exist in siopv)

**C7 — truth-10 checklist item (hook paths):** PASS when hook bodies contain hardcoded `/Users/bruno/siopv/` paths. This is correct per truth-11 (single-project design). Do NOT expect `${CLAUDE_PROJECT_DIR}`.

**C8 — MEMORY.md actual line count:** File has 216 lines (truth files say 217). Remove lines 200–216 using **string matching** — do not use line numbers.

**C9 — MEMORY.md trim target:** ≤185 lines (truth-10 wins over truth-00's ≤200).

**C10 — truth-00 Batch 7 missing 4 files:** Create SIOPV memory directory before writing any Batch 7 files:
```
mkdir -p ~/.claude/projects/-Users-bruno-siopv/memory/
```
Then create these 4 files (content from truth-07):
- `~/.claude/projects/-Users-bruno-siopv/memory/siopv-stage-results.md`
- `~/.claude/projects/-Users-bruno-siopv/memory/siopv-architecture.md`
- `~/.claude/projects/-Users-bruno-siopv/memory/siopv-violations.md`
- `~/.claude/projects/-Users-bruno-siopv/memory/siopv-phase7-8-context.md`

**C11 — siopv-hooks-stage4.md:** Use truth-08 version (not truth-07).

**C12 — SIOPV briefing.md source:** Content from truth-11 only. Do NOT copy from `/Users/bruno/sec-llm-workbench/.claude/workflow/briefing.md`.

**C13 — File count sign-off:** Do NOT use `find .claude -type f | wc -l`. Count is inconsistent across truth files. Use the per-item wiring checklist in truth-10 only.

---

## 6. Implementation Order — Batch 0 + 8 Batches

### Batch 0 — Directory Skeleton (orchestrator executes directly, no worker spawned)

Before any worker is spawned, run these commands in `/Users/bruno/siopv/`:

```bash
mkdir -p .claude/agents
mkdir -p .claude/hooks
mkdir -p .claude/rules
mkdir -p .claude/docs
mkdir -p .claude/skills/verify
mkdir -p .claude/skills/langraph-patterns
mkdir -p .claude/skills/openfga-patterns
mkdir -p .claude/skills/presidio-dlp
mkdir -p .claude/skills/coding-standards-2026
mkdir -p .claude/skills/siopv-remediate
mkdir -p .claude/workflow
mkdir -p .build/checkpoints/pending
mkdir -p .build/checkpoints/daily
mkdir -p .build/logs/agents
mkdir -p .build/logs/sessions
```

Verify with `ls -R /Users/bruno/siopv/.claude/` before spawning Batch 1 worker.

### Complete Directory Tree (authoritative — every file to be created)

```
siopv/.claude/
├── CLAUDE.md                                  [NEW]         truth-02
├── settings.json                              [NEW]         truth-01
├── settings.local.json                        [NEW]         truth-01
├── agents/
│   ├── best-practices-enforcer.md             [ADAPT]       truth-03
│   ├── security-auditor.md                    [ADAPT]       truth-03
│   ├── hallucination-detector.md              [ADAPT]       truth-03  ← fix duplicate fname= (C5)
│   ├── code-reviewer.md                       [ADAPT]       truth-03
│   ├── test-generator.md                      [ADAPT]       truth-03
│   ├── async-safety-auditor.md                [ADAPT]       truth-03
│   ├── semantic-correctness-auditor.md        [ADAPT]       truth-03
│   ├── integration-tracer.md                  [ADAPT]       truth-03
│   ├── smoke-test-runner.md                   [ADAPT]       truth-03  ← permissionMode: plan (C3)
│   ├── config-validator.md                    [ADAPT]       truth-03
│   ├── dependency-scanner.md                  [ADAPT]       truth-03  ← permissionMode: plan (C3)
│   ├── circular-import-detector.md            [ADAPT]       truth-03
│   ├── import-resolver.md                     [ADAPT]       truth-03
│   ├── code-implementer.md                    [ADAPT]       truth-03
│   ├── xai-explainer.md                       [ADAPT]       truth-03
│   ├── hex-arch-remediator.md                 [NEW]         truth-03  ← Wave 3 (Conflict #1)
│   ├── phase7-builder.md                      [NEW]         truth-03
│   └── phase8-builder.md                      [NEW]         truth-03
├── hooks/
│   ├── session-start.sh                       [ADAPT]       truth-01 + truth-11 bodies
│   ├── session-end.sh                         [ADAPT]       truth-01 + truth-11 bodies
│   ├── pre-compact.sh                         [ADAPT]       truth-01 + truth-11 bodies  ← async:true (Conflict #2)
│   ├── post-code.sh                           [ADAPT]       truth-01  ← remove META_PROJECT_DIR guard
│   ├── pre-git-commit.sh                      [COPY]        truth-01
│   ├── pre-write.sh                           [COPY]        truth-01
│   └── coverage-gate.sh                       [NEW]         truth-01
├── rules/
│   ├── agent-reports.md                       [COPY]        truth-04
│   ├── placeholder-conventions.md             [COPY]        truth-04
│   └── tech-stack.md                          [ADAPT]       truth-04
├── docs/
│   ├── verification-thresholds.md             [ADAPT]       truth-05
│   ├── model-selection-strategy.md            [COPY]        truth-05
│   ├── python-standards.md                    [COPY]        truth-05
│   ├── errors-to-rules.md                     [NEW]         truth-05
│   └── siopv-phase7-8-context.md              [NEW]         truth-05
├── skills/
│   ├── verify/SKILL.md                        [ADAPT]       truth-06  ← count=14, remove META-ONLY refs (C1, C6)
│   ├── langraph-patterns/SKILL.md             [COPY]        truth-06
│   ├── openfga-patterns/SKILL.md              [COPY]        truth-06
│   ├── presidio-dlp/SKILL.md                  [COPY]        truth-06
│   ├── coding-standards-2026/SKILL.md         [COPY]        truth-06
│   └── siopv-remediate/SKILL.md               [NEW]         truth-06  ← no 03-human-checkpoints.md ref (Conflict #4)
└── workflow/
    ├── briefing.md                            [NEW]         truth-11  ← from truth-11 §4, NOT meta-project (C12)
    └── compaction-log.md                      [NEW]         truth-11  ← create empty

All hooks → chmod +x immediately after writing (Batch 2).
Source for ADAPT/COPY → read from /Users/bruno/sec-llm-workbench/.claude/ first.
```

### Batches 1–8 — File Implementation

Reference truth-00 Section 5 for the complete file list per batch. Corrections above apply.

| Batch | Worker truth file | Content summary | Critical notes |
|-------|------------------|-----------------|---------------|
| **1 — Foundation** | truth-11 | `workflow/briefing.md`, `workflow/compaction-log.md`, `docs/siopv-phase7-8-context.md`, `.build/` dirs | `.build/` tree: `checkpoints/pending`, `checkpoints/daily`, `logs/agents`, `logs/sessions`. briefing.md from truth-11 §4 (C12). compaction-log.md: create empty. |
| **2 — Settings & Hooks** | truth-01 | `settings.json`, `settings.local.json` (NEW), 7 hook `.sh` files | `async: true` at outer entry level on PreCompact. `chmod +x` every `.sh` immediately after writing. Read source from sec-llm-workbench first. post-code.sh → ADAPT (remove META_PROJECT_DIR guard). |
| **3 — CLAUDE.md** | truth-02 | `CLAUDE.md` | Compact Instructions block from truth-11 §5, not truth-02 (C2). |
| **4 — Rules & Docs** | truth-04 + truth-05 | `rules/*.md` (3 files), `docs/*.md` (4 files) | Read source from sec-llm-workbench before ADAPT. Apply all siopv-specific edits per truth-04/05. |
| **5 — Skills** | truth-06 | 6 `SKILL.md` files | verify/SKILL.md: count=14, remove META-ONLY refs (C6). siopv-remediate: inline CLAUDE.md rule ref instead of 03-human-checkpoints.md (Conflict #4). |
| **6 — Agents** | truth-03 | 18 agent `.md` files (15 ADAPT + 3 NEW) | Read source from sec-llm-workbench. Apply full permissionMode list (C3). Apply memory:project to all 15 ADAPT (C4). Fix hallucination-detector (C5). hex-arch-remediator → Wave 3 (Conflict #1). |
| **7 — User-level** | truth-08 | 9 items in `~/.claude/`: CLAUDE.md, settings.json, deterministic-execution-protocol.md, errors-to-rules.md, MEMORY.md (trim), siopv-hooks-stage4.md (create), researcher-1.md (create), researcher-2.md (create), researcher-3.md (create) | **MANDATORY HUMAN CHECKPOINT BEFORE THIS BATCH.** Create SIOPV memory dir + 4 topic files (C10). Use truth-08 for siopv-hooks-stage4.md (C11). MEMORY.md: remove lines 200–216, target ≤185 (C8, C9). |
| **8 — Verification** | truth-10 | Run acceptance checklist | Per-item checklist only — no file count command (C13). Report every item PASS/FAIL. Any FAIL → stop, alert orchestrator. |

---

## 7. Execution Protocol

**Step 1 — Execution plan gate:**
Write a plan file named `{TIMESTAMP}-s42-execution-plan.md` in `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.2-implementation/` listing every file for every batch. Send to team lead via `SendMessage(to="claude-main", ...)`. Wait for explicit human "approved" reply. Do not start Batch 1 until that approval arrives.

**Step 2 — Batch gate (every batch):**
After each batch completes: send `SendMessage(to="claude-main", ...)` with batch number, exact files created/modified, any deviations from truth files, PASS/FAIL status. Wait for explicit approval before starting the next batch.

**Step 3 — Batch 7 mandatory checkpoint:**
Before spawning the Batch 7 worker: send a dedicated `SendMessage(to="claude-main", ...)` listing all 9 `~/.claude/` changes with exact absolute paths and action (EDIT/CREATE/TRIM). Do not proceed until the human types explicit approval.

**Step 4 — No-improvisation rule:**
Any ambiguity, unexpected file content, missing section, or unclear instruction → STOP → `SendMessage(to="claude-main", ...)` describing exactly what is ambiguous → wait for human response. Never infer. Never guess. Reference `team-management-best-practices.md` Section 9.

**Step 5 — Worker spawn spec (include ALL fields in every spawn request):**
When asking team lead to spawn a worker, the SendMessage body MUST specify:
- `name`: worker slug (e.g., `batch2-worker`)
- `model`: `claude-sonnet-4-6`
- `mode`: `acceptEdits`
- `truth_file`: full absolute path to the single truth file this worker reads
- `batch`: batch number and name
- `corrections`: list the C-numbers from Section 5 that apply to this batch
- `prompt_summary`: one-paragraph prompt telling the worker exactly what to do

**Step 6 — Report before message:**
Worker saves report to disk. Filename per naming conventions. Report path included in every SendMessage body. Team lead does not relay a summary until the report file exists on disk.

---

## 8. Output, Naming, and Model Assignment

**Models:** Orchestrator = `claude-opus-4-6`; all workers = `claude-sonnet-4-6`

**Spawning:** Orchestrator → `SendMessage(to="claude-main")` with worker spec → team lead spawns worker. Orchestrator never calls Agent tool directly.

**Mode:** All workers `mode: acceptEdits`. Never `bypassPermissions`.

**Report naming:** `{TIMESTAMP}-s42-{slug}.md` — timestamp at moment agent begins writing report.
Slugs: `batch1-foundation`, `batch2-settings-hooks`, `batch3-claude-md`, `batch4-rules-docs`,
`batch5-skills`, `batch6-agents`, `batch7-user-level`, `batch8-verification`.

**Write scope (4 paths only — any other path is a violation):**
- `/Users/bruno/siopv/.claude/` — implementation files
- `/Users/bruno/siopv/.build/` — build directories
- `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.2-implementation/` — reports
- `/Users/bruno/.claude/` — user-level (Batch 7 only)

---

## 9. Final Report

Written by orchestrator after Batch 8 passes — last artifact of Stage 4.2.
Named exactly: `stage4.2-final-report.md` (no timestamp prefix).
Structure: follow `stage4.2-final-report-spec.md` exactly — 9 sections, no `...` placeholders, ≤300 lines.

Section 4 row 2 (settings.local.json) and row 3 (agent count): mark as "pre-resolved before Stage 4.2 began".

Section 9 exact text: "Read all directories in `/Users/bruno/siopv/AuditPrePhase7-11mar26/`
(stage1 through stage4.2) and produce the REMEDIATION-HARDENING orchestrator guidelines."

---

*End of Stage 4.2 Orchestrator Guidelines*
