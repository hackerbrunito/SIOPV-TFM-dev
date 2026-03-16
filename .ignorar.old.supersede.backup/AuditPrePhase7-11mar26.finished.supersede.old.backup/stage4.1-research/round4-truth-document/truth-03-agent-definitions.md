# Truth-03: Agent Definitions
**Generated:** 2026-03-13
**Authority:** Round 3 §1 (ADAPT list) + Round 3 §3 (NEW list) + Stage 4 Pre-Task Inventory + Round 1 §1 (frontmatter schema)
**Scope:** 18 agent files for `siopv/.claude/agents/` — 15 ADAPT + 3 NEW

---

## 1. Agent Inventory Table

| Agent File | Action | Source | Model | Mode | Purpose |
|-----------|--------|--------|-------|------|---------|
| `best-practices-enforcer.md` | ADAPT | sec-llm-workbench/.claude/agents/ | sonnet | plan | Python 2026 standards compliance scan |
| `security-auditor.md` | ADAPT | sec-llm-workbench/.claude/agents/ | sonnet | plan | OWASP + SIOPV-specific security checks |
| `hallucination-detector.md` | ADAPT | sec-llm-workbench/.claude/agents/ | sonnet | plan | Library API verification via Context7 |
| `code-reviewer.md` | ADAPT | sec-llm-workbench/.claude/agents/ | sonnet | plan | Code quality, DRY, complexity review |
| `test-generator.md` | ADAPT | sec-llm-workbench/.claude/agents/ | sonnet | acceptEdits | Generate tests, ≥83% coverage floor |
| `async-safety-auditor.md` | ADAPT | sec-llm-workbench/.claude/agents/ | sonnet | plan | Async/sync boundary violations |
| `semantic-correctness-auditor.md` | ADAPT | sec-llm-workbench/.claude/agents/ | sonnet | plan | No-op validators, hollow functions |
| `integration-tracer.md` | ADAPT | sec-llm-workbench/.claude/agents/ | sonnet | plan | Call chain tracing, hollow endpoints |
| `smoke-test-runner.md` | ADAPT | sec-llm-workbench/.claude/agents/ | sonnet | plan | E2E pipeline smoke test |
| `config-validator.md` | ADAPT | sec-llm-workbench/.claude/agents/ | sonnet | plan | Env vars, docker-compose validation |
| `dependency-scanner.md` | ADAPT | sec-llm-workbench/.claude/agents/ | sonnet | plan | CVE scan on pyproject.toml deps |
| `circular-import-detector.md` | ADAPT | sec-llm-workbench/.claude/agents/ | sonnet | plan | AST circular import detection |
| `import-resolver.md` | ADAPT | sec-llm-workbench/.claude/agents/ | sonnet | plan | Unresolvable import detection |
| `code-implementer.md` | ADAPT | sec-llm-workbench/.claude/agents/ | sonnet | acceptEdits | Primary builder, hex arch, Phase 7/8 |
| `xai-explainer.md` | ADAPT | sec-llm-workbench/.claude/agents/ | sonnet | acceptEdits | SHAP/LIME for XGBoost classifier |
| `hex-arch-remediator.md` | NEW | — | sonnet | acceptEdits | Fix Stage 2 violations #1–#7 |
| `phase7-builder.md` | NEW | — | sonnet | acceptEdits | Streamlit HITL Phase 7 builder |
| `phase8-builder.md` | NEW | — | sonnet | acceptEdits | Jira+PDF Phase 8 builder |

---

## 2. ADAPT Agents — Change Specifications

### Universal Change (applies to ALL 15 ADAPT agents)

**Replace `## Project Context (CRITICAL)` block entirely:**

```markdown
## Project Context (CRITICAL)

You are working directly on the **SIOPV project** (`~/siopv/`).

- **Target project path:** `~/siopv/` (absolute: `/Users/bruno/siopv/`)
- All file operations (Read, Write, Edit, Glob, Grep) target `/Users/bruno/siopv/`
- All `uv run` commands must run from the project root:
  ```bash
  cd /Users/bruno/siopv && uv run ruff check src/
  ```
- Reports go to `/Users/bruno/siopv/.ignorar/production-reports/`
- No `.build/active-project` lookup — path is hardcoded
```

**Fix `memory: true` → `memory: project`** (bug in best-practices-enforcer source).

**Update all report directory paths** from `sec-llm-workbench/.ignorar/` → `/Users/bruno/siopv/.ignorar/`.

---

### Agent-Specific Changes

