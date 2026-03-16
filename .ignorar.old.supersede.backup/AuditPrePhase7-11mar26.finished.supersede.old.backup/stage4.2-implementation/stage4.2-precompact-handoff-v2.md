# Stage 4.2 Pre-Work Handoff v2

**Created:** 2026-03-13
**Purpose:** Comprehensive, self-contained handoff for the next session after compaction.
The next session must read this document first and fix all BLOCKING and HIGH gaps in the
orchestrator guidelines before spawning the Stage 4.2 orchestrator. Zero guessing allowed.

---

## 1. SESSION OVERVIEW

### What was accomplished across two pre-work sessions

**Session 1 (brainstorming):**
- Resolved all 5 conflicts in the truth files (Section 8 below for full list)
- Made 20 architectural decisions (all final — Section 8)
- Created `stage4.2-final-report-spec.md` and `stage4.2-naming-and-output-conventions.md`
- Modified truth files: team-management-best-practices.md (added Section 9 no-improvisation rule), truth-00 (post-code.sh COPY→ADAPT), truth-10 (agent count 15→14), truth-11 (NEXT IMMEDIATE ACTION)
- Deleted `/Users/bruno/siopv/.claude/settings.local.json`

**Session 2 (guidelines writing + gap analysis):**
- Wrote `stage4.2-orchestrator-guidelines.md` (284 lines) — primary orchestrator instruction document
- Edited truth files: truth-00 (15→14 agent list), truth-10 lines 59, 111, 62 (agent count + Batch 6 file count), truth-01 (async:true added), truth-02 (Compact Instructions replaced with redirect), truth-06 (siopv-remediate reference fixed)
- Ran a gap analysis agent that found 29 gaps in the orchestrator guidelines (full list in Section 5)

### Current status of Stage 4.2

Stage 4.2 implementation has NOT started. The orchestrator guidelines exist but have 29 gaps
that must be fixed before the orchestrator is spawned. The next session's sole task is:
fix BLOCKING and HIGH gaps, then spawn the orchestrator.

---

## 2. ALL FILES IN stage4.2-implementation/ (current inventory)

Directory: `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.2-implementation/`

| File | Size | Description |
|------|------|-------------|
| `stage4.2-final-report-spec.md` | 6314 bytes | Required structure for the Stage 4.2 final report (9 mandatory sections, ≤300 lines) |
| `stage4.2-naming-and-output-conventions.md` | 2874 bytes | Naming convention `{TIMESTAMP}-s42-{agent-slug}.md`, 4 allowed write paths, 9 batch slugs |
| `stage4.2-orchestrator-guidelines.md` | 17497 bytes | **PRIMARY** — orchestrator instruction document (284 lines, 9 sections). Has 29 gaps — see Section 5. |
| `stage4.2-precompact-handoff.md` | 7350 bytes | Session 1 decisions + specification that drove the orchestrator guidelines |
| `stage4.2-session-handoff-DRAFT.md` | 22326 bytes | Session 2 draft handoff: B-series edits made, C-series corrections, D-series guidelines summary, E-series decisions, F-series next steps |
| `stage4.2-precompact-handoff-v2.md` | (this file) | Final handoff combining all sessions + gap analysis — authoritative source for next session |

---

## 3. ALL TRUTH FILE EDITS MADE (before/after)

All truth files are in: `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/`

### Session 1 Edits

**team-management-best-practices.md:**
- Before: had no Section 9
- After: Section 9 "No-Improvisation Rule" added; former Section 9 Anti-Patterns renumbered to Section 10

**truth-00-directory-structure.md:**
- Before: `post-code.sh` tagged as `[COPY]` in directory tree, mapping table, and Batch 2 item 9
- After: `post-code.sh` tagged as `[ADAPT]` in all three places (remove META_PROJECT_DIR guard)

**truth-10-verification-checklist.md:**
- Before: "15 agents (Wave 1:3, Wave 2:2, Wave 3:10)"
- After: "14 agents (Wave 1:3, Wave 2:2, Wave 3:9) — hex-arch-remediator included in Wave 3 per Conflict #1 resolution; count corrected from original '15' per Conflict #5 resolution"

**truth-11-compaction-proof-session-continuity.md:**
- Before: NEXT IMMEDIATE ACTION pointed to Phase 7/8 implementation
- After: "Read all directories in `/Users/bruno/siopv/AuditPrePhase7-11mar26/` (stage1 through stage4.2) and produce the REMEDIATION-HARDENING orchestrator guidelines."

**/Users/bruno/siopv/.claude/settings.local.json:**
- Before: file existed
- After: DELETED (treat as NEW in implementation)

### Session 2 Edits

