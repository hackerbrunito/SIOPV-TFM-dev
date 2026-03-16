# Orchestrator Planning Best Practices — Research Report
**Date:** 2026-03-13
**Topic:** Claude Code multi-agent orchestrator planning, context preservation, and round-boundary management
**Sources:** Anthropic official docs, Claude Code docs, community implementations, GitHub projects

---

## Executive Summary (6 lines)

1. **Split-planning pattern** is documented but niche — the established default is a single orchestrator that reads input and writes a plan file itself; sub-agent planners add coordination overhead and are only justified when plan sections are truly independent and can be generated in parallel (e.g., 4 independent module plans with no cross-dependencies).

2. **Orchestrator-as-planner-only** is the dominant pattern validated by Anthropic's own multi-agent research system: the lead agent reads input, generates a plan (optionally saving it to a file for persistence), then coordinates workers — keeping the orchestrator context clean of implementation noise.

3. **2,000 lines of input consumes roughly 10,000–20,000 tokens** (estimate: ~5–10 tokens/line for markdown/documentation), which is 5–10% of a 200k context window — this is not a real risk; the orchestrator retains 80–90% of its 200k window free for planning + coordination work.

4. **Complexity threshold for split-planning:** Use a single orchestrator for plans up to ~4 rounds / ~20 tasks with homogeneous sections. Switch to sub-planner delegation only when the planning work itself is independently parallelizable (different domain knowledge per section), involves 10+ distinct plan sections, or would produce a plan exceeding ~50k tokens on its own.

5. **Round-boundary context management:** The verified best practice is the "plan file as shared truth" pattern — orchestrator writes a persistent plan file before Round 1 begins, each round reads only the plan file + current status, and sub-agents return lightweight summaries (not full outputs) to the orchestrator. This prevents context accumulation across rounds.

6. **Opus 4.6 reality:** Default context is 200k tokens (1M is beta/premium). Claude Code reserves 33k–45k tokens as a buffer, leaving ~155k–167k usable tokens. Planning from 2,000 lines of input plus a 4-round execution plan easily fits; the orchestrator only risks context exhaustion if it accumulates full sub-agent outputs + all round execution logs in its conversation history.

---

## Question 1: Split-Planning Pattern

### Is spawning sub-planners a known pattern?

**Yes, but it is a secondary pattern, not the default.**

The established architecture from Anthropic's multi-agent research system uses a **single orchestrator with distributed execution subagents**. The lead agent "analyzes the input, develops a strategy, and spawns subagents" — planning stays in the orchestrator, execution is delegated.

The split-planning pattern (spawning sub-planners for each section) does appear in community implementations:
- Gas Town's "mayor" agent and Multiclaude's "supervisor" agent both delegate execution, not planning
- The Composio agent-orchestrator project and ruflo both use a single planner with parallel workers
- No Anthropic-published pattern explicitly recommends spawning sub-agents to produce sub-plans

### Trade-offs

| Factor | Single Orchestrator Plans Everything | Split Planning via Sub-Agents |
|--------|--------------------------------------|-------------------------------|
| Coordination overhead | Low (single context, no messaging) | High (each sub-plan requires spawn, execute, synthesize cycle) |
| Context consumed by planning | ~10–30k tokens for 4 rounds | ~5k orchestrator + 4× subagent sessions (much higher total cost) |
| Cross-section coherence | Guaranteed (single planner sees all) | Requires synthesis step; risks inconsistency |
| Parallelism benefit | None (planning is sequential reasoning) | Only if plan sections are truly independent domains |
| When justified | Most cases | Only when 10+ truly independent plan sections with domain-specific knowledge |

**Verdict:** Split planning adds significant coordination overhead and is rarely justified for 4-round execution plans. A single orchestrator writing a plan file is simpler, cheaper, and more coherent.

---

## Question 2: Orchestrator-as-Planner-Only Pattern

### Is it better to keep the orchestrator as a pure planner?

