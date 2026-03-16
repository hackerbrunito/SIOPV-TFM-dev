# Researcher → Scanner → Parallel Fixer Agent Pipeline
## Best Practices Research Report — March 2026

**Prepared:** 2026-03-16
**Scope:** Automated code quality pipeline design using multi-agent patterns
**Sources:** Web research covering academic papers, framework docs, and production systems (up to March 2026)

---

## Executive Summary

The Researcher → Scanner → Parallel Fixer pipeline is a real and well-documented pattern. It has multiple names across the literature: **"localize-suggest-fix"** (academic, SGAgent 2026), **"fan-out/fan-in"** or **"map-reduce"** (LangGraph), **"parallel worker swarm with synthesizer"** (Google ADK), and **"orchestrator-worker with parallel fixers"** (ComposioHQ, Claude Code). The core idea is identical across all: sequential specialization phases (research/scan) followed by parallel execution (fix) followed by aggregation (reduce/validate).

The pattern is mature enough in 2025–2026 to have production implementations managing 30+ parallel agents (ComposioHQ), published academic benchmarks (SGAgent, HyperAgent), and first-class framework support in LangGraph's Send API.

---

## 1. Is This Pattern Documented? What Is It Called?

### Academic Naming: "Localize–Suggest–Fix" (LSF)

The most precise academic parallel is **SGAgent** (February 2026, arXiv 2602.23647), which explicitly proposes a three-stage pipeline:

1. **Localizer** — scans the repository, identifies bug locations (= Scanner)
2. **Suggester** — gathers context and produces actionable repair suggestions (= Researcher)
3. **Fixer** — applies the patches based on suggestions (= Fixer)

SGAgent frames this as an improvement over the naive "localize-then-fix" paradigm which skips the intermediate reasoning step. With Claude-3.5 as base model, SGAgent achieves **51.3% repair accuracy** on SWE-Bench — evidence this structured pipeline outperforms single-agent approaches.

The ordering in SGAgent is Localizer → Suggester → Fixer. In the SIOPV pipeline the Researcher precedes the Scanner (inverted from SGAgent), which is also valid when documentation must be fetched before scanning begins.

### Framework Naming: "Fan-Out/Fan-In" or "Map-Reduce"

LangGraph, Google ADK, and AutoGen all use the term **map-reduce** for the pattern where:
- A **"map" phase** dynamically creates N parallel worker agents (fan-out)
- A **"reduce" phase** aggregates all results into a single state (fan-in)

Google ADK's documentation (January 2026) provides the clearest named example: a `CodeReviewSwarm` with three parallel specialist agents (SecurityAuditor, StyleEnforcer, PerformanceAnalyst) feeding a PRSummarizer reducer.

### Industry Naming: "Orchestrator-Worker with Parallel Fixers"

ComposioHQ's Agent Orchestrator (open-sourced 2025), OpenHands Refactor SDK (November 2025), and Claude Code's agent teams all use **orchestrator-worker** terminology. The orchestrator plans and dispatches; workers (fixers) execute in parallel on isolated workspaces.

### Summary of Names

| Context | Name Used |
|---------|-----------|
| Academic (SGAgent 2026) | Localize–Suggest–Fix (LSF) |
| Academic (FixAgent 2024) | Localizer–Repairer–Revisitor |
| LangGraph | Map-Reduce / Fan-Out Fan-In |
| Google ADK | Parallel Fan-Out/Gather with Synthesizer |
| OpenHands | Parallel Agent Refactor with Fixer/Verifier |
| ComposioHQ | Orchestrator-Worker (parallel agents + worktrees) |
| Claude Code | Orchestrator → Parallel Subagents |

The SIOPV pipeline most closely matches the **"Orchestrator → Researcher → Scanner → Parallel Workers → Reducer"** variant of the map-reduce pattern.

---

## 2. Passing Findings from Scanner to Multiple Fixer Agents

### The Core Problem

The Scanner produces a list of findings (violations, issues, patterns). These findings must be partitioned and distributed to N parallel fixer agents. There are two architectures:

### Option A: Shared File (JSON manifest)

