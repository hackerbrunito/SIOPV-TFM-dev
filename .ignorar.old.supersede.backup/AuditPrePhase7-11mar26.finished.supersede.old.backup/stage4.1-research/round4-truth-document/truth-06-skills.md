# Truth-06: SIOPV Skills (`skills/*/SKILL.md`)
**Generated:** 2026-03-13
**Authority:** Round 3 §1 + truth-00 directory structure
**Scope:** All 6 skill directories assigned to truth-06

---

## 1. Skills Inventory

| Skill Dir | Action | Source | Trigger Pattern | Purpose |
|-----------|--------|--------|-----------------|---------|
| `verify/SKILL.md` | ADAPT | `sec-llm-workbench/.claude/skills/verify/SKILL.md` | `/verify [--fix]` — mandatory pre-commit | Run 15-agent verification pipeline on SIOPV; clean pending markers |
| `langraph-patterns/SKILL.md` | COPY | `sec-llm-workbench/.claude/skills/langraph-patterns/SKILL.md` | `langgraph` imports or LangGraph graph/node/checkpoint questions | LangGraph 0.2+ patterns (state graphs, interrupt, checkpointing) |
| `openfga-patterns/SKILL.md` | COPY | `sec-llm-workbench/.claude/skills/openfga-patterns/SKILL.md` | `openfga_sdk` imports or ReBAC/tuple modeling questions | OpenFGA authorization patterns for Phase 5 / Phase 7 auth gate |
| `presidio-dlp/SKILL.md` | COPY | `sec-llm-workbench/.claude/skills/presidio-dlp/SKILL.md` | `presidio_analyzer`/`presidio_anonymizer` imports or PII detection | Presidio DLP patterns for Phase 6 / Phase 7 DLP node |
| `coding-standards-2026/SKILL.md` | COPY | `sec-llm-workbench/.claude/skills/coding-standards-2026/SKILL.md` | Writing/reviewing Python with type hints, Pydantic v2, httpx, structlog, pathlib | Python 2026 standards reference |
| `siopv-remediate/SKILL.md` | NEW | — | `/siopv-remediate` explicit user invocation only | Invoke hex-arch-remediator to fix Stage 2 hexagonal violations |

---

## 2. ADAPT Skills

### `verify/SKILL.md` — ADAPT

**What changes:**

1. **Description line** — update agent count:
   `"Ejecuta los 14 agentes mandatorios de verificacion"` → `"Ejecuta los 15 agentes mandatorios de verificacion (Wave 1+2+3)"`

2. **Remove `.build/active-project` lookup** — meta-project multi-project routing is excluded per truth-00 §4. Replace every occurrence of:
   ```bash
   TARGET=$(cat .build/active-project 2>/dev/null || echo "")
   TARGET="${TARGET/#\~/$HOME}"
   ```
   with:
   ```bash
   TARGET="/Users/bruno/siopv"
   ```
   This applies to: Pre-Check block, Step 1 validation block, Step 4 marker cleanup block, and all Wave 3 `[TARGET_PROJECT]` substitutions.

3. **Remove `regression-guard` agent** — meta-project cross-phase regression tracking, not applicable to SIOPV single-project sessions. Remove from Wave 3 list and timeout/retry policy. Wave 3 drops from 9 to 8 agents.

