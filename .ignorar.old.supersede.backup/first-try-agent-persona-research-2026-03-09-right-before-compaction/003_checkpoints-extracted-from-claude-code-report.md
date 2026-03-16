# Checkpoints Extracted from Claude Code Agent Persona Report (001)

Source: `001_claude-code-agent-persona-guardrails-behavioral-control.md`
Extraction date: 2026-03-09

---

## Category 1: AGENT DEFINITION STRUCTURE

### CP-ADS-01: Use Markdown + YAML frontmatter format
- **Technique:** Agent definitions are `.md` files with YAML frontmatter in `.claude/agents/`. Frontmatter = metadata/constraints. Markdown body = system prompt.
- **Why:** Subagents receive ONLY this system prompt plus basic environment details (working directory), NOT the full Claude Code system prompt. The body IS the entire behavioral context.
- **How:** Create `.md` files in `.claude/agents/` (project, priority 2) or `~/.claude/agents/` (user, priority 3). Use `--agents` CLI flag for session-only (priority 1). Plugin `agents/` dir is priority 4.
- **Source:** Section 1 — Agent Definition File Structure

### CP-ADS-02: Enforce four-field minimum in frontmatter
- **Technique:** Every agent must have at minimum: `name`, `description`, `tools`, and body content. Add `model`, `memory`, `hooks`, `maxTurns` only when needed.
- **Why:** These four fields establish identity, delegation routing, capability boundaries, and behavioral instructions — the irreducible minimum for controlled agent behavior.
- **How:** Audit every agent file. Reject any agent missing `name`, `description`, `tools`, or having an empty body.
- **Source:** Section 9A — Recommendation #2

### CP-ADS-03: Understand all 14 frontmatter fields
- **Technique:** Full field inventory: `name` (required, lowercase+hyphens), `description` (required, used for auto-delegation), `tools` (allowlist), `disallowedTools` (denylist), `model` (sonnet/opus/haiku/inherit), `permissionMode` (default/acceptEdits/dontAsk/bypassPermissions/plan), `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory` (user/project/local), `background`, `isolation` (worktree).
- **Why:** Each field controls a different behavioral dimension. Missing a field means relying on defaults which may not match intent.
- **How:** Maintain a checklist of all 14 fields. For each agent, explicitly decide the value of every field (even if the decision is "omit/use default").
- **Source:** Section 1 — Supported Frontmatter Fields table

### CP-ADS-04: Use description field for delegation routing
- **Technique:** The `description` field is used by Claude for auto-delegation decisions — it determines WHEN the agent gets invoked.
- **Why:** A vague description means Claude may not delegate to the agent when it should, or may delegate inappropriately.
- **How:** Write descriptions that specify the exact trigger conditions: "Expert code review specialist. Use immediately after writing or modifying code." NOT "Reviews code."
- **Source:** Section 1 — Supported Frontmatter Fields, `description` row

### CP-ADS-05: Use tool restriction syntax correctly
- **Technique:** Allowlist: `tools: Read, Grep, Glob, Bash`. Denylist: `disallowedTools: Write, Edit`. Restrict subagent spawning: `tools: Agent(worker, researcher), Read, Bash`. Allow any subagent: `tools: Agent, Read, Bash`.
- **Why:** Syntax errors in tool restrictions silently fail, leaving the agent with full tool access.
- **How:** Validate tool restriction syntax in every agent file. Test by checking if the agent can use tools it shouldn't have.
- **Source:** Section 1 — Tool Restriction Syntax

### CP-ADS-06: Configure agent memory for institutional learning
- **Technique:** Set `memory: project` (or `user`/`local`) to give agents persistent cross-session learning. Agent gets a `MEMORY.md` file (first 200 lines injected at startup) with Read/Write/Edit auto-enabled.
- **Why:** Without memory, agents start from zero every session. With memory, agents like code-reviewer can learn recurring issues.
- **How:** Enable `memory: project` for agents that benefit from accumulated knowledge (code-reviewer, security-auditor). Memory directory: `.claude/agent-memory/<name>/` (project scope). Agent must curate MEMORY.md if it exceeds 200 lines.
- **Source:** Section 1 — Memory Configuration; Section 9D — Recommendation #4

### CP-ADS-07: CLI JSON agents for ephemeral sessions
- **Technique:** Use `--agents` CLI flag with JSON for session-only agents. `prompt` field in JSON is equivalent to markdown body.
- **Why:** Session-only agents (priority 1) override all file-based agents, useful for one-off tasks or experimentation without touching the project.
- **How:** `claude --agents '{"name": {"description": "...", "prompt": "...", "tools": [...], "model": "sonnet"}}'`
- **Source:** Section 1 — CLI-Defined Agents

---

## Category 2: PERSONA/BEHAVIORAL DESIGN

### CP-PBD-01: System prompt IS the persona — single surface
- **Technique:** The body of the agent definition IS the system prompt. The subagent receives ONLY this plus environment details — nothing from the parent conversation.
- **Why:** This means every behavioral instruction must be self-contained in the agent body. You cannot rely on context from the parent conversation or other loaded files.
- **How:** Write each agent body as if it were the only instructions the agent will ever see. Include all necessary context, rules, and workflow steps.
- **Source:** Section 2 — Core Principle

### CP-PBD-02: Pattern A — Role + Checklist
- **Technique:** Define role in first sentence, then numbered workflow steps, then a review checklist of specific items to check, then output format (priority-organized feedback).
- **Why:** Anthropic docs recommend this as the primary pattern. The checklist gives explicit verification criteria rather than vague "review for quality."
- **How:** Structure: (1) "You are a [role]." (2) "When invoked: 1. 2. 3." (3) "Checklist: - item - item" (4) "Provide feedback organized by: Critical / Warnings / Suggestions."
- **Source:** Section 2 — Pattern A (from Anthropic docs)

