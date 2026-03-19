---
name: verify
description: "Runs 17 verification agents (Pre-wave + Waves 1-10), clears pending markers. USE WHEN pre-commit or /verify invoked."
disable-model-invocation: true
context: fork
agent: general-purpose
argument-hint: "[--fix]"
allowed-tools: ["Read", "Grep", "Glob", "Bash", "Task"]
---

# /verify

Runs verification agents and clears pending file markers.

## Usage

```
/verify         # Full verification pipeline
/verify --fix   # Auto-fix issues after verification
```

---

## Pipeline Overview

```
PRE-WAVE  → library-researcher (1 sequential)
WAVE 1    → scanner-bpe + scanner-security + scanner-hallucination (3 parallel per batch)
WAVE 1B   → wave1-judge (1 sequential)
WAVE 2    → code-reviewer + test-generator (2 parallel)
WAVE 3    → N parallel fixers (dynamic, file-level partitioned)
WAVE 3B   → fix-validator (1 sequential)
WAVE 4    → integration-tracer + async-safety-auditor (2 parallel)
WAVE 5    → semantic-correctness-auditor + circular-import-detector (2 parallel)
WAVE 6    → import-resolver + dependency-scanner (2 parallel)
WAVE 7    → config-validator (1 agent)
WAVE 8    → hex-arch-remediator (1 agent)
WAVE 9    → smoke-test-runner (1 agent)
WAVE 10   → wiring-auditor + stub-detector + config-cross-checker (3 parallel, last)
```

## 3-Tier Hierarchy

```
human → team-lead → orchestrator → agents
```
- Agents report ONLY to orchestrator (never to team-lead)
- Orchestrator requests spawns from team-lead
- Team-lead interfaces with human for approvals

---

## TEAM-LEAD PROTOCOL (YOUR PROCESS)

### Step 1: Set Variables

```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
TEAM_NAME="siopv-verify-${TIMESTAMP}"
VERIFY_DIR="/Users/bruno/siopv/.verify-$(date +%d-%m-%Y)"
```

### Step 2: Create Verify Directory

```bash
mkdir -p "$VERIFY_DIR"/{context7-cache,scans,fixes,reports,handoffs}
```

### Step 3: Create Team

```
TeamCreate(team_name="${TEAM_NAME}", description="SIOPV /verify run ${TIMESTAMP}", agent_type="general-purpose")
```

### Step 4: Spawn Orchestrator

```
Agent(
  description="Orchestrate /verify pipeline",
  prompt="Read and follow the orchestrator protocol at ${CLAUDE_SKILL_DIR}/orchestrator-protocol.md — read the complete file before taking any action. Also read ${CLAUDE_SKILL_DIR}/wave-prompts.md for all agent prompt templates, ${CLAUDE_SKILL_DIR}/agent-rules.md for universal rules, and ${CLAUDE_SKILL_DIR}/thresholds.md for pass/fail criteria. Team name: ${TEAM_NAME}. Verify dir: ${VERIFY_DIR}. Report all spawn requests and wave results to team-lead.",
  subagent_type="general-purpose",
  team_name="${TEAM_NAME}",
  name="orchestrator",
  mode="acceptEdits",
  run_in_background=True
)
```

### Step 5: Your Identity

You are "team-lead" in this team. The orchestrator addresses you as "team-lead".

### Step 6: Ongoing Duties (after spawning orchestrator)

**MANDATORY: You MUST NOT spawn any agents without explicit human approval first.**

1. **Spawn requests:** When orchestrator sends a `SPAWN REQUEST`:
   a. STOP. Present the spawn plan to the human.
   b. WAIT for human to explicitly approve.
   c. Only after approval: spawn the requested agents with the exact specs provided.
   d. Notify orchestrator: `SendMessage(to="orchestrator", message="SPAWN CONFIRMED — Wave {N}: all agents spawned.")`

2. **Wave reports:** When orchestrator delivers a `WAVE {N} REPORT`:
   a. Present the full report to the human.
   b. WAIT for explicit human approval before proceeding.

3. **Approval relay:** After human approves:
   `SendMessage(to="orchestrator", message="WAVE {N} APPROVED — proceed.")`

4. **Change requests:** Relay human feedback to orchestrator. Wait for resolution.

5. **Never fix issues yourself** — always delegate to orchestrator.

6. **Silence is not approval.** If in doubt, ask the human.

### Step 7: Cleanup (after all waves pass)

```
TeamDelete()
```

---

## Reference Files (read on demand)

- Universal agent rules: [agent-rules.md](agent-rules.md)
- Orchestrator protocol + communication + JSONL logging: [orchestrator-protocol.md](orchestrator-protocol.md)
- All wave agent prompts (PRE-WAVE through WAVE 10): [wave-prompts.md](wave-prompts.md)
- Pass thresholds + timeout policy: [thresholds.md](thresholds.md)
- Output directory structure + marker system: [output-structure.md](output-structure.md)