The Scanner writes a single structured findings file. The orchestrator reads it and partitions by fixer index. Each fixer receives only its slice.

```
Scanner writes:
  .ignorar/findings/scan-{timestamp}.json
  [
    {"file": "src/a.py", "line": 12, "rule": "E501", "fixer_id": 0},
    {"file": "src/b.py", "line": 44, "rule": "ANN201", "fixer_id": 1},
    ...
  ]

Orchestrator reads → partitions → spawns Fixer-0, Fixer-1, ..., Fixer-N
Each fixer receives: its partition slice as inline context OR path to its slice file
```

**Pros:** Persistent audit trail, easy replay, human-readable, zero IPC complexity.
**Cons:** Requires orchestrator to read the file before dispatching (one extra step).

This is the pattern used by:
- Claude Code's own multi-agent docs: "It's crucial to have each sub-agent save its output to a distinct file" as a clear audit trail
- OpenHands Refactor SDK: task list file is the coordination mechanism
- ComposioHQ: shared task queue with agent claim/mark-complete semantics

### Option B: Message Passing (LangGraph Send API)

In LangGraph, the `Send()` API dispatches work directly from a node to parallel child nodes, passing state inline. No intermediate file needed.

```python
def dispatch_fixers(state: ScanState) -> list[Send]:
    findings = state["findings"]
    batch_size = 8  # findings per fixer
    batches = [findings[i:i+batch_size] for i in range(0, len(findings), batch_size)]
    return [Send("fixer_node", {"batch": batch, "batch_id": i})
            for i, batch in enumerate(batches)]

graph.add_conditional_edges("scanner", dispatch_fixers)
```

**Pros:** Native LangGraph support, no filesystem dependency, cleaner state management.
**Cons:** In-memory only (no audit trail), harder to resume on partial failure.

### Recommendation for SIOPV

**Use hybrid**: Scanner writes a JSON findings file (for audit + replay). Orchestrator reads it, partitions, and passes each partition **inline** to fixer agents via prompt/task content — not by having fixers re-read the file independently. This gives both auditability and clean isolation.

---

## 3. Optimal Number of Parallel Fixers vs. Findings Per Fixer

### Published Constraints

From research across Claude Code docs, LangGraph forums, and OpenHands:

| Constraint | Value | Source |
|-----------|-------|--------|
| Claude Code Task parallelism cap | 10 concurrent tasks | Claude Code docs |
| ComposioHQ orchestrator tested at | 30 concurrent agents | pkarnal.com blog |
| LangGraph Send API | No hard limit, runtime-bound | LangGraph docs |
| Context window practical limit | ~50K tokens per agent | Redis context overflow 2026 |
| Findings per fixer sweet spot | 5–15 (median: 8) | Derived from context analysis |

### Context Window Math

Each fixer agent needs:
- System prompt / instructions: ~2K tokens
- Shared foundation data (file contents being fixed): ~10–30K tokens
- Its batch of findings (descriptions + locations): ~1–3K tokens per finding
- Buffer for fix output: ~5K tokens

At ~200 tokens per finding + file context, **8 findings per fixer** keeps total context under 40K tokens with headroom. At 15 findings, context fills to ~50K — still safe for Sonnet (200K window) but approaching practical working limit.

### Formula for Fixer Count

```
fixer_count = ceil(total_findings / findings_per_fixer)
findings_per_fixer = 8   # conservative default
max_parallel = 10        # Claude Code cap, or 30 for dedicated infra

# Example: 47 findings → ceil(47/8) = 6 fixers (well within cap)
# Example: 120 findings → ceil(120/8) = 15 fixers → cap at 10, use 12/fixer
```

### Recommended Wave Configuration

**For SIOPV's `/verify` pipeline (typical scan: 20–80 findings):**

| Scenario | Findings | Fixers | Findings/Fixer |
|----------|----------|--------|----------------|
| Light scan | ≤ 20 | 3 | 5–7 |
| Normal scan | 21–60 | 5–8 | 7–9 |
| Heavy scan | 61–120 | 10 | 10–12 |
| Very heavy | > 120 | 10 (batched waves) | 12 + second wave |

