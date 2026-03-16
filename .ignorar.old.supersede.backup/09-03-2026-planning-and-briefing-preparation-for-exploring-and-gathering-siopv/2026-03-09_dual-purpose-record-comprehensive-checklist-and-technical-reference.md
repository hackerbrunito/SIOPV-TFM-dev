# Comprehensive Checklist and Technical Reference for Claude Code Agent Projects

**Created:** 2026-03-09
**Sources:** `003_checkpoints-extracted-from-claude-code-report.md` (58 checkpoints) and `004_checkpoints-extracted-from-llm-behavioral-report.md` (74 checkpoints)
**Purpose:** Single source of truth that serves as both a complete implementation checklist and a technical reference for building well-structured, high-quality Claude Code agent projects. Designed to survive any number of context compactions.

---

## TABLE OF CONTENTS

1. [Agent Definition Structure](#1-agent-definition-structure)
2. [Persona and Behavioral Design](#2-persona-and-behavioral-design)
3. [Instruction-Following Techniques](#3-instruction-following-techniques)
4. [Guardrails and Enforcement (Three-Tier Framework)](#4-guardrails-and-enforcement)
5. [Hooks Configuration](#5-hooks-configuration)
6. [Rules Files and Instruction Management](#6-rules-files-and-instruction-management)
7. [Anti-Improvisation and Anti-Drift Techniques](#7-anti-improvisation-and-anti-drift-techniques)
8. [Context Positioning and Attention Management](#8-context-positioning-and-attention-management)
9. [Context Rot, Compaction, and Memory Survival](#9-context-rot-compaction-and-memory-survival)
10. [Structured Output Enforcement](#10-structured-output-enforcement)
11. [Multi-Agent Behavioral Control](#11-multi-agent-behavioral-control)
12. [Agent Handoff and Shutdown](#12-agent-handoff-and-shutdown)
13. [Production Patterns and Case Studies](#13-production-patterns-and-case-studies)
14. [SIOPV-Specific Recommendations](#14-siopv-specific-recommendations)
15. [Summary and Quick-Reference Tables](#15-summary-and-quick-reference-tables)

---

## 1. AGENT DEFINITION STRUCTURE

### 1.1 File Format and Location

- [ ] **Markdown + YAML frontmatter format.** Agent definitions are `.md` files with YAML frontmatter in `.claude/agents/`. Frontmatter = metadata/constraints. Markdown body = system prompt. Subagents receive ONLY this system prompt plus basic environment details (working directory), NOT the full Claude Code system prompt. The body IS the entire behavioral context.
- [ ] **File location priority order.** (1) `--agents` CLI flag = session-only, priority 1. (2) `.claude/agents/` = project-scoped, priority 2. (3) `~/.claude/agents/` = user-scoped, priority 3. (4) Plugin `agents/` dir = priority 4.
- [ ] **CLI JSON agents for ephemeral sessions.** Use `--agents` CLI flag with JSON for session-only agents. `prompt` field in JSON is equivalent to markdown body. Example: `claude --agents '{"name": {"description": "...", "prompt": "...", "tools": [...], "model": "sonnet"}}'`

### 1.2 Frontmatter Fields

- [ ] **Four-field minimum enforced.** Every agent must have at minimum: `name`, `description`, `tools`, and body content. Add `model`, `memory`, `hooks`, `maxTurns` only when needed. These four fields establish identity, delegation routing, capability boundaries, and behavioral instructions.
- [ ] **All 14 frontmatter fields understood and explicitly decided.** Full field inventory: `name` (required, lowercase+hyphens), `description` (required, used for auto-delegation), `tools` (allowlist), `disallowedTools` (denylist), `model` (sonnet/opus/haiku/inherit), `permissionMode` (default/acceptEdits/dontAsk/bypassPermissions/plan), `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory` (user/project/local), `background`, `isolation` (worktree). For each agent, explicitly decide the value of every field (even if the decision is "omit/use default").

### 1.3 Description Field for Delegation

- [ ] **Description field drives delegation routing.** The `description` field is used by Claude for auto-delegation decisions -- it determines WHEN the agent gets invoked. Write descriptions that specify the exact trigger conditions: "Expert code review specialist. Use immediately after writing or modifying code." NOT "Reviews code."

### 1.4 Tool Restriction Syntax

- [ ] **Allowlist and denylist syntax validated.** Allowlist: `tools: Read, Grep, Glob, Bash`. Denylist: `disallowedTools: Write, Edit`. Restrict subagent spawning: `tools: Agent(worker, researcher), Read, Bash`. Allow any subagent: `tools: Agent, Read, Bash`. Syntax errors in tool restrictions silently fail, leaving the agent with full tool access. Test by checking if the agent can use tools it shouldn't have.

### 1.5 Agent Memory

- [ ] **Memory configured for institutional learning.** Set `memory: project` (or `user`/`local`) to give agents persistent cross-session learning. Agent gets a `MEMORY.md` file (first 200 lines injected at startup) with Read/Write/Edit auto-enabled. Memory directory: `.claude/agent-memory/<name>/` (project scope). Agent must curate MEMORY.md if it exceeds 200 lines. Enable for agents that benefit from accumulated knowledge (code-reviewer, security-auditor).

---

## 2. PERSONA AND BEHAVIORAL DESIGN

### 2.1 Core Principle

- [ ] **System prompt IS the persona -- single surface.** The body of the agent definition IS the system prompt. The subagent receives ONLY this plus environment details -- nothing from the parent conversation. Every behavioral instruction must be self-contained in the agent body. Write each agent body as if it were the only instructions the agent will ever see.

### 2.2 Proven Persona Patterns

- [ ] **Pattern A -- Role + Checklist.** (1) "You are a [role]." (2) "When invoked: 1. 2. 3." (3) "Checklist: - item - item" (4) "Provide feedback organized by: Critical / Warnings / Suggestions." The checklist gives explicit verification criteria rather than vague "review for quality." (Anthropic docs pattern)
- [ ] **Pattern B -- Domain Expert with Workflow.** (1) "You are an expert [domain] specializing in [specific area]." (2) Numbered steps: capture, identify, isolate, implement, verify. (3) "Focus on [root principle], not [surface approach]." The sequential workflow prevents the agent from jumping to conclusions. (Anthropic docs pattern)
- [ ] **Pattern C -- Behavioral Boundaries with Scenario Handling.** 3-5 interaction rules, then explicit scenario-response mappings: "If [situation], then [exact response]." Pre-scripted scenario responses prevent improvisation in sensitive situations. (Anthropic API docs pattern)
- [ ] **Pattern D -- Cognitive Personas (SuperClaude).** Personas are `.md` files containing domain-specific expertise, behavioral patterns, and problem-solving approaches. Invocable via `@agent-security` syntax. 16 specialist agents that can delegate to each other.

### 2.3 Four Elements of Effective Persona (Anthropic Official Guidance)

- [ ] **Role set in system prompt.** Even a single sentence makes a difference.
- [ ] **Detailed personality info.** Background, traits, quirks help the model generalize.
- [ ] **Scenarios prepared.** List common situations and expected responses.
- [ ] **Constrained with examples.** Show desired output format -- this "trains" understanding better than abstract instructions.

### 2.4 Direct Persona Assignment

- [ ] **"You are an X" over "Imagine you are...".** Direct persona assignment outperforms imagination framing empirically (LearnPrompting, 2025). Audit all agent prompts. Replace any "Imagine you are...", "Pretend to be...", "Act as if you were..." with direct "You are..." statements.

### 2.5 Persona Scope and Limitations

- [ ] **Persona controls style, NOT accuracy.** Vanilla prompting and persona prompting perform very similarly on accuracy tasks. Persona effectively controls: style, tone, output format, domain vocabulary usage, behavioral constraints (refusals). It does NOT reliably control: factual accuracy, deep reasoning quality, or knowledge beyond training data. Always pair persona with RAG/tool access for knowledge, structured output for format, and validation for correctness.
- [ ] **Anti-pattern: persona trait leakage.** When Claude adopts a persona, it infers personality traits that drive OTHER behaviors beyond those specified. A "friendly helper" persona may become inappropriately casual in security audits. Mitigation: Be explicit about what the persona should NOT do. Add explicit NOT instructions for every behavioral dimension that matters. (Anthropic Persona Selection Model, 2026)

### 2.6 CrewAI Role-Goal-Backstory Pattern

- [ ] **Three mandatory agent attributes.** Role (professional identity -- be specific: "Senior Python Security Auditor" not "Developer"), Goal (single, measurable objective per agent), Backstory (narrative context establishing WHY this agent exists). Specialists outperform generalists.
- [ ] **80/20 Rule: tasks over agent definitions.** 80% of effort into designing tasks, only 20% into defining agents. Task design drives output quality more than agent persona refinement.
- [ ] **Specialists over generalists.** If two agents share >30% of their responsibilities, merge or re-split them. No agent should handle more than one domain.

### 2.7 Constraint-Based Personas

- [ ] **MUST NOT rules alongside MUST rules.** Every agent definition must include a "MUST NOT" section listing at least 3 prohibited behaviors (e.g., "MUST NOT modify files outside the target directory", "MUST NOT make network calls", "MUST NOT approve its own output"). Negative constraints prevent scope creep.

### 2.8 Recommended Agent Body Template (Six Sections)

- [ ] **Section 1 -- Identity:** "You are a [ROLE] specializing in [DOMAIN]."
- [ ] **Section 2 -- Mandate:** "Your ONE task: [specific deliverable]."
- [ ] **Section 3 -- Workflow:** Numbered steps with per-step constraint types (Procedural/Criteria/Template/Guardrail).
- [ ] **Section 4 -- Boundaries:** NEVER statements + edge case handling.
- [ ] **Section 5 -- Output Format:** Exact template structure.
- [ ] **Section 6 -- Verification:** Pre-completion checklist.
- [ ] Reject agent definitions missing any section.

---

## 3. INSTRUCTION-FOLLOWING TECHNIQUES

### 3.1 System Prompt Design

- [ ] **Right altitude balance.** System prompts must occupy a "Goldilocks zone" -- specific enough to guide behavior, flexible enough to provide strong heuristics. No brittle if-else logic (no chains with >3 branches). No vague guidance that assumes shared context. Every constraint has a concrete example or heuristic.
- [ ] **Structural organization with XML/Markdown sections.** Use distinct sections with XML tags or Markdown headers to organize system prompts. Every system prompt and agent briefing must separate: background, instructions, tool guidance, output format, constraints.
- [ ] **Minimal viable prompt approach.** Start with minimal instructions using the best model, then add clarity based on observed failure modes rather than anticipating all edge cases. For new agents, start with a 5-10 line prompt. Log failure modes. Add constraints only for observed failures. Track prompt evolution in version control.

### 3.2 Attention and Repetition

- [ ] **Prompt repetition for attention boost.** Repeating the input prompt improves performance for all major models without increasing generated tokens or latency. Accuracy improvements of up to 67-76% on non-reasoning tasks. Repeat critical instructions at the end of the context window. For non-negotiable rules, include them both in the system prompt AND appended after the final user message. (Leviathan et al., Google Research, arXiv 2512.14982, Dec 2025)
- [ ] **Primacy and recency positioning.** Instructions at the beginning and end of context receive the most attention (U-shaped attention curve). Performance drops >30% when key information sits in the middle. Place non-negotiable constraints at the very beginning. Repeat critical rules at the very end. Never bury important constraints in the middle of long contexts. Audit long prompts (>2000 tokens) for critical rules buried in the middle.

### 3.3 Instructional Segment Embedding (ISE)

- [ ] **Token role classification.** Categorize instruction tokens by role: system instruction = 0, user prompt = 1, data input = 2. For API-based models, use the native system/user/assistant role separation rigorously -- never mix instruction types within a single role message. (ICLR 2025)

### 3.4 Few-Shot Examples

- [ ] **Diverse canonical examples.** For each agent, include 3-5 canonical examples covering the range of expected inputs/outputs. Prefer diversity over edge-case coverage. Review examples quarterly for staleness. Examples shape behavior more reliably than verbose instructions.

### 3.5 Behavioral Templates

- [ ] **Three-template system for fine-grained control.** Use `system_template`, `prompt_template`, `response_template`. System template sets identity, prompt template structures input, response template constrains output format. (PLoP 2024)

### 3.6 Reasoning Mode

- [ ] **Enable reasoning for planning agents.** Enable `reasoning: true` for agents needing planning and reflection before action: orchestrators, code reviewers, security auditors, multi-step decision makers. Disable for simple extraction or formatting agents.

---

## 4. GUARDRAILS AND ENFORCEMENT

### 4.1 The Fundamental Insight

- [ ] **Prompts are requests, hooks are laws.** Rules in prompts are probabilistic requests (Claude may ignore them). Hooks in code are deterministic laws (always execute, cannot be overridden). Claude can read and recite instructions without following them. For anything that MUST happen, implement it as a hook or tool restriction. For preferences and guidance, use prompts. Never rely on prompts alone for safety-critical rules.

### 4.2 The 150-Instruction Ceiling

- [ ] **Instruction compliance decreases with volume.** Frontier models max out at ~150-200 instructions. Beyond this threshold, more rules correlate with WORSE overall compliance across ALL rules. Keep the 20 most critical rules in prompts. Handle the rest via hooks, tool restrictions, or remove them entirely. Count total instructions across all loaded contexts (CLAUDE.md + rules + agent body + skills). (Jaroslawicz et al., 2025)

### 4.3 Three-Tier Guardrails Framework

- [ ] **Tier 1: Prompt-based (probabilistic, ~80% compliance at best, degrades with volume).** For guidance, preferences, soft constraints. Accept ~80% as the ceiling. Monitor and escalate frequently-violated rules.
- [ ] **Tier 2: Tool restrictions (deterministic, 100% compliance).** Tools simply don't exist for the agent. Remove tools the agent doesn't need. An agent without the Write tool cannot create files regardless of how persuasive its reasoning is. Most reliable anti-improvisation mechanism.
- [ ] **Tier 3: Hooks (deterministic, 100% compliance).** Code runs regardless of Claude's reasoning. PreToolUse hooks can block actions. PostToolUse hooks react after actions.
- [ ] **Layer all three tiers simultaneously.** For each agent, implement all three. If the prompt fails (20% of the time), tool restrictions catch the action. If a new tool somehow bypasses restrictions, hooks catch it. Create a matrix: agent x tier x what's implemented.

### 4.4 Guardrails Ladder (Adaline Labs)

- [ ] **Three escalation levels.** Tier 1 = Read-only and analysis (inspect, explain, plan). Tier 2 = Controlled changes in scoped directories (edit only within approved paths). Tier 3 = PR-ready changes with enforced checks (produce PR candidates only after automated checks pass). Assign each agent to a tier.

### 4.5 Per-Step Constraint Types (4 Types)

- [ ] **Procedural (HOW):** Sequential steps, divergence acceptable.
- [ ] **Criteria (WHAT):** Quality judgment, replace "how" with explicit standards.
- [ ] **Template:** Fixed output structure, flexible content.
- [ ] **Guardrail:** Boundaries by prohibition, what must NEVER happen.
- [ ] For each step in an agent's workflow, assign one of the four constraint types and document it alongside the step.

### 4.6 Three-Layer Guardrail Architecture (Production)

- [ ] **Input Layer:** Injection detection, format validation, PII detection (Presidio), rate limits, malicious content filtering.
- [ ] **Interaction Layer:** Tool restriction, autonomous decision cap (max 20 tool calls per invocation), state-machine tool availability, token budget per interaction.
- [ ] **Output Layer:** Structured validation (Pydantic), relevancy checks, hallucination detection, content safety, schema compliance.
- [ ] Every agent must have at least one guardrail per layer.

### 4.7 Deterministic vs Probabilistic Control

- [ ] **For every critical rule currently in CLAUDE.md or rules files, ask:** "What happens if Claude ignores this?" If the answer is unacceptable, implement a deterministic equivalent (hook or tool restriction). Example: "Don't edit .env files" in CLAUDE.md (probabilistic, may be ignored) vs. PreToolUse hook that exits with code 2 when .env is targeted (deterministic, always blocks).

---

## 5. HOOKS CONFIGURATION

### 5.1 Hook Events Inventory (March 2026)

- [ ] **16 hook events known and mapped.** `SessionStart` (startup/resume/clear/compact), `UserPromptSubmit`, `PreToolUse` (tool name matcher, CAN BLOCK), `PermissionRequest`, `PostToolUse`, `PostToolUseFailure`, `Notification`, `SubagentStart` (agent type), `SubagentStop` (agent type), `Stop`, `TeammateIdle`, `TaskCompleted`, `InstructionsLoaded`, `ConfigChange`, `PreCompact` (manual/auto), `SessionEnd`, `WorktreeCreate`/`WorktreeRemove`.

### 5.2 PreToolUse -- The Only Blocking Hook

- [ ] **PreToolUse is the ONLY hook that can block actions.** Two blocking mechanisms: (1) Exit code 2 = block. (2) JSON output with `permissionDecision: "deny"`. Every safety-critical rule that must prevent an action needs a PreToolUse hook.
- [ ] **Exit code blocking pattern.** `INPUT=$(cat)` -> extract via `jq` -> pattern match -> `exit 2` to block, `exit 0` to allow. Error message via stderr (`>&2`).
- [ ] **JSON output blocking pattern.** `jq -n '{ hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: "..." } }'`. Provides structured reason Claude can use to explain the denial.
- [ ] **PreToolUse can modify tool inputs (v2.0.10+).** Can rewrite tool parameters before execution. Use cases: add dry-run flags, redact secrets from commands.

### 5.3 Three Handler Types

- [ ] **`command`:** Shell script, deterministic, best for security rules (block patterns, validate SQL).
- [ ] **`prompt`:** LLM judgment call, for nuanced/context-dependent decisions.
- [ ] **`agent`:** Full codebase state verification, most expensive but most capable.

### 5.4 Hook Configuration Locations (Priority Order)

- [ ] (1) `~/.claude/settings.json` -- all projects.
- [ ] (2) `.claude/settings.json` -- single project, committable.
- [ ] (3) `.claude/settings.local.json` -- single project, gitignored.
- [ ] (4) Managed policy settings -- organization-wide.
- [ ] (5) Plugin `hooks/hooks.json` -- when plugin enabled.
- [ ] (6) Agent frontmatter -- while agent is active.
- [ ] Place hooks at the narrowest applicable scope.

### 5.5 Hook Configuration in Agent Frontmatter

- [ ] **Agent-scoped hooks only run when that specific agent is active.** Add hooks directly to agent frontmatter YAML. Matcher supports pipe-separated tool names: `"Edit|Write"`. Each hook entry needs `type: command` and `command: "./path/to/script.sh"`.

### 5.6 What Hooks CAN Enforce (8 Capabilities)

- [ ] (1) Block dangerous commands (PreToolUse + exit 2).
- [ ] (2) Validate SQL queries (block writes, allow SELECT).
- [ ] (3) Protect files (block Write/Edit to specific paths).
- [ ] (4) Auto-format (PostToolUse runs linter after every edit).
- [ ] (5) Run tests (PostToolUse after changes).
- [ ] (6) Modify tool inputs (PreToolUse v2.0.10+, rewrite parameters: add dry-run flags, redact secrets).
- [ ] (7) Enforce conventions (PostToolUse checks naming/structure).
- [ ] (8) Setup/teardown (SubagentStart/SubagentStop for resource management).

### 5.7 What Hooks CANNOT Enforce (5 Limitations)

- [ ] (1) Reasoning quality -- hooks see actions, not thought processes.
- [ ] (2) Instruction recall -- cannot force Claude to remember something.
- [ ] (3) Planning decisions -- cannot control WHICH tool Claude decides to use.
- [ ] (4) Output quality -- can validate format but not semantic correctness.
- [ ] (5) Cross-turn consistency -- each hook invocation is stateless.
- [ ] For these guarantees, use complementary approaches (verification agents, multi-model review).

---

## 6. RULES FILES AND INSTRUCTION MANAGEMENT

### 6.1 Directory Structure

- [ ] **Rules stored in `.claude/rules/` as standalone Markdown files** with optional YAML frontmatter. Files are discovered recursively, supporting subdirectories for organization. Example: `.claude/rules/code-style.md`, `.claude/rules/security.md`, `.claude/rules/frontend/react.md`.

### 6.2 Path-Targeted Rules

- [ ] **YAML frontmatter `paths:` with glob patterns** to activate rules only when Claude works on matching files. Reduces instruction volume by loading rules only when relevant.
- [ ] **Known bug: path rules only trigger on READ.** Path-based rules only inject into context when Claude READS a matching file, NOT when writing/creating files. For rules that must apply during file creation, make them global (no paths) or implement via hooks.

### 6.3 Rules Loading Behavior

- [ ] Rules without `paths` = global (loaded at session start). Rules with `paths` = conditional (loaded on file match). `InstructionsLoaded` hook event fires when rules are loaded.

### 6.4 Four Instruction Mechanisms (Correct Placement)

| Mechanism | When Loaded | Scope | Use For |
|-----------|-------------|-------|---------|
| CLAUDE.md | Every session | Broad project | Build commands, project conventions |
| `.claude/rules/*.md` | Session start or file match | Modular scoped policies | Domain-specific rules |
| Skills | On demand | Domain knowledge/workflows | Detailed procedures, reference material |
| Agent body | When spawned | Agent-specific system prompt | Identity, mandate, workflow, boundaries |

- [ ] Classify every instruction by scope and timing. Place it in the correct mechanism. Audit for misplacements.

### 6.5 Five Rules for Effective Rule Writing

- [ ] (1) **Keep under 150 instructions total** across all loaded contexts.
- [ ] (2) **Be specific and measurable:** "Calculate ROI on a 3-year TCO basis" beats "Calculate ROI".
- [ ] (3) **Use emphasis markers:** `IMPORTANT`, `YOU MUST`, `CRITICAL` improve adherence. Use sparingly -- overuse dilutes the effect.
- [ ] (4) **Delete rules Claude already follows** -- if removing a rule doesn't change behavior, it wastes attention.
- [ ] (5) **Test rules by observation** -- watch whether behavior actually shifts.

### 6.6 What Rules CANNOT Do (5 Limitations)

- [ ] Rules are advisory, not enforced. Claude can read and recite rules without following them.
- [ ] Compliance degrades as total instruction volume increases.
- [ ] Long sessions cause rule "forgetting" due to context dilution.
- [ ] Rules may be deemed "not relevant" by the model and ignored (Claude's system prompt says instructions "may or may not be relevant").
- [ ] For any rule where non-compliance is unacceptable, implement a deterministic alternative.

---

## 7. ANTI-IMPROVISATION AND ANTI-DRIFT TECHNIQUES

### 7.1 Per-Step Constraint Design

- [ ] **Instead of one freedom level for an entire workflow, assign constraint type per step.** Data collection = Procedural. Analysis = Criteria. Reporting = Template. Safety checks = Guardrail.

### 7.2 Todo List Recitation for Context Anchoring

- [ ] **Agent constantly rewrites a todo list after each step:** `[x] Completed` / `[ ] Remaining` / `Current focus: [step]`. Pushes the global plan into the END of the context window (high-attention zone). Combats lost-in-the-middle degradation.
- [ ] **todo.md pattern (Manus AI).** Every orchestrator and long-running agent must maintain a `todo.md` file. Update after every significant action. Read it back before making decisions. Include: current objective, completed steps, remaining steps, blockers. Serves as both external memory (survives compaction) AND attention anchor (anti-drift).

### 7.3 Fresh Context Windows

- [ ] **Use `/clear` between unrelated tasks.** A clean session with a better prompt almost always outperforms a long session with accumulated corrections. After two failed corrections in one session, start fresh.
- [ ] **Fresh context by default for sub-agents.** Each new agent starts with fresh conversation history. Include prior context only when explicitly needed. When including prior context, use summary transfer (not full history) unless continuity is critical.

### 7.4 Skills as Instruction Anchors

- [ ] **Skills provide step-by-step procedures that Claude follows rigidly.** Without a skill, Claude improvises. With a skill, it follows the defined sequence. For any workflow where Claude improvises despite instructions, convert the workflow into a skill with explicit step-by-step procedures.

### 7.5 Escalation Design

- [ ] **Build flexibility into constraints:** "If these constraints don't fit, propose alternatives with reasoning." Add an escalation clause to every agent's Boundaries section: "If you encounter a situation where these constraints are inappropriate, report it as ESCALATION with your reasoning rather than ignoring the constraint."

### 7.6 Verification Loops -- Highest-Leverage Practice

- [ ] **Give Claude ways to verify its own work:** tests to run, screenshots to compare, expected outputs to validate, linter results to check. Self-verification is the "single highest-leverage thing you can do" (Anthropic official best practices). Every agent body should include a Verification section with concrete checks.

### 7.7 Scoped Tool Access

- [ ] **Remove tools the agent doesn't need.** An agent with only Read, Grep, Glob literally CANNOT improvise by editing files. Default to read-only and add write tools only when the agent's mandate requires modification. Most reliable anti-improvisation mechanism because it is deterministic.

### 7.8 maxTurns Limit

- [ ] **Set `maxTurns` in frontmatter to cap agentic turns.** Simple verification: 10-15 turns. Code implementation: 30-50 turns. Exploratory research: 20-30 turns. Adjust based on observation.

### 7.9 Explicit NOT Instructions

- [ ] **From Anthropic's persona research: Claude infers personality traits beyond what's specified.** Explicitly state what the agent should NOT do. For every agent, add 3-5 DO NOT statements. Example: "DO: Report vulnerabilities with severity ratings. DO NOT: Fix code, suggest implementations, or make edits. DO NOT: Speculate about business impact. DO NOT: Skip files because they 'look fine'."

### 7.10 External Memory for Behavioral Stability

- [ ] **Workflows using external memory show 21% higher behavioral stability** than those relying solely on conversation history. External memory provides "behavioral anchors" resistant to incremental drift. Implement external memory files for: architectural decisions, non-negotiable constraints, accumulated findings, phase state. Re-read these files at decision points.

### 7.11 Runtime Reinforcement via Instruction Re-injection

- [ ] **Callback pattern: intercept LLM requests, generate reinforcement block, append non-negotiable rules to end of prompt.** Rules at the end of context receive maximum attention (recency effect). Apply to every LLM call, not just the first. Timestamp each request for temporal awareness.

### 7.12 Controlled Variation to Break Pattern Lock-In

- [ ] **If context is full of similar past action-observation pairs, the model follows that pattern even when suboptimal.** Introduce structured variation: different serialization templates, alternate phrasing, minor formatting noise. Monitor for repetitive action sequences as a lock-in signal.

### 7.13 Episodic Memory Consolidation

- [ ] **After every 10-20 tool calls, consolidate:** summarize completed work, discard raw tool outputs. Always preserve: decisions made, errors encountered, constraints discovered. Keep last 5 full turns + summary of older turns.

### 7.14 Drift Detection via LLM Judges

- [ ] **Online detection using LLM judges or statistical tests.** For critical agents, implement a lightweight judge that: compares output against baseline expectations, flags deviations >2 standard deviations, triggers re-generation or human escalation.

### 7.15 Agent Stability Index (ASI) -- 12 Dimensions

- [ ] **Track at minimum:** response consistency, tool usage patterns, reasoning pathway stability, inter-agent agreement rates. Log per-agent per-session. (arXiv 2601.04170, Jan 2026)

### 7.16 Three Types of Drift

- [ ] **Semantic drift:** Progressive deviation from original intent. Mitigation: re-anchoring.
- [ ] **Coordination drift:** Breakdown in multi-agent consensus. Mitigation: protocol enforcement.
- [ ] **Behavioral drift:** Emergence of unintended strategies. Mitigation: constraint reinforcement.
- [ ] Monitor for each type separately.

### 7.17 Context Equilibria

- [ ] **Multi-turn drift reaches stable, noise-limited equilibria** rather than runaway decay. Simple reminder interventions reliably reduce divergence. Implement periodic reminder injection (every N turns or tokens) rather than continuous reinforcement. (arXiv 2510.07777, Oct 2025)

---

## 8. CONTEXT POSITIONING AND ATTENTION MANAGEMENT

### 8.1 Lost-in-the-Middle Is Fundamental

- [ ] **LLMs pay the most attention to tokens at the START and END of the context window.** Information in the middle gets deprioritized. This is architectural, not a bug. Instruction placement matters as much as instruction content.

### 8.2 Four-Zone Positioning Hierarchy

| Zone | Position | Attention Level | What Goes Here |
|------|----------|----------------|----------------|
| 1 | System prompt (agent body) | Highest | Core persona, critical rules, workflow steps |
| 2 | Start of conversation | High | CLAUDE.md, project conventions |
| 3 | End of conversation | High | Todo lists, most recent messages, skills |
| 4 | Middle of conversation | Lowest | Earlier non-boundary messages |

### 8.3 Placement Matrix for Instruction Types

- [ ] **Agent body (system prompt):** Core persona, critical rules, workflow steps (highest attention, loaded fresh each time).
- [ ] **CLAUDE.md:** Project conventions, build commands (loaded early, high position).
- [ ] **`.claude/rules/`:** Scoped policies (same priority as CLAUDE.md).
- [ ] **Skills:** Domain knowledge, procedures (loaded on demand, enters at end = recency = high attention).
- [ ] **Todo list:** Current plan, remaining steps (pushed to end = high attention).

### 8.4 Agent Body Size Management

- [ ] **Keep agent body under 200 lines.** Shorter system prompts get more uniform attention. Within those 200 lines, front-load the 20 most critical rules. If over 200 lines, move non-critical content to skills loaded on demand.
- [ ] **Front-load critical rules.** Put the most important instructions at the TOP. Repeat the single most important rule at both the start AND end of the body.

### 8.5 Emphasis Markers

- [ ] **`IMPORTANT`, `CRITICAL`, `YOU MUST` demonstrably improve adherence.** Use sparingly -- overuse dilutes the effect (every instruction being "CRITICAL" means none are). Add to the 20 most critical instructions.

### 8.6 Structured Format Over Prose

- [ ] **Headers, bullet points, tables are more scannable than prose.** Convert all prose instructions to structured format.

### 8.7 Progressive Disclosure via Skills

- [ ] **Keep base prompt minimal, load detailed knowledge via skills only when needed.** Agent body contains only: identity, mandate, workflow skeleton, boundaries. Skills contain: detailed procedures, domain knowledge, reference material.

### 8.8 Prune Rules That Don't Change Behavior

- [ ] **Remove any instruction that doesn't change behavior when removed.** Each line should pass the test: "Would removing this cause Claude to make mistakes?" Systematically test each rule by temporarily removing it and observing behavior.

### 8.9 CLAUDE.md Token Budget

- [ ] **CLAUDE.md loaded EVERY session. Recommended: under 300 lines.** Shorter is better. Bloated CLAUDE.md files cause Claude to ignore actual instructions -- it actively degrades compliance with all instructions including those in the CLAUDE.md itself.

---

## 9. CONTEXT ROT, COMPACTION, AND MEMORY SURVIVAL

### 9.1 Three Mechanisms of Context Rot

- [ ] **(1) Lost-in-the-Middle Effect:** U-shaped attention curve.
- [ ] **(2) Attention Dilution at Scale:** Attention budget spread thinner as context grows.
- [ ] **(3) Distractor Interference:** Irrelevant context actively degrades performance -- adding irrelevant content is worse than having less context.
- [ ] Minimize irrelevant content. Prefer sub-agent delegation with clean context. Actively prune conversation history of tool outputs no longer relevant.

### 9.2 Measured Impact Thresholds

- [ ] Performance drops >30% when relevant information sits in the middle vs. beginning/end.
- [ ] Critical instructions buried 10,000+ tokens back are frequently "forgotten."
- [ ] Negative constraints (things NOT to do) are especially vulnerable to being ignored in long contexts.
- [ ] For contexts >10,000 tokens, re-inject critical instructions. Place all negative constraints in system prompt AND repeat at end.

### 9.3 KV-Cache Optimization

- [ ] **KV-cache hit rate is the primary production metric.** Cached input tokens cost $0.30/MTok vs. uncached $3/MTok (Claude Sonnet) -- 10x cost difference.
- [ ] **Append-only context design:** Never modify or reorder previous content. Corrections appended as new messages. Tool results in execution order.
- [ ] **Deterministic serialization:** Same data must produce same bytes every time. Use `json.dumps(data, sort_keys=True)`. Avoid timestamps or random values in serialized prompts unless semantically necessary.
- [ ] **Consistent tool name prefixes:** e.g., `browser_*`, `shell_*`.

### 9.4 Auto-Compaction Survival Strategy

- [ ] **Auto-compaction triggers at ~95% of 200K tokens.** System prompt survives (structural). Early conversation messages get summarized and may lose nuance.
- [ ] **Add compaction instructions in CLAUDE.md:** "When compacting, always preserve: [list of critical context items]." Example: the full list of modified files.

### 9.5 Three Compression Approaches and Their Risks

- [ ] **(1) Prompt Compression (LLMLingua):** Token-level pruning, risk of breaking meaning.
- [ ] **(2) Dynamic Summarization:** Living summary + last N turns, risk of losing specific constraints.
- [ ] **(3) Verbatim Compaction:** Delete tokens without rewriting, most faithful but least flexible.
- [ ] Design instructions to survive all three: keep constraints self-contained (not dependent on surrounding text), use explicit values not references, mark critical sections for preservation.

### 9.6 Never Generalize Specific Values

- [ ] **Keep exact names, paths, values, error messages, URLs, and version numbers verbatim.** Write "threshold is 0.7" not "threshold is defined elsewhere." Include full file paths, not relative references.

### 9.7 Separate Survival-Critical Instructions

- [ ] Instructions that MUST survive should be in system prompts or pinned sections, not embedded in conversation. Use `<!-- COMPACT-SAFE: summary -->` markers on all critical workflow sections. Every file in `.claude/workflow/` must have a COMPACT-SAFE marker.

### 9.8 Structural Redundancy -- Triple Storage

- [ ] **Critical rules should appear in three places:** system prompt + external file + periodic re-injection. If any rule exists in only one location, it is at risk.

### 9.9 External Memory as Compaction Bypass

- [ ] **Persistent files (NOTES.md, todo.md, projects/*.json) survive compaction entirely** because they exist outside the context. Write critical decisions to disk immediately, not just in conversation. Re-read external files at decision points.
- [ ] **Manus file-system-as-memory pattern:** The file system is the ultimate context: unlimited in size, persistent by nature, directly operable by the agent. For any information that must persist beyond the current context window, write it to a structured file.

### 9.10 Compaction Tuning Parameters

- [ ] Set compaction trigger at 80% of context window. Preserve last 10 messages unchanged. Test compaction output for information loss before deploying. Log what was discarded.

---

## 10. STRUCTURED OUTPUT ENFORCEMENT

### 10.1 Reliability Ranking

| Rank | Approach | Reliability |
|------|----------|-------------|
| 1 | Constrained Decoding (NVIDIA NIM, Guidance, llama.cpp) | Highest -- guarantees format |
| 2 | API-Native Structured Output (Claude, OpenAI) | High |
| 3 | JSON Schema + Validation | High |
| 4 | Pydantic Validation | Medium-High |
| 5 | Grammar-Based Decoding | Medium |
| 6 | Prompt-Only | Lowest -- never for production |

- [ ] For each agent output, select the highest-reliability approach available. Never use prompt-only for any output that will be parsed programmatically.

### 10.2 Pydantic AI Integration

- [ ] **Define Pydantic models for every agent's input and output.** Use these for both prompt construction (JSON Schema) and response validation. Enable durable execution for long-running agents. Pydantic AI streams with immediate validation and supports durable execution across transient API failures.

### 10.3 Validation-Repair Loop

- [ ] **When structured output fails validation:** (1) Validate with Pydantic or Guardrails AI. (2) On failure, run a "repair" prompt with the validator's errors. (3) Retry with error context. Maximum 3 retry attempts. (4) Version payloads with `schemaVersion` field using semver. Log repair events as quality signals.

### 10.4 Guardrail Frameworks for Output

- [ ] **NVIDIA NeMo Guardrails with Colang:** Declarative language for guardrail logic. Topical/safety/execution rails. OpenTelemetry integration.
- [ ] **Guardrails AI:** Pre-built validators from Guardrails Hub (JSON format, PII, profanity). Custom validators for domain-specific rules. Auto-fix vs. re-prompt configurable per validator.
- [ ] **Llama Guard:** Meta's specialized safety classifier. Customizable safety taxonomies, low-latency classification.

### 10.5 DLP-First Guardrail Strategy

- [ ] **Data Loss Prevention is the recommended starting point.** DLP scan on all inputs before LLM processing. DLP scan on all outputs before delivery. DLP scan on all inter-agent payloads. Once data enters the LLM, it cannot be unlearned.

---

## 11. MULTI-AGENT BEHAVIORAL CONTROL

### 11.1 LangGraph State Machine Architecture

- [ ] **Nodes (agents/tools) connected by edges with conditional logic.** Supports cycles, branching, explicit error handling. Per-node error handling: retry/fallback/human escalation. Global token budget enforcer. Define all graph edges with explicit conditions.

### 11.2 Checkpointing for Time-Travel Debugging

- [ ] **Use PostgresSaver in production (not SQLite).** Enable checkpoint-based state replay, rolling back to prior states. Per-node timeouts and automated retries. Log checkpoint IDs for every execution.

### 11.3 Tripwire Guardrail Pattern (OpenAI SDK, Adapted)

- [ ] **Three guardrail types:** Input (on first agent), Output (on last agent), Tool (before/after execution).
- [ ] **Tripwire behavior:** When triggered, immediately raises exception, halting execution.
- [ ] Any CRITICAL security finding = immediate pipeline halt.

### 11.4 Sub-Agent Context Isolation

- [ ] **Each sub-agent handles focused tasks with a clean context window.** Sub-agents return condensed summaries (1,000-2,000 tokens) to the coordinator. The coordinator maintains a high-level view without detailed noise. Verification agents receive only the code under review, not the full conversation. The orchestrator never receives raw tool outputs from sub-agents.

### 11.5 Token Budget Awareness

- [ ] **Multi-agent systems consume up to 15x more tokens than standard chat.** Budget 15x single-agent token cost. Track per-agent and per-wave token usage. Set per-agent token limits. Use token usage as a health metric -- sudden spikes indicate drift or loops.

### 11.6 Observability as Behavioral Control

- [ ] **Trace every step and handoff:** prompts, outputs, tools, tokens, costs, latencies.
- [ ] Sample 10% of runs for manual quality review.
- [ ] Set alerting thresholds for: cost per run, latency per agent, output schema violations.
- [ ] Store traces for at least 30 days.

### 11.7 Framework Selection

- [ ] LangGraph for deterministic flow, CrewAI for rapid prototyping, AutoGen/AG2 for enterprise async, OpenAI Agents SDK for strict guardrails, Pydantic AI for type safety. Document why the framework was chosen and trade-offs accepted.

---

## 12. AGENT HANDOFF AND SHUTDOWN

### 12.1 Core Insight

- [ ] **"Reliability lives and dies in the handoffs."** Most "agent failures" are actually orchestration and context-transfer issues. When an agent fails, investigate the handoff first. Log every handoff payload. Validate handoff payloads against schemas before sending. Track handoff failure rates separately from agent failure rates.

### 12.2 Four Handoff Patterns

| Pattern | When to Use |
|---------|-------------|
| Structured Data Transfer (JSON Schema) | Default for all handoffs |
| Conversation History Transfer | Continuity-critical only |
| Summary Transfer | Long pipelines, token-efficient |
| File-Based Transfer | Cross-session state |

### 12.3 Anti-Patterns

- [ ] **Never use free-text handoffs.** Free text is ambiguous, lossy, and unparseable. Implicit state is the leading cause of handoff failures. Every handoff must use a defined schema. Anything not explicitly serialized is a bug.
- [ ] **Never leave tool calls unpaired.** LLMs expect tool calls paired with responses. Handoff messages must include both the AIMessage containing the tool call and a ToolMessage acknowledging the handoff.

### 12.4 Handoff Best Practices

- [ ] **Version payloads with semver.** Include `schemaVersion` in all handoff payloads. Bump minor for additive changes, major for breaking changes. Receiving agent validates version compatibility.
- [ ] **Validate strictly with repair loop.** Pydantic validation on every handoff receive. On failure: log, repair prompt, retry up to 3 times, then escalate to human.
- [ ] **Bind tool permissions to roles.** Define a tool whitelist per agent role. Block tool calls not in the whitelist. Audit for agents with >10 tools.
- [ ] **Trace every handoff.** Log: handoff payload, sending agent, receiving agent, timestamp, token count.
- [ ] **LangGraph Command.PARENT for parent handoff.** Must include both AIMessage and ToolMessage. Define error nodes routing to human after 3 retries. Enable checkpointing on all handoff nodes.

---

## 13. PRODUCTION PATTERNS AND CASE STUDIES

### 13.1 Trail of Bits -- OS-Level Sandboxing

- [ ] Runs Claude Code in `--dangerously-skip-permissions` mode with OS-level sandboxing (Seatbelt on macOS, bubblewrap on Linux). Security model shifts from restricting the agent to sandboxing the environment. Reference: `trailofbits/claude-code-config`.

### 13.2 Security Reviewer Pattern (Anthropic Docs)

- [ ] `model: opus`, `tools: Read, Grep, Glob, Bash`. Reviews for: injection vulnerabilities, auth flaws, secrets in code, insecure data handling. Must provide specific line references and suggested fixes. Read-only tools prevent modification.

### 13.3 Database Reader -- Hook-Enforced Read-Only

- [ ] Has `tools: Bash` only, with PreToolUse hook validating queries are read-only. Dual enforcement: prompt tells agent it's read-only (Tier 1) + hook blocks write operations deterministically (Tier 3). The prompt-level instruction helps Claude explain denials gracefully.

### 13.4 VoltAgent -- Single Responsibility

- [ ] 100+ specialized subagents, each with single responsibility, clear description, minimal tool set. Reference: `VoltAgent/awesome-claude-code-subagents`.

### 13.5 Adaline Labs -- Plan Gate Before Implementation

- [ ] (1) Plan gate before implementation. (2) Subagent review after implementation. (3) Multi-model review for critical changes. (4) PR opened only when all checks pass.

### 13.6 Captain Hook -- Intent-Based Policy Enforcement

- [ ] Evaluates the agent's intent at the exact moment it decides to act. Deterministic, not advisory. Reference: `securityreview.ai/blog/captain-hook-ai-agent-policy-enforcement-for-claude`.

### 13.7 Codacy -- 5-Minute Deterministic Guardrails

- [ ] Setup takes 5 minutes. PreToolUse hooks for security scanning, PostToolUse for validation. Minimum baseline for every project.

### 13.8 Anti-Drift for Verification Agents (4 Techniques)

- [ ] (1) **Template constraints:** Every verification agent has an exact report template.
- [ ] (2) **Checklist in agent body:** Explicit items to check, not vague "review for quality."
- [ ] (3) **Escalation clause:** "If you cannot complete a check, report it as INCONCLUSIVE rather than skipping it."
- [ ] (4) **Self-verification:** "Before finalizing your report, verify that every section is filled and every file mentioned exists."

---

## 14. SIOPV-SPECIFIC RECOMMENDATIONS

### 14.1 Agent Tool Assignments

| Agent | Tools | Enforcement |
|-------|-------|-------------|
| security-auditor | Read-only + Bash | PreToolUse hook blocks write commands |
| code-implementer | All tools | PostToolUse runs ruff/mypy after every edit |
| test-generator | All tools | PostToolUse runs pytest after test file creation |
| hallucination-detector | Read-only only | NO Bash |
| best-practices-enforcer | Read-only + Bash | For running linters |

### 14.2 Hook Enforcement Configuration

- [ ] PreToolUse matcher "Bash" -> `.claude/hooks/block-dangerous-commands.sh`
- [ ] PostToolUse matcher "Edit|Write" -> `.claude/hooks/run-linter.sh`
- [ ] Add to `.claude/settings.json` under `hooks` key.

### 14.3 Path-Targeted Rules for Domains

- [ ] `security.md` targeted to `src/siopv/infrastructure/**`
- [ ] `orchestration.md` targeted to `src/siopv/application/orchestration/**`
- [ ] Additional domain-specific rules files as needed.

### 14.4 Pipeline State File

- [ ] Have each graph node update a persistent `pipeline_state.md` with current progress, remaining steps, accumulated findings. Serves as both external memory and attention anchor for the orchestrator.

### 14.5 Node-Level Context Isolation in LangGraph

- [ ] Each node receives only the TypedDict fields relevant to its function. Restrict to only the fields it reads/writes. Flag nodes accessing >5 state fields for review.

### 14.6 PostgresSaver for Production Checkpointing

- [ ] Migrate from SQLite to PostgresSaver. Enable time-travel debugging on classify_node and enrich_node.

### 14.7 Three-Layer Guardrails Mapped to Hexagonal Architecture

- [ ] **Input Port Guardrails:** PII/Presidio, Pydantic validation, rate limiting.
- [ ] **Processing Guardrails:** Tool state machine, token budget, timeout/retry, LLM judge on classify_node.
- [ ] **Output Port Guardrails:** Pydantic validation, DLP scan, hallucination detection, schema version enforcement.

### 14.8 Anti-Drift for classify_node (5 Mitigations)

- [ ] (1) Runtime reinforcement -- append classification constraints at end of every LLM prompt.
- [ ] (2) Structured output -- Pydantic models with strict JSON Schema.
- [ ] (3) Behavioral anchoring -- 3-5 canonical classification examples.
- [ ] (4) Output validation -- confidence scores within expected ranges.
- [ ] (5) LLM judge -- lightweight secondary model for consistency verification.

### 14.9 Compaction-Safe Architecture for Multi-Session Pipeline

- [ ] Pin critical constraints in system prompts.
- [ ] Use COMPACT-SAFE markers on all workflow files.
- [ ] External state files per phase.
- [ ] Instruction redundancy -- every critical rule in system prompt, node-level prompt, AND external config.

### 14.10 Verification Pipeline Guardrails

- [ ] Pydantic-validated report schemas for all 5 agents.
- [ ] Tripwire pattern -- CRITICAL finding = immediate halt.
- [ ] Wave timing: Wave 1 max 7 min, Wave 2 max 5 min.
- [ ] Clean context per verification agent.
- [ ] Drift detection -- compare against historical baselines.

### 14.11 Deterministic Behavior Where Possible

- [ ] Deterministic graph flow for non-LLM logic.
- [ ] Reproducibility logging: model ID, temperature, seed, full prompts for every LLM call.
- [ ] Constrained decoding for all LLM calls.
- [ ] Note: true determinism is impossible (temperature=0 is not fully deterministic due to floating-point arithmetic and MoE routing).

### 14.12 Inter-Phase Handoff Protocol

- [ ] `projects/siopv.json` as canonical state transfer.
- [ ] Pydantic models for inter-phase state.
- [ ] Validation on resume -- validate all accumulated state against schemas.
- [ ] Audit trail -- log inputs, outputs, verification results per phase transition.

---

## 15. SUMMARY AND QUICK-REFERENCE TABLES

### 15.1 Seven Key Takeaways (Summary Rules)

1. **Prompts are requests, hooks are laws** -- for anything that MUST happen, use hooks/tool restrictions.
2. **150 instructions is the ceiling** -- prune ruthlessly.
3. **Lost-in-the-middle is real** -- put critical rules at start and end.
4. **Tool restrictions are the most reliable guardrail** -- deterministic prevention.
5. **Per-step constraints beat uniform freedom levels** -- match constraint type to step type.
6. **Fresh context beats accumulated context** -- use /clear between tasks.
7. **Verification is the highest-leverage practice** -- give Claude ways to check its own work.
8. **Personas leak beyond specification** -- explicitly state what agents should NOT do.

### 15.2 Guardrail Tier Decision Matrix

| Requirement | Tier 1 (Prompt) | Tier 2 (Tool Restriction) | Tier 3 (Hook) |
|-------------|-----------------|---------------------------|----------------|
| Guidance/preferences | Primary | -- | -- |
| Code style | Primary | -- | PostToolUse linter |
| Read-only enforcement | Supporting | Primary | PreToolUse blocking |
| Dangerous command blocking | -- | -- | Primary (PreToolUse) |
| Output format | Primary | -- | PostToolUse validation |
| Security-critical rules | Supporting | Where applicable | Primary |

### 15.3 Agent Body Structure Checklist

- [ ] Identity section (role + domain)
- [ ] Mandate section (ONE task, specific deliverable)
- [ ] Workflow section (numbered steps with constraint types)
- [ ] Boundaries section (NEVER statements, 3-5 DO NOT items, escalation clause)
- [ ] Output Format section (exact template)
- [ ] Verification section (pre-completion checklist, self-verification step)
- [ ] Under 200 lines total
- [ ] Critical rules at TOP and repeated at BOTTOM
- [ ] 3-5 canonical examples included

### 15.4 Size Limits

| Component | Maximum | Notes |
|-----------|---------|-------|
| Agent body | 200 lines | Front-load critical rules |
| CLAUDE.md | 300 lines | Shorter is better |
| Total instructions (all contexts) | 150 | Beyond this, compliance drops for ALL rules |
| Critical rules in prompts | 20 | The rest go to hooks/tool restrictions |
| Sub-agent return to orchestrator | 1,000-2,000 tokens | Condensed summaries only |

### 15.5 Source Checkpoint Counts

| Source File | Categories | Checkpoints |
|-------------|-----------|-------------|
| 003 (Claude Code Report) | 8 | 58 |
| 004 (LLM Behavioral Report) | 10 | 74 |
| **This merged record** | **15** | **132 (deduplicated)** |

---

**END OF RECORD**
