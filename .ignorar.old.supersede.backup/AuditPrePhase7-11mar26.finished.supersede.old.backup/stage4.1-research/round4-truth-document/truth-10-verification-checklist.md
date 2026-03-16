# Truth-10: Stage 4.2 Implementation Verification Checklist
**Generated:** 2026-03-13
**Authority:** truth-00 through truth-08 + truth-11
**Scope:** Acceptance criteria for every Stage 4.2 deliverable

---

## 1. Pre-Implementation Checklist (do BEFORE creating any files)

- [ ] **[truth-08]** Confirm `~/.claude/CLAUDE.md` exists and is readable
- [ ] **[truth-08]** Confirm `~/.claude/rules/deterministic-execution-protocol.md` exists
- [ ] **[truth-08]** Confirm `~/.claude/settings.json` exists and is valid JSON
- [ ] **[truth-07]** Count lines in `~/.claude/projects/-Users-bruno-sec-llm-workbench/memory/MEMORY.md` — confirm it is 217 (over limit, fix needed)
- [ ] **[truth-00]** Confirm `siopv/` directory exists at `/Users/bruno/siopv/`
- [ ] **[truth-01]** Confirm `siopv/.claude/` does NOT already have `settings.json` (new file, not overwrite)
- [ ] **[truth-01]** Confirm meta-project source hooks exist: `sec-llm-workbench/.claude/hooks/{session-start,session-end,pre-compact,post-code,pre-git-commit,pre-write}.sh`
- [ ] **[truth-03]** Confirm meta-project source agents exist in `sec-llm-workbench/.claude/agents/` (15 ADAPT sources)
- [ ] **[truth-00]** Create required output dirs: `siopv/.claude/{agents,hooks,rules,docs,skills/verify,skills/langraph-patterns,skills/openfga-patterns,skills/presidio-dlp,skills/coding-standards-2026,skills/siopv-remediate,workflow}/`
- [ ] **[truth-01]** Create `.build/checkpoints/pending/` in siopv root (required by hooks)
- [ ] **[truth-01]** Create `.build/logs/agents/` and `.build/logs/sessions/` dirs in siopv root

---

## 2. File Creation Checklist (implementation order per truth-00 §5)

### Batch 1 — Foundation
- [ ] **[truth-11]** `siopv/.claude/workflow/briefing.md` — 192 lines, contains `> Last updated:` marker, `## Compact Instructions` section, 4 open violations table, NEXT IMMEDIATE ACTION
- [ ] **[truth-11]** `siopv/.claude/workflow/compaction-log.md` — single seed entry `2026-03-13T00:00:00Z — Log initialized`
- [ ] **[truth-05]** `siopv/.claude/docs/siopv-phase7-8-context.md` — Stage 3 library facts: Streamlit, LangGraph, Jira ADF, fpdf2, Redis, OTel, LangSmith patterns

### Batch 2 — Settings + Hooks
- [ ] **[truth-01]** `siopv/.claude/settings.json` — valid JSON, all 8 hook event types registered, `attribution.commit=none`, `statusLine.command` references `.build/current-phase`
- [ ] **[truth-01]** `siopv/.claude/settings.local.json` — 2-key file: `permissions.allow=["Bash(curl:*)"]`, `claudeMdExcludes=[]`
- [ ] **[truth-11]** `siopv/.claude/hooks/session-start.sh` — uses hardcoded `/Users/bruno/siopv/` paths (single-project design — NOT sec-llm-workbench paths), idempotency lock guard present
- [ ] **[truth-11]** `siopv/.claude/hooks/session-end.sh` — uses `${CLAUDE_PROJECT_DIR}` paths, updates `> Last updated:` in briefing.md
- [ ] **[truth-11]** `siopv/.claude/hooks/pre-compact.sh` — uses `${CLAUDE_PROJECT_DIR}` paths, `transcript_path` null guard, `async: true` compatible
- [ ] **[truth-01]** `siopv/.claude/hooks/post-code.sh` — ADAPTED (meta-project guard REMOVED: lines checking `FILE_PATH` starts with `META_PROJECT_DIR` deleted)
- [ ] **[truth-01]** `siopv/.claude/hooks/pre-git-commit.sh` — COPY as-is; `.build/active-project` fallback is already graceful
- [ ] **[truth-01]** `siopv/.claude/hooks/pre-write.sh` — COPY as-is
- [ ] **[truth-01]** `siopv/.claude/hooks/coverage-gate.sh` — NEW; checks `pytest --cov` output for `TOTAL...83%` threshold; writes pending marker if below