**truth-00-directory-structure.md line 221:**
- Before: `[ADAPT — 15-agent list]`
- After: `[ADAPT — 14-agent list]`

**truth-10-verification-checklist.md line 59:**
- Contains direction indicator `15→14` for the implementer — already correct as-is

**truth-10-verification-checklist.md line 111:**
- Before: `lists exactly 15 agents in waves (Wave 1: 3, Wave 2: 2, Wave 3: 10)`
- After: `lists exactly 14 agents in waves (Wave 1: 3, Wave 2: 2, Wave 3: 9) — hex-arch-remediator included in Wave 3 per Conflict #1 resolution; count corrected from original "15" per Conflict #5 resolution`

**truth-10-verification-checklist.md line 62:**
- Before: `### Batch 6 — Agents (27 files; start with code-implementer)`
- After: `### Batch 6 — Agents (18 files; start with code-implementer)`

**truth-01-settings-and-hooks.md:**
- Before: PreCompact hook entry in settings.json spec had no `async` property
- After: `"async": true` added at the outer entry object level of the PreCompact hook entry (Conflict #2 resolution)

**truth-02-claude-md.md lines 104-107:**
- Before: Compact Instructions section contained actual content (a list of items)
- After: Replaced with redirect: `> **IMPLEMENTING AGENT:** Use the Compact Instructions block from truth-11-compaction-proof-session-continuity.md Section 5 verbatim — NOT this placeholder.`

**truth-06-skills.md:**
- Before: `siopv-remediate/SKILL.md` spec referenced `03-human-checkpoints.md`
- After: Reference replaced with inline reference to CLAUDE.md rules 9–10 (Conflict #4 resolution)

**stage4.2-final-report-spec.md Section 4:**
- Before: table had a stale row
- After: Table has exactly 3 rows; stale row removed

---

## 4. ORCHESTRATOR GUIDELINES — CURRENT STATE

**File:** `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.2-implementation/stage4.2-orchestrator-guidelines.md`
**Line count:** 284
**Status:** Has 29 gaps (see Section 5). Do NOT spawn orchestrator until BLOCKING and HIGH gaps are fixed.

### Section Summary

| # | Title | Description |
|---|-------|-------------|
| 1 | Purpose and Scope | Implementation-only mandate; `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` prerequisite |
| 2 | Input Files | 16-file reading list with absolute paths; truth-00 and truth-09 flagged as backbone |
| 3 | Pre-Loaded Conflict Resolutions | 5 conflicts resolved and closed; truth-09 §6 open items flagged as "ignore" |
| 4 | Pre-Resolved Discrepancies | 5 known discrepancies with silent resolutions (no orchestrator decision needed) |
| 5 | Implementation Corrections | 13 corrections C1–C13 to apply without question |
| 6 | Implementation Order | Batch 0 mkdir commands + full 41-file directory tree + 8-batch table with truth files |
| 7 | Execution Protocol | 6-step protocol: plan gate, batch gates, Batch 7 checkpoint, no-improvisation, worker spec template, report-before-message |
| 8 | Output, Naming, Model Assignment | Models, spawning architecture, mode, slug list, 4 write paths |
| 9 | Final Report | Name, structure reference, Section 4 notes, Section 9 exact text |

---

## 5. ALL GAPS IN ORCHESTRATOR GUIDELINES (must fix before spawning orchestrator)

### BLOCKING (6) — must resolve before orchestrator starts

**B1 — Batch 1 `.build/` directory creation: truth file mismatch**
- What is missing: Worker reads truth-11 but `.build/` directory specs are NOT in truth-11. The mkdir commands for `.build/` are in the Batch 0 section, but the Batch 1 worker prompt in Section 6 says "truth-11" as the sole truth file. The Batch 1 worker will not know what to do with `.build/` because it's only reading truth-11.
- Section affected: Section 6, Batch 1 row in the batch table
- Correct content: Batch 1 worker must read BOTH truth-11 (for briefing.md and compaction-log.md) AND confirm that `.build/` dirs were already created by Batch 0. Add explicit note: "`.build/` directories are created in Batch 0 by the orchestrator directly — the Batch 1 worker does NOT need to create them; verify they exist with `ls /Users/bruno/siopv/.build/`."

**B2 — Batch 1 worker truth file mismatch: siopv-phase7-8-context.md**
- What is missing: The Batch 1 table row says "Worker truth file: truth-11" but `docs/siopv-phase7-8-context.md` is a Batch 1 item whose content spec is in truth-05 (not truth-11). The worker will not find the content for this file in truth-11.
- Section affected: Section 6, Batch 1 row
- Correct content: Change Batch 1 worker truth file to "truth-11 AND truth-05". Add note: "`docs/siopv-phase7-8-context.md` content is in truth-05; `workflow/briefing.md` and `workflow/compaction-log.md` content is in truth-11."

**B3 — Worker spawn specification template missing**
- What is missing: Section 7 Step 5 lists 7 required fields (name, model, mode, truth_file, batch, corrections, prompt_summary) but provides no example SendMessage payload. Orchestrator has no concrete template to follow and will improvise the format.
- Section affected: Section 7, Step 5
- Correct content: Add a concrete example SendMessage body immediately after the field list:
```
SendMessage(to="claude-main", message="""
SPAWN WORKER REQUEST
name: batch2-worker
model: claude-sonnet-4-6
mode: acceptEdits
truth_file: /Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/truth-01-settings-and-hooks.md
batch: 2 — Settings & Hooks
corrections: C2, C3, C4, C7 (see guidelines Section 5)
prompt_summary: Read truth-01 in full. Write settings.json and settings.local.json (NEW) to /Users/bruno/siopv/.claude/. Write 7 hook .sh files to /Users/bruno/siopv/.claude/hooks/. Apply async:true at outer level of PreCompact entry. Run chmod +x on every .sh file immediately after writing. Read source files from /Users/bruno/sec-llm-workbench/.claude/ before any ADAPT operation. Remove META_PROJECT_DIR guard from post-code.sh. Save report to /Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.2-implementation/{TIMESTAMP}-s42-batch2-settings-hooks.md before sending any SendMessage.
""")
```

**B4 — CLAUDE.md Compact Instructions block not embedded**
- What is missing: Correction C2 says "copy verbatim from truth-11 §5" but the actual text of that block is NOT reproduced in the guidelines. The orchestrator and Batch 3 worker must navigate to truth-11 §5 independently — but if truth-11 is long, they may miss or misidentify §5.
- Section affected: Section 5, C2
- Correct content: In C2, add the exact section identifier: "truth-11 §5 is the section titled 'CLAUDE.md Compact Instructions Block' — copy everything between the opening triple-backtick fence and closing triple-backtick fence, verbatim, no modifications."

**B5 — Batch 4 worker truth file conflict: rules/*.md are in truth-05, not truth-04**
- What is missing: Section 6 Batch 4 says "truth-04 + truth-05" but truth-00 maps all rules/*.md files to truth-05. truth-04 may contain only the rules list without implementation specs. Must clarify authoritatively.
- Section affected: Section 6, Batch 4 row
- Correct content: Verify by reading truth-00 mapping table. If rules/*.md specs are in truth-05, change Batch 4 worker truth file to "truth-05 ONLY (rules files are in truth-05, not truth-04)". If truth-04 truly covers rules, add explicit note that truth-05 wins on docs/*.md and truth-04 wins on rules/*.md.

**B6 — Working directory for Batch 0 mkdir commands not explicitly set**
- What is missing: The 15 mkdir commands in Section 6 Batch 0 use relative paths (`.claude/agents`, `.build/checkpoints/pending`, etc.) but no explicit `cd` or absolute path prefix. If the orchestrator's shell is not in `/Users/bruno/siopv/`, the directories will be created in the wrong location.
- Section affected: Section 6, Batch 0 block
- Correct content: Change the mkdir block to use absolute paths:
```bash
mkdir -p /Users/bruno/siopv/.claude/agents
mkdir -p /Users/bruno/siopv/.claude/hooks
mkdir -p /Users/bruno/siopv/.claude/rules
mkdir -p /Users/bruno/siopv/.claude/docs
mkdir -p /Users/bruno/siopv/.claude/skills/verify
mkdir -p /Users/bruno/siopv/.claude/skills/langraph-patterns
mkdir -p /Users/bruno/siopv/.claude/skills/openfga-patterns
mkdir -p /Users/bruno/siopv/.claude/skills/presidio-dlp
mkdir -p /Users/bruno/siopv/.claude/skills/coding-standards-2026
mkdir -p /Users/bruno/siopv/.claude/skills/siopv-remediate
mkdir -p /Users/bruno/siopv/.claude/workflow
mkdir -p /Users/bruno/siopv/.build/checkpoints/pending
mkdir -p /Users/bruno/siopv/.build/checkpoints/daily
mkdir -p /Users/bruno/siopv/.build/logs/agents
mkdir -p /Users/bruno/siopv/.build/logs/sessions
```
Also update the verify command from `ls -R /Users/bruno/siopv/.claude/` to confirm absolute paths were created.

---

### HIGH (6) — must resolve or orchestrator will improvise

**H1 — settings.json readiness not stated**
- What is missing: Section 6 Batch 2 says "NEW per truth-01" but does not state whether the JSON in truth-01 §1 is copy-paste-ready or needs modifications before writing. The worker will not know if it should transcribe or transform.
- Section affected: Section 6, Batch 2 critical notes
- Correct content: Add: "The settings.json content in truth-01 §1 is copy-paste-ready as-is after applying the Conflict #2 async:true edit (already applied to truth-01). No additional modifications needed beyond what C2–C7 specify."

**H2 — `chmod +x` exact command not specified**
- What is missing: Section 6 Batch 2 says "chmod +x every .sh immediately after writing" but truth-10 wiring check uses "CHMOD 755". These are different permissions. The exact command is ambiguous.
- Section affected: Section 6, Batch 2 critical notes
- Correct content: Add the exact command: `chmod +x /Users/bruno/siopv/.claude/hooks/*.sh` — run once after all 7 hook files are written.

**H3 — Execution plan file naming convention not explicitly referenced**
- What is missing: Section 7 Step 1 says use slug `execution-plan` in the filename but does not reference the naming convention document that defines the format `{TIMESTAMP}-s42-{slug}.md`. A new-session orchestrator unfamiliar with the convention could format the filename differently.
- Section affected: Section 7, Step 1
- Correct content: Add: "Full filename: `{TIMESTAMP}-s42-execution-plan.md` where TIMESTAMP is generated at the moment of writing using `$(date +%Y-%m-%d-%H%M%S)`. Naming convention per `stage4.2-naming-and-output-conventions.md`."

**H4 — Approval criteria undefined**
- What is missing: Section 7 Steps 1, 2, 3 all say "wait for explicit human approval" but never define what text constitutes approval. The orchestrator cannot distinguish "ok" from "approved" from "looks good — start Batch 1".
- Section affected: Section 7, Steps 1–3
- Correct content: Add to Step 1: "Explicit approval means the human types a message containing 'approved' (case-insensitive) or an unambiguous equivalent such as 'proceed', 'go ahead', 'start'. Any other response is NOT approval — ask for clarification."

**H5 — Timestamp generation method not specified**
- What is missing: Section 8 says "timestamp at moment agent begins writing report" but does not specify how to generate it. An agent using Python's `datetime.now()` will produce a different format than `$(date +%Y-%m-%d-%H%M%S)`.
- Section affected: Section 8
- Correct content: Add: "Generate timestamp with shell command `$(date +%Y-%m-%d-%H%M%S)` — format: `YYYY-MM-DD-HHmmss` (24-hour). Example: `2026-03-13-142305`. Never use Python or any other method."

**H6 — Pending directory ordering: pre-git-commit.sh fires before `.build/` created**
- What is missing: `pre-git-commit.sh` reads `.build/checkpoints/pending/`. If a git commit happens between Batch 0 (which creates `.build/`) and Batch 2 (which installs the hook), the hook will fire without `.build/` existing. More critically, if the orchestrator's Batch 0 is incomplete, any git operation will fail.
- Section affected: Section 6, Batch 0
- Correct content: Add after the mkdir block: "IMPORTANT: Run Batch 0 mkdir commands and verify ALL paths exist before spawning any worker. The pre-git-commit.sh hook (installed in Batch 2) reads `.build/checkpoints/pending/` — this directory MUST exist before the hook is installed."

---

### MEDIUM (7) — should resolve for full determinism

**M1 — ADAPT/COPY/NEW procedures not defined**
- What is missing: No procedure section defining what each action type means concretely.
- Correct content: Add to Section 6 preamble: "COPY = read source file from `/Users/bruno/sec-llm-workbench/.claude/{path}`, write to siopv target path unchanged. ADAPT = read source, apply truth-file modifications exactly as specified, write modified version. NEW = create from scratch using only the truth file content; do NOT read from sec-llm-workbench."

**M2 — Memory directory creation for Batch 7 not in worker prompt spec**
- What is missing: C10 specifies `mkdir -p ~/.claude/projects/-Users-bruno-siopv/memory/` but this command is only in Section 5. The Batch 7 worker table row does not explicitly call this out.
- Correct content: Add to Batch 7 critical notes: "FIRST: run `mkdir -p /Users/bruno/.claude/projects/-Users-bruno-siopv/memory/` before writing any of the 4 topic files."

**M3 — CLAUDE.md body text "15 verification agents" not called out**
- What is missing: C1 says "write 14 everywhere" but does not explicitly flag the CLAUDE.md body sentence that may say "runs 15 verification agents". Worker could miss this instance.
- Correct content: Add to C1: "In CLAUDE.md specifically, the body may contain the phrase 'runs 15 verification agents' — replace with 'runs 14 verification agents'."

**M4 — Source file error handling not specified**
- What is missing: No instruction for what the worker does if a source file does not exist in `/Users/bruno/sec-llm-workbench/.claude/` for a COPY or ADAPT operation.
- Correct content: Add: "If a source file for a COPY or ADAPT operation does not exist in sec-llm-workbench, stop immediately and send SendMessage to team lead describing which file is missing. Do NOT guess or create from scratch — this is a BLOCKING issue."

**M5 — Ambiguity examples not given for the no-improvisation rule**
- What is missing: Step 4 says "any ambiguity → stop" but gives no examples, making it unclear when to stop vs. proceed.
- Correct content: Add examples: "Ambiguous situations that require stopping: (a) a truth file section is missing or empty, (b) two truth files contradict each other on content not covered by Sections 3–5, (c) a source file has unexpected content that does not match truth-file expectations, (d) a file to be ADAPT-ed does not exist in sec-llm-workbench."

**M6 — post-code.sh guard removal not in Batch 2 worker notes**
- What is missing: The pre-resolved discrepancy for post-code.sh (ADAPT: remove META_PROJECT_DIR guard) is in Section 4 but not called out explicitly in the Batch 2 worker critical notes in the batch table.
- Correct content: Add to Batch 2 critical notes: "post-code.sh → ADAPT (not COPY): remove the `META_PROJECT_DIR` guard block. The guard is present in the sec-llm-workbench source but must NOT appear in the siopv version."

**M7 — Hook path pattern not explained**
- What is missing: settings.json uses `$CLAUDE_PROJECT_DIR` for hook command paths (shell portability) while hook bodies hardcode `/Users/bruno/siopv/` (single-project design). This apparent inconsistency is unexplained and a worker may try to normalize them.
- Correct content: Add note to Batch 2: "settings.json hook command entries use `$CLAUDE_PROJECT_DIR` for the command path — this is intentional (shell portability for Claude Code). Hook `.sh` bodies hardcode `/Users/bruno/siopv/` — also intentional (single-project design). Both patterns are correct; do NOT normalize them."

---

### LOW (10) — nice to have, won't block

**L1:** Final report Section 3 vs Section 4 distinction not explained (conflicts vs. discrepancies are different categories — Section 3 covers resolved conflicts, Section 4 covers pre-resolved discrepancies — a brief note would prevent confusion).

**L2:** Wave 3 agent list (9 agents) never spelled out in guidelines. Full list: async-safety-auditor, semantic-correctness-auditor, integration-tracer, smoke-test-runner, config-validator, dependency-scanner, circular-import-detector, import-resolver, hex-arch-remediator.

**L3:** `CLAUDE.local.md` not mentioned in guidelines. truth-02 §2 specifies it but it is absent from the directory tree in Section 6.

**L4:** Execution plan file should be listed in Final Report Section 8 (artifacts inventory).

**L5:** truth-00 does not include `.build/` mkdir in Batch 1 — pre-resolved discrepancy (Batch 0 handles it) but not documented as such in the guidelines.

**L6:** `"async": true` exact JSON placement not shown with a concrete example in the guidelines (it's only described as "outer entry object level").

**L7:** Batch 8 FAIL handling says "stop, alert orchestrator" but provides no next steps after a FAIL is reported.

**L8:** settings.json JSON validation not specified — should run `jq . /Users/bruno/siopv/.claude/settings.json` after writing to confirm valid JSON.

**L9:** coverage-gate.sh logic edge case (minor truth-01 issue, not a guidelines problem).

**L10:** MEMORY.md "string matching" removal method: C8 says "use string matching" but does not specify which exact string to match for the boundary. Worker must identify the correct starting line to remove.

---

## 6. WHAT THE NEXT SESSION MUST DO (step by step)

1. **Read this file in full** before taking any action.

2. **Fix all 6 BLOCKING gaps** in `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.2-implementation/stage4.2-orchestrator-guidelines.md`:
   - B1: Edit Batch 1 row — add note that `.build/` dirs are Batch 0 responsibility; Batch 1 worker only verifies
   - B2: Edit Batch 1 row — change truth file to "truth-11 AND truth-05"; add note on siopv-phase7-8-context.md
   - B3: Edit Section 7 Step 5 — add concrete SendMessage example payload after the field list
   - B4: Edit Section 5 C2 — add exact section identifier for truth-11 §5
   - B5: Read truth-00 mapping table to verify rules/*.md assignment, then edit Batch 4 row accordingly
   - B6: Edit Section 6 Batch 0 — replace relative paths with absolute paths in mkdir block

3. **Fix all 6 HIGH gaps**:
   - H1: Add settings.json readiness note to Batch 2 critical notes
   - H2: Add exact `chmod +x` command to Batch 2 critical notes
   - H3: Add full filename format to Section 7 Step 1
   - H4: Add approval definition to Section 7 Steps 1–3
   - H5: Add timestamp generation method to Section 8
   - H6: Add ordering warning to Section 6 Batch 0 block

4. **Fix MEDIUM gaps (prioritized order)**:
   - M1 (highest priority): Add ADAPT/COPY/NEW procedure definitions to Section 6 preamble
   - M2: Add mkdir command to Batch 7 critical notes
   - M3: Add CLAUDE.md body text callout to C1
   - M6: Add post-code.sh guard removal to Batch 2 critical notes
   - M4, M5, M7: Lower priority but add if line count allows

5. **Verify final line count**: Run `wc -l` on the guidelines file. Target: ≤300 lines. If over 300, consolidate duplicated information (the directory tree is the largest section — consider whether it can be truncated with a reference to truth-00 instead).

6. **Do one final pass**: Read the complete guidelines from top to bottom looking for any remaining point where the orchestrator would have to guess, infer, or decide something not covered by truth files or corrections.

7. **Only after all gaps fixed**: Spawn the Stage 4.2 orchestrator per Section 7 below.

---

## 7. HOW TO SPAWN THE STAGE 4.2 ORCHESTRATOR (exact procedure)

### Step 1 — Verify environment variable

```bash
echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS
```

Must output `1`. If not set, run:
```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```
TeamCreate will not work without this.

### Step 2 — Create the team

```
TeamCreate(
  team_name="siopv-stage42-implementation",
  description="Stage 4.2: Implement siopv/.claude/ configuration files per 12 truth files",
  agent_type="orchestrator"
)
```

### Step 3 — Spawn the orchestrator into the team

```
Agent(
  description="Orchestrate Stage 4.2 implementation of siopv/.claude/ files",
  prompt="Read and follow the orchestrator guidelines at: /Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.2-implementation/stage4.2-orchestrator-guidelines.md — read the complete file before taking any action. Then read all 16 input files listed in Section 2. Then write the execution plan and send it via SendMessage.",
  subagent_type="general-purpose",
  team_name="siopv-stage42-implementation",
  name="orchestrator",
  model="claude-opus-4-6",
  mode="acceptEdits",
  run_in_background=True
)
```

### Step 4 — Name yourself "claude-main"

In the TeamCreate flow, name yourself `claude-main` so the orchestrator can send callbacks:
```
SendMessage(to="claude-main", message="...")
```

### Step 5 — Wait

Do NOT spawn any other agents. Do NOT read any truth files. Do NOT write any implementation files. The orchestrator handles everything from here. Your only role after spawning is:
- Review execution plan when orchestrator sends it via SendMessage
- Type "approved" (or another explicit approval phrase) to ungate each batch
- For the Batch 7 checkpoint: read the full list of `~/.claude/` changes carefully before approving

---

## 8. ALL DECISIONS — CLOSED (do not re-open)

### 5 Conflict Resolutions

| # | Severity | Conflict | Resolution |
|---|----------|----------|------------|
| 1 | CRITICAL | `hex-arch-remediator` placement: Wave 3 vs. standalone on-demand | In `/verify` Wave 3. truth-06 authoritative. truth-03 "on-demand" listing superseded. Human decision, mandatory. |
| 2 | HIGH | `async: true` on pre-compact.sh hook registration | Add at outer entry object level of PreCompact block in settings.json. Already applied to truth-01. |
| 3 | HIGH | Compact Instructions block in CLAUDE.md | Use truth-11 §5 exactly. truth-02 block is now a redirect placeholder — do NOT copy truth-02's block. |
| 4 | MEDIUM | `siopv-remediate` SKILL.md references `03-human-checkpoints.md` (does not exist in siopv) | Replace with inline reference to CLAUDE.md rules 9–10. Already applied to truth-06. |
| 5 | LOW | Agent count: 14 or 15 | 14 total: Wave 1=3, Wave 2=2, Wave 3=9. Any "15" in truth files is stale. Already corrected in truth-00, truth-10. |

### 5 Pre-Resolved Discrepancies

| Discrepancy | Resolution |
|-------------|------------|
| `settings.local.json`: truth-00 says ADAPT, file was deleted | NEW — create from scratch per truth-01 |
| `post-code.sh`: truth-00 says COPY | ADAPT — remove META_PROJECT_DIR guard; truth-01 wins |
| `.build/` directories: absent from truth-00 batches | Create in Batch 0 (15 mkdir commands run by orchestrator) |
| truth-10 agent count was 15 | Corrected to 14 in truth-10 — no further action |
| truth-00 action tags vs. truth-files | Truth-files win; truth-00 action tags superseded where they conflict |

### 13 Corrections (C1–C13)

| Code | Decision |
|------|----------|
| C1 | Write `14` everywhere for agent count (not 15); Wave 3=9; arithmetic 3+2+9=14 |
| C2 | CLAUDE.md Compact Instructions block: copy verbatim from truth-11 §5, not truth-02 |
| C3 | `permissionMode: plan` for exactly 7 agents: dependency-scanner, smoke-test-runner, best-practices-enforcer, security-auditor, hallucination-detector, code-reviewer, test-generator. All others: `acceptEdits`. |
| C4 | `memory: project` is universal — replace any `memory: true` in all 15 ADAPT agents |
| C5 | hallucination-detector: remove duplicate `fname=` parameter (Python syntax error in fpdf2 example) |
| C6 | verify/SKILL.md: delete any line referencing `04-agents.md` or `agent-tool-schemas.md` (do not exist in siopv) |
| C7 | truth-10 hook path check: PASS when hook bodies contain hardcoded `/Users/bruno/siopv/` paths. Do NOT expect `${CLAUDE_PROJECT_DIR}`. |
| C8 | MEMORY.md actual line count is 216 (not 217); remove lines 200–216 using string matching, not line numbers |
| C9 | MEMORY.md trim target: ≤185 lines (truth-10 wins over truth-00's ≤200) |
| C10 | Batch 7 missing 4 files: run `mkdir -p ~/.claude/projects/-Users-bruno-siopv/memory/` then create siopv-stage-results.md, siopv-architecture.md, siopv-violations.md, siopv-phase7-8-context.md (content from truth-07) |
| C11 | siopv-hooks-stage4.md: use truth-08 version (not truth-07) |
| C12 | SIOPV briefing.md: content from truth-11 §4 only; do NOT copy from `/Users/bruno/sec-llm-workbench/.claude/workflow/briefing.md` |
| C13 | File count sign-off: do NOT use `find .claude -type f | wc -l`; use per-item wiring checklist in truth-10 only |

### 20 Architectural Decisions

1. Stage 4.2 scope is implementation only. No research, no new decisions.
2. REMEDIATION-HARDENING is NOT part of Stage 4.2. After Stage 4.2 completes, open a fresh SIOPV session.
3. settings.local.json is NEW (file was deleted before Stage 4.2).
4. post-code.sh action is ADAPT (remove META_PROJECT_DIR guard).
5. `.build/` directory creation belongs in Batch 0 (orchestrator runs directly, no worker).
6. All hook `.sh` files must be `chmod +x` immediately after creation (Batch 2).
7. Source reading for ADAPT/COPY: agent reads source from `/Users/bruno/sec-llm-workbench/.claude/` first.
8. Execution plan gate is mandatory: orchestrator writes plan → SendMessage → waits for "approved" → starts Batch 1.
9. Human checkpoint after EVERY batch: orchestrator sends batch summary, waits for explicit approval.
10. Mandatory dedicated checkpoint before Batch 7: orchestrator lists ALL `~/.claude/` changes with absolute paths and action. Waits for explicit human approval.
11. No-improvisation rule applies to orchestrator and all agents. Any ambiguity → STOP → SendMessage → wait.
12. Old briefing.md "copy from meta-project" instruction is superseded. truth-11 takes priority.
13. Orchestrator model = `claude-opus-4-6`; all workers = `claude-sonnet-4-6`. No exceptions.
14. Spawning architecture: orchestrator sends specs via SendMessage to team lead. Team lead spawns workers. Orchestrator never calls Agent tool directly.
15. All workers use `mode: acceptEdits`. Never `bypassPermissions`.
16. Agent count is 14 (Wave 1:3, Wave 2:2, Wave 3:9). Any "15" in truth files is stale.
17. MEMORY.md trim target: ≤185 lines (C9). Remove using string matching, not line numbers.
18. 4 SIOPV memory topic files must be created in Batch 7 (C10). Directory created first.
19. truth-10 per-item checklist is the sole sign-off mechanism — no `find` command.
20. Worker agents read ONLY their assigned truth file (context efficiency). Orchestrator reads all 16 files.

---

## 9. KEY FILE PATHS (quick reference)

### Stage 4.2 Pre-Work Files

| File | Purpose |
|------|---------|
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.2-implementation/stage4.2-orchestrator-guidelines.md` | PRIMARY orchestrator instruction document (284 lines, has 29 gaps to fix) |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.2-implementation/stage4.2-precompact-handoff-v2.md` | This file — authoritative handoff |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.2-implementation/stage4.2-naming-and-output-conventions.md` | Naming convention + write scope + batch slugs |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.2-implementation/stage4.2-final-report-spec.md` | Final report structure (9 mandatory sections) |

### Truth Files (12 total)

| File | Role |
|------|------|
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/truth-00-directory-structure.md` | Backbone: directory tree, batch order, 41-file inventory |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/truth-01-settings-and-hooks.md` | settings.json + 7 hook specs (async:true already applied) |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/truth-02-claude-md.md` | CLAUDE.md content (Compact Instructions section = redirect to truth-11) |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/truth-03-agent-definitions.md` | 18 agent definitions (15 ADAPT + 3 NEW) |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/truth-04-rules.md` | rules/ directory |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/truth-05-docs.md` | docs/ directory + siopv-phase7-8-context.md content |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/truth-06-skills.md` | skills/ + /verify (siopv-remediate ref already fixed) |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/truth-07-memory.md` | SIOPV memory topic file content |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/truth-08-user-level.md` | ~/.claude/ changes (9 items) + siopv-hooks-stage4.md authoritative source |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/truth-09-cross-file-wiring.md` | Backbone: dependency graph, conflict registry |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/truth-10-verification-checklist.md` | Acceptance checklist (corrected: 14 agents, 18 Batch 6 files) |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/truth-11-compaction-proof-session-continuity.md` | Hook script bodies + SIOPV briefing.md content (§4) + Compact Instructions block (§5) |

### Supporting Files

| File | Purpose |
|------|---------|
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/team-management-best-practices.md` | Orchestration behavior rules (Section 9: no-improvisation rule) |
| `/Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round4-truth-document/compaction-proof-handoff-best-practices.md` | Context preservation patterns |

### Implementation Targets

| Path | What goes there |
|------|----------------|
| `/Users/bruno/siopv/.claude/` | All 41 project-level Claude config files |
| `/Users/bruno/siopv/.build/` | 4 build directories (checkpoints/pending, checkpoints/daily, logs/agents, logs/sessions) |
| `/Users/bruno/.claude/` | User-level changes (Batch 7 only — 9 items) |
| `/Users/bruno/.claude/projects/-Users-bruno-siopv/memory/` | 4 SIOPV memory topic files (C10) |

### Source Files

| Path | Purpose |
|------|---------|
| `/Users/bruno/sec-llm-workbench/.claude/` | Source for all COPY and ADAPT operations |

---

## 10. SIOPV PROJECT CONTEXT (for new sessions)

### What SIOPV is

SIOPV is a security vulnerability processing pipeline built with hexagonal architecture. It processes Trivy vulnerability reports through phases: ingestion → enrichment (CRAG/RAG) → ML classification (XGBoost) → orchestration (LangGraph) → authorization (OpenFGA) → privacy (DLP/Presidio). The project is at Phase 7 (Human-in-the-Loop with Streamlit) — pending.

### Where the project is

Main project: `/Users/bruno/siopv/`
Audit pre-Phase 7 work: `/Users/bruno/siopv/AuditPrePhase7-11mar26/`
Stages completed: stage1 (discovery), stage2 (hexagonal audit), stage3 (SOTA research), stage3.5 (aggregation), stage4.1 (truth files written)
Stage in progress: stage4.2 (implementation of `.claude/` config files)

### What Stage 4.2 is implementing

Stage 4.2 creates 41 files in `/Users/bruno/siopv/.claude/` (agents, hooks, rules, docs, skills, workflow) and 9 items in `/Users/bruno/.claude/` (user-level configuration). These files configure Claude Code to operate efficiently on the SIOPV project with verified agents, skill shortcuts, memory continuity, and a verification pipeline.

### What comes after Stage 4.2

After Stage 4.2 completes and passes Batch 8 verification:
1. Open a fresh SIOPV session at `/Users/bruno/siopv/`
2. First task: read all directories in `/Users/bruno/siopv/AuditPrePhase7-11mar26/` (stage1 through stage4.2)
3. Produce REMEDIATION-HARDENING orchestrator guidelines
4. REMEDIATION-HARDENING addresses the 9 MISSING items and 21 PARTIAL items found in Stage 1 (Phases 0–6 gaps before Phase 7 can begin)
5. After REMEDIATION-HARDENING: implement Phase 7 (Streamlit human-in-the-loop interface)

---

*End of Stage 4.2 Pre-Work Handoff v2*
*Created: 2026-03-13 | Source: stage4.2-session-handoff-DRAFT.md + gap analysis (29 gaps) + stage4.2-orchestrator-guidelines.md (284 lines) + stage4.2-precompact-handoff.md*
