<!-- version: 2026-02 -->
# Agent Report Persistence

When invoking agents via Task tool, include in the prompt:
> "Save your report to `.ignorar/production-reports/{agent-name}/phase-{N}/{TIMESTAMP}-phase-{N}-{agent-name}-{slug}.md`"

## Naming Convention (UUID-based - prevents race conditions)

Format: `{TIMESTAMP}-phase-{N}-{agent-name}-{slug}.md`

Example: `2026-02-07-143022-phase-4-code-implementer-domain-layer.md`

**TIMESTAMP format:** `YYYY-MM-DD-HHmmss` (24-hour format)

**Why UUID-based?** Sequential numbering (001, 002...) breaks under parallel execution. Multiple agents may read the same number before any writes them, causing collisions. Timestamp-based naming ensures uniqueness without coordination.

Directory: `.ignorar/production-reports/{agent}/phase-{N}/`

## Implementation in Agent Prompts

All agent prompts must use timestamp variable. Example bash in hooks:
```bash
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
REPORT_PATH=".ignorar/production-reports/{agent}/phase-{N}/${TIMESTAMP}-phase-{N}-{agent}-{slug}.md"
```

## Agent Wave Timing (Phase 1 - Parallel Execution)

For verification cycles, agents are invoked in 2 waves:

### Wave 1 (Parallel - ~7 min max):
- best-practices-enforcer
- security-auditor
- hallucination-detector

### Wave 2 (Parallel - ~5 min max):
- code-reviewer
- test-generator

**Total time: ~12 minutes** (vs. ~87 minutes sequential, 86% improvement)

Each agent's report should include:
- Execution wave number (Wave 1 or Wave 2)
- Start timestamp (shared across wave)
- End timestamp (individual)
- Duration in minutes

## Workflow Reference
Read `.claude/workflow/` files on demand.