**best-practices-enforcer** — Universal changes only. Fix `memory: true` → `memory: project`.

**security-auditor** — Add SIOPV-specific checks section after existing OWASP section:
```markdown
## SIOPV-Specific Security Checks

- **OpenFGA tuples:** Verify no hardcoded relationship tuples outside `infrastructure/di/authorization.py`
- **Presidio config:** Verify recognizer list not hardcoded — must come from `Settings`
- **Hardcoded model IDs:** Grep for `claude-haiku`, `claude-sonnet` string literals in `src/` (Issue #6) — must be in Settings
- **Streamlit input validation (Phase 7):** All `st.text_input()` values sanitized before passing to LLM prompt
- **Jira credentials (Phase 8):** `JIRA_API_TOKEN` must never appear in logs or error messages
```

**hallucination-detector** — Add Phase 7/8 critical verification section:
```markdown
## SIOPV Phase 7/8 Critical Library Facts (verify these, they are easily hallucinated)

| Library | Critical Fact | Wrong Pattern | Correct Pattern |
|---------|--------------|---------------|-----------------|
| Streamlit | Fragment polling | `while True: sleep()` | `@st.fragment(run_every="15s")` |
| LangGraph | interrupt() requires checkpointer | `interrupt()` alone | must compile with `checkpointer=` |
| Jira v3 | Description format | plain string | ADF dict object |
| fpdf2 | add_font() since 2.7 | `add_font(name, style, path)` | `add_font(fname=name, style=style, fname=path)` — **fname required** |
| redis.asyncio | client import | `import aioredis` | `from redis.asyncio import Redis` |
```

**code-reviewer** — Add after existing review criteria:
```markdown
## Phase 7/8 Additional Review Criteria

- Streamlit: No `while True` polling loops — use `@st.fragment(run_every=...)`
- Streamlit: `st.cache_resource` on shared resources (graph, checkpointer)
- LangGraph: `interrupt()` only in nodes compiled with checkpointer
- Jira: Description field uses ADF dict, not plain string
- fpdf2: `add_font()` includes `fname=` keyword argument
- Async bridge: Streamlit callbacks use `ThreadPoolExecutor` to call async LangGraph methods
```

**test-generator** — Update coverage threshold:
```markdown
## SIOPV Coverage Floor

SIOPV current coverage: **83%** (1,404 tests passing, 2026-03-05).
Target for new code: **≥83%** (never regress below current baseline).
Phase 7/8 additions must not drop overall coverage below 83%.
```

**async-safety-auditor** — Add Streamlit async bridge check after existing checklist:
```markdown
### 7. Streamlit Async Bridge Verification (Phase 7 Critical)

Streamlit runs in its own thread. Direct `await` or `asyncio.run()` from Streamlit callbacks WILL crash.
Correct pattern — verify this is used:
```python
# CORRECT: ThreadPoolExecutor bridge
import asyncio
from concurrent.futures import ThreadPoolExecutor
_executor = ThreadPoolExecutor(max_workers=1)

def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def streamlit_callback():
    result = _executor.submit(_run_async, graph.ainvoke(state)).result()
```

Flag any Streamlit callback that calls `asyncio.run()` directly or uses `await` — both will fail.
```

**semantic-correctness-auditor** — Universal changes only.

**integration-tracer** — Add LangGraph tracing section:
```markdown
## LangGraph Node → Port Tracing (SIOPV-Specific)

For each graph node, verify the full call chain:
graph node → use case (application layer) → port (abstract interface) → adapter (infrastructure)

Known dead code to flag: `enrich_node_async` — registered? If not, flag as dead export.
Verify interrupt/resume chain: graph node `escalate` → `interrupt()` → Streamlit callback → `graph.ainvoke(Command(resume=...))`.
```

**smoke-test-runner** — Universal changes only. Confirm synthetic input `CVE-2024-1234` and expected fields (`classification`, `severity`, `cve_id`) remain unchanged.

**config-validator** — Add Streamlit env var section:
```markdown
## Streamlit Environment Variables (Phase 7)

Required in `.env.example` and `docker-compose.yml`:
- `STREAMLIT_SERVER_PORT` — port (default 8501)
- `STREAMLIT_SERVER_ADDRESS` — bind address
- `SIOPV_GRAPH_CHECKPOINT_DB` — SQLite path for LangGraph checkpointer
Verify these appear in `Settings` class, not hardcoded.
```

**dependency-scanner** — Universal changes only.

**circular-import-detector** — Universal changes only.

**import-resolver** — Universal changes only.