**Yes — this is the Anthropic-recommended pattern.**

Anthropic's own multi-agent research system explicitly implements the "pure planner" separation:
- Lead agent reads input → generates strategy → saves plan to memory/file → spawns workers
- Workers execute and return lightweight results (not full execution logs)
- Lead synthesizes based on plan + summaries

The key insight from Anthropic's engineering blog: *"By persisting research plans in Memory, the system can maintain task continuity even when context is truncated."* This is the plan-file pattern — the plan is the orchestrator's source of truth, not its conversation history.

### Why this works for a 200k context orchestrator

The orchestrator's 200k context is consumed by:
- Static overhead: system prompt, tools, CLAUDE.md (~28k tokens)
- Input brief: ~10–20k tokens (2,000 lines)
- Plan generation: ~5–15k tokens
- Round status updates: ~1–5k per round × 4 rounds = ~4–20k
- Sub-agent summaries: ~0.5–2k per sub-agent × N agents

Total for a well-managed 4-round orchestration: ~50–85k tokens, leaving 70–115k tokens free. The orchestrator-as-planner pattern is safe within 200k.

**The risk is not planning — it is accumulating full sub-agent outputs.** If the orchestrator receives verbose sub-agent reports (5,000+ tokens each) across 4 rounds with 5+ agents per round, it can consume 100k+ tokens in conversation history, crowding out planning reasoning.

---

## Question 3: Context Consumption Reality

### How many tokens does 2,000 lines of input actually consume?

**Empirical estimate based on Claude tokenization rules:**

- Claude tokenizes at approximately 4 characters per token
- Markdown documentation: ~50–80 characters per line average (including headings, code blocks, whitespace)
- 2,000 lines × 65 chars average = 130,000 characters ÷ 4 = **~32,500 tokens**
- Dense code: ~30–50 chars/line → **~15,000–25,000 tokens** for 2,000 lines
- Mixed markdown/code brief: **~20,000–35,000 tokens**

### As a percentage of orchestrator context

| Context limit | Reserved buffer | Usable tokens | 2k-line input % of usable |
|---------------|----------------|---------------|--------------------------|
| 200k (default) | 33k–45k | 155k–167k | 12–23% |
| 1M (beta) | ~45k | ~955k | 2–4% |

**Conclusion:** Reading 2,000 lines of input files consumes roughly 15–23% of a 200k orchestrator's usable context. This is not a risk for planning. The orchestrator has 77–85% of its context window free after loading the input brief.

**Note on the 200k vs. 1M question:** The 1M token context for Opus 4.6 is currently in beta and requires a specific API header plus premium pricing ($10/$37.50 per million tokens). The standard Claude Code session uses 200k. Planning from 2,000-line input is comfortable at 200k; 1M is unnecessary.

---

## Question 4: Established Orchestrator Patterns and Complexity Thresholds

### What do best practices say about when to split planning?

**From official Claude Code docs and Anthropic engineering blog:**

1. **Default to single orchestrator** for tasks with up to ~20 tasks across 4 rounds
2. **Use agent teams** when teammates need to share findings, challenge each other, or coordinate — not for splitting planning
3. **3–5 teammates** is the recommended team size for most workflows
4. **Token cost reality:** A 3-teammate team uses 3–4× the tokens of a single sequential session; 15× more tokens than a simple chat

### Complexity thresholds (synthesized from multiple sources)

| Scenario | Recommendation |
|----------|---------------|
| 1–4 rounds, homogeneous work sections | Single orchestrator plans everything |
| 4–8 rounds, mostly independent sections | Single orchestrator + parallel execution subagents |
| 8+ rounds OR 10+ independent plan sections with domain-specific knowledge | Consider split planning into sub-planners |
| Sub-agents need to communicate and challenge each other | Agent teams |
| Sequential tasks with shared state | Single session or subagents (not teams) |

