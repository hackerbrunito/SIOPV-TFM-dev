# File Inventory Report: 28 Claude Code Configuration Files for SIOPV

**Date:** 2026-03-09
**Agent:** file-inventory-checker
**Total files checked:** 28
**Files exist:** 28/28
**Broken references found:** 3

---

## 1. Root

### 1.1 `/Users/bruno/siopv/CLAUDE.md`

- **Exists:** Yes
- **Lines:** 67
- **Summary:** Main project instruction file for Claude Code. Defines SIOPV as "Sistema Inteligente de Orquestacion y Priorizacion de Vulnerabilidades." Contains CRITICAL RULES section requiring session-start workflow reading, Context7 queries before using external libraries, hexagonal architecture compliance (domain has NO external dependencies), `/verify` execution before commits, and human checkpoint adherence. Includes a Project State table (Python 3.11+, Phases 0-6 completed, 7-8 pending, current work is comprehensive audit stages 1-4). Lists 5 audit stages with statuses (all Pending). Has References and On-Demand References tables pointing to workflow, rules, and docs files. Includes Compact Instructions for context preservation.
- **Cross-references:**
  - `.claude/workflow/01-session-start.md` (exists)
  - `.ignorar/09-03-2026-planning-and-briefing-preparation-for-exploring-and-gathering-siopv/2026-03-09_definitive-dual-purpose-record-merged-comprehensive.md` (exists)
  - `.claude/workflow/04-before-commit.md` (exists)
  - `.claude/workflow/03-human-checkpoints.md` (exists)
  - `.claude/workflow/02-audit-stages.md` (exists)
  - `.claude/rules/tech-stack.md` (exists)
  - `.claude/rules/naming-conventions.md` (exists)
  - `.claude/docs/agent-tool-schemas.md` (exists)
  - `.claude/docs/model-selection-strategy.md` (exists)
  - `.claude/docs/verification-thresholds.md` (exists)
  - `.claude/rules/agent-reports.md` (exists)
  - `docs/SIOPV_Propuesta_Tecnica_v2.txt` -- **BROKEN** (file does not exist, `docs/` directory missing entirely)
  - `.claude/rules/errors-to-rules.md` (exists)
- **Broken references:** `docs/SIOPV_Propuesta_Tecnica_v2.txt` does not exist.

---

## 2. Agents (10 files)

### 2.1 `/Users/bruno/siopv/.claude/agents/codebase-scanner.md`

- **Exists:** Yes
- **Lines:** 86
- **Summary:** Agent definition for a read-only codebase structure scanner. Frontmatter: name `codebase-scanner`, model `sonnet`, maxTurns 25, disallowed tools Write/Edit. Role: scan `~/siopv/src/siopv/` directory structure, catalog all Python files by package (domain, application, adapters, infrastructure, interfaces), track line counts, `__init__.py` exports, external/internal imports, map tests to source modules, and compare `pyproject.toml` declared vs actual imports. Strict DO NOT rules (no modifications, no speculation, no suggestions). Output format: Codebase Scanner Report with STAGE-1/Round/Batch metadata, Findings with F-NNN IDs and severity levels, Summary counts, and Self-Verification checklist.
- **Cross-references:**
  - `~/siopv/src/siopv/` (exists as `/Users/bruno/siopv/src/siopv/`)
  - `~/siopv/tests/` (exists)
  - `~/siopv/pyproject.toml` (exists)
- **Broken references:** None.

### 2.2 `/Users/bruno/siopv/.claude/agents/spec-mapper.md`

- **Exists:** Yes
- **Lines:** 86
- **Summary:** Agent definition for specification compliance scanner. Frontmatter: name `spec-mapper`, model `sonnet`, maxTurns 25, disallowed tools Write/Edit. Role: read the technical specification at `docs/SIOPV_Propuesta_Tecnica_v2.txt`, extract all stated components, and compare against actual implementation in `src/siopv/`. Maps each spec requirement to a status: IMPLEMENTED, PARTIAL, MISSING, or EXTRA. Documents phase-by-phase directory mapping (Phase 1 ingestion through Phase 8 output). Output format: Spec Mapper Report with Spec-vs-Implementation Matrix table, Findings with F-NNN IDs, Summary counts, Self-Verification checklist.
- **Cross-references:**
  - `docs/SIOPV_Propuesta_Tecnica_v2.txt` -- **BROKEN** (file does not exist)
  - `src/siopv/application/ingestion/` (would need verification)
  - Multiple `src/siopv/` subdirectories per phase
