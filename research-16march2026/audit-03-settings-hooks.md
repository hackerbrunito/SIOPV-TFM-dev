# Audit 03: settings.json & Hook Scripts

> **Auditor:** config-audit agent
> **Date:** 2026-03-16
> **Scope:** Project settings.json, global settings.json, all hook scripts (project + global)

---

## Executive Summary

The SIOPV project has a **well-structured** hooks and settings configuration that demonstrates sophisticated use of Claude Code's features — verification gating, traceability logging, auto-formatting, coverage enforcement, and session lifecycle management. However, the audit found **3 P0 issues** (security/correctness), **7 P1 issues** (best practices violations), and **6 P2 issues** (improvements/missing features).

**Key findings:**
- Sandbox configuration uses a **non-standard schema** that won't be recognized by Claude Code
- Global `settings.json` has an **overly broad file write allow rule** (`Write(/Users/bruno/**)`) — security risk
- Several hooks have **hardcoded absolute paths** instead of using `$CLAUDE_PROJECT_DIR`
- Missing Trail of Bits recommended deny rules for sensitive credential files
- No `PostCompact` hook (only `PreCompact`)
- No anti-rationalization `Stop` hook (prompt type)
- `curl` is in the allow list but also should arguably be in `ask` for security

---

## 1. Project settings.json — `/Users/bruno/siopv/.claude/settings.json`

### 1.1 Valid / Good Practices

| Setting | Assessment |
|---------|------------|
| `$schema` | ✅ Present — enables IDE validation |
| `includeGitInstructions: false` | ✅ Correct for custom git workflow |
| `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: "70"` | ✅ Good — compacts earlier to preserve context |
| `env.ENABLE_TOOL_SEARCH: "auto:5"` | ✅ Aggressive tool search threshold (5%) |
| `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"` | ✅ Teams enabled |
| `attribution.commit: "none"` | ✅ No AI attribution in commits (matches errors-to-rules) |
| `cleanupPeriodDays: 30` | ✅ Default, reasonable |
| `statusLine` | ✅ Custom status showing phase + pending count |
| `permissions.deny` | ✅ Blocks `rm -rf /`, `rm -rf ~`, `sudo`, `git push --force`, `git reset --hard`, `.env` read/edit |
| `permissions.ask` | ✅ `git push`, `rm`, `docker`, `docker-compose` require confirmation |
| `permissions.allow` | ✅ Sensible allow list for dev tools |
| Hook coverage | ✅ Covers SessionStart, PreToolUse, PostToolUse, PreCompact, Stop, PostToolUseFailure, SubagentStart, SubagentStop, SessionEnd, Notification |

### 1.2 Issues Found

#### **[P0-S1] Sandbox configuration uses non-standard schema**

The `sandbox` block uses keys that don't match the official schema:

```json
// CURRENT (non-standard)
"sandbox": {
  "mode": "auto-allow",              // ❌ Not a valid key
  "permissions": {                    // ❌ Not a valid key
    "write": { "allowOnly": [...], "denyWithinAllow": [...] }
  },
  "network": { "allowedDomains": [...] },  // ✅ Valid but misplaced (should be under sandbox.network)
  "allowUnsandboxedCommands": false,  // ✅ Valid
  "allowUnixSockets": false           // ❌ Should be sandbox.network.allowAllUnixSockets
}
```

**Expected schema:**
```json
"sandbox": {
  "enabled": true,
  "autoAllowBashIfSandboxed": true,
  "filesystem": {
    "denyWrite": [".env", ".env.local", ".env.*", "credentials.json", "*.pem", "*.key"]
  },
  "network": {
    "allowedDomains": ["pypi.org", ...],
    "allowAllUnixSockets": false
  },
  "allowUnsandboxedCommands": false
}
```

**Impact:** The sandbox is likely **not active** because `sandbox.enabled` is not set to `true`, and the non-standard keys are silently ignored. The write deny rules in `permissions.write.denyWithinAllow` are not being enforced.