**The coordination overhead threshold:** A 3-agent team adds ~50% coordination overhead (messaging, task list management, context synchronization). Split planning only breaks even when each sub-plan section would take more than 50% of an orchestrator's planning budget — which almost never happens for 4-round plans.

### Community-validated thresholds

From ClaudeFast's 5-tier complexity routing system:
- Tiers 1–3 (routine to moderately complex): Single agent or subagents
- Tier 4 (multi-domain, parallelizable): Agent teams with shared task list
- Tier 5 (enterprise scale, 10+ independent workstreams): Split orchestrators with hierarchical coordination

A 4-round audit/remediation plan for a single codebase falls squarely in Tier 3–4, where a single orchestrator is appropriate.

---

## Question 5: Round-Boundary Context Management

### Best practice for orchestrator handling context across Round 1 → Round 2 → Round 3 → Round 4

Multiple sources converge on the same architecture:

### Pattern: Plan File as Shared Truth + Lightweight Round Summaries

```
[Before Round 1]
Orchestrator reads full input brief (20k–35k tokens)
Orchestrator generates and WRITES plan file to disk
  → plan-file.md contains: objectives, round definitions, success criteria per round
Orchestrator context now: static overhead + input brief + plan = ~50–65k tokens used

[Round 1 execution]
Orchestrator spawns sub-agents with focused context (plan section only, not full brief)
Sub-agents return SUMMARY not full output (500–1,500 tokens each)
Orchestrator updates task list status
Orchestrator writes Round 1 checkpoint file to disk
  → round1-checkpoint.md: what was done, what's blocked, what's ready for Round 2

[Round 2 execution]
Orchestrator reads plan file + round1-checkpoint (NOT full conversation history)
Orchestrator spawns Round 2 sub-agents
...repeat pattern...

[If context grows too large]
Orchestrator runs /compact BEFORE hitting 83.5% threshold
  → Auto-compaction at 83.5% is lossy; manual /compact at 50% preserves full fidelity
  → The plan file + checkpoint files survive compaction (they're on disk)
  → After compaction, orchestrator re-reads plan file to restore strategic context
```

### Why this works

1. **Plan file survives compaction** — stored on disk, not in conversation history
2. **Round checkpoint files** — allow the orchestrator to recover full state after compaction
3. **Lightweight summaries** — sub-agents return 500–1,500 token summaries, not 5,000–15,000 token reports
4. **Context stays flat** — each round adds ~2,000–5,000 tokens to orchestrator context (summaries + status), not 20,000–50,000 tokens (full reports)

### Token budget for 4-round orchestration (200k context)

| Component | Tokens |
|-----------|--------|
| Static overhead (system prompt, tools, CLAUDE.md) | 28,000 |
| Input brief (2,000 lines) | 20,000–35,000 |
| Plan generation | 5,000–15,000 |
| Round 1–4 summaries (5 agents × 4 rounds × 1,500 tokens) | 30,000 |
| Task list updates + status messages | 5,000–10,000 |
| **Total estimated** | **88,000–118,000** |
| **Buffer remaining** | **37,000–79,000** |

This is comfortably within 200k. The orchestrator will not run out of context across 4 rounds if it receives summaries (not full reports) and uses the plan file + checkpoint file pattern.

### The "context rot" risk

Research (cited in Claude Code community) shows LLM performance degrades 20–50% as context grows from 10k to 100k+ tokens. This "context rot" is distinct from running out of context — it's degraded reasoning quality from long conversation history.

**Mitigation:** Manual `/compact` at 50% context usage (not waiting for the 83.5% auto-compact threshold). The orchestrator should proactively compact after Round 2, then reload the plan file. This resets conversation history while preserving strategic intent via the disk-persisted plan file.

---

## Question 6 (Additional): Verified Patterns from Community Implementations