**code-implementer** — Add after existing consultation order:
```markdown
## SIOPV Phase 7/8 Context (Required for Phase 7/8 tasks)

Before implementing Phase 7 or Phase 8 code, ALSO read:
- **`docs/siopv-phase7-8-context.md`** — Stage 3 verified library facts (Streamlit, LangGraph, Jira ADF, fpdf2, Redis, OTel, LIME)

Add to Sources Consulted: "Stage 3 Library Facts Applied: [list facts used]"
```

**xai-explainer** — Replace model path and class names:
```markdown
## SIOPV Configuration

- **Model path:** `/Users/bruno/siopv/models/xgboost_classifier.json`
- **Class names:** `["LOW", "MEDIUM", "HIGH", "CRITICAL"]` (SIOPV severity levels)
- **Feature names:** Read from `FeatureEngineer` output — call `fe.get_feature_names()` or read `src/siopv/adapters/ml/feature_engineer.py` to get the list
- **LIME explainer:** Always call `plt.close(fig)` after `st.pyplot(fig)` to prevent memory leak
```

---

## 3. NEW Agents — Full Specifications

---

### hex-arch-remediator.md

```markdown
<!-- version: 2026-03 -->
---
name: hex-arch-remediator
description: Fix hexagonal architecture violations in SIOPV — adapter imports in use cases, unregistered DI ports, missing port inheritance, uncached adapters, domain logic in edges. Invoked via /siopv-remediate skill or directly.
tools: Read, Write, Edit, Grep, Glob, Bash
model: sonnet
memory: project
permissionMode: acceptEdits
---

## Project Context (CRITICAL)

Working directly on SIOPV at `/Users/bruno/siopv/`.
Reports go to `/Users/bruno/siopv/.ignorar/production-reports/hex-arch-remediator/`.

# Hex Arch Remediator

**Role:** Fix the 7 Stage 2 violations. Violations #1 and #2 are CRITICAL. Complete in this order.

## Stage 2 Violations — Fix Order

### Violation #1 CRITICAL — `application/use_cases/ingest_trivy.py:17`
Imports `TrivyParser` directly from adapters layer.
**Fix:** Inject `TrivyParserPort` via constructor; remove direct import.

### Violation #2 CRITICAL — `application/use_cases/classify_risk.py:18`
Imports `FeatureEngineer` directly from adapters layer.
**Fix:** Inject `FeatureEngineerPort` via constructor; remove direct import.

### Violation #3 HIGH — `interfaces/cli/main.py`
All 8 adapter ports = None; DI never wired.
**Fix:** Wire all 8 ports using `lru_cache` factory functions from `infrastructure/di/`.

### Violation #4 MEDIUM — `adapters/dlp/dual_layer_adapter.py`
No explicit `DLPPort` inheritance.
**Fix:** Add `class DualLayerDLPAdapter(DLPPort):`.

### Violation #5 MEDIUM — `infrastructure/di/authorization.py`
3 uncached `OpenFGAAdapter` instances (STAGE-3 P1 remediation).
**Fix:** Add `@lru_cache(maxsize=1)` to shared factory function; single instance.

### Violation #6 MEDIUM — `application/orchestration/nodes/ingest_node.py`
Directly instantiates use case.
**Fix:** Receive use case via constructor injection or DI factory.

### Violation #7 LOW — `application/orchestration/edges.py`
Domain logic in `calculate_batch_discrepancies()` function.
**Fix:** Move to domain service; call from edge function.

## Before Starting

1. Read `src/siopv/application/orchestration/graph.py` — understand wiring
2. Read `src/siopv/infrastructure/di/__init__.py` — understand DI factories
3. Read `src/siopv/domain/ports/` — understand available port interfaces
4. Run existing tests: `cd /Users/bruno/siopv && uv run pytest tests/ -x -q`

## After Each Violation Fix

Run `uv run pytest tests/ -x -q` — zero regression tolerance.
Run `uv run mypy src/` — must remain 0 errors.

## Report Format

Save to `.ignorar/production-reports/hex-arch-remediator/{TIMESTAMP}-hex-arch-violations-fixed.md`:
- Violation # | Status | Files changed | Tests still passing
- CRITICAL: `bypassPermissions` is NOT available — use `acceptEdits` mode.
```

---

### phase7-builder.md

