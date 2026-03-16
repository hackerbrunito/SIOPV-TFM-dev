# Multi-Agent Team Architectures for Code Verification Workflows

**Research Date:** 2026-03-16
**Researcher:** Claude Sonnet 4.6 (deep web research agent)
**Scope:** Best practices up to March 2026 — wave/stage patterns, pipeline architectures, team sizing, orchestration strategies

---

## Executive Summary

By March 2026, multi-agent code verification has become a production standard at Anthropic, Qodo, diffray, and Microsoft. The dominant architecture is a two-phase pattern: parallel specialized scanners in Wave 1, followed by an aggregation/judge agent in Wave 2. The consensus across frameworks (Claude Code, AutoGen, CrewAI, LangGraph) converges on 3–5 specialized agents per wave, strict domain isolation per agent, and summarized (not full) context handoffs between waves. "One task per agent" consistently outperforms "batched files per agent" for accuracy, cost, and reliability.

---

## Q1: Best Patterns for Organizing Agent Teams into Waves/Rounds/Stages

### The Canonical Two-Wave Pattern

The industry has converged on a two-wave architecture:

**Wave 1 — Parallel Specialized Scanners (independent, no inter-agent communication)**
- Each agent owns exactly one domain (security, performance, architecture, style, types, etc.)
- All agents run simultaneously; each has its own clean context window
- Each agent returns a structured finding list with severity ranking
- No agent is aware of what other Wave 1 agents are doing

**Wave 2 — Aggregation / Judge Agent (sequential, depends on Wave 1 outputs)**
- Receives all Wave 1 outputs as inputs
- Cross-checks findings for duplicates and conflicts
- Ranks by severity; filters low-confidence items
- Produces the final consolidated report

This is explicitly confirmed by:
- **Anthropic's Code Review tool** (launched March 9, 2026): "spins up multiple specialized agents that work in parallel, with some probing for data-handling errors, off-by-one conditions, and API misuse. After the parallel detection phase, an aggregation agent cross-checks findings across all the specialized agents, removes duplicates, and ranks issues by severity."
- **Qodo 2.0**: "multi-agent expert review architecture, breaking code review into focused responsibilities… a judge agent evaluates findings across agents, resolves conflicts, removes duplicates."
- **diffray**: "10+ specialized AI agents that investigate, verify, and validate code, with each agent focusing on one domain… a validation agent cross-checks each issue against the actual codebase context before it's shown."

### Extended Three-Wave Pattern (for remediation pipelines)

For pipelines that include fixing (not just detection), a third wave is added:

**Wave 3 — Fixer / Remediation Agent (sequential, depends on Wave 2 ranked output)**
- Takes confirmed, ranked findings from Wave 2
- Generates patches or fix suggestions per finding
- May spawn sub-agents per fix to avoid context mixing

Blueprint2Code (Frontiers in AI, 2025) documents this exact three-stage flow: Previewing Agent → Blueprint Agent → Coding Agent → iterative debugging (max 5 rounds).

### Wave Dependencies (Claude Code GSD Framework)

From the Claude Code GSD framework documentation:
> "Independent tasks run in parallel in waves, where dependent tasks wait. Wave 1 might run three plans simultaneously, and Wave 2 waits for Wave 1, then runs."

The dependency rule is simple: if an agent's input depends on another agent's output, it is in the next wave. If agents are fully independent, they run in the same wave.

---

## Q2: The Researcher → Scanner → Comparator/Fixer Pipeline Pattern

### Published Examples

**Microsoft Code Researcher** (Microsoft Research, June 2025) — the closest published implementation of the researcher-scanner-fixer pipeline:
1. **Researcher phase**: analyzes crash context using symbol definition lookups and pattern searches
2. **Scanner/Synthesis phase**: generates patch candidates based on accumulated evidence
3. **Validator/Fixer phase**: validates patches using automated testing mechanisms

**OpenAI Aardvark** (2025, security researcher agent):
1. **Analysis**: creates a full threat model from repository scan
2. **Commit Scanner**: inspects commit-level changes against the threat model
3. **Fixer**: reports and suggests remediation

