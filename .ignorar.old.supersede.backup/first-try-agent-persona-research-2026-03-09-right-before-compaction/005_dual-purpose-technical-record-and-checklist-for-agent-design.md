# Dual-Purpose Technical Record and Checklist for Agent Design

**Document type:** Audit record + implementation checklist
**Date of research:** 2026-03-09
**Project:** SIOPV (Sistema Inteligente de Orquestacion y Priorizacion de Vulnerabilidades) -- Master's thesis
**Author:** Bruno (principal investigator)

---

## PART 1: RESEARCH METHODOLOGY

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

## PART 2: KEY RESEARCH FINDINGS

### 2.1 Agent Definition Structure and Frontmatter

Agent definitions in Claude Code are `.md` files with YAML frontmatter stored in `.claude/agents/`. The frontmatter provides metadata and constraints; the Markdown body IS the complete system prompt. Subagents receive ONLY this body plus basic environment details (working directory) -- they do NOT inherit the parent's system prompt, conversation, or loaded rules.

**Irreducible minimum fields:** `name`, `description`, `tools`, and non-empty body content. Optional fields: `model`, `memory`, `hooks`, `maxTurns`. The full field set includes 14 frontmatter fields as of March 2026.

**Key implication:** Every agent body must be completely self-contained. It cannot reference instructions from the parent conversation, CLAUDE.md, or rules files unless those are explicitly included in the body.

### 2.2 Behavioral Persona Design

**What works:**
- Direct persona assignment ("You are an X") outperforms imagination framing ("Imagine you are...") -- empirically validated (IF-03, CP-PBD-01).
- The 4-element pattern: identity + domain expertise + constraints + output format (CP-PBD-02, PR-02).
- Explicit "You are NOT" constraints prevent persona leakage -- Claude infers personality traits beyond specification (CP-ANT-09, PR-05).
- Personas with detailed domain expertise produce better style/format/tone control (PR-02).

**What does NOT work:**
- Persona does NOT reliably control factual accuracy, deep reasoning quality, or knowledge beyond training data. Vanilla prompting and persona prompting perform very similarly on accuracy tasks (PR-01).
- Personas without explicit constraints leak inferred behaviors -- a "security auditor" may start suggesting fixes unless explicitly told "DO NOT fix code" (PR-05).
- "Imagine you are..." framing is consistently worse than direct assignment (IF-03).

### 2.3 The 150-Instruction Ceiling and 20-Rule Sweet Spot

Total instructions across all loaded contexts (system prompt + CLAUDE.md + rules + skills) should stay under 150. Beyond this threshold, compliance degrades measurably (CP-GAE-02, CP-RUL-06).

Per agent: maximum 20 core rules in the body, maximum 200 lines total (CP-CTX-04). CLAUDE.md should be under 300 lines (CP-CTX-10).

**Pruning heuristic:** Remove any rule that does not change behavior when removed. If removing a rule causes no observable difference, it wastes attention budget (CP-CTX-09).

### 2.4 Context Positioning and Attention Patterns

**Lost-in-the-middle effect:** LLMs pay the most attention to tokens at the START and END of the context window. Performance drops >30% when key information sits in the middle vs. beginning/end. This is architectural (transformer attention mechanisms), not a bug (IF-08, CP-CTX-01).

**Four-zone positioning hierarchy:**
1. System prompt = highest attention (agent body)
2. Start of conversation = high attention (first messages)
3. End of conversation = high attention (most recent messages, todo lists)
4. Middle of conversation = lowest attention (earlier non-boundary messages)

**Practical strategy:** Front-load the 3 most critical rules at the top of the agent body. Repeat the single most important rule at the end. Use todo list recitation to push the current plan into the high-attention end zone (CP-CTX-05, CP-ANT-02).

### 2.5 Context Rot: Controllable with Interventions

Context rot is the progressive degradation of instruction compliance as conversation length grows. It is caused by: (a) new content diluting the original instructions' attention share, (b) accumulated action-observation pairs creating pattern lock-in, (c) model attention spreading across more tokens (CR-01 through CR-06).