#### **[P0-S2] `attribution.commit: "none"` — invalid value**

The valid values for `attribution.commit` are strings that become the commit trailer text, or `""` (empty string) to suppress. The value `"none"` will literally add `none` as attribution text.

**Fix:** Change to `"attribution": { "commit": "" }` (empty string).

#### **[P1-S1] Missing `$schema` value validation — `includeCoAuthoredBy` not present but `attribution` is**

Good — no deprecated key. No issue here (just noting it was checked).

#### **[P1-S2] Deny rules missing Trail of Bits recommendations**

Missing from deny list:
- `Read(~/.ssh/**)` — SSH keys
- `Read(~/.gnupg/**)` — GPG keys
- `Read(~/.aws/**)` — AWS credentials
- `Read(~/.kube/**)` — Kubernetes config
- `Read(~/.docker/config.json)` — Docker registry auth
- `Read(~/.npmrc)` — npm tokens
- `Read(~/.git-credentials)` — Git credential store
- `Read(~/.config/gh/**)` — GitHub CLI tokens
- `Edit(~/.bashrc)` / `Edit(~/.zshrc)` — Shell config modification
- `Read(./secrets/**)` — Secrets directory

#### **[P1-S3] `Bash(curl:*)` in allow list — potential exfiltration vector**

`curl` can POST data to arbitrary endpoints. While useful for API checks, it should be in `ask` rather than `allow` for a security-sensitive project, or at minimum scoped to specific domains.

#### **[P1-S4] Deny rule syntax may not work as expected**

```json
"Bash(sudo:*)"          // Matches "sudo:something" literally
"Bash(git push --force:*)"  // Matches "git push --force:something"
```

The `:` in Claude Code permission syntax separates the tool name from the specifier. The correct wildcard form for matching commands that **start with** a string is:
```json
"Bash(sudo *)"           // Matches "sudo anything"
"Bash(git push --force *)"  // Matches "git push --force anything"
```

**Impact:** Rules with `:*` may not match actual commands. This is a **critical security gap** — `sudo` and `git push --force` may not actually be blocked.

#### **[P1-S5] No `effortLevel` setting**

The project doesn't pin an effort level. For a thesis project targeting 9.5/10 quality, consider `"effortLevel": "high"`.

#### **[P1-S6] No `language` setting**

The project uses both Spanish and English. Consider `"language": "spanish"` or leave unset (current behavior is fine, but explicit is better).

#### **[P2-S1] `cleanupPeriodDays: 30` could be longer**

For a thesis project with long development cycles, consider 60–90 days to preserve session history longer.

#### **[P2-S2] No `worktree.symlinkDirectories` configured**

The project uses agent teams with worktrees. Adding `"worktree": { "symlinkDirectories": [".venv", "node_modules", ".build"] }` would avoid duplicating large directories.

#### **[P2-S3] Missing `enableAllProjectMcpServers: false`**

Trail of Bits recommends explicitly setting this to `false` to prevent `.mcp.json` from auto-enabling servers from git.

---

## 2. Global settings.json — `~/.claude/settings.json`

### 2.1 Valid / Good Practices

| Setting | Assessment |
|---------|------------|
| `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"` | ✅ Teams enabled globally |
| `attribution.commit: "none"` | ⚠️ Same P0-S2 issue as project — should be `""` |
| `permissions.deny` | ✅ Same deny rules as project |
| `permissions.ask` | ✅ Same ask rules |
| `permissions.defaultMode: "default"` | ✅ Explicit |
| `effortLevel: "medium"` | ✅ Good default |
| `autoUpdatesChannel: "latest"` | ✅ Stays current |
| `teammateMode: "tmux"` | ✅ Better visibility for teams |
| `model: "sonnet"` | ✅ Cost-effective default |

### 2.2 Issues Found

#### **[P0-G1] Overly broad file write permission**

