# R2 — Phase 4 Gap Analysis: Orquestación y Gestión de Incertidumbre

> Analyst: gap-analyzer-phase-4 | Date: 2026-03-11
> Sources: R1 requirements matrix (Phase 4: REQ-P4-001 to REQ-P4-011)

---

## Summary

| Status | Count |
|--------|-------|
| IMPLEMENTED | 6 |
| PARTIAL | 4 |
| MISSING | 1 |

---

## Requirement-by-Requirement Assessment

### REQ-P4-001 — Module name: `LangGraph_Orchestrator`

**Status:** IMPLEMENTED

**Evidence:**
- `src/siopv/application/orchestration/graph.py:1-4` — Module docstring: "LangGraph pipeline builder for SIOPV orchestration. Based on specification section 3.4."
- `src/siopv/application/orchestration/graph.py:90` — `PipelineGraphBuilder` class implements the orchestrator
- Supporting modules: `edges.py`, `utils.py`, `state.py`, `nodes/` directory

**Notes:** The module is named `orchestration` (directory) rather than literally `LangGraph_Orchestrator`, but this is appropriate for Python package naming conventions.

---

### REQ-P4-002 — Model: Claude Sonnet 4.5 for state orchestration

**Status:** MISSING

**Evidence:**
- No Claude model import or invocation found anywhere in `src/siopv/application/orchestration/` (grep for `sonnet`, `claude`, `model` returned zero matches)
- `src/siopv/application/orchestration/nodes/classify_node.py:134-135` — Comment admits: "For now, use ML probability as proxy for LLM confidence. In production, this would come from actual LLM evaluation."
- `src/siopv/application/orchestration/nodes/classify_node.py:147-165` — `_estimate_llm_confidence()` is pure math heuristic, not an LLM call

