# STAGE-3 Round 3 — Aggregated Report
**Aggregator:** round3-aggregator
**Timestamp:** 2026-03-11-182029
**Source:** 2026-03-11-181828-stage3-scanner-langgraph-deep.md

---

## 1. Executive Summary

Round 3 performed a deep audit of the LangGraph orchestration layer (Phases 0–6 existing code). The scanner examined 5 files across `application/orchestration/` totaling ~1,497 lines: `graph.py`, `state.py`, `edges.py`, `classify_node.py`, and `enrich_node.py`.

Key conclusions: graph assembly is architecturally sound, Phase 7 interrupt insertion point is unambiguous (`interrupt_before=["escalate"]`), Phase 8 requires 3 topology changes, the `total=False` TypedDict allows backward-compatible state extensions, and the STAGE-2 #7 violation (edges.py domain logic) is LOW severity / non-blocking.

---

## 2. Full State Schema

`PipelineState(TypedDict, total=False)` — all fields optional (total=False)

| Field | Type | Reducer | Phase |
|-------|------|---------|-------|
| `user_id` | `str \| None` | replace | Ph5 |
| `project_id` | `str \| None` | replace | Ph5 |
| `system_execution` | `bool` | replace | Ph5 |
| `authorization_allowed` | `bool` | replace | Ph5 |
| `authorization_skipped` | `bool` | replace | Ph5 |
| `authorization_result` | `dict[str, object] \| None` | replace | Ph5 |
| `vulnerabilities` | `list[VulnerabilityRecord]` | replace | Ph1 |
| `report_path` | `str \| None` | replace | Ph1 |
| `enrichments` | `dict[str, EnrichmentData]` | replace | Ph2 |
| `classifications` | `dict[str, ClassificationResult]` | replace | Ph3 |
| `escalated_cves` | `Annotated[list[str], operator.add]` | **append-only** | Ph4 |
| `llm_confidence` | `dict[str, float]` | replace | Ph4 |
| `processed_count` | `int` | replace | Ph4 |
| `errors` | `Annotated[list[str], operator.add]` | **append-only** | Ph4 |
| `dlp_result` | `dict[str, object] \| None` | replace | Ph6 |
| `thread_id` | `str` | replace | meta |
| `current_node` | `str` | replace | meta |

**Phase 7 fields (informational — do NOT add until Phase 7 sprint):**
- `human_decision: Literal["approve", "reject", "escalate"] | None`
- `human_review_comment: str | None`
- `hitl_requested_at: str | None`
- `hitl_resolved_at: str | None`

**Phase 8 fields (informational — do NOT add until Phase 8 sprint):**
- `jira_ticket_url: str | None`
- `pdf_report_path: str | None`
- `output_generated_at: str | None`

---

## 3. Current Graph Topology

**Builder:** `PipelineGraphBuilder` (graph.py:90) — builder pattern with closure-based DI.

**Node registration pattern (graph.py:167–219):**
- `authorize`, `dlp`, `enrich` → async inner functions (capture injected ports via closure)
- `ingest`, `escalate` → registered directly
- `classify` → lambda (`lambda state: classify_node(state, classifier=self._classifier)`) — sync only

**Edge wiring (graph.py:221–266):**
```
START
  └─► authorize ──[route_after_authorization]──► ingest
                                              └─► END (403 denied)
        ingest ──► dlp ──► enrich ──► classify
                                        └─[route_after_classify]──► escalate ──► END
                                                                └─► END (no errors / no escalation)
```

**Invoke:** `await graph.ainvoke(initial_state, config)` — always async.

**Checkpointer:**
- Sync path: `SqliteSaver(sqlite3.connect(..., check_same_thread=False))` — correct
- Async path: `AsyncSqliteSaver.from_conn_string(...)` with post-compile attachment — correct for `ainvoke`

---

## 4. Phase 7 interrupt() Insertion Point

**Location:** `compile()` call (graph.py:~280), not inside node bodies.

**Recommended approach:** `interrupt_before=["escalate"]` at compile time (Option A):
```python
graph.compile(checkpointer=checkpointer, interrupt_before=["escalate"])
```

**Trigger condition:** `route_after_classify` returns `"escalate"` — checks `classifications` + `llm_confidence` in state. Phase 7 can call `should_escalate_route(state)` directly to decide when to interrupt.

