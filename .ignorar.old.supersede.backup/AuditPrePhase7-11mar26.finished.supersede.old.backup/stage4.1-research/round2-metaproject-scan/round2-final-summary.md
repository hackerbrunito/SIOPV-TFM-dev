# Round 2 — Consolidated Summary: Claude Code Configuration Inventory
**Generated:** 2026-03-13
**Sources:** r2-metaproject-scanner.md + r2-user-level-scanner.md
**Scope:** `/Users/bruno/sec-llm-workbench/.claude/` + `/Users/bruno/.claude/`

---

## 1. Meta-Project Configuration (`/Users/bruno/sec-llm-workbench/.claude/`)

### Directory Tree (concise)
```
sec-llm-workbench/.claude/
├── CLAUDE.local.md          ← local preferences (not committed)
├── settings.json            ← primary config (284 lines)
├── settings.json.back       ← backup (legacy)
├── git-workflow.md
├── agents/    (23 files)    ← all verification + implementation agents
├── docs/      (8 files)     ← verification-thresholds, model-selection, python-standards, etc.
├── handoffs/  (9 files)     ← session handoff briefs (dated)
├── hooks/     (9 files)     ← 6 active + 3 legacy/unregistered
├── rules/     (3 files)     ← tech-stack, agent-reports, placeholder-conventions
├── scripts/   (12 files)    ← cost, coverage, MCP health, git secret scan, etc.
├── skills/    (17 skills)   ← /verify, langraph-patterns, openfga-patterns, etc.
├── workflow/  (12 files)    ← 01-session-start through 07-orchestrator-invocation + briefs
└── .ignorar/monitoring/     ← context7 status + alerts JSON
```

### Agent Inventory (23 total)
| Category | Count | Model | PermissionMode |
|----------|-------|-------|----------------|
| Wave 1 verification (best-practices, security-auditor, hallucination-detector) | 3 | sonnet | plan (read-only) |
| Wave 2 verification (code-reviewer, test-generator, integration-tracer, async-safety-auditor, semantic-correctness-auditor, smoke-test-runner, config-validator, regression-guard) | 8 | sonnet | plan or default |
| Wave 3 verification (dependency-scanner, circular-import-detector, import-resolver) | 3 | sonnet | plan or default |
| Meta/utility (final-report-agent, report-summarizer, static-checks-agent) | 3 | haiku | — |
| Code writers (code-implementer, test-generator, xai-explainer) | 3 | sonnet | acceptEdits |
| On-demand researchers (researcher-1/2/3, vulnerability-researcher) | 4 | sonnet | — or plan |
| **Total** | **23** | | |

**Naming pattern:** `{role}-{domain}.md` (e.g., `async-safety-auditor.md`, `code-implementer.md`)
**Common pattern:** Every agent except researcher-1/2/3 has a `## Project Context (CRITICAL)` block. All agents read `.build/active-project` to find the target project path.

### Hook System (9 hooks, 6 active)
| Hook | Trigger | Registered | Purpose |
|------|---------|------------|---------|
| `session-start.sh` | SessionStart | ✅ Yes (2 entries) | Injects briefing.md + last 5 lines of compaction-log.md |
| `session-end.sh` | SessionEnd | ✅ Yes | Updates briefing.md timestamp; appends to compaction-log.md |
| `pre-compact.sh` | PreCompact | ✅ Yes (2 entries) | Prints context preservation inline + updates compaction-log.md |
| `post-code.sh` | PostToolUse (Write/Edit) | ✅ Yes | Runs ruff format + ruff check --fix; creates `.build/checkpoints/pending/` marker |
| `pre-git-commit.sh` | PreToolUse (Bash git commit) | ✅ Yes | BLOCKS commit if pending markers exist OR code-reviewer score < 9.0 |
| `pre-write.sh` | PreToolUse (Write/Edit) | ✅ Yes | Checks daily checkpoints; injects reminder if missing (asks, does not block) |
| `pre-commit.sh` | — | ❌ Not registered | Legacy — unregistered, possibly orphaned |
| `test-framework.sh` | — | ❌ Not registered | Legacy — unregistered |
| `verify-best-practices.sh` | — | ❌ Not registered | Legacy — unregistered |

**Checkpoint gate mechanism:** `post-code.sh` creates JSON marker in `.build/checkpoints/pending/` for every Python file written. `pre-git-commit.sh` reads this directory and calls `check-reviewer-score.sh` against reports — blocks commit until both conditions clear. `/verify` skill is the only mechanism that clears markers.