**Empirically validated interventions:**
- External memory files show 21% higher behavioral stability than conversation-only memory (AD-02).
- Todo.md pattern biases attention toward the global plan, counteracting drift (AD-01).
- Runtime reinforcement (appending rules at end of prompt before generation) maintains recency (AD-03).
- Fresh context windows between tasks -- a clean session with a better prompt outperforms a long session with accumulated corrections (CP-ANT-03).
- After two failed corrections in one session, start fresh (CP-ANT-03).

### 2.6 Hooks as Deterministic Enforcement

**"Rules are requests, hooks are laws."** Prompt-based rules achieve ~80% compliance. Hooks + tool restrictions achieve ~100% compliance because they are deterministic (CP-GAE-01, CP-PRD-09).

**PreToolUse is the ONLY blocking hook.** Two blocking mechanisms: exit code 2, or JSON output with `permissionDecision: "deny"` (CP-HCF-02).

**Three handler types:** `command` (shell script, deterministic, best for security), `prompt` (LLM judgment, for nuanced decisions), `agent` (full codebase awareness, most expensive) (CP-HCF-03).

**16 hook events** available as of March 2026, including `SessionStart`, `PreToolUse`, `PostToolUse`, `PreCompact`, `SubagentStart`, `SubagentStop`, `Stop`, and others (CP-HCF-01).

**What hooks CANNOT enforce:** reasoning quality, instruction recall, planning decisions, output semantic correctness, cross-turn consistency (CP-HCF-09).

### 2.7 Three-Layer Guardrails

Production systems require guardrails at three levels (GF-03, SP-04):

| Layer | Purpose | Examples |
|-------|---------|----------|
| Input | Prevent bad data from entering | Injection detection, PII/Presidio, format validation, rate limits |
| Interaction | Control agent behavior during execution | Tool restriction, autonomous decision cap, state-machine tool availability, token budget |
| Output | Validate results before delivery | Structured validation (Pydantic), relevancy checks, hallucination detection, schema compliance |

Single-layer guardrails leave gaps. Each layer catches different failure modes.

### 2.8 Anti-Improvisation and Anti-Drift Techniques

**Per-step constraint design:** Different steps need different constraint types. Data collection = Procedural. Analysis = Criteria. Reporting = Template. Safety checks = Guardrail (CP-ANT-01).

**Scoped tool access is the most reliable anti-improvisation mechanism.** An agent without the Write tool cannot create files regardless of reasoning. Deterministic prevention beats probabilistic instruction-following (CP-ANT-07).

**Todo list recitation:** Agent rewrites a todo list after each step, pushing the global plan into the high-attention end zone (CP-ANT-02, AD-01).

**Explicit DO NOT lists:** 3-5 explicit "DO NOT" statements per agent to counter persona leakage (CP-ANT-09).

**maxTurns limit:** Prevents runaway execution. Simple verification: 10-15 turns. Code implementation: 30-50 turns (CP-ANT-08).

**Three drift types requiring different mitigation:** Semantic drift (re-anchoring), coordination drift (protocol enforcement), behavioral drift (constraint reinforcement) (AD-08).

### 2.9 Compaction-Safe Instruction Design

Auto-compaction triggers at ~95% of 200K tokens. System prompt survives (structural). Early conversation messages get summarized (CP-CTX-11).

**Survival strategies:**
- `<!-- COMPACT-SAFE: summary -->` markers on all critical sections (CS-04).
- Keep constraints self-contained with literal values, not references. Write "threshold is 0.7" not "threshold is defined elsewhere" (CS-02).
- Triple storage: critical rules appear in system prompt + external file + periodic re-injection (CS-05).
- File-system-as-memory: persistent files survive compaction entirely because they exist outside context (CS-06, CS-07).
- PreCompact hook can save state before compaction occurs (CP-HCF-01).

### 2.10 Multi-Agent Orchestration Reliability