**Checkpointer prerequisite:** Already satisfied — async path uses `AsyncSqliteSaver` (graph.py:487–491).

**Resume pattern for Streamlit UI:** `await graph.ainvoke(None, config)` where `config["configurable"]["thread_id"]` matches the interrupted run's `thread_id`.

**No node code changes required.** Only compile-time flag + state fields + Streamlit UI layer.

---

## 5. Phase 8 output_node Insertion Point

**Position:** After `escalate` AND after classify `"continue"` path.

**Target topology:**
```
classify → [route_after_classify] → escalate → output → END
                                 → output → END  (continue path, bypasses escalate)
```

**Required changes to `_add_edges()` (graph.py:246–264):**
1. **Remove:** `escalate → conditional → END` (the `route_after_escalate` edge)
2. **Add:** `escalate → output` (direct edge, no conditional)
3. **Change:** classify `"continue"` path → `output` (instead of `END`)
4. **Add:** `output → END` (direct edge)

**Required change to `_add_nodes()`:** `self._graph.add_node("output", output_node)`

---

## 6. STAGE-2 Violation #7 — edges.py Domain Logic

**Source:** STAGE-2 audit finding, severity LOW.

**Location:** `calculate_batch_discrepancies()` function (edges.py:119–200)

**Violation — exact content:**
```python
# edges.py:119–200 contains:
# - Two-pass discrepancy calculation algorithm (lines 146–198)
# - DiscrepancyHistory management with adaptive threshold via percentile (line 170)
# - ThresholdConfig default value application (line 140)
# - Imports of domain dataclasses: DiscrepancyHistory, DiscrepancyResult, ThresholdConfig
```

**Clean routing functions** (NOT the violation):
- `route_after_classify` → delegates to `should_escalate_route` → calls `check_any_escalation_needed` from `utils.py`
- `route_after_escalate` → thin conditional, always returns `"end"`

**Proposed fix (non-blocking, LOW severity):**
Move `calculate_discrepancy`, `calculate_batch_discrepancies`, and `should_escalate_route` to either:
- `application/orchestration/utils.py` (existing file), or
- New `domain/services/uncertainty_service.py`

`edges.py` should retain only thin routing functions that delegate to the service.

**Phase 7 impact:** NONE. `should_escalate_route(state)` is directly reusable as the interrupt trigger condition even in its current location.

---

## 7. Correlation ID / run_id Propagation

**thread_id lifecycle (graph.py:448–469):**
```python
initial_state = create_initial_state(
    thread_id=thread_id or str(uuid.uuid4()),  # auto-generated if None
)
config: RunnableConfig = {"configurable": {"thread_id": initial_state["thread_id"]}}
```

**Dual storage:** `thread_id` lives in both `PipelineState["thread_id"]` (state field) AND `RunnableConfig["configurable"]` (LangGraph checkpointer key). Both copies carry the same UUID.

**run_id:** No separate field. LangGraph generates an internal `run_id` per `ainvoke` call but it is not surfaced in state. `thread_id` serves as both correlation ID and checkpoint key.

**Structlog propagation:** Each node logs `thread_id=state.get("thread_id")`. Graph logs at `pipeline_execution_started` and `pipeline_execution_complete` (graph.py:471–503). Coverage: good.

**Phase 7 resume requirement:** Streamlit UI must pass same `thread_id` in config to resume checkpointed state.

---

## 8. Key Findings Summary

1. **Graph assembly is correct and Phase 7-ready**: Builder + closure DI pattern is sound; `AsyncSqliteSaver` checkpointer already in place; no changes to existing nodes required to add `interrupt_before=["escalate"]`.

2. **Phase 7 insertion is single-point, compile-time**: `interrupt_before=["escalate"]` in `compile()` is sufficient. `should_escalate_route(state)` is the reusable trigger condition already implemented in edges.py.

3. **Phase 8 requires 3 topology changes**: Remove `route_after_escalate` conditional, add `escalate → output` direct edge, redirect classify `"continue"` to `output`. No existing node logic changes.

4. **State schema is backward-compatible**: `total=False` TypedDict allows Phase 7/8 fields to be added without breaking any existing node. `escalated_cves` and `errors` already have `operator.add` reducers — correct for accumulation patterns.

5. **STAGE-2 #7 is non-blocking**: The edges.py domain logic violation is LOW severity. It does not block Phase 7 implementation. The clean routing functions are already in place and reusable.
