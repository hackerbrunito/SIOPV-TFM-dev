# SIOPV Remediation-Hardening — Orchestrator Execution Guidelines

**Produced by:** Opus orchestrator (2026-03-15)
**Source:** `AuditPrePhase7-11mar26/orchestrator-input-brief.md`
**Project root:** `/Users/bruno/siopv/`

---

## 1. Scope

### Closed Decisions (do not re-open)

| Item | Decision | Reason |
|------|----------|--------|
| LLM confidence stub (`adapters/llm/__init__.py` empty) | **DEFER to Phase 7** | Requires real Claude Sonnet adapter — Phase 7/8 builders own this |
| Phase 2 adapter tests (NVD, EPSS, GitHub, Tavily, ChromaDB at 0–20%) | **INCLUDE** in Round 5 | Adapters are frozen; Phase 7/8 builders shouldn't inherit this gap |
| `SanitizeVulnerabilityUseCase` | **DELETE** (confirmed orphaned) | Only referenced by its own test file — never imported by any production code |
| Phase 7/8 features | **NOT touched** | Phase 7/8 builders own all new feature work |

### Out of Scope

- No new features, no Phase 7/8 work
- No changes to files not listed in the File Ownership Map (Section 3)
- No changes to the audit files in `AuditPrePhase7-11mar26/`
- No dependency upgrades

### Stale Items Confirmed by Code Review

| Briefing Item | Status | Evidence |
|---------------|--------|----------|
| Known #7: "asyncio.run() in sync nodes" | **STALE — no fix needed** | All nodes (`dlp_node`, `enrich_node`, `authorization_node`) are `async def` using `await`. Zero `asyncio.run()` calls in any node. Only `cli/main.py:87` uses `asyncio.run()`, which is the correct CLI sync→async boundary. |
| Known #4: "run_pipeline() drops enrichment clients (graph.py:439-444)" | **STALE — wiring correct** | `run_pipeline()` passes all 5 enrichment clients to `PipelineGraphBuilder` (lines 456-466). `_add_nodes()` wires them into the `_enrich_node` closure (lines 195-205). Clients reach `enrich_node` correctly. |
| Known #5: "DLP DI not exported" | **STALE — already exported** | `infrastructure/di/__init__.py` already imports and exports `get_dlp_port` and `get_dual_layer_dlp_port` (lines 46-49, 57-58). |

Workers assigned to stale items must still **verify** current state, report the finding, and produce a no-op report. They must NOT invent fixes.

---

## 2. Core Rules

### Rule 1 — One file, one worker, one pass
Every file in the codebase is assigned to exactly one worker for the entire remediation. No file appears in two worker assignments. If a file has multiple issues, all are fixed in a single read-fix-verify pass by the same worker.

### Rule 2 — Universal worker protocol (applies to every worker, every round)
1. Read the assigned briefing section (issues for their files)
2. Read the complete content of each assigned file
3. Compare: confirm each issue exists as described
4. If issue confirmed → implement fix
5. If issue NOT found (stale/already fixed) → stop, report to orchestrator, do not touch
6. Run: `ruff format`, `ruff check`, `mypy src` on modified files
7. Run affected tests: `pytest tests/ -x -q --tb=short`
8. Save report to `.ignorar/production-reports/remediation/{TIMESTAMP}-{slug}.md`
9. Report pass/fail to orchestrator

### Rule 3 — Escalate ambiguity, never guess
If the correct fix approach is unclear after reading the file → stop → report to orchestrator → wait for guidance. Never infer. Never guess.

### Rule 4 — No scope creep
Workers fix only their assigned issues. If they notice other problems → document in report → do not fix unless explicitly assigned.

---

## 3. File Ownership Map

**IMPORTANT:** Ports live in `src/siopv/application/ports/`, NOT `src/siopv/domain/ports/`. There is no `domain/ports/` directory. All new port files must be created under `application/ports/`.

