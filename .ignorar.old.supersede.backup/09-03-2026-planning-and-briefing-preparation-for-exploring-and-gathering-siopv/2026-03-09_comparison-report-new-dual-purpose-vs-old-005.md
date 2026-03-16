# Comparison Report: File A (New) vs File B (Old)

**Date:** 2026-03-09
**File A (NEW):** `2026-03-09_dual-purpose-record-comprehensive-checklist-and-technical-reference.md`
**File B (OLD):** `005_dual-purpose-technical-record-and-checklist-for-agent-design.md`

---

## 1. STRUCTURAL OVERVIEW

| Aspect | File A (New) | File B (Old) |
|--------|-------------|-------------|
| Title | "Comprehensive Checklist and Technical Reference for Claude Code Agent Projects" | "Dual-Purpose Technical Record and Checklist for Agent Design" |
| Total lines | ~743 | ~818 |
| Organization | 15 topic-based sections, each with sub-checklist items | 7 parts: Research Methodology, Key Findings, Design Decisions, Stage Architecture, Reusable Team Template, Agent Persona Templates, Implementation Checklist |
| Format | Pure checklist/reference (every item is `- [ ]`) | Narrative + design decisions (DD-001 to DD-015) + stage plans + code templates + checklist |
| Scope | Generic/reusable for any Claude Code agent project | SIOPV-specific with project context |

---

## 2. TOPICS IN FILE B (OLD) THAT FILE A (NEW) IS MISSING

### 2.1 Research Methodology (File B Part 1)

File B has an entire section documenting:
- **What was researched** -- the two complementary domains (Claude Code Agent Configuration + LLM Behavioral Control Science)
- **Sources consulted** -- detailed list of 20+ specific sources with section references: Anthropic docs, Trail of Bits, VoltAgent, Adaline Labs, Captain Hook, Codacy, Manus AI, arXiv papers (2601.04170, 2510.07777, 2512.14982), LangGraph docs, OpenAI Agents SDK, Pydantic AI, Skywork AI, NVIDIA NeMo, Guardrails AI, Meta Llama Guard, LLMLingua
- **Purpose statement** -- explicitly ties the work to the SIOPV master's thesis

File A has none of this. It lists source files (`003_...` and `004_...`) in the header but does not enumerate the original research sources or methodology.

### 2.2 Design Decisions as Formal Artifacts (File B Part 3, DD-001 through DD-015)

File B defines 15 numbered, checkboxed design decisions with explicit **What/Why/How** structure and checkpoint ID cross-references:

| DD | Topic | Present in File A? |
|----|-------|--------------------|
| DD-001 | Agent Definition File Structure | Covered as checklist items in Section 1, but without the DD format |
| DD-002 | Persona Template (4-element) | Covered in Section 2.8 |
| DD-003 | Per-Agent Rule Limit (20 rules) | Covered in Section 8.4 |
| DD-004 | Agent Body Size Limit (200 lines) | Covered in Section 8.4 |
| DD-005 | Hook Configuration (3 hook types) | Covered in Section 5 |
| DD-006 | Tool Restriction Strategy | Covered in Section 14.1 |
| DD-007 | Report Template Enforcement | Partially covered in Section 13.8 |
| DD-008 | Context Positioning Strategy | Covered in Section 8.2-8.4 |
| DD-009 | Anti-Improvisation Constraints | Covered in Section 7 |
| DD-010 | Compaction-Safe Markers | Covered in Section 9.7 |
| DD-011 | Round and Batch Management | **MISSING** -- File A has no concept of rounds, batches, or wave management |
| DD-012 | Human Checkpoint Protocol | **MISSING** as a formal DD -- File A mentions human escalation only in passing |
| DD-013 | Agent Shutdown Protocol | Partially in Section 12, but without the specific lifecycle (write report -> update tracker -> return summary -> terminate) |
| DD-014 | File Naming Convention | **MISSING** -- the `NNN_YYYY-MM-DD_HH.MM.SS_descriptive-name.md` pattern is absent |
| DD-015 | Directory Structure for the Audit Project | **MISSING** -- the full `.ignorar/agent-persona-research-2026-03-09/` tree is absent |