### Batch 3 — CLAUDE.md
- [ ] **[truth-02]** `siopv/CLAUDE.md` — ≤ 97 lines, two `@`-imports (briefing.md + compaction-log.md), Phase 7 gating conditions section, skills table, compact instructions section

### Batch 4 — Rules + Docs
- [ ] **[truth-05]** `siopv/.claude/rules/agent-reports.md` — COPY from sec-llm-workbench
- [ ] **[truth-05]** `siopv/.claude/rules/placeholder-conventions.md` — COPY from sec-llm-workbench
- [ ] **[truth-05]** `siopv/.claude/rules/tech-stack.md` — ADAPT: Phase 7/8 libs added (streamlit, fpdf2, redis.asyncio, langsmith), `mcp-setup.md` reference removed
- [ ] **[truth-05]** `siopv/.claude/docs/verification-thresholds.md` — ADAPT: coverage threshold `80%→83%`, Phase 7 health check section added, `## Cost Monitoring` removed
- [ ] **[truth-05]** `siopv/.claude/docs/model-selection-strategy.md` — COPY from sec-llm-workbench
- [ ] **[truth-05]** `siopv/.claude/docs/python-standards.md` — COPY from sec-llm-workbench
- [ ] **[truth-05]** `siopv/.claude/docs/errors-to-rules.md` — NEW; seeded with 5 Stage 2 error patterns (adapter imports, CLI DI=None, uncached OpenFGA, missing DLPPort, node instantiates use case)

### Batch 5 — Skills
- [ ] **[truth-06]** `siopv/.claude/skills/langraph-patterns/SKILL.md` — COPY
- [ ] **[truth-06]** `siopv/.claude/skills/openfga-patterns/SKILL.md` — COPY
- [ ] **[truth-06]** `siopv/.claude/skills/presidio-dlp/SKILL.md` — COPY
- [ ] **[truth-06]** `siopv/.claude/skills/coding-standards-2026/SKILL.md` — COPY
- [ ] **[truth-06]** `siopv/.claude/skills/verify/SKILL.md` — ADAPT: agent count 15→14, `active-project` lookup removed (hardcoded `/Users/bruno/siopv`), `regression-guard` removed, `hex-arch-remediator` added to Wave 3, coverage floor `75→83`
- [ ] **[truth-06]** `siopv/.claude/skills/siopv-remediate/SKILL.md` — NEW; `disable-model-invocation: true`, delegates to `hex-arch-remediator`, lists all 7 violations