### CP-PBD-03: Pattern B — Domain Expert with Workflow
- **Technique:** Define expertise domain, then numbered sequential workflow from data gathering through resolution.
- **Why:** The sequential workflow prevents the agent from jumping to conclusions or skipping diagnostic steps.
- **How:** Structure: (1) "You are an expert [domain] specializing in [specific area]." (2) Numbered steps: capture → identify → isolate → implement → verify. (3) "Focus on [root principle], not [surface approach]."
- **Source:** Section 2 — Pattern B (from Anthropic docs)

### CP-PBD-04: Pattern C — Behavioral Boundaries with Scenario Handling
- **Technique:** Define rules for interaction, then explicit scenario-response mappings: "If [situation], then [exact response]."
- **Why:** Pre-scripted scenario responses prevent improvisation in sensitive situations. Claude follows the script instead of generating novel responses.
- **How:** List 3-5 interaction rules, then map common edge-case scenarios to specific responses using "If asked about X: [exact text]" format.
- **Source:** Section 2 — Pattern C (from Anthropic API docs)

### CP-PBD-05: Pattern D — Cognitive Personas (SuperClaude)
- **Technique:** Personas are `.md` files containing domain-specific expertise, behavioral patterns, and problem-solving approaches. Invocable via `@agent-security` syntax. 16 specialist agents that can delegate to each other.
- **Why:** Creates a network of specialized expertise where each agent has deep domain knowledge rather than broad shallow knowledge.
- **How:** Create separate `.md` files per domain (security, frontend, backend, etc.). Each contains domain expertise + behavioral patterns + problem-solving approaches.
- **Source:** Section 2 — Pattern D (SuperClaude Framework)

### CP-PBD-06: Four elements of effective persona
- **Technique:** (1) Set role in system prompt — even a single sentence makes a difference. (2) Provide detailed personality info — background, traits, quirks help the model generalize. (3) Prepare for scenarios — list common situations and expected responses. (4) Constrain with examples — show desired output format, this "trains" understanding better than abstract instructions.
- **Why:** Anthropic's official guidance on what makes personas effective. Each element improves compliance measurably.
- **How:** Audit every agent body for all four elements. Add any missing elements.
- **Source:** Section 2 — What Makes Persona Effective (Anthropic official guidance)

### CP-PBD-07: Anti-pattern — persona trait leakage
- **Technique:** When Claude adopts a persona, it infers personality traits that drive OTHER behaviors beyond those specified. A persona designed for one purpose can leak into unintended behavioral dimensions.
- **Why:** Anthropic's Persona Selection Model (2026) research finding. A "friendly helper" persona may become inappropriately casual in security audits.
- **How:** Mitigation: Be explicit about what the persona should NOT do. Add explicit NOT instructions for every behavioral dimension that matters.
- **Source:** Section 2 — Anti-Pattern: Over-Relying on Persona (Anthropic Persona Selection Model 2026)

### CP-PBD-08: Recommended SIOPV agent body structure
- **Technique:** Six-section template: (1) Identity — "You are a [ROLE] specializing in [DOMAIN]." (2) Mandate — "Your ONE task: [specific deliverable]." (3) Workflow — numbered steps with per-step constraint types. (4) Boundaries — NEVER statements + edge case handling. (5) Output Format — exact template structure. (6) Verification — pre-completion checklist.
- **Why:** Combines all proven patterns into a single standardized structure. Each section addresses a different failure mode.
- **How:** Refactor all agent definitions to follow this exact six-section structure. Reject agent definitions missing any section.
- **Source:** Section 9B — Persona Design Pattern for SIOPV Agents

---

## Category 3: GUARDRAILS AND ENFORCEMENT

### CP-GAE-01: Prompts are requests, hooks are laws
- **Technique:** Rules in prompts are probabilistic requests (Claude may ignore them). Hooks in code are deterministic laws (always execute, cannot be overridden). Claude can read and recite instructions without following them.
- **Why:** This is the single most important finding of the research. The distinction between knowledge and execution is real and documented.
- **How:** For anything that MUST happen, implement it as a hook or tool restriction. For preferences and guidance, use prompts. Never rely on prompts alone for safety-critical rules.
- **Source:** Section 3 — The Fundamental Insight

### CP-GAE-02: The 150-instruction ceiling
- **Technique:** Instruction compliance decreases uniformly as instruction count increases. Frontier models max out at ~150-200 instructions. Beyond this threshold, more rules correlate with WORSE overall compliance across ALL rules.
- **Why:** Academic research (Jaroslawicz et al., 2025). Going beyond 150 instructions is counterproductive — it degrades compliance on the rules you already had.
- **How:** Practical recommendation: Keep the 20 most critical rules in prompts. Handle the rest via hooks, tool restrictions, or remove them entirely. Count total instructions across all loaded contexts (CLAUDE.md + rules + agent body + skills).
- **Source:** Section 3 — The 150-Instruction Ceiling (Jaroslawicz et al., 2025)

### CP-GAE-03: Three-tier guardrails framework
- **Technique:** Tier 1: Prompt-based (probabilistic, ~80% compliance at best, degrades with volume) — for guidance, preferences, soft constraints. Tier 2: Tool restrictions (deterministic, 100% compliance) — tools simply don't exist for the agent. Tier 3: Hooks (deterministic, 100% compliance) — code runs regardless of Claude's reasoning.
- **Why:** Layering all three tiers provides defense in depth. Each tier handles a different class of constraints at a different reliability level.
- **How:** For every rule, classify it into the appropriate tier. Escalate any rule that has been violated from Tier 1 to Tier 2 or 3. Never leave safety-critical rules in Tier 1 alone.
- **Source:** Section 3 — Three-Tier Guardrails Framework