The DD format itself (What/Why/How with checkpoint IDs) is a traceability artifact absent from File A.

### 2.3 Stage Architecture (File B Part 4)

File B defines five concrete stages with per-stage detail:
- **STAGE-1:** Discovery & Spec Mapping (scanner agents, rounds, naming, report output path)
- **STAGE-2:** Hexagonal Quality Audit (4-6 scanners per layer, 2-3 rounds)
- **STAGE-3:** SOTA Research & Deep Scan (researcher agents with online tools, topics listed)
- **STAGE-4:** Claude Code Configuration Setup (audit existing `.claude/` config)
- **STAGE-5:** Remediation-Hardening (designed later based on findings)

File A has **zero stage architecture**. It is stage-agnostic.

### 2.4 Reusable Team Template (File B Part 5)

File B specifies a concrete operational lifecycle pattern:
- **Team Lifecycle** (Section 5.1): 10-step process from claude-main spawn through final human approval
- **Context Management** (Section 5.2): 60% context soft limit, external memory, no cross-agent context bleeding
- **Report Structure** (Section 5.3): Exact template with fields (Stage, Round, Batch, Sequence, Timestamp, Duration, Mandate, Findings with F-NNN IDs, Summary, Self-Verification checklist)

File A has no reusable team template. It discusses multi-agent patterns abstractly (Section 11) but never defines a concrete lifecycle.

### 2.5 Agent Persona Templates with Full Code (File B Part 6)

File B includes four complete, copy-paste-ready agent definition templates with YAML frontmatter and Markdown body:
- **Scanner Persona** (Section 6.1): ~50 lines, model: sonnet, maxTurns: 25, with hook config
- **Researcher Persona** (Section 6.2): ~60 lines, model: opus, maxTurns: 30, with WebSearch/WebFetch
- **Summarizer Persona** (Section 6.3): ~65 lines, model: sonnet, maxTurns: 15, with dedup rules
- **Orchestrator Persona** (Section 6.4): ~80 lines, model: opus, maxTurns: 50, with round plan, progress tracking, error handling, and agent spawn template

Each template includes identity, workflow, DO NOT list, output format, boundaries, and a repeated critical rule at the end. File A has a generic 6-section body template (Section 2.8) but no complete, instantiated agent definitions.

### 2.6 Implementation Checklist with Phases (File B Part 7)

File B has a 32-item operational checklist organized into 8 phases:
- **Phase A:** Directory structure setup (items 1-5)
- **Phase B:** Hook scripts (items 6-8, with specific script names and blocking logic)
- **Phase C:** Settings configuration (item 9)
- **Phase D:** Agent definition files (items 10-17, with specific file paths)
- **Phase E:** Rules files (items 18-21, with specific names)
- **Phase F:** Validation and testing (items 22-25)
- **Phase G:** Stage execution (items 26-31)
- **Phase H:** Final audit record (item 32)

File A has no implementation checklist. Every `- [ ]` in File A is a knowledge/reference checklist item, not an implementation task.

### 2.7 Specific Operational Details Missing from File A

- **Wave summarizer concept** -- File B describes summarizers that read only round reports (not raw conversations) to produce consolidated summaries
- **4-6 agent batch limit** -- File B specifies this as an explicit operational constraint; File A mentions it only in passing (Section 11.5)
- **Orchestrator error handling protocol** -- File B (Section 6.4) specifies: if 1 agent fails, report and ask whether to retry or skip; if 2+ agents fail, STOP the stage
- **60% context soft limit** -- File B (Section 5.2) sets this as an operational target; File A does not mention it
- **ESCALATION as a formal category** -- File B templates treat ESCALATION as a structured output type that agents produce when constraints don't fit

