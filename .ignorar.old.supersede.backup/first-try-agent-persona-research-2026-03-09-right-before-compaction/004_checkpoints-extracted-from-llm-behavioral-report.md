# Checkpoints Extracted from LLM Agent Behavioral Control & Guardrails Report

**Source:** `002_llm-agent-behavioral-control-guardrails-techniques.md`
**Extracted:** 2026-03-09
**Purpose:** Every actionable item, design decision, technique, and best practice converted into audit checkpoints.

---

## INSTRUCTION-FOLLOWING TECHNIQUES

### IF-01: System Prompt Right Altitude Balance
- **Technique:** System prompts must occupy a "Goldilocks zone" — specific enough to guide behavior, flexible enough to provide strong heuristics. No brittle if-else logic. No vague guidance that assumes shared context.
- **Why:** Overly specific prompts break on edge cases; overly vague prompts assume context the model does not have. Both cause drift and unreliable behavior.
- **How:** Audit every system prompt for: (a) no if-else chains with >3 branches, (b) no instructions that require unstated context, (c) every constraint has a concrete example or heuristic.
- **Source:** Anthropic, Section 1.1

### IF-02: Structural Organization with XML/Markdown Sections
- **Technique:** Use distinct sections with XML tags or Markdown headers (`<background_information>`, `<instructions>`, `## Tool guidance`, `## Output description`) to organize system prompts.
- **Why:** Structural organization helps models parse and prioritize different instruction types, reducing misinterpretation.
- **How:** Every system prompt and agent briefing must use either XML tags or Markdown headers to separate: background, instructions, tool guidance, output format, constraints.
- **Source:** Section 1.1

### IF-03: Direct Persona Assignment Over Imagination Framing
- **Technique:** "You are an X" outperforms "Imagine you are..." — direct persona assignment is empirically more effective.
- **Why:** Direct assignment creates stronger behavioral anchoring than hypothetical framing (LearnPrompting, 2025).
- **How:** Audit all agent prompts. Replace any "Imagine you are...", "Pretend to be...", "Act as if you were..." with direct "You are..." statements.
- **Source:** LearnPrompting 2025, Section 1.1

### IF-04: Minimal Viable Prompt Approach
- **Technique:** Start with minimal instructions using the best model, then add clarity based on observed failure modes rather than anticipating all edge cases.
- **Why:** Over-specified prompts are brittle and waste tokens. Iterative refinement based on actual failures produces more robust prompts.
- **How:** For new agents, start with a 5-10 line prompt. Log failure modes. Add constraints only for observed failures. Track prompt evolution in version control.
- **Source:** Anthropic, Section 1.1

### IF-05: Prompt Repetition for Attention Boost
- **Technique:** Repeating the input prompt (`<QUERY>` to `<QUERY><QUERY>`) improves performance for Gemini, GPT, Claude, and DeepSeek without increasing generated tokens or latency. Accuracy improvements of up to 67-76% on non-reasoning tasks.
- **Why:** Causal LLMs prevent past tokens from attending to future tokens. Repetition creates bidirectional attention patterns within the prompt, compensating for causal masking.
- **How:** Repeat critical instructions at the end of the context window. For non-negotiable rules, include them both in the system prompt AND appended after the final user message.
- **Source:** Leviathan et al., Google Research, arXiv 2512.14982 (Dec 2025), Section 1.2

### IF-06: Instructional Segment Embedding (ISE)
- **Technique:** Categorize instruction tokens by role: system instruction = 0, user prompt = 1, data input = 2. This structural differentiation helps models prioritize instruction tokens during processing.
- **Why:** Without segment classification, models treat all tokens with equal weight, diluting instruction adherence.
- **How:** When using fine-tuned models or custom architectures, implement ISE token classification. For API-based models, use the native system/user/assistant role separation rigorously — never mix instruction types within a single role message.
- **Source:** ICLR 2025, Section 1.3

### IF-07: Few-Shot Curation with Diverse Canonical Examples
- **Technique:** Use diverse, canonical examples rather than exhaustive edge-case lists. In-context learning from examples shapes behavior more reliably than verbose instructions.
- **Why:** Examples are "the pictures worth a thousand words" for LLMs. They demonstrate expected behavior more effectively than descriptions.
- **How:** For each agent, include 3-5 canonical examples covering the range of expected inputs/outputs. Prefer diversity over edge-case coverage. Review examples quarterly for staleness.
- **Source:** Section 1.4

### IF-08: Primacy and Recency Positioning of Critical Rules
- **Technique:** Instructions at the beginning and end of context receive the most attention (U-shaped attention curve). Performance drops >30% when key information sits in the middle vs. beginning/end.
- **Why:** The "lost-in-the-middle" effect is empirically proven — middle content is systematically underweighted by transformer attention mechanisms.
- **How:** (a) Place non-negotiable constraints at the very beginning (system prompt). (b) Repeat critical rules at the very end (before generation). (c) Never bury important constraints in the middle of long contexts. (d) Audit long prompts (>2000 tokens) for critical rules buried in the middle.
- **Source:** Section 1.5

---

## PERSONA/ROLE DEFINITION

### PR-01: Persona Controls Style Not Accuracy
- **Technique:** Vanilla prompting and vanilla prompting with static persona description perform very similarly on accuracy tasks. Persona does NOT reliably control factual accuracy, deep reasoning quality, or knowledge beyond training data.
- **Why:** Prevents over-reliance on persona as a quality control mechanism. Persona is for style/format/tone, not correctness.
- **How:** Never rely on persona alone for factual accuracy. Always pair persona with: (a) RAG/tool access for knowledge, (b) structured output for format, (c) validation for correctness. Document in agent design that persona controls: style, tone, format, vocabulary, behavioral constraints.
- **Source:** PromptHub 2025, Section 2.1