**Notes:** The spec requires Claude Sonnet 4.5 for state orchestration decisions. Currently the orchestration is purely algorithmic — no LLM is invoked for confidence evaluation or state transitions. This was already flagged in the prior audit (CRITICAL finding #3: "LLM confidence is a heuristic").

---

### REQ-P4-003 — Persistence: SQLite for graph state checkpointing

**Status:** IMPLEMENTED

**Evidence:**
- `src/siopv/application/orchestration/graph.py:9` — `import sqlite3`
- `src/siopv/application/orchestration/graph.py:16-18` — Imports `SqliteSaver` and `AsyncSqliteSaver` from langgraph
- `src/siopv/application/orchestration/graph.py:51` — `DEFAULT_CHECKPOINT_DB = "siopv_checkpoints.db"`
- `src/siopv/application/orchestration/graph.py:268-284` — `_create_checkpointer()` creates `SqliteSaver` with validated path
- `src/siopv/application/orchestration/graph.py:482-494` — `run_pipeline()` uses `AsyncSqliteSaver` for async execution

**Notes:** Fully implemented with both sync (`SqliteSaver`) and async (`AsyncSqliteSaver`) variants. Path validation prevents traversal attacks.

---

### REQ-P4-004 — Uncertainty Trigger: adaptive threshold, NOT fixed value

**Status:** PARTIAL

**Evidence:**
- `src/siopv/application/orchestration/state.py:96-110` — `ThresholdConfig` dataclass with `base_threshold=0.3`, `confidence_floor=0.7`, `percentile=90`, `history_size=500`
- `src/siopv/application/orchestration/state.py:113-149` — `DiscrepancyHistory` class with `add()` and `get_percentile()` methods
- `src/siopv/application/orchestration/edges.py:119-200` — `calculate_batch_discrepancies()` implements two-pass adaptive threshold
- `src/siopv/application/orchestration/utils.py:59-128` — `calculate_escalation_candidates()` also implements adaptive threshold

**Notes:** The adaptive threshold data structures and calculation logic exist. However, `DiscrepancyHistory` is in-memory only — values are lost between runs. The spec requires persistence of historical discrepancies for weekly recalculation (see REQ-P4-006). Additionally, in `check_any_escalation_needed()` (utils.py:150-169), the quick routing check uses `config.base_threshold` (fixed 0.3) instead of the adaptive threshold, creating an inconsistency between routing decision and escalation node logic.

---

### REQ-P4-005 — Discrepancy formula: `|ml_score - llm_confidence|`

**Status:** IMPLEMENTED

**Evidence:**
- `src/siopv/application/orchestration/edges.py:105` — `discrepancy = abs(ml_score - llm_confidence)`
- `src/siopv/application/orchestration/utils.py:55-56` — `discrepancy = abs(ml_score - llm_confidence)` in `should_escalate_cve()`
- `src/siopv/application/orchestration/utils.py:93` — Same formula in `calculate_escalation_candidates()`
- `src/siopv/application/orchestration/state.py:85` — `DiscrepancyResult.discrepancy` field documented as "Absolute difference |ml_score - llm_confidence|"

**Notes:** Formula correctly implemented in all locations.

---

### REQ-P4-006 — Dynamic threshold: `percentile_90(historical_discrepancies)` recalculated weekly from last 500 evaluations

**Status:** PARTIAL

**Evidence:**
- `src/siopv/application/orchestration/state.py:134-149` — `get_percentile()` calculates P90 from sorted history
- `src/siopv/application/orchestration/state.py:103-104` — `percentile: int = 90`, `history_size: int = 500` — correct parameters
- `src/siopv/application/orchestration/state.py:130-132` — Rolling window truncation: `self.values = self.values[-self.max_size:]`

**Notes:** Two gaps:
1. **No persistence** — `DiscrepancyHistory.values` is an in-memory `list[float]`. No SQLite/file persistence exists, so history is lost between pipeline runs. The spec requires continuity across evaluations.
2. **No weekly recalculation** — No scheduler, cron job, or time-based trigger recalculates the threshold. The threshold is recalculated on every batch (edges.py:170), not on a weekly cadence from accumulated history.

---

### REQ-P4-007 — Escalation rule: `discrepancy > threshold OR llm_confidence < 0.7` → escalate to human

**Status:** IMPLEMENTED

**Evidence:**
- `src/siopv/application/orchestration/utils.py:24-56` — `should_escalate_cve()` implements both conditions:
  - Line 51: `if llm_confidence < confidence_floor: return True`
  - Line 55-56: `discrepancy = abs(ml_score - llm_confidence); return discrepancy > threshold`
- `src/siopv/application/orchestration/state.py:101` — `confidence_floor: float = 0.7`
- `src/siopv/application/orchestration/edges.py:108` — `should_escalate = discrepancy > effective_threshold or llm_confidence < config.confidence_floor`

**Notes:** Rule correctly implemented in multiple locations with consistent logic.

---

### REQ-P4-008 — Checkpoint after each node transition — enables resumption, async human review, post-mortem audit

**Status:** PARTIAL

**Evidence:**
- `src/siopv/application/orchestration/graph.py:302-306` — Checkpointer attached to compiled graph
- `src/siopv/application/orchestration/graph.py:487-491` — Async checkpointer used in `run_pipeline()`
- LangGraph's `SqliteSaver`/`AsyncSqliteSaver` automatically checkpoints after each node transition

**Notes:** LangGraph handles automatic checkpointing after each node when a checkpointer is attached. However:
1. `run_pipeline()` only uses checkpointing when `checkpoint_db_path is not None` (line 482). If omitted, no checkpointing occurs (line 493-494).
2. **No resumption API** — There is no function to resume a pipeline from a checkpoint (e.g., after human review in Phase 7). The `thread_id` is passed in config but there's no `resume_pipeline()` or equivalent.
3. **No post-mortem audit query** — No utility to retrieve or inspect historical checkpoints.

---

### REQ-P4-009 — 8-phase pipeline as LangGraph nodes with conditional branching

**Status:** PARTIAL

**Evidence:**
- `src/siopv/application/orchestration/graph.py:158-219` — 6 nodes added: `authorize`, `ingest`, `dlp`, `enrich`, `classify`, `escalate`
- `src/siopv/application/orchestration/graph.py:221-266` — Conditional edges: `route_after_authorization`, `route_after_classify`, `route_after_escalate`
- Flow: `START → authorize → ingest → dlp → enrich → classify → [escalate] → END`

**Notes:** The spec calls for 8 phases as nodes. Currently 6 nodes are wired. Missing:
1. **Phase 7 node** (`human_review` / HITL) — not yet implemented (expected, Phase 7 is pending)
2. **Phase 8 node** (`output` / Jira+PDF) — not yet implemented (expected, Phase 8 is pending)
The prior audit (MEDIUM finding #12) already flagged: "`output_node` missing from graph — Phase 8 requires graph topology change."

---

### REQ-P4-010 — Each node = pure function transforming typed state (TypedDict or Pydantic)

**Status:** IMPLEMENTED

**Evidence:**
- `src/siopv/application/orchestration/state.py:21-75` — `PipelineState(TypedDict, total=False)` — uses TypedDict as required by LangGraph
- `src/siopv/application/orchestration/nodes/ingest_node.py:21` — `def ingest_node(state: PipelineState) -> dict[str, object]:`
- `src/siopv/application/orchestration/nodes/enrich_node.py:28` — `async def enrich_node(state: PipelineState, ...) -> dict[str, object]:`
- `src/siopv/application/orchestration/nodes/classify_node.py:26-30` — `def classify_node(state: PipelineState, ...) -> dict[str, object]:`
- `src/siopv/application/orchestration/nodes/escalate_node.py:21` — `def escalate_node(state: PipelineState) -> dict[str, object]:`

**Notes:** All nodes are pure functions (or async functions) that accept `PipelineState` and return `dict[str, object]` state updates. TypedDict used as required. Some nodes accept injected ports as keyword arguments (DI pattern), which is acceptable — the state transformation remains pure.

---

### REQ-P4-011 — Correlation ID (UUID4) in `PipelineState.run_id`, propagated through all nodes

**Status:** IMPLEMENTED (with naming deviation)

**Evidence:**
- `src/siopv/application/orchestration/state.py:74` — `thread_id: str` field in `PipelineState`
- `src/siopv/application/orchestration/state.py:196` — `thread_id=thread_id or str(uuid.uuid4())` — generates UUID4
- `src/siopv/application/orchestration/graph.py:450` — `thread_id=thread_id or str(uuid.uuid4())` — also in `run_pipeline()`
- `src/siopv/application/orchestration/graph.py:469` — `config: RunnableConfig = {"configurable": {"thread_id": initial_state["thread_id"]}}`
- All nodes log `thread_id=state.get("thread_id")` for traceability

**Notes:** The field is named `thread_id` instead of `run_id` as specified. Functionally equivalent — it's a UUID4 generated at pipeline start, propagated through all nodes, and used in both logging and LangGraph checkpointing config. No separate `run_id` field exists. The naming difference is minor but worth documenting for spec traceability.

---

## Cross-Reference with Prior Audit Findings

| Prior Audit Finding | Related REQ | Confirmed? |
|---------------------|-------------|------------|
| CRITICAL #3: LLM confidence is heuristic | REQ-P4-002 | Yes — still MISSING |
| CRITICAL #4: `run_pipeline()` drops enrichment clients | REQ-P4-009 | Fixed — `run_pipeline()` now passes all clients (graph.py:456-466) |
| MEDIUM #12: `output_node` missing from graph | REQ-P4-009 | Expected — Phase 7/8 pending |

---

## Priority Recommendations

1. **REQ-P4-002 (MISSING)** — Integrate Claude Sonnet for LLM confidence evaluation. Replace `_estimate_llm_confidence()` heuristic with actual LLM call. This is the largest gap in Phase 4.
2. **REQ-P4-006 (PARTIAL)** — Persist `DiscrepancyHistory` to SQLite alongside checkpoints. Add weekly recalculation trigger or document the per-batch approach as an ADR.
3. **REQ-P4-008 (PARTIAL)** — Add `resume_pipeline()` function for Phase 7 HITL integration. This will be critical when Phase 7 is implemented.
4. **REQ-P4-004 (PARTIAL)** — Fix `check_any_escalation_needed()` to use adaptive threshold instead of fixed `base_threshold` for routing consistency.

---

*End of report — 11 requirements assessed: 6 IMPLEMENTED, 4 PARTIAL, 1 MISSING.*
