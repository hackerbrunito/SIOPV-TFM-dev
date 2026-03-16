# Claude Code Agent Persona, Guardrails & Behavioral Control
## State-of-the-Art Research Report (March 2026)

---

## 1. AGENT DEFINITION FILE STRUCTURE

### File Format

Subagents are defined as Markdown files with YAML frontmatter, stored in:
- `.claude/agents/` (project-level, priority 2)
- `~/.claude/agents/` (user-level, priority 3)
- `--agents` CLI flag (session-only, priority 1 highest)
- Plugin `agents/` directory (priority 4 lowest)

The frontmatter defines metadata and constraints. The Markdown body becomes the **system prompt** that guides the subagent's behavior. Subagents receive ONLY this system prompt plus basic environment details (working directory), NOT the full Claude Code system prompt.

### Supported Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique identifier, lowercase letters and hyphens |
| `description` | Yes | When Claude should delegate to this subagent. Used for auto-delegation decisions |
| `tools` | No | Allowlist of tools. Inherits all tools if omitted |
| `disallowedTools` | No | Denylist, removed from inherited/specified list |
| `model` | No | `sonnet`, `opus`, `haiku`, or `inherit` (default) |
| `permissionMode` | No | `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan` |
| `maxTurns` | No | Maximum agentic turns before forced stop |
| `skills` | No | Skills to inject into context at startup (full content, not just availability) |
| `mcpServers` | No | MCP servers available to this subagent |
| `hooks` | No | Lifecycle hooks scoped to this subagent |
| `memory` | No | `user`, `project`, or `local` -- enables persistent cross-session learning |
| `background` | No | `true` to always run as background task |
| `isolation` | No | `worktree` for git worktree isolation |

### Tool Restriction Syntax

```yaml
# Allowlist
tools: Read, Grep, Glob, Bash

# Denylist
disallowedTools: Write, Edit

# Restrict which subagents can be spawned (for --agent mode)
tools: Agent(worker, researcher), Read, Bash

# Allow spawning any subagent
tools: Agent, Read, Bash
```

### CLI-Defined Agents (JSON)

```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer. Use proactively after code changes.",
    "prompt": "You are a senior code reviewer...",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  }
}'
```

The `prompt` field in JSON is equivalent to the markdown body in file-based agents.

### Memory Configuration

When `memory` is set, the subagent gets:
- A persistent directory (`~/.claude/agent-memory/<name>/` for user scope, `.claude/agent-memory/<name>/` for project scope, `.claude/agent-memory-local/<name>/` for local scope)
- First 200 lines of `MEMORY.md` injected into system prompt at startup
- Read, Write, Edit tools automatically enabled for memory management
- Instructions to curate MEMORY.md if it exceeds 200 lines

---

## 2. PERSONA/PERSONALITY PATTERNS

### Core Principle: System Prompt IS the Persona

The body of the agent definition file IS the system prompt. This is the single most important surface for defining persona. The subagent receives only this prompt plus environment details -- nothing else from the parent conversation.

### Proven Persona Patterns

#### Pattern A: Role + Checklist (from Anthropic docs)

```markdown
---
name: code-reviewer
description: Expert code review specialist. Use immediately after writing or modifying code.
tools: Read, Grep, Glob, Bash
model: inherit
---

You are a senior code reviewer ensuring high standards of code quality and security.

When invoked:
1. Run git diff to see recent changes
2. Focus on modified files
3. Begin review immediately

Review checklist:
- Code is clear and readable
- Functions and variables are well-named
- No exposed secrets or API keys
- Input validation implemented

Provide feedback organized by priority:
- Critical issues (must fix)
- Warnings (should fix)
- Suggestions (consider improving)

Include specific examples of how to fix issues.
```

#### Pattern B: Domain Expert with Workflow (from Anthropic docs)

