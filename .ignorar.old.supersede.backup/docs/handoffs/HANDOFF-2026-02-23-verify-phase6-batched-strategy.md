# HANDOFF: Batched /verify Strategy for Phase 6 (DLP) — Context-Safe Execution with Incremental Append

**Date:** 2026-02-23
**Purpose:** Complete strategy for running the mandatory 5-agent `/verify` process for Phase 6 (SIOPV project), using a stateless batch architecture designed to prevent agent context overflow. Any engineer or AI agent picking this up must follow this plan exactly as written — no skipping rules, no improvisation.

**Scope:** Phase 6 (DLP — Presidio + Haiku dual-layer). Code is already committed and pushed. No `/verify` was run before commit. This handoff exists to correct that.

**Project path:** `~/siopv/`
**Reports path:** `~/siopv/.ignorar/production-reports/`
**Thresholds reference:** `~/sec-llm-workbench/.claude/rules/verification-thresholds.md`
**Meta-project rules:** `~/sec-llm-workbench/.claude/` (workflow/, rules/, docs/)

---

## Why This Handoff Exists

Phase 6 was committed without running `/verify` — a violation of project rules. A previous attempt used parallel agents without batching; the test-generator ran out of context and compacted. This handoff defines a safer architecture. Before starting Phase 7, Phase 6 must be fully verified and reports saved to disk.

---

## Core Principles

1. **Stateless batch pattern** — each agent spawn handles exactly one batch. No agent carries state from another spawn. Filesystem is the only shared state.
2. **Filesystem as shared memory** — prompts are minimal pointers (paths + section names), never data carriers. All large data lives on disk.
3. **Incremental append** — each agent type has exactly ONE report file for the entire run. Every spawn of the same agent type appends its batch section to that same file. No merge step needed.
4. **Fixed timestamp** — the Operator computes one timestamp (`FIXED_TIMESTAMP`) at startup and embeds it in every manifest section. This ensures all spawns of the same agent write to the same filename.
5. **Sequential-per-agent, parallel-across-agents** — batches for a given agent run one at a time (spawn → done → next spawn). Different agent types run in parallel with each other.
6. **Context preservation for everyone** — the main session, the operator, and every verification agent must protect their context window. No large data embedded in prompts.
7. **If something goes wrong, ask the human. No autonomous recovery. Ever.**

---

## Execution Model: TeamCreate + Operator

### Main Session Role (lean — does almost nothing)

The main session:
1. Creates the team using `TeamCreate`
2. Spawns the `operator` agent with a complete prompt (see Operator Prompt below)
3. Waits silently — no verbatim requests, no check-ins, no autonomous actions
4. At the very end, reads **only the Summary section** of each agent's report file and presents the combined verdict to the human

The main session does NOT read files, does NOT define batch manifests, does NOT spawn verification agents directly.

### Operator Agent Role

The operator is the coordination agent inside the team. It:

1. Reads this handoff file fully and loyally — no skipping rules
2. Reads all meta-project rules from `~/sec-llm-workbench/.claude/` (workflow/, rules/, docs/)
3. Reads all Phase 6 source and test files in `~/siopv/src/` and `~/siopv/tests/` to determine what exists
4. Counts lines per file to determine appropriate batch sizes per agent
5. Computes `FIXED_TIMESTAMP` once: `$(date +%Y-%m-%d-%H%M%S)` — used in ALL report paths
6. **Writes the batch manifest to disk** (see Batch Manifest section below) before spawning any agent
7. Spawns Wave 1 agents (first batch of each agent type in parallel)
8. As each agent reports DONE, spawns the next batch for that agent — agents within a wave progress independently
9. When all Wave 1 agent types have completed all their batches, spawns Wave 2 agents (same pattern)
10. When all Wave 2 agent types have completed all their batches, spawns Static Checks Agent
11. When static checks report is on disk, signals the main session with paths to all 5 agent report files

The operator MUST NOT:
- Embed file lists in agent prompts (use manifest file instead)
- Read report files or batch sections into its own context
- Make autonomous decisions when something goes wrong — ask the human
- Skip any rule from this handoff or the meta-project
- Spawn the next batch for an agent before the previous batch reports DONE

---

## Batch Manifest File

### Location

```
~/siopv/.ignorar/production-reports/phase-6-batch-manifest.md
```

### Purpose

The manifest is the single source of truth for all batch assignments. The operator writes it once before spawning any agent. The first line of the manifest is the `FIXED_TIMESTAMP`. Each agent receives in its prompt: the manifest path + the exact section header to read. The agent reads only that section and ignores everything else.

### Manifest Header (first thing in the file)

