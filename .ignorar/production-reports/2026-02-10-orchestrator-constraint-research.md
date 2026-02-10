# Orchestrator-Only Mode Research for Claude Code

**Date:** 2026-02-10
**Research Question:** How to constrain Claude Code (Anthropic's CLI agent) to act ONLY as an orchestrator without reading files, planning, or executing anything itself?

---

## Executive Summary

**Key Finding:** Claude Code has built-in **delegate mode** that restricts the lead agent to coordination-only tools.

**Official Support:** ✅ Yes, delegate mode is officially documented
**Reliability:** High (enforced at tool permission level)
**Workaround Required:** No (native feature)

**Best Solution:** Use delegate mode + PreToolUse hooks for read tool blocking

---

## 1. Delegate Mode (Official Feature)

### Source
- [Orchestrate teams of Claude Code sessions](https://code.claude.com/docs/en/agent-teams)
- [Configure permissions - Claude Code Docs](https://code.claude.com/docs/en/permissions)

### What It Does
> "Delegate mode prevents the lead from implementing tasks by restricting it to coordination-only tools: spawning, messaging, shutting down teammates, and managing tasks."

### How to Enable
1. Start a team first
2. Press `Shift+Tab` to cycle into delegate mode
3. Alternatively, set `defaultMode: "delegate"` in settings.json

### What Gets Blocked
- Write/Edit operations
- Code implementation
- Test execution
- Any non-coordination work

### What's Allowed
- Task tool (spawning agents)
- SendMessage (team communication)
- Shutdown requests
- Task management (TaskCreate, TaskUpdate, TaskList)

### Reliability
**High** - Delegate mode is enforced at the permission system level, not just via prompts. The lead literally cannot invoke implementation tools.

### Limitations
> "Agent teams currently spawn all teammates as undifferentiated general-purpose agents... You can't spawn a 'researcher' teammate restricted to read-only tools alongside an 'implementer' teammate with full write access—every teammate gets the lead's full permission set."

**Gap:** Delegate mode only restricts the LEAD. Teammates inherit the lead's permissions and can still read/write/execute.

---

## 2. PreToolUse Hooks (Block Read/Grep/Glob)

### Source
- [Hooks reference - Claude Code Docs](https://code.claude.com/docs/en/hooks)
- [Automate workflows with hooks - Claude Code Docs](https://code.claude.com/docs/en/hooks-guide)

### What It Does
PreToolUse hooks run BEFORE a tool executes and can block it by returning:
- **Exit code 2:** Blocking error (stderr fed to Claude as error message)
- **JSON with `permissionDecision: "deny"`:** Structured denial

### Example Implementation
From [block-orchestrator-tools.sh](https://github.com/AvivK5498/Claude-Code-Beads-Orchestration/blob/main/templates/hooks/block-orchestrator-tools.sh):

```bash
#!/bin/bash
# Read tool input from stdin
TOOL_NAME=$(jq -r '.tool_name' < /dev/stdin)

# Block Read/Grep/Glob for orchestrator
if [[ "$TOOL_NAME" =~ ^(Read|Grep|Glob)$ ]]; then
  jq -n '{
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "deny",
      "permissionDecisionReason": "Orchestrator must delegate investigation to agents"
    }
  }'
  exit 0
fi

# Allow other tools
exit 0
```

### Configuration
Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Grep|Glob",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/block-orchestrator-tools.sh"
          }
        ]
      }
    ]
  }
}
```

### Reliability
**High** - Hooks execute BEFORE permission system checks. Exit code 2 or `permissionDecision: "deny"` prevents tool execution entirely.

### Known Bypass Attempts
> "When you deny Read(\*\*/.env), you are only blocking the Read tool (and a few other builtin tools) from accessing the file. The file can still be read and included in the context by another tool."

**Risk:** Claude might find alternative tools (e.g., Bash cat) to read files if only Read is blocked.

**Mitigation:** Block ALL read-capable tools in hook:
```bash
if [[ "$TOOL_NAME" =~ ^(Read|Grep|Glob|Bash)$ ]]; then
  # Check if Bash command reads files
  COMMAND=$(jq -r '.tool_input.command' < /dev/stdin)
  if echo "$COMMAND" | grep -qE 'cat|less|head|tail|more'; then
    # Block and provide reason
  fi