---

## 3. TOPICS IN FILE A (NEW) THAT FILE B (OLD) IS MISSING

### 3.1 Instruction-Following Techniques (File A Section 3)

File A has a dedicated section with items File B does not cover:
- **ISE (Instructional Segment Embedding)** -- token role classification (system=0, user=1, data=2), ICLR 2025 reference (Section 3.3)
- **Few-shot examples** -- 3-5 diverse canonical examples per agent (Section 3.4)
- **Three-template system** -- `system_template`, `prompt_template`, `response_template` from PLoP 2024 (Section 3.5)
- **Reasoning mode** -- when to enable `reasoning: true` in frontmatter (Section 3.6)
- **Minimal viable prompt approach** -- start with 5-10 lines, add constraints only for observed failures (Section 3.1)
- **Right altitude balance** -- "Goldilocks zone" for specificity (Section 3.1)

### 3.2 Rules Files Detailed Mechanics (File A Section 6)

File A covers rules file mechanics that File B only mentions in passing:
- **Path-targeted rules with YAML `paths:` frontmatter** and glob pattern syntax (Section 6.2)
- **Known bug: path rules only trigger on READ** -- not on write/create (Section 6.2)
- **Four Instruction Mechanisms table** -- CLAUDE.md vs rules vs skills vs agent body, with when-loaded and scope (Section 6.4)
- **Five rules for effective rule writing** (Section 6.5)
- **What rules CANNOT do** -- 5 explicit limitations (Section 6.6)

### 3.3 Expanded Guardrail Coverage (File A Section 4)

- **Guardrails Ladder (Adaline Labs)** -- three escalation tiers: read-only, controlled changes, PR-ready (Section 4.4)
- **Per-step constraint types with explicit names** -- Procedural/Criteria/Template/Guardrail as a formal taxonomy (Section 4.5, also present in File B Section 2.8 but less structured)
- **Deterministic vs Probabilistic Control decision framework** -- "For every critical rule, ask: what happens if Claude ignores this?" (Section 4.7)

### 3.4 Structured Output Enforcement (File A Section 10)

File A has a dedicated section with:
- **Reliability ranking table** -- 6 approaches from constrained decoding (highest) to prompt-only (lowest) (Section 10.1)
- **Pydantic AI integration** specifics -- durable execution, streaming with immediate validation (Section 10.2)
- **Validation-repair loop** -- 3 retry attempts, schemaVersion semver (Section 10.3)
- **Guardrail frameworks** -- NeMo/Colang, Guardrails AI hub, Llama Guard (Section 10.4)
- **DLP-first guardrail strategy** -- scan all inputs, outputs, and inter-agent payloads (Section 10.5)

File B mentions these only briefly in Sections 2.7 and 2.11.

### 3.5 Production Patterns and Case Studies (File A Section 13)

File A documents 8 case studies as checklist items:
- **Trail of Bits OS-level sandboxing** (Section 13.1)
- **Security Reviewer pattern** from Anthropic docs (Section 13.2)
- **Database Reader hook-enforced read-only** (Section 13.3)
- **VoltAgent single-responsibility** pattern (Section 13.4)
- **Adaline Labs plan gate** (Section 13.5)
- **Captain Hook intent-based policy** (Section 13.6)
- **Codacy 5-minute guardrails** (Section 13.7)
- **Anti-drift for verification agents** -- 4 techniques (Section 13.8)

File B references these sources in its methodology section but does not extract them as actionable case studies.

### 3.6 SIOPV-Specific Recommendations (File A Section 14)

