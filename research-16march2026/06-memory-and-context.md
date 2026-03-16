# Claude Code Memory System, Context Management & Workflow Patterns

> **Research Date:** 2026-03-16
> **Scope:** Claude Code auto-memory, MEMORY.md, context management, compaction, session resumption, skills vs. memory vs. CLAUDE.md
> **Sources:** Official Anthropic docs, changelog, community research, blog posts

---

## Table of Contents

1. [Auto-Memory System](#1-auto-memory-system)
2. [Memory Types](#2-memory-types-user-feedback-project-reference)
3. [MEMORY.md Index Structure](#3-memorymd-index-structure)
4. [CLAUDE.md File Hierarchy & Loading Order](#4-claudemd-file-hierarchy--loading-order)
5. [@file Import Syntax](#5-file-import-syntax)
6. [Rules (.claude/rules/)](#6-rules-clauderules)
7. [Skills vs. Memory vs. CLAUDE.md — When to Use Which](#7-skills-vs-memory-vs-claudemd--when-to-use-which)
8. [Context Window & Compaction](#8-context-window--compaction)
9. [PreCompact and PostCompact Hooks](#9-precompact-and-postcompact-hooks)
10. [Session Management & Resumption](#10-session-management--resumption)
11. [Subagent Memory](#11-subagent-memory)
12. [Best Practices for Long Sessions](#12-best-practices-for-long-sessions)
13. [New Features in Early 2026](#13-new-features-in-early-2026)

---

## 1. Auto-Memory System

Auto-memory lets Claude accumulate knowledge across sessions **without user intervention**. Claude writes notes for itself as it works: build commands, debugging insights, architecture notes, code style preferences, and workflow habits.

### Key Characteristics

| Property | Detail |
|----------|--------|
| **Author** | Claude (not the user) |
| **Content** | Learnings and patterns |
| **Scope** | Per working tree (per git repo) |
| **Loaded** | First 200 lines of MEMORY.md at session start |
| **Toggle** | `/memory` command, `autoMemoryEnabled` setting, or `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` env var |
| **Minimum version** | Claude Code v2.1.59+ |
| **Default state** | Enabled |

### Storage Location

```
~/.claude/projects/<project>/memory/
├── MEMORY.md          # Concise index, loaded into every session
├── debugging.md       # Detailed notes on debugging patterns
├── api-conventions.md # API design decisions
└── ...                # Any other topic files Claude creates
```

> "The `<project>` path is derived from the git repository, so all worktrees and subdirectories within the same repo share one auto memory directory." — [Official Docs](https://code.claude.com/docs/en/memory)

Custom storage location via settings:
```json
{
  "autoMemoryDirectory": "~/my-custom-memory-dir"
}
```
This setting is accepted from policy, local, and user settings — **not** from project settings (`.claude/settings.json`) to prevent redirecting memory writes to sensitive locations.

### How It Works

1. First 200 lines of `MEMORY.md` are loaded at the start of **every** conversation
2. Content beyond line 200 is **not** loaded at session start
3. Claude keeps `MEMORY.md` concise by moving detailed notes into separate topic files
4. Topic files (e.g., `debugging.md`, `patterns.md`) are **not** loaded at startup — Claude reads them on demand
5. When you see "Writing memory" or "Recalled memory" in the interface, Claude is actively updating/reading from the memory directory

### What Claude Records

- **Project patterns**: Build commands, test conventions, code style preferences
- **Debugging insights**: Solutions to tricky problems, common error causes
- **Architecture notes**: Key files, module relationships, important abstractions
- **User preferences**: Communication style, workflow habits, tool choices

### Explicit Save

Users can trigger saves directly: `"remember that we use pnpm, not npm"` — Claude saves to auto memory. To save to CLAUDE.md instead, say `"add this to CLAUDE.md"`.

---

## 2. Memory Types: user, feedback, project, reference

The auto-memory system supports four discrete memory types, each with specific frontmatter and purpose:

### Memory File Frontmatter Format

```markdown
---
name: {{memory name}}
description: {{one-line description — used to decide relevance in future conversations}}
type: {{user | feedback | project | reference}}
---

{{memory content}}
```

### Type Details

| Type | Description | When to Save | How to Use |
|------|-------------|--------------|------------|
| **user** | Information about the user's role, goals, responsibilities, knowledge | When you learn details about the user's role, preferences, responsibilities | Tailor behavior to user's profile; adjust explanation depth |
| **feedback** | Guidance or corrections the user has given | When user corrects your approach in a reusable way ("don't mock the database", "stop summarizing") | Let these guide behavior so user doesn't repeat themselves |
| **project** | Ongoing work, goals, initiatives, bugs, incidents not derivable from code/git | When you learn who is doing what, why, by when. Convert relative dates to absolute. | Understand broader context behind user requests |
| **reference** | Pointers to external system locations | When you learn about resources in external systems (Linear project, Grafana board, Slack channel) | When user references external systems |

### Body Structure for feedback and project Types

```markdown
Lead with the rule/fact itself.

**Why:** the reason the user gave — often a past incident or strong preference
**How to apply:** when/where this guidance kicks in
```

### What NOT to Save

- Code patterns, conventions, architecture, file paths — derivable from current project state
- Git history, recent changes — `git log` / `git blame` are authoritative
- Debugging solutions — the fix is in the code
- Anything already in CLAUDE.md files
- Ephemeral task details, in-progress work, current conversation context

### MEMORY.md as Index

`MEMORY.md` is an **index**, not a memory file itself. It should contain only links to memory files with brief descriptions. Lines after 200 will be truncated. Memory content goes in individual topic files, not in the index.

---

## 3. MEMORY.md Index Structure

The MEMORY.md file acts as a lightweight index that Claude reads at session start:

```markdown
# Project Memory

## Identity
- [User profile](user_role.md) — role, expertise, preferences

## Feedback
- [Testing rules](feedback_testing.md) — no mocking in integration tests
- [Response style](feedback_style.md) — terse, no trailing summaries

## Project Context
- [Current sprint](project_sprint.md) — merge freeze after March 5

## References
- [Bug tracker](reference_linear.md) — pipeline bugs in Linear "INGEST"
```

**Critical constraints:**
- Keep under 200 lines (only first 200 loaded at startup)
- Organize semantically by topic, not chronologically
- Update or remove stale memories
- Check for existing memory before creating duplicates

---

## 4. CLAUDE.md File Hierarchy & Loading Order

### Location Priority (most specific wins)

| Scope | Location | Purpose | Shared With |
|-------|----------|---------|-------------|
| **Managed policy** | `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS) | Org-wide instructions | All users in org |
| **Project** | `./CLAUDE.md` or `./.claude/CLAUDE.md` | Team-shared project instructions | Team via source control |
| **User** | `~/.claude/CLAUDE.md` | Personal preferences for all projects | Just you |

### Loading Behavior

1. **Upward walk**: Claude Code walks **up** from the current working directory to the filesystem root, loading every CLAUDE.md it encounters
2. **Above CWD**: Loaded in full at launch
3. **Below CWD (subdirectories)**: Loaded **lazily** — only when Claude reads or edits a file in that subdirectory
4. **User-level rules** (`~/.claude/rules/`): Loaded before project rules (lower priority)
5. **Project rules** (`.claude/rules/`): Higher priority than user-level

> "CLAUDE.md fully survives compaction. After `/compact`, Claude re-reads your CLAUDE.md from disk and re-injects it fresh into the session." — [Official Docs](https://code.claude.com/docs/en/memory)

### Size Recommendation

Target **under 200 lines** per CLAUDE.md file. Longer files consume more context and reduce adherence.

---

## 5. @file Import Syntax

CLAUDE.md files can import additional files using `@path/to/import` syntax:

```text
See @README for project overview and @package.json for available npm commands.

# Additional Instructions
- git workflow @docs/git-instructions.md
```

### Key Rules

- Both relative and absolute paths allowed
- Relative paths resolve relative to **the file containing the import** (not the working directory)
- Imported files can recursively import other files, **max depth of 5 hops**
- Imported files are expanded and loaded into context **at launch** alongside the parent CLAUDE.md
- First encounter triggers an approval dialog; declining disables imports permanently for that project
- Personal files: `@~/.claude/my-project-instructions.md` (stays local, not checked in)

### Important Limitation

> All `@file` references load all content into context immediately at conversation start, regardless of relevance to the current task. There is currently **no deferred/lazy loading** for `@` imports — this is a [requested feature](https://github.com/anthropics/claude-code/issues/11759).

---

## 6. Rules (.claude/rules/)

Rules provide modular, path-scoped instructions:

```
your-project/
├── .claude/
│   ├── CLAUDE.md
│   └── rules/
│       ├── code-style.md      # Loads at session start (no paths frontmatter)
│       ├── testing.md          # Loads at session start
│       └── api-design.md      # Loads when matching files accessed
```

### Path-Specific Rules

```yaml
---
paths:
  - "src/api/**/*.ts"
---

# API Development Rules
- All endpoints must include input validation
```

Rules **without** `paths` frontmatter load unconditionally at session start.
Rules **with** `paths` trigger when Claude reads matching files.

### Symlink Support

The `.claude/rules/` directory supports symlinks for sharing rules across projects:
```bash
ln -s ~/shared-claude-rules .claude/rules/shared
```

---

## 7. Skills vs. Memory vs. CLAUDE.md — When to Use Which

### Decision Matrix

| Mechanism | Author | When Loaded | Survives Compaction | Best For |
|-----------|--------|-------------|---------------------|----------|
| **CLAUDE.md** | User | Every session (full file) | Yes (re-read from disk) | Coding standards, architecture constraints, build commands |
| **Rules** (.claude/rules/) | User | Session start or on file access | Yes (re-read from disk) | Path-scoped instructions, file-type conventions |
| **Skills** (.claude/skills/) | User | **On demand** (descriptions at start, full content on invocation) | Description survives; full content reloads on invoke | Reusable workflows, procedural guides, task automation |
| **Auto Memory** | Claude | First 200 lines of MEMORY.md at start; topic files on demand | MEMORY.md re-read; topic files available on disk | Build commands, debugging insights, preferences discovered over time |

### Key Insight: Context Loading Comparison

| Mechanism | Context Cost at Session Start | Context Cost When Active |
|-----------|-------------------------------|--------------------------|
| CLAUDE.md | Full file always loaded | Already in context |
| Rules (unconditional) | Full file always loaded | Already in context |
| Rules (path-scoped) | Nothing until file match | Full file on match |
| Skills (default) | Description only (~few lines) | Full content on invocation |
| Skills (`disable-model-invocation: true`) | Nothing | Full content on user invocation |
| Auto Memory | First 200 lines of MEMORY.md | Topic files loaded on demand |

### When to Use Skills Instead of Rules

> "Rules load into context every session or when matching files are opened. For task-specific instructions that don't need to be in context all the time, use skills instead, which only load when you invoke them or when Claude determines they're relevant to your prompt." — [Official Docs](https://code.claude.com/docs/en/memory)

### Skill Frontmatter Highlights

```yaml
---
name: deploy
description: Deploy the application to production
disable-model-invocation: true   # Only user can invoke
context: fork                     # Run in isolated subagent
agent: Explore                    # Agent type for fork
allowed-tools: Read, Grep, Glob  # Restrict tool access
model: sonnet                     # Model override
---
```

---

## 8. Context Window & Compaction

### Token Budget

| Component | Tokens | % of Window |
|-----------|--------|-------------|
| **Total context window** | ~200,000 tokens | 100% |
| **System prompt** | ~2,700 tokens | 1.3% |
| **System tools** | ~16,800 tokens | 8.4% |
| **Custom agents** | ~1,300 tokens | 0.7% |
| **Memory files** | ~7,400 tokens | 3.7% |
| **Skills descriptions** | ~1,000 tokens | 0.5% |
| **Auto-compact buffer** | ~33,000 tokens | 16.5% |
| **Usable context** | ~167,000 tokens | ~83.5% |

Source: [Context Buffer Management](https://claudefa.st/blog/guide/mechanics/context-buffer-management)

### Compaction Trigger

- Auto-compaction fires at approximately **83.5% usage** (~167K tokens of a 200K window)
- Configurable via `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` (1-100 range)
- Post-compaction, context typically drops to ~60K tokens

### What Survives Compaction

| Survives | Lost/Summarized |
|----------|-----------------|
| CLAUDE.md (re-read from disk fresh) | Older conversation messages (summarized) |
| Auto memory MEMORY.md (re-loaded) | Detailed tool outputs from early conversation |
| User requests and key code snippets | Ephemeral instructions given only in conversation |
| Loaded skills (descriptions) | Large command outputs |

### Controlling Compaction

1. **Compact Instructions section** in CLAUDE.md — tells Claude what to preserve
2. **Focused compaction**: `/compact focus on the API changes`
3. **Check context usage**: `/context` command shows what's consuming space
4. **MCP cost check**: `/mcp` shows per-server context costs

---

## 9. PreCompact and PostCompact Hooks

### PreCompact Hook

**When it fires:** Before Claude Code runs a compact operation.

**Matcher values:**
- `"manual"` — triggered by `/compact` command
- `"auto"` — auto-compact when context window is full

**Input parameters:**
```json
{
  "session_id": "abc123",
  "transcript_path": "/Users/.../.claude/projects/.../session.jsonl",
  "cwd": "/Users/...",
  "permission_mode": "default",
  "hook_event_name": "PreCompact",
  "trigger": "manual",
  "custom_instructions": ""
}
```

- `trigger`: `"manual"` for `/compact`, `"auto"` for automatic
- `custom_instructions`: contains what user passes to `/compact` (empty for auto)

**Common pattern — shift-change handover:**
```json
{
  "hooks": {
    "PreCompact": [
      {
        "type": "command",
        "matcher": "auto",
        "command": "claude -p 'Summarize the transcript for handover' < $transcript_path > HANDOVER.md"
      }
    ]
  }
}
```

> "Anthropic changelog (January 2026): PreCompact hooks reduce critical information loss by 30% during compactions."

### PostCompact Hook

**When it fires:** After Claude Code completes a compact operation.

**Input parameters include:** `trigger` and `compact_summary` (the generated conversation summary).

```json
{
  "hook_event_name": "PostCompact",
  "trigger": "manual",
  "compact_summary": "Summary of the compacted conversation..."
}
```

**No decision control** — cannot affect the compaction result, only perform follow-up tasks (logging, state updates, context injection).

### SessionStart Hook

**Source matcher values:**

| Matcher | When it fires |
|---------|--------------|
| `startup` | New session |
| `resume` | `--resume`, `--continue`, or `/resume` |
| `clear` | `/clear` |
| `compact` | Auto or manual compaction |

**Context injection:** Any text printed to stdout is added as context for Claude.

**Environment persistence:** Can write to `$CLAUDE_ENV_FILE` to persist environment variables:
```bash
#!/bin/bash
if [ -n "$CLAUDE_ENV_FILE" ]; then
  echo 'export NODE_ENV=production' >> "$CLAUDE_ENV_FILE"
fi
```

### SessionEnd Hook

**Reason matchers:** `clear`, `logout`, `prompt_input_exit`, `bypass_permissions_disabled`, `other`

**Timeout:** Default 1.5 seconds. Override with `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS`.

**No decision control** — cannot block session termination.

---

## 10. Session Management & Resumption

### Session Commands

| Command | Behavior |
|---------|----------|
| `claude --continue` or `claude -c` | Resume the most recent session in the current directory |
| `claude --resume <session-id>` or `claude -r <id>` | Resume a specific session by ID |
| `claude --continue --fork-session` | Branch off from last session with a new ID |
| `claude --list-sessions` | List recent sessions |
| `/compact` | Manually trigger compaction |
| `/compact focus on X` | Compact with focus instructions |
| `/context` | See what's consuming context space |

### Key Session Behaviors

1. **Sessions are independent** — each starts with a fresh context window
2. **Cross-session persistence** comes from: auto memory, CLAUDE.md, and `.claude/rules/`
3. **Resume restores conversation history** but **not** session-scoped permissions (must re-approve)
4. **Forked sessions** create a new ID preserving history up to that point; original unchanged
5. **Multiple terminals on same session** — messages interleave (not corrupted, but jumbled). Use `--fork-session` for parallel work
6. **Sessions tied to directories** — resume only shows sessions from current directory
7. **Branch switching** — Claude sees new branch files, but conversation history unchanged

### Session File Growth

- Session files grow linearly with context usage
- ~90% full context (~180K tokens) → ~3-5 MB session files → ~2-3 second load time

---

## 11. Subagent Memory

Introduced in **Claude Code v2.1.33 (February 2026)**, subagents can maintain their own persistent auto memory via the `memory` frontmatter field in agent definition files.

```yaml
---
name: code-reviewer
description: Review code
memory: user
---
```

Storage location: `.claude/agent-memory/<name-of-agent>`

> "Subagents can also maintain their own auto memory. See subagent configuration for details." — [Official Docs](https://code.claude.com/docs/en/memory)

This enables specialized agents to build up domain-specific knowledge over time, separate from the main session's auto memory.

---

## 12. Best Practices for Long Sessions

### Context Hygiene

1. **Put persistent rules in CLAUDE.md** — they survive compaction (re-read from disk)
2. **Use `/context` regularly** to monitor context usage
3. **Use skills instead of rules** for task-specific instructions that don't need to be always-loaded
4. **Use `disable-model-invocation: true`** on skills to keep their descriptions out of context entirely
5. **Use subagents** for isolated tasks — they get fresh context and return summaries, avoiding context bloat

### Memory Management

1. **Keep MEMORY.md under 200 lines** — only first 200 lines auto-load
2. **Don't duplicate** between CLAUDE.md and auto memory
3. **Review periodically** — after major refactors, skim memory files and delete stale entries
4. **Use topic files** — let Claude move detailed notes out of MEMORY.md into separate files
5. **Organize semantically** — by topic, not chronologically

### Compaction Strategy

1. **Add a "Compact Instructions" section** to CLAUDE.md specifying what to preserve
2. **Use PreCompact hooks** to save critical state before compaction
3. **Use PostCompact hooks** to inject recovery context after compaction
4. **Use SessionStart hooks** (with `compact` matcher) to re-inject critical context after auto-compaction

### Agent Context Protection

> "Auto Memory is long-term memory, recording **knowledge**; PreCompact Handover is a work snapshot, recording **state**." — [Yuanchang's Blog](https://yuanchang.org/en/posts/claude-code-auto-memory-and-hooks/)

- Use auto memory for knowledge that persists across sessions
- Use PreCompact handovers for in-progress work state
- Use subagents to isolate work and protect main context

---

## 13. New Features in Early 2026

### February 2026

- **Auto-memory system** launched (v2.1.59, February 27, 2026) — enabled by default
- **Subagent persistent memory** (v2.1.33, February 2026) — `memory` frontmatter field
- **PostCompact hook** added — fires after compaction with `compact_summary` field
- **Last-modified timestamps** on memory files — helps Claude reason about freshness vs. staleness

### January 2026

- **PreCompact hooks** formalized — reduces critical information loss by ~30%
- **InstructionsLoaded hook** — audit/log which CLAUDE.md and rules files are loaded and why

### March 2026

- **Skills descriptions context budget** — scales dynamically at 2% of context window (fallback 16,000 chars)
- **`SLASH_COMMAND_TOOL_CHAR_BUDGET`** env var to override skill description budget
- **`claudeMdExcludes`** setting — skip CLAUDE.md files in monorepos by path/glob pattern
- **Managed policy CLAUDE.md** cannot be excluded — org-wide instructions always apply
- **Agent hooks**: `SubagentStart`, `SubagentStop` with agent type matching
- **ConfigChange hook**: fires when settings change, with source matching

### Configuration Environment Variables Summary

| Variable | Purpose |
|----------|---------|
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` | Disable auto memory |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Override compaction trigger threshold (1-100) |
| `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS` | Override SessionEnd hook timeout |
| `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1` | Load CLAUDE.md from `--add-dir` directories |
| `SLASH_COMMAND_TOOL_CHAR_BUDGET` | Override skill description context budget |

---

## Sources

- [How Claude remembers your project — Official Docs](https://code.claude.com/docs/en/memory)
- [How Claude Code works — Official Docs](https://code.claude.com/docs/en/how-claude-code-works)
- [Hooks reference — Official Docs](https://code.claude.com/docs/en/hooks)
- [Extend Claude with skills — Official Docs](https://code.claude.com/docs/en/skills)
- [Claude Code Changelog — Official](https://code.claude.com/docs/en/changelog)
- [Claude Code Auto Memory: How Your AI Learns Your Project — ClaudeFast](https://claudefa.st/blog/guide/mechanics/auto-memory)
- [Context Buffer Management — ClaudeFast](https://claudefa.st/blog/guide/mechanics/context-buffer-management)
- [Claude Code's Memory Evolution: Auto Memory & PreCompact Hooks — Yuanchang's Blog](https://yuanchang.org/en/posts/claude-code-auto-memory-and-hooks/)
- [SFEIR Institute — CLAUDE.md Memory System](https://institute.sfeir.com/en/claude-code/claude-code-memory-system-claude-md/deep-dive/)
- [Claude Code Skills and the Problem of Context — OlioApps](https://www.olioapps.com/blog/claude-code-skills-context-problem)
- [Anthropic Just Added Auto-Memory to Claude Code — Medium](https://medium.com/@joe.njenga/anthropic-just-added-auto-memory-to-claude-code-memory-md-i-tested-it-0ab8422754d2)
- [Session Persistence in Claude Code — GitHub Wiki](https://github.com/ruvnet/ruflo/wiki/session-persistence)
- [Claude Code: Resume Sessions Without Context Loss — Medium](https://medium.com/rigel-computer-com/you-close-claude-code-the-context-is-gone-or-is-it-3ebc5c1c379d)
- [What is the --resume Flag — ClaudeLog](https://claudelog.com/faqs/what-is-resume-flag-in-claude-code/)