| Worker slug | Model | Files owned (relative to `src/siopv/`) | Issues | Round |
|-------------|-------|----------------------------------------|--------|-------|
| `fix-di-auth` | Sonnet | `infrastructure/di/authorization.py` | Hex #5: add `@lru_cache(maxsize=1)` to `create_authorization_adapter` so 3 port functions share one `OpenFGAAdapter` instance | 1 |
| `fix-logging` | Sonnet | `infrastructure/logging/setup.py` | Known #9: replace deprecated `structlog.processors.format_exc_info` with `structlog.processors.ExceptionRenderer()` | 1 |
| `fix-sanitize` | Haiku | `application/use_cases/sanitize_vulnerability.py` + `tests/unit/application/test_sanitize_vulnerability.py` | Known #2: delete both files (confirmed orphaned — only self-referencing imports) | 1 |
| `fix-haiku-dlp` | Sonnet | `adapters/dlp/haiku_validator.py` + `adapters/dlp/_haiku_utils.py` + `adapters/dlp/presidio_adapter.py` | Known #6: remove hardcoded `"claude-haiku-4-5-20251001"` defaults — callers must provide model explicitly | 1 |
| `fix-ports-ingest` | Sonnet | `application/use_cases/ingest_trivy.py` + `application/ports/parsing.py` (NEW) | Hex #1: create `TrivyParserPort` Protocol, inject via constructor instead of direct adapter import | 2 |
| `fix-ports-classify` | Sonnet | `application/use_cases/classify_risk.py` + `application/ports/feature_engineering.py` (NEW) | Hex #2: create `FeatureEngineerPort` Protocol, inject via constructor instead of direct adapter import | 2 |
| `fix-dlp-port` | Sonnet | `adapters/dlp/dual_layer_adapter.py` | Hex #4: add explicit `DLPPort` inheritance to `DualLayerDLPAdapter` class | 2 |
| `fix-di-exports` | Haiku | `infrastructure/di/__init__.py` | Known #5: VERIFY ONLY — already exported. Produce no-op report. | 2 |
| `fix-edges` | **Opus** | `application/orchestration/edges.py` + `domain/services/discrepancy.py` (NEW) | Hex #7: move discrepancy logic to new domain service; requires architectural judgment | 2 |
| `fix-ingest-node` | Sonnet | `application/orchestration/nodes/ingest_node.py` | Hex #6: accept use case as parameter instead of instantiating directly; wire via DI | 3 |
| `fix-enrich-node` | Sonnet | `application/orchestration/nodes/enrich_node.py` | Remove dead `enrich_node_async` (lines 190-258); verify async pattern (expected no-op) | 3 |
| `fix-async-nodes` | Haiku | `application/orchestration/nodes/dlp_node.py` + `authorization_node.py` | Verify async pattern (Known #7 — expected no-op); report findings | 3 |
| `fix-graph` | Haiku | `application/orchestration/graph.py` | Known #4: verify enrichment client wiring (expected no-op); report findings | 3 |
| `fix-cli` | **Opus** | `interfaces/cli/main.py` | Hex #3 + Known #1: wire all adapter ports via DI; highest-risk task | 4 |
| `fix-adapter-tests` | Sonnet | Test files only (new files under `tests/unit/adapters/`) | Known #8: write unit tests for 5 Phase 2 adapters | 5 |

---

## 4. Round Structure with Dependency Rationale

```
Round 1 (parallel — no inter-dependencies)
├── fix-di-auth        → infrastructure/di/authorization.py
├── fix-logging        → infrastructure/logging/setup.py
├── fix-sanitize       → sanitize_vulnerability.py + test (DELETE)
└── fix-haiku-dlp      → 3 DLP adapter files

Round 2 (parallel — depends on Round 1 complete)
├── fix-ports-ingest   → ingest_trivy.py + NEW port file
├── fix-ports-classify → classify_risk.py + NEW port file
├── fix-dlp-port       → dual_layer_adapter.py
├── fix-di-exports     → di/__init__.py (verify-only)
└── fix-edges          → edges.py + NEW domain service

Round 3 (parallel — depends on Round 2 complete)
├── fix-ingest-node    → ingest_node.py
├── fix-enrich-node    → enrich_node.py (dead code removal)
├── fix-async-nodes    → dlp_node.py + authorization_node.py (verify)
└── fix-graph          → graph.py (verify)

Round 4 (single — depends on Round 3 complete)
└── fix-cli            → cli/main.py (needs ALL DI correct)

Round 5 (parallel — after Round 4)
└── fix-adapter-tests  → 5 test campaigns (can split to 5 sub-workers)

Round 6 — Verification
└── Full /verify (14 agents, 83% coverage floor)
    ruff format && ruff check && mypy src
    pytest --cov=src --cov-fail-under=83
```

### Dependency Rationale

| Dependency | Why |
|------------|-----|
| R1 before R2 | `fix-di-auth` adds `@lru_cache` to `create_authorization_adapter` — R2 workers creating DI-related ports should see the corrected singleton pattern. `fix-haiku-dlp` cleans hardcoded model IDs before `fix-dlp-port` adds explicit `DLPPort` inheritance. |
| R2 before R3 | `fix-ports-ingest` creates the `TrivyParserPort` that `fix-ingest-node` will use for DI injection. `fix-ports-classify` creates the `FeatureEngineerPort`. `fix-di-exports` confirms DI exports exist before nodes wire through them. |
| R3 before R4 | `fix-cli` must read `di/__init__.py` for all available DI functions after R2-R3 corrections are complete. All ports and DI must be stable. |
| R4 before R5 | Adapter tests are independent of DI wiring but run last so blocking issues are resolved first. |

### Validated: No dependency gaps found

- `fix-edges` (R2) creates a new domain service file — no downstream worker modifies it.
- `fix-ports-ingest` and `fix-ports-classify` (R2) each create their own new port file — no overlap.
- `fix-enrich-node` (R3) only deletes dead code and verifies — no dependency on other R3 workers.
- `fix-graph` (R3) is verify-only — no file changes expected.

---

## 5. Per-Worker Specifications

**Mode:** `acceptEdits` (all workers)
**Report path:** `.ignorar/production-reports/remediation/{TIMESTAMP}-{worker-slug}.md`

### Model Selection Strategy (cost-effective assignment)

| Tier | Model | Criteria | Workers |
|------|-------|----------|---------|
| **Haiku** | `claude-haiku-4-5-20251001` | Purely mechanical: delete files, verify-only no-ops, grep-and-report. Zero architectural judgment. | `fix-sanitize`, `fix-di-exports`, `fix-async-nodes`, `fix-graph` |
| **Sonnet** | `claude-sonnet-4-6` | Standard dev: read file, confirm issue, implement targeted fix, run verification. Default tier. | `fix-di-auth`, `fix-logging`, `fix-haiku-dlp`, `fix-dlp-port`, `fix-enrich-node`, `fix-ingest-node`, `fix-ports-ingest`, `fix-ports-classify`, `fix-adapter-tests` |
| **Opus** | `claude-opus-4-6` | Architectural judgment: deciding WHERE to place domain logic, designing module boundaries, or high-risk multi-port wiring. | `fix-edges`, `fix-cli` |

---

### 5.1 `fix-di-auth` (Round 1) — Model: `claude-sonnet-4-6`

**Prompt:**
```
You are a remediation worker. Your task is to fix the OpenFGA DI singleton issue.

ISSUE: Hex #5 — `infrastructure/di/authorization.py` has 3 port factory functions
(`get_authorization_port`, `get_authorization_store_port`, `get_authorization_model_port`)
each decorated with `@lru_cache(maxsize=1)`. However, each calls
`create_authorization_adapter(settings)` which is NOT cached, creating 3 separate
OpenFGAAdapter instances instead of sharing one.

FIX:
1. Add `@lru_cache(maxsize=1)` decorator to `create_authorization_adapter()`
2. This ensures all 3 port functions return the same underlying adapter instance

FILES TO READ:
- src/siopv/infrastructure/di/authorization.py (full file)

VERIFICATION:
1. ruff format src/siopv/infrastructure/di/authorization.py
2. ruff check src/siopv/infrastructure/di/authorization.py
3. mypy src/siopv/infrastructure/di/authorization.py
4. pytest tests/unit/infrastructure/ -x -q --tb=short
5. Confirm `create_authorization_adapter` now has `@lru_cache(maxsize=1)`

Save report to: .ignorar/production-reports/remediation/{TIMESTAMP}-fix-di-auth.md
```

**Files to read:** `src/siopv/infrastructure/di/authorization.py`
**Fix:** Add `@lru_cache(maxsize=1)` decorator to `create_authorization_adapter()` function (before line 52)
**Verification:** ruff format + ruff check + mypy on file; pytest on infrastructure tests

---

### 5.2 `fix-logging` (Round 1) — Model: `claude-sonnet-4-6`

**Prompt:**
```
You are a remediation worker. Your task is to fix the structlog deprecation warning.

ISSUE: Known #9 — `infrastructure/logging/setup.py` line 31 uses
`structlog.processors.format_exc_info` which is deprecated and emits a warning
on every test run.

FIX:
1. Replace `structlog.processors.format_exc_info` (line 31) with
   `structlog.processors.ExceptionRenderer()`
2. Do NOT change any other processor or logging configuration

IMPORTANT: Before implementing, verify the current structlog API. Use Context7 MCP
to check `structlog` docs for the correct replacement for `format_exc_info`.
If `ExceptionRenderer` is not the correct replacement, escalate to orchestrator.

FILES TO READ:
- src/siopv/infrastructure/logging/setup.py (full file)

VERIFICATION:
1. ruff format src/siopv/infrastructure/logging/setup.py
2. ruff check src/siopv/infrastructure/logging/setup.py
3. mypy src/siopv/infrastructure/logging/setup.py
4. pytest tests/unit/infrastructure/ -x -q --tb=short
5. Confirm the deprecation warning no longer appears in test output

Save report to: .ignorar/production-reports/remediation/{TIMESTAMP}-fix-logging.md
```

**Files to read:** `src/siopv/infrastructure/logging/setup.py`
**Fix:** Replace `structlog.processors.format_exc_info` with the current non-deprecated equivalent (likely `structlog.processors.ExceptionRenderer()`)
**Verification:** ruff + mypy on file; run pytest and confirm no deprecation warning

---

### 5.3 `fix-sanitize` (Round 1) — Model: `claude-haiku-4-5-20251001`

**Rationale:** Purely mechanical — delete 2 confirmed-orphaned files and remove any re-exports. No judgment needed.

**Prompt:**
```
You are a remediation worker. Your task is to delete orphaned files.

ISSUE: Known #2 — `SanitizeVulnerabilityUseCase` is orphaned. It is never imported
or called by any production code. The `dlp_node` is the real DLP execution path.

FIX:
1. Delete `src/siopv/application/use_cases/sanitize_vulnerability.py`
2. Delete `tests/unit/application/test_sanitize_vulnerability.py`
3. Verify no imports of `SanitizeVulnerabilityUseCase` remain in any production file
   (grep the entire src/ directory)
4. Check if `application/use_cases/__init__.py` re-exports this class — if so, remove
   the re-export

FILES TO READ:
- src/siopv/application/use_cases/sanitize_vulnerability.py (confirm it's the orphan)
- tests/unit/application/test_sanitize_vulnerability.py (confirm it's the test)
- src/siopv/application/use_cases/__init__.py (check for re-exports)

VERIFICATION:
1. grep -r "SanitizeVulnerabilityUseCase" src/ — must return 0 results
2. grep -r "sanitize_vulnerability" src/ — must return 0 results
3. ruff check src/siopv/application/use_cases/
4. mypy src/siopv/application/use_cases/
5. pytest tests/unit/application/ -x -q --tb=short (remaining tests must pass)

Save report to: .ignorar/production-reports/remediation/{TIMESTAMP}-fix-sanitize.md
```

**Files to read:** Both files listed above + `application/use_cases/__init__.py`
**Fix:** Delete both files; remove any re-exports
**Verification:** grep to confirm no remaining references; ruff + mypy; pytest

---

### 5.4 `fix-haiku-dlp` (Round 1) — Model: `claude-sonnet-4-6`

**Prompt:**
```
You are a remediation worker. Your task is to remove hardcoded Haiku model IDs
from DLP adapter files.

ISSUE: Known #6 — Three DLP adapter files have hardcoded default parameter
`"claude-haiku-4-5-20251001"` as the model ID. The settings already has
`claude_haiku_model` in `infrastructure/config/settings.py` line 33, and the
DI layer (`infrastructure/di/dlp.py`) already reads from settings and passes it.
The problem is only in the adapter constructors' default values.

FIX — for each file, remove the hardcoded default so callers MUST provide the model:
1. `adapters/dlp/haiku_validator.py` line 63: Change
   `model: str = "claude-haiku-4-5-20251001"` to `model: str` (no default)
2. `adapters/dlp/dual_layer_adapter.py` line 79: Change `_HaikuDLPAdapter.__init__`
   `model: str = "claude-haiku-4-5-20251001"` to `model: str` (no default)
3. `adapters/dlp/dual_layer_adapter.py` line 281: Change `create_dual_layer_adapter`
   `haiku_model: str = "claude-haiku-4-5-20251001"` to `haiku_model: str` (no default)
4. `adapters/dlp/presidio_adapter.py` line 232: Change
   `haiku_model: str = "claude-haiku-4-5-20251001"` to `haiku_model: str` (no default)
5. Update any tests that rely on the default parameter — they must now pass the model
   explicitly. Check test files:
   - tests/unit/adapters/dlp/test_haiku_validator.py
   - tests/unit/adapters/dlp/test_dual_layer_adapter.py
   - Any other test file that instantiates these classes

IMPORTANT: Do NOT touch `infrastructure/di/dlp.py` or `infrastructure/config/settings.py` —
those are not your files and they already handle this correctly.

FILES TO READ:
- src/siopv/adapters/dlp/haiku_validator.py
- src/siopv/adapters/dlp/_haiku_utils.py
- src/siopv/adapters/dlp/presidio_adapter.py
- src/siopv/adapters/dlp/dual_layer_adapter.py
- tests/unit/adapters/dlp/test_haiku_validator.py
- tests/unit/adapters/dlp/test_dual_layer_adapter.py

VERIFICATION:
1. grep -r "claude-haiku-4-5-20251001" src/siopv/adapters/dlp/ — must return 0 results
2. ruff format src/siopv/adapters/dlp/
3. ruff check src/siopv/adapters/dlp/
4. mypy src/siopv/adapters/dlp/
5. pytest tests/unit/adapters/dlp/ -x -q --tb=short

Save report to: .ignorar/production-reports/remediation/{TIMESTAMP}-fix-haiku-dlp.md
```

**Files to read:** All 4 adapter files + 2 test files listed above
**Fix:** Remove hardcoded default `"claude-haiku-4-5-20251001"` from all constructor/factory defaults; update tests
**Verification:** grep for hardcoded ID returns 0; ruff + mypy; DLP tests pass

---

### 5.5 `fix-ports-ingest` (Round 2) — Model: `claude-sonnet-4-6`

**Prompt:**
```
You are a remediation worker. Your task is to fix a hexagonal architecture violation.

ISSUE: Hex #1 — `application/use_cases/ingest_trivy.py` line 17 imports `TrivyParser`
directly from `siopv.adapters.external_apis.trivy_parser`. This violates hexagonal
architecture: use cases must depend on ports, not adapters.

IMPORTANT: Ports in this project live under `src/siopv/application/ports/`, NOT
`src/siopv/domain/ports/`. Check existing ports in `application/ports/__init__.py`
for the pattern to follow.

FIX:
1. Create `src/siopv/application/ports/parsing.py` with a `TrivyParserPort` Protocol:
   - Method `parse_file(path: Path) -> list[VulnerabilityRecord]`
   - Method `parse_dict(data: dict[str, object]) -> list[VulnerabilityRecord]`
   - Properties: `parsed_count: int`, `skipped_count: int`
   - Use `@runtime_checkable` Protocol (same pattern as `DLPPort` in `application/ports/dlp.py`)
2. Update `application/ports/__init__.py` to export `TrivyParserPort`
3. Modify `IngestTrivyReportUseCase.__init__()` to accept `parser: TrivyParserPort`
   as a constructor parameter instead of creating `TrivyParser()` internally
4. Update `ingest_trivy_report()` convenience function to accept an optional
   `parser` parameter (for backwards compatibility, can default to None and
   import TrivyParser locally only in that convenience function)
5. Remove the `from siopv.adapters.external_apis.trivy_parser import TrivyParser`
   line from the module-level imports of ingest_trivy.py

FILES TO READ:
- src/siopv/application/use_cases/ingest_trivy.py (full file)
- src/siopv/application/ports/__init__.py (export pattern)
- src/siopv/application/ports/dlp.py (Protocol pattern reference)
- src/siopv/adapters/external_apis/trivy_parser.py (understand TrivyParser interface)

VERIFICATION:
1. grep "from siopv.adapters" src/siopv/application/use_cases/ingest_trivy.py — must return 0
2. ruff format src/siopv/application/use_cases/ingest_trivy.py src/siopv/application/ports/parsing.py
3. ruff check src/siopv/application/use_cases/ src/siopv/application/ports/
4. mypy src/siopv/application/use_cases/ingest_trivy.py src/siopv/application/ports/parsing.py
5. pytest tests/unit/application/ -x -q --tb=short

Save report to: .ignorar/production-reports/remediation/{TIMESTAMP}-fix-ports-ingest.md
```

**Files to read:** Listed above
**Fix:** Create `TrivyParserPort` Protocol; inject via constructor; remove adapter import
**Verification:** grep confirms no adapter import; ruff + mypy; tests pass

---

### 5.6 `fix-ports-classify` (Round 2) — Model: `claude-sonnet-4-6`

**Prompt:**
```
You are a remediation worker. Your task is to fix a hexagonal architecture violation.

ISSUE: Hex #2 — `application/use_cases/classify_risk.py` line 18 imports
`FeatureEngineer` directly from `siopv.adapters.ml.feature_engineer`. This violates
hexagonal architecture: use cases must depend on ports, not adapters.

IMPORTANT: Ports in this project live under `src/siopv/application/ports/`, NOT
`src/siopv/domain/ports/`. Follow the Protocol pattern from `application/ports/dlp.py`.

FIX:
1. Create `src/siopv/application/ports/feature_engineering.py` with a
   `FeatureEngineerPort` Protocol:
   - Method `extract_features(vulnerability: VulnerabilityRecord, enrichment: EnrichmentData) -> MLFeatureVector`
   - Use `@runtime_checkable` Protocol
   - Use TYPE_CHECKING guard for domain imports
2. Update `application/ports/__init__.py` to export `FeatureEngineerPort`
3. Modify `ClassifyRiskUseCase.__init__()`:
   - Change `feature_engineer: FeatureEngineer | None = None` to
     `feature_engineer: FeatureEngineerPort | None = None`
   - Remove the fallback `or FeatureEngineer()` — require explicit injection
   - Move the import under TYPE_CHECKING
4. Update `create_classify_risk_use_case()` factory similarly
5. Remove the `from siopv.adapters.ml.feature_engineer import FeatureEngineer`
   line from module-level imports

FILES TO READ:
- src/siopv/application/use_cases/classify_risk.py (full file)
- src/siopv/application/ports/__init__.py (export pattern)
- src/siopv/application/ports/dlp.py (Protocol pattern reference)
- src/siopv/adapters/ml/feature_engineer.py (understand FeatureEngineer interface)

VERIFICATION:
1. grep "from siopv.adapters" src/siopv/application/use_cases/classify_risk.py — must return 0
2. ruff format src/siopv/application/use_cases/classify_risk.py src/siopv/application/ports/feature_engineering.py
3. ruff check src/siopv/application/use_cases/ src/siopv/application/ports/
4. mypy src/siopv/application/use_cases/classify_risk.py src/siopv/application/ports/feature_engineering.py
5. pytest tests/unit/application/ -x -q --tb=short

Save report to: .ignorar/production-reports/remediation/{TIMESTAMP}-fix-ports-classify.md
```

**Files to read:** Listed above
**Fix:** Create `FeatureEngineerPort` Protocol; inject via constructor; remove adapter import
**Verification:** grep confirms no adapter import; ruff + mypy; tests pass

---

### 5.7 `fix-dlp-port` (Round 2) — Model: `claude-sonnet-4-6`

**Prompt:**
```
You are a remediation worker. Your task is to fix a hexagonal architecture violation.

ISSUE: Hex #4 — `DualLayerDLPAdapter` in `adapters/dlp/dual_layer_adapter.py` does not
explicitly inherit from `DLPPort`. It relies on structural subtyping (Protocol) which
works at runtime but is not explicit for maintainability and `isinstance` checks.

FIX:
1. Add explicit `DLPPort` import (not under TYPE_CHECKING — needed at runtime for inheritance)
2. Change class declaration from `class DualLayerDLPAdapter:` to
   `class DualLayerDLPAdapter(DLPPort):`
3. Since DLPPort is a `@runtime_checkable Protocol`, this is valid Python — the class
   both inherits the protocol AND implements it via its existing `sanitize()` method
4. Do NOT change any method signatures or logic

NOTE: The hardcoded Haiku model IDs in this file were already fixed by `fix-haiku-dlp`
in Round 1. If you see them still hardcoded, the Round 1 fix may not have completed —
escalate to orchestrator.

FILES TO READ:
- src/siopv/adapters/dlp/dual_layer_adapter.py (full file)
- src/siopv/application/ports/dlp.py (DLPPort definition)

VERIFICATION:
1. python -c "from siopv.adapters.dlp.dual_layer_adapter import DualLayerDLPAdapter; from siopv.application.ports.dlp import DLPPort; assert issubclass(DualLayerDLPAdapter, DLPPort)"
2. ruff format src/siopv/adapters/dlp/dual_layer_adapter.py
3. ruff check src/siopv/adapters/dlp/dual_layer_adapter.py
4. mypy src/siopv/adapters/dlp/dual_layer_adapter.py
5. pytest tests/unit/adapters/dlp/ -x -q --tb=short

Save report to: .ignorar/production-reports/remediation/{TIMESTAMP}-fix-dlp-port.md
```

**Files to read:** `dual_layer_adapter.py`, `application/ports/dlp.py`
**Fix:** Add `DLPPort` as explicit parent class
**Verification:** isinstance check; ruff + mypy; tests pass

---

### 5.8 `fix-di-exports` (Round 2) — Model: `claude-haiku-4-5-20251001`

**Rationale:** Verify-only no-op — read one file, confirm exports exist, report. No changes expected.

**Prompt:**
```
You are a remediation worker. Your task is to VERIFY a reported issue.

ISSUE: Known #5 — Briefing claims `infrastructure/di/__init__.py` is missing exports
for `get_dlp_port` and `get_dual_layer_dlp_port`.

EXPECTED FINDING: This is STALE. The code review shows these are already exported
at lines 46-49 and included in __all__ at lines 57-58.

FIX: NONE expected. Verify the current state. If exports exist → produce no-op report.
If they are somehow missing → add them and report.

FILES TO READ:
- src/siopv/infrastructure/di/__init__.py (full file)
- src/siopv/infrastructure/di/dlp.py (confirm source of exports)

VERIFICATION:
1. python -c "from siopv.infrastructure.di import get_dlp_port, get_dual_layer_dlp_port; print('OK')"
2. Confirm both names appear in __all__

Save report to: .ignorar/production-reports/remediation/{TIMESTAMP}-fix-di-exports.md
```

**Files to read:** `di/__init__.py`, `di/dlp.py`
**Fix:** Expected no-op — verify and report
**Verification:** Python import check

---

### 5.9 `fix-edges` (Round 2) — Model: `claude-opus-4-6`

**Rationale:** Requires architectural judgment — deciding the correct domain home for discrepancy logic, creating a new domain service module, and preserving re-exports for backwards compatibility.

**Prompt:**
```
You are a remediation worker. Your task is to move domain logic out of the
orchestration layer.

ISSUE: Hex #7 — `application/orchestration/edges.py` contains domain logic in
`calculate_batch_discrepancies()` and `calculate_discrepancy()`. These compute
ML/LLM discrepancy scores and adaptive thresholds — this is domain logic that
belongs in the domain layer, not in orchestration routing.

FIX:
1. Create `src/siopv/domain/services/discrepancy.py` with:
   - Move `calculate_discrepancy()` function (lines 82-116)
   - Move `calculate_batch_discrepancies()` function (lines 119-200)
   - Include necessary imports: `DiscrepancyHistory`, `DiscrepancyResult`,
     `ThresholdConfig` from `application/orchestration/state`
   - NOTE: These dataclasses are in `application/orchestration/state.py`.
     Ideally they'd be in the domain layer, but moving them is out of scope.
     Import them as-is for now.
2. In `edges.py`, replace the moved functions with imports from the new module:
   ```python
   from siopv.domain.services.discrepancy import (
       calculate_batch_discrepancies,
       calculate_discrepancy,
   )
   ```
3. Keep the re-exports in `edges.py __all__` so downstream code is not broken
4. If `src/siopv/domain/services/` directory doesn't exist, create it with an
   `__init__.py`

FILES TO READ:
- src/siopv/application/orchestration/edges.py (full file)
- src/siopv/application/orchestration/state.py (understand DiscrepancyHistory etc.)
- ls src/siopv/domain/services/ (check if directory exists)

VERIFICATION:
1. ruff format src/siopv/domain/services/discrepancy.py src/siopv/application/orchestration/edges.py
2. ruff check src/siopv/domain/services/ src/siopv/application/orchestration/edges.py
3. mypy src/siopv/domain/services/discrepancy.py src/siopv/application/orchestration/edges.py
4. pytest tests/unit/application/orchestration/ -x -q --tb=short
5. python -c "from siopv.application.orchestration.edges import calculate_batch_discrepancies; print('OK')"

Save report to: .ignorar/production-reports/remediation/{TIMESTAMP}-fix-edges.md
```

**Files to read:** `edges.py`, `state.py`, check `domain/services/` existence
**Fix:** Move discrepancy functions to new `domain/services/discrepancy.py`; re-export from `edges.py`
**Verification:** ruff + mypy on both files; orchestration tests pass; import check

---

### 5.10 `fix-ingest-node` (Round 3) — Model: `claude-sonnet-4-6`

**Prompt:**
```
You are a remediation worker. Your task is to fix a hexagonal architecture violation.

ISSUE: Hex #6 — `application/orchestration/nodes/ingest_node.py` directly instantiates
`IngestTrivyReportUseCase()` at lines 50 and 105 instead of receiving it via dependency
injection.

CONTEXT: After Round 2, `IngestTrivyReportUseCase` now accepts a `TrivyParserPort`
in its constructor (fix-ports-ingest). The node must receive the use case as a
parameter, or at minimum receive the parser port and construct the use case.

FIX:
1. Modify `ingest_node()` function signature to accept an optional
   `use_case: IngestTrivyReportUseCase | None = None` parameter
2. If `use_case` is None, create one with a default TrivyParser (import locally):
   ```python
   if use_case is None:
       from siopv.adapters.external_apis.trivy_parser import TrivyParser
       use_case = IngestTrivyReportUseCase(parser=TrivyParser())
   ```
3. Apply same pattern to `ingest_node_from_dict()`
4. Update `application/orchestration/graph.py` — NO, that file belongs to fix-graph.
   Your fix must be self-contained within ingest_node.py.

FILES TO READ:
- src/siopv/application/orchestration/nodes/ingest_node.py (full file)
- src/siopv/application/use_cases/ingest_trivy.py (to see updated constructor after R2)

VERIFICATION:
1. ruff format src/siopv/application/orchestration/nodes/ingest_node.py
2. ruff check src/siopv/application/orchestration/nodes/ingest_node.py
3. mypy src/siopv/application/orchestration/nodes/ingest_node.py
4. pytest tests/unit/application/orchestration/ -x -q --tb=short

Save report to: .ignorar/production-reports/remediation/{TIMESTAMP}-fix-ingest-node.md
```

**Files to read:** `ingest_node.py`, `ingest_trivy.py` (post-R2 state)
**Fix:** Accept use case via parameter; local fallback import
**Verification:** ruff + mypy; orchestration tests pass

---

### 5.11 `fix-enrich-node` (Round 3) — Model: `claude-sonnet-4-6`

**Prompt:**
```
You are a remediation worker. Your task is to remove dead code and verify async patterns.

ISSUE 1: Dead code — `enrich_node_async()` function (lines 190-258) in
`application/orchestration/nodes/enrich_node.py` is a duplicate of `enrich_node()`.
It is NOT exported in `application/orchestration/nodes/__init__.py` and is never
imported anywhere in the codebase.

ISSUE 2 (verify-only): Known #7 — Check that no `asyncio.run()` calls exist in
this file. Expected: none found (the function is already `async def`).

FIX:
1. Delete the entire `enrich_node_async()` function (lines 190-258)
2. Remove `"enrich_node_async"` from the `__all__` list at the bottom of the file
3. Verify: confirm no `asyncio.run()` in this file

FILES TO READ:
- src/siopv/application/orchestration/nodes/enrich_node.py (full file)

VERIFICATION:
1. grep "enrich_node_async" src/ -r — must return 0 results (except this report)
2. grep "asyncio.run" src/siopv/application/orchestration/nodes/enrich_node.py — must return 0
3. ruff format src/siopv/application/orchestration/nodes/enrich_node.py
4. ruff check src/siopv/application/orchestration/nodes/enrich_node.py
5. mypy src/siopv/application/orchestration/nodes/enrich_node.py
6. pytest tests/unit/application/orchestration/ -x -q --tb=short

Save report to: .ignorar/production-reports/remediation/{TIMESTAMP}-fix-enrich-node.md
```

**Files to read:** `enrich_node.py`
**Fix:** Delete `enrich_node_async` function and its `__all__` entry
**Verification:** grep confirms no references; ruff + mypy; tests pass

---

### 5.12 `fix-async-nodes` (Round 3) — Model: `claude-haiku-4-5-20251001`

**Rationale:** Verify-only — grep two files for `asyncio.run`, report findings. No changes expected.

**Prompt:**
```
You are a remediation worker. Your task is to VERIFY async patterns in two node files.

ISSUE: Known #7 — Briefing claims `asyncio.run()` is used in `dlp_node.py` and
`authorization_node.py`. This is expected to be STALE — both nodes are likely
`async def` functions using `await`.

FIX: Verify only. If no `asyncio.run()` found → produce no-op report.
If `asyncio.run()` IS found inside an async function → remove it and use `await`.

FILES TO READ:
- src/siopv/application/orchestration/nodes/dlp_node.py (full file)
- src/siopv/application/orchestration/nodes/authorization_node.py (full file)

VERIFICATION:
1. grep "asyncio.run" src/siopv/application/orchestration/nodes/dlp_node.py
2. grep "asyncio.run" src/siopv/application/orchestration/nodes/authorization_node.py
3. If any changes made: ruff format + ruff check + mypy on changed files
4. pytest tests/unit/application/orchestration/ -x -q --tb=short

Save report to: .ignorar/production-reports/remediation/{TIMESTAMP}-fix-async-nodes.md
```

**Files to read:** `dlp_node.py`, `authorization_node.py`
**Fix:** Expected no-op — verify and report
**Verification:** grep for `asyncio.run`; tests pass

---

### 5.13 `fix-graph` (Round 3) — Model: `claude-haiku-4-5-20251001`

**Rationale:** Verify-only — trace client wiring through 3 functions, confirm correct, report. No changes expected.

**Prompt:**
```
You are a remediation worker. Your task is to VERIFY enrichment client wiring.

ISSUE: Known #4 — Briefing claims `run_pipeline()` drops enrichment clients at
graph.py lines 439-444. This is expected to be STALE.

EXPECTED FINDING: `run_pipeline()` passes all 5 enrichment clients (`nvd_client`,
`epss_client`, `github_client`, `osint_client`, `vector_store`) to
`PipelineGraphBuilder` at lines 456-466. `_add_nodes()` wires them into the
`_enrich_node` closure at lines 195-205. Wiring is correct.

FIX: NONE expected. Read the full file, trace the client wiring path, and confirm.
If a gap is found → fix it and report.

FILES TO READ:
- src/siopv/application/orchestration/graph.py (full file)
- src/siopv/application/orchestration/nodes/enrich_node.py (confirm enrich_node accepts clients)

VERIFICATION:
1. Trace: run_pipeline() → PipelineGraphBuilder() → _add_nodes() → _enrich_node closure
2. Confirm all 5 clients are passed through each step
3. If no changes: report no-op

Save report to: .ignorar/production-reports/remediation/{TIMESTAMP}-fix-graph.md
```

**Files to read:** `graph.py`, `enrich_node.py`
**Fix:** Expected no-op — verify and report
**Verification:** Code tracing; no commands needed unless changes made

---

### 5.14 `fix-cli` (Round 4) — Model: `claude-opus-4-6`

**Rationale:** Highest-risk task — must read the full DI container, map 8 adapter ports to their factory functions, wire correctly, and handle 3 TODO stubs. Requires understanding the complete DI graph.

**Prompt:**
```
You are a remediation worker. Your task is the highest-complexity fix in this
remediation: wiring the CLI to the DI container.

ISSUE: Hex #3 + Known #1 — `interfaces/cli/main.py` calls `run_pipeline()` without
passing ANY adapter ports (lines 87-93). All ports default to None, meaning:
- No authorization check (Phase 5 bypassed)
- No DLP sanitization (Phase 6 bypassed)
- No enrichment clients (Phase 2 returns minimal stubs)
- No ML classifier (Phase 3 skipped)

Additionally, the `dashboard` command (lines 124-151) and `train_model` command
(lines 154-249) are already functional — do NOT modify them.

FIX for `process_report()` command:
1. Read `infrastructure/di/__init__.py` to see ALL available DI factory functions
2. Import and call the DI factory functions to obtain ports:
   ```python
   from siopv.infrastructure.di import (
       get_authorization_port,
       get_dual_layer_dlp_port,
   )
   ```
3. Get settings and create ports:
   ```python
   settings = get_settings()
   authorization_port = get_authorization_port(settings)
   dlp_port = get_dual_layer_dlp_port(settings)
   ```
4. Pass ports to `run_pipeline()`:
   ```python
   result = asyncio.run(
       run_pipeline(
           report_path=report_path,
           user_id=user_id,
           project_id=project_id,
           authorization_port=authorization_port,
           dlp_port=dlp_port,
       )
   )
   ```
5. For enrichment clients and classifier: these require more complex DI setup
   that is not yet implemented. Leave them as None for now but add a comment:
   `# TODO(phase-7): Wire enrichment clients and classifier via DI`
6. The TODO comment is acceptable here because Phase 7/8 builders will own this wiring

IMPORTANT: Do NOT modify the `dashboard` or `train_model` commands.
Do NOT modify the `main` callback.
Do NOT modify the `version` command.

FILES TO READ (MUST read both before making changes):
- src/siopv/interfaces/cli/main.py (full file)
- src/siopv/infrastructure/di/__init__.py (available DI functions)
- src/siopv/infrastructure/config/settings.py (get_settings pattern)

VERIFICATION:
1. ruff format src/siopv/interfaces/cli/main.py
2. ruff check src/siopv/interfaces/cli/main.py
3. mypy src/siopv/interfaces/cli/main.py
4. python -c "from siopv.interfaces.cli.main import app; print('CLI imports OK')"
5. pytest tests/unit/interfaces/ -x -q --tb=short (if tests exist)

Save report to: .ignorar/production-reports/remediation/{TIMESTAMP}-fix-cli.md
```

**Files to read:** `cli/main.py`, `di/__init__.py`, `settings.py`
**Fix:** Import DI factories; create ports from settings; pass to `run_pipeline()`
**Verification:** ruff + mypy; import check; CLI tests pass

---

### 5.15 `fix-adapter-tests` (Round 5) — Model: `claude-sonnet-4-6`

**Prompt:**
```
You are a remediation worker. Your task is to write unit tests for 5 Phase 2 adapters
that currently have 0-20% test coverage.

ISSUE: Known #8 — Phase 2 adapters have minimal or no test coverage:
1. NVD client: src/siopv/adapters/external_apis/nvd_client.py
2. EPSS client: src/siopv/adapters/external_apis/epss_client.py
3. GitHub Advisory client: src/siopv/adapters/external_apis/github_advisory_client.py
4. Tavily/OSINT client: src/siopv/adapters/external_apis/tavily_client.py
5. ChromaDB vector store: src/siopv/adapters/vectorstore/chroma_adapter.py

FIX — For EACH adapter, create a test file with:
- Mock external API calls (httpx, graphql, chromadb)
- Test happy path (successful response → correct domain object)
- Test error handling (API error → proper exception or fallback)
- Test rate limiting / circuit breaker behavior if applicable
- Target: 80%+ coverage per adapter file

Test file naming:
1. tests/unit/adapters/external_apis/test_nvd_client.py
2. tests/unit/adapters/external_apis/test_epss_client.py
3. tests/unit/adapters/external_apis/test_github_advisory_client.py
4. tests/unit/adapters/external_apis/test_tavily_client.py
5. tests/unit/adapters/vectorstore/test_chroma_adapter.py

IMPORTANT:
- Use pytest + pytest-asyncio for async tests
- Mock ALL external HTTP calls — no real API calls in unit tests
- Use unittest.mock.AsyncMock for async methods
- Follow existing test patterns in tests/unit/adapters/dlp/ for reference

FILES TO READ:
- Each of the 5 adapter source files (to understand interfaces)
- src/siopv/application/ports/enrichment_clients.py (port contracts)
- src/siopv/application/ports/vector_store.py (VectorStorePort contract)
- tests/unit/adapters/dlp/ (reference test patterns)

VERIFICATION:
1. pytest tests/unit/adapters/external_apis/ -x -q --tb=short
2. pytest tests/unit/adapters/vectorstore/ -x -q --tb=short
3. pytest --cov=src/siopv/adapters/external_apis --cov-report=term-missing tests/unit/adapters/external_apis/
4. pytest --cov=src/siopv/adapters/vectorstore --cov-report=term-missing tests/unit/adapters/vectorstore/
5. ruff format tests/unit/adapters/
6. ruff check tests/unit/adapters/
7. mypy tests/unit/adapters/

Save report to: .ignorar/production-reports/remediation/{TIMESTAMP}-fix-adapter-tests.md
```

**Files to read:** 5 adapter files + 2 port files + reference tests
**Fix:** Create 5 test files with comprehensive mocked unit tests
**Verification:** All tests pass; coverage 80%+ per adapter; ruff + mypy clean

---

## 6. Verification Round (Round 6)

After all 5 rounds complete, run full verification:

### Step 1: Lint and Type Check
```bash
cd /Users/bruno/siopv
ruff format src/ tests/
ruff check src/ tests/
mypy src/
```

### Step 2: Full Test Suite with Coverage
```bash
pytest tests/ --cov=src --cov-fail-under=83 -x -q --tb=short
```

**Coverage floor: 83%** — must not regress below this baseline.

### Step 3: Verify No Remaining Violations
```bash
# Hex #1: No adapter imports in use cases
grep -r "from siopv.adapters" src/siopv/application/use_cases/ | grep -v "__pycache__"
# Expected: 0 results

# Hex #2: Same check (covered by above)

# Known #6: No hardcoded Haiku model IDs in adapter code
grep -r "claude-haiku-4-5-20251001" src/siopv/adapters/
# Expected: 0 results

# Known #2: Orphaned use case deleted
ls src/siopv/application/use_cases/sanitize_vulnerability.py 2>&1
# Expected: "No such file or directory"
```

### Step 4: Run /verify Skill
Execute the `/verify` skill which runs all 14 verification agents.

### Gate
All of the following must be true:
- ruff format: 0 changes needed
- ruff check: 0 errors
- mypy: 0 errors
- pytest: all passing, coverage >= 83%
- /verify: all 14 agents pass

If any gate fails → identify the failing worker's fix → re-run that worker with corrective instructions → re-verify.

---

## 7. Escalation Protocol

### When a worker finds a stale item
1. Worker confirms the issue does not exist in current code
2. Worker produces a no-op report documenting the finding
3. Worker reports to orchestrator: "Item X is stale — no action taken"
4. Orchestrator acknowledges and continues — no re-assignment needed

### When a worker encounters ambiguity
1. Worker STOPS immediately — does not guess or attempt a speculative fix
2. Worker reports to orchestrator with:
   - Which file and line is ambiguous
   - What they considered
   - What information is missing
3. Orchestrator investigates (reads the file, checks context) and provides specific guidance
4. Worker resumes only after receiving clarification

### When a fix breaks tests
1. Worker reviews the test failure traceback
2. If the test failure is expected (test was testing deleted/changed code) → update the test
3. If the test failure is unexpected → revert the change, report to orchestrator
4. Worker does NOT commit broken code

### When coverage drops below 83%
1. Orchestrator identifies which worker's changes caused the regression
2. That worker must add tests to restore coverage before proceeding
3. If the regression is due to deleted code (e.g., `fix-sanitize`), verify that
   removing the test file didn't drop coverage — the file was orphaned so its
   coverage contribution was likely negligible

### When two workers need the same file
This should NOT happen — the file ownership map prevents it. If it does:
1. Orchestrator is the single point of conflict resolution
2. Identify which worker's fix is more critical
3. Assign the file to that worker; give the other worker a workaround
4. Document the deviation in the verification report