File A has 12 SIOPV-specific items that go beyond File B's scope:
- **Agent Tool Assignments table** -- security-auditor, code-implementer, test-generator, hallucination-detector, best-practices-enforcer with specific tools and enforcement (Section 14.1)
- **Path-targeted rules for domains** -- security.md for infrastructure, orchestration.md for orchestration (Section 14.3)
- **Pipeline state file** (Section 14.4)
- **Node-level context isolation in LangGraph** -- restrict TypedDict fields per node (Section 14.5)
- **PostgresSaver for production checkpointing** (Section 14.6)
- **Three-layer guardrails mapped to hexagonal architecture** (Section 14.7)
- **Anti-drift for classify_node** -- 5 specific mitigations (Section 14.8)
- **Compaction-safe architecture for multi-session pipeline** (Section 14.9)
- **Verification pipeline guardrails** -- wave timing, tripwire, drift detection (Section 14.10)
- **Deterministic behavior** -- reproducibility logging, constrained decoding, temperature caveat (Section 14.11)
- **Inter-phase handoff protocol** -- siopv.json as canonical state (Section 14.12)

### 3.7 Additional Anti-Drift Techniques (File A Section 7)

File A includes these techniques absent from File B:
- **Skills as instruction anchors** (Section 7.4)
- **Escalation design** -- "If constraints don't fit, propose alternatives with reasoning" (Section 7.5)
- **Episodic memory consolidation** -- after every 10-20 tool calls (Section 7.13)
- **Drift detection via LLM judges** (Section 7.14)
- **Agent Stability Index (ASI)** -- 12 dimensions, arXiv 2601.04170 (Section 7.15)
- **Context equilibria** -- multi-turn drift reaches stable equilibria, arXiv 2510.07777 (Section 7.17)
- **Controlled variation to break pattern lock-in** (Section 7.12)
- **Runtime reinforcement via instruction re-injection** -- callback pattern (Section 7.11)

### 3.8 Context Rot Details (File A Section 9)

- **Three mechanisms** -- lost-in-the-middle, attention dilution, distractor interference (Section 9.1)
- **Measured impact thresholds** -- >30%, 10,000+ tokens back, negative constraints especially vulnerable (Section 9.2)
- **KV-cache optimization** -- cost difference ($0.30 vs $3/MTok), append-only design, deterministic serialization (Section 9.3)
- **Three compression approaches and their risks** -- prompt compression, dynamic summarization, verbatim compaction (Section 9.5)
- **Compaction tuning parameters** -- 80% trigger, preserve last 10 messages (Section 9.10)

### 3.9 Summary Tables (File A Section 15)

- **Seven key takeaways** summary (Section 15.1, actually 8 items)
- **Guardrail tier decision matrix** -- requirement x tier mapping (Section 15.2)
- **Agent body structure checklist** (Section 15.3)
- **Size limits table** (Section 15.4)
- **Source checkpoint counts** (Section 15.5)

---

## 4. WHERE THEY OVERLAP

Both files cover the same core research findings, though at different depths:

| Topic | File A Section | File B Section |
|-------|---------------|---------------|
| Agent definition structure and frontmatter | 1.1-1.5 | 2.1 |
| Persona design (direct assignment, 4-element pattern, leakage) | 2.1-2.7 | 2.2 |
| 150-instruction ceiling, 20-rule sweet spot | 4.2 | 2.3 |
| Context positioning (lost-in-the-middle, 4-zone hierarchy) | 8.1-8.2 | 2.4 |
| Context rot and interventions | 9.1-9.9 | 2.5 |
| Hooks as deterministic enforcement | 5.1-5.7 | 2.6 |
| Three-layer guardrails | 4.6 | 2.7 |
| Anti-improvisation techniques | 7.1-7.9 | 2.8 |
| Compaction-safe instruction design | 9.4-9.9 | 2.9 |
| Multi-agent orchestration | 11.1-11.7 | 2.10 |
| Agent handoff and shutdown | 12.1-12.4 | 2.11 |
| Prompt repetition | 3.2 | 2.12 |
| Tool restriction as anti-improvisation | 7.7, 14.1 | DD-006 |
| maxTurns limits | 7.8 | DD-009 (part of anti-improvisation) |
| Report template enforcement | 13.8 | DD-007, 5.3 |
| Human checkpoints | Mentioned in 14.10 | DD-012 |

