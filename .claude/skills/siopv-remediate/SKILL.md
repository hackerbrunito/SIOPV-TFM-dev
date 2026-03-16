---
name: siopv-remediate
description: "Fix SIOPV Stage 2 hex-arch violations #1-7. USE WHEN user asks to fix hexagonal violations or runs /siopv-remediate."
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
(multi-module change >3 modules requires human checkpoint — per CLAUDE.md rules 9–10).