```markdown
---
name: debugger
description: Debugging specialist for errors, test failures, and unexpected behavior.
tools: Read, Edit, Bash, Grep, Glob
---

You are an expert debugger specializing in root cause analysis.

When invoked:
1. Capture error message and stack trace
2. Identify reproduction steps
3. Isolate the failure location
4. Implement minimal fix
5. Verify solution works

Focus on fixing the underlying issue, not the symptoms.
```

#### Pattern C: Behavioral Boundaries with Scenario Handling (from Anthropic API docs)

```markdown
You are AcmeBot, the enterprise-grade AI assistant for AcmeTechCo.

Your rules for interaction:
- Always reference AcmeTechCo standards or industry best practices
- If unsure, ask for clarification before proceeding
- Never disclose confidential AcmeTechCo information

Handle situations along these guidelines:
- If asked about AcmeTechCo IP: "I cannot disclose TechCo's proprietary information."
- If questioned on best practices: "Per ISO/IEC 25010, we prioritize..."
- If unclear on a doc: "To ensure accuracy, please clarify section 3.2..."
```

#### Pattern D: SuperClaude Cognitive Personas

The SuperClaude Framework defines "cognitive personas" -- NOT separate AI models, but context configurations that Claude reads to adopt specialized behaviors. Each is a .md file containing:
- Domain-specific expertise
- Behavioral patterns
- Problem-solving approaches

Key insight: Personas are invocable via `@agent-security` or `@agent-frontend` syntax, and the framework provides 16 domain specialist agents that can delegate to each other, creating a network of specialized expertise.

### What Makes Persona Effective

From Anthropic's official guidance:
1. **Set role in system prompt**: Even a single sentence makes a difference
2. **Provide detailed personality info**: Background, traits, quirks help the model generalize
3. **Prepare for scenarios**: List common situations and expected responses
4. **Constrain with examples**: Show desired output format -- this "trains" understanding better than abstract instructions

### Anti-Pattern: Over-Relying on Persona

Research from Anthropic's Persona Selection Model (2026) reveals that when Claude adopts a persona, it infers personality traits that drive OTHER behaviors beyond those specified. A persona designed for one purpose can leak into unintended behavioral dimensions. Mitigation: Be explicit about what the persona should NOT do.

---

## 3. BEHAVIORAL GUARDRAILS

### The Fundamental Insight: Prompts Are Requests, Hooks Are Laws

This is the single most important finding from this research:

> "Rules in prompts are requests. Hooks in code are laws." -- Research consensus across multiple sources

Claude can read and recite instructions without following them. The distinction between knowledge and execution is real and documented.

### The 150-Instruction Ceiling

Academic research (Jaroslawicz et al., 2025) demonstrates:
- Instruction compliance **decreases uniformly** as instruction count increases
- Frontier models max out at ~150-200 instructions
- Going beyond this threshold is **counterproductive** -- more rules correlate with worse overall compliance across ALL rules
- Practical recommendation: **Keep the 20 most critical rules. Handle the rest differently.**

### Three-Tier Guardrails Framework

#### Tier 1: Prompt-Based (Probabilistic)
- System prompt instructions in agent body
- CLAUDE.md rules
- `.claude/rules/*.md` files
- **Compliance: ~80%** at best, degrades with volume
- Use for: Guidance, preferences, soft constraints

#### Tier 2: Tool Restrictions (Deterministic)
- `tools` / `disallowedTools` in frontmatter
- `permissionMode` settings
- `permissions.deny` in settings.json
- **Compliance: 100%** -- tools simply don't exist for the agent
- Use for: Hard capability boundaries

#### Tier 3: Hooks (Deterministic)
- `PreToolUse` hooks that block operations
- `PostToolUse` hooks that validate results
- `Stop` hooks that check completion criteria
- **Compliance: 100%** -- code runs regardless of what Claude thinks
- Use for: Critical safety rules, security enforcement

### Guardrails Ladder (from Adaline Labs)

