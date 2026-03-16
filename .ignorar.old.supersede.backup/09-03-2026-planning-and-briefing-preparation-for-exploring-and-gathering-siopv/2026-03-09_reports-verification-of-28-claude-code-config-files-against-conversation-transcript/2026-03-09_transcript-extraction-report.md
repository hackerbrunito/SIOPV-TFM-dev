# Transcript Extraction Report: Claude Code Configuration Planning Decisions

**Date:** 2026-03-09
**Source:** Full conversation transcript (5,787 lines) + Definitive Dual-Purpose Record (1,455 lines)
**Extracted by:** transcript-reader agent
**Purpose:** Provide a complete inventory of every planning decision related to Claude Code configuration, for cross-verification against the 28 implemented config files.

---

## NOTE ON SOURCES

The conversation transcript (`2026-03-09_16.02.58_full-conversation-transcript-march-9-planning-session.md`) contains 5,787 lines, but USER/ASSISTANT message bodies are EMPTY -- only metadata headers were captured. The actual planning content exists in:

1. **Task-notification result blocks** within the transcript (5 research agent completions)
2. **The definitive dual-purpose record** (`2026-03-09_definitive-dual-purpose-record-merged-comprehensive.md`), which synthesizes all 132 checkpoints from the planning session

This report extracts from both sources.

---

## 1. DESIGN DECISIONS (DD-001 through DD-015)

### DD-001: Three-Tier Guardrail Architecture
- **What:** Use prompts (~80% compliance), tool restrictions (100%), and hooks (100%) as three tiers.
- **Why:** Prompts are requests, not commands. Tool restrictions and hooks provide deterministic enforcement.
- **Implication for config:** Every MUST-happen rule needs a hook or tool restriction, not just a prompt instruction.

### DD-002: 150-Instruction Ceiling
- **What:** Total instructions across all contexts (CLAUDE.md + agent body + rules files) must not exceed 150.
- **Why:** Jaroslawicz 2025 research shows compliance degrades for ALL rules beyond this threshold.
- **Implication for config:** Prune ruthlessly. Each agent body should have max 20 core rules.

### DD-003: Lost-in-the-Middle Mitigation
- **What:** Place critical rules at the TOP and repeat at the BOTTOM of agent bodies.
- **Why:** LLMs attend more to beginning and end, less to middle content.
- **Implication for config:** Every agent definition file must front-load 3 critical rules and repeat the most important one as a REMINDER at the very end.

### DD-004: Anti-Improvisation via Explicit NOT Instructions
- **What:** Include 3-5 "DO NOT" statements in every agent body.
- **Why:** Without explicit boundaries, agents invent new tasks, expand scope, and drift from their mandate.
- **Implication for config:** Every agent .md file must have a "DO NOT" section.

### DD-005: Fresh Context per Agent
- **What:** Each sub-agent starts with a clean context window. No cross-agent context bleeding.
- **Why:** Accumulated context degrades compliance. Fresh context gives best instruction following.
- **Implication for config:** Agents share state only via disk (reports, todo.md). No passing of conversation history.

### DD-006: Todo Recitation
- **What:** Agents must recite their task list after each step.
- **Why:** Prevents drift and helps the agent track progress against its mandate.
- **Implication for config:** Workflow sections must include progress tracking checkboxes.

### DD-007: Scoped Tool Assignment
- **What:** Each agent role gets only the tools it needs.
- **Why:** Tool restrictions are the most reliable guardrail (deterministic prevention).
- **Implication for config:** See Section 4 below for exact tool assignments per role.

### DD-008: maxTurns as Safety Net
- **What:** Set maxTurns to prevent runaway agents.
- **Why:** Without a turn limit, agents can loop indefinitely.
- **Implication for config:** Scanner: 25, Researcher: 30, Summarizer: 15, Orchestrator: 50.

### DD-009: PreToolUse is the ONLY Blocking Hook
- **What:** Only PreToolUse hooks can prevent an action (exit code 2 = block). All other hooks are non-blocking.
- **Why:** This is a Claude Code architectural constraint. PostToolUse hooks run after the action.
- **Implication for config:** Read-only enforcement and dangerous command blocking MUST use PreToolUse hooks.