### PR-02: What Persona Effectively Controls
- **Technique:** Persona controls: style and tone, output format and structure, domain vocabulary usage, behavioral constraints (what the agent refuses to do).
- **Why:** Understanding persona's actual scope prevents misuse and sets correct expectations for agent behavior.
- **How:** In each agent definition, explicitly document which behaviors are persona-controlled (style, vocabulary, refusals) vs. which require other mechanisms (accuracy → validation, reasoning → chain-of-thought, knowledge → RAG).
- **Source:** Section 2.1

### PR-03: CrewAI Role-Goal-Backstory Pattern
- **Technique:** Three mandatory agent attributes: Role (professional identity — be specific: "Senior Python Security Auditor" not "Developer"), Goal (single, measurable objective per agent), Backstory (narrative context establishing WHY this agent exists).
- **Why:** Empirically successful pattern from production CrewAI deployments. Specialists outperform generalists.
- **How:** Every agent definition must include all three attributes. Audit for: (a) Role specificity (no generic titles), (b) Goal measurability (one clear objective), (c) Backstory relevance (explains unique perspective).
- **Source:** CrewAI docs, Section 2.2

### PR-04: 80/20 Rule — Tasks Over Agent Definitions
- **Technique:** 80% of effort should go into designing tasks, only 20% into defining agents.
- **Why:** Task design drives output quality more than agent persona refinement. Well-designed tasks compensate for simpler agent definitions, but not vice versa.
- **How:** For every new agent, spend 4x more time defining task structure, acceptance criteria, and output format than refining the agent's role/backstory. Track time split in planning docs.
- **Source:** CrewAI production experience, Section 2.2

### PR-05: Specialists Over Generalists
- **Technique:** Agents perform better with specialized roles. Design agents with distinct but complementary abilities. Each agent should have a clearly defined, non-overlapping purpose.
- **Why:** Specialization reduces ambiguity in decision-making and improves output quality for the specific domain.
- **How:** Audit agent definitions for overlap. If two agents share >30% of their responsibilities, merge or re-split them. No agent should handle more than one domain.
- **Source:** CrewAI production experience, Section 2.2

### PR-06: Constraint-Based Personas with MUST NOT Rules
- **Technique:** Define what the agent MUST NOT do alongside what it should do.
- **Why:** Negative constraints prevent scope creep and off-task behavior. Without explicit prohibitions, agents tend to expand their scope.
- **How:** Every agent definition must include a "MUST NOT" section listing at least 3 prohibited behaviors (e.g., "MUST NOT modify files outside the target directory", "MUST NOT make network calls", "MUST NOT approve its own output").
- **Source:** PLoP 2024, Section 2.3

### PR-07: Behavioral Templates for Fine-Grained Control
- **Technique:** Use `system_template`, `prompt_template`, `response_template` for fine-grained control over agent behavior at each stage.
- **Why:** Templates enforce consistent structure across all invocations, reducing variability in agent behavior.
- **How:** For agents with strict output requirements, define all three templates. System template sets identity, prompt template structures input, response template constrains output format.
- **Source:** PLoP 2024, Section 2.3

### PR-08: Reasoning Mode for Planning Agents
- **Technique:** Enable `reasoning: true` for agents needing planning and reflection before action.
- **Why:** Reasoning mode forces the model to plan before acting, reducing impulsive tool calls and improving decision quality.
- **How:** Enable reasoning mode for: orchestrators, code reviewers, security auditors, and any agent making multi-step decisions. Disable for simple extraction or formatting agents.
- **Source:** Section 2.3

---

## CONTEXT ROT AND ATTENTION DECAY

### CR-01: Three Mechanisms of Context Rot
- **Technique:** Context rot is driven by three mechanisms: (1) Lost-in-the-Middle Effect (U-shaped attention), (2) Attention Dilution at Scale (attention budget spread thinner), (3) Distractor Interference (irrelevant context actively degrades performance).
- **Why:** Understanding the mechanisms enables targeted mitigation. Distractor interference means adding irrelevant context is worse than having less context.
- **How:** (a) Minimize irrelevant content in agent contexts. (b) Prefer sub-agent delegation with clean context over passing everything to one agent. (c) Actively prune conversation history of tool outputs that are no longer relevant.
- **Source:** Chroma Research, Section 3.1

### CR-02: Measured Impact Thresholds
- **Technique:** Performance drops >30% when relevant information sits in the middle vs. beginning/end. Critical instructions buried 10,000+ tokens back are frequently "forgotten." Negative constraints (things NOT to do) are especially vulnerable to being ignored in long contexts.
- **Why:** These are empirically measured thresholds for context decay. They define when mitigation is mandatory.
- **How:** (a) For contexts >10,000 tokens, re-inject critical instructions. (b) Place all negative constraints in system prompt AND repeat at end. (c) Monitor context length per agent — flag any exceeding 50,000 tokens for review.
- **Source:** Section 3.2

### CR-03: Context Equilibria — Drift Is Controllable
- **Technique:** Multi-turn drift reaches stable, noise-limited equilibria rather than runaway decay. Simple reminder interventions reliably reduce divergence.
- **Why:** Drift is not inevitable runaway degradation — it is a controllable equilibrium phenomenon. This means periodic reminders are sufficient; continuous monitoring is not always necessary.
- **How:** Implement periodic reminder injection (every N turns or every N tokens) rather than continuous reinforcement. Tune the interval based on observed drift metrics.
- **Source:** arXiv 2510.07777 (Oct 2025), Section 3.3