**Never exceed 10 fixers in parallel in Claude Code without dedicated infra.**
If findings exceed 80, use **two sequential waves** of 10 fixers each rather than one wave of 20.

---

## 4. Orchestrator Aggregation and Completeness Validation

### The Reduce Phase

After all parallel fixers complete, the orchestrator must:
1. Collect all fixer output reports
2. Verify every finding was addressed
3. Validate no findings were accidentally skipped
4. Run final linter/mypy to confirm fixes are valid

### Completeness Validation Pattern

The orchestrator tracks a **findings manifest** with status per finding:

```json
{
  "total_findings": 47,
  "findings": [
    {"id": "F-001", "file": "src/a.py", "rule": "E501", "status": "fixed", "fixer_id": 0},
    {"id": "F-002", "file": "src/b.py", "rule": "ANN201", "status": "fixed", "fixer_id": 1},
    {"id": "F-015", "file": "src/c.py", "rule": "UP007", "status": "skipped", "fixer_id": 2}
  ]
}
```

The orchestrator checks: `len([f for f in findings if f["status"] == "fixed"]) == total_findings`

Any `skipped` or missing entries trigger a **retry wave** for just those findings.

### LangGraph Reduce Implementation

```python
# State uses operator.add reducer for thread-safe aggregation
class PipelineState(TypedDict):
    findings: list[Finding]
    fixed_results: Annotated[list[FixResult], operator.add]  # reducer

# After all Send() workers finish, fixed_results contains all N results
# Reducer node validates completeness
def reducer(state: PipelineState) -> PipelineState:
    expected = len(state["findings"])
    actual = len(state["fixed_results"])
    if actual < expected:
        # trigger retry for missing findings
        ...
```

### Cross-Framework Pattern (ADK, AutoGen)

Google ADK uses a `Synthesizer` agent that runs after the ParallelAgent block completes. AutoGen uses a `GroupChatManager` with `SpeakAfterAll` to trigger the reducer only when all workers have spoken.

### Retry Strategy

If a fixer fails or skips a finding:
1. Log the finding as `unresolved`
2. After the reduce phase, spawn a **single cleanup fixer** for all unresolved findings
3. Run verification again on those files only
4. If still unresolved after 2 retries: escalate to human

---

## 5. Published Examples in LangGraph, AutoGen, CrewAI, Claude Code

### LangGraph (Official)

The LangGraph how-to guide "How to create map-reduce branches for parallel execution" is the canonical reference. The Send API is the primary mechanism. Key insight: each worker gets **independent state**, not a copy of the full graph state — this prevents inter-worker interference.

Reference: https://langchain-ai.github.io/langgraphjs/how-tos/map-reduce/
Scaling analysis: https://aipractitioner.substack.com/p/scaling-langgraph-agents-parallelization

### Google ADK (Production-Ready Example)

The `CodeReviewSwarm` example in ADK docs is the clearest published Researcher→Scanner→ParallelFixers analog in production tooling (January 2026).

```python
code_review_pipeline = SequentialAgent(
    name="CodeReviewPipeline",
    sub_agents=[
        # Phase 1: Research + Scan (sequential)
        SequentialAgent(sub_agents=[researcher_agent, scanner_agent]),
        # Phase 2: Parallel fix
        ParallelAgent(
            name="FixerSwarm",
            sub_agents=[fixer_0, fixer_1, fixer_2, fixer_3]
        ),
        # Phase 3: Reduce + validate
        synthesizer_agent,
    ]
)
```

Reference: https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/

### CrewAI

CrewAI's crew-based approach uses hierarchical process mode, where a manager agent delegates to workers. For code review, the documented pattern uses a `Senior Code Reviewer` agent and an `Executor` agent in sequence. CrewAI does not natively support true parallel fan-out in the same way LangGraph does — it approximates it with async task execution.

Reference: https://medium.com/@mtshomsky/crewai-using-agents-to-code-part3-code-reviews-93d52f2a384d

### Claude Code (Native Agent Teams)