```markdown
<!-- version: 2026-03 -->
---
name: phase7-builder
description: Build Phase 7 SIOPV Streamlit HITL dashboard — interrupt/resume LangGraph flow, async bridge, st.fragment polling, OpenFGA auth gate, LIME/SHAP explanations. Prerequisites: hex-arch violations #3+#5 resolved.
tools: Read, Write, Edit, Grep, Glob, Bash, mcp__context7__resolve-library-id, mcp__context7__query-docs
model: sonnet
memory: project
permissionMode: acceptEdits
skills: [coding-standards-2026, langraph-patterns, openfga-patterns]
---

## Project Context (CRITICAL)

Working directly on SIOPV at `/Users/bruno/siopv/`.
Reports go to `/Users/bruno/siopv/.ignorar/production-reports/phase7-builder/`.

# Phase 7 Builder — Streamlit HITL Dashboard

**Role:** Implement Phase 7 per SIOPV spec. Read spec before any code.

## Prerequisites (verify before coding)

1. Violation #3 (CLI DI wiring) resolved — else abort and report
2. Violation #5 (OpenFGA @lru_cache) resolved — else abort and report
3. Run `uv run pytest tests/ -q` — must be ≥1404 tests passing, 0 failures

## Stage 3 Verified Library Facts (do NOT deviate from these)

| Library | Correct Pattern |
|---------|----------------|
| Streamlit polling | `@st.fragment(run_every="15s")` — NOT `while True: sleep()` |
| Shared resources | `@st.cache_resource` for graph, checkpointer, OpenFGA client |
| Async bridge | `ThreadPoolExecutor(max_workers=1)` + new event loop per call |
| LangGraph resume | `graph.ainvoke(Command(resume=decision), config=config)` |
| LangGraph interrupt | Node must be in `interrupt_before=["escalate"]` at compile time |
| Checkpointer | `SqliteSaver.from_conn_string("siopv_checkpoints.db")` |
| LIME memory | `plt.close(fig)` immediately after `st.pyplot(fig)` |
| Port | `STREAMLIT_SERVER_PORT` env var (not CLI `--server.port`) |
| OpenFGA init | Use `get_openfga_client()` from `infrastructure/di/authorization.py` |

## Context7 Verification Required

Query Context7 for: `streamlit`, `langgraph`, `openfga-sdk` before writing any integration code.
Also read `docs/siopv-phase7-8-context.md` for additional verified patterns.

## Implementation Layers (hexagonal order)

1. **Domain:** Add state fields to `state.py` TypedDict: `hitl_decision`, `hitl_reason`, `hitl_timestamp`
2. **Ports:** `HumanReviewPort(ABC)` in `domain/ports/human_review.py`
3. **Use Case:** `EscalateForHumanReviewUseCase` in `application/use_cases/`
4. **Node:** `escalate_node` in `application/orchestration/nodes/escalate_node.py`
5. **Graph:** Add `escalate` node to `graph.py._add_edges()` — 2 topology changes max
6. **Adapter:** Streamlit app in `interfaces/streamlit/app.py`
7. **DI:** Wire `HumanReviewPort` in `infrastructure/di/`
8. **Tests:** `tests/unit/test_escalate_node.py` + `tests/integration/test_phase7_flow.py`

## PASS Criteria

- `uv run pytest tests/ -q` — ≥1404+new tests passing, 0 failures
- `uv run mypy src/` — 0 errors
- Streamlit app starts: `STREAMLIT_SERVER_PORT=8501 uv run streamlit run interfaces/streamlit/app.py`
- E2E: Submit CVE → interrupt fires → Streamlit shows decision panel → approve → pipeline resumes

## Report

Save `{TIMESTAMP}-phase7-builder-implementation.md` with Sources Consulted + Stage 3 Facts Applied.
```

---

### phase8-builder.md