- **Broken references:** `docs/SIOPV_Propuesta_Tecnica_v2.txt` does not exist.

### 2.3 `/Users/bruno/siopv/.claude/agents/hexagonal-auditor.md`

- **Exists:** Yes
- **Lines:** 96
- **Summary:** Agent definition for hexagonal architecture compliance auditor. Frontmatter: name `hexagonal-auditor`, model `sonnet`, maxTurns 30, disallowed tools Write/Edit. Role: verify ports-and-adapters pattern compliance in `~/siopv/src/siopv/`. Defines 6 architecture rules covering dependency direction for all 5 layers (domain, application, adapters, infrastructure, interfaces) plus DI container. Workflow: grep all imports, build import matrix, flag violations, check port definitions have adapters, check DI registration. Output format: Import Matrix table (source layer x target layer), Findings with rule-violated field, Port Coverage table, Summary with violation counts, Self-Verification checklist.
- **Cross-references:**
  - `~/siopv/src/siopv/` (exists)
  - `domain/ports/` (internal reference)
  - `infrastructure/di/` (internal reference)
- **Broken references:** None.

### 2.4 `/Users/bruno/siopv/.claude/agents/sota-researcher.md`

- **Exists:** Yes
- **Lines:** 100
- **Summary:** Agent definition for state-of-the-art techniques researcher. Frontmatter: name `sota-researcher`, model `opus`, maxTurns 30, disallowed tools Write/Edit/Bash. Has WebSearch and WebFetch tools for online research. Role: investigate current best practices for SIOPV components (LangGraph, XGBoost, DLP/Presidio, OpenFGA, ChromaDB RAG/CRAG, Streamlit HITL, Jira/PDF output) and compare against current implementation. Every claim must cite a specific source (URL, paper, documentation). Minimum 3 search queries per topic. Verifies library versions and API via WebSearch. Output format: SOTA Research Report with Current Implementation section, Findings with source citations and applicability, Sources Consulted table, Self-Verification checklist.
- **Cross-references:** None to specific files (scope assigned dynamically by orchestrator).
- **Broken references:** None.

### 2.5 `/Users/bruno/siopv/.claude/agents/security-auditor.md`

- **Exists:** Yes
- **Lines:** 105
- **Summary:** Agent definition for cybersecurity vulnerability scanner. Frontmatter: name `security-auditor`, model `sonnet`, maxTurns 25, disallowed tools Write/Edit. Role: identify vulnerabilities in `~/siopv/src/siopv/` covering OWASP Top 10 + LLM-specific injection vectors. Defines 7 security check categories: (1) Hardcoded Secrets CWE-798, (2) Injection CWE-89/78, (3) Path Traversal CWE-22, (4) Insecure Deserialization CWE-502, (5) LLM/Prompt Injection, (6) Sensitive Data Exposure CWE-200, (7) Dependency Vulnerabilities via pip-audit. Each category has SIOPV-specific guidance (e.g., check for `openfga:openfga`, HaikuSemanticValidatorAdapter). Output format: Security Audit Report with Executive Summary severity table, Findings with CWE IDs, Secrets Scan table, Dependency Vulnerabilities table, PASS/FAIL result, Self-Verification checklist.
- **Cross-references:**
  - `infrastructure/config/settings.py` (internal reference)
  - `.env.example` (exists)
  - `docker-compose.yml` (would need verification)
- **Broken references:** None (references are internal guidance, not hard dependencies).

### 2.6 `/Users/bruno/siopv/.claude/agents/best-practices-enforcer.md`

- **Exists:** Yes
- **Lines:** 95
- **Summary:** Agent definition for Python 2026 standards verification. Frontmatter: name `best-practices-enforcer`, model `sonnet`, maxTurns 25, disallowed tools Write/Edit. Role: verify modern Python standards in `~/siopv/src/siopv/`. Defines 6 verification categories: (1) Type Hints (Python 3.11+ syntax vs legacy `from typing import`), (2) Pydantic v2 (ConfigDict vs class Config), (3) HTTP Client (httpx vs requests), (4) Logging (structlog vs print/logging, ExceptionRenderer vs format_exc_info), (5) Paths (pathlib vs os.path), (6) Async Patterns (asyncio.run() in async contexts). Each category has SIOPV-specific checks. Output format: Summary table by category with OK/FAIL status, Violations Found table, PASS/FAIL result, Self-Verification checklist.
- **Cross-references:**
  - `domain/entities/`, `domain/value_objects/`, `infrastructure/config/settings.py` (internal)
  - `adapters/nvd/`, `adapters/epss/`, `adapters/github/`, `adapters/tavily/` (internal)
  - `dlp_node`, `enrich_node`, `authorization_node` (internal SIOPV nodes)
