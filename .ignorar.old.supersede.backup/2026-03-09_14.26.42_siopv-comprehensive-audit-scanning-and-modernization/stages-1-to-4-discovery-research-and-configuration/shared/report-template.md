# Report Template (Mandatory for All Agents)

Every agent report MUST follow this exact structure. Do not add, remove, or rename sections.

```markdown
# [Agent Name] Report

**Stage:** STAGE-N
**Round:** N, Batch: A
**Sequence:** NNN
**Timestamp:** YYYY-MM-DD HH:MM:SS
**Duration:** N minutes

## Mandate
[One sentence: what this agent was asked to do]

## Scope
[List of files/directories examined]

## Findings
### Finding F-NNN: [Title]
- **Severity:** CRITICAL | HIGH | MEDIUM | LOW | INFO
- **Category:** spec-implemented | spec-missing | beyond-spec | stale-orphaned | incidental
- **Location:** [file path:line number]
- **Description:** [what was found]
- **Evidence:** [grep output, code snippet, or reference]
- **Spec Reference:** [SPEC-PN-NN if applicable, or "beyond-spec"]
- **Importance (if missing):** 0-100 [only for spec-missing items]
- **Recommendation:** [what should be done, if applicable]

## Summary
- Total findings: N
- By severity: CRITICAL: N, HIGH: N, MEDIUM: N, LOW: N, INFO: N
- By category: spec-implemented: N, spec-missing: N, beyond-spec: N, stale-orphaned: N, incidental: N
- Files examined: N
- Files with findings: N

## Self-Verification
- [ ] All sections filled
- [ ] Every file path verified to exist
- [ ] Every finding has evidence
- [ ] Severity assignments are consistent
- [ ] Category assignments match the finding type
```