### CR-04: KV-Cache Hit Rate as Primary Metric
- **Technique:** The KV-cache hit rate is the single most important metric for a production-stage AI agent. Cached input tokens cost $0.30/MTok vs. uncached $3/MTok (Claude Sonnet) — a 10x cost difference.
- **Why:** KV-cache efficiency directly affects both latency and cost in production.
- **How:** (a) Make context append-only (never modify previous content). (b) Avoid reordering actions or observations. (c) Ensure deterministic serialization (same data = same bytes). (d) Design tool names with consistent prefixes (e.g., `browser_*`, `shell_*`).
- **Source:** Manus AI, Section 3.4

### CR-05: Append-Only Context Design
- **Technique:** Context must be append-only — never modify or reorder previous content.
- **Why:** Modifying previous context invalidates the KV-cache, forcing recomputation of all tokens. This 10x cost increase is avoidable.
- **How:** (a) Never insert content into the middle of conversation history. (b) Never reorder messages. (c) Corrections should be appended as new messages, not edits to previous ones. (d) Tool results should be appended in execution order.
- **Source:** Manus AI, Section 3.4

### CR-06: Deterministic Serialization
- **Technique:** Ensure deterministic serialization — same data must produce same bytes every time.
- **Why:** Non-deterministic serialization (e.g., Python dict ordering, random UUIDs in keys) invalidates KV-cache prefixes even when semantic content is identical.
- **How:** (a) Use `json.dumps(data, sort_keys=True)` for all JSON serialization. (b) Use consistent key ordering in all state objects. (c) Avoid timestamps or random values in serialized prompts unless semantically necessary.
- **Source:** Manus AI, Section 3.4

---

## ANTI-DRIFT TECHNIQUES

### AD-01: Goal Persistence via todo.md Pattern
- **Technique:** The agent constantly rewrites a `todo.md` file, reciting its objectives and progress at the end of the context. This biases the model's attention toward the global plan.
- **Why:** Explicit, repeated goal reminders counteract agent drift. The todo.md pattern serves double duty: externalizes the plan (surviving compaction) AND biases attention toward the global goal (anti-drift).
- **How:** Every orchestrator and long-running agent must maintain a `todo.md` (or equivalent) file. Update it after every significant action. Read it back before making decisions. Include: current objective, completed steps, remaining steps, blockers.
- **Source:** Manus AI, Section 4.2.1

### AD-02: External Memory for Behavioral Stability
- **Technique:** Workflows using external memory show 21% higher behavioral stability than those relying solely on conversation history.
- **Why:** External memory provides "behavioral anchors" resistant to incremental drift — they exist outside the attention window and are re-loaded fresh each time.
- **How:** Implement external memory files for: (a) architectural decisions, (b) non-negotiable constraints, (c) accumulated findings, (d) phase state. Re-read these files at decision points rather than relying on conversation history.
- **Source:** Section 4.2.1

### AD-03: Runtime Reinforcement via Instruction Re-injection
- **Technique:** A callback pattern that intercepts LLM requests, generates a reinforcement block, and appends non-negotiable rules to the end of the prompt before the model processes it.
- **Why:** Rules at the end of context receive maximum attention (recency effect). Re-injection at runtime ensures rules are never lost to context growth.
- **How:** Implement a prompt middleware that: (a) timestamps each request for temporal awareness, (b) aggregates non-negotiable rules from config, (c) appends them after the user message and before generation. Apply to every LLM call, not just the first.
- **Source:** Section 4.2.2

### AD-04: Controlled Variation to Break Pattern Lock-In
- **Technique:** If context is full of similar past action-observation pairs, the model tends to follow that pattern even when suboptimal. Introduce structured variation: different serialization templates, alternate phrasing, minor formatting noise.
- **Why:** LLMs are excellent mimics — pattern lock-in causes the model to repeat suboptimal strategies simply because they dominate the context.
- **How:** (a) Vary tool output formatting slightly between invocations. (b) Use 2-3 alternate phrasing templates for recurring observations. (c) Rotate example orderings. (d) Monitor for repetitive action sequences as a lock-in signal.
- **Source:** Manus AI, Section 4.2.3

### AD-05: Episodic Memory Consolidation
- **Technique:** Summarize or prune context to avoid pattern accumulation. Preserve architectural decisions and critical details. Discard redundant outputs. Maintain a "living summary" updated over time, carrying last N turns in full plus a compact summary of everything older.
- **Why:** Pattern accumulation in long conversations creates both context rot and pattern lock-in. Consolidation keeps context focused and relevant.
- **How:** (a) After every 10-20 tool calls, consolidate: summarize completed work, discard raw tool outputs. (b) Always preserve: decisions made, errors encountered, constraints discovered. (c) Keep last 5 full turns + summary of older turns.
- **Source:** Section 4.2.4

### AD-06: Drift Detection via LLM Judges
- **Technique:** Online detection using LLM "judges" or statistical tests, followed by regeneration or policy agent insertion.
- **Why:** Enables real-time course correction during multi-agent interactions. Catches drift before it compounds.
- **How:** For critical agents (classify_node, security-auditor), implement a lightweight judge that: (a) compares current output against baseline expectations, (b) flags deviations >2 standard deviations, (c) triggers re-generation or human escalation on detection.
- **Source:** Section 4.2.5