4. **Add `hex-arch-remediator` as Wave 3 verification agent** — validates that Stage 2 hexagonal violations (#1–#7) are resolved. Wave 3 goes from 8 to 9 agents → total 15 (3+2+9+1 = wait: 3+2+9=14, 14-1+1=14; to reach 15: add hex-arch-remediator brings Wave 3 to 10 → total 15). ✅

   ```
   Task(subagent_type="hex-arch-remediator", prompt="""Verify hexagonal architecture compliance in SIOPV src/.
   Check that all 7 Stage 2 violations are resolved:
   #1 ingest_trivy.py no longer imports TrivyParser from adapters
   #2 classify_risk.py no longer imports FeatureEngineer from adapters
   #3 interfaces/cli/main.py has all 8 adapter ports wired via DI
   #4 dual_layer_adapter.py explicitly inherits DLPPort
   #5 infrastructure/di/authorization.py uses @lru_cache on adapter factory
   #6 ingest_node.py uses injected use case (no direct instantiation)
   #7 edges.py has no domain logic (calculate_batch_discrepancies moved to domain)

   Target project: /Users/bruno/siopv

   PASS criteria: 0 remaining hexagonal violations.
   Report to: .ignorar/production-reports/hex-arch-remediator/phase-{N}/{TIMESTAMP}-phase-{N}-hex-arch-remediator-compliance-check.md
   """)
   ```

5. **Update coverage floor** — in Step 5 `pytest` command:
   `--cov-fail-under=75` → `--cov-fail-under=83`
   In per-module floor comment: `"50% minimum"` → `"50% minimum per-module; 83% overall baseline"`

6. **Remove `show-trace` / `generate-report` references** — these skills are META-ONLY (excluded per truth-00 §4). Remove the footer lines:
   - `Ver /show-trace para consultar logs`
   - `Ver /generate-report para generar reportes`

7. **Remove experimental batch script path** — `.ignorar/experimental-scripts/batch-api-verification/` is a meta-project artifact. Replace batch script path with:
   ```
   siopv/.ignorar/experimental-scripts/batch-api-verification/submit-batch-verification.py
   ```
   (if the file exists; otherwise remove batch section entirely until created)

8. **Trigger pattern update** — keep `disable-model-invocation: true` (user-only, never auto-invoked). Keep `context: fork`. Keep `allowed-tools: ["Read", "Grep", "Glob", "Bash", "Task"]`.

---

## 3. NEW Skills

### `siopv-remediate/SKILL.md`

Complete skill definition following Skills 2.0 format:

```markdown
---
name: siopv-remediate
description: "Fix SIOPV Stage 2 hexagonal architecture violations (#1–#7). Invokes hex-arch-remediator agent. TRIGGER when user explicitly asks to fix hex-arch violations or run /siopv-remediate. DO NOT TRIGGER for general refactoring, normal code fixes, or verification tasks."
disable-model-invocation: true
context: fork
agent: general-purpose
allowed-tools: ["Read", "Grep", "Glob", "Edit", "Write", "Bash"]
---

# /siopv-remediate

Fix hexagonal architecture violations found in SIOPV Stage 2 audit.

## DO NOT TRIGGER conditions

- General refactoring or code improvements → use code-implementer agent
- Verification (checking compliance) → use `/verify` which runs hex-arch-remediator check
- Phase 7 or Phase 8 feature implementation → use phase7-builder or phase8-builder agents

## Stage 2 Violations (7 total)

| # | Severity | File | Issue |
|---|----------|------|-------|
| 1 | CRITICAL | `application/use_cases/ingest_trivy.py:17` | Imports `TrivyParser` from adapters layer |
| 2 | CRITICAL | `application/use_cases/classify_risk.py:18` | Imports `FeatureEngineer` from adapters layer |
| 3 | HIGH | `interfaces/cli/main.py` | All 8 adapter ports = None; DI never wired |
| 4 | MEDIUM | `adapters/dlp/dual_layer_adapter.py` | No explicit `DLPPort` inheritance |
| 5 | MEDIUM | `infrastructure/di/authorization.py` | 3 uncached `OpenFGAAdapter` instances (no `@lru_cache`) |
| 6 | MEDIUM | `application/orchestration/nodes/ingest_node.py` | Directly instantiates use case instead of injected |
| 7 | LOW | `application/orchestration/edges.py` | `calculate_batch_discrepancies()` domain logic in edge routing |

## Invocation

Delegates to `hex-arch-remediator` agent with full violation context:

```
Task(
  subagent_type="hex-arch-remediator",
  prompt="""Fix Stage 2 hexagonal architecture violations in SIOPV.
  Target: /Users/bruno/siopv

  Priority order (CRITICAL first):
  1. #1: ingest_trivy.py — move TrivyParser behind a port interface in domain/ports/
  2. #2: classify_risk.py — move FeatureEngineer behind a port interface in domain/ports/
  3. #3: cli/main.py — wire all 8 adapter ports via DI factories in infrastructure/di/
  4. #4: dual_layer_adapter.py — add explicit `class DualLayerDLPAdapter(DLPPort)`
  5. #5: authorization.py — add @lru_cache to OpenFGA adapter factory function
  6. #6: ingest_node.py — inject use case via constructor, remove direct instantiation
  7. #7: edges.py — extract calculate_batch_discrepancies() to domain layer

  After each fix: run uv run pytest tests/ -x -q to confirm no regressions.
  Save report to: .ignorar/production-reports/hex-arch-remediator/phase-7/
  Report filename: {TIMESTAMP}-phase-7-hex-arch-remediator-remediation.md"""
)
```

## Checkpoint

After invocation, present summary and await human approval before committing
(multi-module change >3 modules requires human checkpoint — per CLAUDE.md rules; `03-human-checkpoints.md` does not exist in siopv/.claude/workflow/ — Conflict #4 resolution).
```

---

## 4. COPY Skills

No changes needed — copy verbatim from source paths:

| Source Path | Destination |
|-------------|-------------|
| `sec-llm-workbench/.claude/skills/langraph-patterns/SKILL.md` | `siopv/.claude/skills/langraph-patterns/SKILL.md` |
| `sec-llm-workbench/.claude/skills/openfga-patterns/SKILL.md` | `siopv/.claude/skills/openfga-patterns/SKILL.md` |
| `sec-llm-workbench/.claude/skills/presidio-dlp/SKILL.md` | `siopv/.claude/skills/presidio-dlp/SKILL.md` |
| `sec-llm-workbench/.claude/skills/coding-standards-2026/SKILL.md` | `siopv/.claude/skills/coding-standards-2026/SKILL.md` |

**Confirmation no changes needed:**
- `langraph-patterns`: Stage 3 verified `@st.fragment`, `interrupt()`, `ThreadPoolExecutor` bridge — patterns confirmed for Phase 7. R3 §1: "Verified correct patterns for Phase 7".
- `openfga-patterns`: Used in Phase 5; same patterns needed for Phase 7 auth gate. No API changes.
- `presidio-dlp`: Used in Phase 6; same patterns needed for Phase 7 DLP node. No API changes.
- `coding-standards-2026`: Python 3.11+, uv, Pydantic v2, httpx, structlog — exact SIOPV stack. No SIOPV-specific deviations.

---

## 5. Excluded Skills

| Meta Skill | Why Excluded |
|-----------|--------------|
| `show-trace/` | Meta-project JSONL trace viewer — SIOPV logs go to `.ignorar/production-reports/` |
| `generate-report/` | Meta-project audit report generator — SIOPV uses agent `.md` reports directly |
| `orchestrator-protocol/` | Multi-project orchestration for meta-project stage coordination |
| `techniques-reference/` | Meta-project techniques catalog — irrelevant to SIOPV coding |
| `new-project/` | Meta-project scaffolding — SIOPV already exists |
| `init-session/` | Meta-project session init — SIOPV uses `session-start.sh` hook |
| `run-tests/` | Superseded by `hooks/coverage-gate.sh` + `/verify` pipeline |
| `scan-vulnerabilities/` | SIOPV uses `cve-research` skill for CVE lookups (separate concern) |
| `trivy-integration/` | Trivy parsing already implemented in SIOPV Phase 1 |
| `xai-visualization/` | Covered by adapted `xai-explainer.md` agent |
| `cve-research/` | NOT excluded — but not listed in truth-00 skills dir. Remains available at `~/.claude/skills/` user level. No project-level copy needed. |

---

## 6. Skill Registration

Skills are **file-based** — no `settings.json` registration required (Skills 2.0 format per Round 1 §5).

- **Discovery:** Claude Code scans `.claude/skills/*/SKILL.md` at session start
- **Context budget:** Descriptions loaded at startup (2% budget, fallback 16K chars); full SKILL.md content loaded only on invocation
- **Live reload:** Skills edited during session are picked up without restart
- **Priority:** Enterprise > personal (`~/.claude/skills/`) > project (`.claude/skills/`) > plugin
  → SIOPV project skills override any user-level duplicates by name

**CLAUDE.md @-import NOT required** for skills — discovery is automatic. Only reference skills in CLAUDE.md when listing available `/commands` for user orientation.
