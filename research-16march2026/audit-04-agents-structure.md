# Audit 04 — `.claude/` Directory Structure & Agent Definitions

> **Date:** 2026-03-16
> **Auditor:** config-audit agent
> **Scope:** Project `.claude/` + global `~/.claude/` directories, all agent definitions, .gitignore coverage

---

## Executive Summary

The `.claude/` directory structure is **well-organized and largely compliant** with 2026 best practices. The project has 18 custom agent definitions — all with valid frontmatter and appropriate tool/permission configurations. Key issues found:

- **P0:** `.gitignore` is missing entries for `.claude/memory/`, `.claude/agent-memory/`, `.claude/agent-memory-local/`, and `.claude/CLAUDE.local.md`
- **P0:** `semantic-correctness-auditor.md` has conflicting `permissionMode: acceptEdits` + `disallowedTools: [Write, Edit]`
- **P1:** `research-cache/` directory is non-standard and tracked by git
- **P1:** 4 legacy handoff files tracked in git under `.claude/` (should be removed)
- **P1:** `docs/` subdirectory under `.claude/` is non-standard — canonical location is `.claude/rules/` for rules or project root `docs/` for documentation
- **P2:** Global researcher agents reference stale path (`sec-llm-workbench/.build/active-project`)
- **P2:** Missing canonical directories: `agent-memory/`, `agent-memory-local/`, `plans/`
- **P2:** `Notification` hook event in settings.json is not a documented event type

---

## 1. Directory Structure Findings

### Project-Level `.claude/` (at `/Users/bruno/siopv/.claude/`)

```
.claude/
├── CLAUDE.local.md          ✅ Correct (personal, should be gitignored)
├── settings.json            ✅ Correct (shared project settings)
├── settings.local.json      ✅ Correct (local overrides, gitignored)
├── agents/                  ✅ Correct (18 agent definitions)
├── skills/                  ✅ Correct (6 skills with SKILL.md)
├── rules/                   ✅ Correct (3 rule files)
├── hooks/                   ✅ Correct (7 hook scripts)
├── workflow/                ✅ Project-specific (acceptable)
├── docs/                    ⚠️ Non-standard — see finding below
└── research-cache/          ⚠️ Non-standard — see finding below
```

**Missing canonical directories:**

| Directory | Status | Impact |
|-----------|--------|--------|
| `agent-memory/` | Missing | No subagent memory persistence (project scope) — agents use `memory: project` but dir doesn't exist yet |
| `agent-memory-local/` | Missing | No local subagent memory |
| `plans/` | Missing | Plan mode files won't persist locally |

**Non-standard directories:**

| Directory | Issue | Recommendation |
|-----------|-------|----------------|
| `docs/` | Not part of canonical `.claude/` structure. Contains 5 reference docs (errors-to-rules.md, model-selection-strategy.md, etc.) | Move rule-like files to `rules/`, move reference docs to project `docs/` or keep as-is with a note |
| `research-cache/` | Contains `context7-cache.json`. Not a standard `.claude/` subdirectory | Move to `.build/cache/` or gitignore it |
| `workflow/` | Project-specific, not in canonical structure but well-used (briefing.md, compaction-log.md, 16 pre-compact briefs) | Acceptable — project-specific convention. Consider purging old pre-compact briefs (16 accumulated) |

### Global `~/.claude/`

```
~/.claude/
├── CLAUDE.md                ✅ Global instructions
├── agents/                  ✅ 3 researcher agents
├── rules/                   ✅ 2 rule files
├── projects/                ✅ Auto-generated per-project data
├── backups/                 ✅ System-managed
├── cache/                   ✅ System-managed
├── debug/                   ✅ System-managed
└── (no skills/)             ℹ️ No global skills defined (acceptable)
```

**No issues found** with global structure.

---

## 2. Agent Definition Findings

### Project Agents (18 files in `.claude/agents/`)