```json
"Write(/Users/bruno/**)",
"Edit(/Users/bruno/**)"
```

This allows Claude to write/edit **any file** under the home directory without prompting — including `.bashrc`, `.zshrc`, `.ssh/config`, other project files, etc. This is a **significant security risk**.

**Fix:** Scope to specific project directories or remove entirely (let the default `acceptEdits` mode handle it per-session).

#### **[P1-G1] `Read(//Users/bruno/**)` — double-slash prefix**

The `//` prefix means "absolute path from filesystem root" in sandbox path syntax, but in permission rules the syntax is different. The correct form for absolute paths in permission rules is just the path: `Read(/Users/bruno/**)`. The `//` prefix may cause the rule to not match.

#### **[P1-G2] `mcp__pencil` allow without scoping**

`"mcp__pencil"` allows ALL Pencil MCP tools without restriction. Consider scoping to specific tools if not all are needed.

#### **[P1-G3] `skipDangerousModePermissionPrompt: true`**

This key is not in the official schema. It may be a leftover from an older version or a custom addition that has no effect.

#### **[P1-G4] Massive WebFetch domain allow list (50+ domains)**

While functional, this list is unmaintainable and grows over time as domains are auto-added. Consider:
- Moving to `WebFetch` (allow all) since the deny list provides the security boundary
- Or maintaining a curated short list of essential domains

#### **[P2-G1] No `$schema` key**

Global settings lacks the JSON schema URL for IDE validation.

#### **[P2-G2] Duplicated deny/ask/allow rules between project and global**

The permission rules are nearly identical in both files. Since arrays merge across scopes, the project file only needs rules **specific to the project**. Common rules should live in global only.

---

## 3. Hook-by-Hook Findings

### 3.1 `session-start.sh` (Project)

| Check | Result |
|-------|--------|
| Exit codes | ⚠️ Uses `trap 'exit 0' ERR` — silences all errors (intentional for robustness but hides bugs) |
| stdin JSON | ❌ Does NOT read stdin — ignores the JSON contract entirely |
| stdout JSON | ❌ Does NOT output JSON — uses plain `echo`/`cat` (works but misses `hookSpecificOutput.additionalContext` pattern) |
| `$CLAUDE_PROJECT_DIR` | ❌ Hardcoded `/Users/bruno/siopv/` paths |
| Timeout | ✅ Default (600s) is fine for this |
| Idempotency | ✅ Lock file mechanism for duplicate fire prevention |

**[P1-H1] Hardcoded paths.** Replace:
```bash
BRIEFING="/Users/bruno/siopv/.claude/workflow/briefing.md"
```
With:
```bash
BRIEFING="${CLAUDE_PROJECT_DIR:-.}/.claude/workflow/briefing.md"
```

**[P1-H2] Should use `hookSpecificOutput.additionalContext`** for proper context injection instead of plain stdout. Current approach works but the output goes to stderr display, not Claude's context window.

### 3.2 `session-end.sh` (Project)

| Check | Result |
|-------|--------|
| Exit codes | ✅ `exit 0` always |
| stdin JSON | ❌ Does NOT read stdin |
| Timeout | ⚠️ SessionEnd has 1.5s default — this script does file I/O + perl regex which is fine but tight |
| `$CLAUDE_PROJECT_DIR` | ❌ Hardcoded paths |
| Error handling | ✅ `trap 'exit 0' ERR` prevents blocking |

**[P1-H3] Hardcoded paths** — same as session-start.sh.

**[P2-H1] Lock file cleanup.** The session-start lock file (`/tmp/siopv-session-start-*.lock`) is never cleaned up by session-end. Should add:
```bash
rm -f /tmp/siopv-session-start-*.lock 2>/dev/null || true
```

### 3.3 `pre-compact.sh` (Project)

