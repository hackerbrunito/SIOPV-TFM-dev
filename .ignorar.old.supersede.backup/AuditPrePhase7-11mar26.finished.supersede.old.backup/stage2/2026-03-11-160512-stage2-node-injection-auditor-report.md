# node-injection-auditor Report

**Auditor:** node-injection-auditor
**Date:** 2026-03-11 16:05:12
**Scope:** 5 orchestration node files — dependency injection audit

## Summary: 4 INJECTED, 1 DIRECT_INSTANTIATION, 0 asyncio.run() usages

| Node | DI Verdict | asyncio.run() | Import Violation |
|------|-----------|---------------|-----------------|
| authorization_node.py | INJECTED | No | No |
| classify_node.py | INJECTED | No | No |
| dlp_node.py | INJECTED | No | No |
| enrich_node.py | INJECTED | No | No |
| ingest_node.py | DIRECT_INSTANTIATION | No | No |

---

## Per-Node Assessment

### authorization_node.py — INJECTED

- **Main function:** `async def authorization_node(state, *, authorization_port: AuthorizationPort | None = None)`
- **DI pattern:** `authorization_port` received as keyword parameter (port interface)
- **Imports:** `siopv.domain.authorization` (domain layer); TYPE_CHECKING: `siopv.application.ports.authorization` (port interface)
- **No adapter/infrastructure imports**
- **No `asyncio.run()`** — function is natively async
- **Depends on:** Port interface (`AuthorizationPort`), not concrete implementation

### classify_node.py — INJECTED

- **Main function:** `def classify_node(state, *, classifier: MLClassifierPort | None = None)`
- **DI pattern:** `classifier` received as keyword parameter (port interface)
- **Internal instantiation:** `ClassifyRiskUseCase(classifier=classifier)` — use case instantiation with injected port (acceptable pattern; the use case is application-layer, not infrastructure)
- **Imports:** `siopv.application.use_cases.classify_risk`, `siopv.domain.value_objects.risk_score`; TYPE_CHECKING: `siopv.application.ports.ml_classifier`
- **No adapter/infrastructure imports**
- **No `asyncio.run()`** — function is synchronous, does not call async code
- **Depends on:** Port interface (`MLClassifierPort`), not concrete implementation

### dlp_node.py — INJECTED

- **Main function:** `async def dlp_node(state, *, dlp_port: DLPPort | None = None)`
- **DI pattern:** `dlp_port` received as keyword parameter (port interface)
- **Imports:** `siopv.domain.privacy.entities`; TYPE_CHECKING: `siopv.application.ports.dlp`
- **No adapter/infrastructure imports**
- **No `asyncio.run()`** — function is natively async
- **Depends on:** Port interface (`DLPPort`), not concrete implementation

### enrich_node.py — INJECTED

- **Main function:** `async def enrich_node(state, *, nvd_client, epss_client, github_client, osint_client, vector_store, max_concurrent=5)`
- **DI pattern:** All 5 adapter ports received as keyword parameters (all port interfaces: `NVDClientPort`, `EPSSClientPort`, `GitHubAdvisoryClientPort`, `OSINTSearchClientPort`, `VectorStorePort`)
- **Internal instantiation:** `EnrichContextUseCase(nvd_client=..., epss_client=..., ...)` — use case instantiation with injected ports (acceptable pattern)
- **Imports:** `siopv.application.use_cases.enrich_context`, `siopv.domain.value_objects`; TYPE_CHECKING: `siopv.application.ports`
- **No adapter/infrastructure imports**
- **No `asyncio.run()`** — function is natively async
- **Depends on:** Port interfaces only, not concrete implementations

### ingest_node.py — DIRECT_INSTANTIATION

- **Main function:** `def ingest_node(state: PipelineState) -> dict[str, object]`
- **DI violation:** `IngestTrivyReportUseCase()` instantiated directly inside the function body (line 50) with **no injected dependencies**
- **No port parameter** — unlike all other nodes, `ingest_node` takes only `state` and no keyword-argument ports
- **Same pattern in `ingest_node_from_dict`** (line 105): `IngestTrivyReportUseCase()` directly instantiated
- **Imports:** `siopv.application.use_cases.ingest_trivy`; TYPE_CHECKING: `siopv.application.orchestration.state`
- **No adapter/infrastructure imports** (the use case itself is application-layer)
- **No `asyncio.run()`** — function is synchronous, does not call async code
- **Ambiguity:** `IngestTrivyReportUseCase` may be a pure parser with no external dependencies (file I/O only), which could justify direct instantiation. However, this breaks the consistent DI pattern used by all other nodes. If the use case were later refactored to need an external adapter (e.g., S3 storage, report validation service), the node signature would need to change.

---

## Known Issue Status

- **Finding #7 (asyncio.run() in sync nodes):** **NOT PRESENT in any of the 5 node files.** None of the nodes use `asyncio.run()`. Three nodes (`authorization_node`, `dlp_node`, `enrich_node`) are natively `async def`. Two nodes (`classify_node`, `ingest_node`) are synchronous `def` but do not call async code. The `asyncio.run()` issue from STAGE-1 appears to reside elsewhere (likely in the CLI or graph runner, not in the node files themselves).

---

## Additional Observations

1. **Consistent pattern across 4/5 nodes:** Authorization, classify, DLP, and enrich nodes all follow the same DI pattern — ports received as `Optional` keyword arguments with `None` defaults, graceful fallback when port is `None`.

2. **Import hygiene is clean:** All 5 nodes import only from `siopv.domain` and `siopv.application` layers. No node imports from `siopv.adapters` or `siopv.infrastructure`. TYPE_CHECKING imports reference port interfaces, not concrete implementations.

3. **Use case instantiation pattern:** `classify_node` and `enrich_node` instantiate use cases internally but pass injected ports into them. This is an acceptable composition pattern — the use case is application-layer orchestration, and the actual external dependencies (ports) are still injected from outside.