### Continuous-Claude v3 (parcadei)
- **Ledgers** (`thoughts/ledgers/CONTINUITY_*.md`) — capture decision rationale across sessions
- **Handoffs** (`thoughts/shared/handoffs/*.yaml`) — YAML-serialized state for session boundaries, described as "more token-efficient than conversation compaction"
- **TLDR code analysis** — 5-layer semantic compression reduces file-read overhead by ~95% (1,200 tokens vs. 23,000 raw)
- **Plans** persisted to `thoughts/shared/plans/*.md`

### Anthropic Multi-Agent Research System
- LeadResearcher saves plan to Memory before context exceeds 200k
- Agents retrieve stored context (plan) from memory rather than losing it to truncation
- Agents store outputs in external artifact systems; pass lightweight references back

### ClaudeFast Sub-Agent Best Practices
- Sub-agents receive "minimum viable context" — only files relevant to their specific task
- Each sub-agent has a full invocation spec: scope, file references, success criteria, output format
- Parallel dispatch for 3+ unrelated tasks with no file overlap
- Sequential dispatch when tasks share state

---

## Recommendations for Stage 4.1 Orchestrator

Based on this research, the following recommendations apply to the SIOPV Stage 4.1 orchestrator:

1. **Do not split planning.** The orchestrator should read all input files and write a complete plan file itself. The 2,000 lines of input (stage3.5 brief + related docs) consume ~20,000–35,000 tokens — well within safe limits for a 200k context window.

2. **Write a plan file before spawning any sub-agents.** The plan file is the source of truth that survives compaction and round boundaries.

3. **Write a checkpoint file after each round.** Each round should end with the orchestrator writing `round{N}-checkpoint.md` documenting: what was completed, what failed, what's blocked, and inputs required for Round N+1.

4. **Receive summaries from sub-agents, not full reports.** Sub-agents should write full reports to disk (`.ignorar/production-reports/`) and return a 500–1,500 token summary to the orchestrator. This prevents context accumulation.

5. **Compact proactively at 50% context usage.** Do not wait for the 83.5% auto-compact trigger. After Round 2, check context usage and compact if above 50%. Reload the plan file immediately after compaction.

6. **Use the task list for round-boundary coordination.** The shared task list persists across compaction. Sub-agents should mark tasks complete; the orchestrator reads the task list (not conversation history) to determine round status.

---

## Sources

- [Orchestrate teams of Claude Code sessions — Claude Code Docs](https://code.claude.com/docs/en/agent-teams)
- [How we built our multi-agent research system — Anthropic Engineering](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Building Effective AI Agents — Anthropic Research](https://www.anthropic.com/research/building-effective-agents)
- [Shipyard: Multi-agent orchestration for Claude Code in 2026](https://shipyard.build/blog/claude-code-multi-agent/)
- [Claude Code Context Buffer: The 33K-45K Token Problem — ClaudeFast](https://claudefa.st/blog/guide/mechanics/context-buffer-management)
- [Claude Code Sub-Agents: Parallel vs Sequential Patterns — ClaudeFast](https://claudefa.st/blog/guide/agents/sub-agent-best-practices)
- [Claude Code: Tasks persisting between sessions — DEV Community](https://dev.to/simone_callegari_1f56a902/claude-code-new-tasks-persisting-between-sessions-and-swarms-of-agents-against-context-rot-5dan)
- [Hierarchical Orchestration in Claude Code Agent Teams — n1n.ai](https://explore.n1n.ai/blog/hierarchical-orchestration-claude-code-agent-teams-2026-02-27)
- [Continuous-Claude-v3 — GitHub (parcadei)](https://github.com/parcadei/Continuous-Claude-v3)
- [Claude Opus 4.6 — What's New — Anthropic](https://www.anthropic.com/news/claude-opus-4-6)
- [Claude Code Swarm Orchestration Skill — GitHub Gist (kieranklaassen)](https://gist.github.com/kieranklaassen/4f2aba89594a4aea4ad64d753984b2ea)
- [Token counting — Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/token-counting)