- **Broken references:** None.

### 2.7 `/Users/bruno/siopv/.claude/agents/test-coverage-auditor.md`

- **Exists:** Yes
- **Lines:** 103
- **Summary:** Agent definition for test coverage gap analysis. Frontmatter: name `test-coverage-auditor`, model `sonnet`, maxTurns 25, disallowed tools Write/Edit. Role: analyze `~/siopv/tests/` coverage against `~/siopv/src/siopv/`. Workflow: run pytest with coverage json output, read coverage.json for per-module line rates, map source files to test files, identify 0% modules, below-50% modules (per-module floor), below-80% modules (project target). Checks SIOPV-specific known gaps (Phase 2 adapters, empty adapter stubs, always-skipping integration tests). Output format: Test Coverage Audit Report with Overall Metrics, Per-Module Coverage table with OK/BELOW_FLOOR/ZERO status, Coverage Gaps findings, Untested Modules table, Always-Skipped Tests table, Summary, Self-Verification checklist.
- **Cross-references:**
  - `~/siopv/tests/` (exists)
  - `~/siopv/src/siopv/` (exists)
  - `coverage.json` (referenced for reading)
  - Phase 2 adapters (NVD, EPSS, GitHub, Tavily, ChromaAdapter)
  - `adapters/llm/`, `adapters/notification/`, `adapters/persistence/` (empty stubs)
- **Broken references:** None.

### 2.8 `/Users/bruno/siopv/.claude/agents/wave-summarizer.md`

- **Exists:** Yes
- **Lines:** 83
- **Summary:** Agent definition for wave/round report consolidation. Frontmatter: name `wave-summarizer`, model `sonnet`, maxTurns 15, disallowed tools Bash/Edit, has Write access. Role: read reports from a round's agents and produce a single consolidated summary. Deduplicates findings (merge same file:line or same issue), preserves ALL specific numbers/paths/severity ratings exactly, sorts by severity. Does NOT add own findings, does NOT change severity ratings. Output format: Consolidated Summary with reports-consolidated count, unique findings count, duplicates-removed count, Findings by Severity sections, Cross-Report Patterns, Escalations, Self-Verification checklist.
- **Cross-references:** None (reads paths assigned dynamically by orchestrator).
- **Broken references:** None.

### 2.9 `/Users/bruno/siopv/.claude/agents/orchestrator.md`

- **Exists:** Yes
- **Lines:** 82
- **Summary:** Agent definition for stage orchestration. Frontmatter: name `orchestrator`, model `opus`, maxTurns 50, has all coordination tools (Read, Grep, Glob, Bash, Write, Agent, SendMessage). Role: manage audit stage execution by spawning specialized agents in rounds, collecting reports, triggering summarizers, and enforcing human checkpoints. Maximum 4-6 parallel agents per batch. After every round, sends summary to claude-main via SendMessage and WAITs for human approval. Agent Spawn Protocol: include full persona, assigned scope, report output path (NNN_YYYY-MM-DD_HH.MM.SS format), and 1,500-token summary budget. Maintains progress tracker file. Error handling: log failures, escalate if 2+ agents fail, mark FAILED after 2 correction attempts. Report paths reference `.ignorar/agent-persona-research-2026-03-09/stage-{1-4}/`.
- **Cross-references:**
  - `.claude/agents/` definitions (indirect, for persona loading)
  - `.ignorar/agent-persona-research-2026-03-09/stage-1/` through `stage-4/` -- **BROKEN** (directory does not exist yet; will be created when stages run)
- **Broken references:** `.ignorar/agent-persona-research-2026-03-09/` directory does not exist yet (expected to be created at runtime).

### 2.10 `/Users/bruno/siopv/.claude/agents/report-generator.md`