### AD-07: Agent Stability Index (ASI) — 12 Dimensions
- **Technique:** The Agent Stability Index evaluates twelve dimensions including: response consistency, tool usage patterns, reasoning pathway stability, inter-agent agreement rates.
- **Why:** Formal metrics enable systematic drift detection rather than ad-hoc observation.
- **How:** Track at minimum: (a) response consistency (do similar inputs produce similar outputs?), (b) tool usage patterns (is the agent using expected tools in expected order?), (c) reasoning pathway stability (are reasoning steps consistent?). Log these per-agent per-session.
- **Source:** arXiv 2601.04170 (Jan 2026), Section 4.1

### AD-08: Three Types of Drift
- **Technique:** Three drift types: (1) Semantic drift — progressive deviation from original intent. (2) Coordination drift — breakdown in multi-agent consensus. (3) Behavioral drift — emergence of unintended strategies.
- **Why:** Each drift type requires different mitigation. Semantic drift needs re-anchoring; coordination drift needs protocol enforcement; behavioral drift needs constraint reinforcement.
- **How:** Monitor for each type separately: (a) Semantic: compare outputs against original task description. (b) Coordination: check inter-agent message format compliance. (c) Behavioral: log unexpected tool calls or output patterns.
- **Source:** arXiv 2601.04170 (Jan 2026), Section 4.1

---

## MULTI-AGENT BEHAVIORAL CONTROL

### MA-01: LangGraph State Machine Architecture
- **Technique:** Nodes (agents/tools) connected by edges with conditional logic. Supports cycles, branching, explicit error handling. Per-node error handling: retry/fallback/human escalation. Global token budget enforcer.
- **Why:** Explicit state machines provide deterministic routing for non-LLM logic, containing non-determinism to LLM-dependent nodes only.
- **How:** (a) Define all graph edges with explicit conditions. (b) Implement per-node error handlers (retry count, fallback node, escalation path). (c) Set a global token budget. (d) Use conditional edges for all branching decisions.
- **Source:** LangGraph docs, Section 5.2

### MA-02: Checkpointing for Time-Travel Debugging
- **Technique:** Use `MemorySaver` (dev) / `PostgresSaver` (production) for persistent state. Enables checkpoint-based state replay, rolling back to prior states, replaying with adjusted parameters. Per-node timeouts and automated retries.
- **Why:** Non-deterministic LLM-dependent nodes produce different outputs on each run. Time-travel debugging enables investigation and reproduction of failures.
- **How:** (a) Use PostgresSaver in production (not SQLite). (b) Enable checkpointing on all LLM-dependent nodes. (c) Set per-node timeouts. (d) Log checkpoint IDs for every execution for post-hoc analysis.
- **Source:** Section 5.2

### MA-03: OpenAI Tripwire Guardrail Pattern
- **Technique:** Three guardrail types: Input (on first agent), Output (on last agent), Tool (before/after execution). Tripwire behavior: when triggered, immediately raises an exception, halting agent execution. Blocking mode (`run_in_parallel=False`) prevents the agent from ever executing.
- **Why:** Tripwires provide immediate halt on policy violation, preventing cascading errors through multi-agent chains.
- **How:** Implement tripwire-equivalent behavior: (a) Input validation that blocks execution on critical violations. (b) Output validation that rejects and triggers re-generation. (c) Tool guardrails that prevent unauthorized tool use. (d) Any CRITICAL security finding = immediate pipeline halt.
- **Source:** OpenAI Agents SDK, Section 5.3

### MA-04: Sub-Agent Context Isolation
- **Technique:** Each sub-agent handles focused tasks with a clean context window. Sub-agents return condensed summaries (1,000-2,000 tokens) to the coordinator. The coordinator maintains a high-level view without detailed noise.
- **Why:** Context isolation prevents cross-contamination between agent tasks. Clean context windows maximize per-agent performance.
- **How:** (a) Each verification agent receives only the code under review, not the full conversation. (b) Agent reports are condensed to 1,000-2,000 tokens before returning to orchestrator. (c) The orchestrator never receives raw tool outputs from sub-agents.
- **Source:** Section 5.4

### MA-05: Token Budget Awareness
- **Technique:** Multi-agent systems consume up to 15x more tokens than standard chat, but context quality is dramatically better.
- **Why:** Understanding the token cost multiplier is essential for budgeting and architecture decisions.
- **How:** (a) Budget 15x single-agent token cost for multi-agent workflows. (b) Track per-agent and per-wave token usage. (c) Set per-agent token limits to prevent runaway consumption. (d) Use token usage as a health metric — sudden spikes indicate drift or loops.
- **Source:** Section 5.4

### MA-06: Observability as Behavioral Control
- **Technique:** Trace every step and handoff (prompts, outputs, tools, tokens, costs, latencies). Sample logs to check for hallucination, off-topic behavior, missed requirements. Route runs through live evaluation pipelines. Monitor cost, latency, and quality as continuous behavioral signals.
- **Why:** Without observability, behavioral degradation is invisible until it produces user-facing failures.
- **How:** (a) Log all agent prompts, outputs, tool calls, and token counts. (b) Sample 10% of runs for manual quality review. (c) Set alerting thresholds for: cost per run, latency per agent, output schema violations. (d) Store traces for at least 30 days.
- **Source:** Section 5.5

