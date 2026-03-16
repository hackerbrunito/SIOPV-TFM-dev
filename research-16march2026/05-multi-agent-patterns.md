# Claude Code Multi-Agent Systems: Best Practices (March 2026)

> Research compiled 2026-03-16. Sources: official Anthropic docs, engineering blogs, community guides.

---

## Table of Contents

1. [TeamCreate — How Teams Work](#1-teamcreate--how-teams-work)
2. [Custom Agent Definition Files (.claude/agents/)](#2-custom-agent-definition-files-claudeagents)
3. [Agent Tool — All Parameters](#3-agent-tool--all-parameters)
4. [Permission Mode Options](#4-permission-mode-options)
5. [Isolation: Worktree](#5-isolation-worktree)
6. [SendMessage / TaskCreate / TaskUpdate Coordination](#6-sendmessage--taskcreate--taskupdate-coordination)
7. [Background vs. Foreground Agents](#7-background-vs-foreground-agents)
8. [Multi-Agent Orchestration Architecture](#8-multi-agent-orchestration-architecture)
9. [Agent Model Selection](#9-agent-model-selection)
10. [Common Pitfalls](#10-common-pitfalls)

---

## 1. TeamCreate — How Teams Work

### What Are Agent Teams?

Agent teams coordinate multiple Claude Code instances working together. One session acts as the **team lead**, coordinating work, assigning tasks, and synthesizing results. **Teammates** work independently, each in its own context window, and communicate directly with each other via a shared mailbox.

> "Unlike subagents, which run within a single session and can only report back to the main agent, you can also interact with individual teammates directly without going through the lead." — [Official Docs](https://code.claude.com/docs/en/agent-teams)

### Enabling Agent Teams

Agent teams are **experimental and disabled by default**. Enable via `settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

Requires Claude Code **v2.1.32+**.

### Architecture Components

| Component | Role |
|-----------|------|
| **Team Lead** | Main session that creates the team, spawns teammates, coordinates work |
| **Teammates** | Separate Claude Code instances, each with own context window |
| **Task List** | Shared work items stored at `~/.claude/tasks/{team-name}/` |
| **Mailbox** | Messaging system for direct agent-to-agent communication |

Team config stored at `~/.claude/teams/{team-name}/config.json`.

### Teams vs. Subagents

| Feature | Subagents | Agent Teams |
|---------|-----------|-------------|
| **Context** | Own window; results return to caller | Own window; fully independent |
| **Communication** | Report back to main agent only | Message each other directly |
| **Coordination** | Main agent manages all work | Shared task list + self-coordination |
| **Best for** | Focused tasks; only result matters | Complex work needing discussion |
| **Token cost** | Lower (summarized back) | Higher (each is separate Claude instance) |
| **Spawn** | Cannot spawn other subagents | Cannot spawn nested teams |

### Display Modes

- **In-process** (default): All teammates in main terminal. `Shift+Down` to cycle.
- **Split panes**: Each teammate gets own pane. Requires `tmux` or iTerm2.

Set via `"teammateMode": "in-process" | "tmux" | "auto"` in settings.json.

### Best Use Cases

1. **Research and review** — Multiple perspectives simultaneously
2. **New modules/features** — Each teammate owns separate files
3. **Debugging with competing hypotheses** — Parallel theory testing
4. **Cross-layer coordination** — Frontend, backend, tests each owned by different teammate

### When NOT to Use Teams

- Sequential tasks
- Same-file edits
- Tasks with many inter-dependencies
- Simple/routine work (cost overhead not justified)

---

## 2. Custom Agent Definition Files (.claude/agents/)

### File Format

Markdown files with YAML frontmatter. The body becomes the system prompt.

```markdown
---
name: code-reviewer
description: Reviews code for quality and best practices
tools: Read, Glob, Grep
model: sonnet
---

You are a code reviewer. Analyze code and provide actionable feedback.
```

### Storage Locations (priority order)

| Location | Scope | Priority |
|----------|-------|----------|
| `--agents` CLI flag | Current session only | 1 (highest) |
| `.claude/agents/` | Current project | 2 |
| `~/.claude/agents/` | All projects | 3 |
| Plugin `agents/` dir | Where plugin enabled | 4 (lowest) |

When names collide, higher-priority location wins.

### Complete Frontmatter Schema

| Field | Required | Description |
|-------|----------|-------------|
| `name` | **Yes** | Unique identifier (lowercase + hyphens) |
| `description` | **Yes** | When Claude should delegate to this agent |
| `tools` | No | Allowlist of tools. Inherits all if omitted |
| `disallowedTools` | No | Denylist of tools (removed from inherited set) |
| `model` | No | `sonnet`, `opus`, `haiku`, full model ID, or `inherit` (default) |
| `permissionMode` | No | `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan` |
| `maxTurns` | No | Max agentic turns before stop |
| `skills` | No | Skills to preload into context at startup |
| `mcpServers` | No | MCP servers available (inline def or name reference) |
| `hooks` | No | Lifecycle hooks scoped to this agent |
| `memory` | No | Persistent memory scope: `user`, `project`, `local` |
| `background` | No | `true` to always run as background task (default: `false`) |
| `isolation` | No | `worktree` to run in temporary git worktree |

### Tool Restriction for Spawning

Use `Agent(worker, researcher)` syntax in `tools` to restrict which subagent types can be spawned:

```yaml
---
name: coordinator
tools: Agent(worker, researcher), Read, Bash
---
```

### Memory Scopes

| Scope | Location | Use |
|-------|----------|-----|
| `user` | `~/.claude/agent-memory/<name>/` | Cross-project learnings |
| `project` | `.claude/agent-memory/<name>/` | Project-specific (VCS-shareable) |
| `local` | `.claude/agent-memory-local/<name>/` | Project-specific (not VCS) |

### MCP Server Scoping

Define MCP servers inline (only available to that agent) or reference by name (shared):

```yaml
mcpServers:
  - playwright:
      type: stdio
      command: npx
      args: ["-y", "@playwright/mcp@latest"]
  - github  # reference by name
```

> "To keep an MCP server out of the main conversation entirely and avoid its tool descriptions consuming context there, define it inline here rather than in .mcp.json." — [Official Docs](https://code.claude.com/docs/en/sub-agents)

### CLI-Defined Agents (Session-Only)

```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer",
    "prompt": "You are a senior code reviewer.",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  }
}'
```

---

## 3. Agent Tool — All Parameters

The `Agent` tool (renamed from `Task` in v2.1.63) spawns subagents. Key parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `description` | string (required) | 3-5 word summary of what the agent will do |
| `prompt` | string (required) | Full task description with all necessary context |
| `subagent_type` | string | Which specialized agent to use (`general-purpose`, `Explore`, `Plan`, custom name) |
| `mode` | enum | Permission mode: `acceptEdits`, `bypassPermissions`, `default`, `dontAsk`, `plan`, `auto` |
| `isolation` | enum | `worktree` for git worktree isolation |
| `model` | enum | `sonnet`, `opus`, `haiku` — overrides agent definition's model |
| `team_name` | string | Team to spawn into (for agent teams) |
| `name` | string | Addressable name for `SendMessage(to: name)` |
| `run_in_background` | boolean | `true` to run concurrently (non-blocking) |
| `resume` | string | Agent ID to resume from previous invocation |

### Built-in Subagent Types

| Type | Model | Tools | Purpose |
|------|-------|-------|---------|
| `Explore` | Haiku | Read-only | Fast codebase search/analysis |
| `Plan` | Inherit | Read-only | Research for planning mode |
| `general-purpose` | Inherit | All | Complex multi-step tasks |

### Key Behaviors

- Subagents **cannot spawn other subagents** (no nesting)
- Each invocation starts fresh unless `resume` is used
- Results return to parent; full output stays in subagent context
- Subagent transcripts stored at `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl`

---

## 4. Permission Mode Options

| Mode | Behavior | Use Case |
|------|----------|----------|
| `default` | Standard prompts for each tool | Interactive development |
| `acceptEdits` | Auto-accept file edits; other tools still prompt | Trusted edit workflows |
| `dontAsk` | Auto-deny unless pre-approved via allow rules | Headless agents with fixed tool surface |
| `bypassPermissions` | Skip ALL permission checks | Containers/VMs only |
| `plan` | Read-only exploration, no writes/executes | Safe code analysis |

### Critical Rules

- **`bypassPermissions`** only works fully when the parent session was started with `--dangerously-skip-permissions`. Without it, the mode parameter has limited effect.
- If parent uses `bypassPermissions`, it **takes precedence** and cannot be overridden by children.
- All teammates inherit the lead's permission settings at spawn time. You can change individual modes after spawning.
- `dontAsk` is ideal for CI/CD agents: tools in `permissions.allow` run normally; everything else is hard-denied.

### Precedence Chain

```
deny (any level) > ask > allow
managed settings > CLI args > local project > shared project > user settings
```

> "If a tool is denied at any level, no other level can allow it." — [Official Docs](https://code.claude.com/docs/en/permissions)

---

## 5. Isolation: Worktree

### What It Does

Setting `isolation: "worktree"` creates a **temporary git worktree** — an isolated copy of the repository. Each agent gets its own files and branch while sharing the same git history and remote.

### When to Use

- **Parallel implementation** — Multiple agents editing the same files without conflicts
- **Exploratory/risky changes** — Try approaches without affecting main working directory
- **Batch migrations** — Spawn N agents, each handling different files in their own worktree

### How It Works

1. Agent gets a new worktree under `.claude/worktrees/` with a dedicated branch
2. All file operations are isolated from the main working directory
3. If the agent makes **no changes**, the worktree is automatically cleaned up
4. If changes are made, the worktree path and branch are returned in the result
5. You then review and merge the branch

### Configuration

In agent definition frontmatter:
```yaml
isolation: worktree
```

Or in Agent tool call:
```python
Agent(isolation="worktree", ...)
```

Or via CLI:
```bash
claude --worktree my-feature
```

### Best Practices

- Run `/init` in each new worktree session
- Name worktrees meaningfully (`claude --worktree auth-refactor`)
- Use `--tmux` flag to launch worktree agents in their own tmux sessions
- Always `git pull --rebase origin main` before pushing from worktree

> "Spawn 5 agents, each handling 10 files in their own worktree, and they all run in parallel without stepping on each other." — Community pattern documented by multiple sources

### Native Support Timeline

- Built-in git worktree support shipped in **Claude Code v2.1.49** (February 19, 2026)
- The built-in `/batch` command uses this pattern internally

---

## 6. SendMessage / TaskCreate / TaskUpdate Coordination

### SendMessage

Enables direct agent-to-agent communication within a team.

```python
SendMessage(to="researcher", message="Start investigating auth module", summary="Assign auth task")
SendMessage(to="*", message="Critical blocker found", summary="Team-wide alert")  # broadcast
```

**Message types:**
- **Plain text** — Direct communication
- **shutdown_request** / **shutdown_response** — Graceful teardown protocol
- **plan_approval_request** / **plan_approval_response** — Gate implementation on plan review

**Rules:**
- Broadcast (`to: "*"`) sends to ALL teammates — **use sparingly** (costs scale linearly)
- Plain text output is NOT visible to teammates — you MUST use SendMessage
- Structured protocol messages cannot be broadcast

### TaskCreate

Creates discrete work items in the shared task list:

```python
TaskCreate(
  description="Refactor auth module",
  assigned_to="backend-dev",  # optional
  blocked_by=["task-123"]     # optional dependencies
)
```

**Task states:** `pending` → `in_progress` → `completed`

**Dependency management:**
- Use `addBlockedBy` / `addBlocks` parameters to express ordering
- Blocked tasks cannot be claimed until dependencies complete
- System auto-unblocks when prerequisites complete
- File locking prevents race conditions on task claiming

### TaskUpdate

```python
TaskUpdate(task_id="abc", status="in_progress")  # claim
TaskUpdate(task_id="abc", status="completed")     # finish
```

### Coordination Patterns

1. **Lead assigns explicitly** — Tell lead which task goes to which teammate
2. **Self-claim** — After finishing, teammate picks next unassigned/unblocked task
3. **Dependency waves** — Wave 1 tasks complete → Wave 2 auto-unblocks
4. **Plan-then-execute** — Require plan approval before implementation starts

### Quality Gates via Hooks

- **`TeammateIdle`** — Runs when teammate about to go idle. Exit code 2 = send feedback, keep working.
- **`TaskCompleted`** — Runs when task being marked complete. Exit code 2 = prevent completion, send feedback.

---

## 7. Background vs. Foreground Agents

### Foreground (Default)

- **Blocks** main conversation until complete
- Permission prompts pass through to user
- `AskUserQuestion` works normally
- Best when: you need results before proceeding

### Background

- Runs **concurrently** while you continue working
- Before launch, Claude prompts for permissions upfront
- Auto-denies anything not pre-approved
- `AskUserQuestion` fails (but agent continues)
- You're notified when it completes

### When to Use Which

| Scenario | Mode | Reason |
|----------|------|--------|
| Research informing next steps | Foreground | Need results to proceed |
| Independent test runs | Background | Don't need result immediately |
| Parallel exploration | Background | Genuinely independent work |
| Sequential dependency chain | Foreground | Each step needs prior result |

### Configuration

In agent definition:
```yaml
background: true  # always run as background
```

Or at invocation:
```python
Agent(run_in_background=True, ...)
```

**Key rule:** Do NOT poll or sleep waiting for background agents. You'll be automatically notified when they complete.

If a background agent fails due to missing permissions, you can **resume it in foreground**:
```python
Agent(resume="agent-id-here")  # continues in foreground with interactive prompts
```

### Ctrl+B Shortcut

Press **Ctrl+B** to background a currently running foreground task.

---

## 8. Multi-Agent Orchestration Architecture

### Anthropic's Recommended Patterns

#### Pattern 1: Orchestrator-Subagent (Hierarchical)

```
Lead (Opus) → spawns specialized subagents (Sonnet/Haiku)
           → synthesizes results
           → decides next steps
```

Best for: teams new to multi-agent systems, clear task decomposition.

#### Pattern 2: Peer Collaboration (Agent Teams)

```
Lead (coordinates) ←→ Teammate A ←→ Teammate B ←→ Teammate C
                    ↕               ↕               ↕
                  [Shared Task List]
```

Best for: tasks requiring inter-agent discussion (debugging, review).

#### Pattern 3: Verification Subagent

> "One consistently effective pattern pairs a main agent with a dedicated agent whose sole responsibility is testing or validating the main agent's work." — [Anthropic Engineering](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them)

Critical: explicitly require comprehensive validation — verification agents tend to "mark outputs as passing without thorough testing."

### Anthropic's Multi-Agent Research System Findings

Key architecture decisions from Anthropic's internal system ([source](https://www.anthropic.com/engineering/multi-agent-research-system)):

1. **Planning with persistence** — Lead uses extended thinking, saves plans to external memory
2. **Explicit effort scaling** — Simple queries: 1 agent, 3-10 tool calls. Complex: 10+ subagents
3. **Context-centric decomposition** — Divide by context boundaries, NOT by problem type
4. **Output to filesystem** — Store artifacts in files rather than passing through conversation history
5. **Breadth-first search** — Start broad, then narrow focus
6. **Parallelization** — 3-5 subagents + 3+ parallel tools per subagent = up to 90% time reduction

> "Token usage by itself explains 80% of the variance [in quality]." — Anthropic Research

### C Compiler Case Study (Anthropic, Feb 2026)

Anthropic validated agent teams by building a 100,000-line Rust C compiler using 16 parallel agents:

- **2,000 Claude Code sessions** over two weeks
- **2 billion input tokens, 140M output tokens** (~$20,000)
- **Lock-file coordination**: agents claim tasks via `current_tasks/` directory
- **Critical lesson**: "The task verifier must be nearly perfect, otherwise Claude will solve the wrong problem"
- **Result**: Compiles bootable Linux 6.9, QEMU, FFmpeg, SQLite, PostgreSQL, Redis; 99% GCC torture test pass rate

Source: [Building a C Compiler with Claude](https://www.anthropic.com/engineering/building-c-compiler)

### Recommended Team Structure

| Team Size | Use Case |
|-----------|----------|
| 2-3 | Most workflows — balanced parallelism with manageable coordination |
| 3-5 | Complex research, multi-perspective review |
| 5+ | Only when work is genuinely independent (batch migrations) |

**Task ratio**: 5-6 tasks per teammate keeps everyone productive.

> "Three focused teammates often outperform five scattered ones." — [Official Docs](https://code.claude.com/docs/en/agent-teams)

---

## 9. Agent Model Selection

### Current Models (March 2026)

| Model | Cost (input/output per MTok) | Context | Best For |
|-------|------------------------------|---------|----------|
| **Haiku 4.5** | $1 / $5 | 200K | High-volume, simple tasks, exploration |
| **Sonnet 4.6** | $3 / $15 | 1M | Daily work, features, debugging |
| **Opus 4.6** | $5 / $25 | 1M | Complex agents, architecture, deep analysis |

### Three-Tier Hierarchy (Recommended)

| Role | Model | Rationale |
|------|-------|-----------|
| **Team Lead / Coordinator** | Opus 4.6 | Strongest reasoning for decomposition and synthesis |
| **Teammates / Workers** | Sonnet 4.6 | 60% cheaper input, handles multi-file logic well |
| **Exploration / Simple subtasks** | Haiku 4.5 | Fastest, cheapest; great for search/classification |

### `opusplan` Alias

Automated hybrid approach:
- **Plan mode** → Uses Opus for reasoning and architecture
- **Execution mode** → Switches to Sonnet for implementation

### Cost Comparison

| Configuration | Approximate Tokens | Cost |
|--------------|-------------------|------|
| Solo session | ~200K | ~$1-2 |
| Subagents (3) | ~440K | ~$4-5 |
| Agent team (3 teammates) | ~800K | ~$8-15 |
| Agent team (5 teammates) | ~1.35M | ~$15-25 |

> "The biggest cost optimization in any AI system is not prompt engineering or caching; it is routing each task to the cheapest model that can handle it reliably." — Community consensus

### Decision Framework

```
Assess complexity:
  HIGH (multi-file, architecture, synthesis)  → Opus
  MEDIUM (features, debugging, integration)   → Sonnet
  LOW (search, format, docs, classification)  → Haiku
```

---

## 10. Common Pitfalls

### Pitfall 1: File Conflicts

**Problem:** Two teammates editing the same file → overwrites.

**Fix:** Break work so each teammate owns different files. Use `isolation: worktree` for implementation tasks that might overlap.

> "This is the single most important rule for implementation tasks." — Multiple sources

### Pitfall 2: Excessive Team Size

**Problem:** 8-agent teams where coordination overhead exceeds productivity.

**Fix:** Start with 3 teammates. Scale up only when work is genuinely independent. "More than 4-5 active agents frequently step on each other's work."

### Pitfall 3: Lead Self-Implementation

**Problem:** Lead starts implementing instead of waiting for teammates.

**Fix:** Explicitly tell the lead: "Wait for your teammates to complete their tasks before proceeding." Use delegate mode (`Shift+Tab`).

### Pitfall 4: Problem-Type Decomposition

**Problem:** Dividing by role (writer, tester, reviewer) creates constant handoff overhead.

**Fix:** Decompose by **context boundaries** — each agent gets a self-contained unit of work.

> "Agents engage in a telephone game, passing information back and forth with each handoff degrading fidelity." — [Anthropic](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them)

### Pitfall 5: Insufficient Context in Spawn Prompts

**Problem:** Teammates don't inherit the lead's conversation history.

**Fix:** Include ALL task-specific details in the spawn prompt. Be generous with context.

### Pitfall 6: Token Waste on Simple Tasks

**Problem:** Using agent teams for work a single session could handle.

**Fix:** Agent teams cost 3-7x more tokens. Reserve for genuinely parallelizable work.

> "Start with the simplest approach that works, and add complexity only when evidence supports it." — [Anthropic](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them)

### Pitfall 7: Weak Verification Agents

**Problem:** Verification agents "mark outputs as passing without thorough testing."

**Fix:** Explicitly require comprehensive validation. Add quality gate hooks (`TaskCompleted` with exit code 2 to reject).

### Pitfall 8: No Session Resumption

**Problem:** `/resume` and `/rewind` don't restore in-process teammates.

**Fix:** After resume, tell lead to spawn new teammates. Design for this limitation.

### Pitfall 9: `bypassPermissions` Misconception

**Problem:** Setting `mode: "bypassPermissions"` in Agent() thinking it bypasses prompts.

**Fix:** Only works when parent session started with `--dangerously-skip-permissions`. Without it, the parameter has no effect. Additionally, `bypassPermissions` forces the Opus model regardless of parent model.

### Pitfall 10: Orphaned Resources

**Problem:** tmux sessions and task files persisting after team ends.

**Fix:** Always use the lead to clean up (`Clean up the team`). Shut down all teammates first. Check `tmux ls` for stragglers.

---

## Key Takeaways

1. **Default to single-agent or subagents.** Only use teams when parallel communication is genuinely needed.
2. **3 teammates is the sweet spot.** More than 5 is almost always counterproductive.
3. **Decompose by context, not role.** Each agent should own a self-contained scope.
4. **Opus leads, Sonnet works, Haiku explores.** Route by complexity.
5. **Plan first, parallelize second.** Review the dependency graph before committing tokens.
6. **Verification must be explicit.** Don't trust agents to validate thoroughly by default.
7. **File ownership is non-negotiable.** No two agents should edit the same file.
8. **Context in spawn prompts must be complete.** Teammates don't inherit history.
9. **Use worktrees for implementation parallelism.** They prevent file conflicts at the git level.
10. **Monitor and steer.** Unattended teams drift. Check in regularly.

---

## Sources

- [Orchestrate teams of Claude Code sessions — Official Docs](https://code.claude.com/docs/en/agent-teams)
- [Create custom subagents — Official Docs](https://code.claude.com/docs/en/sub-agents)
- [Configure permissions — Official Docs](https://code.claude.com/docs/en/permissions)
- [When to use multi-agent systems — Anthropic Blog](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them)
- [How we built our multi-agent research system — Anthropic Engineering](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Building a C Compiler with Claude — Anthropic Engineering](https://www.anthropic.com/engineering/building-c-compiler)
- [From Tasks to Swarms: Agent Teams in Claude Code — alexop.dev](https://alexop.dev/posts/from-tasks-to-swarms-agent-teams-in-claude-code/)
- [Claude Code Agent Teams: The Practical Guide — LaoZhang AI](https://blog.laozhang.ai/en/posts/claude-code-agent-teams)
- [Claude Code Agent Teams: Complete Guide 2026 — claudefa.st](https://claudefa.st/blog/guide/agents/agent-teams)
- [Claude Haiku vs Sonnet vs Opus in 2026 — DEV Community](https://dev.to/clawgenesis/untitled-dcm)
- [Model configuration — Official Docs](https://code.claude.com/docs/en/model-config)
- [Claude Code Worktree Setup Guide — Verdent](https://www.verdent.ai/guides/claude-code-worktree-setup-guide)
- [Git Worktree Isolation in Claude Code — Medium](https://medium.com/@richardhightower/git-worktree-isolation-in-claude-code-parallel-development-without-the-chaos-262e12b85cc5)
