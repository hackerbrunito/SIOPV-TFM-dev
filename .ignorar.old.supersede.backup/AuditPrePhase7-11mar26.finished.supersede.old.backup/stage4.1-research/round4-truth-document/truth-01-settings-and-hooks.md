# Truth-01: settings.json + Hooks — SIOPV
**Generated:** 2026-03-13
**Scope:** `siopv/.claude/settings.json`, `settings.local.json`, `hooks/*.sh` (7 files)
**Authority:** Round 3 §1-§2 + meta-project settings.json + hook source reads

---

## 1. settings.json — Complete Specification

**Action:** NEW (no existing file in siopv/.claude/)

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "includeGitInstructions": false,
  "env": {
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "70",
    "ENABLE_TOOL_SEARCH": "auto:5",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "attribution": {
    "commit": "none"
  },
  "cleanupPeriodDays": 30,
  "statusLine": {
    "type": "command",
    "command": "phase=$(cat .build/current-phase 2>/dev/null || echo 'unknown'); pending=$(ls .build/checkpoints/pending/ 2>/dev/null | wc -l | tr -d ' '); echo \"SIOPV Phase: $phase | Pending: $pending\""
  },
  "sandbox": {
    "mode": "auto-allow",
    "permissions": {
      "write": {
        "allowOnly": ["."],
        "denyWithinAllow": [".env", ".env.local", ".env.*", "credentials.json", "*.pem", "*.key"]
      }
    },
    "network": {
      "allowedDomains": [
        "pypi.org",
        "api.github.com",
        "api.anthropic.com",
        "docs.pydantic.dev",
        "www.anthropic.com",
        "docs.anthropic.com",
        "api.atlassian.com",
        "smith.langchain.com",
        "redis.io",
        "docs.streamlit.io"
      ]
    },
    "allowUnsandboxedCommands": false,
    "allowUnixSockets": false
  },
  "permissions": {
    "deny": [
      "Bash(rm -rf /)",
      "Bash(rm -rf ~)",
      "Bash(sudo:*)",
      "Bash(git push --force:*)",
      "Bash(git reset --hard:*)",
      "Read(.env)",
      "Read(.env.*)",
      "Edit(.env)",
      "Edit(.env.*)",
      "Read(credentials*)",
      "Edit(credentials*)"
    ],
    "ask": [
      "Bash(git push:*)",
      "Bash(rm:*)",
      "Bash(docker:*)",
      "Bash(docker-compose:*)"
    ],
    "allow": [
      "Bash(uv:*)",
      "Bash(ruff:*)",
      "Bash(mypy:*)",
      "Bash(pytest:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git status)",
      "Bash(git diff:*)",
      "Bash(git log:*)",
      "Bash(git worktree:*)",
      "Bash(chmod:*)",
      "Bash(mkdir:*)",
      "Bash(ls:*)",
      "Bash(whoami)",
      "Bash(pwd)",
      "Bash(cat:*)",
      "Bash(tree:*)",
      "Bash(env)",
      "Bash(echo:*)",
      "Bash(find:*)",
      "Bash(grep:*)",
      "Bash(touch:*)",
      "Bash(date:*)",
      "Bash(jq:*)",
      "Bash(wc:*)",
      "Bash(md5:*)",
      "Bash(curl:*)"
    ]
  },
  "hooks": {
    "SessionStart": [
      {
        "hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/session-start.sh"}]
      },
      {
        "hooks": [{"type": "command", "command": "today=$(date +%Y-%m-%d); if [ ! -f .build/checkpoints/daily/$today.json ]; then echo \"REMINDER: No daily checkpoint for $today.\"; fi"}]
      },
      {
        "matcher": "compact",
        "hooks": [{"type": "command", "command": "echo \"=== POST-COMPACT SIOPV CONTEXT ===\"; echo \"Stack: Python 3.11+, LangGraph 0.2+, Streamlit, OpenFGA, Presidio, fpdf2\"; echo \"Phase: $(cat .build/current-phase 2>/dev/null || echo unknown)\"; echo \"Pending: $(ls .build/checkpoints/pending/ 2>/dev/null | tr '\\n' ',')\"; echo \"Read .claude/workflow/briefing.md. Run /verify before commit.\""}]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/pre-write.sh"}]
      },
      {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/pre-git-commit.sh"}]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/post-code.sh", "timeout": 60}]
      },
      {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/coverage-gate.sh", "timeout": 30}]
      }
    ],
    "PreCompact": [
      {
        "hooks": [{"type": "command", "command": "echo \"=== CONTEXT PRESERVATION ===\"; echo \"Phase: $(cat .build/current-phase 2>/dev/null || echo unknown)\"; echo \"Pending: $(ls .build/checkpoints/pending/ 2>/dev/null | wc -l | tr -d ' ')\""}]
      },
      {
        "async": true,
        "hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/pre-compact.sh"}]
      }
    ],
    "Stop": [
      {
        "hooks": [{"type": "command", "command": "pending=$(ls .build/checkpoints/pending/ 2>/dev/null | wc -l | tr -d ' '); if [ \"$pending\" -gt 0 ]; then echo \"WARNING: $pending files pending verification. Run /verify before commit.\"; fi"}]
      }
    ],
    "PostToolUseFailure": [
      {
        "matcher": "Write|Edit",
        "hooks": [{"type": "command", "command": "echo '{\"event\":\"tool_failure\",\"tool\":\"'\"$TOOL_NAME\"'\",\"timestamp\":\"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'\"}' >> .build/logs/agents/$(date +%Y-%m-%d).jsonl 2>/dev/null || true"}]
      }
    ],
    "SubagentStart": [
      {
        "hooks": [{"type": "command", "command": "echo '{\"event\":\"subagent_start\",\"timestamp\":\"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'\"}' >> .build/logs/agents/$(date +%Y-%m-%d).jsonl 2>/dev/null || true"}]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [{"type": "command", "command": "echo '{\"event\":\"subagent_stop\",\"timestamp\":\"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'\"}' >> .build/logs/agents/$(date +%Y-%m-%d).jsonl 2>/dev/null || true"}]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [{"type": "command", "command": "echo '{\"event\":\"session_end\",\"timestamp\":\"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'\"}' >> .build/logs/sessions/$(date +%Y-%m-%d).jsonl 2>/dev/null || true; rm -f /tmp/claude/*.tmp 2>/dev/null || true"}]
      },
      {
        "hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/session-end.sh"}]
      }
    ],
    "Notification": [
      {
        "hooks": [{"type": "command", "command": "echo '{\"event\":\"notification\",\"timestamp\":\"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'\",\"session_id\":\"'$(cat .build/current-session-id 2>/dev/null || echo unknown)'\"}' >> .build/logs/agents/$(date +%Y-%m-%d).jsonl 2>/dev/null || true"}]
      }
    ]
  }
}
```

**Removals vs. meta-project:** No `UserPromptSubmit` project-detection hook (SIOPV is single-project). No MCP health check (`CONTEXT7_API_KEY` concern is meta-project's). No `.build/active-project` references. No duplicate compact matcher calling session-start.sh.

---

## 2. Hook Scripts

### 2a. session-start.sh — ADAPT

**Path:** `siopv/.claude/hooks/session-start.sh`
**What it does:** Prints briefing.md + last 5 lines of compaction-log.md on every session start. Non-blocking.
**Lines to change** (from meta-project source):

```
Line 12: BRIEFING="/Users/bruno/sec-llm-workbench/.claude/workflow/briefing.md"
→         BRIEFING="${CLAUDE_PROJECT_DIR}/.claude/workflow/briefing.md"