Claude Code's `Task` tool dispatches subagents. The orchestrator-worker pattern is explicitly recommended:
- Orchestrator (Opus): plans, dispatches, validates
- Workers (Sonnet): execute fix tasks in parallel (up to 10 concurrent)
- Each worker saves its report to a distinct file for the orchestrator to read

Reference: https://code.claude.com/docs/en/sub-agents
Scaling guide: https://dev.to/bredmond1019/multi-agent-orchestration-running-10-claude-instances-in-parallel-part-3-29da

### OpenHands Refactor SDK (Production Scale)

The most mature production implementation for code refactoring at scale. Uses:
- A task list file as the coordination artifact
- Parallel agents each claiming tasks from the list
- Fixers and verifiers defined as LLM prompts or executable scripts
- No conflict protection needed because fixers claim-and-lock tasks

Reference: https://openhands.dev/blog/automating-massive-refactors-with-parallel-agents

---

## 6. The Map-Reduce Pattern for Agent Teams

### Formal Definition

Map-reduce for agents is a two-phase pattern:

**Map phase (fan-out):**
- An orchestrator node inspects a work manifest (findings list, file list, etc.)
- It dynamically creates N parallel tasks, one per work item or batch
- Each worker receives an isolated, independent state slice
- Workers execute concurrently with no inter-worker communication

**Reduce phase (fan-in):**
- All N workers complete (barrier synchronization)
- A reducer node collects and aggregates all worker outputs
- The reducer validates completeness and produces a consolidated result
- The orchestrator uses the consolidated result to decide next steps

### Why "Dynamic" Matters

The key innovation of LangGraph's Send API and similar mechanisms is that **N is not known at design time**. The number of parallel workers is determined at runtime from the findings list length. This is critical for code pipelines where scan results vary.

### LangGraph Map-Reduce in Three Lines

```python
# Fan-out: distribute findings dynamically
graph.add_conditional_edges("scanner", lambda s: [
    Send("fixer", {"finding": f}) for f in s["findings"]
])
# Fan-in: reducer waits for all fixer nodes via state reducer
graph.add_edge("fixer", "reducer")
```

The `operator.add` reducer on `fixed_results` in the state schema ensures thread-safe accumulation of results from all parallel fixer invocations.

### Superstep Semantics

LangGraph executes all nodes dispatched in the same fan-out as a single "superstep". All fixer nodes run concurrently within that superstep. The reducer only fires after all fixers in the superstep complete — this provides implicit barrier synchronization without explicit coordination.

---

## 7. Conflict Prevention for Parallel File Editors

### The Core Risk

If Fixer-0 and Fixer-3 both need to modify `src/utils.py`, they will produce conflicting edits. This is the primary operational risk of parallel fixer pipelines.

### Solution 1: File-Level Partitioning (Recommended)

Partition findings to fixers by **file ownership**. Each file is assigned to exactly one fixer. No two fixers touch the same file.

```python
def partition_by_file(findings: list[Finding], num_fixers: int) -> list[list[Finding]]:
    # Group findings by file
    file_groups: dict[str, list[Finding]] = {}
    for f in findings:
        file_groups.setdefault(f.file, []).append(f)

    # Distribute file groups to fixers (bin-packing by count)
    batches = [[] for _ in range(num_fixers)]
    for i, (_, file_findings) in enumerate(sorted(
        file_groups.items(), key=lambda x: -len(x[1])
    )):
        batches[i % num_fixers].extend(file_findings)
    return batches
```

This guarantees zero file conflicts. The trade-off: some fixers may get more files, others fewer. Use a bin-packing sort (largest file group first) to balance load.

### Solution 2: Git Worktrees (Infrastructure-Level Isolation)

Used by ComposioHQ (30 agents), OpenHands, and Claude Code's recommended pattern for large-scale fixes. Each fixer operates in a **separate git worktree** — an isolated copy of the repo on a different branch.

