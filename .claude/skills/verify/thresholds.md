# Pass Thresholds and Timeout Policy

## Wave Timeout and Retry Policy

For Waves 4–9, if an agent does not report within 10 minutes:
1. Mark that agent as TIMEOUT-FAIL
2. Continue with remaining agents in the wave — do NOT stop the wave
3. Report TIMEOUT-FAIL in the final verdict — do not silently skip
4. Retry once after all other agents in the wave complete

After each agent completes, verify its report file was created on disk.
An agent that runs but produces no report file is treated as FAILED.

---

## Pass Thresholds (all waves)

| Agent | PASS Criteria |
|-------|--------------|
| prewave-researcher | All libraries cached, BRIEFING.md written |
| scanner-bpe | 0 violations |
| scanner-security | 0 CRITICAL + 0 HIGH |
| scanner-hallucination | 0 hallucinations |
| wave1b-judge | Consolidated file written, 0 contradictions |
| wave2-reviewer | Score >= 9.0/10 |
| wave2-testgen | All tests pass + coverage >= 83% |
| fixer-N | All assigned findings FIXED |
| wave3b-validator | 0 gaps, ruff clean, mypy clean, pytest pass, coverage >= 83% |
| wave4-integration | 0 CRITICAL + 0 HIGH |
| wave4-async | 0 CRITICAL + 0 HIGH |
| wave5-semantic | 0 HIGH findings |
| wave5-circular | 0 circular import cycles |
| wave6-imports | 0 unresolvable absolute imports |
| wave6-deps | 0 CRITICAL + 0 HIGH CVEs |
| wave7-config | All env vars documented, all services consistent |
| wave8-hexarch | 0 hexagonal violations |
| wave9-smoke | Pipeline runs clean, all required fields present |
