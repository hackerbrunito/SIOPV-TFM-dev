# graph-wiring-auditor Report

## Summary: 3 CORRECT, 1 PARTIAL, 1 VIOLATION

---

## Per-File Assessment

### graph.py — CORRECT

**DI Pattern:** `PipelineGraphBuilder` uses **constructor injection** — all 8 ports/adapters (`authorization_port`, `dlp_port`, `nvd_client`, `epss_client`, `github_client`, `osint_client`, `vector_store`, `classifier`) are accepted as constructor parameters and stored as instance attributes. The builder does NOT import from `infrastructure/di/` and does NOT directly instantiate any adapter. This is proper inversion of control — the caller is responsible for resolving dependencies.

**Node wiring:** Each node that needs dependencies is wrapped in a closure that captures `self._*` attributes:
- `_authorize_node` closure → passes `self._authorization_port`
- `_dlp_node` closure → passes `self._dlp_port`
- `_enrich_node` closure → passes all 5 enrichment clients (`nvd_client`, `epss_client`, `github_client`, `osint_client`, `vector_store`)
- `classify` node → lambda passes `self._classifier`
- `ingest_node` and `escalate_node` → no external dependencies (correct)

**`run_pipeline()` signature:** Accepts ALL enrichment clients as keyword arguments and forwards them to `PipelineGraphBuilder`. All default to `None` — the pipeline can technically run with no adapters wired, which delegates responsibility to the caller.

**Edge routing:** Uses imported functions from `edges.py` (`route_after_classify`, `route_after_escalate`, `route_after_authorization`) — clean separation.

**Note:** All port parameters default to `None`. If no caller wires real adapters, nodes receive `None` dependencies. This is not a violation (it's valid optional DI) but places the burden on the entry point (CLI) to resolve adapters.

---

### edges.py — PARTIAL

**Routing functions:** `route_after_classify`, `route_after_escalate`, and `should_escalate_route` are pure routing logic that reads state and returns route strings. This is correct placement for orchestration edge functions.

**Borderline business logic:** `calculate_discrepancy()` and `calculate_batch_discrepancies()` contain the full adaptive threshold algorithm:
- Percentile-based adaptive threshold calculation
- Two-pass iteration over classifications
- Direct access to domain objects (`classification.risk_score.risk_probability`)

This logic implements the spec's Uncertainty Trigger (section 3.4). While it's used for routing decisions, the discrepancy formula and adaptive threshold are domain-level policy that could arguably live in a domain service or use case. The functions access `ClassificationResult` internals via `type: ignore` casts, suggesting tight coupling to domain objects.

**Verdict rationale:** PARTIAL because the routing functions are correctly placed, but `calculate_batch_discrepancies` contains domain policy that would be better encapsulated in a domain service. Not a hard violation — it's a design smell, not a broken dependency.

**No infrastructure/adapter imports** — only imports from `state` and `utils` within the orchestration package.

---

### state.py — CORRECT

**Imports:**
- `siopv.application.use_cases.classify_risk.ClassificationResult` — application layer (same layer, acceptable)
- `siopv.domain.entities.VulnerabilityRecord` — domain layer (acceptable, state references domain types)
- `siopv.domain.value_objects.EnrichmentData` — domain layer (acceptable)

**No imports from `adapters/` or `infrastructure/`** — CORRECT. State module only references domain and application-layer types, which is proper for a TypedDict state schema.

**Data classes:** `DiscrepancyResult`, `ThresholdConfig`, `DiscrepancyHistory` are orchestration-specific data structures, correctly co-located with state. `ThresholdConfig` contains default values from the spec (threshold=0.3, confidence_floor=0.7, percentile=90) — these are configuration constants, appropriately placed.

---

### cli/main.py — VIOLATION

**Finding: CLI does NOT wire DI adapters.**

The `process_report` command calls `run_pipeline()` with only 3 arguments:
```python
result = asyncio.run(
    run_pipeline(
        report_path=report_path,
        user_id=user_id,
        project_id=project_id,
    )
)
```

This means **all 8 adapter ports default to `None`**:
- `authorization_port=None` → authorization node gets no port
- `dlp_port=None` → DLP node gets no port
- `nvd_client=None` → enrichment gets no NVD client
- `epss_client=None` → enrichment gets no EPSS client
- `github_client=None` → enrichment gets no GitHub client
- `osint_client=None` → enrichment gets no OSINT client
- `vector_store=None` → enrichment gets no vector store
- `classifier=None` → classification gets no ML model

The DI container exists at `infrastructure/di/` (confirmed in MEMORY.md: factories with `lru_cache`), but the CLI **completely bypasses it**. The pipeline runs structurally but all adapter-dependent nodes operate with `None` dependencies — meaning no actual enrichment, authorization, DLP, or classification occurs via real adapters.

**`train_model` command:** Directly instantiates `XGBoostClassifier()` (line 234) instead of going through DI. Acceptable for a training utility but inconsistent with the DI pattern.

**`dashboard` command:** Phase 7 TODO stub — expected, not a violation.

**`asyncio.run()` usage:** The CLI uses `asyncio.run()` to call the async `run_pipeline()`. This is the known pattern from STAGE-1 Finding #7 ("asyncio.run() in sync nodes — root is CLI"). Still present — the CLI is the sync/async boundary.

---

### utils.py — CORRECT

**Imports:** Only `structlog` and orchestration-internal types (`ThresholdConfig`, `DiscrepancyHistory` from `state`). No infrastructure or adapter imports.

**Functions:**
- `should_escalate_cve()` — pure function, single-CVE escalation check
- `calculate_escalation_candidates()` — batch escalation with adaptive threshold
- `check_any_escalation_needed()` — quick boolean check for routing

All are stateless utility functions shared between `edges.py` and node implementations. Properly factored to avoid duplication. No side effects beyond logging.

---

## Known Issue Status

### Finding #1 (CLI TODO stubs): PARTIALLY RESOLVED
- `process_report` command IS fully implemented — it calls `run_pipeline`, processes results, writes summary JSON. The command is no longer a stub.
- **However**, it does not wire any DI adapters (see VIOLATION above). The command "works" structurally but runs with all `None` dependencies.
- `dashboard` command remains a Phase 7 TODO stub (expected — Phase 7 not yet implemented).

### Finding #4 (run_pipeline drops enrichment clients): RESOLVED
- `run_pipeline()` now accepts all 5 enrichment clients (`nvd_client`, `epss_client`, `github_client`, `osint_client`, `vector_store`) plus `authorization_port`, `dlp_port`, and `classifier`.
- All 8 ports are forwarded to `PipelineGraphBuilder`.
- The signature matches the builder's constructor 1:1.
- **Caveat:** While `run_pipeline` CAN pass clients, no current caller (CLI) actually provides them. The plumbing is correct; the wiring is missing at the entry point.

---

## Ambiguities Noted (no action taken)

1. **Nodes file not in audit scope:** `nodes.py` (imported by `graph.py`) was not in the 5-file list. The node implementations may contain their own DI violations or direct instantiations — cannot confirm from this audit.
2. **DI factory files not in scope:** `infrastructure/di/__init__.py` and `infrastructure/di/dlp.py` were not read. Cannot confirm whether the DI factories produce the correct port implementations.
3. **`classify_node` uses lambda, not async wrapper:** Unlike `authorize`, `dlp`, and `enrich` (which use async closures), `classify_node` uses a sync lambda. This may be intentional (sync classifier) or an oversight — cannot determine without reading `nodes.py`.