### Batch 6 — Agents (18 files; start with code-implementer)
- [ ] **[truth-03]** `siopv/.claude/agents/code-implementer.md` — ADAPT: Project Context block set to `/Users/bruno/siopv/`, Phase 7/8 context reference added, `memory: true→project`
- [ ] **[truth-03]** `siopv/.claude/agents/best-practices-enforcer.md` — ADAPT: Project Context block, `memory: true→project`
- [ ] **[truth-03]** `siopv/.claude/agents/security-auditor.md` — ADAPT + SIOPV-specific checks section (OpenFGA tuples, Presidio config, hardcoded model IDs, Streamlit input, Jira creds)
- [ ] **[truth-03]** `siopv/.claude/agents/hallucination-detector.md` — ADAPT + Phase 7/8 library facts table (Streamlit/LangGraph/Jira/fpdf2/redis)
- [ ] **[truth-03]** `siopv/.claude/agents/code-reviewer.md` — ADAPT + Phase 7/8 review criteria (no while-True, st.cache_resource, ADF, fpdf2 fname, ThreadPoolExecutor)
- [ ] **[truth-03]** `siopv/.claude/agents/test-generator.md` — ADAPT + SIOPV Coverage Floor section (83%, 1404 tests baseline)
- [ ] **[truth-03]** `siopv/.claude/agents/async-safety-auditor.md` — ADAPT + Streamlit Async Bridge Verification section (ThreadPoolExecutor pattern, flag asyncio.run in callbacks)
- [ ] **[truth-03]** `siopv/.claude/agents/semantic-correctness-auditor.md` — ADAPT: Project Context only
- [ ] **[truth-03]** `siopv/.claude/agents/integration-tracer.md` — ADAPT + LangGraph Node→Port Tracing section (dead `enrich_node_async`, interrupt/resume chain)
- [ ] **[truth-03]** `siopv/.claude/agents/smoke-test-runner.md` — ADAPT: Project Context only
- [ ] **[truth-03]** `siopv/.claude/agents/config-validator.md` — ADAPT + Streamlit env vars section (STREAMLIT_SERVER_PORT, SIOPV_GRAPH_CHECKPOINT_DB)
- [ ] **[truth-03]** `siopv/.claude/agents/dependency-scanner.md` — ADAPT: Project Context only
- [ ] **[truth-03]** `siopv/.claude/agents/circular-import-detector.md` — ADAPT: Project Context only
- [ ] **[truth-03]** `siopv/.claude/agents/import-resolver.md` — ADAPT: Project Context only
- [ ] **[truth-03]** `siopv/.claude/agents/xai-explainer.md` — ADAPT + SIOPV Configuration section (model path `/models/xgboost_classifier.json`, class names LOW/MEDIUM/HIGH/CRITICAL, `plt.close(fig)` note)
- [ ] **[truth-03]** `siopv/.claude/agents/hex-arch-remediator.md` — NEW; violations #1–#7 fix order, `permissionMode: acceptEdits`, `memory: project`
- [ ] **[truth-03]** `siopv/.claude/agents/phase7-builder.md` — NEW; prerequisites check, Stage 3 library facts table, implementation layers (hexagonal order), PASS criteria
- [ ] **[truth-03]** `siopv/.claude/agents/phase8-builder.md` — NEW; ADF helper, exactly-3-topology-changes constraint, `httpx.AsyncClient` for Jira

### Batch 7 — User-Level Changes
- [ ] **[truth-08]** `~/.claude/CLAUDE.md` — edit ONE line: `mode="bypassPermissions"` → `mode="acceptEdits"` on orchestrator spawn line (line 55)
- [ ] **[truth-08]** `~/.claude/settings.json` — add `"attribution": {"commit": "none"}` block before closing brace
- [ ] **[truth-08]** `~/.claude/rules/deterministic-execution-protocol.md` — edit ONE line: `mode="bypassPermissions"` → `mode="acceptEdits"` (line 48)
- [ ] **[truth-08]** `~/.claude/agents/researcher-1.md` — CREATE at user level with Project Context block (active-project lookup + siopv fallback)
- [ ] **[truth-08]** `~/.claude/agents/researcher-2.md` — CREATE at user level with Project Context block
- [ ] **[truth-08]** `~/.claude/agents/researcher-3.md` — CREATE at user level with Project Context block
- [ ] **[truth-07]** `~/.claude/projects/-Users-bruno-sec-llm-workbench/memory/siopv-hooks-stage4.md` — CREATE topic file with hook classification + P1 agents table
- [ ] **[truth-07]** `~/.claude/projects/-Users-bruno-sec-llm-workbench/memory/MEMORY.md` — TRIM lines 201–217 (Hook Classification block), add pointer to `siopv-hooks-stage4.md`; target ≤ 185 lines
- [ ] **[truth-07]** `~/.claude/projects/-Users-bruno-siopv/memory/MEMORY.md` — CREATE (~78 lines, phase table, blockers, key paths, topic file pointers)
- [ ] **[truth-07]** `~/.claude/projects/-Users-bruno-siopv/memory/siopv-stage-results.md` — CREATE topic file
- [ ] **[truth-07]** `~/.claude/projects/-Users-bruno-siopv/memory/siopv-architecture.md` — CREATE topic file
- [ ] **[truth-07]** `~/.claude/projects/-Users-bruno-siopv/memory/siopv-violations.md` — CREATE topic file (Stage 2 violations with line refs + Stage 3 library facts)
- [ ] **[truth-07]** `~/.claude/projects/-Users-bruno-siopv/memory/siopv-phase7-8-context.md` — CREATE topic file (readiness checklist, open questions, integration risks)