| Agent | name | description | model | permissionMode | memory | tools | disallowedTools | skills | Issues |
|-------|------|-------------|-------|----------------|--------|-------|-----------------|--------|--------|
| async-safety-auditor | ✅ | ✅ | sonnet | plan | project | ✅ | [Write, Edit] | — | None |
| best-practices-enforcer | ✅ | ✅ | sonnet | plan | project | ✅ + Context7 | [Write, Edit] | [coding-standards-2026] | None |
| circular-import-detector | ✅ | ✅ | sonnet | plan | project | ✅ | [Write, Edit] | — | None |
| code-implementer | ✅ | ✅ | sonnet | acceptEdits | project | ✅ + Context7 | — | [coding-standards-2026] | None |
| code-reviewer | ✅ | ✅ | sonnet | plan | project | ✅ | [Write, Edit] | — | None |
| config-validator | ✅ | ✅ | sonnet | plan | project | ✅ | [Write, Edit] | — | None |
| dependency-scanner | ✅ | ✅ | sonnet | plan | project | ✅ | — | — | Missing `disallowedTools` (read-only agent should deny Write/Edit) |
| hallucination-detector | ✅ | ✅ | sonnet | plan | project | ✅ + Context7 + Web | [Write, Edit] | — | None |
| hex-arch-remediator | ✅ | ✅ | sonnet | acceptEdits | project | ✅ (full write) | — | — | None |
| import-resolver | ✅ | ✅ | sonnet | plan | project | ✅ | [Write, Edit] | — | None |
| integration-tracer | ✅ | ✅ | sonnet | plan | project | ✅ | [Write, Edit] | — | None |
| phase7-builder | ✅ | ✅ | sonnet | acceptEdits | project | ✅ + Context7 | — | [coding-standards-2026, langraph-patterns, openfga-patterns] | None |
| phase8-builder | ✅ | ✅ | sonnet | acceptEdits | project | ✅ + Context7 | — | [coding-standards-2026] | None |
| security-auditor | ✅ | ✅ | sonnet | plan | project | ✅ + Web | [Write, Edit] | — | None |
| **semantic-correctness-auditor** | ✅ | ✅ | sonnet | **acceptEdits** | project | ✅ | **[Write, Edit]** | — | **P0: Conflicting config** |
| smoke-test-runner | ✅ | ✅ | sonnet | plan | project | ✅ | — | — | Missing `disallowedTools` for read-only role |
| test-generator | ✅ | ✅ | sonnet | acceptEdits | project | ✅ (Write, no Edit) | — | — | Missing `Edit` in tools list |
| xai-explainer | ✅ | ✅ | sonnet | acceptEdits | project | Read, Write, Bash | — | — | Missing `<!-- version -->` comment |

### Per-Agent Issues Detail

#### P0: `semantic-correctness-auditor.md` — Conflicting Configuration

```yaml
permissionMode: acceptEdits    # ← allows auto-accepting edits
disallowedTools: [Write, Edit] # ← but Write/Edit are denied
```

`acceptEdits` is meaningless when Write/Edit are disallowed. This should be `permissionMode: plan` (consistent with other read-only auditors).

#### P2: `dependency-scanner.md` and `smoke-test-runner.md` — Missing disallowedTools

Both are read-only auditing agents (`permissionMode: plan`) but don't explicitly deny Write/Edit. While `plan` mode restricts writes, adding `disallowedTools: [Write, Edit]` provides defense-in-depth (consistent with other auditor agents).

#### P2: `test-generator.md` — Missing `Edit` tool

Has `tools: Read, Write, Grep, Glob, Bash` but not `Edit`. A test generator likely needs to edit existing test files, not just create new ones.

#### P2: `xai-explainer.md` — Missing version comment

All other agents have `<!-- version: 2026-03 -->` at the top. This one doesn't.

### Global Agents (3 files in `~/.claude/agents/`)

| Agent | name | description | model | tools | Issues |
|-------|------|-------------|-------|-------|--------|
| researcher-1 | ✅ | ✅ | sonnet | ✅ + SendMessage | Stale path reference |
| researcher-2 | ✅ | ✅ | sonnet | ✅ + SendMessage | Stale path reference |
| researcher-3 | ✅ | ✅ | sonnet | ✅ + SendMessage | Stale path reference |

#### P2: All 3 researchers reference stale path

```markdown
Before any research, determine the active project:
1. Read `/Users/bruno/sec-llm-workbench/.build/active-project` if it exists
```

This references a different project (`sec-llm-workbench`). If that project doesn't exist or isn't active, the fallback works, but it's confusing and couples global agents to a specific project.

#### P2: Missing `memory` and `permissionMode` fields

None of the global researcher agents specify `memory` or `permissionMode`. Adding `memory: user` would enable cross-project research persistence.

---

## 3. `.gitignore` Findings

### Current `.gitignore` — Missing Entries

| Path | Currently gitignored? | Should be? | Risk |
|------|----------------------|------------|------|
| `.claude/memory/` | **NO** | YES | Machine-local auto-memory would be committed |
| `.claude/agent-memory/` | **NO** | YES | Subagent memory could leak to git |
| `.claude/agent-memory-local/` | **NO** | YES | Local-only subagent memory could leak |
| `.claude/CLAUDE.local.md` | **NO** | YES | Personal config would be committed |
| `.claude/settings.local.json` | ✅ YES | YES | Correctly ignored |
| `.claude/research-cache/` | **NO** | YES | Cache data shouldn't be in VCS |
| `.claude/workflow/pre-compact-brief-*` | **NO** | Consider | 16 accumulated brief files cluttering git |

### Tracked Legacy Files (should be removed)

These 4 files are tracked by git but deleted from working tree (visible as `D` in git status):

