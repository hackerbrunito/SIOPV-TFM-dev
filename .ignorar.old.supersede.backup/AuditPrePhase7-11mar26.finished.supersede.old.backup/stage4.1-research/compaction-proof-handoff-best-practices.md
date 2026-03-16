# Compaction-Proof Handoff Best Practices
# Claude Code Session Continuity — Research-Backed Reference

> **Version:** 2026-03-13
> **Research base:** Online research conducted 2026-03-13 (see raw report: `compaction-proof-research-raw-2026-03-13.md`)
> **Purpose:** Authoritative guide for implementing compaction-proof session continuity in SIOPV.
> **Referenced by:** stage4.1-orchestrator-guidelines.md → truth-11-compaction-proof-session-continuity.md

---

## 1. CORE PRINCIPLE

**Accept compaction as inevitable. Design recovery to be so efficient that compaction becomes a non-event.**

Each successive compaction compounds information loss (cumulative degradation). Do not fight compaction — design around it. A briefing file that is read fresh at session start is more reliable than trusting the compaction summary to carry context across multiple rounds.

---

## 2. HOOK SYSTEM — VERIFIED FACTS (March 2026)

### 2.1 Hook Types Available

| Hook | When it fires | Can block? | Timeout | Context injection? |
|------|--------------|------------|---------|-------------------|
| `SessionStart` | Session start, resume, post-clear, post-compaction | No | None | YES — stdout or additionalContext |
| `PreCompact` | Before compaction runs | No (exit 2 only shows stderr) | None | NO |
| `SessionEnd` | Session terminates | No | **1.5 seconds** | NO |

**PreCompact only supports `type: "command"` hooks.** The `prompt`, `agent`, and `http` types are NOT supported for PreCompact.

### 2.2 SessionStart — Context Injection

**Two methods (both work):**

**Method A: Plain stdout (current meta-project — verified working)**
```bash
cat briefing.md
exit 0
```
Plain stdout at exit 0 is added to Claude's context as visible hook output.

**Method B: JSON additionalContext (recommended — cleaner)**
```bash
context=$(cat briefing.md)
echo "{\"hookSpecificOutput\": {\"hookEventName\": \"SessionStart\", \"additionalContext\": \"$context\"}}"
exit 0
```
JSON format is injected more discretely — does not appear as visible hook output in transcript.