**Sub-agent context isolation:** Each sub-agent gets a clean context window. Returns condensed summaries (1,000-2,000 tokens) to coordinator (MA-04).

**Token budget awareness:** Multi-agent systems consume up to 15x more tokens than single-agent chat (MA-05).

**Single responsibility per agent:** 100+ specialized subagents, each with single responsibility, clear description, minimal tool set (CP-PRD-04).

**Verification is the highest-leverage practice:** Give agents ways to verify their own work -- tests to run, expected outputs to validate (CP-ANT-06).

### 2.11 Agent Handoff and Shutdown

**"Reliability lives and dies in the handoffs."** Most "agent failures" are actually orchestration and context-transfer issues (AH-01).

**Default to structured data transfer** (JSON Schema). Free-text handoffs are the main source of context loss (AH-02, AH-03).

**Version payloads with semver:** Include `schemaVersion` field in all inter-agent payloads (AH-05).

**Fresh context by default:** Each new agent starts with fresh conversation history. Include prior context only when explicitly needed (AH-09).

### 2.12 Prompt Repetition for Accuracy Improvement

Repeating critical rules at both the start AND end of the agent body exploits both primacy and recency effects. This is the simplest high-impact technique (CP-CTX-05, IF-08).

Emphasis markers (`IMPORTANT`, `YOU MUST`, `CRITICAL`, `NEVER`) demonstrably improve adherence, but overuse dilutes the effect (CP-CTX-06).

---

## PART 3: DESIGN DECISIONS FOR SIOPV

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
  005_dual-purpose-technical-record-and-checklist-for-agent-design.md (this file)
  stage-1/   (Discovery & spec mapping reports)
  stage-2/   (Hexagonal quality audit reports)
  stage-3/   (SOTA research & deep scan reports)
  stage-4/   (Claude Code configuration setup artifacts)
  stage-5/   (Remediation-hardening reports)
```

---

## PART 4: STAGE ARCHITECTURE

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

## PART 5: REUSABLE TEAM TEMPLATE

The following template applies uniformly to STAGE-1 through STAGE-4. It encodes the research findings into a concrete operational pattern.

### 5.1 Team Lifecycle

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

### 5.2 Context Management

- **60% context soft limit:** Agents should aim to complete their work within 60% of the context window. PreCompact hook saves state to disk as a safety net before auto-compaction triggers at 95%.
- **External memory:** Orchestrator maintains a `todo.md` file updated after each round. Agents write findings to disk immediately, not held in memory.
- **No cross-agent context bleeding:** Each agent starts fresh. The only shared state is on disk (reports, todo.md, progress tracker).

### 5.3 Report Structure (Uniform)

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

## PART 6: AGENT PERSONA TEMPLATES

### 6.1 Scanner Persona (STAGE-1 and STAGE-2)

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
[Use the exact report template from Section 5.3]

## Boundaries
- Scope: ONLY the files listed in your assignment.
- If you encounter a situation where your constraints do not fit, report it as
  ESCALATION with your reasoning. Do not ignore the constraint silently.

REMINDER: You are read-only. NEVER modify any file. Report findings with evidence only.
```

**Line count: ~50 lines.** Well under the 200-line limit.

### 6.2 Researcher Persona (STAGE-3)

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
[Use the exact report template from Section 5.3, with an additional "Sources" section
listing all URLs and papers consulted]

## Boundaries
- Scope: ONLY the topic assigned. Do not expand into adjacent research areas.
- If you encounter a situation where additional research is needed beyond scope,
  report it as ESCALATION.

REMINDER: Every claim MUST cite a specific source. No unsourced recommendations.
```

**Line count: ~60 lines.** Well under the 200-line limit.

### 6.3 Summarizer Persona (All Stages)

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

### 6.4 Orchestrator Persona (All Stages)

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

## PART 7: IMPLEMENTATION CHECKLIST

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

**Total estimated new files:** 20-25
**Total checklist items:** 32
**Research checkpoints referenced:** 132 (58 from Report 001 + 74 from Report 002)
