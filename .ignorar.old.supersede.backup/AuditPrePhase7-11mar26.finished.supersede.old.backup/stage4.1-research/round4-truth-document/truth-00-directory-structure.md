# Truth-00: SIOPV `.claude/` Directory Structure
**Generated:** 2026-03-13
**Authority:** Round 3 Gap Analysis (Section 6) + Round 1 Best Practices
**Scope:** Complete `siopv/.claude/` file inventory — every file appears exactly once

---

## 1. Complete Directory Tree

```
siopv/.claude/
├── CLAUDE.md                                  [NEW]                                            → truth-02
├── settings.json                              [NEW] full project config                        → truth-01
├── settings.local.json                        [NEW] no source — created from scratch per truth-01 (original file deleted)  → truth-01
├── agents/
│   ├── best-practices-enforcer.md             [ADAPT] from sec-llm-workbench/.claude/agents/best-practices-enforcer.md  → truth-03
│   ├── security-auditor.md                    [ADAPT] from sec-llm-workbench/.claude/agents/security-auditor.md         → truth-03
│   ├── hallucination-detector.md              [ADAPT] from sec-llm-workbench/.claude/agents/hallucination-detector.md   → truth-03
│   ├── code-reviewer.md                       [ADAPT] from sec-llm-workbench/.claude/agents/code-reviewer.md            → truth-03
│   ├── test-generator.md                      [ADAPT] from sec-llm-workbench/.claude/agents/test-generator.md           → truth-03
│   ├── async-safety-auditor.md                [ADAPT] from sec-llm-workbench/.claude/agents/async-safety-auditor.md     → truth-03
│   ├── semantic-correctness-auditor.md        [ADAPT] from sec-llm-workbench/.claude/agents/semantic-correctness-auditor.md → truth-03
│   ├── integration-tracer.md                  [ADAPT] from sec-llm-workbench/.claude/agents/integration-tracer.md       → truth-03
│   ├── smoke-test-runner.md                   [ADAPT] from sec-llm-workbench/.claude/agents/smoke-test-runner.md        → truth-03
│   ├── config-validator.md                    [ADAPT] from sec-llm-workbench/.claude/agents/config-validator.md         → truth-03
│   ├── dependency-scanner.md                  [ADAPT] from sec-llm-workbench/.claude/agents/dependency-scanner.md       → truth-03
│   ├── circular-import-detector.md            [ADAPT] from sec-llm-workbench/.claude/agents/circular-import-detector.md → truth-03
│   ├── import-resolver.md                     [ADAPT] from sec-llm-workbench/.claude/agents/import-resolver.md          → truth-03
│   ├── code-implementer.md                    [ADAPT] from sec-llm-workbench/.claude/agents/code-implementer.md         → truth-03
│   ├── xai-explainer.md                       [ADAPT] from sec-llm-workbench/.claude/agents/xai-explainer.md            → truth-03
│   ├── hex-arch-remediator.md                 [NEW]  Stage 2 hexagonal violations (#1–#7)      → truth-03
│   ├── phase7-builder.md                      [NEW]  Streamlit/LangGraph Phase 7 builder       → truth-03
│   └── phase8-builder.md                      [NEW]  Jira+PDF Phase 8 builder                  → truth-03
├── hooks/
│   ├── session-start.sh                       [ADAPT] from sec-llm-workbench/.claude/hooks/session-start.sh  → truth-01
│   ├── session-end.sh                         [ADAPT] from sec-llm-workbench/.claude/hooks/session-end.sh    → truth-01
│   ├── pre-compact.sh                         [ADAPT] from sec-llm-workbench/.claude/hooks/pre-compact.sh    → truth-01
│   ├── post-code.sh                           [ADAPT] from sec-llm-workbench/.claude/hooks/post-code.sh      → truth-01
│   ├── pre-git-commit.sh                      [COPY]  from sec-llm-workbench/.claude/hooks/pre-git-commit.sh → truth-01
│   ├── pre-write.sh                           [COPY]  from sec-llm-workbench/.claude/hooks/pre-write.sh      → truth-01
│   └── coverage-gate.sh                       [NEW]   pytest cov ≥ 83% gate (PostToolUse)     → truth-01
├── rules/
│   ├── agent-reports.md                       [COPY]  from sec-llm-workbench/.claude/rules/agent-reports.md           → truth-05
│   ├── placeholder-conventions.md             [COPY]  from sec-llm-workbench/.claude/rules/placeholder-conventions.md → truth-05
│   └── tech-stack.md                          [ADAPT] from sec-llm-workbench/.claude/rules/tech-stack.md              → truth-05
├── docs/
│   ├── verification-thresholds.md             [ADAPT] from sec-llm-workbench/.claude/docs/verification-thresholds.md     → truth-05
│   ├── model-selection-strategy.md            [COPY]  from sec-llm-workbench/.claude/docs/model-selection-strategy.md    → truth-05
│   ├── python-standards.md                    [COPY]  from sec-llm-workbench/.claude/docs/python-standards.md            → truth-05
│   ├── errors-to-rules.md                     [NEW]   SIOPV-specific error log (seed with Stage 2 patterns)              → truth-05
│   └── siopv-phase7-8-context.md              [NEW]   Stage 3 library facts for code-implementer                         → truth-05
├── skills/
│   ├── verify/
│   │   └── SKILL.md                           [ADAPT] from sec-llm-workbench/.claude/skills/verify/SKILL.md             → truth-06
│   ├── langraph-patterns/
│   │   └── SKILL.md                           [COPY]  from sec-llm-workbench/.claude/skills/langraph-patterns/SKILL.md  → truth-06
│   ├── openfga-patterns/
│   │   └── SKILL.md                           [COPY]  from sec-llm-workbench/.claude/skills/openfga-patterns/SKILL.md   → truth-06
│   ├── presidio-dlp/
│   │   └── SKILL.md                           [COPY]  from sec-llm-workbench/.claude/skills/presidio-dlp/SKILL.md       → truth-06
│   ├── coding-standards-2026/
│   │   └── SKILL.md                           [COPY]  from sec-llm-workbench/.claude/skills/coding-standards-2026/SKILL.md → truth-06
│   └── siopv-remediate/
│       └── SKILL.md                           [NEW]   triggers hex-arch-remediator; disable-model-invocation: true       → truth-06
└── workflow/
    ├── briefing.md                            [NEW]   SIOPV session state (injected by session-start.sh)  → truth-11
    └── compaction-log.md                      [NEW]   cross-session continuity log                         → truth-11
```

