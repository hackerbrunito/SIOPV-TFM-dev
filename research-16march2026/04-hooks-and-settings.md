# Claude Code Hooks & settings.json — Research Findings (March 2026)

> **Researcher:** claude-code-research agent
> **Date:** 2026-03-16
> **Sources:** Official Claude Code docs, GitHub repos, community guides

---

## Table of Contents

1. [settings.json Full Schema](#1-settingsjson-full-schema)
2. [Hook Event Types](#2-hook-event-types)
3. [Hook Script Format (stdin/stdout JSON Contract)](#3-hook-script-format)
4. [Hook Configuration: settings.json vs Inline](#4-hook-configuration)
5. [Permission Rules (allow / ask / deny)](#5-permission-rules)
6. [New Settings (2025–2026)](#6-new-settings-2025-2026)
7. [autoApprove / dangerouslySkipPermissions](#7-autoapprove--dangerouslyskippermissions)
8. [Model Selection Settings](#8-model-selection-settings)
9. [MCP Server Configuration](#9-mcp-server-configuration)
10. [Best Practices for Hook Scripts](#10-best-practices-for-hook-scripts)

---

## 1. settings.json Full Schema

**Official JSON Schema:** `https://json.schemastore.org/claude-code-settings.json`

Add `"$schema": "https://json.schemastore.org/claude-code-settings.json"` to enable IDE autocomplete and validation.

### Configuration Scopes (Priority Order, highest first)

| Scope | Location | Who it affects | Shared? |
|-------|----------|----------------|---------|
| **Managed** | System-level `managed-settings.json`, plist, or registry | All users on machine | Yes (IT-deployed) |
| **User** | `~/.claude/settings.json` | You, across all projects | No |
| **Project** | `.claude/settings.json` | All collaborators | Yes (committed) |
| **Local** | `.claude/settings.local.json` | You, this repo only | No (gitignored) |

### Complete Available Settings

| Key | Description | Example |
|-----|-------------|---------|
| `$schema` | JSON schema URL for IDE validation | `"https://json.schemastore.org/claude-code-settings.json"` |
| `apiKeyHelper` | Script to generate auth value (X-Api-Key / Bearer) | `"/bin/generate_temp_api_key.sh"` |
| `autoMemoryDirectory` | Custom auto-memory storage dir (not in project scope) | `"~/my-memory-dir"` |
| `cleanupPeriodDays` | Session cleanup period (default: 30). `0` = delete all | `20` |
| `companyAnnouncements` | Startup announcements (array, random cycle) | `["Welcome to Acme Corp!"]` |
| `env` | Environment variables applied to every session | `{"FOO": "bar"}` |
| `attribution` | Customize git/PR attribution | `{"commit": "...", "pr": ""}` |
| `includeCoAuthoredBy` | **Deprecated** — use `attribution` | `false` |
| `includeGitInstructions` | Include built-in git workflow instructions (default: true) | `false` |
| `permissions` | Permission rules object (see Section 5) | `{"allow": [...], "deny": [...]}` |
| `hooks` | Hook configuration (see Section 2) | See hooks section |
| `disableAllHooks` | Disable all hooks and custom status line | `true` |
| `allowManagedHooksOnly` | **(Managed only)** Block user/project/plugin hooks | `true` |
| `allowedHttpHookUrls` | URL allowlist for HTTP hooks (wildcard `*` supported) | `["https://hooks.example.com/*"]` |
| `httpHookAllowedEnvVars` | Env var allowlist for HTTP hook headers | `["MY_TOKEN", "HOOK_SECRET"]` |
| `allowManagedPermissionRulesOnly` | **(Managed only)** Block user/project permission rules | `true` |
| `allowManagedMcpServersOnly` | **(Managed only)** Only admin-allowed MCP servers | `true` |
| `model` | Override default model | `"claude-sonnet-4-6"` or `"opus"` |
| `availableModels` | Restrict model picker options | `["sonnet", "haiku"]` |
| `modelOverrides` | Map Anthropic model IDs to provider-specific IDs | `{"claude-opus-4-6": "arn:aws:bedrock:..."}` |
| `effortLevel` | Persist effort level across sessions | `"low"`, `"medium"`, `"high"` |
| `otelHeadersHelper` | Script to generate OpenTelemetry headers | `"/bin/generate_otel_headers.sh"` |
| `statusLine` | Custom status line configuration | `{"type": "command", "command": "..."}` |
| `fileSuggestion` | Custom `@` file autocomplete command | `{"type": "command", "command": "..."}` |
| `respectGitignore` | `@` picker respects .gitignore (default: true) | `false` |
| `outputStyle` | Output style adjustment | `"Explanatory"` |
| `forceLoginMethod` | Restrict login to `claudeai` or `console` | `"claudeai"` |
| `forceLoginOrgUUID` | Auto-select org during login | `"xxxxxxxx-xxxx-..."` |
| `enableAllProjectMcpServers` | Auto-approve all project .mcp.json servers | `true` |
| `enabledMcpjsonServers` | Specific MCP servers to approve | `["memory", "github"]` |
| `disabledMcpjsonServers` | Specific MCP servers to reject | `["filesystem"]` |
| `allowedMcpServers` | **(Managed)** MCP server allowlist | `[{"serverName": "github"}]` |
| `deniedMcpServers` | **(Managed)** MCP server denylist | `[{"serverName": "filesystem"}]` |
| `strictKnownMarketplaces` | **(Managed)** Plugin marketplace allowlist | `[{"source": "github", "repo": "..."}]` |
| `blockedMarketplaces` | **(Managed)** Plugin marketplace blocklist | `[{"source": "github", "repo": "..."}]` |
| `pluginTrustMessage` | **(Managed)** Custom plugin trust warning | `"All plugins from our marketplace are vetted"` |
| `awsAuthRefresh` | AWS SSO refresh script | `"aws sso login --profile myprofile"` |
| `awsCredentialExport` | AWS credential export script | `"/bin/generate_aws_grant.sh"` |
| `alwaysThinkingEnabled` | Enable extended thinking by default | `true` |
| `plansDirectory` | Custom plan file storage location | `"./plans"` |
| `showTurnDuration` | Show "Cooked for Xm Ys" messages | `true` |
| `spinnerVerbs` | Customize spinner action verbs | `{"mode": "append", "verbs": ["Pondering"]}` |
| `language` | Preferred response language | `"japanese"` |
| `autoUpdatesChannel` | Release channel: `"stable"` or `"latest"` | `"stable"` |
| `spinnerTipsEnabled` | Show tips in spinner (default: true) | `false` |
| `spinnerTipsOverride` | Custom spinner tips | `{"excludeDefault": true, "tips": [...]}` |
| `terminalProgressBarEnabled` | Terminal progress bar (default: true) | `false` |
| `prefersReducedMotion` | Reduce UI animations for accessibility | `true` |
| `fastModePerSessionOptIn` | Require `/fast` each session | `true` |
| `teammateMode` | Agent team display: `auto`, `in-process`, `tmux` | `"in-process"` |
| `feedbackSurveyRate` | Survey probability 0–1 | `0.05` |

### Worktree Settings

| Key | Description | Example |
|-----|-------------|---------|
| `worktree.symlinkDirectories` | Directories to symlink from main repo | `["node_modules", ".cache"]` |
| `worktree.sparsePaths` | Sparse checkout paths (cone mode) | `["packages/my-app"]` |

### Sandbox Settings

| Key | Description | Example |
|-----|-------------|---------|
| `sandbox.enabled` | Enable bash sandboxing (default: false) | `true` |
| `sandbox.autoAllowBashIfSandboxed` | Auto-approve bash when sandboxed (default: true) | `true` |
| `sandbox.excludedCommands` | Commands that run outside sandbox | `["git", "docker"]` |
| `sandbox.allowUnsandboxedCommands` | Allow `dangerouslyDisableSandbox` param (default: true) | `false` |
| `sandbox.filesystem.allowWrite` | Additional writable paths | `["//tmp/build", "~/.kube"]` |
| `sandbox.filesystem.denyWrite` | Blocked write paths | `["//etc"]` |
| `sandbox.filesystem.denyRead` | Blocked read paths | `["~/.aws/credentials"]` |
| `sandbox.network.allowUnixSockets` | Allowed Unix socket paths | `["~/.ssh/agent-socket"]` |
| `sandbox.network.allowAllUnixSockets` | Allow all Unix sockets (default: false) | `true` |
| `sandbox.network.allowLocalBinding` | Allow localhost port binding (macOS, default: false) | `true` |
| `sandbox.network.allowedDomains` | Allowed outbound domains (wildcard `*`) | `["github.com", "*.npmjs.org"]` |
| `sandbox.network.allowManagedDomainsOnly` | **(Managed)** Only managed domains apply | `true` |
| `sandbox.network.httpProxyPort` | Custom HTTP proxy port | `8080` |
| `sandbox.network.socksProxyPort` | Custom SOCKS5 proxy port | `8081` |
| `sandbox.enableWeakerNestedSandbox` | Weaker sandbox for Docker (Linux/WSL2) | `true` |
| `sandbox.enableWeakerNetworkIsolation` | Allow TLS trust service access (macOS) | `true` |

### Sandbox Path Prefixes

| Prefix | Meaning | Example |
|--------|---------|---------|
| `//` | Absolute path from filesystem root | `//tmp/build` → `/tmp/build` |
| `~/` | Home directory relative | `~/.kube` → `$HOME/.kube` |
| `/` | Settings file directory relative | `/build` → `$SETTINGS_DIR/build` |
| `./` or none | Relative path | `./output` |

---

## 2. Hook Event Types

Claude Code supports **25+ hook events** across session, tool, agent, compaction, and worktree lifecycle points.

### Complete Event Reference

| Event | When it fires | Matcher support | Can block? | Hook types |
|-------|---------------|-----------------|------------|------------|
| **SessionStart** | New session or resume | `startup`, `resume`, `clear`, `compact` | No | Command only |
| **SessionEnd** | Session terminates | `clear`, `logout`, `prompt_input_exit`, `bypass_permissions_disabled`, `other` | No | Command only |
| **InstructionsLoaded** | CLAUDE.md / rules loaded | No matcher | No | Command only |
| **ConfigChange** | Config file changes during session | `user_settings`, `project_settings`, `local_settings`, `policy_settings`, `skills` | Yes (except `policy_settings`) | Command only |
| **UserPromptSubmit** | User submits prompt before Claude processes | No matcher | Yes | All types |
| **PreToolUse** | Before tool execution | Tool names: `Bash`, `Edit`, `Write`, `Read`, `Glob`, `Grep`, `Agent`, `WebFetch`, `WebSearch`, `mcp__*` | Yes | All types |
| **PermissionRequest** | Permission dialog about to show | Tool names (same as PreToolUse) | Yes | All types |
| **PostToolUse** | After successful tool execution | Tool names | No (tool already ran) | All types |
| **PostToolUseFailure** | After tool failure | Tool names | No | All types |
| **Stop** | Main Claude agent finishes responding | No matcher | Yes | All types |
| **SubagentStart** | Subagent spawned | Agent type: `Bash`, `Explore`, `Plan`, custom | No | Command only |
| **SubagentStop** | Subagent finishes | Agent type | Yes | All types |
| **TeammateIdle** | Agent team teammate going idle | No matcher | Yes (exit 2 = continue) | Command only |
| **TaskCompleted** | Task marked complete | No matcher | Yes (exit 2 = not done) | All types |
| **Notification** | Claude sends notifications | `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog` | No | Command only |
| **PreCompact** | Before context compaction | `manual`, `auto` | No | Command only |
| **PostCompact** | After compaction completes | `manual`, `auto` | No | Command only |
| **WorktreeCreate** | Creating worktree | No matcher | Yes | Command only |
| **WorktreeRemove** | Removing worktree | No matcher | No | Command only |
| **Elicitation** | MCP server requests user input | MCP server name | Yes | Command only |
| **ElicitationResult** | User responds to elicitation | MCP server name | Yes | Command only |

### Hook Types

| Type | Description | Supports events |
|------|-------------|-----------------|
| `command` | Shell command, receives JSON on stdin | All events |
| `http` | HTTP POST to endpoint | PreToolUse, PostToolUse, PostToolUseFailure, PermissionRequest, UserPromptSubmit, Stop, SubagentStop, TaskCompleted |
| `prompt` | LLM evaluation (fast model) | Same as http |
| `agent` | Agentic verifier with tool access | Same as http |

### Default Timeouts

| Type | Default timeout |
|------|----------------|
| `command` | 600 seconds |
| `prompt` | 30 seconds |
| `agent` | 60 seconds |
| `SessionEnd` | 1.5 seconds (configurable via `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS`) |

---

## 3. Hook Script Format

### Configuration Structure

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "regex_pattern_or_*",
        "hooks": [
          {
            "type": "command",
            "command": "path/to/script.sh",
            "timeout": 600,
            "statusMessage": "Custom spinner text",
            "async": false
          }
        ]
      }
    ]
  }
}
```

### Common Input Fields (JSON on stdin for commands, POST body for HTTP)

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/dir",
  "permission_mode": "default|plan|acceptEdits|dontAsk|bypassPermissions",
  "hook_event_name": "PreToolUse",
  "agent_id": "agent-123",
  "agent_type": "Explore"
}
```

### Event-Specific Input Fields

**PreToolUse** adds:
```json
{
  "tool_name": "Bash",
  "tool_use_id": "toolu_01ABC123...",
  "tool_input": {
    "command": "npm test",
    "description": "Run tests",
    "timeout": 120000,
    "run_in_background": false
  }
}
```

**PostToolUse** adds:
```json
{
  "tool_name": "Write",
  "tool_input": { "file_path": "...", "content": "..." },
  "tool_response": { "filePath": "...", "success": true },
  "tool_use_id": "toolu_01ABC123..."
}
```

**PostToolUseFailure** adds:
```json
{
  "tool_name": "Bash",
  "tool_input": { ... },
  "error": "Command exited with non-zero status code 1",
  "is_interrupt": false
}
```

**Stop / SubagentStop** adds:
```json
{
  "stop_hook_active": false,
  "last_assistant_message": "I've completed the refactoring..."
}
```

**SessionStart** adds:
```json
{
  "source": "startup|resume|clear|compact",
  "model": "claude-sonnet-4-6",
  "agent_type": "optional_agent_name"
}
```

**TaskCompleted** adds:
```json
{
  "task_id": "task-001",
  "task_subject": "Implement user authentication",
  "task_description": "...",
  "teammate_name": "implementer",
  "team_name": "my-project"
}
```

**InstructionsLoaded** adds:
```json
{
  "file_path": "/path/to/CLAUDE.md",
  "memory_type": "User|Project|Local|Managed",
  "load_reason": "session_start|nested_traversal|path_glob_match|include",
  "globs": ["*.ts"],
  "trigger_file_path": "...",
  "parent_file_path": "..."
}
```

### Exit Code Semantics

| Exit Code | Meaning | JSON Processing |
|-----------|---------|-----------------|
| **0** | Success | stdout parsed as JSON |
| **2** | **Blocking error** | stdout ignored; stderr fed to Claude as error |
| **Other** | Non-blocking error | Ignored, execution continues |

### Output JSON Contract

**Universal fields** (all events):
```json
{
  "continue": true,
  "stopReason": "message when continue=false",
  "suppressOutput": false,
  "systemMessage": "warning text shown to user"
}
```

**PreToolUse output** (via `hookSpecificOutput`):
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|deny|ask",
    "permissionDecisionReason": "Explanation text",
    "updatedInput": { "command": "modified command" },
    "additionalContext": "context injected into Claude"
  }
}
```

**PermissionRequest output**:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {
      "behavior": "allow|deny",
      "updatedInput": { "command": "..." },
      "updatedPermissions": [ ... ]
    }
  }
}
```

**PostToolUse / Stop / UserPromptSubmit output** (via top-level `decision`):
```json
{
  "decision": "block",
  "reason": "Explanation"
}
```

**SessionStart output** (inject context):
```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "text added to Claude's context"
  }
}
```

**Elicitation output** (auto-respond to MCP prompts):
```json
{
  "hookSpecificOutput": {
    "hookEventName": "Elicitation",
    "action": "accept|decline|cancel",
    "content": { "username": "alice" }
  }
}
```

### HTTP Hook Specifics

- HTTP hooks receive the same JSON as POST body
- **2xx + empty body** → success (exit 0 equivalent)
- **2xx + plain text** → success, text added as context
- **2xx + JSON** → parsed like command hook output
- **Non-2xx / connection failure** → non-blocking error
- HTTP hooks **cannot** signal blocking via status codes — must use JSON decision fields

### Prompt Hook Response Format

```json
{
  "ok": true,
  "reason": "Explanation if ok=false"
}
```

> **Critical:** Prompt hooks must explicitly instruct the evaluator model to respond with raw JSON only, or it wraps output in markdown, breaking JSON parsing.

### Environment Variables Available in Hooks

| Variable | Description | Scope |
|----------|-------------|-------|
| `CLAUDE_PROJECT_DIR` | Project root directory | All hooks |
| `CLAUDE_PLUGIN_ROOT` | Plugin root (for plugin scripts) | Plugin hooks |
| `CLAUDE_ENV_FILE` | Path to env file for persisting vars | SessionStart only |
| `CLAUDE_CODE_REMOTE` | `"true"` in web environments | All hooks |
| `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS` | SessionEnd timeout override | SessionEnd |

---

## 4. Hook Configuration

### Location Priority (highest first)

1. **Managed policy settings** (organization-wide)
2. **Plugin hooks** (`hooks/hooks.json`)
3. **Project local** (`.claude/settings.local.json`)
4. **Project** (`.claude/settings.json`)
5. **User** (`~/.claude/settings.json`)
6. **Skill/Agent frontmatter** (component-scoped)

### Matcher Patterns by Event

| Event | Matches On | Examples |
|-------|-----------|---------|
| PreToolUse / PostToolUse / PostToolUseFailure / PermissionRequest | Tool name | `Bash`, `Edit\|Write`, `mcp__.*` |
| SessionStart | Session source | `startup`, `resume`, `clear`, `compact` |
| SessionEnd | Exit reason | `clear`, `logout`, `prompt_input_exit` |
| Notification | Type | `permission_prompt`, `idle_prompt` |
| SubagentStart / SubagentStop | Agent type | `Bash`, `Explore`, `Plan` |
| PreCompact / PostCompact | Trigger | `manual`, `auto` |
| ConfigChange | Config source | `user_settings`, `project_settings` |
| UserPromptSubmit / Stop / others | No matcher | Always fires |

Use `"*"`, `""`, or **omit** `matcher` to match all.

### MCP Tool Name Pattern

MCP tools follow: `mcp__<server>__<tool>`

```json
{
  "matcher": "mcp__memory__.*",
  "hooks": [{ "type": "command", "command": "log-memory-ops.sh" }]
}
```

### Async Hooks

```json
{
  "type": "command",
  "command": "long-running-task.sh",
  "async": true
}
```

Async hooks run in background without blocking. Response fields have no effect.

### Disabling Hooks

- **Temporarily disable all:** `"disableAllHooks": true` in settings
- **Enterprise block:** `"allowManagedHooksOnly": true` in managed settings (user `disableAllHooks` cannot override managed hooks)
- **View configured hooks:** `/hooks` command in REPL

---

## 5. Permission Rules

### Structure

```json
{
  "permissions": {
    "allow": [ "Bash(npm run lint)", "Bash(npm run test *)", "Read(~/.zshrc)" ],
    "ask": [ "Bash(git push *)" ],
    "deny": [ "Bash(curl *)", "Read(./.env)", "Read(./secrets/**)" ],
    "additionalDirectories": [ "../docs/" ],
    "defaultMode": "acceptEdits",
    "disableBypassPermissionsMode": "disable"
  }
}
```

### Evaluation Order

**deny → ask → allow** (first match wins)

### Rule Syntax

| Rule | Effect |
|------|--------|
| `Bash` | Matches all Bash commands |
| `Bash(npm run *)` | Matches commands starting with `npm run` |
| `Read(./.env)` | Matches reading `.env` file |
| `Read(./.env.*)` | Wildcard extension matching |
| `Read(./secrets/**)` | Recursive directory matching |
| `WebFetch(domain:example.com)` | Domain-based URL matching |
| `Edit(path/to/file)` | Edit permission for specific file |
| `mcp__server__tool` | Specific MCP tool |

### Merge Behavior

Array settings (`allow`, `deny`, `ask`) **merge across scopes** — they concatenate and deduplicate rather than replace. Lower-priority scopes add entries without overriding higher-priority ones.

### Permission Modes

| Mode | Description |
|------|-------------|
| `default` | Ask for most operations |
| `acceptEdits` | Auto-approve file edits, ask for bash |
| `dontAsk` | Auto-approve most operations |
| `plan` | Plan mode — require approval before execution |
| `bypassPermissions` | Skip all permission prompts (requires `--dangerously-skip-permissions`) |

### Known Issue (as of early 2026)

> **Warning:** There have been documented reports (GitHub issue #6699) that `deny` rules in settings.json may not be reliably enforced in certain versions. The recommended workaround is to use **PreToolUse hooks** with exit code 2 for critical blocking needs, as hooks enforce at the process level.

### Trail of Bits Recommended Deny Rules

```json
{
  "permissions": {
    "deny": [
      "Read(~/.ssh/**)", "Read(~/.gnupg/**)",
      "Read(~/.aws/**)", "Read(~/.azure/**)", "Read(~/.kube/**)",
      "Read(~/.docker/config.json)",
      "Read(~/.npmrc)", "Read(~/.pypirc)", "Read(~/.gem/credentials)",
      "Read(~/.git-credentials)", "Read(~/.config/gh/**)",
      "Edit(~/.bashrc)", "Edit(~/.zshrc)",
      "Read(./.env)", "Read(./.env.*)", "Read(./secrets/**)"
    ]
  }
}
```

---

## 6. New Settings (2025–2026)

### Settings Added or Updated in 2025–2026

| Setting | When Added | Description |
|---------|-----------|-------------|
| `effortLevel` | 2026 | Persist adaptive reasoning level (`low`/`medium`/`high`) across sessions. Supported on Opus 4.6 and Sonnet 4.6. |
| `availableModels` | 2026 | Enterprise restriction on model picker options |
| `modelOverrides` | 2026 | Map Anthropic model IDs to provider-specific IDs (Bedrock ARNs, Vertex names, Foundry deployments) |
| `sandbox.*` | Late 2025 | Full sandboxing subsystem: filesystem/network isolation at OS level |
| `allowManagedHooksOnly` | 2025 | Enterprise: block all non-managed hooks |
| `allowManagedPermissionRulesOnly` | 2025 | Enterprise: block user/project permission rules |
| `allowManagedMcpServersOnly` | 2025 | Enterprise: only admin-allowed MCP servers |
| `allowedHttpHookUrls` | 2026 | URL allowlist for HTTP hooks |
| `httpHookAllowedEnvVars` | 2026 | Env var allowlist for HTTP hook headers |
| `attribution` | 2025 | Replace deprecated `includeCoAuthoredBy` |
| `fastModePerSessionOptIn` | 2026 | Require `/fast` each session |
| `teammateMode` | 2026 | Agent team display mode |
| `statusLine` | 2025 | Custom status line commands |
| `fileSuggestion` | 2025 | Custom `@` file autocomplete |
| `outputStyle` | 2025 | Output style adjustments |
| `autoUpdatesChannel` | 2025 | `"stable"` vs `"latest"` release channel |
| `worktree.*` | 2026 | Worktree management settings |
| `spinnerVerbs` | 2025 | Customize spinner action verbs |
| `spinnerTipsEnabled` / `spinnerTipsOverride` | 2025 | Control spinner tips |
| `language` | 2025 | Preferred response language |
| `feedbackSurveyRate` | 2026 | Enterprise survey control |
| `strictKnownMarketplaces` / `blockedMarketplaces` | 2026 | Managed marketplace controls |
| `pluginTrustMessage` | 2026 | Managed plugin trust warning |
| `prefersReducedMotion` | 2025 | Accessibility animations control |
| `plansDirectory` | 2026 | Custom plan file storage |
| `autoMemoryDirectory` | 2025 | Custom auto-memory storage |
| `showTurnDuration` | 2025 | Show turn duration messages |

### New Hook Types (2025–2026)

| Type | When Added | Description |
|------|-----------|-------------|
| `http` | 2025 | HTTP POST hooks with authentication headers |
| `prompt` | 2025 | LLM-evaluated hooks using fast models |
| `agent` | 2026 | Agentic verifier hooks with tool access |

### New Hook Events (2025–2026)

| Event | When Added | Description |
|-------|-----------|-------------|
| `InstructionsLoaded` | 2026 | Fired when CLAUDE.md / rules loaded |
| `ConfigChange` | 2026 | Config file changes during session |
| `PermissionRequest` | 2026 | Permission dialog about to show |
| `PostToolUseFailure` | 2025 | After tool execution failure |
| `TaskCompleted` | 2026 | Task marked complete (agent teams) |
| `TeammateIdle` | 2026 | Agent team teammate going idle |
| `Elicitation` / `ElicitationResult` | 2026 | MCP elicitation handling |

---

## 7. autoApprove / dangerouslySkipPermissions

### Permission Modes

| Mode | CLI Flag | Effect |
|------|----------|--------|
| `default` | (none) | Standard permission prompting |
| `acceptEdits` | `--allowedTools Edit,Write,...` | Auto-approve file edits |
| `bypassPermissions` | `--dangerously-skip-permissions` | Skip ALL permission prompts |

### `--dangerously-skip-permissions`

- Enables `bypassPermissions` mode for the session
- Required for `mode: "bypassPermissions"` in Agent tool to work
- Forces Opus model when used with Agent `bypassPermissions` mode
- Can be disabled enterprise-wide via `disableBypassPermissionsMode: "disable"` in managed settings

### `defaultMode` in settings.json

```json
{
  "permissions": {
    "defaultMode": "acceptEdits"
  }
}
```

Sets the default permission mode when opening Claude Code. Valid values: `"default"`, `"plan"`, `"acceptEdits"`, `"dontAsk"`, `"bypassPermissions"`.

### Important Caveats

1. **`bypassPermissions` in Agent tool only works** when the parent session was started with `--dangerously-skip-permissions`
2. Without that session-level flag, the `mode` parameter on Agent has no permission effect
3. `bypassPermissions` forces the **Opus model** regardless of parent session model
4. For agent autonomy with specific models, use custom agent files with `model: sonnet` in frontmatter and `mode: "acceptEdits"`

### Trail of Bits Approach

Rather than relying on permission prompts, Trail of Bits recommends:
1. Enable **sandboxing** (`sandbox.enabled: true`)
2. Run with `--dangerously-skip-permissions`
3. Use **deny rules** and **PreToolUse hooks** for critical safety
4. OS-level isolation (Seatbelt/bubblewrap) provides the real security boundary

---

## 8. Model Selection Settings

### Available Model IDs (as of March 2026)

| Alias | Full Model ID | Notes |
|-------|---------------|-------|
| `default` | Depends on plan tier | Max/Team Premium → Opus 4.6, Pro/Team Standard → Sonnet 4.6 |
| `sonnet` | `claude-sonnet-4-6` | Latest Sonnet — daily driver |
| `opus` | `claude-opus-4-6` | Complex reasoning, 1M tokens |
| `haiku` | `claude-haiku-4-5-20251001` | Fast, efficient, budget tasks |
| `sonnet[1m]` | Sonnet with 1M context window | Extended context |
| `opus[1m]` | Opus with 1M context window | Extended context |
| `opusplan` | Opus in plan mode, Sonnet in execution | Hybrid approach |

### Legacy Model IDs (still valid)

| Model ID | Notes |
|----------|-------|
| `claude-opus-4-5-20251101` | Previous generation Opus |
| `claude-sonnet-4-5-20250929` | Previous generation Sonnet |

### Configuration Methods (priority order)

1. **During session:** `/model <alias|name>`
2. **At startup:** `claude --model <alias|name>`
3. **Environment variable:** `ANTHROPIC_MODEL=<alias|name>`
4. **Settings file:** `"model": "opus"` in settings.json

### Model Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_MODEL` | Override model for session |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | Model for `opus` alias / `opusplan` plan mode |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | Model for `sonnet` alias / `opusplan` execution |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | Model for `haiku` alias / background tasks |
| `CLAUDE_CODE_SUBAGENT_MODEL` | Model for subagents |

### Effort Levels

| Level | Description |
|-------|-------------|
| `low` | Faster, cheaper for straightforward tasks |
| `medium` | Default for Opus 4.6 (Max/Team) |
| `high` | Deeper reasoning for complex problems |
| `max` | Deepest reasoning, no token constraint (Opus 4.6 only, current session only) |
| `auto` | Reset to model default |

**Configure via:** `/effort`, `/model` slider, `--effort` flag, `CLAUDE_CODE_EFFORT_LEVEL` env var, or `"effortLevel"` in settings.

### Prompt Caching Controls

| Variable | Description |
|----------|-------------|
| `DISABLE_PROMPT_CACHING` | Disable for all models |
| `DISABLE_PROMPT_CACHING_HAIKU` | Disable for Haiku only |
| `DISABLE_PROMPT_CACHING_SONNET` | Disable for Sonnet only |
| `DISABLE_PROMPT_CACHING_OPUS` | Disable for Opus only |

### Extended Context (1M tokens)

- Opus 4.6 auto-upgraded to 1M on Max/Team/Enterprise plans
- Sonnet 4.6 requires extra usage on most plans
- Disable with `CLAUDE_CODE_DISABLE_1M_CONTEXT=1`
- Standard pricing (no premium beyond 200K)

### Adaptive Reasoning Control

To disable adaptive reasoning and revert to fixed thinking budget:
```
CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1
```
When disabled, uses fixed budget controlled by `MAX_THINKING_TOKENS`.

---

## 9. MCP Server Configuration

### Configuration Locations

| Scope | File | Who sees it |
|-------|------|-------------|
| **Local** (default) | `~/.claude.json` (under project path) | You, this project |
| **Project** | `.mcp.json` (repo root) | All collaborators |
| **User** | `~/.claude.json` (global) | You, all projects |
| **Managed** | System `managed-mcp.json` | All users on machine |

> **Important:** MCP servers are configured in `~/.claude.json` and `.mcp.json`, **not** in `~/.claude/settings.json`.

### Managed MCP Locations

| OS | Path |
|----|------|
| macOS | `/Library/Application Support/ClaudeCode/managed-mcp.json` |
| Linux/WSL | `/etc/claude-code/managed-mcp.json` |
| Windows | `C:\Program Files\ClaudeCode\managed-mcp.json` |

### Configuration Format

```json
{
  "mcpServers": {
    "server-name": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "some-package"],
      "env": { "API_KEY": "${API_KEY}" }
    }
  }
}
```

### Transport Types

| Type | Usage | Example |
|------|-------|---------|
| `stdio` | Local processes | `npx -y @some/package` |
| `http` | Remote HTTP (recommended) | `https://mcp.notion.com/mcp` |
| `sse` | Remote SSE (**deprecated**) | `https://api.example.com/sse` |

### CLI Management

```bash
# Add servers
claude mcp add --transport http notion https://mcp.notion.com/mcp
claude mcp add --transport stdio db -- npx -y @bytebase/dbhub --dsn "..."
claude mcp add-json weather '{"type":"http","url":"https://..."}'

# Manage servers
claude mcp list
claude mcp get <name>
claude mcp remove <name>

# Import from Claude Desktop
claude mcp add-from-claude-desktop
```

### Environment Variable Expansion in .mcp.json

Supports `${VAR}` and `${VAR:-default}` in `command`, `args`, `env`, `url`, `headers`.

### MCP-Related Settings in settings.json

| Setting | Description |
|---------|-------------|
| `enableAllProjectMcpServers` | Auto-approve all .mcp.json servers |
| `enabledMcpjsonServers` | Specific servers to approve |
| `disabledMcpjsonServers` | Specific servers to reject |
| `allowManagedMcpServersOnly` | **(Managed)** Only admin-allowed servers |
| `allowedMcpServers` | **(Managed)** Server allowlist |
| `deniedMcpServers` | **(Managed)** Server denylist |

### Managed MCP Controls

`allowedMcpServers` entries can match by:
- `serverName` — configured server name
- `serverCommand` — exact command + args array (stdio only)
- `serverUrl` — URL pattern with wildcards (remote only)

**Denylist always takes precedence over allowlist.**

### Key Environment Variables

| Variable | Description |
|----------|-------------|
| `MCP_TIMEOUT` | Startup timeout in ms (e.g., `10000`) |
| `MAX_MCP_OUTPUT_TOKENS` | Max output tokens (default: 25000) |
| `ENABLE_CLAUDEAI_MCP_SERVERS` | Enable/disable Claude.ai MCP servers |
| `ENABLE_TOOL_SEARCH` | Control MCP tool search behavior |

### Tool Search

When many MCP tools exist, Claude Code automatically defers tool loading:
- `true` — always enabled
- `auto` — activates when tools > 10% of context (default)
- `auto:<N>` — custom threshold percentage
- `false` — all tools loaded upfront

### Security Recommendation (Trail of Bits)

> Set `enableAllProjectMcpServers: false` explicitly — project `.mcp.json` files live in git, so a compromised repo could ship malicious MCP servers.

---

## 10. Best Practices for Hook Scripts

### Exit Code Rules

| Situation | Correct Exit Code |
|-----------|------------------|
| Success / allow | `0` (parse JSON from stdout) |
| **Block action (security gate)** | `2` (MUST be 2, not 1!) |
| Non-critical warning | `1` or any non-{0,2} (logged, continues) |

> **Critical Mistake:** Using `exit 1` instead of `exit 2` for security gates. Exit 1 is a non-blocking warning — the dangerous command **still executes**. Always use `exit 2` to block.

### Production Hook Structure

```bash
#!/bin/bash
set -euo pipefail

# Read JSON input
INPUT=$(cat)

# Extract fields with jq
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')

# Decision logic
if [[ "$COMMAND" =~ rm\ -rf ]]; then
  # Block with JSON output
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "Destructive command blocked: use trash instead"
    }
  }'
  # OR: simple block via exit code
  echo "Blocked: rm -rf is not allowed" >&2
  exit 2
fi

# Allow (exit 0, optionally with context)
exit 0
```

### Performance Guidelines

1. **Minimize synchronous hooks.** 10 hooks at 500ms each = 5s delay per tool call
2. **Consolidate related logic** into single hooks
3. **Use `"async": true`** for non-blocking operations (logging, metrics)
4. **Set appropriate timeouts** — don't rely on the 600s default for quick checks

### Path Resolution

Always use `$CLAUDE_PROJECT_DIR` for reliable path resolution:
```json
{
  "type": "command",
  "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/my-hook.sh"
}
```

### Script Best Practices

1. **Always use `set -euo pipefail`** at the top of bash hooks
2. **Use `jq`** for JSON parsing (never grep/sed on JSON)
3. **Prefer script files** over inline commands for production hooks
4. **Prefer JSON output** over exit codes for nuanced control
5. **Test with `/hooks`** command and validate JSON with:
   ```bash
   python3 -c "import json; json.load(open('.claude/settings.json'))"
   ```
6. **Quote paths** with spaces: `"$CLAUDE_PROJECT_DIR"` (not `$CLAUDE_PROJECT_DIR`)

### Security Hook Patterns

**Block dangerous bash commands:**
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/block-dangerous.sh"
      }]
    }]
  }
}
```

**Block direct pushes to main:**
```bash
#!/bin/bash
COMMAND=$(cat | jq -r '.tool_input.command // empty')
if echo "$COMMAND" | grep -qE 'git push.*(main|master)'; then
  echo "Direct push to main/master blocked. Use a feature branch." >&2
  exit 2