```
FIXED_TIMESTAMP: 2026-02-23-143022
```

### Section Format

Each section is labeled with a unique, unambiguous header containing agent name and batch identifier:

```
## [best-practices-enforcer] [batch-1-of-3]
## [best-practices-enforcer] [batch-2-of-3]
## [best-practices-enforcer] [batch-3-of-3]
## [security-auditor] [batch-1-of-2]
## [security-auditor] [batch-2-of-2]
## [hallucination-detector] [batch-httpx]
## [hallucination-detector] [batch-pydantic]
## [code-reviewer] [batch-1-of-3]
## [code-reviewer] [batch-2-of-3]
## [code-reviewer] [batch-3-of-3]
## [test-generator] [batch-module-1]
## [test-generator] [batch-module-2]
(etc.)
```

### Section Content

Each section must contain:
- The explicit list of **absolute file paths** to process (nothing to infer)
- The **shared report path** — same file for every batch of this agent type (uses `FIXED_TIMESTAMP`)
- Whether this is the **last batch** (`IS_LAST_BATCH: true/false`) — the last batch also appends the Summary section
- For test-generator: the exact `pytest` command scoped to that module

Example section:

```markdown
## [security-auditor] [batch-1-of-2]

**Files to analyze:**
- /Users/bruno/siopv/src/siopv/dlp/presidio_analyzer.py
- /Users/bruno/siopv/src/siopv/dlp/haiku_classifier.py
- /Users/bruno/siopv/src/siopv/dlp/pipeline.py

**Append findings to:**
/Users/bruno/siopv/.ignorar/production-reports/security-auditor/phase-6/2026-02-23-143022-phase-6-security-auditor.md

**IS_LAST_BATCH:** false
```

```markdown
## [security-auditor] [batch-2-of-2]

**Files to analyze:**
- /Users/bruno/siopv/src/siopv/dlp/router.py
- /Users/bruno/siopv/src/siopv/dlp/models.py

**Append findings to:**
/Users/bruno/siopv/.ignorar/production-reports/security-auditor/phase-6/2026-02-23-143022-phase-6-security-auditor.md

**IS_LAST_BATCH:** true
```

---

## Report File Structure (Incremental Append Format)

Each agent type produces exactly one report file. The file is built incrementally — each spawn appends one section. The last batch also appends the Summary section.

### File path pattern

```
~/siopv/.ignorar/production-reports/{agent-name}/phase-6/{FIXED_TIMESTAMP}-phase-6-{agent-name}.md
```

### File structure (after all batches complete)

```markdown
# {agent-name} — Phase 6 Verification Report
Generated: {FIXED_TIMESTAMP}
Project: ~/siopv/

---

## Batch 1 of N — {batch description}

**Files analyzed:**
- /absolute/path/file1.py
- /absolute/path/file2.py

### Findings

[full findings for this batch]

### Batch 1 Status: PASS / FAIL

---

## Batch 2 of N — {batch description}

[same structure]

---

## Batch N of N — {batch description}

[same structure]

---

## Summary (All Batches)

| Severity | Count |
|----------|-------|
| CRITICAL | N     |
| HIGH     | N     |
| MEDIUM   | N     |
| LOW      | N     |

**Threshold applied:** [threshold from verification-thresholds.md]
**Overall Status: PASS / FAIL**
```

### Append mechanism

Each agent spawn uses bash heredoc append:

```bash
# First batch: create the file with document header
cat > /path/to/report.md << 'REPORT_HEADER'
# {agent-name} — Phase 6 Verification Report
Generated: {FIXED_TIMESTAMP}
Project: ~/siopv/

---
REPORT_HEADER

# Every batch (including first): append batch section
cat >> /path/to/report.md << 'BATCH_SECTION'
## Batch {B} of {T} — {description}

**Files analyzed:**
...

### Findings
...

### Batch {B} Status: PASS / FAIL

---
BATCH_SECTION

# Last batch only: also append Summary section
cat >> /path/to/report.md << 'SUMMARY_SECTION'
## Summary (All Batches)
...
SUMMARY_SECTION
```

**Rule:** The first spawn checks if the file exists before creating the header:
```bash
[ -f /path/to/report.md ] || cat > /path/to/report.md << 'EOF'
# header...
EOF
```

---

## Architecture Overview

