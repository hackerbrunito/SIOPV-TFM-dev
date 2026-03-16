# Definitive Dual-Purpose Technical Record: Comprehensive Checklist and Technical Reference for Agent Design

**Document type:** Audit record + implementation checklist + technical reference
**Date of research:** 2026-03-09
**Project:** SIOPV (Sistema Inteligente de Orquestacion y Priorizacion de Vulnerabilidades) -- Master's thesis
**Author:** Bruno (principal investigator)
**Created:** 2026-03-09
**Sources:** `003_checkpoints-extracted-from-claude-code-report.md` (58 checkpoints) and `004_checkpoints-extracted-from-llm-behavioral-report.md` (74 checkpoints)
**Purpose:** Single source of truth that serves as both a complete implementation checklist and a technical reference for building well-structured, high-quality Claude Code agent projects. Designed to survive any number of context compactions. The architecture must be auditable by thesis examiners, reproducible by the development team, and grounded in specific empirical findings rather than intuition.

---

## TABLE OF CONTENTS

**Part I: Research Methodology and Provenance**
1. [Research Methodology](#1-research-methodology)

**Part II: Technical Reference (Knowledge Base)**
2. [Agent Definition Structure](#2-agent-definition-structure)
3. [Persona and Behavioral Design](#3-persona-and-behavioral-design)
4. [Instruction-Following Techniques](#4-instruction-following-techniques)
5. [Guardrails and Enforcement (Three-Tier Framework)](#5-guardrails-and-enforcement)
6. [Hooks Configuration](#6-hooks-configuration)
7. [Rules Files and Instruction Management](#7-rules-files-and-instruction-management)
8. [Anti-Improvisation and Anti-Drift Techniques](#8-anti-improvisation-and-anti-drift-techniques)
9. [Context Positioning and Attention Management](#9-context-positioning-and-attention-management)
10. [Context Rot, Compaction, and Memory Survival](#10-context-rot-compaction-and-memory-survival)
11. [Structured Output Enforcement](#11-structured-output-enforcement)
12. [Multi-Agent Behavioral Control](#12-multi-agent-behavioral-control)
13. [Agent Handoff and Shutdown](#13-agent-handoff-and-shutdown)
14. [Production Patterns and Case Studies](#14-production-patterns-and-case-studies)
15. [SIOPV-Specific Recommendations](#15-siopv-specific-recommendations)

**Part III: Design Decisions**
16. [Design Decisions for SIOPV (DD-001 through DD-015)](#16-design-decisions-for-siopv)

**Part IV: Architecture and Templates**
17. [Stage Architecture](#17-stage-architecture)
18. [Reusable Team Template](#18-reusable-team-template)
19. [Agent Persona Templates](#19-agent-persona-templates)

**Part V: Implementation and Quick Reference**
20. [Implementation Checklist (32 Items, 8 Phases)](#20-implementation-checklist)
21. [Summary and Quick-Reference Tables](#21-summary-and-quick-reference-tables)

---

## 1. RESEARCH METHODOLOGY

### What Was Researched

Two complementary domains were investigated to design a production-grade agent architecture for SIOPV:

1. **Claude Code Agent Configuration** -- The internal mechanics of how Claude Code defines, constrains, and orchestrates subagents via `.claude/agents/` files, YAML frontmatter, hooks, rules files, tool restrictions, and context management. This covers the specific platform being used to build and operate SIOPV agents.

2. **LLM Behavioral Control Science** -- Cross-platform, vendor-agnostic research on instruction-following techniques, persona design, guardrail architectures, context rot, anti-drift techniques, compaction-safe instruction design, multi-agent orchestration patterns, structured output enforcement, and agent handoff protocols.

### Sources Consulted

**Report 001 (Claude Code Agent Persona):**
- Anthropic official Claude Code documentation (agent definitions, hooks, rules, skills)
- Anthropic persona research papers (persona leakage, direct assignment vs. imagination framing)
- Trail of Bits `claude-code-config` repository (OS-level sandboxing + hooks)
- VoltAgent `awesome-claude-code-subagents` repository (100+ single-responsibility agent patterns)
- Adaline Labs production patterns (plan gate before implementation)
- Captain Hook (`securityreview.ai`) -- intent-based policy enforcement
- Codacy deterministic guardrail patterns
- Community research on CLAUDE.md token budgets and rule effectiveness

**Report 002 (LLM Behavioral Control & Guardrails):**
- Anthropic prompt engineering documentation (Section 1.1-1.5)
- Manus AI -- file-system-as-memory, controlled variation, tool availability state machines (Sections 3.4, 4.2.1-4.2.3, 8.4)
- arXiv 2601.04170 (Jan 2026) -- Agent Stability Index, 12-dimension drift analysis (Section 4.1)
- LangGraph documentation -- state machine architecture, checkpointing, Command.PARENT (Section 5.2, 9.5)
- OpenAI Agents SDK -- tripwire guardrail pattern, three-layer guardrails (Section 5.3)
- Pydantic AI -- structured output enforcement, durable execution (Section 6.3)
- Skywork AI -- validation-repair loop pattern (Section 6.4)
- NVIDIA NeMo Guardrails + Colang (Section 7.1)
- Guardrails AI -- output validation hub (Section 7.2)
- Meta Llama Guard -- safety classification (Section 7.4)
- LLMLingua -- prompt compression techniques (Section 8.1)
- Empirical studies on lost-in-the-middle effect, context rot, and prompt repetition

### Purpose

Design a production-grade, research-backed agent architecture for the SIOPV master's thesis project. The architecture must be auditable by thesis examiners, reproducible by the development team, and grounded in specific empirical findings rather than intuition.

---

## 2. AGENT DEFINITION STRUCTURE

### 2.1 File Format and Location

- [ ] **Markdown + YAML frontmatter format.** Agent definitions are `.md` files with YAML frontmatter in `.claude/agents/`. Frontmatter = metadata/constraints. Markdown body = system prompt. Subagents receive ONLY this system prompt plus basic environment details (working directory), NOT the full Claude Code system prompt. The body IS the entire behavioral context.
- [ ] **File location priority order.** (1) `--agents` CLI flag = session-only, priority 1. (2) `.claude/agents/` = project-scoped, priority 2. (3) `~/.claude/agents/` = user-scoped, priority 3. (4) Plugin `agents/` dir = priority 4.
- [ ] **CLI JSON agents for ephemeral sessions.** Use `--agents` CLI flag with JSON for session-only agents. `prompt` field in JSON is equivalent to markdown body. Example: `claude --agents '{"name": {"description": "...", "prompt": "...", "tools": [...], "model": "sonnet"}}'`

### 2.2 Frontmatter Fields

- [ ] **Four-field minimum enforced.** Every agent must have at minimum: `name`, `description`, `tools`, and body content. Add `model`, `memory`, `hooks`, `maxTurns` only when needed. These four fields establish identity, delegation routing, capability boundaries, and behavioral instructions.
- [ ] **All 14 frontmatter fields understood and explicitly decided.** Full field inventory: `name` (required, lowercase+hyphens), `description` (required, used for auto-delegation), `tools` (allowlist), `disallowedTools` (denylist), `model` (sonnet/opus/haiku/inherit), `permissionMode` (default/acceptEdits/dontAsk/bypassPermissions/plan), `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory` (user/project/local), `background`, `isolation` (worktree). For each agent, explicitly decide the value of every field (even if the decision is "omit/use default").

### 2.3 Description Field for Delegation

- [ ] **Description field drives delegation routing.** The `description` field is used by Claude for auto-delegation decisions -- it determines WHEN the agent gets invoked. Write descriptions that specify the exact trigger conditions: "Expert code review specialist. Use immediately after writing or modifying code." NOT "Reviews code."

### 2.4 Tool Restriction Syntax

- [ ] **Allowlist and denylist syntax validated.** Allowlist: `tools: Read, Grep, Glob, Bash`. Denylist: `disallowedTools: Write, Edit`. Restrict subagent spawning: `tools: Agent(worker, researcher), Read, Bash`. Allow any subagent: `tools: Agent, Read, Bash`. Syntax errors in tool restrictions silently fail, leaving the agent with full tool access. Test by checking if the agent can use tools it shouldn't have.

### 2.5 Agent Memory

- [ ] **Memory configured for institutional learning.** Set `memory: project` (or `user`/`local`) to give agents persistent cross-session learning. Agent gets a `MEMORY.md` file (first 200 lines injected at startup) with Read/Write/Edit auto-enabled. Memory directory: `.claude/agent-memory/<name>/` (project scope). Agent must curate MEMORY.md if it exceeds 200 lines. Enable for agents that benefit from accumulated knowledge (code-reviewer, security-auditor).

---

## 3. PERSONA AND BEHAVIORAL DESIGN

### 3.1 Core Principle

- [ ] **System prompt IS the persona -- single surface.** The body of the agent definition IS the system prompt. The subagent receives ONLY this plus environment details -- nothing from the parent conversation. Every behavioral instruction must be self-contained in the agent body. Write each agent body as if it were the only instructions the agent will ever see.

### 3.2 Proven Persona Patterns

- [ ] **Pattern A -- Role + Checklist.** (1) "You are a [role]." (2) "When invoked: 1. 2. 3." (3) "Checklist: - item - item" (4) "Provide feedback organized by: Critical / Warnings / Suggestions." The checklist gives explicit verification criteria rather than vague "review for quality." (Anthropic docs pattern)
- [ ] **Pattern B -- Domain Expert with Workflow.** (1) "You are an expert [domain] specializing in [specific area]." (2) Numbered steps: capture, identify, isolate, implement, verify. (3) "Focus on [root principle], not [surface approach]." The sequential workflow prevents the agent from jumping to conclusions. (Anthropic docs pattern)
- [ ] **Pattern C -- Behavioral Boundaries with Scenario Handling.** 3-5 interaction rules, then explicit scenario-response mappings: "If [situation], then [exact response]." Pre-scripted scenario responses prevent improvisation in sensitive situations. (Anthropic API docs pattern)
- [ ] **Pattern D -- Cognitive Personas (SuperClaude).** Personas are `.md` files containing domain-specific expertise, behavioral patterns, and problem-solving approaches. Invocable via `@agent-security` syntax. 16 specialist agents that can delegate to each other.

### 3.3 Four Elements of Effective Persona (Anthropic Official Guidance)

- [ ] **Role set in system prompt.** Even a single sentence makes a difference.
- [ ] **Detailed personality info.** Background, traits, quirks help the model generalize.
- [ ] **Scenarios prepared.** List common situations and expected responses.
- [ ] **Constrained with examples.** Show desired output format -- this "trains" understanding better than abstract instructions.

### 3.4 Direct Persona Assignment

- [ ] **"You are an X" over "Imagine you are...".** Direct persona assignment outperforms imagination framing empirically (LearnPrompting, 2025; IF-03, CP-PBD-01). Audit all agent prompts. Replace any "Imagine you are...", "Pretend to be...", "Act as if you were..." with direct "You are..." statements.

### 3.5 Persona Scope and Limitations

- [ ] **Persona controls style, NOT accuracy.** Vanilla prompting and persona prompting perform very similarly on accuracy tasks (PR-01). Persona effectively controls: style, tone, output format, domain vocabulary usage, behavioral constraints (refusals). It does NOT reliably control: factual accuracy, deep reasoning quality, or knowledge beyond training data. Always pair persona with RAG/tool access for knowledge, structured output for format, and validation for correctness.
- [ ] **Anti-pattern: persona trait leakage.** When Claude adopts a persona, it infers personality traits that drive OTHER behaviors beyond those specified (CP-ANT-09, PR-05). A "friendly helper" persona may become inappropriately casual in security audits. A "security auditor" may start suggesting fixes unless explicitly told "DO NOT fix code." Mitigation: Be explicit about what the persona should NOT do. Add explicit NOT instructions for every behavioral dimension that matters. Personas without explicit constraints leak inferred behaviors. (Anthropic Persona Selection Model, 2026)

### 3.6 CrewAI Role-Goal-Backstory Pattern

- [ ] **Three mandatory agent attributes.** Role (professional identity -- be specific: "Senior Python Security Auditor" not "Developer"), Goal (single, measurable objective per agent), Backstory (narrative context establishing WHY this agent exists). Specialists outperform generalists.
- [ ] **80/20 Rule: tasks over agent definitions.** 80% of effort into designing tasks, only 20% into defining agents. Task design drives output quality more than agent persona refinement.
- [ ] **Specialists over generalists.** If two agents share >30% of their responsibilities, merge or re-split them. No agent should handle more than one domain.

### 3.7 Constraint-Based Personas

- [ ] **MUST NOT rules alongside MUST rules.** Every agent definition must include a "MUST NOT" section listing at least 3 prohibited behaviors (e.g., "MUST NOT modify files outside the target directory", "MUST NOT make network calls", "MUST NOT approve its own output"). Negative constraints prevent scope creep.

### 3.8 Recommended Agent Body Template (Six Sections)

- [ ] **Section 1 -- Identity:** "You are a [ROLE] specializing in [DOMAIN]."
- [ ] **Section 2 -- Mandate:** "Your ONE task: [specific deliverable]."
- [ ] **Section 3 -- Workflow:** Numbered steps with per-step constraint types (Procedural/Criteria/Template/Guardrail).
- [ ] **Section 4 -- Boundaries:** NEVER statements + edge case handling.
- [ ] **Section 5 -- Output Format:** Exact template structure.
- [ ] **Section 6 -- Verification:** Pre-completion checklist.
- [ ] Reject agent definitions missing any section.

---

## 4. INSTRUCTION-FOLLOWING TECHNIQUES

### 4.1 System Prompt Design

- [ ] **Right altitude balance.** System prompts must occupy a "Goldilocks zone" -- specific enough to guide behavior, flexible enough to provide strong heuristics. No brittle if-else logic (no chains with >3 branches). No vague guidance that assumes shared context. Every constraint has a concrete example or heuristic.
- [ ] **Structural organization with XML/Markdown sections.** Use distinct sections with XML tags or Markdown headers to organize system prompts. Every system prompt and agent briefing must separate: background, instructions, tool guidance, output format, constraints.
- [ ] **Minimal viable prompt approach.** Start with minimal instructions using the best model, then add clarity based on observed failure modes rather than anticipating all edge cases. For new agents, start with a 5-10 line prompt. Log failure modes. Add constraints only for observed failures. Track prompt evolution in version control.

### 4.2 Attention and Repetition

- [ ] **Prompt repetition for attention boost.** Repeating the input prompt improves performance for all major models without increasing generated tokens or latency. Accuracy improvements of up to 67-76% on non-reasoning tasks. Repeat critical instructions at the end of the context window. For non-negotiable rules, include them both in the system prompt AND appended after the final user message. (Leviathan et al., Google Research, arXiv 2512.14982, Dec 2025; CP-CTX-05, IF-08)
- [ ] **Primacy and recency positioning.** Instructions at the beginning and end of context receive the most attention (U-shaped attention curve). Performance drops >30% when key information sits in the middle. Place non-negotiable constraints at the very beginning. Repeat critical rules at the very end. Never bury important constraints in the middle of long contexts. Audit long prompts (>2000 tokens) for critical rules buried in the middle.
- [ ] **Emphasis markers (`IMPORTANT`, `YOU MUST`, `CRITICAL`, `NEVER`)** demonstrably improve adherence, but overuse dilutes the effect (CP-CTX-06). Add to the 20 most critical instructions only.

### 4.3 Instructional Segment Embedding (ISE)

- [ ] **Token role classification.** Categorize instruction tokens by role: system instruction = 0, user prompt = 1, data input = 2. For API-based models, use the native system/user/assistant role separation rigorously -- never mix instruction types within a single role message. (ICLR 2025)

### 4.4 Few-Shot Examples

- [ ] **Diverse canonical examples.** For each agent, include 3-5 canonical examples covering the range of expected inputs/outputs. Prefer diversity over edge-case coverage. Review examples quarterly for staleness. Examples shape behavior more reliably than verbose instructions.

### 4.5 Behavioral Templates

- [ ] **Three-template system for fine-grained control.** Use `system_template`, `prompt_template`, `response_template`. System template sets identity, prompt template structures input, response template constrains output format. (PLoP 2024)

### 4.6 Reasoning Mode

- [ ] **Enable reasoning for planning agents.** Enable `reasoning: true` for agents needing planning and reflection before action: orchestrators, code reviewers, security auditors, multi-step decision makers. Disable for simple extraction or formatting agents.

---

## 5. GUARDRAILS AND ENFORCEMENT

### 5.1 The Fundamental Insight

- [ ] **Prompts are requests, hooks are laws.** Rules in prompts are probabilistic requests (Claude may ignore them, ~80% compliance at best). Hooks in code are deterministic laws (always execute, cannot be overridden, ~100% compliance). Claude can read and recite instructions without following them. For anything that MUST happen, implement it as a hook or tool restriction. For preferences and guidance, use prompts. Never rely on prompts alone for safety-critical rules. (CP-GAE-01, CP-PRD-09)

### 5.2 The 150-Instruction Ceiling

- [ ] **Instruction compliance decreases with volume.** Frontier models max out at ~150-200 instructions. Beyond this threshold, more rules correlate with WORSE overall compliance across ALL rules. Keep the 20 most critical rules in prompts. Handle the rest via hooks, tool restrictions, or remove them entirely. Count total instructions across all loaded contexts (CLAUDE.md + rules + agent body + skills). Per agent: maximum 20 core rules in the body, maximum 200 lines total (CP-CTX-04). CLAUDE.md should be under 300 lines (CP-CTX-10). (Jaroslawicz et al., 2025; CP-GAE-02, CP-RUL-06)
- [ ] **Pruning heuristic:** Remove any rule that does not change behavior when removed. If removing a rule causes no observable difference, it wastes attention budget (CP-CTX-09).

### 5.3 Three-Tier Guardrails Framework

- [ ] **Tier 1: Prompt-based (probabilistic, ~80% compliance at best, degrades with volume).** For guidance, preferences, soft constraints. Accept ~80% as the ceiling. Monitor and escalate frequently-violated rules.
- [ ] **Tier 2: Tool restrictions (deterministic, 100% compliance).** Tools simply don't exist for the agent. Remove tools the agent doesn't need. An agent without the Write tool cannot create files regardless of how persuasive its reasoning is. Most reliable anti-improvisation mechanism.
- [ ] **Tier 3: Hooks (deterministic, 100% compliance).** Code runs regardless of Claude's reasoning. PreToolUse hooks can block actions. PostToolUse hooks react after actions.
- [ ] **Layer all three tiers simultaneously.** For each agent, implement all three. If the prompt fails (20% of the time), tool restrictions catch the action. If a new tool somehow bypasses restrictions, hooks catch it. Create a matrix: agent x tier x what's implemented.

### 5.4 Guardrails Ladder (Adaline Labs)

- [ ] **Three escalation levels.** Tier 1 = Read-only and analysis (inspect, explain, plan). Tier 2 = Controlled changes in scoped directories (edit only within approved paths). Tier 3 = PR-ready changes with enforced checks (produce PR candidates only after automated checks pass). Assign each agent to a tier.

### 5.5 Per-Step Constraint Types (4 Types)

- [ ] **Procedural (HOW):** Sequential steps, divergence acceptable.
- [ ] **Criteria (WHAT):** Quality judgment, replace "how" with explicit standards.
- [ ] **Template:** Fixed output structure, flexible content.
- [ ] **Guardrail:** Boundaries by prohibition, what must NEVER happen.
- [ ] For each step in an agent's workflow, assign one of the four constraint types and document it alongside the step. (CP-ANT-01)

### 5.6 Three-Layer Guardrail Architecture (Production)

- [ ] **Input Layer:** Injection detection, format validation, PII detection (Presidio), rate limits, malicious content filtering. (GF-03, SP-04)
- [ ] **Interaction Layer:** Tool restriction, autonomous decision cap (max 20 tool calls per invocation), state-machine tool availability, token budget per interaction.
- [ ] **Output Layer:** Structured validation (Pydantic), relevancy checks, hallucination detection, content safety, schema compliance.
- [ ] Every agent must have at least one guardrail per layer. Single-layer guardrails leave gaps. Each layer catches different failure modes.

### 5.7 Deterministic vs Probabilistic Control

- [ ] **For every critical rule currently in CLAUDE.md or rules files, ask:** "What happens if Claude ignores this?" If the answer is unacceptable, implement a deterministic equivalent (hook or tool restriction). Example: "Don't edit .env files" in CLAUDE.md (probabilistic, may be ignored) vs. PreToolUse hook that exits with code 2 when .env is targeted (deterministic, always blocks).

---

## 6. HOOKS CONFIGURATION

### 6.1 Hook Events Inventory (March 2026)

- [ ] **16 hook events known and mapped.** `SessionStart` (startup/resume/clear/compact), `UserPromptSubmit`, `PreToolUse` (tool name matcher, CAN BLOCK), `PermissionRequest`, `PostToolUse`, `PostToolUseFailure`, `Notification`, `SubagentStart` (agent type), `SubagentStop` (agent type), `Stop`, `TeammateIdle`, `TaskCompleted`, `InstructionsLoaded`, `ConfigChange`, `PreCompact` (manual/auto), `SessionEnd`, `WorktreeCreate`/`WorktreeRemove`.

### 6.2 PreToolUse -- The Only Blocking Hook

- [ ] **PreToolUse is the ONLY hook that can block actions.** Two blocking mechanisms: (1) Exit code 2 = block. (2) JSON output with `permissionDecision: "deny"`. Every safety-critical rule that must prevent an action needs a PreToolUse hook. (CP-HCF-02)
- [ ] **Exit code blocking pattern.** `INPUT=$(cat)` -> extract via `jq` -> pattern match -> `exit 2` to block, `exit 0` to allow. Error message via stderr (`>&2`).
- [ ] **JSON output blocking pattern.** `jq -n '{ hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: "..." } }'`. Provides structured reason Claude can use to explain the denial.
- [ ] **PreToolUse can modify tool inputs (v2.0.10+).** Can rewrite tool parameters before execution. Use cases: add dry-run flags, redact secrets from commands.

### 6.3 Three Handler Types

- [ ] **`command`:** Shell script, deterministic, best for security rules (block patterns, validate SQL). (CP-HCF-03)
- [ ] **`prompt`:** LLM judgment call, for nuanced/context-dependent decisions.
- [ ] **`agent`:** Full codebase state verification, most expensive but most capable.

### 6.4 Hook Configuration Locations (Priority Order)

- [ ] (1) `~/.claude/settings.json` -- all projects.
- [ ] (2) `.claude/settings.json` -- single project, committable.
- [ ] (3) `.claude/settings.local.json` -- single project, gitignored.
- [ ] (4) Managed policy settings -- organization-wide.
- [ ] (5) Plugin `hooks/hooks.json` -- when plugin enabled.
- [ ] (6) Agent frontmatter -- while agent is active.
- [ ] Place hooks at the narrowest applicable scope.

### 6.5 Hook Configuration in Agent Frontmatter

- [ ] **Agent-scoped hooks only run when that specific agent is active.** Add hooks directly to agent frontmatter YAML. Matcher supports pipe-separated tool names: `"Edit|Write"`. Each hook entry needs `type: command` and `command: "./path/to/script.sh"`.

### 6.6 What Hooks CAN Enforce (8 Capabilities)

- [ ] (1) Block dangerous commands (PreToolUse + exit 2).
- [ ] (2) Validate SQL queries (block writes, allow SELECT).
- [ ] (3) Protect files (block Write/Edit to specific paths).
- [ ] (4) Auto-format (PostToolUse runs linter after every edit).
- [ ] (5) Run tests (PostToolUse after changes).
- [ ] (6) Modify tool inputs (PreToolUse v2.0.10+, rewrite parameters: add dry-run flags, redact secrets).
- [ ] (7) Enforce conventions (PostToolUse checks naming/structure).
- [ ] (8) Setup/teardown (SubagentStart/SubagentStop for resource management).

### 6.7 What Hooks CANNOT Enforce (5 Limitations)

- [ ] (1) Reasoning quality -- hooks see actions, not thought processes. (CP-HCF-09)
- [ ] (2) Instruction recall -- cannot force Claude to remember something.
- [ ] (3) Planning decisions -- cannot control WHICH tool Claude decides to use.
- [ ] (4) Output quality -- can validate format but not semantic correctness.
- [ ] (5) Cross-turn consistency -- each hook invocation is stateless.
- [ ] For these guarantees, use complementary approaches (verification agents, multi-model review).

---

## 7. RULES FILES AND INSTRUCTION MANAGEMENT

### 7.1 Directory Structure

- [ ] **Rules stored in `.claude/rules/` as standalone Markdown files** with optional YAML frontmatter. Files are discovered recursively, supporting subdirectories for organization. Example: `.claude/rules/code-style.md`, `.claude/rules/security.md`, `.claude/rules/frontend/react.md`.

### 7.2 Path-Targeted Rules

- [ ] **YAML frontmatter `paths:` with glob patterns** to activate rules only when Claude works on matching files. Reduces instruction volume by loading rules only when relevant.
- [ ] **Known bug: path rules only trigger on READ.** Path-based rules only inject into context when Claude READS a matching file, NOT when writing/creating files. For rules that must apply during file creation, make them global (no paths) or implement via hooks.

### 7.3 Rules Loading Behavior

- [ ] Rules without `paths` = global (loaded at session start). Rules with `paths` = conditional (loaded on file match). `InstructionsLoaded` hook event fires when rules are loaded.

### 7.4 Four Instruction Mechanisms (Correct Placement)

| Mechanism | When Loaded | Scope | Use For |
|-----------|-------------|-------|---------|
| CLAUDE.md | Every session | Broad project | Build commands, project conventions |
| `.claude/rules/*.md` | Session start or file match | Modular scoped policies | Domain-specific rules |
| Skills | On demand | Domain knowledge/workflows | Detailed procedures, reference material |
| Agent body | When spawned | Agent-specific system prompt | Identity, mandate, workflow, boundaries |

- [ ] Classify every instruction by scope and timing. Place it in the correct mechanism. Audit for misplacements.

### 7.5 Five Rules for Effective Rule Writing

- [ ] (1) **Keep under 150 instructions total** across all loaded contexts.
- [ ] (2) **Be specific and measurable:** "Calculate ROI on a 3-year TCO basis" beats "Calculate ROI".
- [ ] (3) **Use emphasis markers:** `IMPORTANT`, `YOU MUST`, `CRITICAL` improve adherence. Use sparingly -- overuse dilutes the effect.
- [ ] (4) **Delete rules Claude already follows** -- if removing a rule doesn't change behavior, it wastes attention.
- [ ] (5) **Test rules by observation** -- watch whether behavior actually shifts.

### 7.6 What Rules CANNOT Do (5 Limitations)

- [ ] Rules are advisory, not enforced. Claude can read and recite rules without following them.
- [ ] Compliance degrades as total instruction volume increases.
- [ ] Long sessions cause rule "forgetting" due to context dilution.
- [ ] Rules may be deemed "not relevant" by the model and ignored (Claude's system prompt says instructions "may or may not be relevant").
- [ ] For any rule where non-compliance is unacceptable, implement a deterministic alternative.

---

## 8. ANTI-IMPROVISATION AND ANTI-DRIFT TECHNIQUES

### 8.1 Per-Step Constraint Design

- [ ] **Instead of one freedom level for an entire workflow, assign constraint type per step.** Data collection = Procedural. Analysis = Criteria. Reporting = Template. Safety checks = Guardrail. (CP-ANT-01)

### 8.2 Todo List Recitation for Context Anchoring

- [ ] **Agent constantly rewrites a todo list after each step:** `[x] Completed` / `[ ] Remaining` / `Current focus: [step]`. Pushes the global plan into the END of the context window (high-attention zone). Combats lost-in-the-middle degradation. (CP-ANT-02, AD-01)
- [ ] **todo.md pattern (Manus AI).** Every orchestrator and long-running agent must maintain a `todo.md` file. Update after every significant action. Read it back before making decisions. Include: current objective, completed steps, remaining steps, blockers. Serves as both external memory (survives compaction) AND attention anchor (anti-drift).

### 8.3 Fresh Context Windows

- [ ] **Use `/clear` between unrelated tasks.** A clean session with a better prompt almost always outperforms a long session with accumulated corrections. After two failed corrections in one session, start fresh. (CP-ANT-03)
- [ ] **Fresh context by default for sub-agents.** Each new agent starts with fresh conversation history. Include prior context only when explicitly needed. When including prior context, use summary transfer (not full history) unless continuity is critical. (AH-09)

### 8.4 Skills as Instruction Anchors

- [ ] **Skills provide step-by-step procedures that Claude follows rigidly.** Without a skill, Claude improvises. With a skill, it follows the defined sequence. For any workflow where Claude improvises despite instructions, convert the workflow into a skill with explicit step-by-step procedures.

### 8.5 Escalation Design

- [ ] **Build flexibility into constraints:** "If these constraints don't fit, propose alternatives with reasoning." Add an escalation clause to every agent's Boundaries section: "If you encounter a situation where these constraints are inappropriate, report it as ESCALATION with your reasoning rather than ignoring the constraint."

### 8.6 Verification Loops -- Highest-Leverage Practice

- [ ] **Give Claude ways to verify its own work:** tests to run, screenshots to compare, expected outputs to validate, linter results to check. Self-verification is the "single highest-leverage thing you can do" (Anthropic official best practices). Every agent body should include a Verification section with concrete checks. (CP-ANT-06)

### 8.7 Scoped Tool Access

- [ ] **Remove tools the agent doesn't need.** An agent with only Read, Grep, Glob literally CANNOT improvise by editing files. Default to read-only and add write tools only when the agent's mandate requires modification. Most reliable anti-improvisation mechanism because it is deterministic. (CP-ANT-07, CP-GAE-08)

### 8.8 maxTurns Limit

- [ ] **Set `maxTurns` in frontmatter to cap agentic turns.** Simple verification: 10-15 turns. Code implementation: 30-50 turns. Exploratory research: 20-30 turns. Adjust based on observation. (CP-ANT-08)

### 8.9 Explicit NOT Instructions

- [ ] **From Anthropic's persona research: Claude infers personality traits beyond what's specified.** Explicitly state what the agent should NOT do. For every agent, add 3-5 DO NOT statements. Example: "DO: Report vulnerabilities with severity ratings. DO NOT: Fix code, suggest implementations, or make edits. DO NOT: Speculate about business impact. DO NOT: Skip files because they 'look fine'." (CP-ANT-09)

### 8.10 External Memory for Behavioral Stability

- [ ] **Workflows using external memory show 21% higher behavioral stability** than those relying solely on conversation history. External memory provides "behavioral anchors" resistant to incremental drift. Implement external memory files for: architectural decisions, non-negotiable constraints, accumulated findings, phase state. Re-read these files at decision points. (AD-02)

### 8.11 Runtime Reinforcement via Instruction Re-injection

- [ ] **Callback pattern: intercept LLM requests, generate reinforcement block, append non-negotiable rules to end of prompt.** Rules at the end of context receive maximum attention (recency effect). Apply to every LLM call, not just the first. Timestamp each request for temporal awareness. (AD-03)

### 8.12 Controlled Variation to Break Pattern Lock-In

- [ ] **If context is full of similar past action-observation pairs, the model follows that pattern even when suboptimal.** Introduce structured variation: different serialization templates, alternate phrasing, minor formatting noise. Monitor for repetitive action sequences as a lock-in signal.

### 8.13 Episodic Memory Consolidation

- [ ] **After every 10-20 tool calls, consolidate:** summarize completed work, discard raw tool outputs. Always preserve: decisions made, errors encountered, constraints discovered. Keep last 5 full turns + summary of older turns.

### 8.14 Drift Detection via LLM Judges

- [ ] **Online detection using LLM judges or statistical tests.** For critical agents, implement a lightweight judge that: compares output against baseline expectations, flags deviations >2 standard deviations, triggers re-generation or human escalation.

### 8.15 Agent Stability Index (ASI) -- 12 Dimensions

- [ ] **Track at minimum:** response consistency, tool usage patterns, reasoning pathway stability, inter-agent agreement rates. Log per-agent per-session. (arXiv 2601.04170, Jan 2026)

### 8.16 Three Types of Drift

- [ ] **Semantic drift:** Progressive deviation from original intent. Mitigation: re-anchoring. (AD-08)
- [ ] **Coordination drift:** Breakdown in multi-agent consensus. Mitigation: protocol enforcement.
- [ ] **Behavioral drift:** Emergence of unintended strategies. Mitigation: constraint reinforcement.
- [ ] Monitor for each type separately.

### 8.17 Context Equilibria

- [ ] **Multi-turn drift reaches stable, noise-limited equilibria** rather than runaway decay. Simple reminder interventions reliably reduce divergence. Implement periodic reminder injection (every N turns or tokens) rather than continuous reinforcement. (arXiv 2510.07777, Oct 2025)

---

## 9. CONTEXT POSITIONING AND ATTENTION MANAGEMENT

### 9.1 Lost-in-the-Middle Is Fundamental

- [ ] **LLMs pay the most attention to tokens at the START and END of the context window.** Information in the middle gets deprioritized. This is architectural (transformer attention mechanisms), not a bug. Instruction placement matters as much as instruction content. (IF-08, CP-CTX-01)

### 9.2 Four-Zone Positioning Hierarchy

| Zone | Position | Attention Level | What Goes Here |
|------|----------|----------------|----------------|
| 1 | System prompt (agent body) | Highest | Core persona, critical rules, workflow steps |
| 2 | Start of conversation | High | CLAUDE.md, project conventions |
| 3 | End of conversation | High | Todo lists, most recent messages, skills |
| 4 | Middle of conversation | Lowest | Earlier non-boundary messages |

### 9.3 Placement Matrix for Instruction Types

- [ ] **Agent body (system prompt):** Core persona, critical rules, workflow steps (highest attention, loaded fresh each time).
- [ ] **CLAUDE.md:** Project conventions, build commands (loaded early, high position).
- [ ] **`.claude/rules/`:** Scoped policies (same priority as CLAUDE.md).
- [ ] **Skills:** Domain knowledge, procedures (loaded on demand, enters at end = recency = high attention).
- [ ] **Todo list:** Current plan, remaining steps (pushed to end = high attention). (CP-CTX-05, CP-ANT-02)

### 9.4 Agent Body Size Management

- [ ] **Keep agent body under 200 lines.** Shorter system prompts get more uniform attention (CP-CTX-04). Within those 200 lines, front-load the 20 most critical rules. If over 200 lines, move non-critical content to skills loaded on demand.
- [ ] **Front-load critical rules.** Put the most important instructions at the TOP. Repeat the single most important rule at both the start AND end of the body.

### 9.5 Emphasis Markers

- [ ] **`IMPORTANT`, `CRITICAL`, `YOU MUST` demonstrably improve adherence.** Use sparingly -- overuse dilutes the effect (every instruction being "CRITICAL" means none are). Add to the 20 most critical instructions.

### 9.6 Structured Format Over Prose

- [ ] **Headers, bullet points, tables are more scannable than prose.** Convert all prose instructions to structured format.

### 9.7 Progressive Disclosure via Skills

- [ ] **Keep base prompt minimal, load detailed knowledge via skills only when needed.** Agent body contains only: identity, mandate, workflow skeleton, boundaries. Skills contain: detailed procedures, domain knowledge, reference material.

### 9.8 Prune Rules That Don't Change Behavior

- [ ] **Remove any instruction that doesn't change behavior when removed.** Each line should pass the test: "Would removing this cause Claude to make mistakes?" Systematically test each rule by temporarily removing it and observing behavior.

### 9.9 CLAUDE.md Token Budget

- [ ] **CLAUDE.md loaded EVERY session. Recommended: under 300 lines.** Shorter is better. Bloated CLAUDE.md files cause Claude to ignore actual instructions -- it actively degrades compliance with all instructions including those in the CLAUDE.md itself.

---

## 10. CONTEXT ROT, COMPACTION, AND MEMORY SURVIVAL

### 10.1 Three Mechanisms of Context Rot

- [ ] **(1) Lost-in-the-Middle Effect:** U-shaped attention curve. (CR-01 through CR-06)
- [ ] **(2) Attention Dilution at Scale:** Attention budget spread thinner as context grows.
- [ ] **(3) Distractor Interference:** Irrelevant context actively degrades performance -- adding irrelevant content is worse than having less context.
- [ ] Minimize irrelevant content. Prefer sub-agent delegation with clean context. Actively prune conversation history of tool outputs no longer relevant.

### 10.2 Measured Impact Thresholds

- [ ] Performance drops >30% when relevant information sits in the middle vs. beginning/end.
- [ ] Critical instructions buried 10,000+ tokens back are frequently "forgotten."
- [ ] Negative constraints (things NOT to do) are especially vulnerable to being ignored in long contexts.
- [ ] For contexts >10,000 tokens, re-inject critical instructions. Place all negative constraints in system prompt AND repeat at end.

### 10.3 KV-Cache Optimization

- [ ] **KV-cache hit rate is the primary production metric.** Cached input tokens cost $0.30/MTok vs. uncached $3/MTok (Claude Sonnet) -- 10x cost difference.
- [ ] **Append-only context design:** Never modify or reorder previous content. Corrections appended as new messages. Tool results in execution order.
- [ ] **Deterministic serialization:** Same data must produce same bytes every time. Use `json.dumps(data, sort_keys=True)`. Avoid timestamps or random values in serialized prompts unless semantically necessary.
- [ ] **Consistent tool name prefixes:** e.g., `browser_*`, `shell_*`.

### 10.4 Auto-Compaction Survival Strategy

- [ ] **Auto-compaction triggers at ~95% of 200K tokens.** System prompt survives (structural). Early conversation messages get summarized and may lose nuance. (CP-CTX-11)
- [ ] **Add compaction instructions in CLAUDE.md:** "When compacting, always preserve: [list of critical context items]." Example: the full list of modified files.

### 10.5 Three Compression Approaches and Their Risks

- [ ] **(1) Prompt Compression (LLMLingua):** Token-level pruning, risk of breaking meaning.
- [ ] **(2) Dynamic Summarization:** Living summary + last N turns, risk of losing specific constraints.
- [ ] **(3) Verbatim Compaction:** Delete tokens without rewriting, most faithful but least flexible.
- [ ] Design instructions to survive all three: keep constraints self-contained (not dependent on surrounding text), use explicit values not references, mark critical sections for preservation.

### 10.6 Never Generalize Specific Values

- [ ] **Keep exact names, paths, values, error messages, URLs, and version numbers verbatim.** Write "threshold is 0.7" not "threshold is defined elsewhere." Include full file paths, not relative references. (CS-02)

### 10.7 Separate Survival-Critical Instructions

- [ ] Instructions that MUST survive should be in system prompts or pinned sections, not embedded in conversation. Use `<!-- COMPACT-SAFE: summary -->` markers on all critical workflow sections. Every file in `.claude/workflow/` must have a COMPACT-SAFE marker. (CS-04)

### 10.8 Structural Redundancy -- Triple Storage

- [ ] **Critical rules should appear in three places:** system prompt + external file + periodic re-injection. If any rule exists in only one location, it is at risk. (CS-05)

### 10.9 External Memory as Compaction Bypass

- [ ] **Persistent files (NOTES.md, todo.md, projects/*.json) survive compaction entirely** because they exist outside the context. Write critical decisions to disk immediately, not just in conversation. Re-read external files at decision points. (CS-06, CS-07)
- [ ] **Manus file-system-as-memory pattern:** The file system is the ultimate context: unlimited in size, persistent by nature, directly operable by the agent. For any information that must persist beyond the current context window, write it to a structured file.
- [ ] **PreCompact hook** can save state before compaction occurs. (CP-HCF-01)

### 10.10 Compaction Tuning Parameters

- [ ] Set compaction trigger at 80% of context window. Preserve last 10 messages unchanged. Test compaction output for information loss before deploying. Log what was discarded.

---

## 11. STRUCTURED OUTPUT ENFORCEMENT

### 11.1 Reliability Ranking

| Rank | Approach | Reliability |
|------|----------|-------------|
| 1 | Constrained Decoding (NVIDIA NIM, Guidance, llama.cpp) | Highest -- guarantees format |
| 2 | API-Native Structured Output (Claude, OpenAI) | High |
| 3 | JSON Schema + Validation | High |
| 4 | Pydantic Validation | Medium-High |
| 5 | Grammar-Based Decoding | Medium |
| 6 | Prompt-Only | Lowest -- never for production |

- [ ] For each agent output, select the highest-reliability approach available. Never use prompt-only for any output that will be parsed programmatically.

### 11.2 Pydantic AI Integration

- [ ] **Define Pydantic models for every agent's input and output.** Use these for both prompt construction (JSON Schema) and response validation. Enable durable execution for long-running agents. Pydantic AI streams with immediate validation and supports durable execution across transient API failures.

### 11.3 Validation-Repair Loop

- [ ] **When structured output fails validation:** (1) Validate with Pydantic or Guardrails AI. (2) On failure, run a "repair" prompt with the validator's errors. (3) Retry with error context. Maximum 3 retry attempts. (4) Version payloads with `schemaVersion` field using semver. Log repair events as quality signals. (AH-05)

### 11.4 Guardrail Frameworks for Output

- [ ] **NVIDIA NeMo Guardrails with Colang:** Declarative language for guardrail logic. Topical/safety/execution rails. OpenTelemetry integration.
- [ ] **Guardrails AI:** Pre-built validators from Guardrails Hub (JSON format, PII, profanity). Custom validators for domain-specific rules. Auto-fix vs. re-prompt configurable per validator.
- [ ] **Llama Guard:** Meta's specialized safety classifier. Customizable safety taxonomies, low-latency classification.

### 11.5 DLP-First Guardrail Strategy

- [ ] **Data Loss Prevention is the recommended starting point.** DLP scan on all inputs before LLM processing. DLP scan on all outputs before delivery. DLP scan on all inter-agent payloads. Once data enters the LLM, it cannot be unlearned.

---

## 12. MULTI-AGENT BEHAVIORAL CONTROL

### 12.1 LangGraph State Machine Architecture

- [ ] **Nodes (agents/tools) connected by edges with conditional logic.** Supports cycles, branching, explicit error handling. Per-node error handling: retry/fallback/human escalation. Global token budget enforcer. Define all graph edges with explicit conditions.

### 12.2 Checkpointing for Time-Travel Debugging

- [ ] **Use PostgresSaver in production (not SQLite).** Enable checkpoint-based state replay, rolling back to prior states. Per-node timeouts and automated retries. Log checkpoint IDs for every execution.

### 12.3 Tripwire Guardrail Pattern (OpenAI SDK, Adapted)

- [ ] **Three guardrail types:** Input (on first agent), Output (on last agent), Tool (before/after execution).
- [ ] **Tripwire behavior:** When triggered, immediately raises exception, halting execution.
- [ ] Any CRITICAL security finding = immediate pipeline halt.

### 12.4 Sub-Agent Context Isolation

- [ ] **Each sub-agent handles focused tasks with a clean context window.** Sub-agents return condensed summaries (1,000-2,000 tokens) to the coordinator. The coordinator maintains a high-level view without detailed noise. Verification agents receive only the code under review, not the full conversation. The orchestrator never receives raw tool outputs from sub-agents. (MA-04)

### 12.5 Token Budget Awareness

- [ ] **Multi-agent systems consume up to 15x more tokens than standard chat.** Budget 15x single-agent token cost. Track per-agent and per-wave token usage. Set per-agent token limits. Use token usage as a health metric -- sudden spikes indicate drift or loops. Maximum 4-6 parallel agents per batch as a practical limit for token budget management. (MA-05)

### 12.6 Observability as Behavioral Control

- [ ] **Trace every step and handoff:** prompts, outputs, tools, tokens, costs, latencies.
- [ ] Sample 10% of runs for manual quality review.
- [ ] Set alerting thresholds for: cost per run, latency per agent, output schema violations.
- [ ] Store traces for at least 30 days.

### 12.7 Framework Selection

- [ ] LangGraph for deterministic flow, CrewAI for rapid prototyping, AutoGen/AG2 for enterprise async, OpenAI Agents SDK for strict guardrails, Pydantic AI for type safety. Document why the framework was chosen and trade-offs accepted.

### 12.8 Single Responsibility Per Agent

- [ ] **100+ specialized subagents, each with single responsibility, clear description, minimal tool set** (CP-PRD-04). Verification is the highest-leverage practice -- give agents ways to verify their own work: tests to run, expected outputs to validate. (CP-ANT-06)

---

## 13. AGENT HANDOFF AND SHUTDOWN

### 13.1 Core Insight

- [ ] **"Reliability lives and dies in the handoffs."** Most "agent failures" are actually orchestration and context-transfer issues (AH-01). When an agent fails, investigate the handoff first. Log every handoff payload. Validate handoff payloads against schemas before sending. Track handoff failure rates separately from agent failure rates.

### 13.2 Four Handoff Patterns

| Pattern | When to Use |
|---------|-------------|
| Structured Data Transfer (JSON Schema) | Default for all handoffs (AH-02, AH-03) |
| Conversation History Transfer | Continuity-critical only |
| Summary Transfer | Long pipelines, token-efficient |
| File-Based Transfer | Cross-session state |

### 13.3 Anti-Patterns

- [ ] **Never use free-text handoffs.** Free text is ambiguous, lossy, and unparseable. Implicit state is the leading cause of handoff failures. Every handoff must use a defined schema. Anything not explicitly serialized is a bug.
- [ ] **Never leave tool calls unpaired.** LLMs expect tool calls paired with responses. Handoff messages must include both the AIMessage containing the tool call and a ToolMessage acknowledging the handoff.

### 13.4 Handoff Best Practices

- [ ] **Version payloads with semver.** Include `schemaVersion` in all handoff payloads (AH-05). Bump minor for additive changes, major for breaking changes. Receiving agent validates version compatibility.
- [ ] **Validate strictly with repair loop.** Pydantic validation on every handoff receive. On failure: log, repair prompt, retry up to 3 times, then escalate to human.
- [ ] **Bind tool permissions to roles.** Define a tool whitelist per agent role. Block tool calls not in the whitelist. Audit for agents with >10 tools.
- [ ] **Trace every handoff.** Log: handoff payload, sending agent, receiving agent, timestamp, token count.
- [ ] **LangGraph Command.PARENT for parent handoff.** Must include both AIMessage and ToolMessage. Define error nodes routing to human after 3 retries. Enable checkpointing on all handoff nodes.

### 13.5 Agent Shutdown Protocol

- [ ] **Agents shut down after completing their round.** Reports are written to disk before shutdown. No persistent agent state in memory. Fresh context by default maximizes per-agent performance (AH-09). Persistent agents accumulate context rot. File-based reports survive agent termination (CS-06).
- [ ] **Shutdown sequence:** (1) Write report to assigned path. (2) Update progress tracker. (3) Return condensed summary (1,000-2,000 tokens) to orchestrator. (4) Terminate. SubagentStop hook cleans up temp resources.

---

## 14. PRODUCTION PATTERNS AND CASE STUDIES

### 14.1 Trail of Bits -- OS-Level Sandboxing

- [ ] Runs Claude Code in `--dangerously-skip-permissions` mode with OS-level sandboxing (Seatbelt on macOS, bubblewrap on Linux). Security model shifts from restricting the agent to sandboxing the environment. Reference: `trailofbits/claude-code-config`.

### 14.2 Security Reviewer Pattern (Anthropic Docs)

- [ ] `model: opus`, `tools: Read, Grep, Glob, Bash`. Reviews for: injection vulnerabilities, auth flaws, secrets in code, insecure data handling. Must provide specific line references and suggested fixes. Read-only tools prevent modification.

### 14.3 Database Reader -- Hook-Enforced Read-Only

- [ ] Has `tools: Bash` only, with PreToolUse hook validating queries are read-only. Dual enforcement: prompt tells agent it's read-only (Tier 1) + hook blocks write operations deterministically (Tier 3). The prompt-level instruction helps Claude explain denials gracefully.

### 14.4 VoltAgent -- Single Responsibility

- [ ] 100+ specialized subagents, each with single responsibility, clear description, minimal tool set. Reference: `VoltAgent/awesome-claude-code-subagents`.

### 14.5 Adaline Labs -- Plan Gate Before Implementation

- [ ] (1) Plan gate before implementation. (2) Subagent review after implementation. (3) Multi-model review for critical changes. (4) PR opened only when all checks pass.

### 14.6 Captain Hook -- Intent-Based Policy Enforcement

- [ ] Evaluates the agent's intent at the exact moment it decides to act. Deterministic, not advisory. Reference: `securityreview.ai/blog/captain-hook-ai-agent-policy-enforcement-for-claude`.

### 14.7 Codacy -- 5-Minute Deterministic Guardrails

- [ ] Setup takes 5 minutes. PreToolUse hooks for security scanning, PostToolUse for validation. Minimum baseline for every project.

### 14.8 Anti-Drift for Verification Agents (4 Techniques)

- [ ] (1) **Template constraints:** Every verification agent has an exact report template. (CP-PRD-08)
- [ ] (2) **Checklist in agent body:** Explicit items to check, not vague "review for quality."
- [ ] (3) **Escalation clause:** "If you cannot complete a check, report it as INCONCLUSIVE rather than skipping it."
- [ ] (4) **Self-verification:** "Before finalizing your report, verify that every section is filled and every file mentioned exists."

---

## 15. SIOPV-SPECIFIC RECOMMENDATIONS

### 15.1 Agent Tool Assignments

| Agent | Tools | Enforcement |
|-------|-------|-------------|
| security-auditor | Read-only + Bash | PreToolUse hook blocks write commands |
| code-implementer | All tools | PostToolUse runs ruff/mypy after every edit |
| test-generator | All tools | PostToolUse runs pytest after test file creation |
| hallucination-detector | Read-only only | NO Bash |
| best-practices-enforcer | Read-only + Bash | For running linters |

### 15.2 Hook Enforcement Configuration

- [ ] PreToolUse matcher "Bash" -> `.claude/hooks/block-dangerous-commands.sh`
- [ ] PostToolUse matcher "Edit|Write" -> `.claude/hooks/run-linter.sh`
- [ ] Add to `.claude/settings.json` under `hooks` key.

### 15.3 Path-Targeted Rules for Domains

- [ ] `security.md` targeted to `src/siopv/infrastructure/**`
- [ ] `orchestration.md` targeted to `src/siopv/application/orchestration/**`
- [ ] Additional domain-specific rules files as needed.

### 15.4 Pipeline State File

- [ ] Have each graph node update a persistent `pipeline_state.md` with current progress, remaining steps, accumulated findings. Serves as both external memory and attention anchor for the orchestrator.

### 15.5 Node-Level Context Isolation in LangGraph

- [ ] Each node receives only the TypedDict fields relevant to its function. Restrict to only the fields it reads/writes. Flag nodes accessing >5 state fields for review.

### 15.6 PostgresSaver for Production Checkpointing

- [ ] Migrate from SQLite to PostgresSaver. Enable time-travel debugging on classify_node and enrich_node.

### 15.7 Three-Layer Guardrails Mapped to Hexagonal Architecture

- [ ] **Input Port Guardrails:** PII/Presidio, Pydantic validation, rate limiting.
- [ ] **Processing Guardrails:** Tool state machine, token budget, timeout/retry, LLM judge on classify_node.
- [ ] **Output Port Guardrails:** Pydantic validation, DLP scan, hallucination detection, schema version enforcement.

### 15.8 Anti-Drift for classify_node (5 Mitigations)

- [ ] (1) Runtime reinforcement -- append classification constraints at end of every LLM prompt.
- [ ] (2) Structured output -- Pydantic models with strict JSON Schema.
- [ ] (3) Behavioral anchoring -- 3-5 canonical classification examples.
- [ ] (4) Output validation -- confidence scores within expected ranges.
- [ ] (5) LLM judge -- lightweight secondary model for consistency verification.

### 15.9 Compaction-Safe Architecture for Multi-Session Pipeline

- [ ] Pin critical constraints in system prompts.
- [ ] Use COMPACT-SAFE markers on all workflow files.
- [ ] External state files per phase.
- [ ] Instruction redundancy -- every critical rule in system prompt, node-level prompt, AND external config.

### 15.10 Verification Pipeline Guardrails

- [ ] Pydantic-validated report schemas for all 5 agents.
- [ ] Tripwire pattern -- CRITICAL finding = immediate halt.
- [ ] Wave timing: Wave 1 max 7 min, Wave 2 max 5 min.
- [ ] Clean context per verification agent.
- [ ] Drift detection -- compare against historical baselines.

### 15.11 Deterministic Behavior Where Possible

- [ ] Deterministic graph flow for non-LLM logic.
- [ ] Reproducibility logging: model ID, temperature, seed, full prompts for every LLM call.
- [ ] Constrained decoding for all LLM calls.
- [ ] Note: true determinism is impossible (temperature=0 is not fully deterministic due to floating-point arithmetic and MoE routing).

### 15.12 Inter-Phase Handoff Protocol

- [ ] `projects/siopv.json` as canonical state transfer.
- [ ] Pydantic models for inter-phase state.
- [ ] Validation on resume -- validate all accumulated state against schemas.
- [ ] Audit trail -- log inputs, outputs, verification results per phase transition.

---

## 16. DESIGN DECISIONS FOR SIOPV

### DD-001: Agent Definition File Structure

- [ ] **DD-001**
- **What:** Every SIOPV agent uses `.md` files in `.claude/agents/` with YAML frontmatter containing at minimum: `name`, `description`, `tools`. Body contains the complete system prompt.
- **Why:** Subagents receive ONLY the body content plus environment details (CP-ADS-01, CP-ADS-02). Four-field minimum is the irreducible set for controlled behavior.
- **How:** Create `.claude/agents/` directory structure. Each agent file follows the template: frontmatter (name, description, tools, model, maxTurns, hooks) + body (identity, mandate, workflow, boundaries, output format, critical rule repetition).

### DD-002: Persona Template

- [ ] **DD-002**
- **What:** All SIOPV agents follow a standardized 4-element persona pattern: identity + domain expertise + constraints + output format.
- **Why:** Direct persona assignment outperforms imagination framing (IF-03). The 4-element pattern ensures completeness. Explicit "You are NOT" constraints prevent persona leakage (PR-05, CP-ANT-09).
- **How:** Every agent body begins with: `You are a [role] specialized in [domain]. Your mandate is [single sentence]. You are NOT [anti-persona list]. YOU MUST [top 3 rules]. DO NOT [5-item list].` Followed by workflow steps, then output format, then critical rule repetition at end.

### DD-003: Per-Agent Rule Limit

- [ ] **DD-003**
- **What:** Maximum 20 core rules per agent body. Maximum 200 lines per agent body.
- **Why:** The 150-instruction ceiling applies within agent bodies too. Beyond 20 rules, compliance degrades measurably (CP-GAE-02, CP-CTX-04). Longer prompts suffer internal lost-in-the-middle.
- **How:** Count rules during agent creation. If a body exceeds 20 rules or 200 lines, split into core rules (in body) and supplementary knowledge (in skills loaded on demand). Audit quarterly.

### DD-004: Agent Body Size Limit

- [ ] **DD-004**
- **What:** Agent bodies capped at 200 lines. Non-critical content moved to skills or external reference files.
- **Why:** Shorter system prompts get more uniform attention (CP-CTX-04). The 200-line limit ensures the full body fits within the high-attention zone.
- **How:** Measure every agent body during creation. Bodies exceeding 200 lines trigger a mandatory refactoring into body (core) + skill (supplementary). The body retains: identity, mandate, workflow skeleton, boundaries, output format, and the 20 most critical rules.

### DD-005: Hook Configuration

- [ ] **DD-005**
- **What:** Three hook types deployed across SIOPV agents: (1) PreToolUse blocking hooks for security enforcement. (2) PreCompact hooks to save agent state before compaction. (3) PostToolUse hooks for auto-formatting after edits.
- **Why:** "Rules are requests, hooks are laws" (CP-GAE-01). PreToolUse is the ONLY blocking hook (CP-HCF-02). PreCompact preserves state that would be lost to auto-compaction (CP-CTX-11).
- **How:** In `.claude/settings.json`: PreToolUse matcher "Bash" runs `block-dangerous-commands.sh` (exit code 2 to block). PostToolUse matcher "Edit|Write" runs `run-linter.sh`. Agent-scoped hooks in frontmatter for agent-specific restrictions. PreCompact hook saves current todo state to disk.

### DD-006: Tool Restriction Strategy

- [ ] **DD-006**
- **What:** Tool allowlists per agent type. Default to read-only; add write tools only when the agent's mandate requires modification.
- **Why:** Scoped tool access is the most reliable anti-improvisation mechanism -- deterministic prevention (CP-ANT-07, CP-GAE-08).
- **How:** Scanner agents: `Read, Grep, Glob, Bash` (Bash with PreToolUse blocking writes). Researcher agents: `Read, Grep, Glob, WebSearch, WebFetch`. Summarizer agents: `Read, Grep, Glob, Write` (write only to report directory). Orchestrator agents: `Read, Grep, Glob, Bash, Write, Agent, SendMessage`.

### DD-007: Report Template Enforcement

- [ ] **DD-007**
- **What:** Every agent produces reports following an exact template. Reports are validated structurally before acceptance.
- **Why:** Template constraints on output are one of the four anti-drift techniques for verification agents (CP-PRD-08). Structured payloads prevent context loss (AH-02).
- **How:** Each agent's body includes an exact report template with required sections. Reports must include: agent name, stage/round/batch IDs, timestamp, execution duration, findings (structured), file paths referenced, and a summary. PostToolUse hook validates report structure.

### DD-008: Context Positioning Strategy

- [ ] **DD-008**
- **What:** Front-load the 3 most critical rules at the top of every agent body. Repeat the single most important rule at the end.
- **Why:** >30% performance drop when key information sits in the middle vs. beginning/end (IF-08, CP-CTX-05). Repetition at both positions exploits primacy and recency.
- **How:** Agent body structure: (1) Identity + top 3 rules (first 10 lines). (2) Full workflow. (3) Boundaries and DO NOT list. (4) Output format. (5) Repeat of the #1 most critical rule (last 3 lines). Use `IMPORTANT`, `YOU MUST`, `NEVER` markers sparingly on the top 20 rules only.

### DD-009: Anti-Improvisation Constraints

- [ ] **DD-009**
- **What:** Every agent includes: (a) explicit DO NOT list (5 items minimum), (b) todo list recitation after each step, (c) fresh context between unrelated tasks.
- **Why:** Per-step constraint design prevents both over-constraining creative steps and under-constraining critical steps (CP-ANT-01). Todo recitation pushes global plan into high-attention zone (CP-ANT-02). Fresh context outperforms accumulated corrections (CP-ANT-03).
- **How:** DO NOT list template: `DO NOT: (1) modify files outside your scope, (2) skip files because they "look fine", (3) speculate about business impact, (4) suggest fixes when your role is analysis, (5) proceed without updating your todo list.` Todo recitation instruction: "After each step, update your progress: [x] completed, [ ] remaining, Current focus: [step]."

### DD-010: Compaction-Safe Markers

- [ ] **DD-010**
- **What:** All workflow files and agent briefings include `<!-- COMPACT-SAFE: summary -->` markers. Critical values are literal, not references.
- **Why:** Auto-compaction at ~95% of 200K tokens summarizes conversation content. Markers and literal values survive compression (CS-02, CS-04).
- **How:** Every workflow file header includes a COMPACT-SAFE marker with a one-line summary of the essential information. All thresholds, paths, and constraints use literal values ("threshold is 0.7") never references ("threshold is defined in constants.py"). Triple storage for non-negotiable rules: system prompt + external file + runtime re-injection.

### DD-011: Round and Batch Management

- [ ] **DD-011**
- **What:** Within each stage, work is organized as Rounds (sequential units) containing Batches (parallel groups). Maximum 4-6 parallel agents per batch.
- **Why:** Sub-agent context isolation prevents cross-contamination (MA-04). 4-6 parallel agents is the practical limit for token budget management (MA-05). Sequential rounds allow human checkpoints between phases.
- **How:** Stage execution: Round 1 (Batch A: agents 1-4 in parallel) -> wave summarizer -> human checkpoint -> Round 2 (Batch A: agents 5-8 in parallel) -> wave summarizer -> human checkpoint -> final summarizer reads only round summaries.

### DD-012: Human Checkpoint Protocol

- [ ] **DD-012**
- **What:** Human approval required between rounds, after final summaries, and before any destructive action. Automatic continuation for agent delegation, file reads, and report generation.
- **Why:** Human-in-the-loop at boundaries catches systemic issues before they propagate. Automatic continuation within rounds prevents bottlenecks (from existing `.claude/workflow/03-human-checkpoints.md`).
- **How:** Orchestrator pauses and presents a summary after each round's wave summarizer completes. Human reviews findings, approves next round or requests corrections. No commit without human approval of consolidated verification results.

### DD-013: Agent Shutdown Protocol

- [ ] **DD-013**
- **What:** Agents shut down after completing their round. Reports are written to disk before shutdown. No persistent agent state in memory.
- **Why:** Fresh context by default maximizes per-agent performance (AH-09). Persistent agents accumulate context rot. File-based reports survive agent termination (CS-06).
- **How:** Agent workflow ends with: (1) write report to assigned path, (2) update progress tracker, (3) return condensed summary (1,000-2,000 tokens) to orchestrator, (4) terminate. SubagentStop hook cleans up temp resources.

### DD-014: File Naming Convention

- [ ] **DD-014**
- **What:** All reports follow the pattern: `NNN_YYYY-MM-DD_HH.MM.SS_descriptive-name.md` where NNN is a zero-padded sequence number within the stage.
- **Why:** Timestamp-based naming prevents race conditions under parallel execution. Sequential prefix preserves reading order. UUID-style timestamps ensure uniqueness without coordination (from `.claude/rules/agent-reports.md`).
- **How:** Example: `001_2026-03-09_14.30.45_hexagonal-layer-scan.md`. Each stage has its own sequence counter starting at 001. Agents receive their sequence number from the orchestrator at spawn time.

### DD-015: Directory Structure for the Audit Project

- [ ] **DD-015**
- **What:** All audit artifacts stored under `.ignorar/agent-persona-research-2026-03-09/` with per-stage subdirectories.
- **Why:** `.ignorar/` is gitignored (no leakage of internal artifacts). Per-stage directories enable clean navigation and stage-level auditing.
- **How:**
```
.ignorar/agent-persona-research-2026-03-09/
  001_claude-code-agent-persona-guardrails-behavioral-control.md  (existing)
  002_llm-agent-behavioral-control-guardrails-techniques.md       (existing)
  003_checkpoints-extracted-from-claude-code-report.md             (existing)
  004_checkpoints-extracted-from-llm-behavioral-report.md          (existing)
  005_dual-purpose-technical-record-and-checklist-for-agent-design.md (existing)
  stage-1/   (Discovery & spec mapping reports)
  stage-2/   (Hexagonal quality audit reports)
  stage-3/   (SOTA research & deep scan reports)
  stage-4/   (Claude Code configuration setup artifacts)
  stage-5/   (Remediation-hardening reports)
```

---

## 17. STAGE ARCHITECTURE

### STAGE-1: Discovery & Spec Mapping

**Objective:** Map the SIOPV codebase structure, identify all modules, verify alignment with the project specification, and produce a comprehensive inventory.

**Agent types:**
- **Scanner agents (3-4):** Scan directory structure, imports, dependencies, test coverage per module. Read-only tools.
- **Summarizer (1):** Consolidates scanner findings into a unified spec-vs-implementation matrix.
- **Orchestrator (1):** Manages scanner rounds, collects reports, triggers summarizer.

**Expected rounds:** 2 rounds. Round 1: parallel scanners cover different codebase areas. Round 2: summarizer consolidates.

**Internal naming:** Round 1, Batch A (scanners). Round 2, Batch A (summarizer).

**Report output:** `.ignorar/agent-persona-research-2026-03-09/stage-1/`

### STAGE-2: Hexagonal Quality Audit

**Objective:** Audit code quality against hexagonal architecture principles. Check layer violations, dependency direction, port/adapter compliance, and DI patterns.

**Agent types:**
- **Scanner agents (4-6):** Each audits a specific hexagonal layer or cross-cutting concern (domain, application, infrastructure, interfaces, DI, testing). Read-only tools.
- **Summarizer (1):** Consolidates findings into a severity-ranked finding list with file-level detail.
- **Orchestrator (1):** Manages scanner rounds.

**Expected rounds:** 2-3 rounds. Round 1: domain + application layers. Round 2: infrastructure + interfaces layers. Round 3 (if needed): cross-cutting concerns.

**Internal naming:** Round 1, Batch A (domain scanner, application scanner). Round 2, Batch A (infra scanner, interfaces scanner). Round 3, Batch A (DI scanner, test scanner).

**Report output:** `.ignorar/agent-persona-research-2026-03-09/stage-2/`

### STAGE-3: SOTA Research & Deep Scan

**Objective:** Research state-of-the-art techniques for each SIOPV component. Compare current implementation against best practices from academic literature, framework documentation, and production patterns.

**Agent types:**
- **Researcher agents (4-6):** Each researches a specific domain (LangGraph patterns, DLP/Presidio best practices, vulnerability classification SOTA, OpenFGA patterns, Streamlit HITL patterns). Online research tools (WebSearch, WebFetch, Context7).
- **Summarizer (1):** Consolidates research into actionable recommendations ranked by impact.
- **Orchestrator (1):** Manages researcher rounds.

**Expected rounds:** 2-3 rounds. Round 1: core pipeline research (LangGraph, classification, DLP). Round 2: supporting systems research (OpenFGA, Streamlit, output generation). Round 3 (if needed): gap-filling research.

**Internal naming:** Round 1, Batch A (researchers 1-3). Round 2, Batch A (researchers 4-6). Round 3, Batch A (targeted researchers).

**Report output:** `.ignorar/agent-persona-research-2026-03-09/stage-3/`

### STAGE-4: Claude Code Configuration Setup

**Objective:** Create the actual agent definition files, hook scripts, rules files, and settings.json configuration needed to operate SIOPV's agent team.

**Agent types:**
- **Scanner agents (2):** Audit existing `.claude/` configuration against research findings. Identify gaps and misconfigurations.
- **Summarizer (1):** Produces a configuration gap analysis and implementation plan.
- **Orchestrator (1):** Manages the audit and produces the final configuration blueprint.

**Expected rounds:** 2 rounds. Round 1: configuration audit scanners. Round 2: gap analysis summarizer.

**Report output:** `.ignorar/agent-persona-research-2026-03-09/stage-4/`

### STAGE-5: Remediation-Hardening (Designed Later)

**Objective:** Apply corrections and fixes identified in STAGE-1 through STAGE-4. This stage is designed AFTER stages 1-4 complete, based on their findings.

**Agent types:** To be determined based on findings. Expected to include code-implementer agents (write-capable), verification agents (5-agent pipeline), and a remediation orchestrator.

**Expected rounds:** Variable, determined by finding volume and severity.

**Report output:** `.ignorar/agent-persona-research-2026-03-09/stage-5/`

---

## 18. REUSABLE TEAM TEMPLATE

The following template applies uniformly to STAGE-1 through STAGE-4. It encodes the research findings into a concrete operational pattern.

### 18.1 Team Lifecycle

1. **claude-main** spawns an orchestrator via `TeamCreate` + `Agent`.
2. The orchestrator reads its briefing file and manages everything from that point.
3. The orchestrator spawns rounds of 4-6 parallel agents maximum per batch.
4. Each agent operates with a clean context window (fresh context by default -- AH-09).
5. Agents write their reports to disk, return a condensed summary (1,000-2,000 tokens), and terminate.
6. A wave summarizer reads ONLY the round's reports (not the raw agent conversations) and produces a round summary.
7. The orchestrator presents the round summary to the human via `SendMessage` to claude-main.
8. **Human checkpoint:** Human reviews and approves the next round or requests corrections.
9. After all rounds complete, a final summarizer reads ONLY round summaries (not individual agent reports) and produces the stage deliverable.
10. Human approves the stage deliverable.

### 18.2 Context Management

- **60% context soft limit:** Agents should aim to complete their work within 60% of the context window. PreCompact hook saves state to disk as a safety net before auto-compaction triggers at 95%.
- **External memory:** Orchestrator maintains a `todo.md` file updated after each round. Agents write findings to disk immediately, not held in memory.
- **No cross-agent context bleeding:** Each agent starts fresh. The only shared state is on disk (reports, todo.md, progress tracker).

### 18.3 Report Structure (Uniform)

Every agent report, regardless of stage or role, follows this structure:

```markdown
# [Agent Name] Report

**Stage:** STAGE-N
**Round:** N, Batch: A
**Sequence:** NNN
**Timestamp:** YYYY-MM-DD HH:MM:SS
**Duration:** N minutes

## Mandate
[One sentence: what this agent was asked to do]

## Findings
### Finding F-NNN: [Title]
- **Severity:** CRITICAL | HIGH | MEDIUM | LOW | INFO
- **Location:** [file path:line number]
- **Description:** [what was found]
- **Evidence:** [grep output, code snippet, or reference]
- **Recommendation:** [what should be done]

## Summary
- Total findings: N
- By severity: CRITICAL: N, HIGH: N, MEDIUM: N, LOW: N, INFO: N
- Files examined: N
- Files with findings: N

## Self-Verification
- [ ] All sections filled
- [ ] Every file path verified to exist
- [ ] Every finding has evidence
- [ ] Severity assignments are consistent
```

---

## 19. AGENT PERSONA TEMPLATES

### 19.1 Scanner Persona (STAGE-1 and STAGE-2)

```markdown
---
name: siopv-scanner-[domain]
description: "Scans [domain] for [specific audit criteria]"
tools:
  - Read
  - Grep
  - Glob
  - Bash
model: sonnet
maxTurns: 25
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: ".claude/hooks/block-write-commands.sh"
---

# Scanner: [Domain Name]

YOU MUST follow these three rules above all others:
1. NEVER modify any file. You are read-only. Your job is to observe and report.
2. Every finding MUST include a file path and line number as evidence.
3. Follow the exact report template below. Do not invent sections or skip sections.

## Identity
You are a code scanner specialized in [domain]. Your mandate is to examine the SIOPV
codebase and report findings related to [specific audit criteria].

You are NOT a code implementer. You are NOT a fixer. You are NOT an advisor on business
strategy. You do not suggest solutions. You report facts.

## Workflow
1. Read your assigned scope: [list of directories/files].
2. For each file, check against these criteria:
   - [Criterion 1]
   - [Criterion 2]
   - [Criterion 3]
3. After each file, update your progress:
   [x] Completed files
   [ ] Remaining files
   Current focus: [file]
4. Write your report to: [assigned report path]
5. Return a condensed summary (max 1,500 tokens) to the orchestrator.

## DO NOT
1. DO NOT modify, edit, or create any file other than your report.
2. DO NOT skip files because they "look fine" -- examine every file in scope.
3. DO NOT speculate about developer intent or business impact.
4. DO NOT suggest implementations or fixes.
5. DO NOT run any command that modifies the filesystem (no rm, mv, cp, write).

## Output Format
[Use the exact report template from Section 18.3]

## Boundaries
- Scope: ONLY the files listed in your assignment.
- If you encounter a situation where your constraints do not fit, report it as
  ESCALATION with your reasoning. Do not ignore the constraint silently.

REMINDER: You are read-only. NEVER modify any file. Report findings with evidence only.
```

**Line count: ~50 lines.** Well under the 200-line limit.

### 19.2 Researcher Persona (STAGE-3)

```markdown
---
name: siopv-researcher-[topic]
description: "Researches state-of-the-art techniques for [topic]"
tools:
  - Read
  - Grep
  - Glob
  - WebSearch
  - WebFetch
model: opus
maxTurns: 30
---

# Researcher: [Topic Name]

YOU MUST follow these three rules above all others:
1. Every claim MUST cite a specific source (URL, paper, documentation page).
2. NEVER rely on training data alone -- verify all technical claims via WebSearch.
3. Follow the exact report template below. Do not invent sections or skip sections.

## Identity
You are a technical researcher specialized in [topic]. Your mandate is to investigate
current state-of-the-art techniques and best practices for [specific SIOPV component],
compare them against the current SIOPV implementation, and produce actionable
recommendations.

You are NOT a code implementer. You are NOT a summarizer of general knowledge. You are
NOT speculating -- every recommendation must be grounded in a specific source.

## Workflow
1. Read the current SIOPV implementation of [component]: [list of files].
2. Search for current best practices using WebSearch:
   - Query 1: "[specific search query]"
   - Query 2: "[specific search query]"
   - Query 3: "[specific search query]"
3. For each source found, extract: technique, evidence of effectiveness, applicability
   to SIOPV.
4. Compare current implementation against findings.
5. After each search, update your progress:
   [x] Completed searches
   [ ] Remaining searches
   Current focus: [query]
6. Write your report to: [assigned report path]
7. Return a condensed summary (max 1,500 tokens) to the orchestrator.

## Verification Before Reporting
- For every library recommendation, verify current API via Context7 or documentation.
- For every technique, verify it has been validated in production (not just proposed).

## DO NOT
1. DO NOT modify any file other than your report.
2. DO NOT recommend techniques without citing a specific source.
3. DO NOT rely solely on training data -- use WebSearch for all claims.
4. DO NOT recommend tools or libraries without checking their current maintenance status.
5. DO NOT provide code implementations -- provide technique descriptions and references.

## Output Format
[Use the exact report template from Section 18.3, with an additional "Sources" section
listing all URLs and papers consulted]

## Boundaries
- Scope: ONLY the topic assigned. Do not expand into adjacent research areas.
- If you encounter a situation where additional research is needed beyond scope,
  report it as ESCALATION.

REMINDER: Every claim MUST cite a specific source. No unsourced recommendations.
```

**Line count: ~60 lines.** Well under the 200-line limit.

### 19.3 Summarizer Persona (All Stages)

```markdown
---
name: siopv-summarizer-[stage]-[round]
description: "Consolidates reports from [stage] [round] into a unified summary"
tools:
  - Read
  - Grep
  - Glob
  - Write
model: sonnet
maxTurns: 15
---

# Summarizer: [Stage] [Round/Final]

YOU MUST follow these three rules above all others:
1. ONLY read the reports listed below. Do not read source code or other files.
2. Preserve ALL specific numbers, file paths, severity ratings, and metrics exactly as
   stated in the source reports. NEVER generalize specific values.
3. Deduplicate findings: if multiple reports mention the same issue, merge them into one
   finding with all evidence combined. Do not report duplicates.

## Identity
You are a technical summarizer. Your mandate is to read the reports produced by
[round/stage] agents and produce a single consolidated summary that preserves all
findings while eliminating redundancy.

You are NOT an analyst. You are NOT adding your own findings. You are NOT changing
severity ratings. You consolidate and deduplicate, nothing more.

## Workflow
1. Read each report in order:
   - [Report path 1]
   - [Report path 2]
   - [Report path N]
2. Extract all findings from each report.
3. Deduplicate: merge findings that reference the same file:line or the same issue.
4. Sort findings by severity (CRITICAL first, then HIGH, MEDIUM, LOW, INFO).
5. Write the consolidated summary to: [assigned output path]
6. Return a condensed summary (max 2,000 tokens) to the orchestrator.

## DO NOT
1. DO NOT read source code files. Your input is ONLY the agent reports.
2. DO NOT add new findings that are not in the source reports.
3. DO NOT change severity ratings assigned by scanners/researchers.
4. DO NOT generalize specific values (write "0.7" not "a threshold value").
5. DO NOT omit findings. Every finding from every report must appear in the output.

## Output Format
# Consolidated Summary: [Stage] [Round/Final]

**Reports consolidated:** N
**Total unique findings:** N (after deduplication)
**Duplicates removed:** N

## Findings by Severity

### CRITICAL (N)
[merged findings]

### HIGH (N)
[merged findings]

[... etc.]

## Cross-Report Patterns
[Any patterns that appear across multiple reports]

## Escalations
[Any ESCALATION items from source reports]

REMINDER: Preserve ALL specific numbers and file paths exactly. NEVER generalize.
```

**Line count: ~65 lines.** Well under the 200-line limit.

### 19.4 Orchestrator Persona (All Stages)

```markdown
---
name: siopv-orchestrator-[stage]
description: "Orchestrates [stage] execution: spawns agents, manages rounds, enforces checkpoints"
tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Write
  - Agent
  - SendMessage
model: opus
maxTurns: 50
---

# Orchestrator: [Stage Name]

YOU MUST follow these three rules above all others:
1. NEVER do analysis work yourself. You spawn agents to do work. You coordinate.
2. Maximum 4-6 parallel agents per batch. NEVER exceed this limit.
3. After every round, send a summary to claude-main via SendMessage and WAIT for human
   approval before starting the next round.

## Identity
You are an orchestrator for [stage]. Your mandate is to manage the execution of
[stage objective] by spawning specialized agents in rounds, collecting their reports,
triggering summarizers, and enforcing human checkpoints between rounds.

You are NOT a scanner. You are NOT a researcher. You are NOT a summarizer. You do not
examine code, search the web, or consolidate findings. You delegate, coordinate, and
enforce process.

## Round Plan
### Round 1: [description]
- Batch A: [agent list with assigned scopes]
- After all agents complete: spawn wave summarizer
- Send round summary to claude-main
- WAIT for human approval

### Round 2: [description]
- Batch A: [agent list with assigned scopes]
- After all agents complete: spawn wave summarizer
- Send round summary to claude-main
- WAIT for human approval

### Final: Consolidation
- Spawn final summarizer to read only round summaries (NOT individual reports)
- Send final summary to claude-main
- WAIT for human approval

## Progress Tracking
Maintain a progress file at: [stage todo path]
Update after each event:
```
[x] Round 1 agents spawned (N/N completed)
[x] Round 1 summarizer completed
[x] Round 1 human approval received
[ ] Round 2 agents spawned
[ ] Round 2 summarizer
[ ] Final summarizer
Current: [state]
```

## Agent Spawn Template
When spawning each agent, include in the prompt:
1. The agent's persona (from the appropriate template)
2. Assigned scope (specific files/directories)
3. Report output path: `[stage dir]/NNN_YYYY-MM-DD_HH.MM.SS_descriptive-name.md`
4. Maximum token budget for their summary return

## DO NOT
1. DO NOT do any analysis, scanning, or research yourself.
2. DO NOT spawn more than 6 agents in a single batch.
3. DO NOT proceed to the next round without human approval.
4. DO NOT read source code files -- only read agent reports and progress files.
5. DO NOT modify any file except the progress tracker and orchestration state.

## Error Handling
- If an agent fails or times out: log the failure, report to claude-main, ask whether
  to retry or skip.
- If 2+ agents in a batch fail: STOP the stage and escalate to claude-main.
- After two failed corrections of the same agent, mark it as FAILED and report.

REMINDER: You are a coordinator. NEVER do analysis work yourself. Spawn agents.
```

**Line count: ~80 lines.** Well under the 200-line limit.

---

## 20. IMPLEMENTATION CHECKLIST

This is the operational checklist. Order matters -- each item depends on previous items being complete.

### Phase A: Directory Structure Setup (est. 3 files)

- [ ] 1. Create `.ignorar/agent-persona-research-2026-03-09/stage-1/` directory
- [ ] 2. Create `.ignorar/agent-persona-research-2026-03-09/stage-2/` directory
- [ ] 3. Create `.ignorar/agent-persona-research-2026-03-09/stage-3/` directory
- [ ] 4. Create `.ignorar/agent-persona-research-2026-03-09/stage-4/` directory
- [ ] 5. Create `.ignorar/agent-persona-research-2026-03-09/stage-5/` directory

### Phase B: Hook Scripts (est. 3 files)

- [ ] 6. Create `.claude/hooks/block-write-commands.sh` -- PreToolUse script that reads `$INPUT` via `cat`, extracts command via `jq`, blocks `rm`, `mv`, `cp`, `chmod`, `chown`, `dd`, write redirects. Exit 2 to block, exit 0 to allow.
- [ ] 7. Create `.claude/hooks/block-dangerous-commands.sh` -- PreToolUse script for general Bash safety (blocks `sudo`, `curl | bash`, `eval`, `exec`). Exit 2 to block.
- [ ] 8. Create `.claude/hooks/run-linter.sh` -- PostToolUse script that runs `ruff check` and `ruff format --check` after Edit/Write operations.

### Phase C: Settings Configuration (est. 1 file)

- [ ] 9. Update `.claude/settings.json` with hook configurations: PreToolUse matcher "Bash" pointing to `block-dangerous-commands.sh`, PostToolUse matcher "Edit|Write" pointing to `run-linter.sh`.

### Phase D: Agent Definition Files (est. 8-12 files)

- [ ] 10. Create scanner agent template: `.claude/agents/siopv-scanner-template.md` (base template, copied and customized per stage).
- [ ] 11. Create researcher agent template: `.claude/agents/siopv-researcher-template.md`.
- [ ] 12. Create summarizer agent template: `.claude/agents/siopv-summarizer-template.md`.
- [ ] 13. Create orchestrator agent template: `.claude/agents/siopv-orchestrator-template.md`.
- [ ] 14. Create STAGE-1 orchestrator briefing: `.ignorar/agent-persona-research-2026-03-09/stage-1-briefing.md` with concrete round plan, agent assignments, scope mappings, and report paths.
- [ ] 15. Create STAGE-2 orchestrator briefing: `.ignorar/agent-persona-research-2026-03-09/stage-2-briefing.md`.
- [ ] 16. Create STAGE-3 orchestrator briefing: `.ignorar/agent-persona-research-2026-03-09/stage-3-briefing.md`.
- [ ] 17. Create STAGE-4 orchestrator briefing: `.ignorar/agent-persona-research-2026-03-09/stage-4-briefing.md`.

### Phase E: Rules Files (est. 3-5 files)

- [ ] 18. Create `.claude/rules/scanner-read-only.md` -- global rule enforcing read-only behavior for scanner agents.
- [ ] 19. Create `.claude/rules/report-template.md` -- global rule with the mandatory report structure.
- [ ] 20. Create `.claude/rules/anti-improvisation.md` -- global rule with DO NOT list and todo recitation requirement.
- [ ] 21. Create path-targeted rules for domain-specific constraints (e.g., `security.md` targeted to `src/siopv/infrastructure/**`).

### Phase F: Validation and Testing (est. 2-3 files)

- [ ] 22. Test PreToolUse hook: spawn a test agent and verify it cannot execute write commands via Bash.
- [ ] 23. Test PostToolUse hook: verify linter runs after file edits.
- [ ] 24. Test agent definition loading: spawn each agent template and verify it receives only its body as system prompt.
- [ ] 25. Test report template compliance: verify agents produce reports matching the mandatory structure.

### Phase G: Stage Execution (operational, no new files)

- [ ] 26. Execute STAGE-1: Spawn orchestrator, run rounds, collect reports, human checkpoints.
- [ ] 27. Execute STAGE-2: Spawn orchestrator, run rounds, collect reports, human checkpoints.
- [ ] 28. Execute STAGE-3: Spawn orchestrator, run rounds, collect reports, human checkpoints.
- [ ] 29. Execute STAGE-4: Spawn orchestrator, run rounds, collect reports, human checkpoints.
- [ ] 30. Design STAGE-5 based on findings from STAGE-1 through STAGE-4.
- [ ] 31. Execute STAGE-5: Apply corrections and fixes.

### Phase H: Final Audit Record (est. 1 file)

- [ ] 32. Produce final consolidated audit report covering all 5 stages with cross-references to research findings, design decisions, and implementation evidence.

---

## 21. SUMMARY AND QUICK-REFERENCE TABLES

### 21.1 Key Takeaways (Summary Rules)

1. **Prompts are requests, hooks are laws** -- for anything that MUST happen, use hooks/tool restrictions.
2. **150 instructions is the ceiling** -- prune ruthlessly.
3. **Lost-in-the-middle is real** -- put critical rules at start and end.
4. **Tool restrictions are the most reliable guardrail** -- deterministic prevention.
5. **Per-step constraints beat uniform freedom levels** -- match constraint type to step type.
6. **Fresh context beats accumulated context** -- use /clear between tasks.
7. **Verification is the highest-leverage practice** -- give Claude ways to check its own work.
8. **Personas leak beyond specification** -- explicitly state what agents should NOT do.

### 21.2 Guardrail Tier Decision Matrix

| Requirement | Tier 1 (Prompt) | Tier 2 (Tool Restriction) | Tier 3 (Hook) |
|-------------|-----------------|---------------------------|----------------|
| Guidance/preferences | Primary | -- | -- |
| Code style | Primary | -- | PostToolUse linter |
| Read-only enforcement | Supporting | Primary | PreToolUse blocking |
| Dangerous command blocking | -- | -- | Primary (PreToolUse) |
| Output format | Primary | -- | PostToolUse validation |
| Security-critical rules | Supporting | Where applicable | Primary |

### 21.3 Agent Body Structure Checklist

- [ ] Identity section (role + domain)
- [ ] Mandate section (ONE task, specific deliverable)
- [ ] Workflow section (numbered steps with constraint types)
- [ ] Boundaries section (NEVER statements, 3-5 DO NOT items, escalation clause)
- [ ] Output Format section (exact template)
- [ ] Verification section (pre-completion checklist, self-verification step)
- [ ] Under 200 lines total
- [ ] Critical rules at TOP and repeated at BOTTOM
- [ ] 3-5 canonical examples included

### 21.4 Size Limits

| Component | Maximum | Notes |
|-----------|---------|-------|
| Agent body | 200 lines | Front-load critical rules |
| CLAUDE.md | 300 lines | Shorter is better |
| Total instructions (all contexts) | 150 | Beyond this, compliance drops for ALL rules |
| Critical rules in prompts | 20 | The rest go to hooks/tool restrictions |
| Sub-agent return to orchestrator | 1,000-2,000 tokens | Condensed summaries only |
| Parallel agents per batch | 4-6 | Token budget management limit |

### 21.5 Source Checkpoint Counts

| Source File | Categories | Checkpoints |
|-------------|-----------|-------------|
| 003 (Claude Code Report) | 8 | 58 |
| 004 (LLM Behavioral Report) | 10 | 74 |
| **This merged record** | **21** | **132 (deduplicated)** |

---

**Total estimated new files (implementation):** 20-25
**Total implementation checklist items:** 32
**Total design decisions:** 15 (DD-001 through DD-015)
**Research checkpoints referenced:** 132 (58 from Report 001 + 74 from Report 002)

---

**END OF DEFINITIVE MERGED RECORD**