| Level | Description | What agents can do |
|-------|-------------|-------------------|
| Tier 1 | Read-only and analysis | Inspect, explain, plan. Cannot write or run risky commands |
| Tier 2 | Controlled changes in scoped directories | Edit only within approved paths |
| Tier 3 | PR-ready changes with enforced checks | Produce PR candidates only after automated checks pass |

### Deterministic vs Probabilistic Control

**Probabilistic** (prompt-based):
- "Don't edit .env files" in CLAUDE.md
- Claude may ignore this under pressure or when context is long
- Subject to lost-in-the-middle degradation

**Deterministic** (code-based):
- PreToolUse hook that exits with code 2 when .env is targeted
- ALWAYS runs, ALWAYS blocks, regardless of Claude's reasoning
- Cannot be overridden by the model

### Per-Step Constraint Design (Anti-Drift)

Four constraint types for different step requirements:

1. **Procedural (HOW)**: Sequential steps where divergence is acceptable
2. **Criteria (WHAT)**: Steps requiring quality judgment -- replace "how to do it" with explicit standards
3. **Template**: Fix output structure while allowing flexible content
4. **Guardrail**: Define boundaries by prohibition -- what must NEVER happen

Best practice: Apply different constraint types to each step based on its requirements, rather than one freedom level for the entire workflow.

---

## 4. HOOKS FOR BEHAVIORAL CONTROL

### All Hook Events (16 total as of March 2026)

| Event | When | Can Block? | Matcher Input |
|-------|------|-----------|---------------|
| `SessionStart` | Session begins/resumes | No | `startup`, `resume`, `clear`, `compact` |
| `UserPromptSubmit` | Prompt submitted, before processing | No | No matcher support |
| `PreToolUse` | Before tool execution | **YES** | Tool name (e.g., `Bash`, `Edit\|Write`) |
| `PermissionRequest` | Permission dialog appears | No | Tool name |
| `PostToolUse` | After tool succeeds | No | Tool name |
| `PostToolUseFailure` | After tool fails | No | Tool name |
| `Notification` | Notification sent | No | Notification type |
| `SubagentStart` | Subagent spawned | No | Agent type name |
| `SubagentStop` | Subagent finishes | No | Agent type name |
| `Stop` | Claude finishes responding | No | No matcher support |
| `TeammateIdle` | Agent team member going idle | No | No matcher support |
| `TaskCompleted` | Task marked completed | No | No matcher support |
| `InstructionsLoaded` | CLAUDE.md or rules loaded | No | No matcher support |
| `ConfigChange` | Config file changes | No | Config source |
| `PreCompact` | Before context compaction | No | `manual`, `auto` |
| `SessionEnd` | Session terminates | No | Exit reason |
| `WorktreeCreate`/`WorktreeRemove` | Worktree lifecycle | No | No matcher support |

### Three Handler Types

1. **`command`**: Shell script. Deterministic. Best for security rules.
2. **`prompt`**: LLM judgment call. For nuanced decisions.
3. **`agent`**: Full codebase state verification. Most expensive but most capable.

### What Hooks CAN Enforce

- **Block dangerous commands**: PreToolUse + exit code 2 or JSON `permissionDecision: "deny"`
- **Validate SQL queries**: Block write operations, allow only SELECT
- **Protect files**: Block Write/Edit to specific paths
- **Auto-format**: PostToolUse runs linter after every edit
- **Run tests**: PostToolUse triggers test suite after changes
- **Modify tool inputs**: PreToolUse (v2.0.10+) can rewrite tool parameters before execution (e.g., add dry-run flags, redact secrets)
- **Enforce conventions**: PostToolUse checks naming, structure
- **Setup/teardown**: SubagentStart/SubagentStop for resource management

### What Hooks CANNOT Enforce