### Workflow Files (12)
| File | Auto-loaded | Purpose |
|------|-------------|---------|
| `01-session-start.md` | Yes (@ in CLAUDE.md) | Session state machine (NO_EXISTE → COMPLETADO) |
| `02-reflexion-loop.md` | On-demand | Reflection loop for code quality |
| `03-human-checkpoints.md` | Yes (@ in CLAUDE.md) | 3 mandatory human pause points + flow diagram |
| `04-agents.md` | On-demand | Agent invocation table, waves, consultation order |
| `05-before-commit.md` | Yes (@ in CLAUDE.md) | Commit checklist; /verify behavior |
| `06-decisions.md` | On-demand | Auto-decision rules |
| `07-orchestrator-invocation.md` | On-demand (skill) | Orchestrator → code-implementer delegation |
| `briefing.md` | Via session-start.sh | Master SIOPV session briefing (auto-injected) |
| `compaction-log.md` | Via session-start.sh | Auto-maintained compaction event log |
| `orchestrator-briefing.md` | Manual | Orchestrator-specific briefing |
| `setup-checklist.md` | Manual | Project setup checklist |
| `spec-findings.md` | Manual | Specification findings tracker |

### Rules and Docs
- **Rules:** `tech-stack.md` (Python 3.11+/uv/Pydantic v2/httpx/structlog), `agent-reports.md` (timestamp UUID naming, wave timing, report paths), `placeholder-conventions.md` (syntax standards)
- **Docs:** `verification-thresholds.md` (15 pass/fail criteria), `model-selection-strategy.md` (hierarchical routing), `python-standards.md`, `agent-tool-schemas.md`, `techniques.md`, `mcp-setup.md`, `traceability.md`, `errors-to-rules.md` (project-specific)

### settings.json Key Values
- `includeGitInstructions: false` — suppresses default git instructions
- `attribution.commit: "none"` — no Co-Authored-By in commits
- `cleanupPeriodDays: 30`
- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: "70"` — compact at 70% context
- `ENABLE_TOOL_SEARCH: "auto:5"` — deferred tool search, max 5 results
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"` — enables TeamCreate
- Sandbox: `auto-allow`; writes blocked for `.env*`, `*.pem`, `*.key`, `credentials.json`
- Network allowed: pypi.org, api.github.com, api.anthropic.com, docs.pydantic.dev, structlog, typer, anthropic/claude docs
- Deny: `rm -rf /`, `rm -rf ~`, `sudo:*`, `git push --force`, `git reset --hard`, Read/Edit `.env*` / `credentials*`
- Ask: `git push`, `rm`, `docker`, `docker-compose`
- Allow: `uv`, `ruff`, `mypy`, `pytest`, `git` (add/commit/status/diff/log/worktree), `ls`, `cat`, `grep`, `find`, `jq`, `date`, `tree`, `touch`, `mkdir`, `chmod`, `env`, `echo`, `pwd`, `whoami`, `wc`, `md5`

### CLAUDE.md (project root) Structure
5 sections: CRITICAL RULES (7 mandates) → References on-demand (3 workflow files) → On-Demand References (6 skills/docs) → Compact Instructions (5 preserve items). Auto-loads 3 `@` refs: `01-session-start.md`, `05-before-commit.md`, `03-human-checkpoints.md`. Deliberately minimal auto-loads to avoid context bloat.

---

## 2. User-Level Configuration (`/Users/bruno/.claude/`)

### Directory Tree (concise)
```
/Users/bruno/.claude/
├── CLAUDE.md                    ← global instructions (58 lines)
├── settings.json                ← global permissions + env + model (83 lines)
├── settings.local.json          ← local hooks extension (23 lines)
├── history.jsonl
├── stats-cache.json
├── rules/
│   ├── errors-to-rules.md       ← 10 cross-project error rules (118 lines)
│   └── deterministic-execution-protocol.md  ← TeamCreate formal spec (67 lines)
├── hooks/
│   └── user-prompt-submit.sh    ← fires before EVERY prompt (26 lines)
├── docs/
│   ├── team-management-best-practices.md    ← hub-and-spoke team guide (~200 lines)
│   └── 2026-02-12-1017-openfga-authentication-.../ (plan dir)
├── plans/                       ← 3 random-name plan files
├── plugins/
│   └── marketplaces/claude-plugins-official/
│       ├── external_plugins/    ← context7, github, gitlab, linear, asana, slack, stripe, etc.
│       └── plugins/             ← commit-commands, feature-dev, pr-review-toolkit, hookify, etc.
├── projects/
│   └── -Users-bruno-sec-llm-workbench/     ← ACTIVE PROJECT
│       ├── sessions-index.json
│       └── memory/
│           ├── MEMORY.md        ← 217 lines (⚠ OVER 200-line limit)
│           └── siopv-audit-2026-03-05.md    ← 129 lines
└── [runtime dirs: todos, teams, tasks, telemetry, statsig, cache, debug, ide, backups, etc.]
```