### CP-GAE-04: Tier 1 compliance is ~80% at best
- **Technique:** Prompt-based instructions (system prompt, CLAUDE.md, rules files) achieve approximately 80% compliance under ideal conditions. Compliance degrades further with: high instruction volume, long sessions, complex tasks.
- **Why:** Sets realistic expectations. If you need 100% compliance, prompts are insufficient by definition.
- **How:** Accept ~80% as the ceiling for prompt-based rules. For the remaining 20%, implement hooks or tool restrictions. Monitor prompt-based rule compliance and escalate frequently-violated rules.
- **Source:** Section 3 — Tier 1 description

### CP-GAE-05: Guardrails Ladder (Adaline Labs)
- **Technique:** Three escalation levels: Tier 1 = Read-only and analysis (inspect, explain, plan — cannot write or run risky commands). Tier 2 = Controlled changes in scoped directories (edit only within approved paths). Tier 3 = PR-ready changes with enforced checks (produce PR candidates only after automated checks pass).
- **Why:** Provides a graduated approach to agent capability. Start agents at the lowest tier needed for their task.
- **How:** Assign each agent to a tier. Implement the tier's restrictions via tool allowlists and hooks. Verify agents cannot exceed their tier.
- **Source:** Section 3 — Guardrails Ladder (from Adaline Labs)

### CP-GAE-06: Deterministic vs probabilistic control examples
- **Technique:** Probabilistic: "Don't edit .env files" in CLAUDE.md — Claude may ignore this under pressure or when context is long, subject to lost-in-the-middle degradation. Deterministic: PreToolUse hook that exits with code 2 when .env is targeted — ALWAYS runs, ALWAYS blocks, regardless of Claude's reasoning, cannot be overridden by the model.
- **Why:** Concrete illustration of the gap between Tier 1 and Tier 3. The same rule expressed in two different ways has dramatically different reliability.
- **How:** For every critical rule currently in CLAUDE.md or rules files, ask: "What happens if Claude ignores this?" If the answer is unacceptable, implement a deterministic equivalent.
- **Source:** Section 3 — Deterministic vs Probabilistic Control

### CP-GAE-07: Per-step constraint types (4 types)
- **Technique:** Four constraint types: (1) Procedural (HOW) — sequential steps, divergence acceptable. (2) Criteria (WHAT) — quality judgment, replace "how" with explicit standards. (3) Template — fixed output structure, flexible content. (4) Guardrail — boundaries by prohibition, what must NEVER happen.
- **Why:** Different steps have different requirements. Applying one freedom level to an entire workflow either over-constrains creative steps or under-constrains critical steps.
- **How:** For each step in an agent's workflow, assign one of the four constraint types. Document the constraint type alongside the step.
- **Source:** Section 3 — Per-Step Constraint Design; Section 6 — Technique 1

### CP-GAE-08: SIOPV-specific agent tool assignments
- **Technique:** Concrete tool assignments per agent: `security-auditor` = Read-only + Bash, PreToolUse hook blocks write commands. `code-implementer` = All tools, PostToolUse runs ruff/mypy after every edit. `test-generator` = All tools, PostToolUse runs pytest after test file creation. `hallucination-detector` = Read-only only, NO Bash. `best-practices-enforcer` = Read-only + Bash for running linters.
- **Why:** Each agent needs exactly the tools for its task and nothing more. The hallucination-detector having no Bash prevents it from running arbitrary commands. The security-auditor having write-blocked Bash prevents it from modifying code.
- **How:** Implement these exact tool assignments in each agent's frontmatter. Test by attempting tool usage that should be blocked.
- **Source:** Section 9C — Guardrails Strategy for SIOPV

### CP-GAE-09: Layer all three tiers simultaneously
- **Technique:** For each agent, implement: (1) Prompt-based: persona, workflow steps, output format in agent body. (2) Tool restrictions: remove unneeded tools in frontmatter. (3) Hooks: PreToolUse for safety-critical rules in frontmatter or settings.json.
- **Why:** Defense in depth. If the prompt fails (20% of the time), tool restrictions catch the action. If a new tool somehow bypasses restrictions, hooks catch it.
- **How:** For every agent, verify that all three tiers are present. Create a matrix: agent x tier x what's implemented.
- **Source:** Section 9C — Guardrails Strategy

---

## Category 4: HOOKS CONFIGURATION

### CP-HCF-01: 16 hook events inventory (March 2026)
- **Technique:** Complete hook event list: `SessionStart` (startup/resume/clear/compact), `UserPromptSubmit`, `PreToolUse` (tool name matcher, CAN BLOCK), `PermissionRequest` (tool name), `PostToolUse` (tool name), `PostToolUseFailure` (tool name), `Notification`, `SubagentStart` (agent type), `SubagentStop` (agent type), `Stop`, `TeammateIdle`, `TaskCompleted`, `InstructionsLoaded`, `ConfigChange`, `PreCompact` (manual/auto), `SessionEnd`, `WorktreeCreate`/`WorktreeRemove`.
- **Why:** Knowing the complete set prevents missing enforcement opportunities. Many teams only use PreToolUse and miss SubagentStart, Stop, and other events.
- **How:** Map each hook event to potential use cases for the project. Implement hooks for every event where enforcement adds value.
- **Source:** Section 4 — All Hook Events table

### CP-HCF-02: PreToolUse is the ONLY blocking hook
- **Technique:** PreToolUse is the ONLY hook that can block actions. Two blocking mechanisms: (1) Exit code 2 = block. (2) JSON output with `permissionDecision: "deny"`.
- **Why:** If you need to PREVENT an action, PreToolUse is your only option. All other hooks are observational or reactive.
- **How:** Every safety-critical rule that must prevent an action needs a PreToolUse hook. PostToolUse can only react after the action has already happened.
- **Source:** Section 4 — PreToolUse: The Critical Hook