### DD-010: Four Persona Patterns
- **What:** Use pattern A (Role+Checklist) for scanners, B (Domain Expert+Workflow) for researchers, C (Behavioral Boundaries) for summarizers, D (Cognitive Personas) combined as needed.
- **Why:** Different agent roles need different instruction structures for optimal compliance.
- **Implication for config:** Agent body structure varies by role.

### DD-011: Report Template Uniformity
- **What:** All agents produce reports in the same mandatory structure (see Section 8).
- **Why:** Summarizers and orchestrators need predictable input format.
- **Implication for config:** Every agent must include the exact report template in its Output Format section.

### DD-012: Round/Batch Management
- **What:** Rounds are sequential (with human checkpoints between them). Batches are parallel (max 4-6 agents).
- **Why:** Prevents context exhaustion and enables human oversight.
- **Implication for config:** Orchestrator definitions must encode round plans with batch limits.

### DD-013: Compaction Survival
- **What:** Use COMPACT-SAFE markers, triple storage (memory + disk + prompt), and external memory to survive context compaction.
- **Why:** Auto-compaction at 95% context can lose critical state.
- **Implication for config:** Orchestrators must maintain external progress files. Agents must write findings to disk immediately.

### DD-014: Path-Targeted Rules
- **What:** Rules files can be targeted to specific directories using path patterns.
- **Why:** Domain-specific constraints should apply only to relevant code.
- **Implication for config:** `security.md` targets `src/siopv/infrastructure/**`, `orchestration.md` targets `src/siopv/application/orchestration/**`.

### DD-015: 5-Stage Architecture
- **What:** STAGE-1 (Discovery), STAGE-2 (Hexagonal Audit), STAGE-3 (SOTA Research), STAGE-4 (Config Setup), STAGE-5 (Remediation-Hardening).
- **Why:** Systematic progression from understanding through audit to improvement.
- **Implication for config:** Each stage has its own orchestrator briefing, report directory, and agent set.

---

## 2. AGENT DEFINITION FILES (Frontmatter Fields)

### 2.1 Required Frontmatter Fields
The planning session identified 14 possible frontmatter fields for agent definition files:
- `name` (required)
- `description` (required)
- `tools` (list of allowed tools)
- `disallowedTools` (list of blocked tools)
- `model` (sonnet or opus)
- `permissionMode` (bypassPermissions for orchestrators)
- `maxTurns` (integer safety limit)
- `skills` (list)
- `mcpServers` (list)
- `hooks` (nested structure with matchers)
- `memory` (boolean or path)
- `background` (boolean)
- `isolation` (boolean)

### 2.2 Agent Templates Defined

#### Scanner Agent Template
```yaml
name: siopv-scanner-[domain]
description: "Scans [domain] for [specific audit criteria]"
tools: [Read, Grep, Glob, Bash]
model: sonnet
maxTurns: 25
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: ".claude/hooks/block-write-commands.sh"
```
Body: ~50 lines. 6 sections: Identity, Workflow, DO NOT (5 items), Output Format, Boundaries, REMINDER.

#### Researcher Agent Template
```yaml
name: siopv-researcher-[topic]
description: "Researches state-of-the-art techniques for [topic]"
tools: [Read, Grep, Glob, WebSearch, WebFetch]
model: opus
maxTurns: 30
```
Body: ~60 lines. 7 sections: Identity, Workflow, Verification Before Reporting, DO NOT (5 items), Output Format, Boundaries, REMINDER.

#### Summarizer Agent Template
```yaml
name: siopv-summarizer-[stage]-[round]
description: "Consolidates reports from [stage] [round] into a unified summary"
tools: [Read, Grep, Glob, Write]
model: sonnet
maxTurns: 15
```
Body: ~65 lines. 6 sections: Identity, Workflow, DO NOT (5 items), Output Format, Boundaries, REMINDER.

#### Orchestrator Agent Template
```yaml
name: siopv-orchestrator-[stage]
description: "Orchestrates [stage] execution"
tools: [Read, Grep, Glob, Bash, Write, Agent, SendMessage]
model: opus
maxTurns: 50
```
Body: ~80 lines. 7 sections: Identity, Round Plan, Progress Tracking, Agent Spawn Template, DO NOT (5 items), Error Handling, REMINDER.