### Global CLAUDE.md Key Behavioral Rules
1. Read `errors-to-rules.md` before every task (@ import)
2. Language: Spanish or English both accepted
3. Be direct and concise; no confirmation on standard tasks
4. **TeamCreate is the ONLY default execution mode** — mandatory announcement before every task
5. Override requires explicit typed phrase: "Use a subagent" / "Use a task/subtask" / "Do it yourself"
6. Orchestrator spawn protocol: TeamCreate → Agent(team_name, mode=bypassPermissions) → name self "claude-main" → wait

### Global settings.json Key Values
- `model: "sonnet"` (default)
- `autoUpdatesChannel: "latest"`
- `skipDangerousModePermissionPrompt: true`
- `teammateMode: "tmux"`
- `permissions.defaultMode: "default"`
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"`
- Allow: uv, ruff, mypy, pytest, git (add/commit/status/diff/log/worktree/check-ignore/init/branch), ls, cat, grep, find, env, echo, touch, jq, wc, md5, chmod, mkdir, whoami, pwd, tree, date, python3, bash -n, brew install, du, pre-commit, Read/Write/Edit `/Users/bruno/**`, WebSearch, specific WebFetch domains, mcp__pencil, mcp__context7__resolve-library-id
- Deny: rm -rf /, rm -rf ~, sudo, git push --force, git reset --hard, Read/Edit `.env*` / `credentials*`
- Ask: git push, rm, docker, docker-compose

### Rules
- **`errors-to-rules.md`** (10 rules, cross-project): missed grep audit, wrong file naming, Co-Authored-By in public commit, bypassed verification, no git init, hardcoded credentials, committed .claude/ to public repo, stale training data, modified wave plan without reading, bypassPermissions trap, TeamCreate announced but not called
- **`deterministic-execution-protocol.md`**: Formal spec of TeamCreate default. Defines exact announcement text, 3 override phrases, 4-step orchestrator spawn. Context protection rationale.

### Memory System
- **Active project memory:** `memory/MEMORY.md` (217 lines, ⚠ OVER 200-line limit — lines 201–217 silently truncated = Hook Classification section drops)
- **Topic file:** `siopv-audit-2026-03-05.md` (4 CRITICAL, 5 HIGH findings from pre-Stage audit)
- **Historical projects:** 10+ other project directories exist but have no memory/ files (session archives only)

### Plugins/Extensions
- **External plugins:** context7, github, gitlab, linear, asana, slack, stripe, supabase, firebase, greptile, playwright, laravel-boost, serena (13 total)
- **Internal plugins:** commit-commands (/commit, /commit-push-pr), code-review, feature-dev, pr-review-toolkit, hookify, ralph-loop, claude-code-setup, claude-md-management, agent-sdk-dev, 15+ LSP plugins (pyright, rust-analyzer, gopls, typescript, etc.)

---

## 3. Cross-Level Patterns

### Settings Present at Both Levels
| Setting | User-Level (`~/.claude/`) | Meta-Project (`.claude/`) |
|---------|--------------------------|--------------------------|
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | `"1"` | `"1"` |
| `model` | `"sonnet"` | (inherited) |
| Deny `rm -rf /`, `rm -rf ~` | ✅ | ✅ |
| Deny `sudo:*` | ✅ | ✅ |
| Deny `git push --force`, `git reset --hard` | ✅ | ✅ |
| Deny Read/Edit `.env*` / `credentials*` | ✅ | ✅ |
| Ask `git push`, `rm`, `docker` | ✅ | ✅ |
| Allow `uv`, `ruff`, `mypy`, `pytest` | ✅ | ✅ |
| Allow `git` subcommands (add, commit, status...) | ✅ | ✅ |
| Attribution `commit: "none"` | Not set | ✅ |
| `includeGitInstructions: false` | Not set | ✅ |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Not set | `"70"` |
| Sandbox (auto-allow + deny list) | Not set | ✅ |

**Potential conflict:** User level has broad `Write(/Users/bruno/**)` allow. Meta-project level adds sandbox restrictions (deny `.env*`, `*.pem`, `*.key`). Meta-project rules take precedence in that context.

### Naming Conventions
- Agent files: `{role}-{domain}.md`
- Report files: `{YYYY-MM-DD-HHmmss}-phase-{N}-{agent}-{slug}.md` (timestamp UUID)
- Memory files: `{project}-{topic}-{date}.md`
- Skills: directories with `SKILL.md`
- Plans: random adjective-animal combos
- Project dirs in `~/.claude/projects/`: path-with-dashes (`-Users-bruno-sec-llm-workbench`)