```
Main session
│   TeamCreate → spawns Operator → waits silently
│   Receives ONE message from Operator with compact verdict → presents to human
│   Main session NEVER reads any file. Ever.
│
Operator
│   1. Reads handoff + meta-project rules + Phase 6 files
│   2. Computes FIXED_TIMESTAMP once
│   3. Writes batch manifest to disk (with FIXED_TIMESTAMP embedded)
│   4. Spawns first batch of Wave 1 agents (parallel across agent types)
│   5. As each agent reports DONE: spawns next batch for that agent type
│   6. When all Wave 1 agent types finish all batches → spawns Wave 2 (same pattern)
│   7. When all Wave 2 agent types finish all batches → spawns Static Checks Agent
│   8. When static checks report exists → spawns Final Report Agent
│   9. Receives compact verdict message from Final Report Agent
│  10. Relays that message verbatim to the main session → shuts down
│
├── WAVE 1 (3 agent types — batches sequential per type, parallel across types)
│   ├── best-practices-enforcer  batch-1 → [DONE] → batch-2 → [DONE] → batch-3 → [DONE]
│   ├── security-auditor         batch-1 → [DONE] → batch-2 → [DONE]
│   └── hallucination-detector   batch-httpx → [DONE] → batch-pydantic → [DONE]
│   Each agent type appends to its own single report file.
│   All 3 types progress independently (no synchronization within Wave 1).
│   Wave 1 completes when ALL 3 types have finished ALL their batches.
│
├── WAVE 2 (2 agent types — same pattern)
│   ├── code-reviewer    batch-1 → [DONE] → batch-2 → [DONE] → batch-3 → [DONE]
│   └── test-generator   batch-module-1 → [DONE] → batch-module-2 → [DONE]
│   Wave 2 completes when BOTH types have finished ALL their batches.
│
├── STATIC CHECKS AGENT (Haiku — spawned after Wave 2 completes)
│       Runs 4 bash commands in ~/siopv/:
│       - uv run ruff format src tests --check
│       - uv run ruff check src tests
│       - uv run mypy src
│       - uv run pytest tests/ -v
│       Saves stdout/stderr + exit codes to:
│       .ignorar/production-reports/static-checks/phase-6/{FIXED_TIMESTAMP}-phase-6-static-checks.md
│       Sends operator: "DONE: static checks — report saved to {path}"
│
└── FINAL REPORT AGENT (Haiku — spawned after static checks report exists)
        Reads ONLY the ## Summary section of each of the 5 agent report files (bash grep)
        Reads the static checks report
        Applies PASS/FAIL thresholds from verification-thresholds.md
        Composes a compact verdict (≤30 lines) — see Verdict Format below
        Sends the verdict as a MESSAGE to the operator
        Does NOT write any file. Does NOT read full report files.
        Shuts down after sending.
```

**Result: 5 report files (one per agent, built incrementally). Main session context used = 0.**

---

## Batch Sizing Rules

| Agent | Context Risk | Batch Size | Grouping Logic |
|---|---|---|---|
| best-practices-enforcer | Low | 4–5 files per batch | Group by module |
| security-auditor | Medium | 3–4 files per batch | Group by module |
| hallucination-detector | High | By library | All httpx usage in one batch, all Pydantic in another, etc. |
| code-reviewer | Medium | 3–4 files per batch | Group by module |
| test-generator | Highest | 1 module per batch | `pytest tests/test_X.py --cov=src/siopv/X/` scoped to that module only |

---

## Report Naming Convention

All reports saved under `~/siopv/.ignorar/production-reports/`.

```
# One report per agent type — all batches appended incrementally
{FIXED_TIMESTAMP}-phase-6-{agent-name}.md
  → saved in: .ignorar/production-reports/{agent-name}/phase-6/

# Static checks report
{FIXED_TIMESTAMP}-phase-6-static-checks.md
  → saved in: .ignorar/production-reports/static-checks/phase-6/
```

`FIXED_TIMESTAMP` format: `YYYY-MM-DD-HHmmss` (24-hour format, set once by the Operator at startup)

Example (5 agent reports + 1 static checks report = 6 files total):
```
2026-02-23-143022-phase-6-best-practices-enforcer.md
2026-02-23-143022-phase-6-security-auditor.md
2026-02-23-143022-phase-6-hallucination-detector.md
2026-02-23-143022-phase-6-code-reviewer.md
2026-02-23-143022-phase-6-test-generator.md
2026-02-23-143022-phase-6-static-checks.md
```

---

## Final Report Agent Prompt Template