- **Reasoning quality**: Hooks see actions, not thought processes
- **Instruction recall**: Can't force Claude to remember something from its prompt
- **Planning decisions**: Can't control WHICH tool Claude decides to use
- **Output quality**: Can validate format but not semantic correctness of natural language output
- **Cross-turn consistency**: Each hook invocation is stateless

### PreToolUse: The Critical Hook

PreToolUse is the ONLY hook that can block actions. Two mechanisms:

**Exit code based:**
```bash
#!/bin/bash
# Exit 0 = allow, Exit 2 = block
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
if echo "$COMMAND" | grep -iE '\b(DROP|DELETE|TRUNCATE)\b' > /dev/null; then
  echo "Blocked: Write operations not allowed" >&2
  exit 2
fi
exit 0
```

**JSON output based:**
```bash
#!/bin/bash
jq -n '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: "Destructive command blocked"
  }
}'
```

### Hook Configuration in Agent Frontmatter

```yaml
---
name: db-reader
description: Execute read-only database queries
tools: Bash
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-readonly-query.sh"
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "./scripts/run-linter.sh"
---
```

### Hook Configuration Locations

| Location | Scope |
|----------|-------|
| `~/.claude/settings.json` | All projects |
| `.claude/settings.json` | Single project (committable) |
| `.claude/settings.local.json` | Single project (gitignored) |
| Managed policy settings | Organization-wide |
| Plugin `hooks/hooks.json` | When plugin enabled |
| Agent frontmatter | While agent is active |

---

## 5. RULES FILES FOR CONDITIONING

### Directory Structure

Rules are stored in `.claude/rules/` as standalone Markdown files with optional YAML frontmatter for path targeting. Files are discovered **recursively**, supporting subdirectories for organization.

```
.claude/rules/
  code-style.md          # Global rule
  testing.md             # Global rule
  security.md            # Global rule
  frontend/
    react.md             # Path-targeted rule
  api/
    conventions.md       # Path-targeted rule
```

### Path-Targeted Rules

```yaml
---
paths:
  - "src/api/**/*.ts"
---
This rule only activates when Claude works on files matching this pattern.
```

**Important caveat (known bug):** Path-based rules only inject into context when Claude **reads** a matching file, NOT when writing/creating files. Rules targeting file creation conventions are silently ignored for new files.

### How Rules Load

- Rules without `paths` apply **globally** (loaded at session start)
- Rules with `paths` load **conditionally** when working on matching files
- Rules load with the **same priority as CLAUDE.md**
- The `InstructionsLoaded` hook event fires when rules are loaded

### Rules vs CLAUDE.md vs Skills

| Mechanism | When Loaded | Purpose |
|-----------|-------------|---------|
| CLAUDE.md | Every session | Broad project instructions |
| `.claude/rules/*.md` | Session start (global) or on file match (path-scoped) | Modular, scoped policies |
| Skills | On demand (invoked or auto-matched) | Domain knowledge, workflows |
| Agent body | When agent is spawned | Agent-specific system prompt |

### Effective Rule Writing

From community research:

1. **Keep under 150 instructions total** across all loaded contexts
2. **Be specific and measurable**: "Calculate ROI on a 3-year TCO basis" beats "Calculate ROI"
3. **Use emphasis markers**: `IMPORTANT`, `YOU MUST`, `CRITICAL` improve adherence
4. **Delete rules Claude already follows**: If removing a rule doesn't change behavior, it's wasting attention
5. **Test rules by observation**: Watch whether Claude's behavior actually shifts after adding a rule

### What Rules CANNOT Do