---

## 3. Wiring Verification Checklist

Run after ALL files are created:

- [ ] **[truth-01]** Every hook referenced in `settings.json` has a corresponding `.sh` file in `siopv/.claude/hooks/` and is `chmod +x`
- [ ] **[truth-01]** settings.json `SessionStart` block has 3 entries: session-start.sh + daily checkpoint reminder + compact context echo
- [ ] **[truth-01]** `pre-compact.sh` registration includes `"async": true` — verify in PreCompact block
- [ ] **[truth-02]** Both `@`-imports in `siopv/CLAUDE.md` resolve: `@.claude/workflow/briefing.md` and `@.claude/workflow/compaction-log.md`
- [ ] **[truth-02]** `siopv/CLAUDE.md` lists exactly 6 skills matching the 6 directories in `siopv/.claude/skills/`
- [ ] **[truth-03]** All 18 agent files have valid YAML frontmatter (name, description, tools, model, permissionMode)
- [ ] **[truth-03]** All agents use `model: sonnet` (zero haiku, zero opus)
- [ ] **[truth-03]** All agents use `permissionMode: acceptEdits` (zero bypassPermissions)
- [ ] **[truth-06]** `skills/verify/SKILL.md` lists exactly 14 agents in waves (Wave 1: 3, Wave 2: 2, Wave 3: 9) — hex-arch-remediator included in Wave 3 per Conflict #1 resolution; count corrected from original "15" per Conflict #5 resolution
- [ ] **[truth-06]** `skills/verify/SKILL.md` has no `.build/active-project` reference; hardcoded path is `/Users/bruno/siopv`
- [ ] **[truth-06]** `skills/siopv-remediate/SKILL.md` has `disable-model-invocation: true`
- [ ] **[truth-11]** `briefing.md` `> Last updated:` marker is on a line by itself (hooks use `grep -q "^> Last updated:"`)
- [ ] **[truth-01]** `post-code.sh` does NOT contain the meta-project guard block (`META_PROJECT_DIR` / `FILE_PATH` check)
- [ ] **[truth-00]** Total file count in `siopv/.claude/`: 41 files (verify with `find siopv/.claude -type f | wc -l`)

---

## 4. Functional Verification Checklist

```bash
cd /Users/bruno/siopv
```