### CP-HCF-03: Three handler types for hooks
- **Technique:** (1) `command` — shell script, deterministic, best for security rules. (2) `prompt` — LLM judgment call, for nuanced decisions. (3) `agent` — full codebase state verification, most expensive but most capable.
- **Why:** Different enforcement scenarios need different handler types. Using `command` for everything misses nuanced cases. Using `agent` for everything is too expensive.
- **How:** Use `command` for security rules (block patterns, validate SQL). Use `prompt` for context-dependent decisions. Use `agent` only for complex verification requiring full codebase awareness.
- **Source:** Section 4 — Three Handler Types

### CP-HCF-04: PreToolUse exit code blocking pattern
- **Technique:** Bash script reads `$INPUT` from stdin via `cat`, extracts tool_input via `jq`, checks for dangerous patterns with grep, exits 0 to allow, exits 2 to block. Error message via stderr (`>&2`).
- **Why:** The exit code pattern is simpler and more reliable for straightforward block/allow decisions.
- **How:** Implementation: `INPUT=$(cat)` → `COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')` → pattern match → `exit 2` to block, `exit 0` to allow.
- **Source:** Section 4 — Exit code based example

### CP-HCF-05: PreToolUse JSON output blocking pattern
- **Technique:** Output JSON with `hookSpecificOutput.hookEventName: "PreToolUse"`, `permissionDecision: "deny"`, `permissionDecisionReason: "..."` using `jq -n`.
- **Why:** JSON pattern allows providing structured reason for the block, which Claude can use to explain to the user and adjust its approach.
- **How:** `jq -n '{ hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: "Destructive command blocked" } }'`
- **Source:** Section 4 — JSON output based example

### CP-HCF-06: Hook configuration in agent frontmatter
- **Technique:** Hooks can be scoped to a specific agent via YAML frontmatter under `hooks:` key, with `PreToolUse`/`PostToolUse` arrays, each with `matcher` (tool name or pipe-separated names) and `hooks` array of `type`+`command` entries.
- **Why:** Agent-scoped hooks only run when that specific agent is active, avoiding interference with other agents.
- **How:** Add hooks directly to agent frontmatter YAML. Matcher supports pipe-separated tool names: `"Edit|Write"`. Each hook entry needs `type: command` and `command: "./path/to/script.sh"`.
- **Source:** Section 4 — Hook Configuration in Agent Frontmatter

### CP-HCF-07: Six hook configuration locations (priority order)
- **Technique:** (1) `~/.claude/settings.json` — all projects. (2) `.claude/settings.json` — single project, committable. (3) `.claude/settings.local.json` — single project, gitignored. (4) Managed policy settings — organization-wide. (5) Plugin `hooks/hooks.json` — when plugin enabled. (6) Agent frontmatter — while agent is active.
- **Why:** Hooks at different scopes serve different purposes. Organization-wide for compliance, project-level for project rules, agent-level for agent-specific restrictions.
- **How:** Place hooks at the narrowest applicable scope. Project-wide hooks in `.claude/settings.json`. Agent-specific hooks in frontmatter. User-wide hooks in `~/.claude/settings.json`.
- **Source:** Section 4 — Hook Configuration Locations table

### CP-HCF-08: What hooks CAN enforce (8 capabilities)
- **Technique:** (1) Block dangerous commands (PreToolUse + exit 2). (2) Validate SQL queries (block writes, allow SELECT). (3) Protect files (block Write/Edit to specific paths). (4) Auto-format (PostToolUse runs linter after every edit). (5) Run tests (PostToolUse after changes). (6) Modify tool inputs (PreToolUse v2.0.10+, rewrite parameters: add dry-run flags, redact secrets). (7) Enforce conventions (PostToolUse checks naming/structure). (8) Setup/teardown (SubagentStart/SubagentStop for resource management).
- **Why:** Understanding the full capability set prevents under-utilization of the hooks system.
- **How:** For each capability, evaluate whether the project needs it. Implement hooks for all applicable capabilities.
- **Source:** Section 4 — What Hooks CAN Enforce

### CP-HCF-09: What hooks CANNOT enforce (5 limitations)
- **Technique:** Hooks cannot enforce: (1) Reasoning quality — hooks see actions, not thought processes. (2) Instruction recall — can't force Claude to remember something from its prompt. (3) Planning decisions — can't control WHICH tool Claude decides to use. (4) Output quality — can validate format but not semantic correctness of natural language. (5) Cross-turn consistency — each hook invocation is stateless.
- **Why:** Knowing limitations prevents false confidence. If you need these guarantees, hooks are insufficient and you need complementary approaches (verification agents, multi-model review).
- **How:** For each limitation, identify whether the project requires that guarantee. If yes, implement a complementary approach (e.g., verification agents for reasoning quality, output templates for format).
- **Source:** Section 4 — What Hooks CANNOT Enforce

### CP-HCF-10: PreToolUse can modify tool inputs (v2.0.10+)
- **Technique:** As of v2.0.10, PreToolUse hooks can rewrite tool parameters before execution. Use cases: add dry-run flags, redact secrets from commands.
- **Why:** Input modification is a powerful capability that goes beyond simple block/allow. It allows enforcing safety without blocking the action entirely.
- **How:** Hook outputs modified `tool_input` in its JSON response. Example: add `--dry-run` to destructive commands, strip secrets from logged commands.
- **Source:** Section 4 — What Hooks CAN Enforce, bullet 6

### CP-HCF-11: SIOPV hook enforcement configuration
- **Technique:** Specific JSON configuration: PreToolUse matcher "Bash" → `.claude/hooks/block-dangerous-commands.sh`. PostToolUse matcher "Edit|Write" → `.claude/hooks/run-linter.sh`.
- **Why:** Provides the exact hook configuration for the SIOPV project.
- **How:** Add the JSON block to `.claude/settings.json` under `hooks` key. Create the two referenced scripts.
- **Source:** Section 9F — Hook Enforcement for SIOPV