- **Exists:** Yes
- **Lines:** 94
- **Summary:** Agent definition for final stage report generation. Frontmatter: name `report-generator`, model `sonnet`, maxTurns 15, disallowed tools Bash/Edit, has Write access. Role: read round summaries (NOT individual agent reports or source code) and produce a final consolidated stage report suitable for thesis documentation. Merges findings across rounds, deduplicates, generates executive summary with metrics, identifies cross-cutting themes. Output format: Stage Final Report with Executive Summary severity table, Findings by severity with source-round cross-references, Cross-Cutting Themes, Stage Metrics (rounds, agents, reports, findings pre/post dedup, duration), Self-Verification checklist.
- **Cross-references:** None (reads paths assigned dynamically by orchestrator).
- **Broken references:** None.

---

## 3. Hooks (2 files)

### 3.1 `/Users/bruno/siopv/.claude/hooks/session-start.sh`

- **Exists:** Yes
- **Lines:** 115
- **Summary:** Bash session-start hook script. Sections: (1) Environment Validation -- copies `.env.example` to `.env` if missing, sources `.env` if present. (2) Log Rotation -- 30-day rolling window, compresses logs older than 7 days with gzip, deletes logs older than 30 days. (3) Traceability -- creates `.build/logs/{agents,sessions,decisions}/` directories, rotates existing logs, creates `.build/checkpoints/{pending,daily}/`, writes session JSON file with session_id, timestamp, project name, counters. Writes `current-session-id` to `.build/`. (4) State Detection -- detects current phase (checks for `interfaces/streamlit` or `interfaces/dashboard` directories), detects audit stage progress (scans `.ignorar/agent-persona-research-2026-03-09/stage-{1-4}/` for .md files). Writes `current-phase`, `current-audit-stage`, and `active-project` to `.build/`.
- **Cross-references:**
  - `.env.example` (exists)
  - `.env` (created from example if missing)
  - `.build/logs/`, `.build/checkpoints/` (created by script)
  - `.build/current-session-id`, `.build/current-phase`, `.build/current-audit-stage`, `.build/active-project` (created by script)
  - `.ignorar/agent-persona-research-2026-03-09/stage-{1-4}/` (checked but not yet created)
- **Broken references:** None (script handles non-existence gracefully).

### 3.2 `/Users/bruno/siopv/.claude/hooks/pre-git-commit.sh`

- **Exists:** Yes
- **Lines:** 97
- **Summary:** Bash pre-tool-use hook that intercepts `git commit` commands. Reads JSON input from stdin, extracts command via `jq`. If not a git commit, allows. If git commit: checks `.build/checkpoints/pending/` for unverified file markers. If pending files exist, BLOCKS the commit with a Spanish-language message listing pending files and directing to run `/verify`. Logs all commit decisions (allowed/blocked) to `.build/logs/decisions/` as JSONL entries with decision ID, timestamp, session ID, outcome, and reason. Uses `hookSpecificOutput` format with `permissionDecision: allow/deny`.
- **Cross-references:**
  - `.build/checkpoints/pending/` (checked for markers)
  - `.build/logs/decisions/` (writes decision logs)
- **Broken references:** None.

---

## 4. Rules (4 files)

### 4.1 `/Users/bruno/siopv/.claude/rules/errors-to-rules.md`

- **Exists:** Yes
- **Lines:** 29
- **Summary:** SIOPV-specific errors-to-rules log. Currently EMPTY (no errors logged yet). Contains template for adding entries (YYYY-MM-DD: Short description, Error, Rule format). Notes that global errors are in `~/.claude/rules/errors-to-rules.md` (which exists and has 10 logged errors).
- **Cross-references:**
  - `~/.claude/rules/errors-to-rules.md` (exists, global file)
- **Broken references:** None.

### 4.2 `/Users/bruno/siopv/.claude/rules/agent-reports.md`

- **Exists:** Yes
- **Lines:** 63
- **Summary:** Defines report persistence conventions for SIOPV agents. Report directory structure under `.ignorar/agent-persona-research-2026-03-09/stage-{1-5}/`. Naming convention: `NNN_YYYY-MM-DD_HH.MM.SS_descriptive-name.md` (sequence + timestamp for uniqueness under parallel execution). Agent wave timing: Batch A of 4-6 agents per round, wave summarizer after completion, human checkpoint. Timing targets: scanners ~10 min, researchers ~15 min, summarizers ~5 min, round total ~20 min. Report content requirements: stage/round/batch assignment, sequence number, timestamps, duration, self-verification checklist. Return summary token limits: scanners/researchers 1,500 tokens, summarizers/report-generators 2,000 tokens.
- **Cross-references:**
  - `.ignorar/agent-persona-research-2026-03-09/stage-{1-5}/` (not yet created)