```
You are the Final Report Agent for the SIOPV project — Phase 6 (DLP) verification.

Your ONLY job is to read the Summary section of each agent report, apply thresholds,
compose a compact verdict, and send it as a message to the operator. You do NOT write
any file. You do NOT read full reports.

Rules to follow:
- ~/sec-llm-workbench/.claude/rules/verification-thresholds.md

Extract Summary sections using bash (do NOT read full files):
  grep -A 30 "## Summary" {report_path}

Report paths (read FIXED_TIMESTAMP from manifest first line):
- ~/siopv/.ignorar/production-reports/best-practices-enforcer/phase-6/{FIXED_TIMESTAMP}-phase-6-best-practices-enforcer.md
- ~/siopv/.ignorar/production-reports/security-auditor/phase-6/{FIXED_TIMESTAMP}-phase-6-security-auditor.md
- ~/siopv/.ignorar/production-reports/hallucination-detector/phase-6/{FIXED_TIMESTAMP}-phase-6-hallucination-detector.md
- ~/siopv/.ignorar/production-reports/code-reviewer/phase-6/{FIXED_TIMESTAMP}-phase-6-code-reviewer.md
- ~/siopv/.ignorar/production-reports/test-generator/phase-6/{FIXED_TIMESTAMP}-phase-6-test-generator.md
- ~/siopv/.ignorar/production-reports/static-checks/phase-6/{FIXED_TIMESTAMP}-phase-6-static-checks.md

Manifest path (to read FIXED_TIMESTAMP):
~/siopv/.ignorar/production-reports/phase-6-batch-manifest.md

When done:
1. Compose the compact verdict using the Verdict Format below
2. Send it as a message to the operator (SendMessage — do NOT print it, SEND it)
3. Shut down immediately after sending.
```

### Verdict Format (≤30 lines — sent as a message, never written to a file)

```
PHASE 6 VERIFICATION — FINAL VERDICT

Agent Results:
| Agent                    | Status | Notes                        |
|--------------------------|--------|------------------------------|
| best-practices-enforcer  | PASS   | 0 violations                 |
| security-auditor         | PASS   | 0 CRITICAL/HIGH              |
| hallucination-detector   | PASS   | 0 hallucinations             |
| code-reviewer            | PASS   | Score: 9.2/10                |
| test-generator           | PASS   | Coverage: 84%                |

Static Checks:
| Check       | Status |
|-------------|--------|
| ruff format | PASS   |
| ruff check  | PASS   |
| mypy        | PASS   |
| pytest      | PASS   |

OVERALL: PASS ✓  (or FAIL — list which agents failed)

Report files:
- .ignorar/production-reports/best-practices-enforcer/phase-6/{FIXED_TIMESTAMP}-phase-6-best-practices-enforcer.md
- (etc.)
```

---

## Agent Prompt Template (each batch spawn)

Prompts must be minimal pointers — no file lists, no large data. The manifest file carries all that.

```
You are {agent-name} for the SIOPV project — Phase 6 (DLP) verification.

YOUR SCOPE: BATCH {B} of {T} ({batch-description}).

Rules to follow:
- ~/sec-llm-workbench/.claude/rules/verification-thresholds.md
- ~/sec-llm-workbench/.claude/workflow/04-agents.md
- ~/sec-llm-workbench/.claude/docs/errors-to-rules.md

Batch manifest file:
~/siopv/.ignorar/production-reports/phase-6-batch-manifest.md

Read ONLY the section with this exact header:
## [{agent-name}] [batch-{B}-of-{T}]
Ignore all other sections entirely.

That section contains:
- The exact files to analyze (analyze ONLY those files)
- The shared report file path to append to
- Whether this is the last batch (IS_LAST_BATCH)

When done, append your findings to the report file using the structure in the handoff:
1. If the report file does not exist yet: create it with the document header first
2. Append your batch section (## Batch {B} of {T}) using bash >> append
3. If IS_LAST_BATCH is true: also append the Summary section (aggregate all batches)
4. Send a message to the operator: "DONE: {agent-name} batch {B} of {T} — appended to {path}"
5. Wait for shutdown. Do not take any further action.

DO NOT analyze any files outside your manifest section.
DO NOT read other agents' report files.
DO NOT overwrite the report file — ALWAYS append (>>).
```

---

## Model Assignment (Cost-Effective — No Opus Anywhere)

| Role | Model | Rationale |
|---|---|---|
| Operator | Sonnet | Reads files, reasons about batching strategy, coordinates spawning |
| best-practices-enforcer | Haiku | Grep patterns + ruff — mechanical, no reasoning needed |
| security-auditor | Haiku | Grep patterns + bandit — mechanical pattern detection |
| hallucination-detector | Sonnet | Context7 queries + reasoning required |
| code-reviewer | Sonnet | Quality scoring + reasoning required |
| test-generator | Haiku | Run pytest + read coverage output — mechanical |
| Static Checks Agent | Haiku | 4 bash commands — no reasoning, no file reading, pure mechanical |
| Final Report Agent | Haiku | bash grep + threshold table lookup — mechanical, no reasoning needed |