---

## 3. DIRECTORY STRUCTURE

### 3.1 Report Output Directories
```
.ignorar/agent-persona-research-2026-03-09/
  stage-1/     # Discovery scan reports
  stage-2/     # Hexagonal audit reports
  stage-3/     # SOTA research reports
  stage-4/     # Config setup reports
  stage-5/     # Remediation-hardening reports
```

### 3.2 File Naming Convention
Format: `NNN_YYYY-MM-DD_HH.MM.SS_descriptive-name.md`
Example: `001_2026-03-09_14.30.22_domain-layer-scan.md`

Note: This differs from the existing project convention (timestamp-based UUID without NNN prefix). The NNN prefix was added for sequential ordering within stages.

### 3.3 Stage Briefing Files
```
.ignorar/agent-persona-research-2026-03-09/
  stage-1-briefing.md
  stage-2-briefing.md
  stage-3-briefing.md
  stage-4-briefing.md
```

---

## 4. TOOL ASSIGNMENTS BY ROLE

| Role | Tools | Model | maxTurns |
|------|-------|-------|----------|
| Scanner | Read, Grep, Glob, Bash | sonnet | 25 |
| Researcher | Read, Grep, Glob, WebSearch, WebFetch | opus | 30 |
| Summarizer | Read, Grep, Glob, Write | sonnet | 15 |
| Orchestrator | Read, Grep, Glob, Bash, Write, Agent, SendMessage | opus | 50 |

### SIOPV-Specific Existing Agent Tool Assignments (from audit findings)
| Agent | Tools | Hook Enforcement |
|-------|-------|-----------------|
| security-auditor | Read-only + Bash | PreToolUse blocks writes |
| code-implementer | All tools | PostToolUse runs ruff/mypy |
| test-generator | All tools | PostToolUse runs pytest |
| hallucination-detector | Read-only ONLY | NO Bash |
| best-practices-enforcer | Read-only + Bash | -- |

---

## 5. HOOK SCRIPTS

### 5.1 Hooks to Create
1. **`.claude/hooks/block-write-commands.sh`** (PreToolUse:Bash)
   - Reads `$INPUT` via `cat`, extracts command via `jq`
   - Blocks: `rm`, `mv`, `cp`, `chmod`, `chown`, `dd`, write redirects (`>`, `>>`)
   - Exit 2 = block, Exit 0 = allow

2. **`.claude/hooks/block-dangerous-commands.sh`** (PreToolUse:Bash)
   - Blocks: `sudo`, `curl | bash`, `eval`, `exec`
   - Exit 2 = block

3. **`.claude/hooks/run-linter.sh`** (PostToolUse:Edit|Write)
   - Runs `ruff check` and `ruff format --check` after Edit/Write operations

### 5.2 Existing Hooks (from transcript metadata)
- `pre-git-commit.sh` (PreToolUse:Bash) -- blocks commits without verification
- `session-start.sh` (SessionStart:compact) -- re-injects context after compaction
- Stop hook -- checks for pending verification markers
- MCP health check -- validates MCP server connectivity
- Post-compact context re-injection

### 5.3 Hook Architecture Notes
- **16 hook events** exist in Claude Code
- **PreToolUse** is the ONLY blocking hook (exit 2 prevents the action)
- Hook input arrives via `$INPUT` (JSON), parse with `jq`
- PreToolUse matcher format: tool name string (e.g., `"Bash"`, `"Edit|Write"`)

---

## 6. RULES FILES

### 6.1 Rules Files to Create
1. **`.claude/rules/scanner-read-only.md`** -- global rule enforcing read-only behavior for scanner agents
2. **`.claude/rules/report-template.md`** -- global rule with the mandatory report structure
3. **`.claude/rules/anti-improvisation.md`** -- global rule with DO NOT list and todo recitation requirement
4. **Path-targeted rules:**
   - `security.md` targeted to `src/siopv/infrastructure/**`
   - `orchestration.md` targeted to `src/siopv/application/orchestration/**`

---

## 7. SETTINGS CONFIGURATION