- **Broken references:** None (directories created at runtime).

### 4.3 `/Users/bruno/siopv/.claude/rules/naming-conventions.md`

- **Exists:** Yes
- **Lines:** 84
- **Summary:** Comprehensive naming conventions for SIOPV. Terminology hierarchy: Phase (development phase 0-8), Stage (audit stage 1-5), Round (sequential unit within stage), Batch (parallel group max 4-6 agents), Wave (legacy term from meta-project). File naming patterns: agent reports (`NNN_YYYY-MM-DD_HH.MM.SS_descriptive-name.md`), production reports (`{TIMESTAMP}-phase-{N}-{agent-name}-{slug}.md`), briefings (`stage-{N}-briefing.md`), handoffs (`handoff-YYYY-MM-DD-{description}.md`). Full directory structure map showing `.claude/`, `.ignorar/`, `.build/`, `src/siopv/`, `tests/`. Python code naming: snake_case files, PascalCase classes, UPPER_SNAKE_CASE constants, test files as `test_{module_name}.py`.
- **Cross-references:**
  - `.claude/agents/`, `.claude/hooks/`, `.claude/rules/`, `.claude/workflow/`, `.claude/docs/` (all exist)
  - `.ignorar/agent-persona-research-2026-03-09/stage-{1-5}/` (not yet created)
  - `.ignorar/production-reports/{agent-name}/phase-{N}/` (not yet created)
  - `.build/checkpoints/`, `.build/logs/` (exist)
- **Broken references:** None (directories created at runtime).

### 4.4 `/Users/bruno/siopv/.claude/rules/tech-stack.md`

- **Exists:** Yes
- **Lines:** 78
- **Summary:** Complete technology stack reference for SIOPV. Runtime: Python 3.11+, uv, ruff, mypy, pytest. Core libraries table (15 entries): LangGraph >=0.2.0 (orchestration), XGBoost >=2.0.0 (ML classification), SHAP/LIME (XAI), Pydantic v2 (validation), structlog (logging), httpx (async HTTP), ChromaDB >=0.5.0 (RAG/CRAG), Presidio >=2.2.0 (DLP), Anthropic SDK (Claude Haiku semantic validator), OpenFGA SDK (authorization), Streamlit >=1.40.0 (Phase 7 dashboard), FPDF2 (Phase 8 PDF), Typer (CLI), tenacity (retry). Infrastructure: PostgreSQL 16, OpenFGA, Keycloak, Docker Compose. Architecture section: hexagonal pattern, dependency direction inward, DI via `@lru_cache`, LangGraph TypedDict state, SQLite checkpointing. Pipeline flow: `START -> authorize -> ingest -> dlp -> enrich -> classify -> [escalate] -> END`. Commands section with setup, run, test, lint, type check examples.
- **Cross-references:**
  - `application/orchestration/` (internal)
  - `application/classification/` (internal)
  - Various adapter directories (internal)
  - `infrastructure/config/`, `infrastructure/logging/`, `infrastructure/di/` (internal)
  - `interfaces/cli/`, `interfaces/streamlit/` (internal)
- **Broken references:** None.

---

## 5. Workflow (4 files)

### 5.1 `/Users/bruno/siopv/.claude/workflow/01-session-start.md`

