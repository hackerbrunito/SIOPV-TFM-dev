# Team Management Best Practices
# Claude Code Agent Teams — Reusable Reference

> **Version:** 2026-03-13
> **Purpose:** Reusable guide for managing Claude Code agent teams across projects.
> **Scope:** Hub-and-spoke orchestration, wave-based execution, communication patterns.
> **Requires:** Claude Code v2.1.32+ | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

---

## 1. HARD ARCHITECTURAL CONSTRAINT

**Teammates CANNOT spawn other agents or sub-teams.**

The `Agent`, `TeamCreate`, and `TeamDelete` tools are **stripped from teammates at spawn time**. Only the team lead (the main Claude Code session) can spawn agents. Teammates have 20 tools; standalone subagents have 25.

This is not configurable. It is a platform-level restriction.

---

## 2. ROLES

### Team Lead (main Claude Code session)
- Creates the team with `TeamCreate`
- Spawns the orchestrator agent
- Receives agent specifications from the orchestrator via `SendMessage`
- Spawns all worker agents round by round
- Activates **delegate mode** (Shift+Tab) to restrict itself to coordination-only tools
- Does NOT use `/compact` mid-run — use `/rewind → Summarize from here` between rounds instead
- Approves at human checkpoints before each new round

### Orchestrator (a spawned agent — Opus model)
- Plans and coordinates only — does NOT write code, does NOT implement files
- Reads all input files before writing any plan
- Writes its execution plan to a file on disk
- Sends `SendMessage` to the team lead specifying **exactly** what agents to spawn (names, prompts, output paths, model)
- Waits for agents to complete (reads their output files)
- Aggregates results, writes round summary, sends next-round specs to team lead
- Does NOT spawn agents itself — requests spawning from the team lead via SendMessage

### Worker Agents (spawned agents — Sonnet model)
- Execute assigned tasks (research, scan, write, analyze)
- Save full output to a timestamped file on disk
- Send only a 3–5 line summary via `SendMessage` back to team lead
- Never edit files assigned to other agents in the same wave

---

## 3. MODEL ASSIGNMENT

| Role | Model | Rationale |
|------|-------|-----------|
| Orchestrator | `claude-opus-4-6` | Planning, synthesizing across large inputs |
| All worker agents | `claude-sonnet-4-6` | Execution — best cost/speed ratio |

This is Anthropic's own production pattern. Do not swap models between roles.

---

## 4. COMMUNICATION PATTERN

- **All communication via `SendMessage`** — no exceptions
- Team lead name in team = `"team-lead"` (use this when the orchestrator sends messages back)
- Teammates discover each other via `~/.claude/teams/{team-name}/config.json`
- **Use direct messages (one-to-one)**, not broadcast — broadcast cost scales linearly with team size
- Message format from orchestrator → team lead: structured agent specification (see Section 6)

---

## 5. FILE-BASED RESULTS PATTERN (mandatory)

Every agent saves its full output to a persistent file. Agents send only a summary via SendMessage.

**File naming convention:**
```
{TIMESTAMP}-{round-identifier}-{agent-slug}.md
```

**Examples:**
```
2026-03-13-143022-r1-streamlit-researcher.md
2026-03-13-143022-r2-metaproject-scanner.md
2026-03-13-143022-r3-gap-analyst.md
```

**Why file-based:**
- Survives compaction — files are on disk, not in context
- Team lead reads files only when depth is needed
- Prevents context bloat from large agent outputs
- Enables parallel wave execution without coordination conflicts

---

## 6. WAVE STRUCTURE

### Team Size
- Maximum **3–5 active teammates** per wave
- For larger rounds, use sequential waves: Wave A → Wave B → Wave C
- Each wave completes fully before next wave spawns

### Wave Pattern for Stage 4.1
```
Wave A: 3–5 parallel research/scan agents
Wave B: 1–3 summarizer agents (after Wave A files are written)
Wave C: 1 aggregator agent (after Wave B files are written)
```

### Agent Specification (orchestrator sends this to team lead)
```
Agent Name: r1-streamlit-researcher
Model: claude-sonnet-4-6
Task: Research Streamlit 1.x patterns for human-in-the-loop UI
Output path: /Users/bruno/siopv/AuditPrePhase7-11mar26/stage4.1-research/round1-online-research/2026-03-13-HHMMSS-r1-streamlit-researcher.md
Summary to send back: 3–5 lines only
```

---

## 7. TEAMMATE HOOKS (Claude Code v2.1.32+)

Two hooks were released **February 6, 2026** that enable quality gates at task completion:

| Hook | Trigger | Use Case |
|------|---------|----------|
| `TeammateIdle` | Teammate has no pending tasks | Auto-run linting or validation |
| `TaskCompleted` | Agent completes an assigned task | Quality gate before result is accepted |

**Registration in `settings.json`:**
```json
{
  "hooks": {
    "TeammateIdle": [{"hooks": [{"type": "command", "command": "..."}]}],
    "TaskCompleted": [{"hooks": [{"type": "command", "command": "..."}]}]
  }
}
```

**Exit code 2** from either hook blocks task completion — use this for mandatory quality checks.

---

## 8. CONTEXT MANAGEMENT DURING ACTIVE TEAMS

| Scenario | Correct Action | Never Do |
|----------|---------------|----------|
| Context filling mid-round | Wait — agents write to disk, context not critical | `/compact` mid-run |
| Between rounds | `/rewind → Summarize from here` | `/compact` |
| After all rounds complete | Normal `/compact` is safe | — |

**Why no `/compact` mid-run:** Compaction breaks the teammate communication state. Agents that have already been spawned and are communicating via SendMessage will lose context of their coordination. Between rounds is safe because all agents have completed.

---

## 9. MANDATORY RULE — NO IMPROVISATION

**This rule applies to every participant without exception: team lead, orchestrator, and all worker agents.**

> **When anything is unclear, vague, not explicitly specified, or requires interpretation — STOP. Do not guess. Do not infer. Do not improvise. Send a message to the team lead immediately and wait for human approval before doing anything.**

Specific prohibitions:
- **No guessing** — if a value, path, decision, or behavior is not explicitly stated in the briefing or truth files, do not assume a value
- **No inference** — do not derive unstated requirements from context, patterns, or "what makes sense"
- **No interpretation** — instructions mean exactly what they say; do not expand or narrow their scope
- **No improvisation** — do not fill gaps with judgment calls, even well-intentioned ones
- **No silent decisions** — if a conflict, ambiguity, or missing specification is discovered, it must be reported; it must not be silently resolved

**Required behavior when blocked:**
1. Stop all work immediately
2. Send a `SendMessage` to the team lead describing exactly what is unclear and why work cannot proceed
3. Wait — do not take any action until the team lead relays human approval or clarification
4. Resume only after explicit approval is received via `SendMessage`

This applies to the team lead (main session) equally: if the human's instruction is ambiguous, ask before spawning anything.

---

## 10. ANTI-PATTERNS

| Anti-Pattern | Consequence |
|-------------|-------------|
| Two agents editing the same file in parallel | One agent's work silently overwritten |
| Vague task specifications | Conflicting output formats, incomplete results |
| Orchestrator spawning agents directly | Architecture violation — tools stripped at spawn |
| Broadcast messages instead of direct | Token cost multiplies by team size |
| `/compact` mid-run | Breaks teammate communication state |
| Teams larger than 5 active agents | Coordination overhead exceeds gains |
| No plan approval before spawning workers | Inconsistent results across rounds |
| Agents sending full report via SendMessage | Context bloat — always file + 3-5 line summary |
| Orchestrator using Sonnet | Loss of synthesis quality across large inputs |
| Workers using Opus | Unnecessary cost with no quality gain |
| Guessing or inferring when instructions are unclear | Silent errors, wrong outputs, wasted work |
| Resolving ambiguity without human approval | Undetected divergence from intended design |

---

## 10. REQUIRED SETTINGS

In `settings.json` (project-level):
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

Requires Claude Code v2.1.32 or later. Verify with `claude --version` before spawning teams.

---

## 11. ORCHESTRATOR SPAWN PROTOCOL

```
Step 1 — Create the team:
TeamCreate(
  team_name="{descriptive-project-name}",
  description="{what this team is doing}",
  agent_type="orchestrator"
)

Step 2 — Spawn the orchestrator into the team:
Agent(
  description="Orchestrate {project name}",
  prompt="Read and follow the briefing file at: {absolute_path_to_briefing_file}",
  subagent_type="general-purpose",
  model="opus",
  team_name="{same-team-name-as-step-1}",
  name="orchestrator",
  run_in_background=True
)

Step 3 — Name yourself "team-lead" in the team so the orchestrator can SendMessage back to you.

Step 4 — Activate delegate mode (Shift+Tab) to restrict yourself to coordination-only tools.

Step 5 — Wait. The orchestrator sends agent specs via SendMessage. Execute each spec by spawning the worker agents.
```

---

*End of team management best practices. This file is referenced by stage4.1-orchestrator-guidelines.md.*
