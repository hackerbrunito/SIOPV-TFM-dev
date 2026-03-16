# Round 1 Final Summary — Claude Code Best Practices (March 2026)

**Sources:** Official Claude Code docs (code.claude.com) + changelog — verified 2026-03-13
**Compiled from:** 4 Round 1 reports (agent-definitions-memory, hooks-settings, skills-claudemd-workflow, teams-new-features)

---

## 1. Agent Definitions

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | **Yes** | Unique identifier — lowercase + hyphens |
| `description` | **Yes** | When to delegate (used for auto-delegation) |
| `tools` | No | Allowlist; inherits all if omitted; supports `Agent(type)` syntax |
| `disallowedTools` | No | Denylist — removes from inherited/specified list |
| `model` | No | `sonnet`, `opus`, `haiku`, full model ID, or `inherit` (default) |
| `permissionMode` | No | `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan` |
| `maxTurns` | No | Max agentic turns before agent stops |
| `skills` | No | Preload full skill content into agent context at startup |
| `mcpServers` | No | MCP servers scoped to this agent |
| `hooks` | No | `PreToolUse`, `PostToolUse`, `Stop` scoped to agent lifecycle |
| `memory` | No | `user`, `project`, or `local` — persistent cross-session memory scope |
| `background` | No | `true` = always run as background task |
| `isolation` | No | `worktree` = isolated git worktree (auto-cleaned if no changes) |

### Valid Model Values

| Value | Meaning |
|-------|---------|
| `sonnet` | Alias → latest Sonnet |
| `opus` | Alias → latest Opus |
| `haiku` | Alias → fastest/cheapest |
| `claude-sonnet-4-6` | Full model ID (exact version) |
| `claude-opus-4-6` | Full model ID (exact version) |
| `inherit` | Same as parent (default if omitted) |

### Discovery & Loading

- Priority: `--agents` CLI flag > `.claude/agents/` (project) > `~/.claude/agents/` (user) > plugin `agents/`
- Name conflicts: higher-priority location wins
- Added mid-session: requires `/agents` command or restart to take effect
- Subagents receive ONLY their own system prompt + basic env — NO parent conversation history
- **Subagents CANNOT spawn other subagents** (no nesting)
- `Task(...)` still works as alias for `Agent(...)` (renamed in v2.1.63)

### New 2026 Features
- `background`, `isolation`, `skills`, `memory` frontmatter fields
- `SubagentStart` / `SubagentStop` hook events
- `/agents` interactive UI (create, edit, delete)
- Resume subagents via agent ID; transcripts at `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl`
- Auto-compaction supported at ~95% capacity

---

## 2. Memory System

| System | Author | Loaded | Scope |
|--------|--------|--------|-------|
| CLAUDE.md files | Developer | Every session (full) | Project/user/org |
| Auto memory (MEMORY.md) | Claude | Every session (first 200 lines) | Per git worktree |
| Subagent memory | Claude | Per agent scope | `user`, `project`, or `local` |

### MEMORY.md Format & Limits

| Item | Limit / Rule |
|------|-------------|
| MEMORY.md load at startup | First **200 lines only** (hard cut) |
| Beyond 200 lines | NOT loaded at session start |
| CLAUDE.md size recommendation | Target **< 200 lines** (no hard cut, but reduces adherence) |
| Topic files | NOT loaded at startup — read on demand |
| Location | `~/.claude/projects/<encoded-path>/memory/MEMORY.md` |

- MEMORY.md = plain Markdown index pointing to topic files
- Topic files in same dir hold detail — referenced from MEMORY.md, read on demand
- Auto memory is machine-local only (not shared across machines)

### Auto-Memory Behavior
- **On by default** (v2.1.59+)
- Toggle: `/memory` command or `autoMemoryEnabled: false` in settings
- Disable session-level: `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`
- Custom location: `autoMemoryDirectory` setting (user/local/policy only — NOT in `.claude/settings.json`)

### Memory File Frontmatter (project-configured format)
```markdown
---
name: memory_name
description: one-line description (used for relevance matching)
type: user | feedback | project | reference
---
Content. For feedback/project types: rule/fact, then **Why:** and **How to apply:** lines.
```

### Subagent Memory Scope Paths
- `user` → `~/.claude/agent-memory/<agent-name>/`
- `project` → `.claude/agent-memory/<agent-name>/`
- `local` → `.claude/agent-memory-local/<agent-name>/`

