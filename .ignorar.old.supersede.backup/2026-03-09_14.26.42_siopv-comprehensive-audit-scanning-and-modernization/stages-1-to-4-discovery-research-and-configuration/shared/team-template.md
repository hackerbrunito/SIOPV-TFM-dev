# Team Template: SIOPV Audit Stages

This template defines the reusable team structure for all audit stages (STAGE-1 through STAGE-4).

## Team Lifecycle

1. claude-main creates a team with TeamCreate and spawns an orchestrator via Agent.
2. claude-main names itself "claude-main" in the team.
3. claude-main delegates everything to the orchestrator. claude-main does NOT manage agents, does NOT read code, does NOT do analysis.
4. The orchestrator reads its briefing file and manages all rounds.
5. The orchestrator spawns rounds of 4-6 parallel agents maximum per batch.
6. Each agent operates with a clean context window (fresh context, no inherited conversation).
7. Agents write their reports to disk, return a condensed summary (1,000-2,000 tokens) to the orchestrator, and terminate.
8. A wave summarizer is spawned to read ONLY that round's reports and produce a round summary.
9. The orchestrator sends the round summary to claude-main via SendMessage.
10. Human checkpoint: The human reviews and approves the next round or requests corrections.
11. After all rounds complete, a final summarizer reads ONLY round summaries (NOT individual agent reports) and produces the stage deliverable.
12. Human approves the stage deliverable.

## Agent Types

| Type | Model | maxTurns | Tools | Purpose |
|------|-------|----------|-------|---------|
| Scanner | sonnet | 25 | Read, Grep, Glob, Bash (read-only) | Examine code files, report findings |
| Researcher | opus | 30 | Read, Grep, Glob, WebSearch, WebFetch | Research SOTA, compare with implementation |
| Summarizer | sonnet | 15 | Read, Grep, Glob, Write | Consolidate reports, deduplicate findings |
| Orchestrator | opus | 50 | Read, Grep, Glob, Bash, Write, Agent, SendMessage | Coordinate rounds, enforce checkpoints |

## Human Checkpoint Protocol

After each round:
1. Orchestrator sends round summary to claude-main via SendMessage
2. claude-main presents summary to human
3. Human reviews and approves (or requests corrections)
4. Only after approval does the orchestrator proceed to the next round

## File Naming Convention

Reports: `NNN_YYYY-MM-DD_HH.MM.SS_descriptive-name-ten-to-fifteen-words.md`
- NNN = zero-padded sequence number (001, 002, ...)
- Dots in timestamps (filesystem safe, human readable)
- 10-15 word descriptive kebab-case name

## Error Handling

- If an agent fails or times out: log the failure, report to claude-main, ask whether to retry or skip.
- If 2+ agents in a batch fail: STOP the stage and escalate to claude-main.
- After two failed corrections of the same agent, mark it as FAILED and report.
