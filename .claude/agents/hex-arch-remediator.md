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

### Pre-Write Hardcoding Prevention

Before writing or modifying any code, apply this check:

1. Identify every new or changed value in your code that is: a numeric literal, a path, a URL, a timeout, a threshold, a rate limit, a credential, or a model identifier.
2. For each such value, check if `settings.py` has a corresponding field.
3. If `settings.py` LACKS the field: add the field to `settings.py` FIRST, add the env var to `.env.example`, then use the settings value in code via DI injection.
4. If `settings.py` HAS the field: use it. Do not redefine or shadow it.
5. NEVER introduce a hardcoded value with the intent to "wire it later". Wire it now or don't write the code.

## Report Format

Save to `.ignorar/production-reports/hex-arch-remediator/{TIMESTAMP}-hex-arch-violations-fixed.md`:
- Violation # | Status | Files changed | Tests still passing
- CRITICAL: `bypassPermissions` is NOT available — use `acceptEdits` mode.