fi
```

**Anti-rationalization gate (Stop hook):**
```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "prompt",
        "prompt": "You MUST respond with raw JSON only, no markdown. Evaluate if this response rationalizes incomplete work: $ARGUMENTS. Respond: {\"ok\": true} or {\"ok\": false, \"reason\": \"...\"}",
        "model": "claude-haiku-4-5-20251001",
        "timeout": 30
      }]
    }]
  }
}
```

**Post-write linting (async):**
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": ".claude/hooks/lint-check.sh",
        "async": true
      }]
    }]
  }
}
```

**Inject context at session start:**
```bash
#!/bin/bash
# SessionStart hook — inject project context
jq -n --arg ctx "$(cat .claude/workflow/briefing.md)" '{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: $ctx
  }
}'
```

### Debugging Hooks

1. **`/hooks`** — view all configured hooks in the REPL
2. **Ctrl+O** (verbose mode) — see non-blocking errors/warnings
3. **stderr** — always appears in verbose mode for non-blocking errors, or fed to Claude for blocking errors
4. **`CLAUDE_CODE_DEBUG=true`** — additional debug logging

### Key Insight (Trail of Bits)

> "Hooks are structured prompt injection at opportune times — not security boundaries, but powerful guardrails that fire at contextual decision points where system instructions alone might be forgotten under context pressure."

