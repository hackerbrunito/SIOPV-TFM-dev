# Claude Code Directory Structure & Configuration — Research Report

> **Date:** 2026-03-16
> **Scope:** Complete `.claude/` directory structure, configuration files, hooks, agents, skills, memory, and settings.json schema
> **Sources:** Official Anthropic documentation (code.claude.com/docs), community guides, GitHub repos

---

## Table of Contents

1. [Complete `.claude/` Directory Structure](#1-complete-claude-directory-structure)
2. [CLAUDE.md vs `.claude/` Subdirectory Files](#2-claudemd-vs-claude-subdirectory-files)
3. [settings.json — Full Schema](#3-settingsjson--full-schema)
4. [Hooks — All Event Types & Configuration](#4-hooks--all-event-types--configuration)
5. [Agents — Custom Subagent Definition Files](#5-agents--custom-subagent-definition-files)
6. [Skills — SKILL.md & `.claude/skills/` Directory](#6-skills--skillmd--claudeskills-directory)
7. [Memory — Auto Memory System](#7-memory--auto-memory-system)
8. [New Features in Early 2026](#8-new-features-in-early-2026)
9. [Sources](#9-sources)

---

## 1. Complete `.claude/` Directory Structure

### Project-Level `.claude/` (committed to git)

```
.claude/
├── CLAUDE.md                     # Project instructions (alternative to root ./CLAUDE.md)
├── settings.json                 # Project settings (shared with team via git)
├── settings.local.json           # Local settings (gitignored, personal overrides)
├── rules/                        # Modular instruction files
│   ├── code-style.md             # Unconditional rules (loaded at launch)
│   ├── testing.md
│   ├── security.md
│   └── api-design.md             # Can have `paths:` frontmatter for conditional loading
├── agents/                       # Custom subagent definitions
│   ├── code-reviewer.md
│   ├── debugger.md
│   └── security-reviewer.md
├── skills/                       # Skill definitions
│   ├── deploy/
│   │   ├── SKILL.md              # Required entrypoint
│   │   ├── scripts/
│   │   └── references/
│   └── fix-issue/
│       └── SKILL.md
├── commands/                     # Legacy slash commands (merged into skills)
│   └── deploy.md                 # Same as skills but single-file format
├── agent-memory/                 # Subagent persistent memory (project scope)
│   └── <agent-name>/
│       └── MEMORY.md
├── agent-memory-local/           # Subagent persistent memory (local scope, gitignored)
│   └── <agent-name>/
│       └── MEMORY.md
└── hooks/                        # Hook scripts (referenced from settings.json)
    ├── pre-compact.sh
    ├── session-start.sh
    └── session-end.sh
```

### User-Level `~/.claude/` (personal, all projects)

```
~/.claude/
├── CLAUDE.md                     # Global user instructions (all projects)
├── settings.json                 # Global user settings
├── rules/                        # Personal rules (all projects)
│   ├── preferences.md
│   └── workflows.md
├── agents/                       # Personal subagents (all projects)
│   └── my-agent.md
├── skills/                       # Personal skills (all projects)
│   └── explain-code/
│       └── SKILL.md
├── commands/                     # Legacy global commands
├── agent-memory/                 # Subagent persistent memory (user scope)
│   └── <agent-name>/
│       └── MEMORY.md
├── projects/                     # Auto-generated per-project data
│   └── <encoded-project-path>/
│       └── memory/               # Auto memory directory
│           ├── MEMORY.md         # Index file (first 200 lines loaded at session start)
│           ├── debugging.md      # Topic files (loaded on demand)
│           └── api-conventions.md
├── plans/                        # Plan files (default location, configurable)
├── keybindings.json              # Custom keyboard shortcuts
└── plugins/                      # Installed plugins
```

### Managed (Enterprise) Locations

| OS | Path |
|----|------|
| macOS | `/Library/Application Support/ClaudeCode/CLAUDE.md` + `managed-settings.json` |
| Linux/WSL | `/etc/claude-code/CLAUDE.md` + `managed-settings.json` |
| Windows | `C:\Program Files\ClaudeCode\CLAUDE.md` + `managed-settings.json` |

### Other Config Files

| File | Location | Purpose |
|------|----------|---------|
| `~/.claude.json` | Home dir | Preferences, OAuth, MCP servers (user/local), per-project state, caches |
| `.mcp.json` | Project root | Project-scoped MCP server definitions |

---

## 2. CLAUDE.md vs `.claude/` Subdirectory Files

### CLAUDE.md — Instruction Hierarchy

| Scope | Location | Priority | Purpose |
|-------|----------|----------|---------|
| Managed policy | System-level path | Highest (cannot be excluded) | Organization-wide standards |
| Project (`.claude/`) | `.claude/CLAUDE.md` | High | Team conventions |
| Project (root) | `./CLAUDE.md` | High | Team conventions (alternative location) |
| User | `~/.claude/CLAUDE.md` | Medium | Personal preferences |
| Parent directories | `../CLAUDE.md` etc. | Loaded by walking up tree | Monorepo shared rules |
| Child directories | `subdir/CLAUDE.md` | Loaded on demand | Subdirectory-specific context |

### Key Rules

- **Target under 200 lines per file** — longer files reduce adherence
- **No required format** — plain markdown, human-readable
- **Loaded every session** — only include broadly applicable content
- Use `@path/to/import` syntax to import additional files (max depth: 5 hops)
- `claudeMdExcludes` setting can skip specific CLAUDE.md files (glob patterns)
- CLAUDE.md **fully survives compaction** — re-read from disk after `/compact`
- Run `/init` to auto-generate a starter CLAUDE.md

### `.claude/rules/` — Modular Rules

- Each `.md` file covers one topic (descriptive filename like `testing.md`)
- Discovered recursively (supports subdirectories like `frontend/`, `backend/`)
- Rules **without** `paths` frontmatter: loaded at launch unconditionally
- Rules **with** `paths` frontmatter: loaded only when Claude works with matching files
- Supports symlinks for sharing rules across projects
- User-level rules: `~/.claude/rules/` (loaded before project rules)

#### Path-Specific Rules Example

```markdown
---
paths:
  - "src/api/**/*.ts"
  - "lib/**/*.ts"
---

# API Development Rules
- All API endpoints must include input validation
- Use the standard error response format
```

### What Goes Where

| Content Type | CLAUDE.md | `.claude/rules/` | Skills |
|---|---|---|---|
| Build/test commands | Yes | - | - |
| Code style rules | Yes | Yes (conditional) | - |
| Architecture decisions | Yes | - | - |
| Domain knowledge | - | - | Yes (on-demand) |
| Repeatable workflows | - | - | Yes (invocable) |
| File-type-specific rules | - | Yes (with `paths`) | - |

---

## 3. settings.json — Full Schema

### Locations & Scopes

| Scope | File | Shared? |
|-------|------|---------|
| Managed | `managed-settings.json` (system path) | Yes (deployed by IT) |
| User | `~/.claude/settings.json` | No (personal) |
| Project | `.claude/settings.json` | Yes (committed to git) |
| Local | `.claude/settings.local.json` | No (gitignored) |

**Schema URL:** `https://json.schemastore.org/claude-code-settings.json`

Add `"$schema": "https://json.schemastore.org/claude-code-settings.json"` for autocomplete in VS Code / Cursor.

### Complete Settings Reference

#### Core Settings

| Key | Type | Description | Example |
|-----|------|-------------|---------|
| `$schema` | string | JSON schema URL for IDE validation | `"https://json.schemastore.org/claude-code-settings.json"` |
| `model` | string | Override default model | `"claude-sonnet-4-6"` |
| `availableModels` | string[] | Restrict model selection | `["sonnet", "haiku"]` |
| `modelOverrides` | object | Map model IDs to provider-specific IDs | `{"claude-opus-4-6": "arn:aws:bedrock:..."}` |
| `effortLevel` | string | Persist effort level: `"low"`, `"medium"`, `"high"` | `"medium"` |
| `language` | string | Preferred response language | `"spanish"` |
| `outputStyle` | string | System prompt output style adjustment | `"Explanatory"` |

#### Permission Settings

| Key | Type | Description |
|-----|------|-------------|
| `permissions.allow` | string[] | Tool use allowlist (evaluated after deny) |
| `permissions.ask` | string[] | Tools requiring confirmation |
| `permissions.deny` | string[] | Tool use denylist (evaluated first) |
| `permissions.additionalDirectories` | string[] | Extra working directories |
| `permissions.defaultMode` | string | Default permission mode: `"default"`, `"acceptEdits"`, `"dontAsk"`, `"bypassPermissions"`, `"plan"` |
| `permissions.disableBypassPermissionsMode` | string | Set to `"disable"` to prevent bypass mode |

**Permission Rule Syntax:** `Tool` or `Tool(specifier)` — evaluated: deny → ask → allow, first match wins.

Examples:
- `Bash(npm run *)` — matches commands starting with `npm run`
- `Read(./.env)` — matches reading `.env`
- `WebFetch(domain:example.com)` — matches fetch to domain
- `Agent(Explore)` — matches specific subagent type

#### Hook Settings

| Key | Type | Description |
|-----|------|-------------|
| `hooks` | object | Hook definitions keyed by event name |
| `disableAllHooks` | boolean | Disable all hooks and custom status line |
| `allowManagedHooksOnly` | boolean | (Managed only) Block non-managed hooks |
| `allowedHttpHookUrls` | string[] | URL allowlist for HTTP hooks (supports `*` wildcard) |
| `httpHookAllowedEnvVars` | string[] | Env var allowlist for HTTP hook headers |

#### Sandbox Settings

| Key | Type | Description |
|-----|------|-------------|
| `sandbox.enabled` | boolean | Enable bash sandboxing |
| `sandbox.autoAllowBashIfSandboxed` | boolean | Auto-approve bash when sandboxed (default: true) |
| `sandbox.excludedCommands` | string[] | Commands that run outside sandbox |
| `sandbox.allowUnsandboxedCommands` | boolean | Allow `dangerouslyDisableSandbox` parameter |
| `sandbox.filesystem.allowWrite` | string[] | Additional writable paths |
| `sandbox.filesystem.denyWrite` | string[] | Blocked write paths |
| `sandbox.filesystem.denyRead` | string[] | Blocked read paths |
| `sandbox.network.allowedDomains` | string[] | Allowed outbound domains |
| `sandbox.network.allowUnixSockets` | string[] | Allowed Unix socket paths |
| `sandbox.network.allowAllUnixSockets` | boolean | Allow all Unix sockets |
| `sandbox.network.allowLocalBinding` | boolean | Allow localhost port binding (macOS only) |
| `sandbox.network.allowManagedDomainsOnly` | boolean | (Managed only) Only managed domains allowed |
| `sandbox.network.httpProxyPort` | number | Custom HTTP proxy port |
| `sandbox.network.socksProxyPort` | number | Custom SOCKS5 proxy port |
| `sandbox.enableWeakerNestedSandbox` | boolean | Weaker sandbox for unprivileged Docker |
| `sandbox.enableWeakerNetworkIsolation` | boolean | (macOS) Allow TLS trust service access |

#### Worktree Settings

| Key | Type | Description |
|-----|------|-------------|
| `worktree.symlinkDirectories` | string[] | Directories to symlink from main repo |
| `worktree.sparsePaths` | string[] | Directories for sparse-checkout |

#### Attribution Settings

| Key | Type | Description |
|-----|------|-------------|
| `attribution.commit` | string | Git commit attribution text (empty = hidden) |
| `attribution.pr` | string | PR description attribution text (empty = hidden) |
| `includeCoAuthoredBy` | boolean | **Deprecated** — use `attribution` instead |

#### MCP Settings

| Key | Type | Description |
|-----|------|-------------|
| `enableAllProjectMcpServers` | boolean | Auto-approve all `.mcp.json` servers |
| `enabledMcpjsonServers` | string[] | Specific servers to approve |
| `disabledMcpjsonServers` | string[] | Specific servers to reject |
| `allowedMcpServers` | object[] | (Managed) MCP server allowlist |
| `deniedMcpServers` | object[] | (Managed) MCP server denylist |
| `allowManagedMcpServersOnly` | boolean | (Managed) Only managed servers allowed |

#### UI & UX Settings

| Key | Type | Description |
|-----|------|-------------|
| `statusLine` | object | Custom status line config |
| `fileSuggestion` | object | Custom `@` file autocomplete command |
| `respectGitignore` | boolean | `@` picker respects `.gitignore` (default: true) |
| `showTurnDuration` | boolean | Show "Cooked for X" messages |
| `spinnerVerbs` | object | Custom spinner action verbs (`mode`: `"replace"` or `"append"`) |
| `spinnerTipsEnabled` | boolean | Show tips in spinner (default: true) |
| `spinnerTipsOverride` | object | Custom spinner tips |
| `terminalProgressBarEnabled` | boolean | Terminal progress bar (default: true) |
| `prefersReducedMotion` | boolean | Reduce UI animations |
| `feedbackSurveyRate` | number | Survey probability (0–1) |

#### Session & Memory Settings

| Key | Type | Description |
|-----|------|-------------|
| `cleanupPeriodDays` | number | Session cleanup threshold (default: 30; 0 = disable persistence) |
| `autoMemoryEnabled` | boolean | Enable/disable auto memory |
| `autoMemoryDirectory` | string | Custom memory storage directory |
| `plansDirectory` | string | Custom plans storage path |

#### Authentication & API Settings

| Key | Type | Description |
|-----|------|-------------|
| `apiKeyHelper` | string | Script to generate auth value |
| `forceLoginMethod` | string | `"claudeai"` or `"console"` |
| `forceLoginOrgUUID` | string | Auto-select organization UUID |
| `awsAuthRefresh` | string | AWS credential refresh script |
| `awsCredentialExport` | string | AWS credential export script |
| `otelHeadersHelper` | string | OpenTelemetry headers script |
| `alwaysThinkingEnabled` | boolean | Extended thinking by default |
| `includeGitInstructions` | boolean | Built-in git workflow instructions (default: true) |

#### Plugin & Marketplace Settings

| Key | Type | Description |
|-----|------|-------------|
| `strictKnownMarketplaces` | object[] | (Managed) Plugin marketplace allowlist |
| `blockedMarketplaces` | object[] | (Managed) Marketplace blocklist |
| `pluginTrustMessage` | string | (Managed) Custom plugin trust warning message |

#### Mode Settings

| Key | Type | Description |
|-----|------|-------------|
| `fastModePerSessionOptIn` | boolean | Fast mode doesn't persist across sessions |
| `teammateMode` | string | Agent team display: `"auto"`, `"in-process"`, `"tmux"` |
| `autoUpdatesChannel` | string | `"stable"` or `"latest"` (default) |

---

## 4. Hooks — All Event Types & Configuration

### Hook Lifecycle

```
SessionStart → UserPromptSubmit → [Agentic Loop] → SessionEnd
                                  ├─ PreToolUse
                                  ├─ PermissionRequest
                                  ├─ PostToolUse
                                  ├─ PostToolUseFailure
                                  ├─ SubagentStart/Stop
                                  ├─ TaskCompleted
                                  ├─ TeammateIdle
                                  └─ Stop
```

### Configuration Structure

```json
{
  "hooks": {
    "EVENT_NAME": [
      {
        "matcher": "filter_pattern",
        "hooks": [
          {
            "type": "command|http|prompt|agent",
            "command": "script.sh",
            "timeout": 600,
            "async": false,
            "statusMessage": "Running..."
          }
        ]
      }
    ]
  }
}
```

### Hook Handler Types

| Type | Description | Key Fields |
|------|-------------|------------|
| `command` | Shell command, JSON on stdin | `command`, `timeout`, `async`, `statusMessage` |
| `http` | HTTP POST to endpoint | `url`, `headers`, `allowedEnvVars`, `timeout` |
| `prompt` | Single-turn LLM evaluation | `prompt`, `model`, `timeout` |
| `agent` | Multi-turn agentic verification | `prompt`, `timeout` |

### Exit Code Behavior

| Code | Meaning | Effect |
|------|---------|--------|
| 0 | Success | Parse stdout for JSON; action proceeds |
| 2 | Blocking error | Ignore stdout; stderr shown to Claude; action blocked |
| Other | Non-blocking error | stderr in verbose mode; continues |

### Complete Event Reference

#### Session Lifecycle Events

| Event | Matcher Values | Can Block? | Key Input Fields |
|-------|---------------|------------|------------------|
| `SessionStart` | `startup`, `resume`, `clear`, `compact` | Yes (`continue: false`) | `source`, `model` |
| `SessionEnd` | `clear`, `logout`, `prompt_input_exit`, `bypass_permissions_disabled`, `other` | No | `reason` |
| `PreCompact` | `manual`, `auto` | No | `trigger`, `custom_instructions` |
| `PostCompact` | `manual`, `auto` | No | `trigger`, `compact_summary` |

**SessionStart special feature:** Can persist env vars via `$CLAUDE_ENV_FILE`:
```bash
if [ -n "$CLAUDE_ENV_FILE" ]; then
  echo 'export NODE_ENV=production' >> "$CLAUDE_ENV_FILE"
fi
```

**SessionEnd note:** Default timeout 1.5 seconds (configurable via `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS`)

#### User Input Events

| Event | Matcher Values | Can Block? | Key Input Fields |
|-------|---------------|------------|------------------|
| `UserPromptSubmit` | — | Yes (`decision: "block"`) | `prompt` |

#### Tool Events

| Event | Matcher Values | Can Block? | Key Input Fields |
|-------|---------------|------------|------------------|
| `PreToolUse` | Tool names: `Bash`, `Edit`, `Write`, `Read`, `Glob`, `Grep`, `Agent`, `WebFetch`, `WebSearch`, `mcp__*` | Yes (`permissionDecision: "deny"`) | `tool_name`, `tool_input`, `tool_use_id` |
| `PostToolUse` | Same as PreToolUse | Yes (`decision: "block"`) | `tool_name`, `tool_input`, `tool_response`, `tool_use_id` |
| `PostToolUseFailure` | Same as PreToolUse | No | `tool_name`, `tool_input`, `tool_use_id`, `error`, `is_interrupt` |
| `PermissionRequest` | Same as PreToolUse | Yes (`decision: "allow\|deny"`) | `tool_name`, `tool_input`, `permission_suggestions` |

**PreToolUse output schema:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|deny|ask",
    "permissionDecisionReason": "Reason shown to user",
    "updatedInput": { "field": "modified_value" },
    "additionalContext": "Context for Claude"
  }
}
```

**PostToolUse output schema:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Context for Claude",
    "updatedMCPToolOutput": "replacement output"
  }
}
```

#### Agent Events

| Event | Matcher Values | Can Block? | Key Input Fields |
|-------|---------------|------------|------------------|
| `SubagentStart` | Agent type names: `Bash`, `Explore`, `Plan`, custom names | No (add context only) | `agent_id`, `agent_type` |
| `SubagentStop` | Same as SubagentStart | Yes (`decision: "block"`) | `agent_id`, `agent_type`, `agent_transcript_path`, `last_assistant_message` |
| `Stop` | — | Yes (`decision: "block"`) | `stop_hook_active`, `last_assistant_message` |
| `TaskCompleted` | — | Yes (exit 2 = not completed) | `task_id`, `task_subject`, `task_description`, `teammate_name`, `team_name` |
| `TeammateIdle` | — | Yes (exit 2 = continue working) | `teammate_name`, `team_name` |

#### Instruction & Config Events

| Event | Matcher Values | Can Block? | Key Input Fields |
|-------|---------------|------------|------------------|
| `InstructionsLoaded` | — | No (observability only) | `file_path`, `memory_type`, `load_reason`, `globs` |
| `ConfigChange` | `user_settings`, `project_settings`, `local_settings`, `policy_settings`, `skills` | Yes (`decision: "block"`) | `source`, `file_path` |

**Note:** `policy_settings` changes cannot be blocked.

#### Worktree Events

| Event | Matcher Values | Can Block? | Key Input Fields |
|-------|---------------|------------|------------------|
| `WorktreeCreate` | — | Custom (prints path to stdout) | `name` |
| `WorktreeRemove` | — | No | `worktree_path` |

#### MCP Elicitation Events

| Event | Matcher Values | Can Block? | Key Input Fields |
|-------|---------------|------------|------------------|
| `Elicitation` | MCP server name | Yes (`action: "accept\|decline\|cancel"`) | `mcp_server_name`, `message`, `mode`, `url`, `requested_schema` |
| `ElicitationResult` | — | Override possible | `mcp_server_name`, `action`, `mode`, `content`, `elicitation_id` |

### Common Input Fields (All Hooks)

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/dir",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse",
  "agent_id": "optional-subagent-id",
  "agent_type": "optional-agent-type"
}
```

### Common Output Fields (All Hooks)

```json
{
  "continue": true,
  "stopReason": "Message if continue is false",
  "suppressOutput": false,
  "systemMessage": "Warning shown to user"
}
```

### Environment Variables for Hooks

| Variable | Description |
|----------|-------------|
| `$CLAUDE_PROJECT_DIR` | Project root directory |
| `$CLAUDE_PLUGIN_ROOT` | Plugin root (for plugin hooks) |
| `$CLAUDE_ENV_FILE` | File for persisting env vars (SessionStart only) |

---

## 5. Agents — Custom Subagent Definition Files

### File Format

Markdown files with YAML frontmatter + system prompt in body:

```markdown
---
name: code-reviewer
description: Reviews code for quality and best practices
tools: Read, Glob, Grep
model: sonnet
---

You are a code reviewer. When invoked, analyze the code and provide
specific, actionable feedback on quality, security, and best practices.
```

### Storage Locations & Priority

| Priority | Location | Scope |
|----------|----------|-------|
| 1 (highest) | `--agents` CLI flag (JSON) | Current session only |
| 2 | `.claude/agents/` | Current project |
| 3 | `~/.claude/agents/` | All projects |
| 4 (lowest) | Plugin `agents/` directory | Where plugin is enabled |

When multiple subagents share the same name, higher-priority location wins.

### Complete Frontmatter Schema

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | Yes | string | Unique identifier (lowercase letters and hyphens) |
| `description` | Yes | string | When Claude should delegate to this subagent |
| `tools` | No | string (CSV) or array | Tool allowlist; inherits all if omitted |
| `disallowedTools` | No | string (CSV) or array | Tool denylist |
| `model` | No | string | `sonnet`, `opus`, `haiku`, full model ID, or `inherit` (default: `inherit`) |
| `permissionMode` | No | string | `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan` |
| `maxTurns` | No | number | Maximum agentic turns before stop |
| `skills` | No | string[] | Skills to preload into context at startup |
| `mcpServers` | No | array | MCP servers: inline definitions or string references |
| `hooks` | No | object | Lifecycle hooks scoped to this subagent |
| `memory` | No | string | Persistent memory scope: `user`, `project`, or `local` |
| `background` | No | boolean | Always run in background (default: false) |
| `isolation` | No | string | Set to `worktree` for isolated git worktree |

### Tool Configuration

**Allowlist (restrict):**
```yaml
tools: Read, Grep, Glob, Bash
```

**Denylist (remove from inherited):**
```yaml
disallowedTools: Write, Edit
```

**Restrict spawnable subagents (main thread only):**
```yaml
tools: Agent(worker, researcher), Read, Bash
```

### MCP Server Scoping

```yaml
mcpServers:
  # Inline definition: scoped to this subagent only
  - playwright:
      type: stdio
      command: npx
      args: ["-y", "@playwright/mcp@latest"]
  # Reference by name: reuses already-configured server
  - github
```

### Memory Scopes

| Scope | Location | Use When |
|-------|----------|----------|
| `user` | `~/.claude/agent-memory/<name>/` | Learnings across all projects |
| `project` | `.claude/agent-memory/<name>/` | Project-specific, shareable via git |
| `local` | `.claude/agent-memory-local/<name>/` | Project-specific, not in git |

When memory is enabled, Read/Write/Edit tools are auto-enabled, and first 200 lines of the agent's `MEMORY.md` are loaded at startup.

### Built-in Subagents

| Agent | Model | Tools | Purpose |
|-------|-------|-------|---------|
| Explore | Haiku | Read-only | File discovery, code search |
| Plan | Inherit | Read-only | Codebase research for planning |
| general-purpose | Inherit | All | Complex multi-step tasks |
| Bash | Inherit | Terminal | Running commands in separate context |
| statusline-setup | Sonnet | - | Status line configuration |
| Claude Code Guide | Haiku | - | Questions about Claude Code features |

### CLI-Defined Subagents

```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer.",
    "prompt": "You are a senior code reviewer.",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  }
}'
```

### Subagent Limitations

- Subagents **cannot spawn other subagents** (no nesting)
- Subagent transcripts persist independently of main conversation
- Auto-compaction triggers at ~95% capacity (configurable via `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`)
- Transcripts cleaned up based on `cleanupPeriodDays` (default: 30)

---

## 6. Skills — SKILL.md & `.claude/skills/` Directory

### Directory Structure

```
my-skill/
├── SKILL.md           # Required entrypoint
├── template.md        # Template for Claude to fill in
├── examples/
│   └── sample.md      # Example output
├── scripts/
│   └── validate.sh    # Executable scripts
├── references/
│   └── api-docs.md    # Documentation loaded on demand
└── assets/
    └── template.html  # Binary/template files
```

### Storage Locations & Priority

| Location | Path | Scope |
|----------|------|-------|
| Enterprise | Managed settings | Organization-wide |
| Personal | `~/.claude/skills/<name>/SKILL.md` | All projects |
| Project | `.claude/skills/<name>/SKILL.md` | This project only |
| Plugin | `<plugin>/skills/<name>/SKILL.md` | Where plugin enabled |

Higher-priority wins when names conflict. Plugin skills use namespace: `plugin-name:skill-name`.

### Complete Frontmatter Schema

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | No | string | Display name / slash-command. Max 64 chars, lowercase+hyphens. Defaults to directory name |
| `description` | Recommended | string | What skill does / when to use it. Max 1024 chars |
| `argument-hint` | No | string | Hint during autocomplete (e.g., `[issue-number]`) |
| `disable-model-invocation` | No | boolean | Prevent Claude auto-loading (default: false) |
| `user-invocable` | No | boolean | Show in `/` menu (default: true) |
| `allowed-tools` | No | string (CSV) | Tools Claude can use without permission |
| `model` | No | string | Model override when skill is active |
| `context` | No | string | Set to `fork` to run in forked subagent |
| `agent` | No | string | Subagent type for `context: fork` (e.g., `Explore`, `Plan`, custom) |
| `hooks` | No | object | Hooks scoped to this skill's lifecycle |

### String Substitutions

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments passed to skill |
| `$ARGUMENTS[N]` or `$N` | Specific argument by 0-based index |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `${CLAUDE_SKILL_DIR}` | Directory containing SKILL.md |

### Dynamic Context Injection

The `` !`command` `` syntax runs shell commands before skill content is sent to Claude:

```yaml
---
name: pr-summary
description: Summarize changes in a pull request
context: fork
agent: Explore
---

## PR Context
- PR diff: !`gh pr diff`
- Changed files: !`gh pr diff --name-only`
```

### Invocation Control Summary

| Setting | You invoke? | Claude invokes? | Context loading |
|---------|-------------|-----------------|-----------------|
| (default) | Yes | Yes | Description always in context |
| `disable-model-invocation: true` | Yes | No | Not in context |
| `user-invocable: false` | No | Yes | Description always in context |

### Bundled Skills (ship with Claude Code)

| Skill | Purpose |
|-------|---------|
| `/batch <instruction>` | Large-scale parallel changes with worktrees |
| `/claude-api` | Claude API reference for your language |
| `/debug [description]` | Troubleshoot session via debug log |
| `/loop [interval] <prompt>` | Run prompt on recurring interval |
| `/simplify [focus]` | Review changed files for reuse/quality |

### Skill Description Budget

Descriptions are loaded into context; if too many skills, some may be excluded. Budget: 2% of context window (~16,000 chars fallback). Override with `SLASH_COMMAND_TOOL_CHAR_BUDGET` env var.

---

## 7. Memory — Auto Memory System

### Two Memory Systems

| | CLAUDE.md | Auto Memory |
|---|---|---|
| **Who writes** | You | Claude |
| **Contains** | Instructions & rules | Learnings & patterns |
| **Scope** | Project, user, or org | Per working tree |
| **Loaded** | Every session (full) | Every session (first 200 lines of MEMORY.md) |
| **Use for** | Coding standards, workflows | Build commands, debugging insights, preferences |

### Auto Memory Storage

**Location:** `~/.claude/projects/<project>/memory/`

The `<project>` path is derived from the git repository, so all worktrees and subdirectories within the same repo share one auto memory directory. Outside git, the project root is used.

**Custom directory:** Set `autoMemoryDirectory` in user or local settings (not accepted from project settings for security).

### MEMORY.md Structure

```
~/.claude/projects/<project>/memory/
├── MEMORY.md              # Concise index (first 200 lines loaded every session)
├── debugging.md           # Topic file (loaded on demand)
├── api-conventions.md     # Topic file (loaded on demand)
└── patterns.md            # Topic file (loaded on demand)
```

### Key Rules

- **200-line hard limit** on MEMORY.md — content beyond line 200 is not loaded at startup
- Claude keeps MEMORY.md concise by moving detailed notes to topic files
- Topic files are NOT loaded at startup — Claude reads them on demand
- Auto memory is **machine-local** — not shared across machines
- Files are plain markdown — editable by you at any time
- Run `/memory` to browse, toggle auto memory, or open files in editor

### Enabling/Disabling

```json
// In settings.json
{ "autoMemoryEnabled": false }

// Or via environment variable
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1
```

### Subagent Memory

Subagents can have their own persistent memory via the `memory` frontmatter field:

| Scope | Location | Use When |
|-------|----------|----------|
| `user` | `~/.claude/agent-memory/<name>/` | Cross-project learnings |
| `project` | `.claude/agent-memory/<name>/` | Project-specific, shareable |
| `local` | `.claude/agent-memory-local/<name>/` | Project-specific, private |

---

## 8. New Features in Early 2026

### Agent Teams (Experimental)

- Coordinate multiple Claude Code sessions working together
- One session acts as team lead; teammates work independently
- Each teammate has its own context window
- Communication via `SendMessage` tool
- Display modes: `auto`, `in-process`, `tmux`
- Configuration: `teammateMode` in settings.json
- Enabled via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` (as of early 2026, now more widely available)

### Plugins

- Package skills, hooks, subagents, and MCP servers into installable units
- Plugin marketplace with managed restrictions
- Plugin-provided agents live in `<plugin>/agents/`
- Plugin-provided skills live in `<plugin>/skills/`
- Plugin hooks in `hooks/hooks.json`
- Managed marketplace controls: `strictKnownMarketplaces`, `blockedMarketplaces`

### Skills Merge with Commands

- `.claude/commands/` files now work as skills
- Skills take precedence if same name exists
- Skills add: directory support, frontmatter, auto-invocation
- New `context: fork` option to run skills in isolated subagent

### New Hook Events (2026 additions)

- `SubagentStart` / `SubagentStop` — agent lifecycle hooks
- `TaskCompleted` / `TeammateIdle` — team coordination hooks
- `InstructionsLoaded` — observability for loaded instructions
- `ConfigChange` — react to settings file changes
- `WorktreeCreate` / `WorktreeRemove` — custom worktree management
- `Elicitation` / `ElicitationResult` — MCP server user input
- `PostToolUseFailure` — tool failure handling
- `PermissionRequest` — permission dialog interception
- `PostCompact` — post-compaction processing
- Hook types expanded: `prompt` and `agent` types added alongside `command` and `http`

### Worktree Improvements

- `worktree.symlinkDirectories` — avoid duplicating large dirs
- `worktree.sparsePaths` — sparse-checkout for large monorepos
- `isolation: "worktree"` in subagent frontmatter
- Custom `WorktreeCreate`/`WorktreeRemove` hooks

### Other New Settings

- `effortLevel` — persist effort level across sessions
- `fastModePerSessionOptIn` — require per-session fast mode opt-in
- `autoUpdatesChannel` — `"stable"` vs `"latest"` release channels
- `fileSuggestion` — custom `@` file autocomplete
- `outputStyle` — adjust system prompt style
- `spinnerVerbs`, `spinnerTipsOverride` — UI customization
- `prefersReducedMotion` — accessibility setting
- `terminalProgressBarEnabled` — progress bar for supported terminals
- `availableModels` — restrict model selection
- `modelOverrides` — provider-specific model ID mapping
- `plansDirectory` — custom plan file storage
- `showTurnDuration` — show/hide turn timing

---

## 9. Sources

### Official Anthropic Documentation
- [Claude Code Settings](https://code.claude.com/docs/en/settings)
- [Hooks Reference](https://code.claude.com/docs/en/hooks)
- [Create Custom Subagents](https://code.claude.com/docs/en/sub-agents)
- [Extend Claude with Skills](https://code.claude.com/docs/en/skills)
- [How Claude Remembers Your Project (Memory)](https://code.claude.com/docs/en/memory)
- [Best Practices for Claude Code](https://code.claude.com/docs/en/best-practices)
- [Claude Code Overview](https://code.claude.com/docs/en/overview)

### Community & Third-Party Guides
- [The .claude/ Folder Structure — DeepWiki](https://deepwiki.com/FlorianBruniaux/claude-code-ultimate-guide/4.4-the-.claude-folder-structure)
- [CLAUDE.md: The Complete Guide (2026) — MorphLLM](https://www.morphllm.com/claude-md-guide)
- [Claude Code Configuration Guide — ClaudeLog](https://claudelog.com/configuration/)
- [Claude Code Settings Reference — ClaudeFast](https://claudefa.st/blog/guide/settings-reference)
- [settings.json Schema — JSON Schema Store](https://json.schemastore.org/claude-code-settings.json)
- [Trail of Bits Claude Code Config — GitHub](https://github.com/trailofbits/claude-code-config)
- [Claude Code Complete Guide 2026 — ClaudeWorld](https://claude-world.com/articles/claude-code-complete-guide-2026/)
- [Writing a Good CLAUDE.md — HumanLayer](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- [CLAUDE.md Best Practices — UX Planet](https://uxplanet.org/claude-md-best-practices-1ef4f861ce7c)
- [Using CLAUDE.md Files — Anthropic Blog](https://claude.com/blog/using-claude-md-files)
- [Claude Code Hooks Guide — Anthropic Blog](https://claude.com/blog/how-to-configure-hooks)
- [Claude Code Agent Teams — Addy Osmani](https://addyosmani.com/blog/claude-code-agent-teams/)
- [Agent Skills Deep Dive — Lee Han Chung](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)
- [Inside Claude Code Skills — Mikhail Shilkov](https://mikhail.io/2025/10/claude-code-skills/)
- [Claude Code Release Notes (March 2026) — Releasebot](https://releasebot.io/updates/anthropic/claude-code)