```
.claude/handoff-2026-02-09.md
.claude/handoff-2026-02-10.md
.claude/handoff-2026-02-10-session2.md
.claude/handoff-2026-02-10-session3.md
```

These should be permanently removed with `git rm --cached`.

---

## 4. `settings.json` Findings

### Validated Against Schema

| Setting | Value | Valid? | Notes |
|---------|-------|--------|-------|
| `$schema` | ✅ Set | ✅ | Correct schema URL |
| `includeGitInstructions` | `false` | ✅ | Intentional override |
| `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | `"70"` | ✅ | |
| `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | `"1"` | ✅ | Teams enabled |
| `attribution.commit` | `"none"` | ✅ | No AI attribution |
| `cleanupPeriodDays` | `30` | ✅ | Default |
| `statusLine` | command-based | ✅ | Custom SIOPV status |
| `sandbox` | Configured | ⚠️ | `sandbox.mode` is not a documented key — should be `sandbox.enabled` |
| `permissions.deny/ask/allow` | Configured | ✅ | Well-structured permission rules |
| `hooks.Notification` | Configured | ⚠️ | **Not a documented hook event** |

#### P2: `hooks.Notification` — Undocumented Event

The `Notification` hook event is not in the official documentation. It may be silently ignored. If observability logging is the goal, `SubagentStop` or `TaskCompleted` are the documented equivalents.

#### P2: `sandbox.mode` — Possibly Invalid Key

`sandbox.mode: "auto-allow"` doesn't appear in the schema. The documented key is `sandbox.enabled: true` with `sandbox.autoAllowBashIfSandboxed: true`.

---

## 5. Prioritized Fix List

### P0 — Must Fix (breaks correctness or security)

| # | Finding | Fix |
|---|---------|-----|
| 1 | `.gitignore` missing `.claude/memory/`, `.claude/agent-memory/`, `.claude/agent-memory-local/`, `.claude/CLAUDE.local.md` | Add all 4 entries to `.gitignore` |
| 2 | `semantic-correctness-auditor.md` conflicting `acceptEdits` + `disallowedTools: [Write, Edit]` | Change to `permissionMode: plan` |

### P1 — Should Fix (non-standard, potential issues)

| # | Finding | Fix |
|---|---------|-----|
| 3 | `.claude/research-cache/` is non-standard and not gitignored | Add `.claude/research-cache/` to `.gitignore`, or move to `.build/cache/` |
| 4 | 4 legacy handoff files tracked in git under `.claude/` | `git rm --cached .claude/handoff-*.md` |
| 5 | 16 accumulated `pre-compact-brief-*` files in `workflow/` | Purge old briefs, keep only latest; consider gitignoring `workflow/pre-compact-brief-*` |
| 6 | `.claude/docs/` is non-standard location | Consider migrating to `.claude/rules/` (for rule-like docs) or project `docs/` |

### P2 — Nice to Have (consistency, hygiene)

| # | Finding | Fix |
|---|---------|-----|
| 7 | `dependency-scanner.md` and `smoke-test-runner.md` missing `disallowedTools` | Add `disallowedTools: [Write, Edit]` for defense-in-depth |
| 8 | `test-generator.md` missing `Edit` tool | Add `Edit` to tools list |
| 9 | `xai-explainer.md` missing `<!-- version -->` comment | Add `<!-- version: 2026-03 -->` |
| 10 | Global researchers reference stale `sec-llm-workbench` path | Update to use `$CLAUDE_PROJECT_DIR` or remove the lookup |
| 11 | Global researchers missing `memory: user` and `permissionMode` | Add both fields |
| 12 | `hooks.Notification` may be undocumented | Verify or remove |
| 13 | `sandbox.mode` possibly invalid key | Verify against current schema or switch to `sandbox.enabled` |
| 14 | Missing `agent-memory/`, `agent-memory-local/`, `plans/` directories | Create with `.gitkeep` where appropriate |

---

## Appendix: Agent Frontmatter Summary

All 18 project agents use:
- **model:** `sonnet` (consistent, cost-effective)
- **memory:** `project` (consistent)
- **Valid `name` format:** lowercase + hyphens (all pass)
- **`description` length:** All under 1024 chars (all pass)
- **No `maxTurns`:** None set (agents run until done — acceptable for verification workflows)
- **No `hooks`:** No agent-scoped hooks (all use global hooks — acceptable)
- **No `isolation`:** None use worktree isolation (appropriate — these are auditors, not parallel implementers)
- **No `background`:** None force background mode (appropriate — invocation controls this)

### Permission Mode Distribution

| Mode | Agents | Role |
|------|--------|------|
| `plan` (read-only) | 11 | Auditors/verifiers |
| `acceptEdits` | 7 | Implementers/generators |

This is a healthy split — auditors can't write, implementers can.
