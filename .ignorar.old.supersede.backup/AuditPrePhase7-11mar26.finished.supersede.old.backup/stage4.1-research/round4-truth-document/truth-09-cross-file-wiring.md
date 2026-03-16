# Truth-09: Cross-File Dependency and Wiring Verification
**Generated:** 2026-03-13
**Authority:** All truth files (truth-00 through truth-11)
**Scope:** Cross-file reference consistency — hooks↔settings, skills↔agents, CLAUDE.md↔files

---

## 1. Reference Graph

```
settings.json (truth-01)
  → hooks/session-start.sh         (SessionStart: startup/resume)
  → hooks/pre-write.sh             (PreToolUse: Write|Edit)
  → hooks/pre-git-commit.sh        (PreToolUse: Bash)
  → hooks/post-code.sh             (PostToolUse: Write|Edit)
  → hooks/coverage-gate.sh         (PostToolUse: Bash)
  → hooks/pre-compact.sh           (PreCompact)
  → hooks/session-end.sh           (SessionEnd)
  → .build/current-phase           (statusLine command)
  → .build/checkpoints/pending/    (statusLine + Stop hook)
  → .build/checkpoints/daily/      (SessionStart inline hook)
  → .build/logs/agents/            (PostToolUseFailure, SubagentStart/Stop, Notification)
  → .build/logs/sessions/          (SessionEnd inline hook)
  → .build/current-session-id      (Notification hook)

CLAUDE.md (truth-02) — @ imports (loaded every session)
  → .claude/workflow/briefing.md         (truth-11)
  → .claude/workflow/compaction-log.md   (truth-11)

CLAUDE.md (truth-02) — on-demand references
  → .claude/docs/siopv-phase7-8-context.md   (truth-05)
  → .claude/docs/verification-thresholds.md  (truth-05)
  → .claude/docs/model-selection-strategy.md (truth-05)
  → .claude/docs/python-standards.md         (truth-05)
  → .claude/docs/errors-to-rules.md          (truth-05)
  → .claude/rules/tech-stack.md              (truth-05)
  → .claude/rules/agent-reports.md           (truth-05)

CLAUDE.md (truth-02) — skill invocations
  → skills/verify/SKILL.md              (truth-06)
  → skills/siopv-remediate/SKILL.md     (truth-06)
  → skills/coding-standards-2026/SKILL.md (truth-06)
  → skills/langraph-patterns/SKILL.md   (truth-06)
  → skills/openfga-patterns/SKILL.md    (truth-06)
  → skills/presidio-dlp/SKILL.md        (truth-06)

hooks/session-start.sh (truth-11)
  → workflow/briefing.md         (cats to stdout)
  → workflow/compaction-log.md   (tail -5 to stdout)
  → /tmp/siopv-session-start-*.lock (idempotency guard)

hooks/session-end.sh (truth-11)
  → workflow/briefing.md         (updates > Last updated: timestamp)
  → workflow/compaction-log.md   (appends SessionEnd event)

hooks/pre-compact.sh (truth-11)
  → workflow/briefing.md         (updates > Last updated: timestamp)
  → workflow/compaction-log.md   (appends PreCompact event)
  → ~/.claude/projects/*/*.jsonl (bug #13668 fallback)

hooks/post-code.sh (truth-01)
  → pyproject.toml               (must exist in SIOPV root)
  → .build/checkpoints/pending/  (writes pending markers)

hooks/coverage-gate.sh (truth-01)
  → .build/checkpoints/pending/  (writes coverage-below-threshold marker)
  → docs/verification-thresholds.md (coverage floor = 83%)

hooks/pre-git-commit.sh (truth-01)
  → .build/checkpoints/pending/  (reads markers to block commit)

skills/verify/SKILL.md (truth-06)
  → agents/best-practices-enforcer.md    (Wave 1)
  → agents/security-auditor.md          (Wave 1)
  → agents/hallucination-detector.md    (Wave 1)
  → agents/code-reviewer.md             (Wave 2)
  → agents/test-generator.md            (Wave 2)
  → agents/async-safety-auditor.md      (Wave 3)
  → agents/semantic-correctness-auditor.md (Wave 3)
  → agents/integration-tracer.md        (Wave 3)
  → agents/smoke-test-runner.md         (Wave 4)
  → agents/config-validator.md          (Wave 4)
  → agents/dependency-scanner.md        (Wave 4)
  → agents/circular-import-detector.md  (Wave 5)
  → agents/import-resolver.md           (Wave 5)
  → agents/hex-arch-remediator.md       (Wave 3 per truth-06 — CONFLICT: truth-03 says on-demand)
  → .build/checkpoints/pending/         (clears markers on PASS)
  → /Users/bruno/siopv                  (TARGET path — replaces .build/active-project)

skills/siopv-remediate/SKILL.md (truth-06)
  → agents/hex-arch-remediator.md
  → .claude/workflow/03-human-checkpoints.md  (⚠️ DOES NOT EXIST — see §6 Conflict #4)

agents/code-implementer.md (truth-03)
  → docs/siopv-phase7-8-context.md      (required reading before Phase 7/8)

agents/phase7-builder.md (truth-03)
  → docs/siopv-phase7-8-context.md
  → mcp__context7__resolve-library-id (tool dependency)
  → mcp__context7__query-docs         (tool dependency)

agents/phase8-builder.md (truth-03)
  → docs/siopv-phase7-8-context.md
  → mcp__context7__resolve-library-id (tool dependency)
  → mcp__context7__query-docs         (tool dependency)

rules/tech-stack.md (truth-05)
  [Removed reference to] docs/mcp-setup.md (ADAPT: meta-only ref removed)

workflow/briefing.md (truth-11)
  → hooks/session-start.sh   (consumed — injected at session start)
  → hooks/session-end.sh     (written — timestamp updated)
  → hooks/pre-compact.sh     (written — timestamp updated)

workflow/compaction-log.md (truth-11)
  → hooks/session-start.sh   (consumed — last 5 lines injected)
  → hooks/session-end.sh     (written — events appended)
  → hooks/pre-compact.sh     (written — events appended)
```

