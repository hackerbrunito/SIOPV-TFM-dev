# Compaction-Proof Session Continuity in Claude Code — Research Report
**Date:** 2026-03-13
**Researcher:** Claude Code (claude-sonnet-4-6)
**Scope:** March 2026 best practices for Claude Code hook system + session continuity

---

## 1. Hook System Findings (PreCompact, SessionStart, SessionEnd)

### 1.1 Hook Registration — settings.json Schema

Hooks are defined in one of four locations (in ascending specificity):
- `~/.claude/settings.json` — all projects, not shareable
- `.claude/settings.json` — single project, can be committed
- `.claude/settings.local.json` — single project, gitignored
- Managed policy settings — org-wide, admin-controlled

The full hook config schema nests three levels:
1. **Hook event name** (e.g. `"PreCompact"`)
2. **Matcher group** — regex string filtering when the hook fires
3. **Hook handlers** — array of command/http/prompt/agent objects

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [{ "type": "command", "command": "/path/to/script.sh" }]
      },
      {
        "matcher": "compact",
        "hooks": [{ "type": "command", "command": "/path/to/post-compact.sh" }]
      }
    ],
    "PreCompact": [
      {
        "hooks": [{ "type": "command", "command": "/path/to/pre-compact.sh", "async": true }]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [{ "type": "command", "command": "/path/to/session-end.sh" }]
      }
    ]
  }
}
```

**CRITICAL: PreCompact only supports `type: "command"` hooks.** The prompt, agent, and http types are NOT supported for PreCompact, InstructionsLoaded, ConfigChange, Notification. This is documented in the official reference as a hard constraint.

---

### 1.2 SessionStart Hook

**When it fires:** Every session start, resume, post-clear, or post-compaction. Cannot block execution.

**Input JSON received (stdin):**
```json
{
  "session_id": "abc123",
  "transcript_path": "/Users/.../.claude/projects/.../transcript.jsonl",
  "cwd": "/Users/...",
  "permission_mode": "default",
  "hook_event_name": "SessionStart",
  "source": "startup",
  "model": "claude-sonnet-4-6"
}
```

**Matcher values:**
| Matcher   | Fires when                                   |
|-----------|----------------------------------------------|
| `startup` | New session                                  |
| `resume`  | `--resume`, `--continue`, or `/resume`       |
| `clear`   | `/clear` command                             |
| `compact` | Auto or manual compaction                    |

**Context injection — two methods:**

**Method A: Plain stdout (current meta-project approach)**
```bash
cat briefing.md
exit 0
```
Plain stdout at exit 0 is added to Claude's context. This is the simpler approach and verified to work.

**Method B: JSON `additionalContext` (recommended by official docs)**
```bash
context=$(cat briefing.md)
echo '{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "'"$context"'"}}'
exit 0
```
The `additionalContext` field is injected "more discretely" — it does not appear as visible hook output in the transcript, whereas plain stdout does. Both work, but JSON format provides cleaner context injection.

**KNOWN BUG (active as of March 2026, issue #15174 + #13650):**
> SessionStart hooks with the **`compact` matcher** execute successfully but their stdout output is **NOT injected into Claude's context** after compaction completes.

This means the `source: "compact"` SessionStart trigger is **unreliable for context restoration**. The CLAUDE.md workaround is confirmed to be the only reliable mechanism for post-compaction context.

**Other confirmed undocumented behaviors:**
- `claude --continue` causes **double-firing**: both `startup` AND `resume` matchers fire simultaneously
- `model` field is absent for `clear` and `resume` sources (despite official docs claiming it's always present)
- `/clear` generates a new session ID; `/compact` preserves the existing session ID
- `permission_mode` field does not always appear despite being documented

**Special capability: `CLAUDE_ENV_FILE`**
SessionStart hooks (and ONLY SessionStart hooks) have access to `CLAUDE_ENV_FILE` — a path where they can write `export` statements that persist as environment variables for all subsequent Bash tool calls in the session.

---

### 1.3 PreCompact Hook

**When it fires:** Before compaction runs (manual `/compact` or auto at ~95% context fill).

**Input JSON received (stdin):**
```json
{
  "session_id": "abc123",
  "transcript_path": "/Users/.../.claude/projects/.../transcript.jsonl",
  "cwd": "/Users/...",
  "permission_mode": "default",
  "hook_event_name": "PreCompact",
  "trigger": "manual",
  "custom_instructions": ""
}
```

**Key fields:**
- `trigger`: `"manual"` (from `/compact`) or `"auto"` (automatic)
- `custom_instructions`: contains user's instructions from `/compact [instructions]`; empty for auto
- `transcript_path`: path to the full JSONL conversation history

**Can it read the compaction summary content?**
**NO.** The PreCompact hook fires BEFORE the compaction summary is generated. It receives `transcript_path` pointing to the raw full conversation, not a pre-computed summary. The hook must independently read the transcript and, if needed, spawn a fresh Claude instance (`claude -p`) to generate a summary.

**What it can do:**
- Read the full transcript via `transcript_path`
- Spawn `claude -p "summarize this session" --print` using the transcript content
- Write a handoff/recovery document to disk
- Append log entries
- Update timestamps
- Run `async: true` to avoid blocking compaction (recommended for backup operations)

**What it CANNOT do:**
- Block compaction (exit code 2 only shows stderr to user, does not stop compaction)
- Access the compaction summary that's about to be generated
- Use prompt/agent/http hook types (command-only)
- Return `additionalContext` to inject into the post-compaction session (no decision control)

**KNOWN BUG (issue #13668):**
In some scenarios, the `transcript_path` received by PreCompact is empty/null. Production hooks must implement fallback detection for the transcript path.

**Best practice — async backup pattern:**
```bash
#!/usr/bin/env bash
# Use async: true in settings.json since backups don't need to block compaction
INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)