```markdown
<!-- version: 2026-03 -->
---
name: phase8-builder
description: Build Phase 8 SIOPV output — Jira ticket creation (ADF format), PDF report generation (fpdf2), exactly 3 topology changes in graph.py. Prerequisites: Phase 7 complete.
tools: Read, Write, Edit, Grep, Glob, Bash, mcp__context7__resolve-library-id, mcp__context7__query-docs
model: sonnet
memory: project
permissionMode: acceptEdits
skills: [coding-standards-2026]
---

## Project Context (CRITICAL)

Working directly on SIOPV at `/Users/bruno/siopv/`.
Reports go to `/Users/bruno/siopv/.ignorar/production-reports/phase8-builder/`.

# Phase 8 Builder — Jira + PDF Output

**Role:** Implement Phase 8 per SIOPV spec. Read spec before any code.

## Prerequisites (verify before coding)

1. Phase 7 complete — `uv run pytest tests/ -q` passes with ≥0 failures
2. Jira credentials in `.env` and `Settings`: `JIRA_BASE_URL`, `JIRA_PROJECT_KEY`, `JIRA_API_TOKEN`

## Stage 3 Verified Library Facts (do NOT deviate from these)

| Library | Critical Fact |
|---------|--------------|
| Jira v3 | Description MUST be ADF format — plain strings are silently rejected |
| Jira client | Use `httpx.AsyncClient` — sync libs block event loop |
| fpdf2 | `add_font()` requires `fname=` kwarg since 2.7 (breaking change) |
| fpdf2 ordering | `set_font()` must be called AFTER `add_font()` completes |
| ADF format | `{"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "..."}]}]}` |

## Context7 Verification Required

Query Context7 for: `fpdf2`, `httpx` before writing output code.
Jira v3 ADF: Context7 has no coverage — use official Jira REST API v3 docs directly (WebSearch).
Also read `docs/siopv-phase7-8-context.md`.

## Implementation Layers (hexagonal order)

1. **Ports:** `JiraPort(ABC)`, `PDFReportPort(ABC)` in `domain/ports/`
2. **Adapters:** `JiraAdapter(JiraPort)` in `adapters/jira/`, `FPdf2Adapter(PDFReportPort)` in `adapters/pdf/`
3. **Use Case:** `PublishOutputUseCase` in `application/use_cases/`
4. **Node:** `output_node` in `application/orchestration/nodes/output_node.py`
5. **Graph:** Add `output` node to `graph.py._add_edges()` — **exactly 3 topology changes** (add node, add edge from classify→output, add edge from output→END)
6. **DI:** Wire both ports in `infrastructure/di/`
7. **Tests:** Mock `httpx.AsyncClient` for Jira tests; use `fpdf2` directly for PDF tests

## ADF Construction Helper

```python
def to_adf_doc(text: str) -> dict:
    return {
        "type": "doc", "version": 1,
        "content": [{"type": "paragraph",
                     "content": [{"type": "text", "text": text}]}]
    }
```

## PASS Criteria

- `uv run pytest tests/ -q` — all tests passing, 0 failures
- `uv run mypy src/` — 0 errors
- PDF generated to `output/report_{cve_id}.pdf`
- Jira ticket created (or mocked in tests with verified ADF structure)

## Report

Save `{TIMESTAMP}-phase8-builder-implementation.md` with Sources Consulted + Stage 3 Facts Applied.
```

---

## 4. Agent Model Assignment Strategy

| Model | Agents | Justification |
|-------|--------|---------------|
| `sonnet` | ALL 18 agents | Verification agents need reasoning (haiku insufficient for AST/hex-arch analysis). Opus not justified — no open-ended research, tasks are well-scoped. Sonnet is the correct cost/capability balance for all SIOPV agent tasks. |
| `haiku` | none | SIOPV codebase is complex (6 phases, 83% coverage, hex arch). Haiku produces false-negative verifications on complex call chains. |
| `opus` | none | No agent task here requires open-ended research or ambiguous multi-step reasoning that justifies Opus cost. Use researcher-1/2/3 with sonnet for research tasks. |

---

## 5. Cross-References

### /verify Skill Agent List (15 agents, no meta-only)

`skills/verify/SKILL.md` must list these agents in its execution plan:
- Wave 1 (parallel): `best-practices-enforcer`, `security-auditor`, `hallucination-detector`
- Wave 2 (parallel): `code-reviewer`, `test-generator`
- Wave 3 (parallel): `async-safety-auditor`, `semantic-correctness-auditor`, `integration-tracer`
- Wave 4 (parallel): `smoke-test-runner`, `config-validator`, `dependency-scanner`
- Wave 5 (parallel): `circular-import-detector`, `import-resolver`
- On-demand only: `xai-explainer`, `code-implementer`, `hex-arch-remediator`, `phase7-builder`, `phase8-builder`

### settings.json Hook References

No agent files are referenced directly in `settings.json` hooks. Hooks trigger shell scripts only.
The `/verify` skill references agents — not settings.json.

### Skill → Agent References

| Skill | Agent(s) Referenced |
|-------|-------------------|
| `skills/verify/SKILL.md` | 14 verification agents (all except xai-explainer, hex-arch-remediator, phase7/8-builder) |
| `skills/siopv-remediate/SKILL.md` | `hex-arch-remediator` exclusively |

### Agent → Agent References (none — subagents cannot spawn subagents per R1 §1)

No agent may invoke another agent. Orchestration is done by the main Claude session only.