```bash
# Orchestrator sets up worktrees before dispatching fixers
git worktree add .worktrees/fixer-0 -b fix/batch-0
git worktree add .worktrees/fixer-1 -b fix/batch-1
# ...
# Each fixer is told: work in .worktrees/fixer-N/
# After all fixers complete, orchestrator merges branches
```

**Pros:** Absolute isolation, no file conflicts possible, each fixer works on a full independent codebase copy.
**Cons:** Requires post-fix merge (usually trivial if file partitioning was used; complex if same files were touched).

**Best practice (2025–2026):** Combine file partitioning + worktrees. File partitioning eliminates merge conflicts; worktrees provide safety-net isolation for concurrent filesystem writes.

### Solution 3: Read-Only Shared Data, Write-Only Private Data

The orchestrator writes a read-only findings manifest. Each fixer reads from it but writes only to its own output files. Fixers NEVER write directly to source files — they write **patch files** (unified diff format). The orchestrator applies all patches sequentially after all fixers complete.

```
Fixer-0 writes: .ignorar/patches/batch-0.patch
Fixer-1 writes: .ignorar/patches/batch-1.patch
Orchestrator applies: git apply .ignorar/patches/batch-0.patch && git apply .ignorar/patches/batch-1.patch
```

This is the safest approach for CI/CD pipelines where filesystem isolation (worktrees) isn't available.

### Conflict Risk Matrix

| Partitioning Strategy | Same-File Risk | Complexity | Recommended For |
|----------------------|---------------|------------|-----------------|
| Random partition | HIGH | Low | Never |
| Round-robin partition | MEDIUM | Low | Avoid |
| File-level partition | ZERO | Medium | SIOPV default |
| Worktree isolation | ZERO | High | Large refactors (>50 files) |
| Patch-file output | ZERO | Medium | CI/CD pipelines |

---

## 8. Concrete Wave Configuration for SIOPV `/verify`

### Recommended Pipeline Architecture

```
Phase 1 (Sequential):
  RESEARCHER
  └── Fetches docs from Context7 for all libraries in use
  └── Output: .ignorar/findings/library-facts-{timestamp}.json

  SCANNER (reads library-facts)
  └── Runs ruff check, mypy, custom hex-arch scanner
  └── Output: .ignorar/findings/scan-{timestamp}.json
     [{"id": "F-001", "file": "...", "rule": "...", "category": "ruff|mypy|hexarch"}]

Phase 2 (Orchestrator reads scan output, partitions by file):
  DISPATCH
  └── Groups findings by file ownership
  └── Creates N batches (target: 8 findings/fixer, max: 10 fixers)

Phase 3 (Parallel, all fixers run concurrently):
  FIXER-0  → fixes files assigned to batch-0
  FIXER-1  → fixes files assigned to batch-1
  ...
  FIXER-N  → fixes files assigned to batch-N
  Each fixer outputs: .ignorar/findings/fixed-batch-{N}-{timestamp}.json

Phase 4 (Sequential):
  REDUCER
  └── Reads all fixed-batch files
  └── Cross-references against scan manifest
  └── Identifies unresolved findings
  └── Runs: ruff check && mypy (fast validation)
  └── Output: .ignorar/findings/reduction-report-{timestamp}.json

  [If unresolved > 0]: CLEANUP FIXER (single agent, all unresolved)
  VERIFIER (runs full /verify suite)
```

### Fixer Count Decision Logic

```python
def decide_fixer_count(findings: list, max_fixers: int = 10) -> tuple[int, int]:
    """Returns (fixer_count, findings_per_fixer)."""
    IDEAL_BATCH = 8
    needed = math.ceil(len(findings) / IDEAL_BATCH)
    fixer_count = min(needed, max_fixers)
    findings_per_fixer = math.ceil(len(findings) / fixer_count)
    return fixer_count, findings_per_fixer

# Examples:
# 12 findings → 2 fixers, 6 each
# 47 findings → 6 fixers, 8 each
# 80 findings → 10 fixers, 8 each
# 120 findings → 10 fixers, 12 each (or two waves)
```

### Per-Fixer Prompt Template

