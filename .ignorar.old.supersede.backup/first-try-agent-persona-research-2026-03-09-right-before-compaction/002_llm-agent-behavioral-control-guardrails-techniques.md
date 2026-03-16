# LLM Agent Behavioral Control & Guardrails Techniques
## State-of-the-Art Research Report (March 2026)

---

## 1. INSTRUCTION-FOLLOWING TECHNIQUES (Proven Methods)

### 1.1 System Prompt Architecture

The system prompt provides a stable "operating environment" for the LLM, significantly reducing "concept drift" and keeping the model aligned with application intent throughout a conversation. Key principles:

- **Right Altitude Balance** (Anthropic): System prompts should occupy a "Goldilocks zone" -- specific enough to guide behavior effectively, yet flexible enough to provide strong heuristics. Avoid overly brittle if-else logic and avoid vague guidance that assumes shared context.
- **Structural Organization**: Use distinct sections with XML tagging or Markdown headers (`<background_information>`, `<instructions>`, `## Tool guidance`, `## Output description`).
- **Direct Persona Assignment**: "You are an X" outperforms "Imagine you are..." -- direct persona assignment is empirically more effective (LearnPrompting, 2025).
- **Minimal Viable Prompt**: Start with minimal instructions using the best model, then add clarity based on observed failure modes rather than anticipating all edge cases (Anthropic).

### 1.2 Prompt Repetition (Google Research, Dec 2025)

A groundbreaking finding: **repeating the input prompt improves performance for Gemini, GPT, Claude, and DeepSeek without increasing generated tokens or latency**. Transforming `<QUERY>` to `<QUERY><QUERY>` enables each prompt token to attend to every other prompt token, compensating for the causal masking limitation of transformer architectures.

- Accuracy improvements of up to 67-76% on non-reasoning tasks
- Theoretically grounded: causal LLMs prevent past tokens from attending to future tokens, so repetition creates bidirectional attention patterns within the prompt
- Practical implication: repeat critical instructions at the end of the context to maximize attention weight