---

## 5. FACTUAL DIFFERENCES AND CONTRADICTIONS

### 5.1 No Direct Contradictions Found

The two files are consistent on all factual claims. They share the same research base and cite the same checkpoint IDs (CP-*, IF-*, CR-*, AD-*, etc.).

### 5.2 Emphasis Differences

| Topic | File A emphasis | File B emphasis |
|-------|----------------|----------------|
| Persona patterns | Lists 4 patterns (A-D) including CrewAI and SuperClaude | Focuses on the single 4-element pattern |
| Hook events | Lists all 16 events by name | Lists representative events, cites "16 hook events" |
| Agent body template | 6-section template (Identity/Mandate/Workflow/Boundaries/Output/Verification) | Equivalent but with minor wording differences |
| Structured output | Full section with reliability ranking, Pydantic AI, NeMo, Guardrails AI, Llama Guard | Mentioned briefly in handoff context |
| File naming | Not specified | `NNN_YYYY-MM-DD_HH.MM.SS_descriptive-name.md` (DD-014) |
| Batch size | "up to 15x tokens" and token budget awareness | "Maximum 4-6 parallel agents per batch" as hard limit |

### 5.3 Minor Difference: Key Takeaways Count

File A Section 15.1 says "Seven Key Takeaways" but actually lists 8 items.

---

## 6. OVERALL COMPREHENSIVENESS ASSESSMENT

### File A (New) is more comprehensive as a REFERENCE DOCUMENT

- Covers more topics (15 sections vs 7 parts)
- More granular checklist items (~132 checkboxed items across all sections)
- Broader coverage of techniques (ISE, few-shot, three-template system, reasoning mode, LLM judges, ASI, context equilibria)
- Better structured output coverage
- More production case studies
- More SIOPV-specific technical recommendations (classify_node, hexagonal mapping, PostgresSaver)
- Summary tables for quick reference

### File B (Old) is more comprehensive as an OPERATIONAL DOCUMENT

- Complete stage architecture (5 stages with rounds, batches, agents per stage)
- Copy-paste-ready agent persona templates (4 complete definitions with YAML frontmatter)
- Formal design decisions (DD-001 to DD-015) with traceability to research checkpoints
- Concrete implementation checklist (32 actionable items in 8 phases)
- Reusable team lifecycle template (10-step process)
- Research methodology and provenance (full source list)
- Operational constraints (60% context soft limit, 4-6 batch max, orchestrator error handling)
- Report structure template (exact Markdown with all fields)

### Verdict

**Neither file is a superset of the other.** They serve complementary purposes:

- **File A** is the knowledge base -- "everything we know about building agent systems, organized by topic."
- **File B** is the execution plan -- "exactly how we will build THIS system, with templates, stages, and a checklist."

A complete project record needs BOTH. File A alone lacks operational specificity (no stages, no templates, no implementation sequence). File B alone lacks reference depth (no structured output ranking, no ISE, no case studies, no LangGraph-specific recommendations).

### Recommended Consolidation Priority

If merging into one document, the items most urgently needed from File B that File A lacks:
1. **Stage Architecture** (STAGE-1 through STAGE-5) -- operational backbone
2. **Agent Persona Templates** (4 complete definitions) -- immediate utility
3. **Implementation Checklist** (32 items in 8 phases) -- execution sequencing
4. **Reusable Team Template** (lifecycle, context management, report structure) -- operational pattern
5. **Research Methodology** section -- academic provenance for thesis
6. **File Naming Convention** (DD-014) -- prevents operational ambiguity
7. **Design Decision format** (What/Why/How) -- traceability for thesis examiners

---

**END OF COMPARISON REPORT**