---

## 3. Hook System

### Complete Hook Types (17 total)

| Event | When it fires | Can block? | Matcher |
|-------|--------------|------------|---------|
| `SessionStart` | Session begins/resumes | No | `startup`, `resume`, `clear`, `compact` |
| `UserPromptSubmit` | Before Claude processes prompt | Yes (exit 2) | None |
| `PreToolUse` | Before tool executes | Yes (exit 2 or hookSpecificOutput) | tool name regex |
| `PermissionRequest` | When permission dialog appears | Yes (hookSpecificOutput) | tool name |
| `PostToolUse` | After tool succeeds | No (stderr → Claude) | tool name regex |
| `PostToolUseFailure` | After tool fails | No (stderr → Claude) | tool name regex |
| `Notification` | When notification sent | No | `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog` |
| `SubagentStart` | When subagent spawned | No | agent type |
| `SubagentStop` | When subagent finishes | Yes (exit 2) | agent type |
| `Stop` | When Claude finishes responding | Yes (exit 2) | None |
| `TeammateIdle` | Teammate about to go idle | Yes (exit 2) | None |
| `TaskCompleted` | Task being marked completed | Yes (exit 2) | None |
| `InstructionsLoaded` | CLAUDE.md or `.claude/rules/*.md` loaded | No | None |
| `ConfigChange` | Config file changes during session | Yes (except `policy_settings`) | `user_settings`, `project_settings`, `local_settings`, `policy_settings`, `skills` |
| `WorktreeCreate` | Worktree being created | Yes (non-zero fails) | None |
| `WorktreeRemove` | Worktree being removed | No | None |
| `PreCompact` | Before context compaction | No | `manual`, `auto` |
| `SessionEnd` | Session terminates | No | `clear`, `logout`, `prompt_input_exit`, `bypass_permissions_disabled`, `other` |

**Note:** `PostCompact` does NOT exist — use `SessionStart` with `compact` matcher instead.

### Handler Types

| Type | Format | Blocking |
|------|--------|---------|
| `command` | Shell script; JSON via stdin | Exit 2 blocks |
| `http` | POST JSON to URL; response body as output | Return JSON `decision: "block"` |
| `prompt` | Single-turn Claude evaluation | Returns yes/no JSON |
| `agent` | Spawns subagent (Read/Grep/Glob tools) | Exit 2 blocks |

- **Exit 0** → success, parse stdout for JSON
- **Exit 2** → blocking error; stderr fed to Claude
- **Other** → non-blocking error; stderr in verbose mode only
- All matching hooks run in parallel; identical handlers deduplicated
- `async: true` runs command in background (non-blocking; command hooks only)