- **Exists:** Yes
- **Lines:** 54
- **Summary:** Session start workflow for SIOPV. Three triggers: (1) "Continua con SIOPV" -- detects current phase and audit stage from `.build/` files, continues from where left off. (2) "Ejecuta Stage N" -- reads stage briefing, verifies prerequisites, spawns orchestrator. (3) Default (no instruction) -- reads current audit stage, proposes next action. State detection table: AUDIT_NOT_STARTED, AUDIT_IN_PROGRESS, AUDIT_COMPLETE, PHASE_7_PENDING, PHASE_8_PENDING. Key Paths table: briefing file, tech spec, stage reports, settings, graph. Known Audit Findings summary from 2026-03-05 (4 CRITICAL, 5 HIGH, 4 MEDIUM, 2 LOW).
- **Cross-references:**
  - `.build/current-phase` (exists)
  - `.build/current-audit-stage` (exists)
  - `.ignorar/09-03-2026-planning-and-briefing-preparation-for-exploring-and-gathering-siopv/2026-03-09_definitive-dual-purpose-record-merged-comprehensive.md` (exists)
  - `docs/SIOPV_Propuesta_Tecnica_v2.txt` -- **BROKEN** (does not exist)
  - `.ignorar/agent-persona-research-2026-03-09/stage-{N}/` (not yet created)
  - `src/siopv/infrastructure/config/settings.py` (exists)
  - `src/siopv/application/orchestration/graph.py` (exists)
- **Broken references:** `docs/SIOPV_Propuesta_Tecnica_v2.txt` does not exist.

### 5.2 `/Users/bruno/siopv/.claude/workflow/02-audit-stages.md`

- **Exists:** Yes
- **Lines:** 85
- **Summary:** Overview of the 5 audit stages to run before Phase 7. Purpose: comprehensive audit of Phases 0-6 codebase. Stage summary table: Stage 1 (Discovery & Spec Mapping, 2 rounds), Stage 2 (Hexagonal Quality Audit, 2-3 rounds), Stage 3 (SOTA Research & Deep Scan, 2-3 rounds), Stage 4 (Config Setup, 2 rounds), Stage 5 (Remediation-Hardening, variable rounds). Team template: claude-main spawns orchestrator via TeamCreate + Agent, orchestrator manages rounds, 4-6 parallel agents per batch, wave summarizer, human checkpoint. Round structure diagram showing batch -> summarizer -> human checkpoint flow. Stage details listing which agents are used per stage and expected outputs. Report directories under `.ignorar/agent-persona-research-2026-03-09/stage-{1-5}/`.
- **Cross-references:**
  - `.ignorar/agent-persona-research-2026-03-09/stage-{1-5}/` (not yet created)
  - `.ignorar/09-03-2026-planning-and-briefing-preparation-for-exploring-and-gathering-siopv/2026-03-09_definitive-dual-purpose-record-merged-comprehensive.md` (exists)
  - Agent names: codebase-scanner, spec-mapper, test-coverage-auditor, hexagonal-auditor, security-auditor, best-practices-enforcer, sota-researcher (all exist as agent definitions)
- **Broken references:** None (stage directories created at runtime).

### 5.3 `/Users/bruno/siopv/.claude/workflow/03-human-checkpoints.md`

- **Exists:** Yes
- **Lines:** 85
- **Summary:** Defines when to PAUSE for human approval vs CONTINUE automatically. PAUSE triggers: (1) After each audit round -- present wave-summarizer consolidated summary, (2) Stage transitions -- present final report and next stage plan, (3) Destructive/irreversible actions (file deletion, architectural changes, multi-module changes >3 modules), (4) After verification agents, (5) Stage 5 remediation design. CONTINUE automatically for: agent delegation (scan/research/summarize), Context7 queries, report generation, file reading, progress tracker updates. Two checkpoint flow diagrams: Audit Stage flow (agents -> summarizer -> human checkpoint -> next round -> report-generator -> human approval) and Code Implementation flow (implementer -> human review -> verification agents -> human approval -> commit).
- **Cross-references:** None (process document, references concepts not specific files).
- **Broken references:** None.

### 5.4 `/Users/bruno/siopv/.claude/workflow/04-before-commit.md`

- **Exists:** Yes
- **Lines:** 59
- **Summary:** Pre-commit checklist for SIOPV. Mandatory steps: ruff format, ruff check, mypy, pytest. For significant changes: run security-auditor, best-practices-enforcer, test-coverage-auditor agents. Verification thresholds table (ruff check 0 errors, ruff format no changes, mypy 0 errors, pytest all pass, security-auditor 0 CRITICAL/HIGH, best-practices-enforcer 0 violations, test-coverage-auditor all modules >= 50%). Hook section: pre-git-commit.sh blocks commit if `.build/checkpoints/pending/` has unverified markers. Failure procedure: do not commit, fix, re-verify, then commit. SIOPV-Specific Checks: domain layer isolation, port-adapter coverage, DI registration, no asyncio.run in async contexts, no hardcoded model IDs, structlog ExceptionRenderer usage.
- **Cross-references:**
  - `.claude/docs/verification-thresholds.md` (exists)
  - `.build/checkpoints/pending/` (exists)
  - `.claude/hooks/pre-git-commit.sh` (exists, implicit reference)