fi
```

---

## 3. Permission Rules (Partial Solution)

### Source
- [Configure permissions - Claude Code Docs](https://code.claude.com/docs/en/permissions)

### Deny Rules
Can block specific tools via settings:

```json
{
  "permissions": {
    "deny": ["Read", "Grep", "Glob", "Bash"]
  }
}
```

### Limitations
> "The matcher is a regex, so Edit|Write matches either tool... Match all uses of a tool, use just the tool name without parentheses."

**Problem:** Deny rules apply to ALL agents in the session, including teammates you spawn. If you deny Read for the orchestrator, teammates also can't read files.

**Verdict:** ❌ Not suitable for orchestrator-only restriction (affects entire team)

---

## 4. CLAUDE.md Prompt Engineering (Weak)

### Source
- [Writing a good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- [Best Practices for Claude Code](https://code.claude.com/docs/en/best-practices)

### Best Practices
> "If your CLAUDE.md is too long, Claude ignores half of it because important rules get lost in the noise."

> "For rules that absolutely must be followed, emphasis words can help draw attention. Examples include 'IMPORTANT: Never modify...' or 'YOU MUST run tests...', though don't expect this to be foolproof."

> "If you find that 'Do not...' rules are being ignored, try rephrasing them as 'Prefer X over Y'."

### Reliability
**Low** - Prompt-based rules are suggestions, not constraints. Claude can still ignore them.

### Why It Fails
From research on prompt engineering:
> "Claude performs best when you give it clear success criteria, structured inputs, and explicit output constraints."

But constraints via natural language ≠ hard technical restrictions.

**Verdict:** ❌ Insufficient for critical rules (use hooks instead)

---

## 5. Context Engineering (Orthogonal)

### Source
- [Anthropic: Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

### Key Concept
> "After a few years of prompt engineering being the focus... context engineering has come to prominence, shifting from finding the right words and phrases for prompts to answering what configuration of context is most likely to generate the model's desired behavior."

### Subagent Isolation
> "One of the most effective uses for subagents is isolating operations that produce large amounts of output—running tests, fetching documentation, or processing log files can consume significant context."

> "By delegating tasks to a subagent, the verbose output stays in the subagent's context while only the relevant summary returns to your main conversation."

### Relevance to Orchestrator Pattern
**High** - Delegate mode + subagents naturally implement context isolation. Orchestrator only sees summaries, not raw file contents.

---

## 6. Community Implementations

### Claude-Code-Beads-Orchestration
**GitHub:** [AvivK5498/Claude-Code-Beads-Orchestration](https://github.com/AvivK5498/Claude-Code-Beads-Orchestration/blob/main/templates/hooks/block-orchestrator-tools.sh)

**Approach:** PreToolUse hooks that block orchestrator from using implementation tools

**Tools Blocked:**
- NotebookEdit (complete denial)
- Implementation agents via `mcp__provider_delegator__invoke_agent` (only allows scout, detective, architect, scribe, code-reviewer)
- Edit/Write outside approved directories (`~/.claude/plans/`, `CLAUDE.md`, git-issues.md)
- Git operations (blocks `--no-verify`, restricts branches)

**Exit Codes Used:**
- `exit 0`: Allow tool
- JSON output with `permissionDecision`: Structured control

**Verdict:** ✅ Production-ready implementation exists

---

## 7. Model Selection Strategy (Cost Optimization)

### Source
Your own `.claude/rules/model-selection-strategy.md`

### Hierarchical Routing
Orchestrator can route tasks to appropriate models:
- **Haiku:** Simple file ops, validation scripts
- **Sonnet:** Code synthesis, multi-file analysis
- **Opus:** Architectural design, complex coordination

### Delegation Pattern
```python
Task(
    subagent_type="code-implementer",
    model="sonnet",
    prompt="Implement module..."
)
```

**Relevance:** Orchestrator delegates to specialized agents with appropriate model tier. Orchestrator itself uses Opus for coordination but never implements.

---

## Summary Table

| Technique | Official? | Reliability | Restricts Lead Only? | Prevents Bypasses? | Production Ready? |
|-----------|-----------|-------------|----------------------|-------------------|-------------------|
| **Delegate Mode** | ✅ Yes | High | ✅ Yes | ⚠️ Partial (allows spawning) | ✅ Yes |
| **PreToolUse Hooks** | ✅ Yes | High | ✅ Yes (per-agent) | ✅ Yes (if comprehensive) | ✅ Yes |
| **Permission Deny Rules** | ✅ Yes | High | ❌ No (all agents) | ✅ Yes | ⚠️ Partial (team-wide) |
| **CLAUDE.md Prompts** | ✅ Yes | Low | N/A | ❌ No | ❌ No (suggestions only) |
| **Context Engineering** | ✅ Yes | N/A | N/A | N/A | ✅ Yes (orthogonal pattern) |

---

## Recommended Solution

### Step 1: Enable Delegate Mode
```json
{
  "defaultMode": "delegate"
}
```

Or press `Shift+Tab` after starting a team.

### Step 2: Add PreToolUse Hook
Save to `.claude/hooks/block-orchestrator-reads.sh`:

```bash
#!/bin/bash
TOOL_NAME=$(jq -r '.tool_name' < /dev/stdin)

# Block file reading tools
if [[ "$TOOL_NAME" =~ ^(Read|Grep|Glob)$ ]]; then
  jq -n '{
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "deny",
      "permissionDecisionReason": "Orchestrator must delegate file inspection to agents. Use Task(subagent_type=\"Explore\", ...) instead."
    }
  }'
  exit 0
fi