- Rules are **advisory**, not enforced
- Claude can read and recite rules without following them
- Compliance degrades as total instruction volume increases
- Long sessions cause rule "forgetting" due to context dilution
- Rules may be deemed "not relevant" by the model and ignored (Claude's system prompt says instructions "may or may not be relevant")

---

## 6. ANTI-IMPROVISATION TECHNIQUES

### Technique 1: Per-Step Constraint Design

Instead of assigning one freedom level to an entire workflow, apply different constraint types per step:

| Step Type | Constraint | Example |
|-----------|-----------|---------|
| Data collection | Procedural | "Run these 3 commands in order" |
| Analysis | Criteria | "Evaluate on these 3 axes: X, Y, Z" |
| Reporting | Template | "Output must follow this exact structure" |
| Safety checks | Guardrail | "NEVER modify files outside src/" |

### Technique 2: Todo List Recitation

By constantly rewriting a todo list, agents push the global plan into the END of the context window (most recent attention span). This combats lost-in-the-middle degradation.

```markdown
After each step, update your todo list:
- [x] Completed steps
- [ ] Remaining steps
- Current focus: [specific step]
```

### Technique 3: Fresh Context Windows

Use `/clear` between unrelated tasks. A clean session with a better prompt almost always outperforms a long session with accumulated corrections. After two failed corrections in one session, start fresh.

### Technique 4: Skills as Instruction Anchors

Skills provide step-by-step procedures that Claude follows rigidly. Without a skill, Claude improvises. With a skill, it follows the defined sequence.

Example: Without a TDD skill, "write tests first" produces inconsistent results. With the skill installed, it follows Red-Green-Refactor every time because the skill explicitly defines each step.

### Technique 5: Escalation Design

Build flexibility into constraints: "If these constraints don't fit, propose alternatives with reasoning." This prevents agents from either blindly following inappropriate rules OR ignoring them silently.

### Technique 6: Verification Loops

Give Claude a way to verify its own work:
- Tests to run
- Screenshots to compare
- Expected outputs to validate
- Linter results to check

Self-verification is the "single highest-leverage thing you can do" (Anthropic official best practices).

### Technique 7: Scoped Tool Access

Remove tools the agent doesn't need. An agent with only Read, Grep, Glob literally CANNOT improvise by editing files. Tool restrictions are the most reliable anti-improvisation mechanism because they're deterministic.

### Technique 8: MaxTurns Limit

Set `maxTurns` in frontmatter to cap how many agentic turns the subagent can take. Prevents runaway exploration or infinite loops.

### Technique 9: Explicit NOT Instructions

From Anthropic's persona research: Claude infers personality traits beyond what's specified. Explicitly state what the agent should NOT do:

```markdown
You are a security auditor.
- DO: Report vulnerabilities with severity ratings
- DO NOT: Fix code, suggest implementations, or make edits
- DO NOT: Speculate about business impact
- DO NOT: Skip files because they "look fine"
```

---

## 7. CONTEXT POSITIONING

### The Lost-in-the-Middle Problem

LLMs pay the most attention to tokens at the **start** and **end** of the context window. Information buried in the middle gets deprioritized. This is a fundamental architectural limitation, not a bug.

### Positioning Hierarchy

1. **System prompt** (highest attention): The agent body/system prompt gets maximum attention. Put critical behavioral instructions here.
2. **Start of conversation** (high attention): First messages in the context.
3. **End of conversation** (high attention): Most recent messages, including todo lists and recent instructions.
4. **Middle of conversation** (lowest attention): Earlier messages that aren't at the boundary.

### Practical Implications

| Placement | What to put there | Why |
|-----------|-------------------|-----|
| Agent body (system prompt) | Core persona, critical rules, workflow steps | Highest attention, loaded fresh each time |
| CLAUDE.md (loaded at session start) | Project conventions, build commands | Loaded early, high position in context |
| `.claude/rules/` | Scoped policies | Same priority as CLAUDE.md |
| Skills (loaded on demand) | Domain knowledge, procedures | Loaded when needed, enters at end of context (recent) |
| Todo list (continuously updated) | Current plan, remaining steps | Pushed to end of context = high attention |

### Strategies for Maximum Attention

1. **Keep agent body under 200 lines**: Shorter system prompts get more uniform attention
2. **Front-load critical rules**: Put the most important instructions at the TOP of the agent body
3. **Use emphasis markers**: `IMPORTANT`, `CRITICAL`, `YOU MUST` demonstrably improve adherence
4. **Use structured format**: Headers, bullet points, tables are more scannable than prose
5. **Repeat critical instructions**: State the most important rule at both the start AND end of the agent body
6. **Progressive disclosure**: Keep base prompt minimal, load detailed knowledge via skills only when needed
7. **Prune regularly**: Remove any instruction that doesn't change behavior when removed

### CLAUDE.md Token Budget

CLAUDE.md is loaded EVERY session. The general consensus:
- Under 300 lines is recommended
- Shorter is better
- Each line should pass the test: "Would removing this cause Claude to make mistakes?" If not, cut it.
- Bloated CLAUDE.md files cause Claude to **ignore your actual instructions**

### Auto-Compaction Impact

When context reaches ~95% of 200K tokens, auto-compaction triggers. This summarizes earlier content, which means:
- System prompt survives (it's structural, not conversational)
- Early conversation messages get summarized and may lose nuance
- Add compaction instructions in CLAUDE.md: "When compacting, always preserve the full list of modified files"

---

## 8. PRODUCTION EXAMPLES

### Example 1: Trail of Bits Security Config

Trail of Bits runs Claude Code in `--dangerously-skip-permissions` mode with OS-level sandboxing. Their opinionated configuration includes:
- Sandboxing via Seatbelt (macOS) / bubblewrap (Linux)
- Hooks for security enforcement
- Skills for security auditing workflows
- Agent-native design principle: "agents can achieve any outcome users can"
- CLI tools as primary interface (preferring Exa AI for web searches)

Repository: [trailofbits/claude-code-config](https://github.com/trailofbits/claude-code-config)

### Example 2: Security Reviewer Agent (from Anthropic docs)

```markdown
---
name: security-reviewer
description: Reviews code for security vulnerabilities
tools: Read, Grep, Glob, Bash
model: opus
---
You are a senior security engineer. Review code for:
- Injection vulnerabilities (SQL, XSS, command injection)
- Authentication and authorization flaws
- Secrets or credentials in code
- Insecure data handling

Provide specific line references and suggested fixes.
```

### Example 3: Database Reader with Hook Enforcement

```yaml
---
name: db-reader
description: Execute read-only database queries
tools: Bash
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-readonly-query.sh"
---
You are a database analyst with read-only access. Execute SELECT queries to answer questions about the data.

You cannot modify data. If asked to INSERT, UPDATE, DELETE, or modify schema, explain that you only have read access.
```

### Example 4: VoltAgent Collection (100+ agents)

Repository [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) provides 100+ specialized subagents covering development use cases. Pattern: single responsibility, clear descriptions, minimal tool sets.

### Example 5: wshobson Multi-Agent System

Repository [wshobson/agents](https://github.com/wshobson/agents) combines:
- 112 specialized AI agents
- 16 multi-agent workflow orchestrators
- 146 agent skills
- 79 development tools
- 72 focused plugins

### Example 6: Captain Hook Policy Enforcement

[Captain Hook](https://www.securityreview.ai/blog/captain-hook-ai-agent-policy-enforcement-for-claude) provides deterministic policy enforcement by evaluating the agent's intent at the exact moment it decides to act. Enforcement is deterministic, not advisory.

### Example 7: Adaline Labs Guardrails Ladder

From [Adaline Labs](https://labs.adaline.ai/p/how-to-ship-reliably-with-claude-code):
- Plan gate before implementation
- Subagent review after implementation
- Multi-model review for critical changes
- PR opened only when all checks pass

### Example 8: Codacy Deterministic Guardrails

From [Codacy](https://blog.codacy.com/equipping-claude-code-with-deterministic-security-guardrails): Setup takes 5 minutes. Use PreToolUse hooks for security scanning, PostToolUse for validation. Deterministic means "always runs, always enforced."

---

## 9. RECOMMENDATIONS FOR SIOPV

Based on all research findings, here are specific recommendations for the SIOPV project's agent system.

### A. Agent Definition Architecture

1. **Keep agent bodies under 150 lines**. Front-load the 20 most critical rules.
2. **Use the four-field minimum**: `name`, `description`, `tools`, and body. Add `model`, `memory`, `hooks` only when needed.
3. **Set tool restrictions explicitly**: Every agent should have a `tools` allowlist. Never let verification agents have Write/Edit.
4. **Use `maxTurns`** for agents that might run away (especially exploratory ones).

### B. Persona Design Pattern for SIOPV Agents

Recommended structure for each agent definition body:

```markdown
## Identity
You are a [ROLE] specializing in [DOMAIN].

## Mandate
Your ONE task: [specific deliverable].

## Workflow
1. [Step with procedural constraint]
2. [Step with criteria constraint]
3. [Step with template constraint]

## Boundaries
- NEVER [prohibited action 1]
- NEVER [prohibited action 2]
- If [edge case], then [expected behavior]

## Output Format
[Template with exact structure expected]

## Verification
Before reporting completion:
- [ ] Check 1
- [ ] Check 2
```

### C. Guardrails Strategy

Layer all three tiers:

1. **Prompt-based** (in agent body): Persona, workflow steps, output format
2. **Tool restrictions** (in frontmatter): Remove tools agents don't need
3. **Hooks** (in frontmatter or settings.json): PreToolUse for safety-critical rules

For SIOPV specifically:
- `security-auditor`: Read-only tools + Bash. PreToolUse hook blocks any write commands.
- `code-implementer`: All tools, but PostToolUse hook runs ruff/mypy after every edit.
- `test-generator`: All tools, PostToolUse hook runs pytest after test file creation.
- `hallucination-detector`: Read-only only. No Bash.
- `best-practices-enforcer`: Read-only + Bash for running linters.

### D. Context Management

1. **CLAUDE.md**: Keep under 200 lines. Only universally applicable instructions.
2. **Rules files**: Use `.claude/rules/` with path targeting for domain-specific rules (e.g., `security.md` for `src/siopv/infrastructure/` files).
3. **Skills**: Move domain knowledge and detailed procedures into skills loaded on demand.
4. **Agent memory**: Enable `memory: project` for agents that build institutional knowledge (e.g., code-reviewer learning recurring issues).

### E. Anti-Drift for Verification Agents

1. **Template constraints on output**: Every verification agent should have an exact report template.
2. **Checklist in agent body**: Explicit items to check, not vague "review for quality."
3. **Escalation clause**: "If you cannot complete a check, report it as INCONCLUSIVE rather than skipping it."
4. **Self-verification**: "Before finalizing your report, verify that every section is filled and every file mentioned exists."

### F. Hook Enforcement for SIOPV

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/block-dangerous-commands.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/run-linter.sh"
          }
        ]
      }
    ]
  }
}
```

### G. Key Takeaways

1. **Prompts are requests, hooks are laws.** For anything that MUST happen, use hooks or tool restrictions.
2. **150 instructions is the ceiling.** Prune ruthlessly. Each instruction competes for attention.
3. **Lost-in-the-middle is real.** Put critical rules at the start and end of agent bodies.
4. **Tool restrictions are the most reliable guardrail.** An agent without Write tool literally cannot edit files.
5. **Per-step constraints beat uniform freedom levels.** Different steps need different constraint types.
6. **Fresh context beats accumulated context.** Use `/clear` between tasks; use subagents for exploration.
7. **Verification is the highest-leverage practice.** Give agents ways to check their own work.
8. **Personas leak beyond specification.** Explicitly state what agents should NOT do, not just what they should do.

---

## Sources

### Official Documentation
- [Create custom subagents - Claude Code Docs](https://code.claude.com/docs/en/sub-agents)
- [Hooks reference - Claude Code Docs](https://code.claude.com/docs/en/hooks)
- [Best Practices for Claude Code - Claude Code Docs](https://code.claude.com/docs/en/best-practices)
- [Keep Claude in character - Claude API Docs](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/keep-claude-in-character)
- [Skill authoring best practices - Claude API Docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [Equipping agents for the real world with Agent Skills - Anthropic](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [How Claude Code works - Claude Code Docs](https://code.claude.com/docs/en/how-claude-code-works)
- [The Persona Selection Model - Anthropic](https://www.anthropic.com/research/persona-selection-model)

### Community & Research
- [How to Stop Claude Code Skills from Drifting - DEV Community](https://dev.to/akari_iku/how-to-stop-claude-code-skills-from-drifting-with-per-step-constraint-design-2ogd)
- [I Wrote 200 Lines of Rules for Claude Code. It Ignored Them All - DEV Community](https://dev.to/minatoplanb/i-wrote-200-lines-of-rules-for-claude-code-it-ignored-them-all-4639)
- [Claude Code Rules Directory: Modular Instructions That Scale - ClaudeFast](https://claudefa.st/blog/guide/mechanics/rules-directory)
- [Writing a good CLAUDE.md - HumanLayer](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- [How to Ship Reliably With Claude Code - Adaline Labs](https://labs.adaline.ai/p/how-to-ship-reliably-with-claude-code)
- [Claude Code Hooks: Guardrails That Actually Work - Paddo.dev](https://paddo.dev/blog/claude-code-hooks-guardrails/)
- [Equipping Claude Code with Deterministic Security Guardrails - Codacy](https://blog.codacy.com/equipping-claude-code-with-deterministic-security-guardrails)
- [Stop Arguing With Claude Code: Where Your Agent Rules Actually Belong - Medium](https://medium.com/coding-nexus/stop-arguing-with-claude-code-where-your-agent-rules-actually-belong-f0a3caa0db18)
- [Claude Code Gets Path-Specific Rules - Paddo.dev](https://paddo.dev/blog/claude-rules-path-specific-native/)

### GitHub Repositories
- [SuperClaude-Org/SuperClaude_Framework](https://github.com/SuperClaude-Org/SuperClaude_Framework) - Cognitive personas and development methodologies
- [trailofbits/claude-code-config](https://github.com/trailofbits/claude-code-config) - Opinionated security-focused defaults
- [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) - 100+ specialized subagents
- [wshobson/agents](https://github.com/wshobson/agents) - 112 agents + orchestrators
- [ChrisWiles/claude-code-showcase](https://github.com/ChrisWiles/claude-code-showcase) - Hooks, skills, agents showcase
- [feiskyer/claude-code-settings](https://github.com/feiskyer/claude-code-settings) - Settings, commands, agents for vibe coding
- [steipete/agent-rules](https://github.com/steipete/agent-rules) - Rules and knowledge for agent work
- [rulebricks/claude-code-guardrails](https://github.com/rulebricks/claude-code-guardrails) - Real-time guardrails for tool calls
- [disler/claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery) - Hooks mastery patterns

### Blog Posts & Guides
- [Claude Code Hooks Guide: All 12 Lifecycle Events - Pixelmojo](https://www.pixelmojo.io/blogs/claude-code-hooks-production-quality-ci-cd-patterns)
- [Claude Code Hooks Complete Guide (February 2026) - SmartScope](https://smartscope.blog/en/generative-ai/claude/claude-code-hooks-guide/)
- [Claude Code: Tips and Tricks for Advanced Users - Cuttlesoft](https://cuttlesoft.com/blog/2026/02/03/claude-code-for-advanced-users/)
- [Best practices for Claude Code subagents - PubNub](https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/)
- [How to Write a Good CLAUDE.md - Builder.io](https://www.builder.io/blog/claude-md-guide)
- [ClaudeLog - Best Practices](https://claudelog.com/)