- [ ] **[truth-01]** `cat .claude/settings.json | jq .` exits 0 (valid JSON)
- [ ] **[truth-11]** `bash .claude/hooks/session-start.sh` prints briefing.md content and last 5 log lines, exits 0
- [ ] **[truth-11]** `bash .claude/hooks/session-end.sh` updates `> Last updated:` timestamp in briefing.md, exits 0
- [ ] **[truth-11]** `bash .claude/hooks/pre-compact.sh <<< '{}'` updates timestamp, exits 0 (null transcript handled)
- [ ] **[truth-01]** `echo '{"tool_input":{"command":"pytest --cov src/ --cov-report=term"}, "tool_output":"TOTAL   100   20   80%"}' | bash .claude/hooks/coverage-gate.sh` — creates pending marker `coverage-below-threshold` (80% < 83%)
- [ ] **[truth-01]** `echo '{"tool_input":{"command":"pytest --cov src/ --cov-report=term"}, "tool_output":"TOTAL   100   5   95%"}' | bash .claude/hooks/coverage-gate.sh` — NO pending marker created (95% ≥ 83%)
- [ ] **[truth-02]** `wc -l siopv/CLAUDE.md` reports ≤ 97 lines
- [ ] **[truth-07]** `wc -l ~/.claude/projects/-Users-bruno-sec-llm-workbench/memory/MEMORY.md` reports ≤ 185 lines
- [ ] **[truth-07]** `wc -l ~/.claude/projects/-Users-bruno-siopv/memory/MEMORY.md` reports ≤ 100 lines
- [ ] **[truth-08]** `grep "bypassPermissions" ~/.claude/CLAUDE.md` returns EMPTY (fixed)
- [ ] **[truth-08]** `grep "bypassPermissions" ~/.claude/rules/deterministic-execution-protocol.md` returns EMPTY (fixed)
- [ ] **[truth-08]** `grep '"attribution"' ~/.claude/settings.json` returns a match (added)

---

## 5. Regression Checklist

- [ ] **[truth-08]** `claude --model claude-sonnet-4-6` in `sec-llm-workbench/` still loads the meta-project session correctly (no settings.json breakage)
- [ ] **[truth-08]** `grep "bypassPermissions" ~/.claude/CLAUDE.md` is empty — but meta-project `sec-llm-workbench/.claude/` is UNCHANGED (only user-level was edited)
- [ ] **[truth-00]** No meta-project files were accidentally created in `siopv/.claude/workflow/` (only `briefing.md` and `compaction-log.md` should be there)
- [ ] **[truth-00]** No excluded files were copied: `regression-guard.md`, `final-report-agent.md`, `report-summarizer.md`, `vulnerability-researcher.md` must NOT exist in `siopv/.claude/agents/`
- [ ] **[truth-06]** No excluded skills copied: `show-trace/`, `generate-report/`, `orchestrator-protocol/` must NOT exist in `siopv/.claude/skills/`

---

## 6. Final Sign-Off Criteria

Stage 4.2 is **COMPLETE** when ALL of the following are true:

1. **File count:** `find /Users/bruno/siopv/.claude -type f | wc -l` = 41
2. **All wiring checks pass:** Section 3 — zero unchecked boxes
3. **All functional tests pass:** Section 4 — zero failures
4. **No regressions:** Section 5 — all 5 checks pass
5. **User-level fixes applied:** `~/.claude/CLAUDE.md` and `deterministic-execution-protocol.md` have zero `bypassPermissions` references
6. **MEMORY.md within limit:** `~/.claude/projects/-Users-bruno-sec-llm-workbench/memory/MEMORY.md` ≤ 185 lines
7. **SIOPV memory initialized:** `~/.claude/projects/-Users-bruno-siopv/memory/` has 5 files (MEMORY.md + 4 topic files)
8. **Human approval obtained:** Implementer presents consolidated summary to human; human explicitly approves before marking Stage 4.2 complete

**Sign-off command (run at completion):**
```bash
echo "=== Stage 4.2 Final Check ===" && \
  find /Users/bruno/siopv/.claude -type f | wc -l && \
  wc -l ~/.claude/projects/-Users-bruno-sec-llm-workbench/memory/MEMORY.md && \
  wc -l /Users/bruno/siopv/.claude/workflow/briefing.md && \
  grep -c "bypassPermissions" ~/.claude/CLAUDE.md ~/.claude/rules/deterministic-execution-protocol.md && \
  echo "DONE — present to human for approval"
```

Expected output: `41` file count, `≤185` MEMORY.md lines, `≤192` briefing.md lines, `0 0` bypassPermissions count.