**Total files: 41** — 15 ADAPT · 15 COPY · 11 NEW
*(Skills count each directory as 1 file entry via its SKILL.md)*

---

## 2. File-to-Truth Mapping Table

| File | Action | Source | Truth File |
|------|--------|--------|------------|
| `CLAUDE.md` | NEW | — | truth-02 |
| `settings.json` | NEW | sec-llm-workbench/.claude/settings.json (reference) | truth-01 |
| `settings.local.json` | NEW | — (no source; original file was deleted) | truth-01 |
| `hooks/session-start.sh` | ADAPT | sec-llm-workbench/.claude/hooks/session-start.sh | truth-01 |
| `hooks/session-end.sh` | ADAPT | sec-llm-workbench/.claude/hooks/session-end.sh | truth-01 |
| `hooks/pre-compact.sh` | ADAPT | sec-llm-workbench/.claude/hooks/pre-compact.sh | truth-01 |
| `hooks/post-code.sh` | ADAPT | sec-llm-workbench/.claude/hooks/post-code.sh | truth-01 |
| `hooks/pre-git-commit.sh` | COPY | sec-llm-workbench/.claude/hooks/pre-git-commit.sh | truth-01 |
| `hooks/pre-write.sh` | COPY | sec-llm-workbench/.claude/hooks/pre-write.sh | truth-01 |
| `hooks/coverage-gate.sh` | NEW | — | truth-01 |
| `agents/best-practices-enforcer.md` | ADAPT | sec-llm-workbench/.claude/agents/best-practices-enforcer.md | truth-03 |
| `agents/security-auditor.md` | ADAPT | sec-llm-workbench/.claude/agents/security-auditor.md | truth-03 |
| `agents/hallucination-detector.md` | ADAPT | sec-llm-workbench/.claude/agents/hallucination-detector.md | truth-03 |
| `agents/code-reviewer.md` | ADAPT | sec-llm-workbench/.claude/agents/code-reviewer.md | truth-03 |
| `agents/test-generator.md` | ADAPT | sec-llm-workbench/.claude/agents/test-generator.md | truth-03 |
| `agents/async-safety-auditor.md` | ADAPT | sec-llm-workbench/.claude/agents/async-safety-auditor.md | truth-03 |
| `agents/semantic-correctness-auditor.md` | ADAPT | sec-llm-workbench/.claude/agents/semantic-correctness-auditor.md | truth-03 |
| `agents/integration-tracer.md` | ADAPT | sec-llm-workbench/.claude/agents/integration-tracer.md | truth-03 |
| `agents/smoke-test-runner.md` | ADAPT | sec-llm-workbench/.claude/agents/smoke-test-runner.md | truth-03 |
| `agents/config-validator.md` | ADAPT | sec-llm-workbench/.claude/agents/config-validator.md | truth-03 |
| `agents/dependency-scanner.md` | ADAPT | sec-llm-workbench/.claude/agents/dependency-scanner.md | truth-03 |
| `agents/circular-import-detector.md` | ADAPT | sec-llm-workbench/.claude/agents/circular-import-detector.md | truth-03 |
| `agents/import-resolver.md` | ADAPT | sec-llm-workbench/.claude/agents/import-resolver.md | truth-03 |
| `agents/code-implementer.md` | ADAPT | sec-llm-workbench/.claude/agents/code-implementer.md | truth-03 |
| `agents/xai-explainer.md` | ADAPT | sec-llm-workbench/.claude/agents/xai-explainer.md | truth-03 |
| `agents/hex-arch-remediator.md` | NEW | — | truth-03 |
| `agents/phase7-builder.md` | NEW | — | truth-03 |
| `agents/phase8-builder.md` | NEW | — | truth-03 |
| `rules/agent-reports.md` | COPY | sec-llm-workbench/.claude/rules/agent-reports.md | truth-05 |
| `rules/placeholder-conventions.md` | COPY | sec-llm-workbench/.claude/rules/placeholder-conventions.md | truth-05 |
| `rules/tech-stack.md` | ADAPT | sec-llm-workbench/.claude/rules/tech-stack.md | truth-05 |
| `docs/verification-thresholds.md` | ADAPT | sec-llm-workbench/.claude/docs/verification-thresholds.md | truth-05 |
| `docs/model-selection-strategy.md` | COPY | sec-llm-workbench/.claude/docs/model-selection-strategy.md | truth-05 |
| `docs/python-standards.md` | COPY | sec-llm-workbench/.claude/docs/python-standards.md | truth-05 |
| `docs/errors-to-rules.md` | NEW | — | truth-05 |
| `docs/siopv-phase7-8-context.md` | NEW | — | truth-05 |
| `skills/verify/SKILL.md` | ADAPT | sec-llm-workbench/.claude/skills/verify/SKILL.md | truth-06 |
| `skills/langraph-patterns/SKILL.md` | COPY | sec-llm-workbench/.claude/skills/langraph-patterns/SKILL.md | truth-06 |
| `skills/openfga-patterns/SKILL.md` | COPY | sec-llm-workbench/.claude/skills/openfga-patterns/SKILL.md | truth-06 |
| `skills/presidio-dlp/SKILL.md` | COPY | sec-llm-workbench/.claude/skills/presidio-dlp/SKILL.md | truth-06 |
| `skills/coding-standards-2026/SKILL.md` | COPY | sec-llm-workbench/.claude/skills/coding-standards-2026/SKILL.md | truth-06 |
| `skills/siopv-remediate/SKILL.md` | NEW | — | truth-06 |
| `workflow/briefing.md` | NEW | — | truth-11 |
| `workflow/compaction-log.md` | NEW | — | truth-11 |