---

## 2. Hook Wiring Verification

| Hook Type | Matcher | Script Path | Script Exists (truth-01)? | Referenced by truth-11? |
|-----------|---------|-------------|--------------------------|------------------------|
| SessionStart | startup/resume (no matcher) | `$CLAUDE_PROJECT_DIR/.claude/hooks/session-start.sh` | ✅ §2a | ✅ §4 |
| SessionStart | `compact` | inline echo (no script) | N/A — inline | ✅ (§1 bug workaround note) |
| SessionStart | daily | inline check (no script) | N/A — inline | ✅ |
| PreToolUse | `Write\|Edit` | `$CLAUDE_PROJECT_DIR/.claude/hooks/pre-write.sh` | ✅ §2f | ❌ not in truth-11 scope |
| PreToolUse | `Bash` | `$CLAUDE_PROJECT_DIR/.claude/hooks/pre-git-commit.sh` | ✅ §2e | ❌ not in truth-11 scope |
| PostToolUse | `Write\|Edit` | `$CLAUDE_PROJECT_DIR/.claude/hooks/post-code.sh` | ✅ §2d | ❌ not in truth-11 scope |
| PostToolUse | `Bash` | `$CLAUDE_PROJECT_DIR/.claude/hooks/coverage-gate.sh` | ✅ §2g | ❌ not in truth-11 scope |
| PreCompact | none | `$CLAUDE_PROJECT_DIR/.claude/hooks/pre-compact.sh` | ✅ §2c | ✅ §4 — ⚠️ `async: true` discrepancy (§6 Conflict #2) |
| SessionEnd | none | `$CLAUDE_PROJECT_DIR/.claude/hooks/session-end.sh` | ✅ §2b | ✅ §4 |
| Stop | none | inline pending check | N/A — inline | ❌ not in truth-11 scope |
| PostToolUseFailure | `Write\|Edit` | inline JSONL log | N/A — inline | ❌ not in scope |
| SubagentStart | none | inline JSONL log | N/A — inline | ❌ not in scope |
| SubagentStop | none | inline JSONL log | N/A — inline | ❌ not in scope |
| Notification | none | inline JSONL log | N/A — inline | ❌ not in scope |

**Verdict:** All 7 hook scripts are registered in settings.json and specified in truth-01. ✅

---

## 3. Agent Wiring Verification

| Agent | Model (truth-03) | Mode (truth-03) | In settings.json? | In /verify? | In CLAUDE.md? |
|-------|-----------------|-----------------|-------------------|-------------|---------------|
| best-practices-enforcer | sonnet | plan | ❌ (agents not in settings.json — correct) | ✅ Wave 1 | ❌ not listed individually |
| security-auditor | sonnet | plan | ❌ | ✅ Wave 1 | ❌ |
| hallucination-detector | sonnet | plan | ❌ | ✅ Wave 1 | ❌ |
| code-reviewer | sonnet | plan | ❌ | ✅ Wave 2 | ❌ |
| test-generator | sonnet | acceptEdits | ❌ | ✅ Wave 2 | ❌ |
| async-safety-auditor | sonnet | plan | ❌ | ✅ Wave 3 | ❌ |
| semantic-correctness-auditor | sonnet | plan | ❌ | ✅ Wave 3 | ❌ |
| integration-tracer | sonnet | plan | ❌ | ✅ Wave 3 | ❌ |
| smoke-test-runner | sonnet | plan | ❌ | ✅ Wave 4 | ❌ |
| config-validator | sonnet | plan | ❌ | ✅ Wave 4 | ❌ |
| dependency-scanner | sonnet | plan | ❌ | ✅ Wave 4 | ❌ |
| circular-import-detector | sonnet | plan | ❌ | ✅ Wave 5 | ❌ |
| import-resolver | sonnet | plan | ❌ | ✅ Wave 5 | ❌ |
| code-implementer | sonnet | acceptEdits | ❌ | ❌ on-demand | ❌ |
| xai-explainer | sonnet | acceptEdits | ❌ | ❌ on-demand | ❌ |
| hex-arch-remediator | sonnet | acceptEdits | ❌ | ⚠️ CONFLICT (§6 Conflict #1) | via `/siopv-remediate` |
| phase7-builder | sonnet | acceptEdits | ❌ | ❌ on-demand | ❌ |
| phase8-builder | sonnet | acceptEdits | ❌ | ❌ on-demand | ❌ |

Note: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json env enables multi-agent execution. All agents use sonnet — consistent with `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` requirement. ✅

---

## 4. Skill Wiring Verification

| Skill | Trigger Pattern | Conflicts with other skills? | Referenced in CLAUDE.md? |
|-------|-----------------|------------------------------|--------------------------|
| `verify` | `/verify [--fix]` | No conflict | ✅ rule 7 + Skills table |
| `langraph-patterns` | `langgraph` import or LangGraph questions | No conflict | ✅ Skills table |
| `openfga-patterns` | `openfga_sdk` import or ReBAC questions | No conflict | ✅ Skills table |
| `presidio-dlp` | `presidio_analyzer`/`presidio_anonymizer` imports | No conflict | ✅ Skills table |
| `coding-standards-2026` | Python code with type hints, Pydantic v2, httpx, structlog | No conflict | ✅ Skills table |
| `siopv-remediate` | `/siopv-remediate` explicit invocation only | No conflict | ✅ Phase 7 Gating Conditions |

All 6 skills are `disable-model-invocation: true` (user-only). Skill discovery is automatic (file-based) — no settings.json registration needed per truth-06 §6. ✅

---

## 5. Path Consistency Check

### Hook paths: `$CLAUDE_PROJECT_DIR` vs hardcoded
- **truth-01** (settings.json): Uses `"$CLAUDE_PROJECT_DIR"/.claude/hooks/*.sh` — portable ✅
- **truth-01** (ADAPT spec): Specifies change FROM hardcoded `sec-llm-workbench` TO `${CLAUDE_PROJECT_DIR}` variable
- **truth-11** (hook scripts): Uses hardcoded `/Users/bruno/siopv/.claude/workflow/` paths internally
- **Verdict:** settings.json uses portable variable ✅. Hook script internals use hardcoded paths — intentional (truth-11 documents this as the ADAPT for single-project use). No conflict with settings.json paths.

### SIOPV paths (not meta-project paths)
- truth-01: All hook commands use `$CLAUDE_PROJECT_DIR` — no meta-project paths ✅
- truth-03: All agent Project Context blocks hardcoded to `/Users/bruno/siopv/` ✅
- truth-06: verify skill replaces `.build/active-project` with `TARGET="/Users/bruno/siopv"` ✅
- truth-11: Hook scripts use `/Users/bruno/siopv/` throughout ✅
- truth-08: researcher agents fall back to `/Users/bruno/siopv/` when `.build/active-project` missing ✅

### briefing.md path consistency
- truth-11 specifies: `/Users/bruno/siopv/.claude/workflow/briefing.md` ✅
- truth-01 §2a says adapt to: `${CLAUDE_PROJECT_DIR}/.claude/workflow/briefing.md` ✅ (resolves to same)
- truth-02 @-imports: `@.claude/workflow/briefing.md` ✅
- truth-00: lists `workflow/briefing.md` ✅
- Briefing.md §6 internal references: `/Users/bruno/siopv/.claude/hooks/` ✅

### truth-00 directory structure vs truth file assignments
- All 41 files in truth-00 map to exactly one truth file — no file assigned twice ✅
- truth-04 is deliberately empty (reserved but no files) ✅
- No meta-project files included in SIOPV structure ✅

---

## 6. Conflicts and Inconsistencies Found

### Conflict #1 — CRITICAL: hex-arch-remediator placement contradicts between truth-03 and truth-06

**Truth files:** truth-03 §5 vs truth-06 §2
**Conflict:**
- truth-03 §5: "On-demand only: xai-explainer, code-implementer, hex-arch-remediator, phase7-builder, phase8-builder" — explicitly NOT in /verify
- truth-06 §2: "Add `hex-arch-remediator` as Wave 3 verification agent" — explicitly IN /verify

**Also note:** truth-03 §5 header says `/verify Skill Agent List (15 agents)` but the wave list totals only 13 (3+2+3+3+2). The count is internally inconsistent.

**Recommended resolution:** truth-06 (the verify skill truth) is the authoritative source for /verify content. Include hex-arch-remediator in Wave 3 of /verify as a compliance checker (verify-only mode, not fix mode). truth-03 on-demand list should remove hex-arch-remediator. Total in /verify = 14 (13 wave agents + hex-arch-remediator). The "15" in CLAUDE.md may be wrong — check against final verify/SKILL.md agent count.

---

### Conflict #2 — HIGH: `async: true` missing from pre-compact.sh registration

**Truth files:** truth-01 §1 (settings.json spec) vs truth-11 §4 (pre-compact note)
**Conflict:**
- truth-01 settings.json PreCompact spec: No `async: true` on pre-compact.sh hook entry
- truth-11 §4: "settings.json registration for pre-compact.sh: `async: true` — does not block compaction"

**Why it matters:** pre-compact.sh spawns `claude -p` for transcript summary (background process). Without `async: true`, the hook blocks compaction until the `claude -p` call completes — which could be 30+ seconds.

**Recommended resolution:** Add `"async": true` to the pre-compact.sh hook entry in settings.json truth-01. The inline echo hook entry before it (which has no script file) should remain synchronous.

---

### Conflict #3 — HIGH: Compact Instructions block differs between truth-02 and truth-11

**Truth files:** truth-02 §1 (CLAUDE.md content) vs truth-11 §5 (Compact Instructions block)
**Conflict:** Both specify the `## Compact Instructions` block for `siopv/CLAUDE.md` with different content:
- truth-02 (6 bullets): phase, gating conditions, violations, pending files, decisions, coverage baseline
- truth-11 (7 bullets + update instructions): phase+status, NEXT IMMEDIATE ACTION, key file paths, phase table, metrics, violations, project path; plus "update briefing.md when task completes"

**Why it matters:** Both documents will be used to write CLAUDE.md. The block can only appear once.

**Recommended resolution:** Use truth-11's version — it is the ONLY reliable post-compaction mechanism (bug #15174 workaround). truth-11 is explicitly authoritative for compaction behavior. truth-02 should defer to truth-11 for this specific block.

---

### Conflict #4 — MEDIUM: siopv-remediate skill references non-existent file

**Truth files:** truth-06 §3 (siopv-remediate/SKILL.md) vs truth-04 (no workflow/*.md files beyond briefing/compaction-log)
**Conflict:** siopv-remediate/SKILL.md Checkpoint section reads:
> "per `.claude/workflow/03-human-checkpoints.md` — multi-module change >3 modules"

truth-04 explicitly states: The numbered workflow guides (01–07) are NOT copied to SIOPV. `03-human-checkpoints.md` does not exist in SIOPV. truth-00 §4 lists it under excluded META-ONLY items.

**Recommended resolution:** Replace the reference with the equivalent rule from CLAUDE.md (truth-02 rules 9–10): "per CLAUDE.md rules 9–10 — pause for human approval on changes affecting >3 modules."

---

### Conflict #5 — LOW: Agent count claims (15) not supported by wave lists

**Truth files:** truth-03 §5, truth-06 §2, truth-02 rule 7, CLAUDE.md Skills table
**Conflict:**
- CLAUDE.md says "15 verification agents"
- truth-06 description update says "15 agents (Wave 1+2+3)"
- Actual wave count in truth-03: 13 mandatory wave agents + hex-arch-remediator (contested) = 14
- The "Wave 3" in truth-06 appears to collapse what truth-03 calls Waves 3+4+5 (8 agents), then adds hex-arch-remediator = 9, giving total 3+2+9=14, not 15.

**Recommended resolution:** Reconcile after resolving Conflict #1. If hex-arch-remediator goes into /verify, final count is 14. Update CLAUDE.md rule 7 and verify/SKILL.md description from "15" to "14". Alternatively, confirm the correct total by counting truth-03's wave lists explicitly after conflict #1 is resolved.

---

## 7. Implementation Dependencies

Based on the reference graph, Stage 4.2 creation order must follow:

```
BATCH 1 — No dependencies (foundation)
  workflow/briefing.md              ← needed by session-start.sh, session-end.sh, pre-compact.sh
  workflow/compaction-log.md        ← needed by same 3 hooks
  docs/siopv-phase7-8-context.md   ← needed by code-implementer, phase7-builder, phase8-builder

BATCH 2 — Depends on BATCH 1 paths being known
  settings.json                    ← registers all 7 hook paths (MUST add async:true to pre-compact)
  settings.local.json
  hooks/session-start.sh           ← reads briefing.md + compaction-log.md
  hooks/session-end.sh             ← writes briefing.md + compaction-log.md
  hooks/pre-compact.sh             ← writes both; must match settings.json async:true
  hooks/post-code.sh
  hooks/pre-git-commit.sh          ← reads .build/checkpoints/pending/
  hooks/pre-write.sh
  hooks/coverage-gate.sh           ← writes .build/checkpoints/pending/

BATCH 3 — Depends on knowing which files exist and which skills are final
  CLAUDE.md                        ← @-imports briefing.md, compaction-log.md (must exist)
                                     Compact Instructions block: use truth-11 version (not truth-02)

BATCH 4 — Rules and docs (no inter-dependencies)
  rules/agent-reports.md
  rules/placeholder-conventions.md
  rules/tech-stack.md              ← remove mcp-setup.md reference
  docs/verification-thresholds.md
  docs/model-selection-strategy.md
  docs/python-standards.md
  docs/errors-to-rules.md

BATCH 5 — Skills (must resolve Conflict #1 before writing verify/SKILL.md)
  skills/langraph-patterns/SKILL.md
  skills/openfga-patterns/SKILL.md
  skills/presidio-dlp/SKILL.md
  skills/coding-standards-2026/SKILL.md
  skills/verify/SKILL.md           ← Resolve Conflict #1 (hex-arch-remediator in/out of /verify)
  skills/siopv-remediate/SKILL.md  ← Fix Conflict #4 (remove 03-human-checkpoints.md reference)

BATCH 6 — Agents (depend on docs context existing)
  code-implementer.md (reads docs/siopv-phase7-8-context.md)
  [all other ADAPT agents]
  hex-arch-remediator.md [NEW]
  phase7-builder.md [NEW]    (reads docs/siopv-phase7-8-context.md)
  phase8-builder.md [NEW]    (reads docs/siopv-phase7-8-context.md)

BATCH 7 — User-level and memory (external to siopv/.claude/)
  ~/.claude/CLAUDE.md           (fix bypassPermissions → acceptEdits)
  ~/.claude/settings.json       (add attribution block)
  ~/.claude/rules/deterministic-execution-protocol.md (fix bypassPermissions)
  ~/.claude/agents/researcher-{1,2,3}.md (create with Project Context block)
  memory/MEMORY.md              (trim to <200 lines)
  memory/siopv-hooks-stage4.md  (create topic file)

BATCH 8 — Verification
  Run truth-10 acceptance checklist
```

---

**Conflicts summary:** 5 conflicts found across truth files.
- Conflict #1 CRITICAL (resolve before writing verify/SKILL.md)
- Conflict #2 HIGH (fix in settings.json spec)
- Conflict #3 HIGH (resolve before writing CLAUDE.md)
- Conflict #4 MEDIUM (fix in siopv-remediate/SKILL.md)
- Conflict #5 LOW (follow-on from Conflict #1 resolution)