### MA-07: Framework Selection Matrix
- **Technique:** Framework comparison for different use cases: LangGraph (deterministic flow), CrewAI (rapid prototyping), AutoGen/AG2 (enterprise async), OpenAI Agents SDK (strict guardrails), Pydantic AI (type safety).
- **Why:** Framework choice determines available control mechanisms. Mismatched framework = fighting the tooling.
- **How:** For SIOPV: LangGraph for pipeline orchestration (already chosen), Pydantic for validation, tripwire patterns from OpenAI SDK adapted to LangGraph. Document why the framework was chosen and what trade-offs were accepted.
- **Source:** Section 5.1

---

## STRUCTURED OUTPUT ENFORCEMENT

### SO-01: Constrained Decoding as Gold Standard
- **Technique:** Token-level masking prevents invalid outputs at generation time. Tools: NVIDIA NIM, Guidance, llama.cpp. Guidance shows highest coverage on 6 of 8 benchmark datasets; llama.cpp leads on domain-specific datasets.
- **Why:** Constrained decoding is the only approach that guarantees format compliance — all other approaches are probabilistic.
- **How:** For all LLM calls producing structured data: (a) Use API-native structured output mode (Claude, OpenAI). (b) For local models, use Guidance or llama.cpp grammar constraints. (c) Never rely on prompt-only format instructions for production outputs.
- **Source:** Section 6.1, 6.2

### SO-02: Reliability Ranking of Output Approaches
- **Technique:** Ranked from most to least reliable: (1) Constrained Decoding, (2) API-Native Structured Output, (3) JSON Schema + Validation, (4) Pydantic Validation, (5) Grammar-Based Decoding, (6) Prompt-Only (lowest).
- **Why:** Choosing the wrong approach leads to unpredictable output format failures. Prompt-only is the least reliable method.
- **How:** For each agent output, select the highest-reliability approach available. Never use prompt-only for any output that will be parsed programmatically. Document the approach chosen for each agent.
- **Source:** Section 6.1

### SO-03: Pydantic AI Integration Pattern
- **Technique:** Pydantic AI uses Pydantic models to: (1) build JSON Schema for LLM, (2) validate data at end of run, (3) stream with immediate validation, (4) support durable execution across transient API failures.
- **Why:** Pydantic provides both schema definition and runtime validation in one system, reducing inconsistencies between expected and actual output.
- **How:** (a) Define Pydantic models for every agent's input and output. (b) Use these models for both prompt construction (JSON Schema) and response validation. (c) Enable durable execution for long-running agents.
- **Source:** Section 6.3

### SO-04: Validation-Repair Loop
- **Technique:** When structured output fails validation: (1) Validate with Pydantic or Guardrails AI. (2) On failure, run a "repair" prompt with the validator's errors. (3) Retry with error context. (4) Version payloads with `schemaVersion` field using semver.
- **Why:** LLMs occasionally produce malformed output even with constrained decoding. The repair loop provides graceful degradation.
- **How:** (a) Wrap every structured output call in a validation-repair loop. (b) Maximum 3 retry attempts. (c) Include the validation error message in the repair prompt. (d) Add `schemaVersion` to all inter-agent payloads. (e) Log repair events as quality signals.
- **Source:** Skywork AI, Section 6.4

---

## GUARDRAIL FRAMEWORKS

### GF-01: NVIDIA NeMo Guardrails with Colang
- **Technique:** Open-source toolkit for programmable guardrails: Colang language for defining conversational rails, topical/safety/execution rails, parallel execution, OpenTelemetry integration.
- **Why:** Colang provides a declarative language specifically designed for guardrail logic, more maintainable than embedding guardrails in application code.
- **How:** Evaluate NeMo Guardrails for: (a) input validation rails, (b) topic boundary enforcement, (c) safety classification. Integrate via OpenTelemetry for tracing.
- **Source:** NeMo Guardrails GitHub, Section 7.1

### GF-02: Guardrails AI for Output Validation
- **Technique:** Open-source framework with pre-built validators from Guardrails Hub. Custom validator creation. Can automatically adjust invalid output OR re-prompt with additional context.
- **Why:** Pre-built validators accelerate guardrail deployment; custom validators handle domain-specific rules.
- **How:** (a) Use Guardrails Hub validators for common checks (JSON format, PII, profanity). (b) Create custom validators for domain-specific rules (vulnerability classification format, severity ranges). (c) Configure auto-fix vs. re-prompt per validator.
- **Source:** Guardrails AI GitHub, Section 7.2

### GF-03: Three-Layer Guardrail Architecture
- **Technique:** Production systems require guardrails at three levels: Input Layer (injection detection, format validation, PII detection, rate limits, malicious content filtering), Interaction Layer (tool restriction, autonomous decision cap, state-machine tool availability, token budget), Output Layer (structured validation, relevancy checks, hallucination detection, content safety, schema compliance).
- **Why:** Single-layer guardrails leave gaps. Each layer catches different failure modes.
- **How:** For each agent, define guardrails at all three layers. Audit coverage: every agent must have at least one guardrail per layer. Document which guardrails are active at each layer.
- **Source:** Section 7.3

### GF-04: Interaction Layer — Cap Autonomous Decisions
- **Technique:** Cap number of autonomous decisions per task chain. Use state-machine-based tool availability (Manus pattern). Enforce token budgets per interaction.
- **Why:** Uncapped autonomous decisions lead to runaway agent behavior, excessive token usage, and unpredictable outcomes.
- **How:** (a) Set maximum autonomous decisions per agent (e.g., max 20 tool calls per invocation). (b) Define which tools are available at each graph node. (c) Set per-node token budgets. (d) Escalate to human when caps are hit.
- **Source:** Section 7.3

