---
task: verify hexagonal architecture compliance (regression check)
start: 2026-03-17T11:25:00Z
agent: wave8-hexarch
wave: 8
---

## Checks to perform
1. ingest_trivy.py does NOT import TrivyParser from adapters/
2. classify_risk.py does NOT import FeatureEngineer from adapters/
3. interfaces/cli/main.py has all 8 adapter ports wired via DI (none are None)
4. dual_layer_adapter.py explicitly inherits DLPPort
5. infrastructure/di/authorization.py uses @lru_cache on adapter factory
6. ingest_node.py uses injected use case (no direct instantiation)
7. edges.py has no domain logic (calculate_batch_discrepancies moved to domain)

## Status
IN PROGRESS