```
You are Fixer-{N} in a parallel code quality pipeline.

CONTEXT (library facts for the files you are fixing):
{relevant_library_facts}  # Only facts for libraries in your assigned files

YOUR ASSIGNED FINDINGS ({count} items):
{findings_json_slice}

CONSTRAINTS:
- Fix ONLY the files listed in your findings
- Do NOT touch any file not in your list
- For each finding: apply the minimum change that resolves the violation
- After fixing, verify: ruff check {your_files} && mypy {your_files}
- Save your completion report to: .ignorar/findings/fixed-batch-{N}-{timestamp}.json
  Format: [{"id": "F-XXX", "status": "fixed|skipped", "note": "..."}]
```

### Recommended Model Selection

| Role | Model | Reason |
|------|-------|--------|
| Researcher | claude-sonnet-4-6 | Handles Context7 queries, structured output |
| Scanner | claude-haiku-3-5 | Fast file reads, no generation needed |
| Orchestrator | claude-sonnet-4-6 | Partitioning logic, dispatch decisions |
| Fixer | claude-sonnet-4-6 | Code generation quality needed |
| Reducer | claude-haiku-3-5 | Simple aggregation, manifest comparison |
| Cleanup Fixer | claude-sonnet-4-6 | Harder cases that initial fixers skipped |

---

## 9. File-Based vs. Message-Based Result Passing: Summary

### File-Based (Recommended for SIOPV)

**Use when:** Audit trail required, partial failures need replay, human inspection needed, cross-session coordination.

| Aspect | Detail |
|--------|--------|
| Scanner output | `scan-{timestamp}.json` with all findings |
| Fixer output | `fixed-batch-{N}-{timestamp}.json` per fixer |
| Reducer reads | All `fixed-batch-*` files |
| Failure recovery | Re-run failed fixer only; others' outputs persist |
| Audit | Full history of what each fixer did |

### Message-Based (LangGraph Send API)

**Use when:** In-memory pipeline, no intermediate persistence needed, same-session execution.

| Aspect | Detail |
|--------|--------|
| Scanner output | In-graph state `findings: list[Finding]` |
| Dispatch | `Send("fixer", {"batch": batch})` per batch |
| Fixer output | Accumulates into `fixed_results: Annotated[list, operator.add]` |
| Failure recovery | Full pipeline re-run required |
| Audit | Only available via LangSmith tracing |

### Hybrid Pattern (Best of Both)

Use file-based for scanner output (persistent, human-readable JSON manifest) and message-based for fixer dispatch (inline batch in Task prompt). Fixers write their completion reports to files (for reducer to read). This is the pattern Claude Code's own multi-agent documentation recommends.

---

## 10. Key Takeaways for SIOPV Implementation

1. **The pattern has a name**: "Localize–Suggest–Fix" (academic), "Fan-Out/Fan-In Map-Reduce" (LangGraph), "Parallel Worker Swarm" (ADK). Use these names in code comments and docs.

2. **Always partition by file ownership**: The single most important conflict-prevention measure. Never assign the same file to two fixers.

3. **8 findings per fixer is the sweet spot**: Enough work per fixer to amortize prompt overhead; small enough to stay well within context limits.

4. **Max 10 parallel fixers in Claude Code**: Hard limit from the Task tool. For >80 findings, use two sequential waves of 10.

5. **Save scan results to a JSON file**: Enables replay, auditing, and partial retry. This is the industry-standard coordination artifact.

6. **Reducer must verify completeness**: Cross-reference all `finding.id` values against `fixed_results.id` before declaring success. Never assume all fixers succeeded.

7. **Retry is a single-agent cleanup pass**: When a fixer skips or fails, the orchestrator collects all unresolved findings and sends them to a single cleanup fixer — not another parallel wave (too few items to justify parallelism).

---

## Sources