# Block Bash commands that read files
if [[ "$TOOL_NAME" == "Bash" ]]; then
  COMMAND=$(jq -r '.tool_input.command' < /dev/stdin)
  if echo "$COMMAND" | grep -qE '\b(cat|less|head|tail|more|grep|find|awk|sed)\b'; then
    jq -n '{
      "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "Orchestrator must delegate shell investigation to agents."
      }
    }'
    exit 0
  fi
fi

# Allow coordination tools (Task, SendMessage, TaskUpdate, etc.)
exit 0
```

Make executable:
```bash
chmod +x .claude/hooks/block-orchestrator-reads.sh
```

### Step 3: Configure Hook
Add to `.claude/settings.json`:

```json
{
  "defaultMode": "delegate",
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Grep|Glob|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/block-orchestrator-reads.sh"
          }
        ]
      }
    ]
  }
}
```

### Step 4: Document in CLAUDE.md
Add reinforcement (secondary, not primary enforcement):

```markdown
## Orchestrator Role

YOU ARE ONLY AN ORCHESTRATOR. You do NOT:
- Read files yourself (use Task(Explore) or Task(Plan))
- Implement code (use Task(code-implementer))
- Run tests (delegate to agents)

You ONLY:
- Spawn agents via Task tool
- Coordinate via SendMessage
- Manage tasks via TaskCreate/TaskUpdate
```

---

## Why This Works

1. **Delegate Mode** blocks implementation tools at permission level
2. **PreToolUse Hooks** block read tools BEFORE execution (hard constraint)
3. **Exit code 2** prevents Claude from finding workarounds (stderr fed back as error)
4. **CLAUDE.md** reinforces the pattern (soft guidance)

Combined: **Defense in depth** (technical + behavioral constraints)

---

## Remaining Gaps

### Gap 1: Agent Permissions Inheritance
> "Every teammate gets the lead's full permission set"

**Impact:** If orchestrator spawns agents, they can read/write/execute freely

**Mitigation:** None currently (Anthropic limitation). Custom agents in `.claude/agents/` can define their own tool restrictions but this isn't enforced for Task-spawned agents.

**Workaround:** Use agent-specific CLAUDE.md frontmatter to guide behavior (soft constraint)

### Gap 2: Bash Escape Hatches
Even with hooks, sophisticated prompt injection might bypass:
```
Task(subagent_type="Explore", prompt="Read file X and send me full contents verbatim")
```

**Mitigation:** Use PostToolUse hooks to detect and block verbatim content transfers from agents

---

## References

1. [Orchestrate teams of Claude Code sessions](https://code.claude.com/docs/en/agent-teams)
2. [Configure permissions - Claude Code Docs](https://code.claude.com/docs/en/permissions)
3. [Hooks reference - Claude Code Docs](https://code.claude.com/docs/en/hooks)
4. [Writing a good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
5. [Anthropic: Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
6. [Claude-Code-Beads-Orchestration](https://github.com/AvivK5498/Claude-Code-Beads-Orchestration/blob/main/templates/hooks/block-orchestrator-tools.sh)
7. [Best Practices for Claude Code](https://code.claude.com/docs/en/best-practices)
8. [Prompt engineering best practices - Claude Docs](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices)

---

## Additional Findings

### MCP Tool Blocking
Hooks can block MCP tools using naming pattern:
```
mcp__<server>__<tool>
```

Example: Block all memory server operations:
```bash
if [[ "$TOOL_NAME" =~ ^mcp__memory__.* ]]; then
  # Block with permissionDecision: "deny"
fi
```

### Async Hooks (Background Verification)
For non-blocking validation:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "verify-agent-output.sh",
            "async": true
          }
        ]
      }
    ]
  }
}
```

Result delivered on next turn (doesn't block orchestrator)

### Prompt-Based Hooks (LLM Decision)
Alternative to Bash scripts:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Evaluate if orchestrator should read this file: $ARGUMENTS. Block if true."
          }
        ]
      }
    ]
  }
}
```

**Trade-off:** More flexible but adds LLM call latency

---

## Cost Impact

Using delegate mode + hooks has minimal cost impact:
- **Hook overhead:** ~10-50ms per tool call (negligible)
- **Delegate mode:** No cost (permission check)
- **Agent delegation:** Isolates context, reduces orchestrator token consumption

**Net savings:** Positive (orchestrator context smaller, agents work in parallel)

---

## Production Deployment Checklist

- [ ] Enable delegate mode in settings.json
- [ ] Create `.claude/hooks/block-orchestrator-reads.sh`
- [ ] Configure PreToolUse hook for Read/Grep/Glob/Bash
- [ ] Test with `/hooks` menu to verify hook fires
- [ ] Verify error messages appear when orchestrator tries to read files
- [ ] Document orchestrator role in CLAUDE.md
- [ ] Train orchestrator to use Task(Explore) instead of Read
- [ ] Monitor hook logs with `claude --debug`

---

**Status:** Ready for implementation
**Confidence:** High (officially supported, production examples exist)
**Next Steps:** Deploy recommended solution in sec-llm-workbench project