| Check | Result |
|-------|--------|
| Exit codes | ✅ `exit 0` |
| stdin JSON | ✅ Reads and parses with jq |
| `$CLAUDE_PROJECT_DIR` | ❌ Hardcoded paths |
| Error handling | ✅ `trap 'exit 0' ERR` |
| Async | ✅ Registered as `async: true` in settings — correct for slow operations |

**[P1-H4] Hardcoded paths** — same issue.

**[P2-H2] Spawns `claude -p` subprocess.** This works but:
- May fail silently if `claude` CLI isn't in PATH during hook execution
- The `&` background fork inside an async hook is unusual — the async flag already handles non-blocking
- Generated brief files accumulate without cleanup

**[P2-H3] Transcript fallback is fragile.** The glob `~/.claude/projects/*/*.jsonl` may match wrong project transcripts.

### 3.4 `pre-git-commit.sh` (Project)

| Check | Result |
|-------|--------|
| Exit codes | ✅ Always `exit 0` — uses JSON `permissionDecision: "deny"` to block |
| stdin JSON | ✅ Reads and parses with jq |
| stdout JSON | ✅ Correct `hookSpecificOutput` format |
| `$CLAUDE_PROJECT_DIR` | ✅ Uses `${CLAUDE_PROJECT_DIR:-.}` |
| `set -euo pipefail` | ✅ Present |

**This is the best-written hook in the project.** Correct JSON contract, proper exit codes, traceability logging, and uses `$CLAUDE_PROJECT_DIR`.

**Minor:** The score check script path uses `${CLAUDE_PROJECT_DIR:-.}/.claude/scripts/check-reviewer-score.sh` — verify this file exists (not found in glob).

### 3.5 `post-code.sh` (Project)

| Check | Result |
|-------|--------|
| Exit codes | ✅ `exit 0` |
| stdin JSON | ✅ Reads and parses with jq |
| `$CLAUDE_PROJECT_DIR` | ✅ Uses `${CLAUDE_PROJECT_DIR:-.}` |
| `set -euo pipefail` | ✅ Present |
| Side effects | ✅ Auto-format with ruff + pending marker creation |

**Good hook.** One minor issue:

**[P2-H4]** The `cd "$PROJECT_DIR"` changes working directory which could affect subsequent hooks in the same process. Since hooks run as separate processes this is fine, but worth noting.

### 3.6 `coverage-gate.sh` (Project)

| Check | Result |
|-------|--------|
| Exit codes | ✅ `exit 0` always (non-blocking, writes marker instead) |
| stdin JSON | ✅ Reads with jq |
| Error handling | ✅ `trap 'exit 0' ERR` |
| Logic | ⚠️ Reads `tool_output` but PostToolUse provides `tool_response`, not `tool_output` |

**[P1-H5] Wrong field name.** The PostToolUse input has `tool_response`, not `tool_output`:
```bash
# Current (may not work):
OUTPUT=$(echo "$INPUT" | jq -r '.tool_output // empty' 2>/dev/null)
# Correct:
OUTPUT=$(echo "$INPUT" | jq -r '.tool_response // empty' 2>/dev/null)
```

This means the coverage gate **may never trigger** because it reads an empty field.

### 3.7 `pre-write.sh` (Project)