- **Broken references:** None.

---

## 6. Docs (3 files)

### 6.1 `/Users/bruno/siopv/.claude/docs/verification-thresholds.md`

- **Exists:** Yes
- **Lines:** 60
- **Summary:** Centralized pass/fail criteria for all verification checks. Two threshold tables: (1) General checks -- ruff check (0 errors+warnings), ruff format (no changes), mypy (0 errors), pytest (all pass), security-auditor (0 CRITICAL/HIGH, MEDIUM is warning-only), best-practices-enforcer (0 violations), test-coverage project (>= 80%), test-coverage per-module (>= 50%). (2) SIOPV-Specific checks -- hexagonal compliance (0 layer violations), port coverage (all ports have adapters + DI), async safety (0 asyncio.run in async paths), no hardcoded secrets, no hardcoded model IDs. Details sections for security-auditor severity levels, best-practices violation types, test-coverage exclusions. Command Blockers section describing pre-git-commit hook behavior. Failure procedure: do not commit, fix, re-verify.
- **Cross-references:**
  - `.claude/hooks/pre-git-commit.sh` (exists)
  - `.build/checkpoints/pending/` (exists)
- **Broken references:** None.

### 6.2 `/Users/bruno/siopv/.claude/docs/model-selection-strategy.md`

- **Exists:** Yes
- **Lines:** 57
- **Summary:** Decision tree for selecting AI models when delegating to agents. Model capabilities table: Haiku ($0.25/$1.25 MTok, for file ops/simple validation), Sonnet 4.5 ($3/$15, for code synthesis/verification), Opus 4.6 ($15/$75, for orchestration/architecture). Agent model assignments table (10 agents mapped): codebase-scanner/spec-mapper/hexagonal-auditor/security-auditor/best-practices-enforcer/test-coverage-auditor/wave-summarizer/report-generator all use Sonnet; sota-researcher and orchestrator use Opus. Decision tree: single file read -> Haiku, multi-file scan -> Sonnet, SOTA research -> Opus, orchestration -> Opus. Override guidelines for downgrade/upgrade. Cost targets: < $0.50 per verification cycle, distribution ~40% Haiku / ~50% Sonnet / ~10% Opus.
- **Cross-references:** Agent names match all 10 agent definitions in `.claude/agents/`.
- **Broken references:** None.

### 6.3 `/Users/bruno/siopv/.claude/docs/agent-tool-schemas.md`

- **Exists:** Yes
- **Lines:** 67
- **Summary:** Tool access permissions matrix for all 10 agents. Full matrix table showing which tools each agent can use (Read, Grep, Glob, Bash, Write, Edit, WebSearch, WebFetch, Agent, SendMessage). Key constraints sections: Scanner/Auditor agents (read-only, Bash restricted to read-only commands), Researcher agents (no filesystem mods, WebSearch required for claims), Summarizer/Report agents (Write only to assigned paths, read only assigned inputs), Orchestrator (full coordination tools including Agent and SendMessage). Parallelization rules: independent tools can run in parallel (multiple Greps, Reads), dependent tools must be sequential (Glob -> Read -> Analyze). Bash safety rules for scanner agents: ALLOWED list (ruff, mypy, pytest, wc, find) and BLOCKED list (rm, mv, cp, chmod, sudo, eval, write redirects).
- **Cross-references:** All 10 agent names match definitions in `.claude/agents/`.
- **Broken references:** None.

---

## 7. Memory (1 file)

### 7.1 `/Users/bruno/.claude/projects/-Users-bruno-siopv/memory/MEMORY.md`

