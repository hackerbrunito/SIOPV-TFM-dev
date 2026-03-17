---
task: orchestrate /verify pipeline waves 6–9
status: Wave 5 COMPLETE, awaiting approval for Wave 6
last_updated: 2026-03-17T10:50:00Z
---

# Orchestrator Handoff — Post Wave 5

## Pipeline State

| Wave | Status | Result |
|------|--------|--------|
| Pre-wave | COMPLETE | 5 libraries cached, BRIEFING.md written |
| Wave 1 | COMPLETE | PASS — 0 actionable findings (5 combined scanners) |
| Wave 1B | COMPLETE | PASS — 1 LOW finding (non-blocking) |
| Wave 2 | COMPLETE | PASS — reviewer 9/10, testgen 92% coverage, 8 tests added (1,558 total) |
| Wave 3 | SKIPPED | No fixers needed (0 actionable findings) |
| Wave 4 | COMPLETE | PASS — integration 5 MEDIUM, async 1 MEDIUM (all non-blocking) |
| Wave 5 | COMPLETE | PASS — semantic 2 MEDIUM (non-blocking), circular 0 cycles |
| Wave 6 | PENDING | import-resolver + dependency-scanner (2 agents, parallel) |
| Wave 7 | PENDING | config-validator (1 agent) |
| Wave 8 | PENDING | hex-arch-remediator (1 agent) |
| Wave 9 | PENDING | smoke-test-runner (1 agent) |

## Current Position

Wave 5 report was ALREADY SENT to team-lead. Team-lead acknowledged and approved.

**NEXT IMMEDIATE ACTION:** Send SPAWN REQUEST for Wave 6 to team-lead.

## Wave 6 SPAWN REQUEST (ready to send)

2 agents, parallel:

**Agent 1: name=wave6-imports** (import-resolver)
- Method: Walk all .py files under src/ using ast, extract absolute imports, test each with `uv run python3 -c "import {module}"`
- Skip: relative imports, TYPE_CHECKING blocks, try/except ImportError blocks
- PASS: 0 unresolvable absolute imports
- Report: /Users/bruno/siopv/.verify-17-03-2026/reports/wave6-import-resolver.md

**Agent 2: name=wave6-deps** (dependency-scanner)
- Method: `cd /Users/bruno/siopv && uv run pip-audit --format=json`
- PASS: 0 CRITICAL + 0 HIGH CVEs
- Report: /Users/bruno/siopv/.verify-17-03-2026/reports/wave6-dependency-scanner.md

Both agents use standard handoff/offloading/context rules. Full prompts in wave-prompts.md.

## Remaining Waves After Wave 6

**Wave 7** — config-validator (1 agent):
- Check all settings.* accesses have .env.example entry
- Check all Docker service refs match docker-compose.yml
- PASS: all env vars documented, all services consistent

**Wave 8** — hex-arch-remediator (1 agent):
- Regression check on 7 specific hex violations fixed in remediation-hardening
- PASS: 0 hexagonal violations

**Wave 9** — smoke-test-runner (1 agent, runs LAST):
- Import check, pipeline run (120s timeout), Streamlit health check
- PASS: pipeline runs clean, all required fields present

## Completion Protocol

After Wave 9 PASS:
1. Run post-wave actions (ruff format/check, mypy, pytest --cov)
2. Clear pending markers: `rm -rf /Users/bruno/siopv/.build/checkpoints/pending/*`
3. Send to team-lead: "ALL WAVES PASSED. Marker cleanup complete. Verifications passed. Ready for TeamDelete."

## Key Paths

- VERIFY_DIR: /Users/bruno/siopv/.verify-17-03-2026
- Context7 cache: /Users/bruno/siopv/.verify-17-03-2026/context7-cache/
- Scan results: /Users/bruno/siopv/.verify-17-03-2026/scans/
- Reports: /Users/bruno/siopv/.verify-17-03-2026/reports/
- Protocol files: /Users/bruno/siopv/.claude/skills/verify/
- Wave prompts: /Users/bruno/siopv/.claude/skills/verify/wave-prompts.md
- Agent rules: /Users/bruno/siopv/.claude/skills/verify/agent-rules.md
- Thresholds: /Users/bruno/siopv/.claude/skills/verify/thresholds.md

## Constraint

Max 5 agents per wave (human-imposed). Sweet spot 3–5.