- [SGAgent: Suggestion-Guided Multi-Agent Software Repair (arXiv 2602.23647)](https://arxiv.org/abs/2602.23647)
- [FixAgent: Hierarchical Multi-Agent Framework for Unified Software Debugging](https://arxiv.org/html/2404.17153v2)
- [HyperAgent: Generalist Software Engineering Agents (arXiv 2409.16299)](https://arxiv.org/abs/2409.16299)
- [Developer's Guide to Multi-Agent Patterns in ADK — Google Developers Blog](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/)
- [Parallel Agents — Google ADK Docs](https://google.github.io/adk-docs/agents/workflow-agents/parallel-agents/)
- [Google's Eight Essential Multi-Agent Design Patterns — InfoQ](https://www.infoq.com/news/2026/01/multi-agent-design-patterns/)
- [How to Create Map-Reduce Branches for Parallel Execution — LangGraph Docs](https://langchain-ai.github.io/langgraphjs/how-tos/map-reduce/)
- [Scaling LangGraph Agents: Parallelization, Subgraphs, and Map-Reduce Trade-Offs](https://aipractitioner.substack.com/p/scaling-langgraph-agents-parallelization)
- [Map-Reduce with the Send() API in LangGraph](https://medium.com/ai-engineering-bootcamp/map-reduce-with-the-send-api-in-langgraph-29b92078b47d)
- [LangGraph Best Practices — Swarnendu De](https://www.swarnendu.de/blog/langgraph-best-practices/)
- [Automating Massive Refactors with Parallel Agents — OpenHands](https://openhands.dev/blog/automating-massive-refactors-with-parallel-agents)
- [The OpenHands Software Agent SDK (arXiv 2511.03690)](https://arxiv.org/html/2511.03690v1)
- [Open-Sourcing Agent Orchestrator: Effectively Manage 30 Parallel Agents](https://pkarnal.com/blog/open-sourcing-agent-orchestrator)
- [ComposioHQ Agent Orchestrator — GitHub](https://github.com/ComposioHQ/agent-orchestrator)
- [Git Worktrees: The Secret Weapon for Running Multiple AI Coding Agents in Parallel](https://medium.com/@mabd.dev/git-worktrees-the-secret-weapon-for-running-multiple-ai-coding-agents-in-parallel-e9046451eb96)
- [Codex App Worktrees Explained: How Parallel Agents Avoid Git Conflicts](https://www.verdent.ai/guides/codex-app-worktrees-explained)
- [Create Custom Subagents — Claude Code Docs](https://code.claude.com/docs/en/sub-agents)
- [Claude Code Sub-Agents: Parallel vs Sequential Patterns](https://claudefa.st/blog/guide/agents/sub-agent-best-practices)
- [Multi-Agent Orchestration: Running 10+ Claude Instances in Parallel](https://dev.to/bredmond1019/multi-agent-orchestration-running-10-claude-instances-in-parallel-part-3-29da)
- [Orchestrator-Worker Agents: A Practical Comparison — Arize AI](https://arize.com/blog/orchestrator-worker-agents-a-practical-comparison-of-common-agent-frameworks/)
- [AutoGen v0.4 — Microsoft Research](https://www.microsoft.com/en-us/research/wp-content/uploads/2025/01/WEF-2025_Leave-Behind_AutoGen.pdf)
- [Deep Dive into AutoGen Multi-Agent Patterns 2025](https://sparkco.ai/blog/deep-dive-into-autogen-multi-agent-patterns-2025)
- [CrewAI: Using Agents to Code — Code Reviews](https://medium.com/@mtshomsky/crewai-using-agents-to-code-part3-code-reviews-93d52f2a384d)
- [Introducing Aardvark: OpenAI's Agentic Security Researcher](https://openai.com/index/introducing-aardvark/)
- [Fixing Security Vulnerabilities with AI — GitHub Blog](https://github.blog/engineering/platform-security/fixing-security-vulnerabilities-with-ai/)
- [Context Window Overflow in 2026 — Redis](https://redis.io/blog/context-window-overflow/)
- [Multi-Agent Coding: Parallel Development Guide](https://www.digitalapplied.com/blog/multi-agent-coding-parallel-development)
- [Advanced Claude Code Techniques — Multi-Agent Workflows and Parallel Development](https://medium.com/@salwan.mohamed/advanced-claude-code-techniques-multi-agent-workflows-and-parallel-development-for-devops-89377460252c)
