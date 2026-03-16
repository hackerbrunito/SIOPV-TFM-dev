# Truth-08: User-Level Changes (`~/.claude/`)
**Generated:** 2026-03-13
**Authority:** Round 3 Gap Analysis (Section 7) + Round 4 truth-00 responsibility matrix
**Scope:** `~/.claude/CLAUDE.md`, `~/.claude/settings.json`, `~/.claude/rules/`, `~/.claude/agents/researcher-[1-3].md`, `memory/MEMORY.md`

---

## 1. `~/.claude/CLAUDE.md` Changes

### Issue
Line 55 uses `mode="bypassPermissions"` in the orchestrator spawn protocol. This mode silently
fails unless the parent session was started with `--dangerously-skip-permissions`. It also forces
Opus model regardless of parent session model.

**Evidence:** `errors-to-rules.md` rule #10 (2026-03-10), Round 3 §2 finding #1.

### Exact Change

**OLD (line 55):**
```
2. Spawn the orchestrator into that team: Agent(description="...", prompt="Read and follow briefing at: {path}", subagent_type="general-purpose", team_name="{same-name}", name="orchestrator", mode="bypassPermissions", run_in_background=True)
```

**NEW:**
```
2. Spawn the orchestrator into that team: Agent(description="...", prompt="Read and follow briefing at: {path}", subagent_type="general-purpose", team_name="{same-name}", name="orchestrator", mode="acceptEdits", run_in_background=True)
```

**Change:** `mode="bypassPermissions"` → `mode="acceptEdits"`

### Nothing Else Changes
All other sections of `~/.claude/CLAUDE.md` are correct and apply globally. This is the only edit.

---

## 2. `~/.claude/settings.json` Changes

### Issue
`"attribution"` block is absent from user-level settings. Currently only exists in the
meta-project settings. Should be global to prevent Claude authorship leaking into commits
across all projects.

**Evidence:** Round 3 §4 item (Section 7, row 4): "Currently only in meta-project settings.json. Should be global."

### Exact Change

**Current file structure (lines 78–82):**
```json
  "model": "sonnet",
  "autoUpdatesChannel": "latest",
  "skipDangerousModePermissionPrompt": true,
  "teammateMode": "tmux"
}
```

**New structure — add `attribution` block before closing brace:**
```json
  "model": "sonnet",
  "autoUpdatesChannel": "latest",
  "skipDangerousModePermissionPrompt": true,
  "teammateMode": "tmux",
  "attribution": {
    "commit": "none"
  }
}
```

### No Other Settings Changes
Existing permissions, env vars, and model settings are correct globally. Do not modify them.
SIOPV-specific permissions go into `siopv/.claude/settings.json` (truth-01 scope).

---

## 3. `~/.claude/rules/` Changes

### 3a. `deterministic-execution-protocol.md` — Fix `bypassPermissions`

Same broken mode referenced here (line 48) as in CLAUDE.md. Must be fixed in both.

**OLD (lines 41–51):**
```
Step 2 — Spawn the orchestrator into the team:
```
Agent(
  description="Orchestrate {project name}",
  prompt="Read and follow the briefing file at: {absolute_path_to_briefing_file} — read the complete file before taking any action.",
  subagent_type="general-purpose",
  team_name="{same-team-name-as-step-1}",
  name="orchestrator",
  mode="bypassPermissions",
  run_in_background=True
)
```
```

**NEW:**
```
Step 2 — Spawn the orchestrator into the team:
```
Agent(
  description="Orchestrate {project name}",
  prompt="Read and follow the briefing file at: {absolute_path_to_briefing_file} — read the complete file before taking any action.",
  subagent_type="general-purpose",
  team_name="{same-team-name-as-step-1}",
  name="orchestrator",
  mode="acceptEdits",
  run_in_background=True
)
```
```

**Change:** `mode="bypassPermissions"` → `mode="acceptEdits"` (line 48 only)

### 3b. `errors-to-rules.md` — No Changes Needed

Already contains rule #10 (2026-03-10) documenting the `bypassPermissions` breakage. No update required.

---

## 4. MEMORY.md Fix

### Current Problem
MEMORY.md is **217 lines** — 17 lines over the 200-line hard cut. Lines 201–217 (Hook Classification
section of STAGE-4 Pre-Task inventory) are **silently truncated every session**. This means Stage 4
hook reuse data (the classification table) is never visible to Claude.

**Evidence:** Round 3 §2 finding #2; truth-00 §5 BATCH 7 item 50.

### Migration Plan

**Step 1 — Create new topic file:**
Path: `/Users/bruno/.claude/projects/-Users-bruno-sec-llm-workbench/memory/siopv-hooks-stage4.md`