### GF-05: Llama Guard for Safety Classification
- **Technique:** Meta's specialized safety classifier for LLM inputs and outputs. Fine-tuned for content safety, supports customizable safety taxonomies, low-latency classification.
- **Why:** Purpose-built safety classifiers outperform general-purpose LLMs at safety classification, with lower latency and cost.
- **How:** Evaluate Llama Guard as input/output safety classifier for production pipeline. Use customizable taxonomy to define SIOPV-specific safety categories.
- **Source:** Section 7.4

### GF-06: DLP-First Guardrail Strategy
- **Technique:** Data Loss Prevention (DLP) is the recommended starting point for guardrail strategies because it prevents sensitive data from ever entering the LLM.
- **Why:** This is the only reliable way to keep sensitive data out of model logs, caches, embeddings, or training pipelines. Once data enters the LLM, it cannot be unlearned.
- **How:** (a) DLP scan on all inputs before LLM processing (already implemented via Presidio). (b) DLP scan on all outputs before delivery. (c) DLP scan on all inter-agent payloads. (d) DLP is the first guardrail, not an afterthought.
- **Source:** Section 7.5

---

## COMPACTION-SAFE INSTRUCTIONS

### CS-01: Three Compression Approaches and Their Risks
- **Technique:** Three primary compression approaches: (1) Prompt Compression (LLMLingua) — token-level pruning, risk of breaking meaning. (2) Dynamic Summarization — living summary + last N turns, risk of losing specific constraints. (3) Verbatim Compaction — delete tokens without rewriting, most faithful but least flexible.
- **Why:** Understanding compression mechanisms enables designing instructions that survive all three approaches.
- **How:** Design instructions to survive all three: (a) keep constraints self-contained (not dependent on surrounding text), (b) use explicit values not references, (c) mark critical sections for preservation.
- **Source:** Section 8.1

### CS-02: Never Generalize Specific Values
- **Technique:** Keep exact names, paths, values, error messages, URLs, and version numbers verbatim during compaction. Never generalize specifics.
- **Why:** Generalization during compaction loses the exact information needed for correct execution (paths, thresholds, version numbers).
- **How:** (a) All constraints must include literal values, not references. (b) Write "threshold is 0.7" not "threshold is defined elsewhere." (c) Include full file paths, not relative references. (d) Audit compacted output for generalized values.
- **Source:** Section 8.2

### CS-03: Separate Survival-Critical Instructions
- **Technique:** Instructions that MUST survive should be in system prompts or pinned sections, not embedded in conversation.
- **Why:** Conversation content is the first to be compressed. System prompts and pinned sections are preserved by design.
- **How:** (a) Move all non-negotiable rules to system prompt or CLAUDE.md. (b) Never embed critical constraints in tool call responses or assistant messages. (c) Use `<!-- COMPACT-SAFE: summary -->` markers on all critical workflow sections.
- **Source:** Section 8.2

### CS-04: COMPACT-SAFE Markers
- **Technique:** Tag sections that must be preserved during compaction with `<!-- COMPACT-SAFE: summary -->` comments.
- **Why:** Explicit markers tell the compaction system which content is expendable and which is not.
- **How:** (a) Add COMPACT-SAFE markers to all workflow files (already partially done). (b) Include a one-line summary in the marker that captures the essential information. (c) Audit: every file in `.claude/workflow/` must have a COMPACT-SAFE marker.
- **Source:** Claude Code pattern, Section 8.2, 8.3

### CS-05: Structural Redundancy — Triple Storage
- **Technique:** Critical rules should appear in multiple places: system prompt + external file + periodic re-injection.
- **Why:** Redundancy ensures that even if one storage location is lost to compaction or context limits, the rule persists in another.
- **How:** For every non-negotiable rule, verify it exists in: (a) system prompt / CLAUDE.md, (b) an external file (workflow, config), (c) periodic re-injection mechanism (runtime reinforcement callback). If any rule exists in only one location, it is at risk.
- **Source:** Section 8.2