---

## Sources

- [Claude Code Settings — Official Docs](https://code.claude.com/docs/en/settings)
- [Hooks Reference — Official Docs](https://code.claude.com/docs/en/hooks)
- [Model Configuration — Official Docs](https://code.claude.com/docs/en/model-config)
- [MCP Configuration — Official Docs](https://code.claude.com/docs/en/mcp)
- [Trail of Bits Claude Code Config](https://github.com/trailofbits/claude-code-config)
- [Anthropic Claude Code GitHub — Settings Examples](https://github.com/anthropics/claude-code/tree/main/examples/settings)
- [Claude Code Hooks Mastery](https://github.com/disler/claude-code-hooks-mastery)
- [eesel.ai — Claude Code Settings Guide](https://www.eesel.ai/blog/settings-json-claude-code)
- [eesel.ai — Claude Code Hooks Reference](https://www.eesel.ai/blog/hooks-reference-claude-code)
- [SmartScope — Claude Code Hooks Advanced Guide](https://smartscope.blog/en/generative-ai/claude/claude-code-hooks-practical-implementation/)
- [Blake Crosley — Claude Code Hooks Tutorial](https://blakecrosley.com/blog/claude-code-hooks-tutorial)
- [DataCamp — Claude Code Hooks Practical Guide](https://www.datacamp.com/tutorial/claude-code-hooks)
- [Claude Code Managed Settings Guide](https://managed-settings.com/)