**Opus is explicitly forbidden for all roles.**
**Default to Haiku. Use Sonnet only where reasoning or Context7 is required.**

---

## Operator Rules (strict)

### The operator MUST NOT:
- Embed file lists or large data in agent prompts
- Ask any agent for verbatim output, progress updates, or summaries mid-run
- Interpret agent idleness as a signal to act
- Read report files or batch sections into its own context
- Make autonomous decisions when something goes wrong
- Skip any rule from this handoff or the meta-project
- Spawn the next batch for an agent before the previous batch reports DONE

### The operator MUST:
- Read this handoff fully before doing anything else
- Read all relevant meta-project rules from `~/sec-llm-workbench/.claude/`
- Compute `FIXED_TIMESTAMP` once at startup before writing the manifest
- Write the batch manifest to disk before spawning any agent
- Spawn agents with minimal prompts (manifest path + section header + rules paths)
- Confirm report file existence by checking with `ls` — never reading content
- Ask the human if anything goes wrong — no autonomous recovery

### When something goes wrong:
The operator reports to the human:
- What was expected (agent name, batch number, expected output file path)
- What was observed (file missing, error message if visible)
- No suggested fix, no autonomous action

The human decides what to do next.

---

## Verification Thresholds (from verification-thresholds.md)

| Agent | PASS | FAIL | Blocking |
|---|---|---|---|
| best-practices-enforcer | 0 violations | Any violation | Yes |
| security-auditor | 0 CRITICAL/HIGH | Any CRITICAL/HIGH | Yes |
| security-auditor (MEDIUM) | Warning | — | No |
| hallucination-detector | 0 hallucinations | Any hallucination | Yes |
| code-reviewer | Score ≥ 9.0/10 | Score < 9.0/10 | Yes |
| test-generator | All tests pass + coverage ≥ 80% | Any failure OR coverage < 80% | Yes |
| ruff check (errors) | 0 errors | Any error | Yes |
| ruff check (warnings) | 0 warnings | Any warning | Yes |
| ruff format | No changes needed | Changes required | Yes |
| mypy | 0 errors | Any error | Yes |

---

## Additional Static Checks (delegated to Static Checks Agent after Wave 2 completes)

The operator spawns a dedicated **Haiku Static Checks Agent** with a minimal prompt: run these 4 commands in `~/siopv/`, save all stdout/stderr and exit codes to the path below, then report done.

```bash
uv run ruff format src tests --check
uv run ruff check src tests
uv run mypy src
uv run pytest tests/ -v
```

**Report saved to:** `.ignorar/production-reports/static-checks/phase-6/{FIXED_TIMESTAMP}-phase-6-static-checks.md`

The operator confirms completion by checking file existence only (`ls`). It does NOT read the report content.

---

## Human Checkpoint

After the Final Report Agent sends its verdict message to the Operator:

1. Operator relays the compact verdict message **verbatim** to the main session (SendMessage — no file reading, no summarizing)
2. Main session receives the message and **displays it directly to the human** — no file reads, no context growth beyond the message itself
3. **Human reviews the verdict and approves before any further action**
4. If FAIL: human decides what corrections to make — operator does not decide
5. If PASS: human authorizes proceeding to Phase 7

**The main session reads zero files at any point in this process.**

---

## Before Starting — Pre-flight Checklist (Operator executes this)

- [ ] Read this handoff fully
- [ ] Read all meta-project rules from `~/sec-llm-workbench/.claude/`
- [ ] Identify all Phase 6 source files in `~/siopv/src/`
- [ ] Identify all Phase 6 test files in `~/siopv/tests/`
- [ ] Count lines per file to determine batch sizes
- [ ] Compute `FIXED_TIMESTAMP`: `$(date +%Y-%m-%d-%H%M%S)`
- [ ] Define batch assignments for all 5 agents
- [ ] Write batch manifest to `~/siopv/.ignorar/production-reports/phase-6-batch-manifest.md` (first line: `FIXED_TIMESTAMP: {value}`)
- [ ] Confirm `.ignorar/production-reports/` directory exists and is writable
- [ ] Confirm all agent report subdirectories exist (create if missing):
  - `.ignorar/production-reports/best-practices-enforcer/phase-6/`
  - `.ignorar/production-reports/security-auditor/phase-6/`
  - `.ignorar/production-reports/hallucination-detector/phase-6/`
  - `.ignorar/production-reports/code-reviewer/phase-6/`
  - `.ignorar/production-reports/test-generator/phase-6/`
  - `.ignorar/production-reports/static-checks/phase-6/`
- [ ] Only then: spawn first batch of Wave 1 agents