### 7.1 settings.json Hook Configuration
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/block-dangerous-commands.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/run-linter.sh"
          }
        ]
      }
    ]
  }
}
```

---

## 8. REPORT TEMPLATE (MANDATORY)

Every agent report must follow this structure:
```markdown
# [Agent Name] Report

**Stage:** STAGE-N
**Round:** N, Batch: A
**Sequence:** NNN
**Timestamp:** YYYY-MM-DD HH:MM:SS
**Duration:** N minutes

## Mandate
[One sentence]

## Findings
### Finding F-NNN: [Title]
- **Severity:** CRITICAL | HIGH | MEDIUM | LOW | INFO
- **Location:** [file path:line number]
- **Description:** [what]
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

## 9. AGENT BODY STRUCTURE (6-SECTION TEMPLATE)

Every agent body must include these 6 sections:
1. **Identity** -- role + domain
2. **Mandate** -- ONE task, specific deliverable
3. **Workflow** -- numbered steps with progress tracking
4. **Boundaries** -- 3-5 DO NOT items + escalation clause
5. **Output Format** -- exact report template
6. **Verification** -- pre-completion self-check

### Structural Rules
- Under 200 lines total
- Critical rules at TOP (first 3 lines after frontmatter)
- Critical rule repeated at BOTTOM as REMINDER
- 3-5 canonical examples included where applicable

---

## 10. SIZE LIMITS

| Component | Maximum |
|-----------|---------|
| Agent body | 200 lines |
| CLAUDE.md | 300 lines |
| Total instructions (all contexts) | 150 |
| Critical rules in prompts | 20 |
| Sub-agent return to orchestrator | 1,000-2,000 tokens |
| Parallel agents per batch | 4-6 |

---

## 11. TEAM LIFECYCLE

1. `claude-main` spawns orchestrator via `TeamCreate` + `Agent`
2. Orchestrator reads briefing file, manages everything from that point
3. Orchestrator spawns rounds of 4-6 parallel agents per batch
4. Each agent has fresh context (no cross-agent bleeding)
5. Agents write reports to disk, return condensed summary (1,000-2,000 tokens), terminate
6. Wave summarizer reads ONLY round reports (not raw conversations)
7. Orchestrator sends round summary to `claude-main` via `SendMessage`
8. **Human checkpoint:** human reviews, approves next round or requests corrections
9. After all rounds: final summarizer reads ONLY round summaries (not individual reports)
10. Human approves stage deliverable

---

## 12. CONTEXT MANAGEMENT

- **60% context soft limit:** Agents aim to complete within 60% of context window
- **PreCompact hook:** saves state to disk before auto-compaction at 95%
- **External memory:** Orchestrator maintains `todo.md` updated after each round
- **Agents write findings to disk immediately,** not held in memory
- **COMPACT-SAFE markers:** in workflow files to survive compaction

---

## 13. GUARDRAIL TIER DECISION MATRIX

| Requirement | Tier 1 (Prompt) | Tier 2 (Tool Restriction) | Tier 3 (Hook) |
|-------------|-----------------|---------------------------|----------------|
| Guidance/preferences | Primary | -- | -- |
| Code style | Primary | -- | PostToolUse linter |
| Read-only enforcement | Supporting | Primary | PreToolUse blocking |
| Dangerous command blocking | -- | -- | Primary (PreToolUse) |
| Output format | Primary | -- | PostToolUse validation |
| Security-critical rules | Supporting | Where applicable | Primary |

---

## 14. IMPLEMENTATION CHECKLIST (32 items)

### Phase A: Directory Structure (5 items)
- Create stage-1/ through stage-5/ directories under `.ignorar/agent-persona-research-2026-03-09/`

### Phase B: Hook Scripts (3 items)
- `block-write-commands.sh`, `block-dangerous-commands.sh`, `run-linter.sh`

### Phase C: Settings Configuration (1 item)
- Update `.claude/settings.json` with hook configurations

### Phase D: Agent Definition Files (8 items)
- 4 agent templates (scanner, researcher, summarizer, orchestrator)
- 4 stage briefing files (stage-1 through stage-4)

### Phase E: Rules Files (4 items)
- `scanner-read-only.md`, `report-template.md`, `anti-improvisation.md`, path-targeted rules