### CP-HCF-12: SubagentStart/SubagentStop for resource management
- **Technique:** Use `SubagentStart` and `SubagentStop` hooks to manage resources (e.g., spin up/tear down test databases, create/clean temp directories).
- **Why:** Agents may need environmental setup that the agent itself shouldn't control (separation of concerns, security).
- **How:** Implement SubagentStart hook to prepare the environment. SubagentStop hook to clean up. Agent operates in the prepared environment without needing setup/teardown tools.
- **Source:** Section 4 — What Hooks CAN Enforce, bullet 8

---

## Category 5: RULES FILES

### CP-RUL-01: Directory structure with subdirectories
- **Technique:** Rules stored in `.claude/rules/` as standalone Markdown files with optional YAML frontmatter. Files are discovered recursively, supporting subdirectories for organization.
- **Why:** Recursive discovery allows logical grouping (e.g., `frontend/react.md`, `api/conventions.md`) without sacrificing discoverability.
- **How:** Organize rules into subdirectories by domain. Example: `.claude/rules/code-style.md`, `.claude/rules/security.md`, `.claude/rules/frontend/react.md`.
- **Source:** Section 5 — Directory Structure

### CP-RUL-02: Path-targeted rules with YAML frontmatter
- **Technique:** Add `paths:` YAML frontmatter with glob patterns (e.g., `"src/api/**/*.ts"`) to activate rules only when Claude works on matching files.
- **Why:** Reduces instruction volume by loading rules only when relevant, helping stay under the 150-instruction ceiling.
- **How:** Add `---\npaths:\n  - "pattern"\n---` frontmatter. Rule activates only when Claude reads matching files.
- **Source:** Section 5 — Path-Targeted Rules

### CP-RUL-03: Known bug — path rules only trigger on READ
- **Technique:** Path-based rules only inject into context when Claude READS a matching file, NOT when writing/creating files. Rules targeting file creation conventions are silently ignored for new files.
- **Why:** This is a known bug. If you rely on path-targeted rules for creation conventions, they will not fire when creating new files.
- **How:** For rules that must apply during file creation, make them global (no paths) or implement via hooks instead. Never rely on path-targeted rules alone for new file conventions.
- **Source:** Section 5 — Important caveat (known bug)

### CP-RUL-04: Rules loading behavior
- **Technique:** Rules without `paths` = global (loaded at session start). Rules with `paths` = conditional (loaded on file match). Rules load with same priority as CLAUDE.md. `InstructionsLoaded` hook event fires when rules are loaded.
- **Why:** Understanding loading behavior prevents rules from being absent when needed. The InstructionsLoaded hook can be used to verify rules are actually loading.
- **How:** For critical rules, make them global. For domain-specific rules, use path targeting. Use InstructionsLoaded hook to log which rules load.
- **Source:** Section 5 — How Rules Load

### CP-RUL-05: Rules vs CLAUDE.md vs Skills vs Agent body
- **Technique:** Four instruction mechanisms: CLAUDE.md (every session, broad project instructions). `.claude/rules/*.md` (session start or on file match, modular scoped policies). Skills (on demand, domain knowledge/workflows). Agent body (when spawned, agent-specific system prompt).
- **Why:** Each mechanism has different loading timing and scope. Putting the wrong instruction in the wrong mechanism causes it to be absent or over-present.
- **How:** Classify every instruction by scope and timing. Place it in the correct mechanism. Audit for misplacements.
- **Source:** Section 5 — Rules vs CLAUDE.md vs Skills table

### CP-RUL-06: Five rules for effective rule writing
- **Technique:** (1) Keep under 150 instructions total across all loaded contexts. (2) Be specific and measurable: "Calculate ROI on a 3-year TCO basis" beats "Calculate ROI". (3) Use emphasis markers: `IMPORTANT`, `YOU MUST`, `CRITICAL` improve adherence. (4) Delete rules Claude already follows — if removing a rule doesn't change behavior, it wastes attention. (5) Test rules by observation — watch whether behavior actually shifts.
- **Why:** Community research findings on what makes rules effective. Each point is empirically validated.
- **How:** Audit all rules against these five criteria. Count total instructions. Remove any rule that fails criteria 4. Add emphasis markers to the 20 most critical rules.
- **Source:** Section 5 — Effective Rule Writing