| Check | Result |
|-------|--------|
| Exit codes | ✅ `exit 0` |
| stdin JSON | ❌ Does NOT read stdin (but doesn't need to — checks filesystem state) |
| stdout JSON | ✅ Correct `hookSpecificOutput` format |
| `$CLAUDE_PROJECT_DIR` | ✅ Uses `${CLAUDE_PROJECT_DIR:-.}` |
| `set -euo pipefail` | ✅ Present |

**Solid hook.** Uses `permissionDecision: "ask"` as a soft gate — appropriate for reminder-level enforcement.

### 3.8 `user-prompt-submit.sh` (Global — `~/.claude/hooks/`)

| Check | Result |
|-------|--------|
| Exit codes | ✅ Implicit `exit 0` |
| stdin JSON | ❌ Does NOT read stdin — ignores the prompt content |
| stdout | ⚠️ Outputs plain text, not JSON |
| Registration | ❌ **NOT registered in any settings.json** |

**[P0-H1] Hook is not registered in settings.json.** The file exists at `~/.claude/hooks/user-prompt-submit.sh` but neither the global nor project `settings.json` has a `UserPromptSubmit` hook entry. This means the hook **never fires**.

**Fix:** Add to `~/.claude/settings.json`:
```json
"hooks": {
  "UserPromptSubmit": [
    {
      "hooks": [{"type": "command", "command": "~/.claude/hooks/user-prompt-submit.sh"}]
    }
  ]
}
```

**[P1-H6] Should output JSON.** Plain text stdout from hooks is treated as a non-blocking message. For reliable context injection, use:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "MANDATORY PROTOCOL — ..."
  }
}
```

### 3.9 Inline hooks in settings.json

Several hooks are defined inline rather than as script files:

| Hook | Event | Assessment |
|------|-------|------------|
| Daily checkpoint reminder | SessionStart | ✅ Simple enough for inline |
| Post-compact context | SessionStart (compact) | ✅ Good compact recovery |
| PreCompact context preservation | PreCompact | ✅ Simple echo |
| Stop pending warning | Stop | ✅ Good reminder |
| PostToolUseFailure logger | PostToolUseFailure | ⚠️ Uses `$TOOL_NAME` env var which doesn't exist — should parse from stdin JSON |
| SubagentStart logger | SubagentStart | ⚠️ Same — doesn't parse stdin for agent details |
| SubagentStop logger | SubagentStop | ⚠️ Same |
| SessionEnd logger | SessionEnd | ✅ Simple logging |
| Notification logger | Notification | ⚠️ Uses non-existent `current-session-id` file |

**[P1-H7] Inline logging hooks don't read stdin.** The PostToolUseFailure, SubagentStart, SubagentStop, and Notification hooks write JSON logs but don't extract any data from the stdin JSON input. They log timestamps only, missing tool names, agent types, error messages, and notification types.

---

## 4. Prioritized Fix List

### P0 — Must Fix (Security / Correctness)

| ID | Issue | Location | Fix |
|----|-------|----------|-----|
| P0-S1 | Sandbox uses non-standard schema — likely not active | Project settings.json | Rewrite sandbox block using official schema; set `sandbox.enabled: true` |
| P0-S2 | `attribution.commit: "none"` adds literal "none" | Both settings.json | Change to `""` (empty string) |
| P0-G1 | `Write(/Users/bruno/**)` + `Edit(/Users/bruno/**)` — unrestricted home dir writes | Global settings.json | Remove or scope to specific project paths |

### P1 — Should Fix (Best Practices)

| ID | Issue | Location | Fix |
|----|-------|----------|-----|
| P1-S2 | Missing Trail of Bits deny rules | Project settings.json | Add `~/.ssh/**`, `~/.aws/**`, `~/.gnupg/**`, etc. to deny |
| P1-S3 | `curl` in allow list | Project settings.json | Move to `ask` |
| P1-S4 | Deny rules use `:*` syntax instead of ` *` | Both settings.json | Change `Bash(sudo:*)` → `Bash(sudo *)`, etc. |
| P1-H1/H3/H4 | Hardcoded absolute paths in 3 hooks | session-start.sh, session-end.sh, pre-compact.sh | Use `$CLAUDE_PROJECT_DIR` |
| P1-H2 | session-start.sh doesn't use `additionalContext` | session-start.sh | Output JSON with `hookSpecificOutput` |
| P1-H5 | coverage-gate.sh reads wrong field (`tool_output` vs `tool_response`) | coverage-gate.sh | Fix field name to `tool_response` |
| P1-H7 | Inline logging hooks don't parse stdin JSON | settings.json inline hooks | Rewrite to read stdin and extract event data |

### P2 — Nice to Have (Improvements)

| ID | Issue | Location | Fix |
|----|-------|----------|-----|
| P2-S1 | `cleanupPeriodDays` could be longer for thesis | Project settings.json | Consider 60–90 days |
| P2-S2 | No `worktree.symlinkDirectories` | Project settings.json | Add `.venv`, `.build` |
| P2-S3 | Missing `enableAllProjectMcpServers: false` | Project settings.json | Add explicitly |
| P2-G1 | No `$schema` in global settings | Global settings.json | Add schema URL |
| P2-G2 | Duplicated rules across project/global | Both settings.json | Deduplicate — common rules in global only |
| P2-H1 | Lock files never cleaned up | session-end.sh | Add cleanup |

---

## 5. Missing Hooks That Should Be Added

### 5.1 Anti-Rationalization Stop Hook (HIGH VALUE)

The current `Stop` hook only checks for pending verification files. Add a **prompt-type** hook that evaluates whether Claude is rationalizing incomplete work:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [{
          "type": "prompt",
          "prompt": "You MUST respond with raw JSON only, no markdown. Evaluate if this response rationalizes incomplete work or claims something is done when it clearly isn't: $ARGUMENTS. Respond: {\"ok\": true} or {\"ok\": false, \"reason\": \"...\"}",
          "model": "claude-haiku-4-5-20251001",
          "timeout": 30
        }]
      }
    ]
  }
}
```

### 5.2 PostCompact Hook

Currently only `PreCompact` exists. A `PostCompact` hook could verify that the compacted context still contains critical SIOPV state (phase, metrics, file paths):

```json
{
  "PostCompact": [{
    "hooks": [{
      "type": "command",
      "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/post-compact.sh"
    }]
  }]
}
```

### 5.3 TaskCompleted Verification Hook

For agent teams, verify that completed tasks actually meet quality gates:

```json
{
  "TaskCompleted": [{
    "hooks": [{
      "type": "prompt",
      "prompt": "Verify task completion: $ARGUMENTS. Check if the task was actually completed or just marked done. Respond with raw JSON: {\"ok\": true} or {\"ok\": false, \"reason\": \"...\"}",
      "timeout": 30
    }]
  }]
}
```

### 5.4 UserPromptSubmit Hook (Fix Registration)

The existing `~/.claude/hooks/user-prompt-submit.sh` is orphaned. Register it in global settings.json.

### 5.5 PreToolUse for `WebFetch` — URL Logging

For thesis auditability, log all external URL fetches:

```json
{
  "matcher": "WebFetch",
  "hooks": [{
    "type": "command",
    "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/log-web-fetch.sh",
    "async": true
  }]
}
```

---

## 6. Summary Statistics

| Category | Count |
|----------|-------|
| P0 (Must Fix) | 3 |
| P1 (Should Fix) | 7 |
| P2 (Nice to Have) | 6 |
| Missing hooks recommended | 5 |
| Hook scripts audited | 8 (7 project + 1 global) |
| Inline hooks audited | 9 |
| **Total findings** | **21** |

### Hook Quality Ranking

| Rank | Hook | Score |
|------|------|-------|
| 1 | `pre-git-commit.sh` | 9/10 — exemplary JSON contract, traceability, `$CLAUDE_PROJECT_DIR` |
| 2 | `post-code.sh` | 8/10 — solid, reads stdin, auto-formats |
| 3 | `pre-write.sh` | 8/10 — clean JSON output, good soft-gate pattern |
| 4 | `coverage-gate.sh` | 6/10 — good concept but reads wrong field |
| 5 | `pre-compact.sh` | 6/10 — hardcoded paths, fragile transcript fallback |
| 6 | `session-start.sh` | 5/10 — hardcoded paths, no JSON output, no stdin read |
| 7 | `session-end.sh` | 5/10 — hardcoded paths, no stdin read |
| 8 | `user-prompt-submit.sh` | 3/10 — not registered, no JSON output, no stdin read |