### Registration Format (settings.json)
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": ".claude/hooks/validate.sh", "timeout": 30 }
        ]
      }
    ]
  }
}
```

### Known Bugs
| Bug | Symptom | Workaround |
|-----|---------|-----------|
| #15174 / #13650 | `SessionStart` `compact` matcher unreliable after auto-compact | Use `PreCompact` to save state instead |
| #13668 | `transcript_path` in `PreCompact` stdin may be null | Always check `if [ -n "$TRANSCRIPT_PATH" ]` |
| Hook changes mid-session | Direct file edits don't take effect (security by design) | Restart or review via `/hooks` menu |
| HTTP hooks blocking | Non-2xx → non-blocking only | Return 2xx with `decision: "block"` JSON |

---

## 4. settings.json Schema

### Top-Level Keys (selected)

| Key | Category | Description |
|-----|----------|-------------|
| `hooks` | Core | Hook event registrations |
| `permissions` | Core | allow/ask/deny rules + additionalDirectories |
| `env` | Core | Environment variables for every session |
| `model` | Model | Default model override |
| `availableModels` | Model | Restrict selectable models |
| `modelOverrides` | Model | Map model IDs to provider-specific IDs (Bedrock/Vertex) |
| `disableAllHooks` | Hooks | Disable hooks without removing them |
| `allowManagedHooksOnly` | Hooks | Block user/project hooks |
| `allowedHttpHookUrls` | Hooks | URL allowlist for HTTP hooks |
| `sandbox` | Security | Bash sandboxing (filesystem + network) |
| `autoMemoryDirectory` | Memory | Custom auto memory location |
| `autoMemoryEnabled` | Memory | Toggle auto memory |
| `teammateMode` | Teams | `auto`, `in-process`, `tmux` |
| `statusLine` | UI | Custom status line config |
| `language` | UI | Claude's response language |
| `alwaysThinkingEnabled` | Model | Extended thinking always on |
| `showTurnDuration` | UI | Show turn duration messages |
| `plansDirectory` | Storage | Custom plan file path |
| `cleanupPeriodDays` | Storage | Session cleanup threshold (default: 30) |
| `includeGitInstructions` | Content | `false` = remove built-in git workflow instructions |
| `disableBypassPermissionsMode` | Security | Prevent bypass mode (managed only) |
| `fastModePerSessionOptIn` | Model | Require per-session fast mode opt-in |

### Permissions Format
```json
{
  "permissions": {
    "allow": ["Bash(npm run *)", "Read(~/.zshrc)"],
    "ask":   ["Bash(git push *)"],
    "deny":  ["Bash(curl *)", "Read(./.env)"],
    "additionalDirectories": ["../docs/"],
    "defaultMode": "acceptEdits"
  }
}
```
- Evaluation order: **deny → ask → allow** (deny wins first match)
- Array settings **MERGE** across scopes (not replace)

### Scope Priority (highest → lowest)

| Scope | Location | Shareable |
|-------|----------|-----------|
| Managed | `/Library/Application Support/ClaudeCode/managed-settings.json` | Admin only |
| Local | `.claude/settings.local.json` | No (gitignored) |
| Project | `.claude/settings.json` | Yes (committed) |
| User | `~/.claude/settings.json` | No |

---

## 5. Skills System

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | No | Slash command name (dir name used if omitted) |
| `description` | Recommended | When to use; drives auto-invocation |
| `argument-hint` | No | Autocomplete hint |
| `disable-model-invocation` | No | `true` = user-only, Claude cannot auto-invoke |
| `user-invocable` | No | `false` = hidden from `/` menu, Claude-only |
| `allowed-tools` | No | Tools allowed without per-use approval |
| `model` | No | Override model for skill execution |
| `context` | No | `fork` = run in isolated subagent context |
| `agent` | No | Subagent type with `context: fork` |
| `hooks` | No | Hooks scoped to skill lifecycle |

### Invocation & Discovery
- **Direct:** `/skill-name [args]`; **Auto:** when description matches conversation
- `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N`, `${CLAUDE_SESSION_ID}`, `${CLAUDE_SKILL_DIR}` substitutions
- `!`command`` syntax: execute shell commands, inject output into skill before Claude sees it
- Priority: enterprise > personal (`~/.claude/skills/`) > project (`.claude/skills/`) > plugin
- Descriptions loaded at session start (2% context budget, fallback 16K chars); full content on invocation
- Skills edited during session are picked up without restart (live reload)
- v2.1.3: slash commands (`.claude/commands/`) merged into skills — both formats still work

---

## 6. CLAUDE.md

### Loading Order

| Scope | Location | Notes |
|-------|----------|-------|
| Managed policy | `/Library/Application Support/ClaudeCode/CLAUDE.md` | Cannot be excluded |
| Personal | `~/.claude/CLAUDE.md` | All projects |
| Project | `./CLAUDE.md` or `./.claude/CLAUDE.md` | Team-shared |
| Ancestor dirs | `../../CLAUDE.md` etc. | Loaded at launch |
| Subdirectory | `./src/CLAUDE.md` | **On demand** only (when Claude reads files there) |
| Rules | `.claude/rules/*.md` | At launch; `paths` frontmatter = on demand |

- `@path/to/file` imports inline; relative paths from containing file; max **5 hops**
- `claudeMdExcludes` in `.claude/settings.local.json` can skip specific files (managed cannot be excluded)
- CLAUDE.md fully survives `/compact` — re-read from disk on compaction

### Size Recommendations
- Target **< 200 lines** per CLAUDE.md file
- Use `IMPORTANT` / `YOU MUST` emphasis for critical rules
- Add `## Compact Instructions` section: Claude preserves it when compacting

---

## 7. Workflow Files

- `.claude/workflow/` = **custom project convention** — NOT an official Claude Code structure
- Official recommended layout uses `.claude/skills/`, `.claude/agents/`, `.claude/rules/`
- Equivalent official patterns:

| Custom pattern | Official equivalent |
|---------------|---------------------|
| `workflow/` files loaded via CLAUDE.md | `@` imports or path-scoped rules |
| Session-start workflow | `SessionStart` hook + CLAUDE.md `## Workflow` section |
| Before-commit workflow | Pre-commit hook + `/verify` skill with `disable-model-invocation: true` |
| Human checkpoints | `AskUserQuestion` tool in agents; `plan` permission mode |
| Verification agents | Custom agents in `.claude/agents/` + skills with `context: fork` |

---

## 8. Agent Teams

### TeamCreate API
- Requires: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` env var; Claude Code v2.1.32+
- Parameters: `team_name`, `description`, `agent_type`
- Storage: `~/.claude/teams/{name}/config.json` + `~/.claude/tasks/{name}/`

### SendMessage Types

| Type | Purpose |
|------|---------|
| `message` | Direct DM to one teammate |
| `broadcast` | All teammates (use sparingly — scales linearly) |
| `shutdown_request` | Ask teammate to shut down gracefully |
| `shutdown_response` | Approve/reject shutdown |
| `plan_approval_response` | Approve/reject teammate's plan |

### Architecture Constraints
- No nested teams; teammates CANNOT spawn their own teams/teammates
- One team per lead session; lead is fixed for team lifetime
- Each teammate has own context window — does NOT inherit lead's history
- In-process teammates: `/resume` and `/rewind` do NOT restore them
- Task status can lag — monitor and nudge teammates

### Task Tools

| Tool | Purpose |
|------|---------|
| `TaskCreate` | Define work unit with dependencies |
| `TaskUpdate` | Claim, complete, or delete task |
| `TaskGet` | Get task details |
| `TaskList` | List all tasks with status |
| `TaskOutput` | Read background task output |
| `TaskStop` | Stop a running task |

- Task states: `pending` → `in_progress` → `completed`
- File locking prevents race conditions on simultaneous claims
- Dependency tracking: blocked tasks auto-unblock when dependencies complete

### Team Size Recommendations
- Optimal: 3–5 teammates
- > 5–6: coordination overhead exceeds parallel benefit

---

## 9. New Features (Jan–Mar 2026)

**Current version:** 2.1.74 (March 12, 2026)

### New Hook Types (all in current docs)
| Hook | Added | Trigger |
|------|-------|---------|
| `TeammateIdle` | v2.1.32 | Teammate about to go idle |
| `TaskCompleted` | v2.1.32 | Task being marked complete |
| `InstructionsLoaded` | ~v2.1.50 | CLAUDE.md / rules file loaded |
| `ConfigChange` | ~v2.1.50 | Config file changes during session |
| `WorktreeCreate` | ~v2.1.60 | Worktree created |
| `WorktreeRemove` | ~v2.1.60 | Worktree removed |

### New Tools
| Tool | Version | Description |
|------|---------|-------------|
| `ExitWorktree` | v2.1.72 | Leave EnterWorktree session |
| `CronCreate` | v2.1.71 | Schedule recurring prompts/commands |
| `CronList` | v2.1.71 | List scheduled cron jobs |
| `CronDelete` | v2.1.71 | Remove cron jobs |

### Model Changes
- Sonnet 4.6 (v2.1.45): **1M context** support (disable: `CLAUDE_CODE_DISABLE_1M_CONTEXT`)
- Opus 4.6: default medium effort
- Opus 4 and Opus 4.1: **removed** (v2.1.68) — auto-migrated to Opus 4.6

### Key New Settings Keys (2026)
- `autoMemoryDirectory`, `autoMemoryEnabled` — auto memory control
- `modelOverrides` — Bedrock/Vertex model ID mapping
- `teammateMode` — `in-process | tmux | auto`
- `includeGitInstructions: false` — remove built-in git instructions
- `plansDirectory` — custom plan storage
- `allowedHttpHookUrls`, `httpHookAllowedEnvVars` — HTTP hook security
- `sandbox` — Bash filesystem + network isolation
- `alwaysThinkingEnabled`, `showTurnDuration`, `spinnerVerbs`
- `disableBypassPermissionsMode` — managed policy only

### Deprecations / Breaking Changes
| Item | Version | Action |
|------|---------|--------|
| `/output-style` command | v2.1.73 | → `/config` |
| npm installations | v2.1.15 | → `claude install` |
| Opus 4 / 4.1 models | v2.1.68 | Auto-migrated to Opus 4.6 |
| `.claude/commands/` slash commands | v2.1.3 | Merged into skills (both still work) |
| Tool results persistence threshold | v2.1.51 | Reduced 100K → 50K characters |