### CP-RUL-07: What rules CANNOT do (5 limitations)
- **Technique:** Rules are advisory, not enforced. Claude can read and recite rules without following them. Compliance degrades as total instruction volume increases. Long sessions cause rule "forgetting" due to context dilution. Rules may be deemed "not relevant" by the model and ignored (Claude's system prompt says instructions "may or may not be relevant").
- **Why:** Sets realistic expectations for prompt-based rules. The "may or may not be relevant" clause in Claude's system prompt explicitly allows the model to ignore rules it deems irrelevant.
- **How:** Accept these limitations. For any rule where non-compliance is unacceptable, implement a deterministic alternative (hook or tool restriction).
- **Source:** Section 5 — What Rules CANNOT Do

### CP-RUL-08: Use path-targeted rules for SIOPV domains
- **Technique:** Use `.claude/rules/` with path targeting for domain-specific rules. Example: `security.md` targeted to `src/siopv/infrastructure/` files.
- **Why:** SIOPV has distinct domains (security, DLP, orchestration, DI) that need different rules. Path targeting keeps instruction count low per context.
- **How:** Create rules files per domain: `security.md` (paths: `src/siopv/infrastructure/**`), `orchestration.md` (paths: `src/siopv/application/orchestration/**`), etc.
- **Source:** Section 9D — Context Management, Recommendation #2

---

## Category 6: ANTI-IMPROVISATION

### CP-ANT-01: Per-step constraint design
- **Technique:** Instead of one freedom level for an entire workflow, assign constraint type per step: Data collection = Procedural ("Run these 3 commands in order"). Analysis = Criteria ("Evaluate on these 3 axes: X, Y, Z"). Reporting = Template ("Output must follow this exact structure"). Safety checks = Guardrail ("NEVER modify files outside src/").
- **Why:** Different steps need different constraint types. One uniform freedom level either over-constrains creative steps or under-constrains critical steps.
- **How:** For each agent workflow, annotate every step with its constraint type. Implement the constraint accordingly.
- **Source:** Section 6 — Technique 1

### CP-ANT-02: Todo list recitation for context anchoring
- **Technique:** Agent constantly rewrites a todo list after each step: `[x] Completed` / `[ ] Remaining` / `Current focus: [step]`. This pushes the global plan into the END of the context window.
- **Why:** Combats lost-in-the-middle degradation. The most recent content gets highest attention. By rewriting the plan, it stays in the high-attention zone.
- **How:** Add to every agent body: "After each step, update your todo list with completed steps, remaining steps, and current focus."
- **Source:** Section 6 — Technique 2

### CP-ANT-03: Fresh context windows between tasks
- **Technique:** Use `/clear` between unrelated tasks. A clean session with a better prompt almost always outperforms a long session with accumulated corrections. After two failed corrections in one session, start fresh.
- **Why:** Context accumulation degrades instruction compliance. A fresh start is more effective than accumulated corrections.
- **How:** Implement as a practice: after two failed attempts to correct an agent's behavior, `/clear` and start over with improved instructions rather than adding more corrections.
- **Source:** Section 6 — Technique 3

### CP-ANT-04: Skills as instruction anchors
- **Technique:** Skills provide step-by-step procedures that Claude follows rigidly. Without a skill, Claude improvises. With a skill, it follows the defined sequence.
- **Why:** Example: Without a TDD skill, "write tests first" produces inconsistent results. With the skill installed, it follows Red-Green-Refactor every time because the skill explicitly defines each step.
- **How:** For any workflow where Claude improvises despite instructions, convert the workflow into a skill with explicit step-by-step procedures.
- **Source:** Section 6 — Technique 4

### CP-ANT-05: Escalation design for constraint flexibility
- **Technique:** Build flexibility into constraints: "If these constraints don't fit, propose alternatives with reasoning." This prevents agents from either blindly following inappropriate rules OR ignoring them silently.
- **Why:** Rigid constraints without escalation paths cause agents to either break rules silently or produce suboptimal results while technically complying.
- **How:** Add an escalation clause to every agent's Boundaries section: "If you encounter a situation where these constraints are inappropriate, report it as ESCALATION with your reasoning rather than ignoring the constraint."
- **Source:** Section 6 — Technique 5

### CP-ANT-06: Verification loops — highest-leverage practice
- **Technique:** Give Claude ways to verify its own work: tests to run, screenshots to compare, expected outputs to validate, linter results to check.
- **Why:** Self-verification is the "single highest-leverage thing you can do" — Anthropic official best practices.
- **How:** Every agent body should include a Verification section with concrete checks. Code-implementer: run tests + linter. Security-auditor: verify findings with grep. Test-generator: run generated tests.
- **Source:** Section 6 — Technique 6 (Anthropic official best practices)

### CP-ANT-07: Scoped tool access — most reliable anti-improvisation
- **Technique:** Remove tools the agent doesn't need. An agent with only Read, Grep, Glob literally CANNOT improvise by editing files. Tool restrictions are the most reliable anti-improvisation mechanism because they're deterministic.
- **Why:** Deterministic prevention. An agent without the Write tool cannot create files regardless of how persuasive its reasoning is.
- **How:** For every agent, list the minimum tools needed for its task. Remove everything else. Default to read-only and add write tools only when the agent's mandate requires modification.
- **Source:** Section 6 — Technique 7

### CP-ANT-08: maxTurns limit to prevent runaway execution
- **Technique:** Set `maxTurns` in frontmatter to cap agentic turns. Prevents runaway exploration or infinite loops.
- **Why:** Without maxTurns, an agent can loop indefinitely, consuming tokens and time without producing results.
- **How:** Set `maxTurns` based on expected task complexity. Simple verification: 10-15 turns. Code implementation: 30-50 turns. Exploratory research: 20-30 turns. Adjust based on observation.
- **Source:** Section 6 — Technique 8

### CP-ANT-09: Explicit NOT instructions to counter persona leakage
- **Technique:** From Anthropic's persona research: Claude infers personality traits beyond what's specified. Explicitly state what the agent should NOT do.
- **Why:** A security auditor persona may infer "helpful" traits and start suggesting fixes instead of just reporting. Explicit NOT instructions prevent this.
- **How:** For every agent, add 3-5 DO NOT statements: "DO: Report vulnerabilities with severity ratings. DO NOT: Fix code, suggest implementations, or make edits. DO NOT: Speculate about business impact. DO NOT: Skip files because they 'look fine'."
- **Source:** Section 6 — Technique 9 (Anthropic persona research)

---

## Category 7: CONTEXT POSITIONING

### CP-CTX-01: Lost-in-the-middle is a fundamental limitation
- **Technique:** LLMs pay the most attention to tokens at the START and END of the context window. Information buried in the middle gets deprioritized. This is architectural, not a bug.
- **Why:** This means instruction placement matters as much as instruction content. A critical rule in the wrong position may be ignored.
- **How:** Audit the position of every critical instruction. Move critical rules to the start or end of wherever they appear.
- **Source:** Section 7 — The Lost-in-the-Middle Problem

### CP-CTX-02: Four-zone positioning hierarchy
- **Technique:** (1) System prompt = highest attention (agent body). (2) Start of conversation = high attention (first messages). (3) End of conversation = high attention (most recent messages, todo lists). (4) Middle of conversation = lowest attention (earlier non-boundary messages).
- **Why:** Each zone has different attention weight. Placing instructions in the wrong zone reduces their effectiveness.
- **How:** Critical behavioral instructions → agent body (Zone 1). Project conventions → CLAUDE.md loaded at session start (Zone 2). Current plan/progress → todo lists at end (Zone 3). Never put critical rules in long middle-of-conversation messages (Zone 4).
- **Source:** Section 7 — Positioning Hierarchy

### CP-CTX-03: Placement matrix for instruction types
- **Technique:** Agent body (system prompt) → core persona, critical rules, workflow steps (highest attention, loaded fresh each time). CLAUDE.md → project conventions, build commands (loaded early, high position). `.claude/rules/` → scoped policies (same priority as CLAUDE.md). Skills → domain knowledge, procedures (loaded on demand, enters at end = recent = high attention). Todo list → current plan, remaining steps (pushed to end = high attention).
- **Why:** Each mechanism enters the context at a different position. Skills and todo lists benefit from recency. Agent body benefits from structural priority.
- **How:** Place each instruction in the mechanism that gives it the best positioning for its importance level.
- **Source:** Section 7 — Practical Implications table

### CP-CTX-04: Keep agent body under 200 lines
- **Technique:** Shorter system prompts get more uniform attention. Recommended maximum: 200 lines for agent body. Within those 200 lines, front-load the 20 most critical rules.
- **Why:** Longer system prompts suffer from internal lost-in-the-middle. The 150-instruction ceiling applies within the agent body too.
- **How:** Audit every agent body for line count. If over 200 lines, move non-critical content to skills loaded on demand. Keep only the 20 most critical rules in the body.
- **Source:** Section 7 — Strategies for Maximum Attention, item 1; Section 9A — Recommendation #1

### CP-CTX-05: Front-load critical rules in agent body
- **Technique:** Put the most important instructions at the TOP of the agent body. Additionally, repeat the single most important rule at both the start AND end of the body.
- **Why:** Start and end get highest attention within any text block. Repetition at both positions ensures the rule survives lost-in-the-middle.
- **How:** Restructure every agent body: critical rules at top, mandate at top, workflow in middle, repeat the single most critical rule at the bottom of the body.
- **Source:** Section 7 — Strategies, items 2 and 5

### CP-CTX-06: Use emphasis markers for critical instructions
- **Technique:** `IMPORTANT`, `CRITICAL`, `YOU MUST` demonstrably improve adherence.
- **Why:** Empirically validated: emphasis markers increase the probability of compliance. Not a guarantee, but a measurable improvement.
- **How:** Add emphasis markers to the 20 most critical instructions. Use sparingly — overuse dilutes the effect (every instruction being "CRITICAL" means none are).
- **Source:** Section 7 — Strategies, item 3

### CP-CTX-07: Use structured format over prose
- **Technique:** Headers, bullet points, tables are more scannable than prose.
- **Why:** Structured format helps the model parse and locate specific instructions. Prose buries instructions in natural language that the model must decompose.
- **How:** Convert all prose instructions to structured format: headers for sections, bullet points for individual rules, tables for comparisons/mappings.
- **Source:** Section 7 — Strategies, item 4

### CP-CTX-08: Progressive disclosure via skills
- **Technique:** Keep base prompt minimal, load detailed knowledge via skills only when needed.
- **Why:** Reduces baseline instruction volume, staying under the 150-instruction ceiling. Skills enter at the end of context (recency) when needed.
- **How:** Move domain-specific knowledge out of agent bodies and CLAUDE.md into skills. Agent body contains only: identity, mandate, workflow skeleton, boundaries. Skills contain: detailed procedures, domain knowledge, reference material.
- **Source:** Section 7 — Strategies, item 6

### CP-CTX-09: Prune rules that don't change behavior
- **Technique:** Remove any instruction that doesn't change behavior when removed. Each line should pass the test: "Would removing this cause Claude to make mistakes?"
- **Why:** Every instruction competes for attention. Instructions that don't change behavior waste attention budget and push the total closer to the 150-instruction ceiling.
- **How:** Systematically test each rule by temporarily removing it and observing behavior. If no change, delete it permanently.
- **Source:** Section 7 — Strategies, item 7; CLAUDE.md Token Budget section

### CP-CTX-10: CLAUDE.md token budget — under 300 lines
- **Technique:** CLAUDE.md is loaded EVERY session. Recommended: under 300 lines. Shorter is better. Bloated CLAUDE.md files cause Claude to ignore actual instructions.
- **Why:** Consensus from community research. Bloated CLAUDE.md doesn't just waste tokens — it actively degrades compliance with all instructions including those in the CLAUDE.md itself.
- **How:** Audit CLAUDE.md line count. If over 300 lines, move content to rules files (path-targeted where possible) or skills. Keep only universally applicable instructions in CLAUDE.md.
- **Source:** Section 7 — CLAUDE.md Token Budget

### CP-CTX-11: Auto-compaction survival strategy
- **Technique:** Auto-compaction triggers at ~95% of 200K tokens. System prompt survives (structural). Early conversation messages get summarized and may lose nuance. Add compaction instructions in CLAUDE.md.
- **Why:** Without compaction instructions, critical context (modified file lists, architectural decisions) may be lost during summarization.
- **How:** Add to CLAUDE.md: "When compacting, always preserve: [list of critical context items]". Example from report: "the full list of modified files."
- **Source:** Section 7 — Auto-Compaction Impact

---

## Category 8: PRODUCTION PATTERNS

### CP-PRD-01: Trail of Bits — OS-level sandboxing + hooks
- **Technique:** Trail of Bits runs Claude Code in `--dangerously-skip-permissions` mode with OS-level sandboxing (Seatbelt on macOS, bubblewrap on Linux). Configuration: sandboxing + hooks + skills + agent-native design principle.
- **Why:** "Agents can achieve any outcome users can" — the security model shifts from restricting the agent to sandboxing the environment. This allows full agent capability within a safe boundary.
- **How:** Evaluate OS-level sandboxing for production deployment. Repository: `trailofbits/claude-code-config`.
- **Source:** Section 8 — Example 1 (Trail of Bits)

### CP-PRD-02: Security reviewer — opus model + read-only + line references
- **Technique:** Security reviewer agent: `model: opus`, `tools: Read, Grep, Glob, Bash`. Reviews for: injection vulnerabilities, auth flaws, secrets in code, insecure data handling. Must provide specific line references and suggested fixes.
- **Why:** Anthropic docs example. Using opus (most capable model) for security review. Read-only tools prevent the reviewer from modifying code.
- **How:** Implement this exact pattern for SIOPV's security-auditor. Verify tools are read-only. Verify output includes line references.
- **Source:** Section 8 — Example 2 (from Anthropic docs)

### CP-PRD-03: Database reader — hook-enforced read-only
- **Technique:** DB reader agent has `tools: Bash` only, with PreToolUse hook on "Bash" that validates queries are read-only. Agent body includes both positive instruction ("Execute SELECT queries") and negative instruction ("If asked to INSERT, UPDATE, DELETE, explain that you only have read access").
- **Why:** Dual enforcement: prompt tells the agent it's read-only (Tier 1), hook blocks write operations deterministically (Tier 3). The prompt-level instruction helps Claude explain denials gracefully.
- **How:** For any agent with restricted Bash access, implement both: prompt-level explanation of restrictions AND hook-level enforcement.
- **Source:** Section 8 — Example 3

### CP-PRD-04: Single responsibility per agent (VoltAgent pattern)
- **Technique:** 100+ specialized subagents, each with single responsibility, clear description, minimal tool set.
- **Why:** Single responsibility prevents scope creep and makes tool restriction trivial. An agent that does one thing needs few tools.
- **How:** Audit every agent for scope. If an agent does more than one thing, split it. Repository: `VoltAgent/awesome-claude-code-subagents`.
- **Source:** Section 8 — Example 4 (VoltAgent)

### CP-PRD-05: Adaline Labs — plan gate before implementation
- **Technique:** Four-step pattern: (1) Plan gate before implementation. (2) Subagent review after implementation. (3) Multi-model review for critical changes. (4) PR opened only when all checks pass.
- **Why:** Plan gate catches issues before code is written. Multi-model review catches issues one model might miss. Gate-before-commit prevents unverified code from entering the codebase.
- **How:** Implement plan gate: agent must produce and get approval for a plan before writing code. Implement multi-model review for critical changes.
- **Source:** Section 8 — Example 7 (Adaline Labs)

### CP-PRD-06: Captain Hook — intent-based policy enforcement
- **Technique:** Captain Hook evaluates the agent's intent at the exact moment it decides to act. Enforcement is deterministic, not advisory.
- **Why:** Intent-based enforcement catches dangerous actions before they happen, at the decision point rather than after execution.
- **How:** Evaluate Captain Hook for policy enforcement needs. Reference: `securityreview.ai/blog/captain-hook-ai-agent-policy-enforcement-for-claude`.
- **Source:** Section 8 — Example 6

### CP-PRD-07: Codacy — 5-minute deterministic guardrails
- **Technique:** Setup takes 5 minutes. Use PreToolUse hooks for security scanning, PostToolUse for validation. "Deterministic means always runs, always enforced."
- **Why:** Low setup cost removes excuses for not implementing guardrails. If it takes 5 minutes, every project should have it.
- **How:** Implement PreToolUse security scanning hook and PostToolUse validation hook as minimum baseline for every project.
- **Source:** Section 8 — Example 8 (Codacy)

### CP-PRD-08: Anti-drift for verification agents (4 techniques)
- **Technique:** (1) Template constraints on output — every verification agent has an exact report template. (2) Checklist in agent body — explicit items to check, not vague "review for quality." (3) Escalation clause — "If you cannot complete a check, report it as INCONCLUSIVE rather than skipping it." (4) Self-verification — "Before finalizing your report, verify that every section is filled and every file mentioned exists."
- **Why:** Verification agents are the last line of defense. If they drift, bad code passes through uncaught.
- **How:** Add all four techniques to every verification agent. Audit that each verification agent has: output template, explicit checklist, escalation clause, self-verification step.
- **Source:** Section 9E — Anti-Drift for Verification Agents

### CP-PRD-09: Seven key takeaways (summary rules)
- **Technique:** (1) Prompts are requests, hooks are laws — for anything that MUST happen, use hooks/tool restrictions. (2) 150 instructions is the ceiling — prune ruthlessly. (3) Lost-in-the-middle is real — put critical rules at start and end. (4) Tool restrictions are the most reliable guardrail. (5) Per-step constraints beat uniform freedom levels. (6) Fresh context beats accumulated context — use /clear between tasks. (7) Verification is the highest-leverage practice. (8) Personas leak beyond specification — explicitly state what agents should NOT do.
- **Why:** These are the distilled principles from the entire research. Each one is backed by evidence from the report.
- **How:** Use as a checklist for every agent design review. Every agent should satisfy all seven principles.
- **Source:** Section 9G — Key Takeaways

---

## CROSS-REFERENCE INDEX

| Checkpoint | Enforces Principle | Implementation Tier |
|------------|-------------------|-------------------|
| CP-GAE-01 | Prompts vs Hooks | Architecture |
| CP-GAE-02 | 150-instruction ceiling | Audit |
| CP-GAE-03 | Three-tier framework | Architecture |
| CP-ADS-05 | Tool restrictions | Tier 2 (deterministic) |
| CP-HCF-02 | PreToolUse blocking | Tier 3 (deterministic) |
| CP-ANT-07 | Scoped tool access | Tier 2 (deterministic) |
| CP-ANT-09 | Persona leakage prevention | Tier 1 (prompt) |
| CP-CTX-01 | Context positioning | Tier 1 (prompt) |
| CP-CTX-04 | Agent body size limit | Audit |
| CP-CTX-10 | CLAUDE.md size limit | Audit |
| CP-PRD-08 | Verification agent anti-drift | All tiers |

---

**Total checkpoints extracted: 58**
**Categories: 8**
**Source report sections covered: All 9 sections**