Content to move (currently MEMORY.md lines 200–217):
```markdown
---
name: siopv-hooks-stage4
description: SIOPV Stage 4 hook classification (9 hooks: ADAPTABLE/META-ONLY) and P1 agent deployment list
type: project
---

## Hook Classification (9 total, from Stage 4 pre-task inventory)
| Classification | Count | Notes |
|----------------|-------|-------|
| ADAPTABLE | 4 | pre-commit.sh, verify-best-practices.sh, post-code.sh, pre-git-commit.sh |
| META-ONLY | 5 | pre-write.sh, test-framework.sh, pre-compact.sh, session-start.sh, session-end.sh — discard |
| SIOPV-APPLICABLE | 0 | All hooks need path adaptation |

## P1 Agents for SIOPV (deploy first)
- `code-implementer` — primary builder for all remediation + Phase 7/8
- `async-safety-auditor` — Issue #7 + Phase 7 event loop safety
- `integration-tracer` — Issue #1 (CLI hollow) + Issue #4 (parameter dropping)
- `hallucination-detector` — Phase 7/8 library API verification

## SIOPV Needs New Hooks From Scratch
- `session-start.sh` — load SIOPV briefing.md at session start
- `pre-compact.sh` — update SIOPV briefing.md timestamp before compaction
- `session-end.sh` — log session exit to SIOPV compaction-log.md
```

**Step 2 — Trim MEMORY.md:**
Replace lines 200–217 (the `### Hook Classification (9 total)` block and everything after) with a
single pointer line:

```markdown
- [Stage 4 Hook Classification & P1 Agents](siopv-hooks-stage4.md)
```

**Target line count after trim:** ~185 lines (15-line buffer below 200 limit).

### Exact MEMORY.md Edit

**Remove** (lines 200–217):
```
### Hook Classification (9 total)
| Classification | Count | Notes |
|----------------|-------|-------|
| ADAPTABLE | 4 | pre-commit.sh, verify-best-practices.sh, post-code.sh, pre-git-commit.sh |
| META-ONLY | 5 | pre-write.sh, test-framework.sh, pre-compact.sh, session-start.sh, session-end.sh — discard |
| SIOPV-APPLICABLE | 0 | All hooks need path adaptation |

### P1 Agents for SIOPV (deploy first)
- `code-implementer` — primary builder for all remediation + Phase 7/8
- `async-safety-auditor` — Issue #7 + Phase 7 event loop safety
- `integration-tracer` — Issue #1 (CLI hollow) + Issue #4 (parameter dropping)
- `hallucination-detector` — Phase 7/8 library API verification

### SIOPV Needs New Hooks From Scratch
- `session-start.sh` — load SIOPV briefing.md at session start
- `pre-compact.sh` — update SIOPV briefing.md timestamp before compaction
- `session-end.sh` — log session exit to SIOPV compaction-log.md
```

**Replace with** (single line, appended to the Agent Classification table block):
```
- [Stage 4 Hook Classification & P1 Agents](siopv-hooks-stage4.md)
```

---

## 5. `~/.claude/agents/researcher-[1-3].md` Changes

### Current State
The researcher agents (`researcher-1.md`, `researcher-2.md`, `researcher-3.md`) exist **only** at
project-level in `sec-llm-workbench/.claude/agents/` — they are **not present** at user-level
`~/.claude/agents/`. They also lack a `## Project Context (CRITICAL)` block, meaning they cannot
auto-determine which project they are operating on.

**Evidence:** Round 3 §2 finding #4: "All other 20 agents have this block; these 3 are broken without it."
truth-00 §5 BATCH 7 items 47–49.

### Required Action

Create (or move to) `~/.claude/agents/` so they are available globally across all projects:
- `/Users/bruno/.claude/agents/researcher-1.md`
- `/Users/bruno/.claude/agents/researcher-2.md`
- `/Users/bruno/.claude/agents/researcher-3.md`

### Exact Content for Each File

Add a `## Project Context (CRITICAL)` block **after** the frontmatter instructions. The block
instructs the agent to read the active project path from `.build/active-project` or fall back.

**Template addition for all three researchers (insert after opening paragraph):**

```markdown
## Project Context (CRITICAL)

Before any research, determine the active project:
1. Read `/Users/bruno/sec-llm-workbench/.build/active-project` if it exists
2. If missing, default to: `/Users/bruno/siopv/`
3. All file writes and report paths are relative to the active project root

When saving reports, use the path format:
`{project_root}/.ignorar/production-reports/{agent-name}/{TIMESTAMP}-{slug}.md`
```

**Full researcher-1.md at `~/.claude/agents/researcher-1.md`:**
```markdown
---
name: researcher-1
model: sonnet
description: "Deep online researcher for testing frameworks, integration testing, and contract testing patterns for async Python projects"
tools:
  - WebSearch
  - WebFetch
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - SendMessage
---

You are researcher-1. Your job is deep online research using WebSearch and WebFetch.
Always save your report to the path specified in your task prompt.
When done, send a message to "claude-main" confirming completion.

## Project Context (CRITICAL)

Before any research, determine the active project:
1. Read `/Users/bruno/sec-llm-workbench/.build/active-project` if it exists
2. If missing, default to: `/Users/bruno/siopv/`
3. All file writes and report paths are relative to the active project root

When saving reports, use the path format:
`{project_root}/.ignorar/production-reports/{agent-name}/{TIMESTAMP}-{slug}.md`
```