### CS-06: External Memory as Compaction Bypass
- **Technique:** Persistent files (NOTES.md, todo.md, projects/*.json) survive compaction entirely because they exist outside the context.
- **Why:** Files on disk are immune to context compression. They provide perfect recall of any information written to them.
- **How:** (a) Use `projects/siopv.json` for phase state (already done). (b) Extend to per-phase state files. (c) Write critical decisions to disk immediately, not just in conversation. (d) Re-read external files at decision points.
- **Source:** Section 8.2, 8.4

### CS-07: Manus File-System-as-Memory Pattern
- **Technique:** The file system is the ultimate context: unlimited in size, persistent by nature, directly operable by the agent. The model writes to and reads from files on demand — using the file system as structured, externalized memory.
- **Why:** File system memory has no token limit, survives compaction, and can be shared across agents and sessions.
- **How:** (a) For any information that must persist beyond the current context window, write it to a file. (b) Structure external memory files (not free-form notes). (c) Use consistent file naming and paths. (d) Index external memory files for quick retrieval.
- **Source:** Manus AI, Section 8.4

### CS-08: Compaction Tuning Parameters
- **Technique:** Maximize recall first, then improve precision. Configurable thresholds: trigger compaction based on token limits, message count, or user turns. Retention windows: preserve the last N messages unchanged.
- **Why:** Premature precision optimization loses important information. Recall-first ensures nothing critical is discarded.
- **How:** (a) Set compaction trigger at 80% of context window. (b) Preserve last 10 messages unchanged. (c) Test compaction output for information loss before deploying. (d) Log what was discarded for post-hoc analysis.
- **Source:** Section 8.5

---

## AGENT HANDOFF AND SHUTDOWN

### AH-01: Critical Insight — Reliability Lives in Handoffs
- **Technique:** "Reliability lives and dies in the handoffs — most 'agent failures' are actually orchestration and context-transfer issues."
- **Why:** This reframes debugging priorities: when agents fail, investigate the handoff first, not the agent itself.
- **How:** (a) Log every handoff payload. (b) When an agent fails, first check: was the handoff payload correct and complete? (c) Validate handoff payloads against schemas before sending. (d) Track handoff failure rates separately from agent failure rates.
- **Source:** Section 9.1

### AH-02: Structured Data Transfer as Default
- **Technique:** Four handoff patterns: (1) Structured Data Transfer (JSON Schema, default for all handoffs), (2) Conversation History Transfer (continuity-critical), (3) Summary Transfer (token-efficient), (4) File-Based Transfer (cross-session).
- **Why:** Free-text handoffs are the main source of context loss. Structured payloads ensure completeness and parseability.
- **How:** (a) Default to JSON Schema-constrained payloads for all handoffs. (b) Use conversation history only when continuity is critical. (c) Use summary transfer for long pipelines. (d) Use file-based transfer for cross-session state.
- **Source:** Section 9.2

### AH-03: Anti-Pattern — Free-Text Handoffs
- **Technique:** Free-text handoffs are the main source of context loss. Always use structured payloads. Never assume the next agent "knows" something — serialize everything.
- **Why:** Free text is ambiguous, lossy, and unparseable by downstream agents. Implicit state is the leading cause of handoff failures.
- **How:** (a) Ban free-text handoffs in agent design docs. (b) Every handoff must use a defined schema. (c) Audit existing handoffs for implicit state — anything not explicitly serialized is a bug.
- **Source:** Section 9.3

### AH-04: Anti-Pattern — Missing Tool Call Pairs
- **Technique:** LLMs expect tool calls paired with responses. Handoff messages must include both the AIMessage containing the tool call and a ToolMessage acknowledging the handoff.
- **Why:** Unpaired tool calls confuse the model's expectations and can cause unpredictable behavior in the receiving agent.
- **How:** (a) Every handoff must include both AIMessage and ToolMessage. (b) Validate that all tool calls in handoff context have corresponding responses. (c) Use LangGraph's `Command.PARENT` for parent-agent handoffs.
- **Source:** Section 9.3, 9.5

### AH-05: Version Payloads with Semver
- **Technique:** Include `schemaVersion` field in all handoff payloads. Follow semver for schema evolution.
- **Why:** Schema evolution without versioning causes silent breakage when agents are updated independently.
- **How:** (a) Add `schemaVersion: "1.0.0"` to every inter-agent payload. (b) Bump minor version for additive changes, major for breaking changes. (c) Receiving agent validates version compatibility before processing.
- **Source:** Section 9.4

### AH-06: Validate Strictly with Repair Loop
- **Technique:** Use Pydantic or Guardrails for handoff validation. On failure, run a "repair" prompt with validator errors and retry.
- **Why:** Strict validation catches malformed handoffs before they cause downstream failures. Repair loop provides graceful recovery.
- **How:** (a) Wrap every handoff receive in Pydantic validation. (b) On validation failure, log the error, run repair prompt, retry up to 3 times. (c) After 3 failures, escalate to human.
- **Source:** Section 9.4

### AH-07: Bind Tool Permissions to Roles
- **Technique:** Each agent only has access to tools relevant to its role. Separate concerns by role: Retrieval, Research, Drafting, Reviewing.
- **Why:** Unrestricted tool access enables scope creep, accidental side effects, and security vulnerabilities.
- **How:** (a) Define a tool whitelist per agent role. (b) Enforce at runtime — block tool calls not in the whitelist. (c) Audit for agents with >10 tools (likely over-scoped). (d) Never give write-access tools to read-only agents.
- **Source:** Section 9.4

### AH-08: Trace Every Handoff
- **Technique:** Capture prompts, outputs, tools, tokens, costs, latencies for every handoff.
- **Why:** Without tracing, handoff failures are invisible and debugging requires reproduction (which is non-deterministic with LLMs).
- **How:** (a) Log handoff payload, sending agent, receiving agent, timestamp, token count. (b) Store traces for at least 30 days. (c) Set alerting on handoff validation failures. (d) Review handoff traces as part of incident response.
- **Source:** Section 9.4

### AH-09: Fresh Context by Default
- **Technique:** By default, each new agent starts with fresh conversation history. Include prior context only when explicitly needed.
- **Why:** Carrying full context forward causes context rot and attention dilution. Fresh context maximizes per-agent performance.
- **How:** (a) Default to fresh context for all sub-agents. (b) Document when and why prior context is included. (c) When including prior context, use summary transfer (not full history) unless continuity is critical.
- **Source:** Section 9.4

### AH-10: LangGraph Command.PARENT for Parent Handoff
- **Technique:** Use `Command.PARENT` for handing off to parent agent. Must include both AIMessage (tool call) and ToolMessage (acknowledgment). Checkpointing enables pause-and-resume at specific nodes. Error nodes route to human intervention after repeated failures.
- **Why:** LangGraph's native handoff patterns ensure consistent behavior and enable time-travel debugging.
- **How:** (a) Use `Command.PARENT` for all upward handoffs. (b) Ensure paired messages. (c) Define error nodes that route to human after 3 retries. (d) Enable checkpointing on all handoff nodes.
- **Source:** Section 9.5

---

## SIOPV-SPECIFIC RECOMMENDATIONS (from Section 10)

### SP-01: Pipeline State File (todo.md Pattern for SIOPV)
- **Technique:** Have each graph node update a persistent `pipeline_state.md` file with current progress, remaining steps, and accumulated findings.
- **Why:** Serves as both external memory and attention anchor for the pipeline orchestrator.
- **How:** Create `pipeline_state.md` template. Each node appends its status on entry and exit. Orchestrator reads before routing decisions.
- **Source:** Section 10.1

### SP-02: Node-Level Context Isolation in LangGraph
- **Technique:** Each node should receive only the TypedDict fields relevant to its function, not the entire accumulated context.
- **Why:** Already partially implemented. Full isolation prevents cross-contamination and reduces context rot per node.
- **How:** Audit each node's state access. Restrict to only the fields it reads/writes. Flag nodes accessing >5 state fields for review.
- **Source:** Section 10.1

### SP-03: PostgresSaver for Production Checkpointing
- **Technique:** Use PostgresSaver in production (currently SQLite). Enable time-travel debugging for non-deterministic LLM-dependent nodes (classify, enrich).
- **Why:** SQLite does not support concurrent access. PostgresSaver enables production-grade checkpointing with concurrent pipeline runs.
- **How:** Migrate from SQLite to PostgresSaver. Enable time-travel on classify_node and enrich_node.
- **Source:** Section 10.1

### SP-04: Three-Layer Guardrails for Hexagonal Architecture
- **Technique:** Input Port Guardrails (PII/Presidio, Pydantic validation, rate limiting). Processing Guardrails (tool state machine, token budget, timeout/retry, LLM judge on classify_node). Output Port Guardrails (Pydantic validation, DLP scan, hallucination detection, schema version enforcement).
- **Why:** Maps the three-layer guardrail architecture to SIOPV's hexagonal architecture ports.
- **How:** Implement one guardrail per layer per node. Audit existing guardrails against this matrix. Fill gaps.
- **Source:** Section 10.2

### SP-05: Anti-Drift for classify_node
- **Technique:** Five specific mitigations: (1) Runtime reinforcement — append classification constraints at end of every LLM prompt. (2) Structured output — Pydantic models with strict JSON Schema. (3) Behavioral anchoring — 3-5 canonical classification examples. (4) Output validation — confidence scores within expected ranges. (5) LLM judge — lightweight secondary model for consistency verification.
- **Why:** classify_node is the most drift-vulnerable component because it uses LLM inference.
- **How:** Implement all five mitigations. Test each independently. Measure classification consistency before and after.
- **Source:** Section 10.3

### SP-06: Compaction-Safe Architecture for Multi-Session Pipeline
- **Technique:** (1) Pin critical constraints in system prompts. (2) Use COMPACT-SAFE markers. (3) External state files per phase. (4) Instruction redundancy — every critical rule appears in system prompt, node-level prompt, AND external config.
- **Why:** SIOPV's multi-phase, multi-session workflow is especially vulnerable to compaction loss between sessions.
- **How:** Audit all critical rules for triple redundancy. Create per-phase state files. Verify COMPACT-SAFE markers on all workflow docs.
- **Source:** Section 10.4

### SP-07: Verification Pipeline Guardrails
- **Technique:** (1) Pydantic-validated report schemas for all 5 agents. (2) Tripwire pattern — CRITICAL finding = immediate halt. (3) Wave timing with per-agent timeouts. (4) Clean context per verification agent. (5) Drift detection — compare against historical baselines.
- **Why:** The verification pipeline is the last line of defense. Its reliability must be higher than the code it verifies.
- **How:** Define Pydantic schemas for each agent's report. Implement tripwire on CRITICAL. Set timeouts (Wave 1: 7 min max, Wave 2: 5 min max). Track historical baselines.
- **Source:** Section 10.5

### SP-08: Deterministic Behavior Where Possible
- **Technique:** (1) Deterministic graph flow for non-LLM logic. (2) Reproducibility logging: model ID, temperature, seed, full prompts. (3) Version-aware behavior. (4) Constrained decoding for all LLM calls.
- **Why:** True determinism is impossible (temperature=0 is not fully deterministic due to floating-point arithmetic and MoE routing), but reproducibility logging enables investigation.
- **How:** Log model ID, temperature, seed, and full prompts for every LLM call. Use structured output mode everywhere. Track which model version produced which output.
- **Source:** Section 10.6

### SP-09: Inter-Phase Handoff Protocol
- **Technique:** (1) `projects/siopv.json` as canonical state transfer. (2) Pydantic models for inter-phase state. (3) Validation on resume — validate all accumulated state against schemas. (4) Audit trail — log inputs, outputs, verification results per phase transition.
- **Why:** Multi-phase architecture (phases 0-8) requires clean handoffs between sessions to avoid accumulated errors.
- **How:** Define Pydantic models for each phase's output state. Validate on session start. Log every phase transition with full context.
- **Source:** Section 10.7

---

## SUMMARY STATISTICS

| Category | Checkpoint Count |
|----------|-----------------|
| Instruction-Following Techniques | 8 |
| Persona/Role Definition | 8 |
| Context Rot and Attention Decay | 6 |
| Anti-Drift Techniques | 8 |
| Multi-Agent Behavioral Control | 7 |
| Structured Output Enforcement | 4 |
| Guardrail Frameworks | 6 |
| Compaction-Safe Instructions | 8 |
| Agent Handoff and Shutdown | 10 |
| SIOPV-Specific Recommendations | 9 |
| **TOTAL** | **74** |