- **Exists:** Yes
- **Lines:** 95
- **Summary:** Persistent project memory for SIOPV across Claude Code sessions. Active Project section: name SIOPV (full name in Spanish), path `~/siopv/`, type master's thesis, hexagonal architecture. Phase Status table: Phases 0-6 Completed, 7-8 PENDING. Audit Status table: all 5 stages "Not started" (Stage 5 designed after 1-4). Metrics from 2026-03-05: 1,404 tests passed, 12 skipped, 83% coverage, 0 mypy errors, 0 ruff errors, 214 packages resolved. Known Audit Findings: detailed list of 15 findings (4 CRITICAL + 5 HIGH + 4 MEDIUM + 2 LOW) with specific descriptions. Key File Paths table (8 entries). Briefing file path. Pipeline flow diagram. Architecture notes (TypedDict state, SQLite checkpointing, lru_cache DI, Docker Compose, dlp_node is the real path).
- **Cross-references:**
  - `~/siopv/` (exists)
  - `src/siopv/application/orchestration/graph.py` (exists)
  - `src/siopv/application/orchestration/state.py` (exists)
  - `src/siopv/interfaces/cli/main.py` (exists)
  - `src/siopv/infrastructure/config/settings.py` (exists)
  - `src/siopv/infrastructure/di/__init__.py` (exists)
  - `src/siopv/infrastructure/di/dlp.py` (exists)
  - `src/siopv/domain/constants.py` (exists)
  - `src/siopv/infrastructure/logging/setup.py` (exists)
  - `docs/SIOPV_Propuesta_Tecnica_v2.txt` -- **BROKEN** (does not exist)
  - `.ignorar/09-03-2026-planning-and-briefing-preparation-for-exploring-and-gathering-siopv/2026-03-09_definitive-dual-purpose-record-merged-comprehensive.md` (exists)
- **Broken references:** `docs/SIOPV_Propuesta_Tecnica_v2.txt` does not exist.

---

## Summary

### File Existence

| Category | Count | All Exist |
|----------|-------|-----------|
| Root | 1 | Yes |
| Agents | 10 | Yes |
| Hooks | 2 | Yes |
| Rules | 4 | Yes |
| Workflow | 4 | Yes |
| Docs | 3 | Yes |
| Memory | 1 | Yes |
| **Total** | **28** | **Yes (28/28)** |

### Line Counts

| File | Lines |
|------|-------|
| CLAUDE.md | 67 |
| codebase-scanner.md | 86 |
| spec-mapper.md | 86 |
| hexagonal-auditor.md | 96 |
| sota-researcher.md | 100 |
| security-auditor.md | 105 |
| best-practices-enforcer.md | 95 |
| test-coverage-auditor.md | 103 |
| wave-summarizer.md | 83 |
| orchestrator.md | 82 |
| report-generator.md | 94 |
| session-start.sh | 115 |
| pre-git-commit.sh | 97 |
| errors-to-rules.md | 29 |
| agent-reports.md | 63 |
| naming-conventions.md | 84 |
| tech-stack.md | 78 |
| 01-session-start.md | 54 |
| 02-audit-stages.md | 85 |
| 03-human-checkpoints.md | 85 |
| 04-before-commit.md | 59 |
| verification-thresholds.md | 60 |
| model-selection-strategy.md | 57 |
| agent-tool-schemas.md | 67 |
| MEMORY.md | 95 |
| **Total** | **~2,024** |

### Broken References (3 unique broken paths)

| Broken Path | Referenced By |
|-------------|--------------|
| `docs/SIOPV_Propuesta_Tecnica_v2.txt` | CLAUDE.md, spec-mapper.md, 01-session-start.md, MEMORY.md |
| `.ignorar/agent-persona-research-2026-03-09/` | orchestrator.md, agent-reports.md, naming-conventions.md, session-start.sh, 01-session-start.md, 02-audit-stages.md (expected: created at runtime) |

**Note:** The `docs/SIOPV_Propuesta_Tecnica_v2.txt` reference is genuinely broken -- the entire `docs/` directory does not exist in the SIOPV project. This file is referenced by 4 configuration files and is critical for the spec-mapper agent to function. The `.ignorar/agent-persona-research-2026-03-09/` directory is expected to be created when audit stages begin running -- this is not a true broken reference but a runtime dependency.

### Cross-Reference Consistency

All 10 agent definitions use consistent frontmatter format with name, description, tools, model, maxTurns, and disallowedTools. Model assignments in agent frontmatter match the model-selection-strategy.md document exactly. Tool permissions in agent frontmatter match the agent-tool-schemas.md matrix exactly. All agents follow the same report template structure (Findings with F-NNN IDs, severity levels, Self-Verification checklist). The orchestrator references all other agents correctly. Naming conventions in naming-conventions.md align with agent-reports.md format specifications.
