# SIOPV Project Errors → Rules Log

Project-specific errors. Reviewed by agents at session start.
> **Global log:** `~/.claude/rules/errors-to-rules.md`

---

## Logged Errors

### 2026-03-11: Adapter imports in application layer (Stage 2 CRITICAL)

**Error:** `application/use_cases/ingest_trivy.py:17` imports `TrivyParser` directly from
`adapters/`. `application/use_cases/classify_risk.py:18` imports `FeatureEngineer` from
`adapters/`. Application layer must depend only on ports (abstract interfaces).

**Rule:** Use cases MUST import only from `domain/` and `application/ports/`. If an adapter
class is needed, inject it via the port interface. Never import from `adapters/` in `application/`.

---

### 2026-03-11: DI ports left as None in CLI (Stage 2 HIGH)

**Error:** `interfaces/cli/main.py` wires all 8 adapter ports as `None`. The dependency
injection container is never invoked at CLI entry point.

**Rule:** ALWAYS call the DI factory functions (`infrastructure/di/`) before constructing
the orchestration graph in the CLI. Verify with: `assert port is not None` before graph init.

---

### 2026-03-11: Duplicate OpenFGA adapter instances (Stage 2 MEDIUM)

**Error:** `infrastructure/di/authorization.py` creates 3 separate `OpenFGAAdapter` instances
instead of caching one. Causes multiple connections and inconsistent state.

**Rule:** ALWAYS decorate DI factory functions with `@lru_cache`. One adapter instance per
process. OpenFGA adapter is expensive to create — `@lru_cache` is mandatory.

---

### 2026-03-11: Missing DLPPort inheritance (Stage 2 MEDIUM)

**Error:** `adapters/dlp/dual_layer_adapter.py` does not explicitly inherit from `DLPPort`.
Passes duck-typing tests but breaks strict port compliance checks.

**Rule:** Every adapter class MUST explicitly inherit from its port interface. No implicit
duck typing. Pattern: `class DualLayerDLPAdapter(DLPPort):`.

---

### 2026-03-11: Use case instantiated directly in node (Stage 2 MEDIUM)

**Error:** `application/orchestration/nodes/ingest_node.py` directly instantiates
`IngestTrivyUseCase()` instead of receiving it via constructor injection.

**Rule:** LangGraph nodes are thin wrappers. They MUST receive use cases via constructor
injection — never instantiate domain/application objects inside node functions.

---

### 2026-03-16: Fix agents spawned without Context7 consultation

**Error:** Fix agents (fix-lru_cache, fix-ruff-arg002) were spawned with prompts that relied purely on Claude training data (cutoff August 2025). No Context7 MCP query was included in the agent prompts. This risks introducing fixes based on outdated library APIs or stale Python patterns.

**Rule:** EVERY fix agent prompt MUST include an explicit step to consult Context7 BEFORE implementing any fix:
1. `mcp__context7__resolve-library-id` for each library involved
2. `mcp__context7__get-library-docs` to get current API patterns
3. Only then implement the fix using verified current patterns

This applies to ALL agents — not just research agents. Training data is stale by definition. Context7 is available in every session via the configured MCP variable.

---

### 2026-03-11: Domain logic in LangGraph edge routing (Stage 2 LOW)

**Error:** `application/orchestration/edges.py::calculate_batch_discrepancies()` contains
domain logic (discrepancy calculation) that belongs in a domain service.

**Rule:** LangGraph edges must contain only routing decisions (if/else on state fields).
Any calculation or business logic belongs in a domain service, called from a node.