**CRITICAL BUG (active March 2026, issues #15174 + #13650):**
> SessionStart hooks with the **`compact` matcher** execute successfully BUT their stdout output is **NOT injected into Claude's context** after compaction completes.

**Consequence:** The `source: "compact"` SessionStart trigger is unreliable for context restoration. This affects the current meta-project's `session-start.sh`.

**Correct workaround:** Add compact instructions to CLAUDE.md (see Section 5.1).

**Other known behaviors:**
- `claude --continue` causes double-firing: both `startup` AND `resume` matchers fire simultaneously. Design hooks to be idempotent.
- `/clear` generates a new session ID; `/compact` preserves the existing session ID.
- `model` field absent for `clear` and `resume` sources despite docs claiming it's always present.

**Special capability:** SessionStart hooks (and only them) have access to `CLAUDE_ENV_FILE` — a path where they can write `export` statements that persist as env vars for all subsequent Bash tool calls.

### 2.3 PreCompact — What It Can and Cannot Do

**Input JSON received (stdin):**
```json
{
  "transcript_path": "/path/to/transcript.jsonl",
  "trigger": "manual" | "auto",
  "custom_instructions": ""
}
```

**Key fact:** PreCompact fires BEFORE the compaction summary is generated. It receives `transcript_path` to the raw full conversation — NOT the summary that's about to be created.

**What it CAN do:**
- Read the full transcript via `transcript_path`
- Generate a recovery brief by spawning `claude -p "summarize..." --print` (with transcript tail)
- Write timestamped pre-compaction briefs to disk
- Append log entries, update timestamps

**What it CANNOT do:**
- Block compaction
- Access the compaction summary content
- Receive the result of what the compaction LLM will generate

**KNOWN BUG (issue #13668):** `transcript_path` can be null/empty. Always implement fallback:
```bash
if [[ -z "$TRANSCRIPT" || "$TRANSCRIPT" == "null" ]]; then
  TRANSCRIPT=$(ls -t ~/.claude/projects/*/*.jsonl 2>/dev/null | head -1)
fi
```

**Best practice — async PreCompact pattern:**
```bash
#!/usr/bin/env bash
# Register with async: true in settings.json — does not block compaction
INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path')
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)

# Fallback for empty transcript_path (bug #13668)
if [[ -z "$TRANSCRIPT" || "$TRANSCRIPT" == "null" ]]; then
  TRANSCRIPT=$(ls -t ~/.claude/projects/*/*.jsonl 2>/dev/null | head -1)
fi

if [[ -f "$TRANSCRIPT" ]]; then
  tail -100 "$TRANSCRIPT" | claude -p \
    "Generate compact recovery brief: current task, key decisions, next action, files modified. Max 30 lines." \
    --print > ".claude/workflow/pre-compact-brief-${TIMESTAMP}.md" 2>/dev/null
fi

# Always update timestamp in briefing.md
BRIEFING=".claude/workflow/briefing.md"
if [[ -f "$BRIEFING" ]]; then
  sed -i '' "s/Last updated: .*/Last updated: $(date -u +%Y-%m-%dT%H:%M:%SZ)/" "$BRIEFING"
fi

echo "PreCompact: brief saved to pre-compact-brief-${TIMESTAMP}.md" >&2
exit 0
```

### 2.4 SessionEnd — Constraints

**Hard limit: 1.5 second default timeout.** Override with:
```bash
CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS=5000 claude
```

**Do NOT do in SessionEnd:**
- Call `claude -p` to generate summaries
- Run git operations
- Read large files

**DO in SessionEnd:** timestamp updates, log line appends, small file writes only.

---

## 3. HANDOFF FILE — REQUIRED SECTIONS

Every compaction-proof recovery document must contain these sections:

| # | Section | Purpose |
|---|---------|---------|
| 1 | Recovery header comment | First line: `<!-- COMPACT-SAFE: read after compaction -->` |
| 2 | Project identity | What is this project, where is the spec, absolute paths |
| 3 | Current status table | Phase completion with ✅/⏳/❌ markers, last-known metrics |
| 4 | Ordered execution plan | All stages with status markers, entry conditions |
| 5 | NEXT IMMEDIATE ACTION | Single executable sentence — no ambiguity |
| 6 | Key file paths | Absolute paths to all critical files |
| 7 | Critical constraints | Scope rules, architecture decisions that cannot change |
| 8 | Agent/hook inventory | Brief table of what exists and what each does |
| 9 | Errors to avoid | Past mistakes that must not recur |

**Sections to AVOID:**
- Large raw code snippets (reference file paths instead)
- Verbose prose (use tables and bullets)
- Information that changes on every tool call
- Duplicate content already in CLAUDE.md

**Size limit: ≤ 500 lines.** Beyond this, the file consumes too much context budget at session start.

For projects exceeding 500 lines of critical context, use a tiered system:
- `briefing.md` — ≤ 200 lines, critical recovery info only (always injected via SessionStart)
- `briefing-full.md` — complete context, loaded on demand with `@.claude/workflow/briefing-full.md`

---

## 4. WHEN TO UPDATE THE HANDOFF FILE

**Recommended hybrid approach for multi-round orchestration:**

| Trigger | Who updates | What changes |
|---------|-------------|-------------|
| Stage completes | Claude (behavioral instruction in CLAUDE.md) | Status marker, next immediate action |
| PreCompact fires | Hook (pre-compact.sh) | Timestamp only + generate timed brief |
| SessionEnd fires | Hook (session-end.sh) | Timestamp + log entry |
| Human checkpoint approved | Claude | Status marker, notes |

**Do NOT** update the briefing file on every tool call. This creates race conditions and meaningless diffs.

**The behavioral instruction to add to CLAUDE.md:**
```
When a stage, round, or major task completes, immediately update briefing.md:
- Change stage status from ⏳ PENDING to ✅ COMPLETE
- Update "NEXT IMMEDIATE ACTION" to the next concrete step
- Add the absolute path to the stage's final report in Section 4 (Key File Paths)
```

---

## 5. CRITICAL WORKAROUNDS

### 5.1 compact matcher SessionStart stdout bug — WORKAROUND

Add compact instructions to CLAUDE.md. This is the **only reliable mechanism** for guiding what survives compaction.

```markdown
## Compact Instructions

When compacting, always preserve:
- Current stage name and status (PENDING/IN-PROGRESS/COMPLETE)
- The NEXT IMMEDIATE ACTION sentence verbatim
- All absolute file paths from briefing.md Section 4
- Phase completion table with ✅/⏳/❌ markers
- Last known test metrics (passing count, coverage %, mypy/ruff errors)
- The two-project setup paths (meta-project + SIOPV project)
```

### 5.2 Multi-round orchestration: file-based state for recovery

For TeamCreate orchestration with multiple rounds, context cannot be trusted to carry across compaction boundaries. **Every agent must write its completion state to disk.**

Implementation:
- Each agent writes a completion record to a known path before going idle
- The orchestrator reads agent state files at round boundaries (never from context)
- The briefing.md contains the path to the current round's state directory

### 5.3 Idempotent hooks for --continue double-firing

SessionStart with `--continue` fires both `startup` AND `resume` matchers simultaneously. Protect against double execution:
```bash
LOCK="/tmp/session-start-${SESSION_ID}.lock"
if [[ -f "$LOCK" ]]; then exit 0; fi
touch "$LOCK"
# ... do work ...
```

---

## 6. CURRENT META-PROJECT ASSESSMENT

### What the meta-project does correctly
- PreCompact: updates timestamp + logs — lightweight, non-blocking, exits 0 ✅
- SessionEnd: updates timestamp + logs — within 1.5s timeout ✅
- SessionStart: cats briefing.md — plain stdout injection verified working for `startup` source ✅
- briefing.md has recovery header, phase table, ordered execution plan ✅
- Hooks always exit 0 — never blocks compaction ✅

### Gaps to fix in SIOPV (Stage 4.2 deliverables)

| Gap | Priority | Fix |
|-----|----------|-----|
| compact matcher SessionStart stdout not injected (bug #15174) | HIGH | Add compact instructions to CLAUDE.md |
| PreCompact does not generate a brief from transcript | MEDIUM | Upgrade pre-compact.sh to use `claude -p` |
| No phase-completion update behavioral rule in CLAUDE.md | MEDIUM | Add compact instructions block to CLAUDE.md |
| No per-agent file-based state for multi-round recovery | MEDIUM | Agent spec must require state file write at task completion |
| Plain stdout vs. JSON additionalContext | LOW | Optional — plain stdout works |
| transcript_path null guard | MEDIUM | Add fallback to pre-compact.sh |

---

## 7. IMPLEMENTATION TEMPLATE FOR SIOPV

### settings.json hook registration
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [{ "type": "command", "command": "/Users/bruno/siopv/.claude/hooks/session-start.sh" }]
      },
      {
        "matcher": "compact",
        "hooks": [{ "type": "command", "command": "/Users/bruno/siopv/.claude/hooks/session-start.sh" }]
      },
      {
        "matcher": "resume",
        "hooks": [{ "type": "command", "command": "/Users/bruno/siopv/.claude/hooks/session-start.sh" }]
      }
    ],
    "PreCompact": [
      {
        "hooks": [{ "type": "command", "command": "/Users/bruno/siopv/.claude/hooks/pre-compact.sh", "async": true }]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [{ "type": "command", "command": "/Users/bruno/siopv/.claude/hooks/session-end.sh" }]
      }
    ]
  }
}
```

### CLAUDE.md compact instructions block (mandatory)
```markdown
## Compact Instructions

When compacting, always preserve:
- Current SIOPV phase and status (e.g., "Phase 7 — Human-in-the-Loop: IN PROGRESS")
- The NEXT IMMEDIATE ACTION sentence verbatim
- All absolute file paths from briefing.md Section 4 (Key File Paths)
- Phase completion table with ✅/⏳/❌ markers
- Last known metrics: tests passing, coverage %, mypy/ruff error counts
- Meta-project path: /Users/bruno/sec-llm-workbench/
- SIOPV project path: /Users/bruno/siopv/
- Current working directory for active session
```

---

## 8. KEY BUGS TO KNOW (March 2026)

| Bug # | Description | Workaround |
|-------|-------------|-----------|
| #15174 / #13650 | SessionStart `compact` matcher stdout not injected post-compaction | Use CLAUDE.md compact instructions |
| #13668 | PreCompact `transcript_path` can be null/empty | Add fallback: `ls -t ~/.claude/projects/*/*.jsonl | head -1` |
| #14281 | `additional_context` (underscore) causes duplicate injection | Use `additionalContext` (camelCase) in JSON format |

---

*End of compaction-proof handoff best practices. This file is referenced by stage4.1-orchestrator-guidelines.md.*