**Source**: [Prompt Repetition Improves Non-Reasoning LLMs](https://arxiv.org/abs/2512.14982) (Leviathan et al., Google Research)

### 1.3 Instructional Segment Embedding (ICLR 2025)

A novel architectural approach: **Instructional Segment Embedding (ISE)** categorizes different types of instructions distinctly, incorporating segment information that classifies each token by its role (system instruction = 0, user prompt = 1, data input = 2). This structural differentiation helps models prioritize instruction tokens during processing.

**Source**: [ICLR 2025 Conference Paper](https://proceedings.iclr.cc/paper_files/paper/2025/file/ea13534ee239bb3977795b8cc855bacc-Paper-Conference.pdf)

### 1.4 Few-Shot Curation

Examples are "the pictures worth a thousand words" for LLMs. Use diverse, canonical examples rather than exhaustive edge-case lists. In-context learning from examples shapes behavior more reliably than verbose instructions.

### 1.5 Position Matters: Primacy and Recency Effects

Instructions at the **beginning and end** of the context receive the most attention. The "U-shaped" attention curve means middle content is systematically underweighted. Practical rules:

- Place non-negotiable constraints at the very beginning (system prompt)
- Repeat critical rules at the very end (before the model generates)
- Never bury important constraints in the middle of long contexts
- Performance drops >30% when key information sits in the middle vs. beginning/end

---

## 2. PERSONA/ROLE DEFINITION (What Works, What Doesn't)

### 2.1 Empirical Evidence: Mixed Results

Research from PromptHub (2025) shows that **vanilla prompting and vanilla prompting with static persona description perform very similarly** on accuracy tasks. None of the personas tested led to statistically significant improvements in model performance on factual or reasoning benchmarks.

**What persona/role prompting DOES control effectively:**
- Style and tone
- Output format and structure
- Domain vocabulary usage
- Behavioral constraints (what the agent refuses to do)

**What persona/role prompting DOES NOT reliably control:**
- Factual accuracy (models still hallucinate regardless of persona)
- Deep reasoning quality
- Knowledge beyond training data

### 2.2 CrewAI's Role-Goal-Backstory Pattern

CrewAI's empirically successful agent definition uses three mandatory attributes:

| Attribute | Purpose | Best Practice |
|-----------|---------|---------------|
| **Role** | Professional identity, shapes expertise simulation | Be specific: "Senior Python Security Auditor" not "Developer" |
| **Goal** | Clear, concise instruction guiding decision-making | Single, measurable objective per agent |
| **Backstory** | Narrative context enriching realism | Establishes WHY this agent exists and its unique perspective |

**Key findings from production CrewAI deployments:**
- **Specialists over generalists**: Agents perform better with specialized roles
- **80/20 Rule**: 80% of effort should go into designing tasks, only 20% into defining agents
- **Complementary skills**: Design agents with distinct but complementary abilities
- **Clear purpose**: Each agent should have a clearly defined, non-overlapping purpose

### 2.3 Effective Persona Techniques

From PLoP 2024 pattern language research and production systems:

1. **Constraint-Based Personas**: Define what the agent MUST NOT do alongside what it should do
2. **Domain Expert Personas**: Work best when combined with domain-specific tools and knowledge
3. **Behavioral Templates**: Use `system_template`, `prompt_template`, `response_template` for fine-grained control
4. **Reasoning Mode**: Enable `reasoning: true` for agents needing planning and reflection before action

**Source**: [Toward A Pattern Language for Persona-based Interactions with LLMs](https://www.cs.wm.edu/~dcschmidt/PDF/schreiber-PLoP24.pdf)

---

## 3. CONTEXT ROT AND ATTENTION DECAY (The Science)

### 3.1 Definition and Mechanism

**Context rot** is the performance degradation that occurs when LLMs process increasingly long input contexts. Models produce less accurate, less reliable outputs as context grows -- even when the context window is not full.

Three mechanisms drive context rot:

1. **Lost-in-the-Middle Effect**: U-shaped attention curve where beginning and end tokens receive disproportionate attention. Token #1 is visible to all subsequent tokens; token #500 is only visible from token #501 onward.
2. **Attention Dilution at Scale**: As context length increases, each token's attention budget is spread thinner across more tokens, reducing the model's ability to capture pairwise relationships.
3. **Distractor Interference**: Irrelevant context actively degrades performance on the target task, not just passively occupying space.

**Source**: [Chroma Research: Context Rot](https://research.trychroma.com/context-rot)

### 3.2 Measured Impact

- Performance drops >30% when relevant information sits in the middle vs. beginning/end
- LLMs suffer from the "Recency Effect" -- disproportionate attention to the last few user messages
- Critical instructions buried 10,000+ tokens back in history are frequently "forgotten"
- Negative constraints (things NOT to do) are especially vulnerable to being ignored in long contexts

### 3.3 Context Equilibria (arXiv, Oct 2025)

Recent research challenges the assumption that context drift is inevitable runaway degradation. Experiments reveal **stable, noise-limited equilibria** rather than runaway decay. Simple reminder interventions reliably reduce divergence, suggesting multi-turn drift is a **controllable equilibrium phenomenon**.

**Source**: [Drift No More? Context Equilibria in Multi-Turn LLM Interactions](https://arxiv.org/abs/2510.07777)

### 3.4 The KV-Cache Hit Rate Metric

From Manus AI's production experience: **The KV-cache hit rate is the single most important metric for a production-stage AI agent**, directly affecting both latency and cost. With Claude Sonnet, cached input tokens cost $0.30/MTok while uncached cost $3/MTok -- a 10x difference.

Key practices for KV-cache optimization:
- Make context **append-only** (never modify previous content)
- Avoid reordering actions or observations
- Ensure **deterministic serialization** (same data = same bytes every time)
- Prefix consistency: design tool names with consistent prefixes (e.g., `browser_*`, `shell_*`)

**Source**: [Manus Context Engineering Blog](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)

---

## 4. ANTI-DRIFT TECHNIQUES (Preventing Deviation)

### 4.1 Agent Drift: Formal Definition (Jan 2026)

The paper "Agent Drift: Quantifying Behavioral Degradation in Multi-Agent LLM Systems Over Extended Interactions" introduces the **Agent Stability Index (ASI)**, a composite metric evaluating twelve dimensions:

- Response consistency
- Tool usage patterns
- Reasoning pathway stability
- Inter-agent agreement rates

Three types of drift are identified:
1. **Semantic drift**: Progressive deviation from original intent
2. **Coordination drift**: Breakdown in multi-agent consensus mechanisms
3. **Behavioral drift**: Emergence of unintended strategies

**Source**: [Agent Drift (arXiv 2601.04170)](https://arxiv.org/abs/2601.04170)

### 4.2 Proven Mitigation Strategies

#### 4.2.1 Goal Persistence via Repeated Anchoring
- Explicit, repeated goal reminders at each turn counteract agent drift
- Manus AI's **todo.md pattern**: The agent constantly rewrites a `todo.md` file, reciting its objectives and progress at the end of the context. This biases the model's attention toward the global plan, mitigating "lost-in-the-middle" issues.
- External memory provides "behavioral anchors" resistant to incremental drift -- workflows using external memory show **21% higher behavioral stability** than those relying solely on conversation history

#### 4.2.2 Runtime Reinforcement (Instruction Re-injection)
A callback pattern that intercepts LLM requests, generates a reinforcement block, and appends non-negotiable rules to the end of the prompt before the model processes it. Implementation involves:
- Time stamping for temporal awareness
- Rule aggregation for non-negotiable constraints
- Prompt surgery: appending rules to the end of the user's message to maximize attention weight

#### 4.2.3 Controlled Variation to Break Pattern Lock-In
LLMs are excellent mimics -- if context is full of similar past action-observation pairs, the model tends to follow that pattern even when suboptimal. Manus introduces **structured variation**:
- Different serialization templates
- Alternate phrasing for observations
- Minor noise in formatting
- This "controlled randomness" breaks pattern lock-in and improves decision diversity

#### 4.2.4 Episodic Memory Consolidation
- Summarize or prune context to avoid pattern accumulation
- Preserve architectural decisions and critical details
- Discard redundant outputs or messages
- Maintain a "living summary" updated over time, carrying last N turns in full plus a compact summary of everything older

#### 4.2.5 Drift Detection via LLM Judges
Online detection using LLM "judges" or statistical tests, followed by regeneration or policy agent insertion. This enables real-time course correction during multi-agent interactions.

---

## 5. MULTI-AGENT BEHAVIORAL CONTROL (Orchestration Patterns)

### 5.1 Framework Comparison (2025-2026)

| Framework | Control Model | Reliability Mechanism | Best For |
|-----------|--------------|----------------------|----------|
| **LangGraph** | Explicit state machine (graph) | Checkpointing, time-travel, conditional edges | Complex workflows requiring deterministic flow |
| **CrewAI** | Role-based delegation | Role/goal/backstory, human-in-loop | Rapid prototyping, team-oriented systems |
| **AutoGen/AG2** | Event-driven async | Robust error handling, group chat, handoffs | Enterprise scale, Microsoft ecosystem |
| **OpenAI Agents SDK** | Handoff-based routing | Tripwire guardrails, input/output validation | OpenAI-native apps with strict guardrails |
| **Pydantic AI** | Type-safe structured | Pydantic validation, durable execution | Production-grade type safety |

### 5.2 LangGraph Production Patterns

**State Machine Architecture:**
- Nodes (agents/tools) connected by edges with conditional logic
- Supports cycles, branching, and explicit error handling
- Per-node error handling: retry/fallback/human escalation
- Global token budget enforcer

**Checkpointing for Behavioral Control:**
- `MemorySaver` (dev) / `PostgresSaver` (production) for persistent state
- Time-travel debugging: checkpoint-based state replay for non-deterministic agents
- Enables rolling back to prior states and replaying with adjusted parameters
- Per-node timeouts and automated retries

**Source**: [LangGraph State Machines in Production](https://dev.to/jamesli/langgraph-state-machines-managing-complex-agent-task-flows-in-production-36f4)

### 5.3 OpenAI Agents SDK Guardrail Patterns

Three guardrail types with **tripwire mechanism**:

1. **Input Guardrails**: Run on user input; only on the first agent in a chain
2. **Output Guardrails**: Run on final agent output; only on the last agent
3. **Tool Guardrails**: Run before/after tool execution; can skip, replace, or tripwire

**Tripwire behavior**: When triggered, immediately raises an exception (`InputGuardrailTripwireTriggered` or `OutputGuardrailTripwireTriggered`), halting agent execution. Blocking mode (`run_in_parallel=False`) prevents the agent from ever executing, saving tokens and preventing side effects.

**Source**: [OpenAI Agents SDK Guardrails](https://openai.github.io/openai-agents-python/guardrails/)

### 5.4 Sub-Agent Architecture for Context Isolation

The most effective multi-agent pattern for behavioral control:
- Each sub-agent handles focused tasks with a **clean context window**
- Sub-agents return condensed summaries (1,000-2,000 tokens) to the coordinator
- The coordinator maintains a high-level view without the detailed noise
- Token usage: multi-agent systems consume up to **15x more tokens** than standard chat, but context quality is dramatically better

### 5.5 Observability as Behavioral Control

Production multi-agent systems require:
- Tracing every step and handoff (prompts, outputs, tools, tokens, costs, latencies)
- Sampling logs to check for hallucination, off-topic behavior, missed requirements
- Routing runs through live evaluation pipelines
- Cost, latency, and quality monitoring as continuous behavioral signals

---

## 6. STRUCTURED OUTPUT ENFORCEMENT (Forcing Format Compliance)

### 6.1 Approaches Ranked by Reliability

| Approach | Reliability | Mechanism |
|----------|-------------|-----------|
| **Constrained Decoding** | Highest | Token-level masking prevents invalid outputs at generation time |
| **API-Native Structured Output** | Very High | Provider-managed schema enforcement (OpenAI, Claude, Gemini) |
| **JSON Schema + Validation** | High | Schema definition + post-generation validation + retry |
| **Pydantic Validation** | High | Type-safe validation with automatic error messages |
| **Grammar-Based Decoding** | High | Formal grammar rules enforced during generation |
| **Prompt-Only** | Lowest | Relying on instructions alone for format compliance |

### 6.2 Constrained Decoding (State of the Art)

Tools like NVIDIA NIM, Guidance, and llama.cpp guide the model so that any invalid token (one that would break JSON format or violate the schema) is not produced. This is the gold standard for format compliance.

Empirical results (from structured output benchmarks):
- **Guidance** shows highest coverage on 6 of 8 benchmark datasets
- **Llama.cpp** leads on domain-specific and hard JSON Schema datasets

### 6.3 Pydantic AI Integration

Pydantic AI uses Pydantic models to:
1. Build the JSON Schema that tells the LLM how to return data
2. Perform validation to guarantee data correctness at end of run
3. Stream structured output continuously with immediate validation
4. Support tool calling, provider-managed structured outputs, and manual prompting

Key feature: **Durable Execution** -- agents preserve progress across transient API failures, handling long-running workflows with production-grade reliability.

### 6.4 Validation-Repair Loop

When structured output fails validation:
1. Validate with Pydantic or Guardrails AI
2. On failure, run a "repair" prompt with the validator's errors
3. Retry with error context
4. Version payloads with `schemaVersion` field using semver

**Source**: [Skywork AI: Agent Orchestration Best Practices](https://skywork.ai/blog/ai-agent-orchestration-best-practices-handoffs/)

---

## 7. GUARDRAIL FRAMEWORKS (Tools and Patterns)

### 7.1 NVIDIA NeMo Guardrails

Open-source toolkit for programmable guardrails on LLM-based conversational systems:
- **Colang** language for defining conversational rails
- Supports topical rails, safety rails, and execution rails
- Parallel rails execution for performance
- OpenTelemetry integration for tracing
- Programmable: define custom dialog flows and safety constraints

**Source**: [NeMo Guardrails GitHub](https://github.com/NVIDIA-NeMo/Guardrails)

### 7.2 Guardrails AI

Open-source framework for output validation:
- Pre-built validators available from Guardrails Hub
- Custom validator creation
- Integration with NeMo Guardrails for combined input/output control
- Can automatically adjust invalid output OR re-prompt the LLM with additional context

**Source**: [Guardrails AI GitHub](https://github.com/guardrails-ai/guardrails)

### 7.3 Multi-Layer Guardrail Architecture

Production systems require guardrails at three levels:

**Input Layer:**
- Prompt injection detection
- Input format validation
- PII detection and redaction
- Length and rate limits
- Malicious content filtering

**Interaction Layer (especially for agentic systems):**
- Restrict tools available during function calling
- Cap number of autonomous decisions per task chain
- State-machine-based tool availability (Manus pattern)
- Token budget enforcement

**Output Layer:**
- Structured output validation
- Relevancy checks
- Hallucination detection
- Content safety filtering
- Schema compliance verification

### 7.4 Llama Guard

Meta's specialized safety classifier for LLM inputs and outputs:
- Fine-tuned for content safety classification
- Supports customizable safety taxonomies
- Can be used as both input and output guardrail
- Low-latency classification suitable for real-time use

### 7.5 The DLP-First Approach

Data Loss Prevention (DLP) is the recommended starting point for guardrail strategies because it prevents sensitive data from ever entering the LLM. This is the only reliable way to keep sensitive data out of model logs, caches, embeddings, or training pipelines.

---

## 8. COMPACTION-SAFE INSTRUCTIONS (Surviving Context Compression)

### 8.1 The Compaction Problem

When context approaches limits, systems must compress conversation history. The critical challenge: **preserving instructions and constraints while discarding redundant content**. Three primary compression approaches:

| Method | Mechanism | Risk |
|--------|-----------|------|
| **Prompt Compression** (LLMLingua) | Token-level pruning guided by model signals | Can break meaning if over-compressed |
| **Dynamic Summarization** | Living summary updated over time + last N full turns | May lose specific constraints |
| **Verbatim Compaction** | Delete tokens without rewriting; survivors are character-for-character from input | Most faithful but least flexible |

### 8.2 Principles for Compaction-Survivable Instructions

Based on production experience from Claude Code, Manus, and ForgeCode:

1. **Never generalize specific values**: Keep exact names, paths, values, error messages, URLs, and version numbers verbatim
2. **Separate concerns**: Instructions that MUST survive should be in system prompts or pinned sections, not embedded in conversation
3. **Use COMPACT-SAFE markers**: Tag sections that must be preserved during compaction (as seen in Claude Code workflow files)
4. **Structural redundancy**: Critical rules should appear in multiple places (system prompt + external file + periodic re-injection)
5. **External memory as backup**: Persistent files (NOTES.md, todo.md) survive compaction entirely because they exist outside the context

### 8.3 Claude Code's Approach

In Claude Code:
- `CLAUDE.md` files are pre-loaded at context start and survive compaction
- `<!-- COMPACT-SAFE: summary -->` comments mark sections that compaction must preserve
- Architectural decisions, unresolved bugs, and implementation details are preserved
- Redundant tool outputs and messages are discarded
- Sub-agents maintain their own clean context windows

### 8.4 Manus AI's File-System-as-Memory

Manus treats the file system as the ultimate context: unlimited in size, persistent by nature, directly operable by the agent. The model writes to and reads from files on demand -- using the file system not just as storage, but as structured, externalized memory.

The `todo.md` pattern serves double duty: it externalizes the plan (surviving compaction) AND biases attention toward the global goal (anti-drift).

### 8.5 Compaction Tuning

- **Maximize recall first**: Ensure the compaction prompt captures every relevant piece of information
- **Then improve precision**: Eliminate superfluous content iteratively
- **Configurable thresholds**: Trigger compaction based on token limits, message count, or user turns
- **Retention windows**: Preserve the last N messages unchanged

---

## 9. AGENT HANDOFF BEST PRACTICES (Clean Shutdown/Restart)

### 9.1 The Critical Insight

**"Reliability lives and dies in the handoffs -- most 'agent failures' are actually orchestration and context-transfer issues."**

### 9.2 Handoff Patterns

| Pattern | Mechanism | Use Case |
|---------|-----------|----------|
| **Structured Data Transfer** | JSON Schema-constrained payloads | Default for all handoffs |
| **Conversation History Transfer** | Pass full chat context to next agent | Continuity-critical flows |
| **Summary Transfer** | Condensed summary of prior work | Token-efficient, long pipelines |
| **File-Based Transfer** | Write state to file, next agent reads | Cross-session persistence |

### 9.3 Anti-Patterns to Avoid

- **Free-text handoffs**: The main source of context loss. Always use structured payloads.
- **Implicit state**: Never assume the next agent "knows" something. Serialize everything.
- **Missing tool call pairs**: LLMs expect tool calls paired with responses. Handoff messages must include both the AIMessage containing the tool call and a ToolMessage acknowledging the handoff.

### 9.4 Production Handoff Checklist

1. **Version payloads**: Include `schemaVersion` field; follow semver
2. **Validate strictly**: Use Pydantic or Guardrails; on failure, run a "repair" prompt with validator errors and retry
3. **Separate concerns by role**: Keep agents specialized (Retrieval, Research, Drafting, Reviewing)
4. **Bind tool permissions to roles**: Each agent only has access to tools relevant to its role
5. **Trace every handoff**: Capture prompts, outputs, tools, tokens, costs, latencies
6. **Fresh context option**: By default, each new agent starts with fresh conversation history. Include prior context only when explicitly needed.

### 9.5 LangGraph Handoff Patterns

- `Command.PARENT` for handing off to parent agent
- Must include both AIMessage (tool call) and ToolMessage (acknowledgment)
- Checkpointing enables pause-and-resume at specific nodes
- Error nodes route to human intervention or logging after repeated failures

### 9.6 OpenAI Agents SDK Handoff

- Handoffs as first-class primitives
- Input/output guardrails run at chain boundaries (input on first agent, output on last)
- Tool guardrails run before/after every tool execution
- Tripwire mechanism for immediate halt on policy violation

---

## 10. RECOMMENDATIONS FOR SIOPV (Synthesis for a Hexagonal Python Security Pipeline)

Based on the research above, here are specific recommendations for the SIOPV project -- a hexagonal-architecture Python security vulnerability pipeline using LangGraph orchestration.

### 10.1 Context Engineering for the Pipeline Graph

**Current architecture**: START -> authorize -> ingest -> dlp -> enrich -> classify -> [escalate] -> END

Recommendations:
- **Adopt the todo.md pattern**: Have each graph node update a persistent `pipeline_state.md` file with current progress, remaining steps, and accumulated findings. This serves as both external memory and attention anchor.
- **Node-level context isolation**: Each node should receive only the state it needs (TypedDict fields relevant to its function), not the entire accumulated context. This is already partially implemented via LangGraph's state model.
- **Checkpoint aggressively**: Use `PostgresSaver` in production (already using SQLite). Enable time-travel debugging for non-deterministic LLM-dependent nodes (classify, enrich).

### 10.2 Guardrail Architecture

Implement three-layer guardrails aligned with the hexagonal architecture:

```
Input Port Guardrails:
  - PII detection (Presidio - already implemented)
  - Input schema validation (Pydantic)
  - Rate limiting per source

Processing Guardrails:
  - Tool availability state machine per node
  - Token budget enforcement per LLM call
  - Timeout per node with retry/fallback
  - LLM judge for drift detection on classify_node

Output Port Guardrails:
  - Structured output validation (Pydantic models)
  - DLP scan on all outputs (already implemented)
  - Hallucination detection on LLM-generated content
  - Schema version enforcement on all inter-node payloads
```

### 10.3 Anti-Drift for the Classification Node

The `classify_node` is the most drift-vulnerable component because it uses LLM inference for confidence estimation. Recommendations:

1. **Runtime reinforcement**: Append classification constraints at the end of every LLM prompt
2. **Structured output enforcement**: Use Pydantic models with strict JSON Schema for all LLM outputs
3. **Behavioral anchoring**: Include 3-5 canonical classification examples in-context (few-shot)
4. **Output validation**: Validate that confidence scores are within expected ranges before accepting
5. **LLM judge**: Run a lightweight secondary model to verify classification consistency

### 10.4 Compaction-Safe Architecture

Given SIOPV's multi-phase, multi-session workflow:

1. **Pin critical constraints in system prompts**: Security rules, classification taxonomy, and compliance requirements should be in system prompts that survive compaction
2. **Use `<!-- COMPACT-SAFE -->` markers** in all workflow documentation (already partially implemented)
3. **External state files**: `projects/siopv.json` already serves as external memory. Extend this pattern to per-phase state files.
4. **Instruction redundancy**: Critical rules should appear in: (a) system prompt, (b) node-level prompt, (c) external config file

### 10.5 Agent Verification Pipeline

For the 5-agent verification pipeline (best-practices-enforcer, security-auditor, hallucination-detector, code-reviewer, test-generator):

1. **Structured report format**: Enforce Pydantic-validated report schemas for all agents
2. **Tripwire pattern**: Implement OpenAI-style tripwires -- if any CRITICAL finding, halt the pipeline immediately
3. **Wave timing with guardrails**: Wave 1 (parallel: 3 agents) and Wave 2 (parallel: 2 agents) with per-agent timeouts
4. **Inter-agent isolation**: Each verification agent gets a clean context window with only the code under review
5. **Drift detection**: Compare current verification results against historical baselines to detect systematic drift

### 10.6 Deterministic Behavior Where Possible

True determinism is impossible with LLMs (even temperature=0 is not fully deterministic due to floating-point arithmetic and MoE routing). Practical recommendations:

- **Deterministic graph flow**: LangGraph's state machine provides deterministic routing -- use this for all non-LLM logic
- **Reproducibility logging**: Log model ID, temperature, seed, and full prompts for every LLM call
- **Version-aware behavior**: Track which model version produced which output
- **Constrained decoding**: Use structured output mode for all LLM calls to maximize output consistency

### 10.7 Handoff Between Phases

SIOPV's multi-phase architecture (0-8) requires clean handoffs between sessions:

1. **State serialization**: Use `projects/siopv.json` as the canonical state transfer mechanism
2. **Pydantic state models**: Define explicit Pydantic models for inter-phase state
3. **Validation on resume**: When starting a new session, validate all accumulated state against schemas
4. **Audit trail**: Every phase transition should be logged with inputs, outputs, and verification results

---

## SOURCES

### Academic Papers
- [Agent Drift: Quantifying Behavioral Degradation in Multi-Agent LLM Systems](https://arxiv.org/abs/2601.04170) (Jan 2026)
- [Drift No More? Context Equilibria in Multi-Turn LLM Interactions](https://arxiv.org/abs/2510.07777) (Oct 2025)
- [Prompt Repetition Improves Non-Reasoning LLMs](https://arxiv.org/abs/2512.14982) (Dec 2025, Google Research)
- [ICLR 2025: Instructional Segment Embedding](https://proceedings.iclr.cc/paper_files/paper/2025/file/ea13534ee239bb3977795b8cc855bacc-Paper-Conference.pdf)
- [Revisiting the Reliability of Language Models in Instruction-Following](https://arxiv.org/html/2512.14754v1) (Dec 2025)
- [SLOT: Structuring the Output of Large Language Models](https://aclanthology.org/2025.emnlp-industry.32.pdf) (EMNLP 2025)
- [Generating Structured Outputs from Language Models: Benchmark](https://arxiv.org/html/2501.10868v1) (Jan 2025)
- [NeMo Guardrails: Programmable Rails for LLM Applications](https://arxiv.org/abs/2310.10501)
- [Memory Management for Long-Running Low-Code Agents](https://arxiv.org/pdf/2509.25250) (Sep 2025)
- [Toward A Pattern Language for Persona-based Interactions with LLMs](https://www.cs.wm.edu/~dcschmidt/PDF/schreiber-PLoP24.pdf) (PLoP 2024)

### Industry Research & Engineering
- [Anthropic: Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Manus: Context Engineering for AI Agents](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)
- [Chroma Research: Context Rot](https://research.trychroma.com/context-rot)
- [OpenAI Agents SDK: Guardrails](https://openai.github.io/openai-agents-python/guardrails/)
- [OpenAI: A Practical Guide to Building Agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- [OpenAI Cookbook: Orchestrating Agents](https://cookbook.openai.com/examples/orchestrating_agents)

### Framework Documentation
- [CrewAI: Agents](https://docs.crewai.com/en/concepts/agents)
- [LangGraph: Agent Orchestration Framework](https://www.langchain.com/langgraph)
- [Pydantic AI](https://pydantic.dev/pydantic-ai)
- [NeMo Guardrails](https://github.com/NVIDIA-NeMo/Guardrails)
- [Guardrails AI](https://github.com/guardrails-ai/guardrails)

### Guides & Tutorials
- [Datadog: LLM Guardrails Best Practices](https://www.datadoghq.com/blog/llm-guardrails-best-practices/)
- [Runtime Reinforcement: Preventing Instruction Decay](https://towardsai.net/p/machine-learning/runtime-reinforcement-preventing-instruction-decay-in-long-context-windows)
- [How Agent Handoffs Work in Multi-Agent Systems](https://towardsdatascience.com/how-agent-handoffs-work-in-multi-agent-systems/)
- [Skywork AI: Agent Orchestration Best Practices](https://skywork.ai/blog/ai-agent-orchestration-best-practices-handoffs/)
- [Redis: Context Rot Explained](https://redis.io/blog/context-rot/)
- [Context Engineering Deep Dive (Prompting Guide)](https://www.promptingguide.ai/agents/context-engineering-deep-dive)
- [LLM Determinism in Production](https://medium.com/@2nick2patel2/llm-determinism-in-prod-temperature-seeds-and-replayable-results-8f3797583eb1)
- [Keywords AI: How to Get Consistent LLM Outputs in 2025](https://www.keywordsai.co/blog/llm_consistency_2025)