# Fallback if transcript_path is empty
if [[ -z "$TRANSCRIPT" || "$TRANSCRIPT" == "null" ]]; then
  # Detect from known pattern
  TRANSCRIPT=$(ls -t ~/.claude/projects/*/*.jsonl 2>/dev/null | head -1)
fi

# Tail last 50 lines and generate summary via fresh Claude instance
if [[ -f "$TRANSCRIPT" ]]; then
  tail -50 "$TRANSCRIPT" | claude -p "Generate a compact recovery brief: current task, key decisions, next action, files modified" --print \
    > "$CLAUDE_PROJECT_DIR/.claude/workflow/pre-compact-brief-${TIMESTAMP}.md" 2>/dev/null
fi

exit 0
```

---

### 1.4 SessionEnd Hook

**When it fires:** Session terminates (normal exit, /exit, browser close, etc.).

**Input JSON:**
```json
{
  "session_id": "abc123",
  "transcript_path": "/Users/.../.claude/projects/.../transcript.jsonl",
  "cwd": "/Users/...",
  "permission_mode": "default",
  "hook_event_name": "SessionEnd",
  "reason": "other"
}
```

**Reason values:** `clear`, `logout`, `prompt_input_exit`, `bypass_permissions_disabled`, `other`

**CRITICAL CONSTRAINT:** SessionEnd has a **default timeout of 1.5 seconds**. This applies to both session exit AND `/clear`. Any work that takes longer will be cut off. Override with:
```bash
CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS=5000 claude
```

**Implication:** SessionEnd is unsuitable for expensive operations like calling `claude -p` to generate summaries. Use PreCompact for that. SessionEnd should only do lightweight operations: timestamp updates, log appends, file writes.

**Cannot:** Block session termination, inject context, return any decision.

---

## 2. Handoff File Best Practices

### 2.1 Core Philosophy (2026 community consensus)

> **"Compound, don't compact"** — extract learnings automatically, start fresh with full context each time.

The strategic approach favored in 2026 is to **accept compaction as inevitable** and design the recovery system to be so efficient that compaction becomes a non-event rather than trying to preserve or prevent it.

Key insight from research: **cumulative compaction degrades quality**. Each successive compaction compounds information loss. This means a briefing file that is read fresh at session start is more reliable than trusting the compaction summary to carry forward context across multiple rounds.

### 2.2 When to Update the Handoff File

**Two schools of thought:**

**School A — Event-driven (hooks only):**
Update the handoff file only at: PreCompact, SessionEnd, and at natural phase boundaries. Rationale: constant updates bloat the file and introduce noise; let the hooks handle it.

**School B — Dirty-flag threshold (Continuous Claude v3 pattern):**
Track a "dirty flag" that increments on every significant change (file edit, decision made). When dirty_flag > 20, trigger an auto-handoff write. This creates progressive snapshots during active sessions.

**Recommendation for multi-round orchestration:**
Use a hybrid — hooks fire at compaction/session-end, but the briefing file should be **manually updated by Claude at natural phase boundaries** (after each stage completes, before a new one begins). Do NOT update on every tool call; this creates race conditions and meaningless diffs.

**Official docs guidance on CLAUDE.md:**
> "Customize compaction behavior in CLAUDE.md with instructions like 'When compacting, always preserve the full list of modified files and any test commands'"

This is the officially recommended mechanism for influencing what survives compaction.

### 2.3 Mandatory Sections in a Recovery Document

Based on research across multiple community implementations and the official docs, a compaction-proof recovery document must contain:

1. **Project identity** — What is this project, what is the final goal, where is the spec
2. **Current status** — Phase completion table, last known metrics, what passed/failed
3. **Ordered execution plan** — Full sequence of stages with status markers (✅/⏳/❌)
4. **Next immediate action** — Exactly what to do next (single executable step)
5. **Critical constraints** — Scope rules, decisions made that cannot be changed
6. **Key file paths** — Absolute paths to all critical files (state file, spec, reports)
7. **Agent/hook inventory** — What agents exist and what each one does
8. **Anti-patterns / errors to avoid** — Past mistakes that must not recur
9. **Recovery instruction header** — Top-of-file instruction "read this after compaction"

**Optional but valuable:**
- Last 5 compaction log entries
- Architecture diagram or flow summary
- Environment setup notes

**Sections to AVOID in a recovery document:**
- Large raw code snippets (reference file paths instead)
- Verbose narrative prose (use tables and bullets)
- Information that changes on every tool call (timestamps at the end are OK, not in critical sections)
- Duplicate information already in CLAUDE.md (wastes context budget)

### 2.4 Size Constraints

The briefing file is injected at every session start. If it is too large, it consumes too much of the available context window before work begins. Community practice suggests keeping the briefing file under **500 lines** for a project of moderate complexity.

For larger projects, use a **tiered briefing system**:
- `briefing.md` — core compact document (≤ 500 lines), always loaded
- `briefing-details.md` — full context, loaded on demand via `@` import or manual read

---

## 3. Comparison: Meta-Project Current vs. 2026 Best Practices

### 3.1 What the Meta-Project Does Well

| Aspect | Status | Notes |
|--------|--------|-------|
| PreCompact fires + updates timestamp | ✅ Correct | Lightweight, non-blocking, exits 0 |
| SessionEnd fires + logs event | ✅ Correct | 1.5s timeout is fine for simple writes |
| SessionStart cats briefing.md | ✅ Works | Plain stdout injection is verified to work |
| briefing.md has recovery header | ✅ Correct | `<!-- COMPACT-SAFE: ... read this file immediately after any compaction -->` |
| briefing.md has phase table | ✅ Correct | Essential section, properly formatted |
| briefing.md has ordered execution plan | ✅ Correct | Stages with status markers present |
| Always exits 0 in all hooks | ✅ Correct | Never blocks compaction or session operations |

### 3.2 Gaps and Risks

| Gap | Severity | Details |
|-----|----------|---------|
| **compact matcher SessionStart bug** | HIGH | The `session-start.sh` fires on `compact` source, but per bug #15174/#13650, stdout is NOT injected post-compaction. The file is being cat'd but Claude may not see it. |
| **Pre-compact hook does NOT generate a summary** | MEDIUM | Currently only updates a timestamp — does not read the transcript and generate a recovery brief. The most valuable use of PreCompact is left unused. |
| **No `additionalContext` JSON format** | LOW | Plain stdout works but appears as visible hook output in transcript. JSON format is cleaner. Low priority. |
| **SessionEnd uses same timeout risk** | LOW | Current operations (timestamp + log append) are fast — well within 1.5s. No immediate risk. |
| **No dirty-flag update mechanism** | LOW | Briefing only updated at hooks, not at phase completion. If session ends without hooks firing (crash, kill -9), last phase boundary update is lost. |
| **transcript_path not read in PreCompact** | MEDIUM | Hook does not utilize the `transcript_path` field to generate a richer summary before compaction — this is a missed opportunity for the most critical recovery point. |
| **No per-agent recovery in multi-agent setup** | MEDIUM | For multi-round orchestration with TeamCreate, the single briefing.md serves as the only recovery document. If an orchestrator is mid-round when compaction hits, there is no mechanism to restore its in-progress task list or round state. |
| **`CLAUDE_ENV_FILE` not used** | INFO | SessionStart could use this to inject project-specific env vars. Not currently used. Neutral — only relevant if env setup is needed. |

### 3.3 The Critical Workaround for compact SessionStart bug

Because the `compact` matcher SessionStart stdout is unreliable, the **CLAUDE.md approach is the correct mechanism** for post-compaction context:

```markdown
<!-- in CLAUDE.md or via @import -->
When compacting, always preserve:
- The current stage and its status (PENDING/IN-PROGRESS/COMPLETE)
- The next immediate action
- All absolute file paths to reports and specs
- The ordered execution plan with status markers
```

This instructs the compaction LLM directly on what to include in the summary it generates. This is the officially recommended and battle-tested approach.

---

## 4. Recommended Handoff File Structure/Template

```markdown
<!-- COMPACT-SAFE: [PROJECT NAME] master briefing — read this file immediately after any compaction or session start -->

# [PROJECT NAME] Master Briefing — Compaction-Proof Recovery Document

> **If you just compacted or resumed:** Read this file top to bottom before doing anything else.
> Last updated: [TIMESTAMP]

---

## 1. PROJECT IDENTITY

[One paragraph: what is this project, what is the final deliverable, where is the spec]

- **Spec location:** [absolute path]
- **State file:** [absolute path]
- **Two-project setup (if applicable):** [project paths and what each contains]

---

## 2. CURRENT STATUS

### Phase Completion
| Phase | Name | Status |
|-------|------|--------|
| N | [Name] | ✅/⏳/❌ |

### Metrics (as of [date])
| Metric | Value |
|--------|-------|
| Tests passing | N |
| Coverage | N% |
| mypy errors | N |

---

## 3. ORDERED EXECUTION PLAN

> Source of truth for what to do next. Execute in order. Never skip steps.

### [STAGE-1]: [Name] — ✅ COMPLETE
[Brief description]

### [STAGE-2]: [Name] — ⏳ PENDING
[Brief description + entry conditions]
**Entry condition:** [What must be true before starting this stage]

### NEXT IMMEDIATE ACTION
> [Exactly one sentence. The next concrete step. No ambiguity.]

---

## 4. KEY FILE PATHS

| Component | Absolute Path |
|-----------|--------------|
| Main spec | /path/to/spec |
| State file | /path/to/state.json |
| Final report | /path/to/report.md |
| [Other critical files] | /path/to/... |

---

## 5. CRITICAL CONSTRAINTS

[Numbered list of decisions/rules that cannot change]
1. [Scope rule: e.g. "Phases 7/8 items appearing as MISSING in Phase 0-6 are EXPECTED-MISSING"]
2. [Architecture rule: e.g. "LangGraph uses TypedDict state, not Pydantic — by design"]
3. [Quality rule: e.g. "Precision over speed — target 9.5/10 across all dimensions"]

---

## 6. AGENT/TEAM INVENTORY

| Agent | Role | APPLICABLE/ADAPTABLE/META-ONLY |
|-------|------|--------------------------------|
| [agent-name] | [what it does] | APPLICABLE |

### Hook Inventory
| Hook | Purpose |
|------|---------|
| PreCompact | [what it does] |
| SessionStart | [what it does] |
| SessionEnd | [what it does] |

---

## 7. ERRORS TO AVOID THIS SESSION

[Short list of past mistakes that must not recur in this project]
1. [Error pattern 1]
2. [Error pattern 2]

---

## 8. COMPACTION-SURVIVAL CHECKLIST (for CLAUDE.md)

> Paste this block into CLAUDE.md under "Compact Instructions":

When compacting, preserve:
- Current stage name and status (PENDING/IN-PROGRESS/COMPLETE)
- The NEXT IMMEDIATE ACTION sentence
- All absolute file paths in Section 4
- Phase completion table with status markers
- Current metric values
```

---

## 5. Key Pitfalls to Avoid

### 5.1 CRITICAL: compact matcher SessionStart stdout bug

**Do not rely on SessionStart with matcher `compact` to restore context.** As of March 2026 (bug #15174, #13650), hook stdout with the `compact` source is not injected into Claude's context. The workaround is CLAUDE.md compact instructions.

### 5.2 SessionEnd 1.5-second timeout

**Do not perform expensive work in SessionEnd.** Calling `claude -p`, running git operations, or reading large files will timeout. Limit SessionEnd to: timestamp updates, log line appends, small file writes.

### 5.3 PreCompact does NOT receive the compaction summary

**The PreCompact hook fires BEFORE the summary is generated.** It only gets `transcript_path` to the raw full conversation. If you want a pre-compaction summary, you must generate it yourself by reading the transcript and calling `claude -p`.

### 5.4 Bloated briefing files lose instructions

**Official docs warning (Best Practices page):** "Bloated CLAUDE.md files cause Claude to ignore your actual instructions!" Same principle applies to briefing.md. Keep it under 500 lines. Ruthlessly prune.

### 5.5 transcript_path can be empty in PreCompact

**Bug #13668:** The `transcript_path` field can be null/empty in PreCompact hooks. Always implement fallback path detection:
```bash
if [[ -z "$TRANSCRIPT" || "$TRANSCRIPT" == "null" ]]; then
  TRANSCRIPT=$(ls -t ~/.claude/projects/*/*.jsonl 2>/dev/null | head -1)