Line 13: COMPACT_LOG="/Users/bruno/sec-llm-workbench/.claude/workflow/compaction-log.md"
→         COMPACT_LOG="${CLAUDE_PROJECT_DIR}/.claude/workflow/compaction-log.md"
```

All other lines: unchanged. Exit 0 trap ensures session start never blocks.

---

### 2b. session-end.sh — ADAPT

**Path:** `siopv/.claude/hooks/session-end.sh`
**What it does:** Updates `> Last updated:` timestamp in briefing.md, appends to compaction-log.md. Non-blocking.
**Lines to change:**

```
Line 12: BRIEFING="/Users/bruno/sec-llm-workbench/.claude/workflow/briefing.md"
→         BRIEFING="${CLAUDE_PROJECT_DIR}/.claude/workflow/briefing.md"

Line 13: COMPACT_LOG="/Users/bruno/sec-llm-workbench/.claude/workflow/compaction-log.md"
→         COMPACT_LOG="${CLAUDE_PROJECT_DIR}/.claude/workflow/compaction-log.md"
```

---

### 2c. pre-compact.sh — ADAPT

**Path:** `siopv/.claude/hooks/pre-compact.sh`
**What it does:** Updates briefing.md timestamp + appends compaction event to log. Fires before auto/manual compaction.
**Lines to change:**

```
Line 12: BRIEFING="/Users/bruno/sec-llm-workbench/.claude/workflow/briefing.md"
→         BRIEFING="${CLAUDE_PROJECT_DIR}/.claude/workflow/briefing.md"

Line 13: COMPACT_LOG="/Users/bruno/sec-llm-workbench/.claude/workflow/compaction-log.md"
→         COMPACT_LOG="${CLAUDE_PROJECT_DIR}/.claude/workflow/compaction-log.md"
```

**R1 verified:** `PreCompact` is the correct hook for saving state before compaction. `PostCompact` does not exist. `SessionStart` compact matcher is unreliable (bug #15174).

---

### 2d. post-code.sh — ADAPT ⚠️

**Path:** `siopv/.claude/hooks/post-code.sh`
**Truth-00 says COPY — but MUST ADAPT:** The meta-project source (lines 54-58) contains a guard that skips files when `FILE_PATH` starts with `CLAUDE_PROJECT_DIR`. When run from SIOPV, this guard matches ALL SIOPV source files and prevents ruff formatting and pending marker creation entirely.

**Remove these lines:**
```bash
# No procesar archivos del META-PROYECTO
META_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"
if [ -n "$META_PROJECT_DIR" ] && [[ "$FILE_PATH" == "$META_PROJECT_DIR"* ]]; then
    exit 0