**HAMY's 9-Agent Code Review System** (Claude Code, February 2026):
- Published open-source slash command `/code-review` for Claude Code
- 9 parallel agents including: Linter & Static Analysis, Code Reviewer (non-obvious issues), Security Reviewer (injection/auth/secrets), Quality & Style Reviewer (complexity/duplication)
- Main agent combines all results into a prioritized summary with a final verdict: "Ready to Merge", "Needs Attention", or "Needs Work"
- Key insight: "closing the loop" — giving AI a way to validate itself dramatically improves outcome quality

**Greptile v3** (late 2025) uses the Anthropic Claude Agent SDK for autonomous code investigation with a similar staged pipeline.

### Pattern Summary

```
Researcher(s) → Scanner(s) → Comparator/Judge → [Fixer(s)]
   [Wave 1a]      [Wave 1b]      [Wave 2]         [Wave 3]
```

In practice, the Researcher and Scanner phases are often collapsed into a single parallel wave of specialized scanner-researchers, each combining domain knowledge (research) with active analysis (scanning).

---

## Q3: How LangChain/AutoGen/CrewAI/Claude Code Organize Agents for Parallel Code Analysis

### LangGraph (LangChain)

LangGraph treats agents as nodes in a stateful graph. For parallel code analysis:
- Independent analyzer nodes fan out simultaneously (LangGraph's built-in parallel execution)
- A supervisor node (LLM) decides which agent nodes to call next using `Command` routing
- Downstream nodes wait for all parallel branches to complete before proceeding
- Built for concurrency: "ten retrieval branches fanning out and then rejoining deterministically"

LangGraph is the strongest choice for workflows where the set of subtasks is not known at start time (dynamic fan-out), which is common in code analysis.

### AutoGen (Microsoft)

AutoGen organizes agents through structured turn-taking (conversational):
- Writer → Critic → Executor → back to Writer (iterative loop)
- Each participant posts a message and waits before reacting
- Excels at iterative refinement: code generation → review → execution → revision
- Less suited for true parallel fan-out (inherently sequential turn structure)
- Better for open-ended problem-solving where the path is unknown upfront

### CrewAI

CrewAI emphasizes a team/crew analogy with role-based agents:
- Orchestrator creates the crew and assigns roles (Author, Security Auditor, Merge Decider)
- Supports parallel task execution and horizontal replication of agents within defined roles
- "One agent generates patches, another audits security implications, a third decides whether to merge"
- Best for predefined, structured workflows where the steps are known in advance
- Team Lead + Teammates pattern mirrors Claude Code's agent team model

### Claude Code (Anthropic)

Two execution models, both published in 2026:

**Subagents** (pre-February 2026):
- Spawned by main session, run in parallel, report results back
- Cannot communicate with each other mid-task
- Each gets a clean 200,000-token context window (no degradation at task 50 vs. task 1)
- Lower token cost; best for focused, isolated tasks
- `isolation: worktree` in frontmatter enables parallel file editing without conflicts

**Agent Teams** (launched February 5, 2026 alongside Opus 4.6):
- One Team Lead + 2–N Teammates
- Teammates can message each other, claim tasks from a shared list, coordinate mid-task
- Recommended: 3–5 teammates for most workflows ("5–6 tasks per teammate keeps everyone productive")
- Teammates cannot spawn sub-teams (by design, to prevent exponential token costs)
- A 3-agent team costs ~2.5× more in tokens but finishes ~2× faster

---

## Q4: Recommended Team Size Per Wave to Avoid Context Overflow

### Authoritative Guidance (Claude Code Docs, February 2026)

> "Start with 3–5 teammates for most workflows, as this balances parallel work with manageable coordination. Having 5–6 tasks per teammate keeps everyone productive without excessive context switching."

### Practical Constraints

1. **Token cost scales linearly**: each agent has its own context window and consumes tokens independently. A 10-agent team costs 10× as much as one agent.
2. **Coordination overhead**: beyond 5–7 parallel agents, the aggregation (Wave 2) agent's context grows large enough to risk overflow when processing all findings.
3. **False positive management**: diffray uses 10+ agents per review but reports it took significant engineering to get their judge agent to reliably handle that volume of inputs.
4. **Start with 1, add only when necessary**: "A common mistake is building a 10-agent system before validating that a single agent can't handle the task. Start with one well-prompted agent, add agents only when you hit clear limitations."

### Recommended Team Sizes by Use Case

| Use Case | Wave 1 Agents | Wave 2 | Total |
|----------|--------------|--------|-------|
| Simple PR review | 3–4 | 1 judge | 4–5 |
| Full code verification (SIOPV-style) | 5–7 | 1 judge | 6–8 |
| Enterprise security scan | 7–10 | 1–2 judges | 8–12 |
| Research preview (Anthropic Code Review) | Multiple (not disclosed) | 1 aggregator | ~5–8 |

### Context Overflow Prevention Techniques

- **Summarized handoffs**: pass compressed summaries (200–500 tokens) between waves, not full agent outputs (5,000–20,000 tokens). "A common mistake is passing entire conversation histories between agents without summarization, causing context overflow and degraded responses."
- **Structured finding objects**: each Wave 1 agent returns a typed JSON list of findings (severity, file, line, description, confidence), not prose. This is parseable at ~50–100 tokens per finding.
- **AGENTS.md / CLAUDE.md scoping**: giving each agent a scoped repository context file rather than the full codebase. However, note the research caveat: "context files tend to reduce task success rates compared to providing no repository context, while also increasing inference cost by over 20%." Prefer scoped, relevant context over comprehensive context dumps.

---

## Q5: How Orchestrators Coordinate Parallel Agents Before Proceeding to Next Wave

### Barrier Synchronization Pattern

The canonical pattern across all frameworks is a **barrier/join** at the end of each wave:

1. Orchestrator dispatches all Wave 1 agents simultaneously
2. Orchestrator waits (blocks) until ALL Wave 1 agents have returned results
3. Only then does the orchestrator pass aggregated results to Wave 2

In LangGraph, this is native: parallel nodes automatically rejoin at the next sequential node. In Claude Code subagents, the main session dispatches all tasks and polls/awaits their completion. In Claude Code Agent Teams, the Team Lead assigns tasks and teammates post results back to the team channel.

### Result Collection Strategies

**Shared State Object** (LangGraph default):
- All agents read from and write to a shared state dict
- Conflict resolution handled by graph-level merge functions
- Best for structured, typed findings

**Task Queue + Claim Model** (Claude Code Agent Teams):
- Team Lead posts a list of tasks to a shared queue
- Teammates claim tasks atomically, preventing duplicate work
- Results posted back to the team communication channel
- Team Lead aggregates once all tasks are claimed and completed

**Report Files** (Claude Code subagents with worktrees):
- Each subagent writes its findings to a dedicated report file (e.g., `.ignorar/production-reports/{agent}/`)
- Orchestrator reads all files after all agents complete
- UUID/timestamp-based naming prevents race conditions in parallel writes

### Timeout and Failure Handling

The evidence recommends:
- Set per-agent timeouts (not global); if one scanner times out, proceed with remaining results and flag the gap
- Do not retry failing agents in a loop; diagnose root cause
- The aggregator (Wave 2) should handle missing Wave 1 inputs gracefully (skip, flag as "could not assess")

---

## Q6: "One Task Per Agent" vs "Batched Files Per Agent"

### Consensus: One Task Per Agent Wins

All published evidence from 2025–2026 favors the **one specialized task per agent** model over batching multiple files or concerns into a single agent's context.

**Evidence:**
- "The best way to manage context is sometimes to isolate it into separate threads or agents, where complex tasks are often divided among multiple sub-agents, each with its own narrow context, rather than one agent trying to juggle a huge combined context." (Azure Architecture Center)
- "Don't orchestrate with LLMs — putting flow control in a prompt introduces failure modes and LLMs are unreliable routers. Workflows are good at sequencing, counting, routing, and retrying." (context engineering research)
- "Context files tend to reduce task success rates compared to providing no repository context, while also increasing inference cost by over 20%." (arXiv 2602.11988, COLM 2025)
- diffray's 87% fewer false positives result was attributed specifically to the one-domain-per-agent design
- Claude Code docs: "Run subagents in parallel only for disjoint slugs (different modules/files)"

**Why one-task-per-agent works better:**

1. **Context clarity**: an agent focused on "find SQL injection vulnerabilities in authentication code" has a tighter prompt and spends no tokens on irrelevant concerns
2. **No false negatives from distraction**: a security agent isn't context-switching between PEP8 checks and JWT validation
3. **Easier debugging**: when a finding is wrong, you know exactly which agent produced it and why
4. **Reliable context size**: a file-scoped or domain-scoped agent predictably uses far less context than a "review everything" agent
5. **Competitive validation**: "instead of asking one agent to get it right, ask three agents to try differently and pick the best outcome. Let them compete."

**When batching is acceptable:**
- When files are small and tightly related (same module, same concern)
- When the task is inherently cross-file (e.g., "check that all usages of X are consistent")
- When cost is the primary constraint and quality can be slightly reduced

---

## Recommended Architecture for SIOPV `/verify` Workflow

Based on all findings, the recommended architecture for a code verification pipeline like SIOPV's `/verify` is:

```
Wave 1 (parallel, ~7 min):
  ├── best-practices-enforcer   → findings.json
  ├── security-auditor          → findings.json
  └── hallucination-detector    → findings.json

Wave 2 (parallel, ~5 min):
  ├── code-reviewer             → findings.json (reads Wave 1 outputs for context)
  └── test-generator            → findings.json

Wave 3 (sequential, ~2 min):
  └── judge/aggregator          → consolidated-report.md (deduplicates, ranks, final verdict)
```

### Key Configuration Decisions

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| Agents per wave | 3–5 maximum | Balances parallelism vs. aggregation context cost |
| Context handoff format | Typed JSON findings list | ~50–100 tokens/finding vs. 5,000+ tokens for prose |
| File scoping per agent | Domain-scoped, not file-batched | Prevents context overflow, reduces false positives |
| Timeout per agent | 10–15 min hard limit | Prevents stale blocks; flag missing results |
| Report persistence | Timestamped files per agent | UUID naming prevents parallel write races |
| Wave synchronization | Barrier (wait for all in wave) | Required for aggregator to have complete inputs |
| Agent team vs. subagents | Subagents for SIOPV `/verify` | Results-only reporting is sufficient; lower cost |
| Judge agent position | After all scanners | Must see all findings before deduplicating |

### Tradeoffs: Parallel vs. Sequential Waves

| Dimension | Fully Parallel (all at once) | Wave-Based (parallel within wave) | Fully Sequential |
|-----------|------------------------------|-----------------------------------|-----------------|
| Speed | Fastest (~7 min) | Moderate (~12 min) | Slowest (~87 min) |
| Cost | Highest (all agents simultaneously) | Balanced | Lowest |
| Context quality | Each agent blind to others | Wave N+1 sees Wave N results | Full context accumulation |
| Aggregation complexity | High (many independent findings) | Moderate (fewer, pre-grouped) | Low (one stream) |
| Recommended for | Simple scans with no interdependencies | Standard verification pipelines | Iterative debugging loops |

The wave-based approach (the SIOPV `/verify` design with Wave 1 + Wave 2) hits the optimal point: Wave 1 parallelism captures speed gains, and Wave 2 having Wave 1 results enables code-reviewers to build on scanner findings without re-discovering them.

---

## Sources

- [Anthropic launches a multi-agent code review tool - The New Stack](https://thenewstack.io/anthropic-launches-a-multi-agent-code-review-tool-for-claude-code/)
- [Scaling Code Review: Multi-Agent Systems for Enterprise Engineering Teams - RKoots](https://rkoots.github.io/blog/2026/03/09/bringing-code-review-to-claude-code/)
- [9 Parallel AI Agents That Review My Code (Claude Code Setup) - HAMY](https://hamy.xyz/blog/2026-02_code-reviews-claude-subagents)
- [Orchestrate teams of Claude Code sessions - Claude Code Docs](https://code.claude.com/docs/en/agent-teams)
- [Best Practices for Claude Code - Claude Code Docs](https://code.claude.com/docs/en/best-practices)
- [Create custom subagents - Claude Code Docs](https://code.claude.com/docs/en/sub-agents)
- [Claude Code Sub-Agents: Parallel vs Sequential Patterns - claudefa.st](https://claudefa.st/blog/guide/agents/sub-agent-best-practices)
- [How to Kill the Code Review - Latent.Space](https://www.latent.space/p/reviews-dead)
- [LLM-Based Multi-Agent Systems for Software Engineering - ACM TOSEM](https://dl.acm.org/doi/10.1145/3712003)
- [CrewAI vs LangGraph vs AutoGen: Choosing the Right Multi-Agent Framework - DataCamp](https://www.datacamp.com/tutorial/crewai-vs-langgraph-vs-autogen)
- [AutoGen vs LangGraph vs CrewAI: Which Agent Framework Holds Up in 2026 - DEV Community](https://dev.to/synsun/autogen-vs-langgraph-vs-crewai-which-agent-framework-actually-holds-up-in-2026-3fl8)
- [Agent Orchestration Patterns: Swarm vs Mesh vs Hierarchical vs Pipeline - DEV Community](https://dev.to/jose_gurusup_dev/agent-orchestration-patterns-swarm-vs-mesh-vs-hierarchical-vs-pipeline-b40)
- [Meet the 10 AI Code Review Agents - diffray](https://diffray.ai/agents/)
- [Single-Agent vs. Multi-Agent Code Review: Why One AI Isn't Enough - Qodo](https://www.qodo.ai/blog/single-agent-vs-multi-agent-code-review/)
- [Introducing Qodo 2.0 and the next generation of AI code review - Qodo](https://www.qodo.ai/blog/introducing-qodo-2-0-agentic-code-review/)
- [Microsoft AI Introduces Code Researcher - MarkTechPost](https://www.marktechpost.com/2025/06/14/microsoft-ai-introduces-code-researcher-a-deep-research-agent-for-large-systems-code-and-commit-history/)
- [Introducing Aardvark: OpenAI's agentic security researcher](https://openai.com/index/introducing-aardvark/)
- [LangGraph Multi-Agent Orchestration Guide 2025 - Latenode](https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/langgraph-multi-agent-orchestration-complete-framework-guide-architecture-analysis-2025)
- [AI Agent Orchestration Patterns - Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)
- [Context Engineering for Coding Agents - Martin Fowler](https://martinfowler.com/articles/exploring-gen-ai/context-engineering-coding-agents.html)
- [Evaluating AGENTS.md - arXiv 2602.11988](https://arxiv.org/html/2602.11988v1)
- [Agentic Engineering: The Complete Guide - NxCode](https://www.nxcode.io/resources/news/agentic-engineering-complete-guide-vibe-coding-ai-agents-2026)
- [Multi-Agent AI Systems Explained - BoilerplateHub](https://boilerplatehub.com/blog/multi-agent-ai-systems)
- [How to Use Claude Code Sub-Agents for Parallel Work - Tim Dietrich](https://timdietrich.me/blog/claude-code-parallel-subagents/)
- [Building a C compiler with a team of parallel Claudes - Anthropic Engineering](https://www.anthropic.com/engineering/building-c-compiler)
- [Your Home for Multi-Agent Development - VS Code Blog](https://code.visualstudio.com/blogs/2026/02/05/multi-agent-development)
- [Shipyard: Multi-agent orchestration for Claude Code in 2026](https://shipyard.build/blog/claude-code-multi-agent/)
- [Claude Code Swarm Orchestration Skill - GitHub Gist (kieranklaassen)](https://gist.github.com/kieranklaassen/4f2aba89594a4aea4ad64d753984b2ea)
- [Blueprint2Code: a multi-agent pipeline for reliable code - Frontiers in AI](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1660912/pdf)
