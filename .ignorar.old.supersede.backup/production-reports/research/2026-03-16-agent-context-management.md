# Agent Context Window Management — Preventing Overflow in Multi-Agent Pipelines

**Research date:** 2026-03-16
**Scope:** Best practices up to March 2026 for managing individual agent context in multi-agent systems
**Author:** Research agent (WebSearch + WebFetch)

---

## Table of Contents

1. [Core Problem: Context Overflow in Multi-Agent Systems](#1-core-problem)
2. [Strategy Catalogue: Keeping Individual Agent Context Small](#2-strategy-catalogue)
3. [Handoff File / Agent Journal Pattern](#3-handoff-file--agent-journal-pattern)
4. [Framework-Specific Approaches](#4-framework-specific-approaches)
5. [Shared Cache vs. Independent Query: Architecture Decision](#5-shared-cache-vs-independent-query)
6. [Designing Tasks to Fit a Single Context Window](#6-designing-tasks-to-fit-a-single-context-window)
7. [Shared Memory and Cache Between Agents](#7-shared-memory-and-cache-between-agents)
8. [Agent Restart and Resume After Context Overflow](#8-agent-restart-and-resume-after-context-overflow)
9. [Concrete Size Estimates](#9-concrete-size-estimates)
10. [Synthesis: Decision Tree for Context Strategy](#10-synthesis-decision-tree)

---

## 1. Core Problem

### What Causes Overflow

In a multi-agent pipeline, context fills up from four primary sources that compound each other:

| Source | Typical Token Cost |
|---|---|
| System prompt (repeated every call) | 500 – 2,000 tokens |
| Conversation / message history (all turns) | Grows unboundedly |
| RAG retrieval results (10 docs × 1,500 tokens) | 15,000 tokens per retrieval |
| Tool outputs (DB query, API call, web search) | 200 – 20,000 tokens each |

Even with large context windows (200k–1M tokens), overflow is a real risk in long workflows because:

- **Context rot** begins well before the hard limit. Research (Hong et al., 2025) measured 18 LLMs and found performance becomes "increasingly unreliable as input length grows." The soft rot zone typically begins around 25% of nominal capacity.
- **KV-cache penalty**: In multi-agent systems where sub-agents share context, every agent pays the full attention cost for irrelevant sibling content.
- **Tool output accumulation**: Each tool call compounds — 5 tool calls at 5,000 tokens each = 25,000 tokens consumed before any reasoning.

### The GoLang Concurrency Principle Applied to Agents

A foundational insight from the 2025–2026 literature: **"Share memory by communicating, don't communicate by sharing memory."**
If every sub-agent shares the same context, you pay a massive KV-cache penalty and confuse the model with irrelevant details. Context isolation is not an optimization — it is a correctness requirement.

---

## 2. Strategy Catalogue: Keeping Individual Agent Context Small

The industry has converged on a four-axis framework called **Context Engineering**:

### Axis A: Context Offloading

Move information out of the active context window into an external system. Only bring it back when needed.

- **When:** After any tool output exceeds 2,000 tokens; after any completed reasoning phase.
- **How:** Write to files, vector stores, or structured key-value stores. Store a *pointer* (path or retrieval key) in context instead of the content.
- **Pattern:** "Pointer-based tool output" — instead of injecting a 20,000-token database response into context, the agent writes it to a file and keeps only the filename + a one-sentence summary.

### Axis B: Context Reduction (Compression)

Summarize or prune existing context before it grows too large.

**Trigger threshold:** At 70–80% of context capacity — do not wait for the API error.

Strategies, ranked by cost:

| Strategy | Token Savings | Latency Cost | Loss Risk |
|---|---|---|---|
| Sliding window (keep last N messages) | High | None | High (drops early context) |
| Token-aware trimming (trim oldest to fit budget) | High | None | Medium |
| LLM-based summarization | Medium | 1–2 additional LLM calls | Low |
| Importance scoring (recency + relevance + entity weight) | Medium–High | Low (offline scoring) | Low |

**Recommended:** LLM summarization at 75% capacity, with a fallback sliding window at 90%.

### Axis C: Context Retrieval (Dynamic Injection)

Rather than keeping all knowledge in context, retrieve only what the current step needs.

- **RAG at query time** instead of pre-loading all documents.
- **Memory recall on demand** — agents store facts externally and pull them in via similarity search before each task, not before the whole job.
- **Recommendation:** Budget 4,000–8,000 tokens for RAG results per step. Use retrieval depth flags: `depth="shallow"` for routine context, `depth="deep"` only for complex queries.

### Axis D: Context Isolation

Structurally separate agents so they cannot see each other's history.

- Each sub-agent gets its own context window — the lead agent (orchestrator) sees only structured summaries from sub-agents.
- Sub-agents store their outputs externally; the orchestrator retrieves summaries, not raw transcripts.
- **Anthropic's research system** (2025): The lead agent creates 3–5 parallel sub-agents, each with independent contexts. Sub-agents compress findings before returning results. This pattern "reduces path dependency and prevents context pollution."

---

## 3. Handoff File / Agent Journal Pattern

This is the most widely recommended pattern for long-running multi-session tasks.

### What It Is

Before compacting, ending a session, or spawning a fresh sub-agent, the current agent writes a structured **handoff file** (also called a "compaction brief," "agent journal," or "progress file"). The new agent or resumed session reads this file first, before any other action.

### Required Contents of a Handoff File

Based on multiple sources (Anthropic, lethain.com, akfpartners.com, 2025):

```markdown
# Handoff File — [Agent Name] — [ISO Timestamp]

## Current Status
One-sentence summary of what has been accomplished and what remains.

## Key Decisions Made
- Decision 1 and why it was made
- Decision 2 and rationale

## Important Constraints
- Constraint A (architectural, business, or test requirements)
- Constraint B

## Absolute File Paths — Files Read or Modified
- /absolute/path/to/file1.py — [what was done to it]
- /absolute/path/to/file2.md — [what was done to it]

## What Remains To Do (ordered by priority)
1. Next immediate action
2. Second step
3. ...

## Critical Data and References
- Key values, IDs, tokens, or configuration needed to continue
- External dependencies or blockers

## Git State
- Last commit hash: abc1234
- Branch: feature/xyz
- Working tree: clean / uncommitted changes in [list]
```

### When to Trigger Handoff

- **Pre-compaction:** Before the compaction prompt fires (monitor token count, trigger at 75% capacity).
- **Pre-spawn:** Before spawning a fresh sub-agent to continue a task.
- **Phase boundaries:** Always at the end of a completed phase, even if context is not full.
- **Pre-shutdown:** At session end, regardless of task completion status.

### Journal Pattern Variant

For long multi-phase work, maintain a **running journal** (append-only log) rather than a single handoff file:

```
claude-progress.txt  (append-only)
- [2026-03-16T10:00Z] Phase 1 complete. Implemented X. Tests pass.
- [2026-03-16T10:30Z] Phase 2 started. Working on Y.
- [2026-03-16T11:00Z] Phase 2 blocked on Z dependency. See issue #42.
```

Anthropic's "Effective Harnesses for Long-Running Agents" (2025) uses exactly this pattern: an Initializer Agent creates `claude-progress.txt`, and each subsequent Coding Agent appends to it and reads it at session start.

### Handoff Token Budget

A well-written handoff file should be **500–2,000 tokens**. If it exceeds 3,000 tokens, it is too detailed — the new agent will spend too much of its budget reading state instead of working.

---

## 4. Framework-Specific Approaches

### LangGraph

LangGraph's primary mechanism is **checkpointing** — a snapshot of graph state saved at every node execution step.

- **SQLite / DynamoDB / PostgreSQL** checkpointers persist state across sessions.
- Large payloads (≥ 350 KB) are automatically offloaded to S3 with DynamoDB storing a reference pointer — the same pointer pattern recommended at the application level.
- **Message trimming:** `trim_messages(strategy="last", max_tokens=N)` keeps the most recent messages within a token budget.
- **Summarization node pattern:** Insert a summarization node into the graph that fires when `len(messages) > threshold` — it replaces raw history with a structured summary, then continues.
- **Interrupt + resume:** `interrupt()` checkpoints state, pauses execution (for human review), and resumes from the same point. No context is lost.
- **Known issue (2025):** Token limit exceeded from ToolMessages (issue #3717) — if a tool returns a massive payload, the ToolMessage itself overflows. Fix: post-process ToolMessages to truncate or offload before storing in state.

### AutoGen (v0.4+)

AutoGen handles context at the model context level:

- **`BufferedChatCompletionContext`**: Most-recent-used (MRU) buffer — keeps only the last `buffer_size` messages. Clean and simple but drops early context entirely.
- **`TransformMessages`**: Pipeline of transformations applied before each LLM call: message count limiting, per-message token truncation, overall conversation token budget.
- **Processing order:** Newest-to-oldest, so recent messages are always preserved.
- **No built-in summarization** as of 2025. The community roadmap (issue #156) lists summarization as planned but not yet shipped. Workaround: add a custom summarization transformation.
- **Note:** In October 2025, Microsoft merged AutoGen with Semantic Kernel into a unified Microsoft Agent Framework (GA target Q1 2026). The context management APIs are converging.

### CrewAI

CrewAI's approach is task-boundary memory management:

- **`respect_context_window=True`** (default): When a conversation exceeds token limits, CrewAI automatically triggers LLM-based summarization instead of stopping with an error.
- **Unified Memory class** (2025 redesign): Replaces separate short-term/long-term/entity memory with a single intelligent API. Uses LLM to infer scope, categories, and importance when storing.
- **Adaptive recall depth:** `depth="shallow"` for routine agent context, `depth="deep"` for complex queries.
- **Task-boundary injection:** Before each task, the agent recalls relevant context from memory and injects it. After each task, discrete facts are extracted and stored.
- **Known limitation:** SQLite3 backend — not suitable for high-throughput or containerized deployments. Use Mem0 integration for production.

### Anthropic Claude Agent SDK

- Provides compaction as a built-in feature, but Anthropic explicitly states: **"compaction isn't sufficient on its own."**
- The recommended pattern is compaction + handoff file + structured task decomposition (one feature per session).
- The two-agent architecture (Initializer + Coding Agent) is the canonical pattern for long multi-session work.

---

## 5. Shared Cache vs. Independent Query: Architecture Decision

### Option A: Pre-Compute Shared Knowledge (Cache-First)

Each agent queries a shared, pre-computed cache rather than independently calling external services.

**Advantages:**
- MOONCAKE research (2025): shared KV cache across agents increased effective request capacity by 59–498% compared to independent computation.
- Eliminates redundant prefill computation when multiple agents work on related content.
- Consistent results — all agents see the same retrieved content.

**Architecture:** Centralized KV Cache Manager + shared vector store. One agent (or a pre-computation step) fills the cache; all workers read from it.

**When to use:** When 2+ agents work on the same corpus (same codebase, same document set, same data slice). Savings are proportional to redundancy.

### Option B: Each Agent Queries Independently

Each agent runs its own retrieval against the same vector store without sharing computed results.

**Advantages:**
- Simpler architecture. No coordination overhead.
- Each agent retrieves only what it needs — less irrelevant content in context.
- No risk of stale cache serving wrong content to the wrong agent.

**When to use:** When agents work on disjoint data; when retrieval results must be personalized or task-specific; when the shared-cache infrastructure is not yet available.

### Recommendation (2025 consensus)

**Use shared cache for system prompts and static knowledge; use independent retrieval for task-specific content.**

Specifically:
- **Pre-compute and cache:** System instructions, project specifications, architecture documents, any content read by every agent.
- **Independent retrieval:** Task-specific context, search results, tool outputs, intermediate artifacts.

Agentic Plan Caching (2025 research): extracting and reusing structured plan templates from the planning stage reduces cost by 50.31% and latency by 27.28% on average.

---

## 6. Designing Tasks to Fit a Single Context Window

### Core Principle: One Feature / One Phase Per Session

The #1 rule from production systems (Anthropic, Factory.ai, codegen.com): **agents that try to do too much in one session fail consistently.** The failure mode is the agent losing track of early constraints mid-task, hallucinating completions, or running out of context before finishing.

### Task Decomposition Guidelines

1. **Leaf-node granularity:** A task is sized correctly if an agent can complete it in 10–30 tool calls without needing to reference more than 3–5 files simultaneously.

2. **Token budget allocation for a 200k-token window:**

   | Component | Recommended Budget |
   |---|---|
   | System prompt + instructions | 2,000 – 4,000 tokens |
   | Task description + handoff file | 1,000 – 3,000 tokens |
   | Working context (files being edited) | 20,000 – 40,000 tokens |
   | Tool outputs (per step, cleared between steps) | 5,000 – 15,000 tokens |
   | Reasoning / message history | 10,000 – 30,000 tokens |
   | Safety headroom (never fill to limit) | 25% reserved |

3. **Serial dependency test:** If task B cannot start until task A produces an artifact, they must be separate sequential tasks (not parallel). If they are independent, they can run as parallel sub-agents.

4. **Context isolation check:** If implementing task X requires simultaneously keeping context from tasks A, B, and C in mind, decompose further until each task is self-contained with only 1–2 dependencies.

5. **Anti-pattern — "complete the app":** Never assign a task like "implement all remaining features." This is the primary cause of agent context collapse. Use a feature list JSON file with `"status": false` entries and have agents pick ONE item per session.

### Scalability Rules from Anthropic Research System

- Simple queries: 1 agent, 3–10 tool calls.
- Complex research: 10+ sub-agents with independent contexts, each focused on one aspect.
- Rule of thumb: **"If a human senior engineer would need a day to do it, it fits in one agent session. If it would take a week, it needs decomposition."**

---

## 7. Shared Memory and Cache Between Agents

### Memory Architecture Tiers

Production systems use three tiers (inspired by MemGPT / Letta OS-inspired design):

| Tier | Storage | Scope | Access Speed | Use Case |
|---|---|---|---|---|
| Working memory | In-context | Current step | Instant | Active reasoning, current tool outputs |
| Short-term / session memory | SQLite / Redis | Current session | Fast (ms) | Inter-step continuity, partial results |
| Long-term memory | Vector store + DB | Cross-session | Moderate (100ms) | Accumulated knowledge, past decisions |

### Recommended Backends

| Purpose | Recommended Backend | Notes |
|---|---|---|
| Shared vector store | ChromaDB (local) / Pinecone (cloud) | Embedding-based recall |
| Session state cache | Redis | Also handles semantic caching — 50–80% cost reduction on redundant queries |
| Structured agent outputs | JSON files on shared filesystem | Simplest; works for team agents on same machine |
| Cross-session facts | SQLite (dev) / PostgreSQL (prod) | CrewAI, LangGraph checkpointers |
| Artifact storage | Files + manifest JSON | Large outputs (code, reports) — store path, not content |

### Shared File-Based Memory (Simplest for Claude Code Teams)

For Claude Code team agents operating on the same filesystem:

```
.ignorar/
  agent-memory/
    research-cache.json      ← shared lookup table (key → file path)
    phase-N-facts.md         ← accumulated facts from phase N
    artifact-index.json      ← maps artifact IDs to file paths
  agent-outputs/
    agent-A-2026-03-16.md   ← each agent's structured output
    agent-B-2026-03-16.md
```

**Pattern:** Agents write outputs to dated files. The orchestrator reads the index (small) to find specific artifacts, then reads only the relevant artifact file (not all outputs). This keeps orchestrator context small.

### Access Control Considerations

Recent research (2025) identifies a gap: most frameworks do not enforce per-agent memory access control. Best practice:
- Use `agent_id` namespacing in shared stores to prevent agents from accidentally reading each other's private state.
- Read-only access to shared cache; read-write access only to the agent's own namespace.

---

## 8. Agent Restart and Resume After Context Overflow

### Strategy 1: Checkpoint + Resume (LangGraph pattern)

LangGraph checkpointers save state at every node. On overflow:
1. Detect context approaching limit (monitor token count in graph state).
2. Trigger a summarization node to compress message history.
3. Continue from the checkpoint — no data loss.
4. If hard overflow occurs: read last checkpoint, spawn new run from that state.

### Strategy 2: Fresh Sub-Agent + Handoff File (Anthropic pattern)

When approaching the context limit:
1. Write handoff file (see Section 3) to disk.
2. Spawn a fresh sub-agent with a clean context window.
3. The new agent's first instruction: "Read handoff file at [absolute path]. Then continue."
4. The new agent picks up exactly where the previous stopped.

**This is the recommended pattern for Claude Code team agents.** It is simpler than LangGraph checkpointing and works without framework-level infrastructure.

### Strategy 3: Session Memory Injection at Start

For recurring long-running workflows (not single tasks):
1. At every session start, the agent reads the progress file / journal.
2. The journal contains the minimal state needed to orient the agent — not the full history.
3. The agent reconstructs working context from the journal + current file state (git history, file system).

**Critical:** The resume file must be minimal. If reading the handoff file consumes more than 10% of the context budget, it is too large.

### Known Issues to Avoid

- **AutoGen subagent resume bug (2025, issue #11712):** Subagent transcript files do not store the user prompts that initiated them. Resumed agents lack critical context. Workaround: always pass full task context in the initial prompt, not just as conversation history.
- **LangGraph ToolMessage overflow (issue #3717):** Large tool outputs stored as ToolMessages overflow context at the state level. Workaround: post-process ToolMessages with a truncation or offloading transform before they enter graph state.

---

## 9. Concrete Size Estimates

### File Type → Token Estimate (Claude tokenizer, 2025)

| File Type | Estimate |
|---|---|
| 100 lines Python | ~1,000 tokens |
| 1 KB plain text | ~250 tokens |
| Typical Context7 library query response | 2,000 – 8,000 tokens |
| Typical web search result page | 3,000 – 15,000 tokens |
| Well-written handoff file | 500 – 2,000 tokens |
| Full research report (like this one) | 3,000 – 6,000 tokens |
| Medium Python module (300 lines) | ~3,000 tokens |
| Large Python file (1,000 lines) | ~10,000 tokens |
| JSON feature list (200 items) | ~5,000 – 8,000 tokens |
| RAG result (10 documents, 500 words each) | ~7,000 – 12,000 tokens |

**Ratio:** 1 token ≈ 4 characters ≈ 0.75 words (English plain text). Code tokenizes less efficiently — more tokens per word due to symbols, indentation, and identifiers.

### Context Window Usage Rules of Thumb

| Threshold | Action |
|---|---|
| 0–50% full | Normal operation |
| 50–75% full | Monitor; avoid large tool outputs |
| 75% full | Trigger compaction / summarization now |
| 80–90% full | Emergency: write handoff file, spawn fresh agent |
| >90% full | Context rot zone — responses are unreliable |

### Token Cost of Multi-Agent Systems (Anthropic data, 2025)

- Single agent: ~4× more tokens than a standard chat interaction.
- Multi-agent system: ~15× more tokens than a standard chat interaction.
- Token usage explains 80% of performance variance in research tasks.

### Cost Savings from Context Management

| Technique | Reported Savings |
|---|---|
| Semantic caching (Redis) | 50–80% reduction in redundant LLM calls |
| Shared KV cache (MOONCAKE) | 59–498% capacity increase |
| Agentic Plan Caching | 50.31% cost reduction, 27.28% latency reduction |
| Token compression (sparse attention) | 70–80% fewer tokens (task-specific, varies) |

---

## 10. Synthesis: Decision Tree for Context Strategy

```
START: New agent task
│
├─ Is the task completable in < 30 tool calls?
│   ├─ YES: Single agent session. Allocate budget as per Section 6.
│   └─ NO: Decompose. Split into phases. Each phase = one agent session.
│
├─ Do 2+ agents need the same static knowledge (docs, specs)?
│   ├─ YES: Pre-compute shared cache. All agents read from cache.
│   └─ NO: Each agent retrieves independently at query time.
│
├─ Is this a multi-session long-running task?
│   ├─ YES: Set up handoff file + progress journal from session 1.
│   └─ NO: Checkpoint at phase boundaries only.
│
├─ At 75% context capacity:
│   ├─ LangGraph: Insert summarization node. Continue.
│   └─ Claude Code team: Write handoff file. Spawn fresh sub-agent.
│
└─ At session end (always):
    Write handoff file. Commit git state. Update progress journal.
```

### Top 5 Non-Negotiable Rules

1. **Never wait for API overflow.** Trigger compaction at 75% capacity, not at failure.
2. **Always write a handoff file at session end**, even if the task completed successfully — the next agent or session will need it.
3. **Never put large tool outputs in context.** Write them to files. Keep only pointers.
4. **Context isolation between agents is a correctness requirement**, not an optimization. Each sub-agent gets its own window.
5. **One task per agent session.** An agent that tries to complete "all remaining work" will fail. Use a feature list with boolean status flags.

---

## Sources

- [Context Window Overflow in 2026: Fix LLM Errors Fast — Redis](https://redis.io/blog/context-window-overflow/)
- [The Context Window Problem: Scaling Agents Beyond Token Limits — Factory.ai](https://factory.ai/news/context-window-problem/)
- [Context Engineering for AI Agents: Part 2 — Philschmid](https://www.philschmid.de/context-engineering-part-2)
- [Architecting Efficient Context-Aware Multi-Agent Framework for Production — Google Developers Blog](https://developers.googleblog.com/architecting-efficient-context-aware-multi-agent-framework-for-production/)
- [How We Built Our Multi-Agent Research System — Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Effective Harnesses for Long-Running Agents — Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Best Practices for Multi-Agent Orchestration and Reliable Handoffs — Skywork](https://skywork.ai/blog/ai-agent-orchestration-best-practices-handoffs/)
- [Building an Internal Agent: Context Window Compaction — lethain.com](https://lethain.com/agents-context-compaction/)
- [Agentic Pattern: Handoff + Resume — AKF Partners](https://akfpartners.com/growth-blog/agentic-pattern-handoff-resume/)
- [Handling Long Contexts — AutoGen 0.2 Docs](https://microsoft.github.io/autogen/0.2/docs/topics/handling_long_contexts/intro_to_transform_messages/)
- [AutoGen Context Overflow Roadmap — GitHub Issue #156](https://github.com/microsoft/autogen/issues/156)
- [AutoGen Model Context Management — GitHub Discussion #5006](https://github.com/microsoft/autogen/discussions/5006)
- [Memory — CrewAI Docs](https://docs.crewai.com/en/concepts/memory)
- [Deep Dive into CrewAI Memory Systems — Sparkco](https://sparkco.ai/blog/deep-dive-into-crewai-memory-systems)
- [AI Agent Memory: Comparative Analysis LangGraph, CrewAI, AutoGen — DEV Community](https://dev.to/foxgem/ai-agent-memory-a-comparative-analysis-of-langgraph-crewai-and-autogen-31dp)
- [Persistence — LangChain/LangGraph Docs](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Managing Long Conversations in LangGraph Using Trimming — Medium](https://medium.com/fundamentals-of-artificial-intelligence/managing-long-conversations-in-langgraph-using-trimming-dd9f3142fff0)
- [LangGraph Token Limit Exceeded — GitHub Issue #3717](https://github.com/langchain-ai/langgraph/issues/3717)
- [Solving Context Window Overflow in AI Agents — arXiv 2511.22729](https://arxiv.org/html/2511.22729v1)
- [Multi-Agent Memory from a Computer Architecture Perspective — arXiv 2603.10062](https://arxiv.org/html/2603.10062)
- [Agentic Plan Caching — arXiv 2506.14852](https://arxiv.org/abs/2506.14852)
- [Collaborative Memory: Multi-User Memory Sharing — arXiv 2505.18279](https://arxiv.org/abs/2505.18279)
- [Context Compaction Research: Claude Code, Codex CLI — GitHub Gist](https://gist.github.com/badlogic/cd2ef65b0697c4dbe2d13fbecb0a0a5f)
- [Long-Running AI Agents and Task Decomposition 2026 — Zylos Research](https://zylos.ai/research/2026-01-16-long-running-ai-agents)
- [Subagents: When and How to Use Them — Builder.io](https://www.builder.io/blog/subagents)
- [Code to Tokens Conversion — 16x Prompt](https://prompt.16x.engineer/blog/code-to-tokens-conversion)
- [Context Engineering: Lessons from Building Azure SRE Agent — Microsoft Tech Community](https://techcommunity.microsoft.com/blog/appsonazureblog/context-engineering-lessons-from-building-azure-sre-agent/4481200/)