fi
```

### 5.6 Double-firing on --continue

**SessionStart fires twice** (startup + resume matchers simultaneously) when using `claude --continue`. If your SessionStart hook has side effects (like creating files or running commands), it will execute twice. Design hooks to be idempotent.

### 5.7 Compacting mid-task breaks coherence

**Community reports:** Auto-compact at ~95% context fill "can cause the model to 'go off the rails' if it happens mid-task." Mitigation: use CLAUDE.md compact instructions to guide the summary, and consider manually compacting between logical phases rather than waiting for auto-compact.

### 5.8 Cumulative compaction degrades quality

**Research finding:** Each successive compaction compounds information loss. After 3+ compactions in a session, quality degrades measurably. For multi-round orchestration, design agents to write explicit file-based state at task completion — never rely on in-context memory to carry across compaction boundaries.

### 5.9 Multi-round orchestration: no per-agent recovery

**Gap in current tooling:** Claude Code's hook system is session-scoped. If a TeamCreate orchestrator is mid-round when compaction hits, the task list and round state must be recovered from persisted files, not from context. Every agent must write its state to disk before going idle or completing.

---

## 6. Summary of Actionable Recommendations

### Recommendation 1 — Fix the compact matcher (HIGH PRIORITY)
The current `session-start.sh` firing on the `compact` source is broken per bug #15174. The correct fix is to add compact instructions to CLAUDE.md:
```markdown
## Compact Instructions
When compacting, preserve:
- Current stage and its status
- The NEXT IMMEDIATE ACTION
- All file paths in Section 4 of briefing.md
- Phase completion table
```
This directly instructs the compaction LLM, which is the only reliable mechanism.

### Recommendation 2 — Upgrade PreCompact to generate a summary (MEDIUM PRIORITY)
The current pre-compact.sh only updates a timestamp. Upgrade it to:
1. Read `transcript_path` (with null guard)
2. Spawn `claude -p "generate recovery brief" --print` with tail of transcript
3. Write the brief to a timestamped file (e.g., `.claude/workflow/pre-compact-brief-TIMESTAMP.md`)
4. Reference the brief path in briefing.md

Use `async: true` in settings.json so backup generation does not block compaction.

### Recommendation 3 — Add phase-completion updates to briefing.md (MEDIUM PRIORITY)
The current approach relies only on hooks to update briefing.md. Claude should update the `CURRENT STATUS` and `NEXT IMMEDIATE ACTION` sections in briefing.md whenever a stage completes. This is a Claude behavioral instruction in CLAUDE.md, not a hook.

### Recommendation 4 — Implement file-based state for multi-round agents (MEDIUM PRIORITY)
For TeamCreate orchestration with multiple rounds:
- Each agent must write its completion state to a YAML or JSON file before going idle
- The orchestrator must read agent state files at round boundaries, not from context
- The briefing.md should contain the path to the current round's state directory

### Recommendation 5 — Keep briefing.md lean and add per-section tiering (LOW PRIORITY)
Consider splitting into:
- `briefing.md` — ≤200 lines, critical recovery info only (always injected)
- `briefing-full.md` — complete context, loaded on demand with `@.claude/workflow/briefing-full.md`

### Recommendation 6 — Switch to `additionalContext` JSON format for SessionStart (LOW PRIORITY)
Replace plain `cat` stdout with structured JSON output for cleaner injection. Low urgency — current approach works. Note: if switching, avoid the `additional_context` (underscore) typo that causes duplicate injection (bug #14281).

---

## Sources

- [Hooks reference - Claude Code Docs](https://code.claude.com/docs/en/hooks)
- [Best Practices for Claude Code - Claude Code Docs](https://code.claude.com/docs/en/best-practices)
- [Session Continuity and Strategic Compaction – Claude CN](https://claudecn.com/en/docs/claude-code/workflows/session-continuity/)
- [Claude Code Session Hooks: Auto-Load Context Every Time](https://claudefa.st/blog/tools/hooks/session-lifecycle-hooks)
- [Claude Code Hooks: Complete Guide to All 12 Lifecycle Events](https://claudefa.st/blog/tools/hooks/hooks-guide)
- [GitHub - parcadei/Continuous-Claude-v3](https://github.com/parcadei/Continuous-Claude-v3)
- [Never Lose Your Flow: Smart Handoff for Claude Code](https://blog.skinnyandbald.com/never-lose-your-flow-smart-handoff-for-claude-code/)
- [BUG: SessionStart hook with "compact" matcher output not injected](https://github.com/anthropics/claude-code/issues/15174)
- [BUG: SessionStart hook stdout silently dropped](https://github.com/anthropics/claude-code/issues/13650)
- [BUG: PreCompact hook receives empty transcript_path](https://github.com/anthropics/claude-code/issues/13668)
- [BUG: Hook additionalContext injected multiple times](https://github.com/anthropics/claude-code/issues/14281)
- [Claude Code SessionStart hook verification (Windows/MINGW64)](https://dev.classmethod.jp/en/articles/claude-code-session-start-hook-verification/)
- [GitHub - mvara-ai/precompact-hook](https://github.com/mvara-ai/precompact-hook)
- [Claude Code Auto Memory and PreCompact Hooks](https://yuanchang.org/en/posts/claude-code-auto-memory-and-hooks/)
- [Context Compaction Research: Claude Code](https://gist.github.com/badlogic/cd2ef65b0697c4dbe2d13fbecb0a0a5f)
- [8 failure modes in dual-orchestrator systems](https://gist.github.com/sigalovskinick/6cc1cef061f76b7edd198e0ebc863397)
- [GitHub - hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code)
- [GitHub - trailofbits/claude-code-config](https://github.com/trailofbits/claude-code-config)