### TeamCreate Enforcement Chain
Three redundant layers:
1. **Global `CLAUDE.md`** (written instruction, loaded every session via @ import)
2. **`deterministic-execution-protocol.md`** (formal spec, loaded as rule)
3. **`user-prompt-submit.sh` → `settings.local.json`** (runtime hook, fires before EVERY prompt as system message)

The hook is the strongest layer — it injects a MANDATORY PROTOCOL reminder as a system message before Claude reasons on each request.

### Enforcement Mechanisms Layering
```
User-level (global, lowest priority)
  ├── CLAUDE.md (TeamCreate + error review mandate)
  ├── settings.json (broad allow + deny base)
  ├── settings.local.json (hook registration)
  └── hooks/user-prompt-submit.sh (runtime TeamCreate gate)

Meta-project level (project-specific, higher priority)
  ├── CLAUDE.md (Context7 mandate + /verify mandate + auto-load @refs)
  ├── settings.json (sandbox + stricter denies + compaction + agent teams)
  ├── hooks/ (6 active: session lifecycle + code quality gate + commit gate)
  └── agents/ (23 agents with permission modes enforced at agent level)
```

---

## 4. Issues & Observations

### Active Issues
| # | Severity | Issue |
|---|----------|-------|
| 1 | HIGH | **MEMORY.md truncation:** 217 lines, only first 200 loaded. Hook Classification section (lines 201–217) silently drops every session. Stage 4 hook reuse data is invisible to Claude. |
| 2 | MEDIUM | **3 unregistered hooks:** `pre-commit.sh`, `test-framework.sh`, `verify-best-practices.sh` exist in `hooks/` but not in `settings.json`. May be legacy, may be intended but forgotten. |
| 3 | MEDIUM | **researcher-1/2/3 lack Project Context block:** Newly added agents have minimal definitions without the standard `## Project Context (CRITICAL)` block. They won't auto-read `.build/active-project`. |
| 4 | LOW | **`settings.json.back` exists:** Backup of prior settings config. Could cause confusion if referenced. |
| 5 | LOW | **No `.mcp.json` in inventory:** `session-start.sh` references `.mcp.json` for MCP health check but file not inventoried in `.claude/` scan. May be in project root or missing. |
| 6 | LOW | **`bypassPermissions` mode trap documented but pattern still used:** errors-to-rules documents that `bypassPermissions` doesn't work without `--dangerously-skip-permissions`, yet orchestrator spawn protocol in CLAUDE.md still uses `mode="bypassPermissions"`. |
| 7 | INFO | **`CLAUDE.local.md` duplicates model routing already in `model-selection-strategy.md`:** Small redundancy, not a blocker. |

---

## 5. Key Facts for Gap Analysis (Round 3)

- **23 agents** across 3 verification waves + meta utilities + on-demand specialists. All use `sonnet` except 3 haiku utilities.
- **14 active verification agents** in `/verify` skill (Wave 1: 3, Wave 2: 8, Wave 3: 3).
- **9 hooks defined, 6 registered.** Checkpoint gate: `post-code.sh` creates markers; `pre-git-commit.sh` blocks commits; `/verify` clears markers.
- **Briefing injection system** (session-start.sh + pre-compact.sh + session-end.sh) provides cross-session continuity for SIOPV project without relying solely on context.
- **TeamCreate enforcement is triple-layered:** CLAUDE.md → rules → runtime hook. The runtime hook (fires before every prompt) is the strongest.
- **Model routing strategy:** sonnet=agents, haiku=utilities, opus=planning/orchestration (>5 modules).
- **Permission modes by role:** `plan` = read-only auditors; `acceptEdits` = writers; `default` = runtime runners.
- **Meta-project vs target project separation:** Meta-project is orchestration layer; target projects (siopv, etc.) read from `.build/active-project`.
- **MEMORY.md is 217 lines** (limit 200). Hook Classification data is silently lost every session — a live defect needing fix before Stage 4 reuse decisions.
- **3 unregistered hooks** (`pre-commit.sh`, `test-framework.sh`, `verify-best-practices.sh`) may indicate legacy scripts that should be audited or removed.
- **researcher-1/2/3 agents** are newly added (untracked git status) and lack the standard Project Context block — they cannot auto-determine target project path.
- **`skipDangerousModePermissionPrompt: true`** at global level means sessions launched with `--dangerously-skip-permissions` will have full agent autonomy.
- **17 skills** registered, most domain-specific (langraph, openfga, presidio, trivy, xai, cve). Key operational skill: `/verify` which is the gate for all commits.
- **Verification thresholds:** 0 violations for best-practices-enforcer, 0 CRITICAL/HIGH for security-auditor, 0 hallucinations for hallucination-detector, code-reviewer score ≥ 9.0/10.
- **12 scripts** in `scripts/` support cost tracking, MCP health, parallel verification, secret scanning — these are supporting infrastructure for the meta-project workflow.