fi
```

All other lines: unchanged. The hook still uses `CLAUDE_PROJECT_DIR` correctly for log dirs and markers.

---

### 2e. pre-git-commit.sh — COPY

**Path:** `siopv/.claude/hooks/pre-git-commit.sh`
**Action:** COPY as-is.
**Why it works:** `.build/active-project` read gracefully returns empty → falls back to `CLAUDE_PROJECT_DIR` for pending dir. Score check script won't exist (`if [ -f "$SCORE_CHECK_SCRIPT" ]` guard skips it). All other logic is portable.

---

### 2f. pre-write.sh — COPY

**Path:** `siopv/.claude/hooks/pre-write.sh`
**Action:** COPY as-is.
**Why it works:** Uses `CLAUDE_PROJECT_DIR` for checkpoint paths. If daily checkpoints don't exist (fresh SIOPV install), it emits `ask` permission with reminder — non-breaking fallback.

---

### 2g. coverage-gate.sh — NEW

**Path:** `siopv/.claude/hooks/coverage-gate.sh`
**Hook type:** PostToolUse (matcher: `Bash`) — non-blocking; emits stderr warning Claude reads
**What it does:** After any pytest --cov command, checks TOTAL coverage ≥ 83%. If below, writes a pending marker (causing pre-git-commit to block commit) and warns Claude via stderr.

```bash
#!/usr/bin/env bash
# coverage-gate.sh — PostToolUse: check pytest coverage >= 83%
# Non-blocking hook; writes pending marker to block commit if coverage regresses.

trap 'exit 0' ERR

INPUT=$(cat)

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
if [[ "$COMMAND" != *"pytest"* ]] || [[ "$COMMAND" != *"--cov"* ]]; then
    exit 0
fi

OUTPUT=$(echo "$INPUT" | jq -r '.tool_output // empty' 2>/dev/null)
COVERAGE=$(echo "$OUTPUT" | grep -oE 'TOTAL[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+([0-9]+)%' \
    | grep -oE '[0-9]+%$' | tr -d '%' | tail -1)

if [[ -z "$COVERAGE" ]]; then
    exit 0
fi

THRESHOLD=83
if [[ "$COVERAGE" -lt "$THRESHOLD" ]]; then
    VERIFICATION_DIR="${CLAUDE_PROJECT_DIR:-.}/.build/checkpoints/pending"
    mkdir -p "$VERIFICATION_DIR"
    cat > "$VERIFICATION_DIR/coverage-below-threshold" << EOF
{
  "file": "coverage-check",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "verified": false,
  "reason": "Coverage ${COVERAGE}% below threshold ${THRESHOLD}%"
}
EOF
    echo "COVERAGE GATE: ${COVERAGE}% < ${THRESHOLD}% threshold. Commit blocked until coverage is restored." >&2
fi

exit 0
```

---

## 3. settings.local.json

**Path:** `siopv/.claude/settings.local.json` (gitignored — machine-local only)
**Action:** ADAPT — expand from current 7-line single-rule file

```json
{
  "permissions": {
    "allow": [
      "Bash(curl:*)"
    ]
  },
  "claudeMdExcludes": []
}
```

**Notes:**
- `curl:*` replaces the overly specific `curl -s "https://www.google.com" | head -1` that exists currently
- `docker` and `docker-compose` stay in `ask` (settings.json) — promote to `allow` here if desired locally
- `claudeMdExcludes` left empty; developers can add files to skip (e.g., `["~/.claude/CLAUDE.md"]`) without committing that preference

---

## 4. Cross-References

| File in truth-01 | Depends on | Depended on by |
|-----------------|------------|----------------|
| `settings.json` | `workflow/briefing.md` path must exist (truth-11) | truth-09 (wiring audit), truth-10 (acceptance checklist) |
| `hooks/session-start.sh` | `workflow/briefing.md` + `workflow/compaction-log.md` (truth-11) | truth-11 |
| `hooks/session-end.sh` | `workflow/briefing.md` + `workflow/compaction-log.md` (truth-11) | truth-11 |
| `hooks/pre-compact.sh` | `workflow/compaction-log.md` (truth-11) | truth-11 |
| `hooks/post-code.sh` | `pyproject.toml` must exist in SIOPV root | truth-09 |
| `hooks/pre-git-commit.sh` | `.build/checkpoints/pending/` (created by post-code.sh, coverage-gate.sh) | truth-10 |
| `hooks/coverage-gate.sh` | `pytest --cov` output format (TOTAL line) | truth-05 (verification-thresholds.md: 83% floor) |
| Agent model settings | `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json | truth-03 |
| `/verify` skill | Hook-created pending markers in `.build/checkpoints/pending/` | truth-06 |
| `compaction-log.md` timestamp format | `> Last updated:` marker in briefing.md | truth-11 |