---

## 3. Truth File Responsibility Matrix

| Truth File | Files It Specifies | Dependencies |
|------------|-------------------|--------------|
| truth-00 | This directory structure | — |
| truth-01 | `settings.json`, `settings.local.json`, `hooks/*.sh` (7 files) | truth-00 |
| truth-02 | `CLAUDE.md` | truth-00 |
| truth-03 | `agents/*.md` (18 files: 15 ADAPT + 3 NEW) | truth-00 |
| truth-04 | *(reserved — no workflow/*.md beyond briefing/compaction-log)* | truth-00 |
| truth-05 | `rules/*.md` (3), `docs/*.md` (5) | truth-00 |
| truth-06 | `skills/*/SKILL.md` (6 directories) | truth-00 |
| truth-07 | `~/.claude/projects/.../memory/` topic files | truth-00 |
| truth-08 | `~/.claude/CLAUDE.md`, `~/.claude/settings.json`, `~/.claude/agents/researcher-[1-3].md` | truth-00 |
| truth-09 | Cross-file wiring: hook↔settings.json registration; skill↔CLAUDE.md @-import references; agent↔verify/SKILL.md list | truth-01…truth-08 |
| truth-10 | Implementation verification checklist (Stage 4.2 acceptance criteria) | truth-01…truth-08 |
| truth-11 | `workflow/briefing.md`, `workflow/compaction-log.md` | truth-00, truth-01 |

---

## 4. Excluded Items (DO NOT INCLUDE)

| File/Dir | Category | Why Excluded |
|----------|----------|--------------|
| `workflow/briefing.md` (meta version) | META-ONLY | Contains audit-stage state for meta-orchestration; confuses implementation context |
| `workflow/orchestrator-briefing.md` | META-ONLY | Stage 1–4 audit orchestration — irrelevant to SIOPV coding |
| `workflow/setup-checklist.md` | META-ONLY | Meta-project project setup checklist |
| `workflow/spec-findings.md` | META-ONLY | Meta-project specification tracker |
| `agents/final-report-agent.md` | META-ONLY | Generates audit summaries, not SIOPV code |
| `agents/report-summarizer.md` | META-ONLY | Aggregates audit reports — wrong tool for SIOPV |
| `agents/vulnerability-researcher.md` | META-ONLY | CVE/OSINT research; SIOPV has `cve-research` skill |
| `agents/regression-guard.md` | NOT LISTED | Not in Round 3 applicable set; meta-project internal |
| `agents/static-checks-agent.md` | NOT LISTED | Not in Round 3 applicable set; meta-project internal |
| `scripts/` (12 files) | META-ONLY | Cost tracking, MCP health — wrong paths for SIOPV |
| `handoffs/` (9 files) | META-ONLY | Dated meta-project session handoffs |
| `docs/techniques.md` | META-ONLY | Meta-project techniques catalog |
| `docs/mcp-setup.md` | META-ONLY | Meta-project MCP setup |
| `docs/agent-tool-schemas.md` | META-ONLY | Meta-project orchestration tooling |
| `docs/traceability.md` | META-ONLY | Meta-project tracing setup |
| `docs/errors-to-rules.md` (meta version) | SUPERSEDED | SIOPV gets its own `docs/errors-to-rules.md` [NEW] |
| `skills/show-trace/` | META-ONLY | Meta-project tracing skill |
| `skills/generate-report/` | META-ONLY | Meta-project report generation |
| `skills/orchestrator-protocol/` | META-ONLY | Meta-project orchestrator invocation |
| `skills/techniques-reference/` | META-ONLY | Meta-project techniques catalog |
| `skills/new-project/` | META-ONLY | Meta-project project creation |
| `skills/init-session/` | META-ONLY | Meta-project session initialization |
| `skills/run-tests/` | META-ONLY | Superseded by `hooks/coverage-gate.sh` + `/verify` |
| `skills/scan-vulnerabilities/` | META-ONLY | SIOPV uses `cve-research` skill |
| `skills/trivy-integration/` | META-ONLY | Trivy parsing already in SIOPV Phase 1 |
| `skills/xai-visualization/` | META-ONLY | Covered by adapted `xai-explainer.md` agent |
| `.build/active-project` mechanism | META-ONLY | Multi-project routing — SIOPV is a single project |
| `hooks/pre-commit.sh` | ORPHANED | Not registered in settings.json (R3 §2 #3) — do not copy |
| `hooks/test-framework.sh` | ORPHANED | Not registered in settings.json (R3 §2 #3) — do not copy |
| `hooks/verify-best-practices.sh` | ORPHANED | Not registered in settings.json (R3 §2 #3) — do not copy |
| `settings.json.back` | ORPHANED | Backup file — confusing, no functional purpose |

---

## 5. Implementation Order

Stage 4.2 must create files in this dependency order:

```
BATCH 1 — Foundation (no dependencies)
  1. workflow/briefing.md                    (truth-11) — needed by session-start.sh
  2. workflow/compaction-log.md              (truth-11) — needed by session-start.sh + pre-compact.sh
  3. docs/siopv-phase7-8-context.md          (truth-05) — needed by code-implementer + phase7/8 builders

BATCH 2 — Settings + Hooks (depend on briefing.md path being known)
  4. settings.json                           (truth-01) — registers all hooks
  5. settings.local.json                     (truth-01) [NEW — no source; original file deleted, create from scratch]
  6. hooks/session-start.sh                  (truth-01)
  7. hooks/session-end.sh                    (truth-01)
  8. hooks/pre-compact.sh                    (truth-01)
  9. hooks/post-code.sh                      (truth-01) [ADAPT — remove META_PROJECT_DIR guard per truth-01]
 10. hooks/pre-git-commit.sh                 (truth-01) [COPY]
 11. hooks/pre-write.sh                      (truth-01) [COPY]
 12. hooks/coverage-gate.sh                  (truth-01) [NEW]

BATCH 3 — CLAUDE.md (depends on knowing which @-imports exist)
 13. CLAUDE.md                               (truth-02)

BATCH 4 — Rules + Docs (no inter-agent dependencies)
 14. rules/agent-reports.md                  (truth-05) [COPY]
 15. rules/placeholder-conventions.md        (truth-05) [COPY]
 16. rules/tech-stack.md                     (truth-05) [ADAPT]
 17. docs/verification-thresholds.md         (truth-05) [ADAPT]
 18. docs/model-selection-strategy.md        (truth-05) [COPY]
 19. docs/python-standards.md                (truth-05) [COPY]
 20. docs/errors-to-rules.md                 (truth-05) [NEW]

BATCH 5 — Skills (depend on agent list being final)
 21. skills/langraph-patterns/SKILL.md       (truth-06) [COPY]
 22. skills/openfga-patterns/SKILL.md        (truth-06) [COPY]
 23. skills/presidio-dlp/SKILL.md            (truth-06) [COPY]
 24. skills/coding-standards-2026/SKILL.md   (truth-06) [COPY]
 25. skills/verify/SKILL.md                  (truth-06) [ADAPT — 14-agent list]
 26. skills/siopv-remediate/SKILL.md         (truth-06) [NEW]

BATCH 6 — Agents (depend on docs/context being available)
 27-41. agents/*.md — 15 ADAPT + 3 NEW       (truth-03)
        Recommended sub-order: core verifiers first, then builders
        27. code-implementer.md       [ADAPT — embeds phase7/8 library patterns]
        28. best-practices-enforcer.md
        29. security-auditor.md
        30. hallucination-detector.md
        31. code-reviewer.md
        32. test-generator.md
        33. async-safety-auditor.md
        34. semantic-correctness-auditor.md
        35. integration-tracer.md
        36. smoke-test-runner.md
        37. config-validator.md
        38. dependency-scanner.md
        39. circular-import-detector.md
        40. import-resolver.md
        41. xai-explainer.md
        42. hex-arch-remediator.md    [NEW]
        43. phase7-builder.md         [NEW]
        44. phase8-builder.md         [NEW]

BATCH 7 — User-level changes (external to siopv/.claude/)
 45. ~/.claude/CLAUDE.md              (truth-08) — fix bypassPermissions → acceptEdits
 46. ~/.claude/settings.json          (truth-08) — add attribution commit:none
 47. ~/.claude/agents/researcher-1.md (truth-08) — add Project Context block
 48. ~/.claude/agents/researcher-2.md (truth-08) — add Project Context block
 49. ~/.claude/agents/researcher-3.md (truth-08) — add Project Context block
 50. memory/MEMORY.md                 (truth-07) — trim to ≤ 200 lines
 51. memory/siopv-hooks-stage4.md     (truth-07) — new topic file (lines 201–217 extracted)

BATCH 8 — Cross-file verification
 52. Wiring audit: verify all hook registrations in settings.json (truth-09)
 53. Acceptance checklist sign-off (truth-10)
```