### Phase F: Validation and Testing (4 items)
- Test PreToolUse hook, PostToolUse hook, agent definition loading, report template compliance

### Phase G: Stage Execution (6 items)
- Execute stages 1-4, design stage 5, execute stage 5

### Phase H: Final Audit Record (1 item)
- Produce final consolidated audit report

---

## 15. REFERENCES AND NAMING CONVENTIONS

### File Naming
- Agent definitions: `.claude/agents/siopv-{role}-{domain}.md`
- Hook scripts: `.claude/hooks/{descriptive-name}.sh`
- Rules files: `.claude/rules/{descriptive-name}.md`
- Stage briefings: `.ignorar/agent-persona-research-2026-03-09/stage-{N}-briefing.md`
- Reports: `.ignorar/agent-persona-research-2026-03-09/stage-{N}/NNN_YYYY-MM-DD_HH.MM.SS_descriptive-name.md`

### Key Takeaway Rules (from Section 21)
1. Prompts are requests, hooks are laws
2. 150 instructions is the ceiling
3. Lost-in-the-middle is real
4. Tool restrictions are the most reliable guardrail
5. Per-step constraints beat uniform freedom levels
6. Fresh context beats accumulated context
7. Verification is the highest-leverage practice
8. Personas leak beyond specification -- use explicit NOT instructions

---

## 16. EXISTING HOOKS VISIBLE IN TRANSCRIPT

From the transcript metadata, these hooks were actively running during the planning session:
1. `pre-git-commit.sh` -- PreToolUse:Bash, blocks unverified commits
2. `session-start.sh` -- SessionStart:compact, post-compact context re-injection
3. Stop hook -- checks pending verification markers
4. MCP health check -- SessionStart, validates MCP server connectivity

---

## 17. STAGE DESCRIPTIONS

### STAGE-1: Discovery Scan
- **Objective:** Full codebase scan for code smells, TODO/FIXME markers, unused imports, dead code, circular dependencies
- **Agents:** 4-6 scanner agents (each scans a directory subtree) + 1 summarizer + 1 orchestrator
- **Rounds:** 2-3 (Round 1: src/siopv/domain + application, Round 2: infrastructure + interfaces, Round 3: cross-cutting)

### STAGE-2: Hexagonal Architecture Audit
- **Objective:** Audit code quality against hexagonal architecture principles (layer violations, dependency direction, port/adapter compliance, DI patterns)
- **Agents:** 4-6 scanner agents (each audits a hexagonal layer) + 1 summarizer + 1 orchestrator
- **Rounds:** 2-3 (Round 1: domain + application, Round 2: infrastructure + interfaces, Round 3: DI + testing)

### STAGE-3: SOTA Research
- **Objective:** Research state-of-the-art techniques for each SIOPV component
- **Agents:** 4-6 researcher agents (LangGraph, DLP/Presidio, vulnerability classification, OpenFGA, Streamlit HITL) + 1 summarizer + 1 orchestrator
- **Rounds:** 2-3 (Round 1: core pipeline, Round 2: supporting systems, Round 3: gap-filling)

### STAGE-4: Config Setup
- **Objective:** Create agent definition files, hook scripts, rules files, settings.json
- **Agents:** 2 scanner agents (audit existing .claude/ config) + 1 summarizer + 1 orchestrator
- **Rounds:** 2 (Round 1: config audit, Round 2: gap analysis)

### STAGE-5: Remediation-Hardening
- **Objective:** Apply corrections from stages 1-4
- **Agents:** TBD based on findings
- **Rounds:** Variable

---

## 18. ERROR HANDLING IN ORCHESTRATOR

- If an agent fails or times out: log failure, report to claude-main, ask whether to retry or skip
- If 2+ agents in a batch fail: STOP the stage and escalate to claude-main
- After two failed corrections of the same agent: mark as FAILED and report

---

**END OF EXTRACTION REPORT**

**Total planning decisions extracted:** 15 design decisions (DD-001 through DD-015), 4 agent templates with full frontmatter and body structure, 3 hook scripts, 4+ rules files, 5 stage definitions, 32-item implementation checklist, size limits, guardrail matrix, team lifecycle, context management strategy, error handling protocol.