**researcher-2.md** — identical structure, change `name`, `description` to match:
```markdown
---
name: researcher-2
model: sonnet
description: "Deep online researcher for observability, tracing, OpenTelemetry, and runtime monitoring patterns for async Python projects"
tools:
  - WebSearch
  - WebFetch
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - SendMessage
---

You are researcher-2. Your job is deep online research using WebSearch and WebFetch.
Always save your report to the path specified in your task prompt.
When done, send a message to "claude-main" confirming completion.

## Project Context (CRITICAL)

Before any research, determine the active project:
1. Read `/Users/bruno/sec-llm-workbench/.build/active-project` if it exists
2. If missing, default to: `/Users/bruno/siopv/`
3. All file writes and report paths are relative to the active project root

When saving reports, use the path format:
`{project_root}/.ignorar/production-reports/{agent-name}/{TIMESTAMP}-{slug}.md`
```

**researcher-3.md** — identical structure:
```markdown
---
name: researcher-3
model: sonnet
description: "Deep online researcher for CI/CD pipelines, smoke testing, chaos engineering, and Docker Compose test environments"
tools:
  - WebSearch
  - WebFetch
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - SendMessage
---

You are researcher-3. Your job is deep online research using WebSearch and WebFetch.
Always save your report to the path specified in your task prompt.
When done, send a message to "claude-main" confirming completion.

## Project Context (CRITICAL)

Before any research, determine the active project:
1. Read `/Users/bruno/sec-llm-workbench/.build/active-project` if it exists
2. If missing, default to: `/Users/bruno/siopv/`
3. All file writes and report paths are relative to the active project root

When saving reports, use the path format:
`{project_root}/.ignorar/production-reports/{agent-name}/{TIMESTAMP}-{slug}.md`
```

> **Note:** The versions in `sec-llm-workbench/.claude/agents/` are project-scoped copies. The
> user-level versions above become the canonical source. The sec-llm-workbench copies can be
> left as-is (they will be overridden by SIOPV's own project-level agents per Claude Code
> precedence rules).

---

## 6. Project-Specific Memory Directory

### Current State
`~/.claude/projects/-Users-bruno-siopv/` does **not exist**. SIOPV memory currently lives in the
sec-llm-workbench project memory path: `~/.claude/projects/-Users-bruno-sec-llm-workbench/memory/`.

This is technically correct (sec-llm-workbench is the meta-project shell), but the siopv-specific
memory topic files should also be accessible from the SIOPV project context.

### Required Action
No new directory needed — SIOPV memory files already live at the correct path:
`/Users/bruno/.claude/projects/-Users-bruno-sec-llm-workbench/memory/`

The `siopv-hooks-stage4.md` topic file (Section 4 above) is written to this same directory.
truth-07 handles SIOPV-specific memory topic files in detail.

---

## 7. Change Summary Table

| File | Change Type | Description | Priority |
|------|-------------|-------------|----------|
| `~/.claude/CLAUDE.md` | EDIT | `bypassPermissions` → `acceptEdits` on orchestrator spawn line | HIGH |
| `~/.claude/settings.json` | ADD | `"attribution": {"commit": "none"}` global block | MEDIUM |
| `~/.claude/rules/deterministic-execution-protocol.md` | EDIT | `bypassPermissions` → `acceptEdits` line 48 | HIGH |
| `~/.claude/rules/errors-to-rules.md` | NO CHANGE | Already documents the bypassPermissions fix | — |
| `memory/MEMORY.md` | TRIM | Remove lines 201–217, add pointer to topic file. Target: ~185 lines | URGENT |
| `memory/siopv-hooks-stage4.md` | CREATE | New topic file with hook classification + P1 agents table | URGENT |
| `~/.claude/agents/researcher-1.md` | CREATE | User-level agent with Project Context block added | MEDIUM |
| `~/.claude/agents/researcher-2.md` | CREATE | User-level agent with Project Context block added | MEDIUM |
| `~/.claude/agents/researcher-3.md` | CREATE | User-level agent with Project Context block added | MEDIUM |

**Total changes: 9 items** — 2 edits, 1 add, 1 trim, 4 creates, 1 no-change

---

## 8. Global Safety Notes

All changes above are **additive or minimally corrective**:
- The `bypassPermissions` → `acceptEdits` fix corrects a documented broken behavior; no working
  functionality is removed
- The `attribution` block only prevents Claude authorship in commits — it does not affect any
  permissions or features
- The MEMORY.md trim preserves 100% of content — it moves, not deletes, the truncated section
- The researcher agent files are net-new at user level; they do not overwrite any existing files
- No other project's settings, rules, or agents are modified
