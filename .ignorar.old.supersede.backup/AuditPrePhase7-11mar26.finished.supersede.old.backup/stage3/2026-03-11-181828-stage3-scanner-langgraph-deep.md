# STAGE-3 Deep Scan: LangGraph State Management
**Agent:** scanner-langgraph
**Timestamp:** 2026-03-11-181828
**Scope:** Phases 0–6 existing code only (NOT Phase 7/8 requirements)

---

## 1. Files Scanned

| File | Lines |
|------|-------|
| `application/orchestration/graph.py` | 517 |
| `application/orchestration/state.py` | 208 |
| `application/orchestration/edges.py` | 264 |
| `application/orchestration/nodes/classify_node.py` | 243 |
| `application/orchestration/nodes/enrich_node.py` | 265 |

---

## 2. Graph Assembly Pattern

### Builder Pattern
`PipelineGraphBuilder` class (graph.py:90) follows standard builder pattern:
- `build()` → calls `_add_nodes()` + `_add_edges()` → returns `self`
- `compile(with_checkpointer=True)` → attaches checkpointer, returns `CompiledStateGraph`
- `create_pipeline_graph()` factory function wraps builder for convenience (graph.py:361)

### Node Registration
Nodes use closure pattern to inject dependencies (graph.py:167–219):
- `authorize`, `dlp`, `enrich` → async inner functions (capture `self._*` ports via closure)
- `ingest`, `escalate` → registered directly (no injected deps)
- `classify` → **lambda** (`lambda state: classify_node(state, classifier=self._classifier)`) — sync only

### Edge Registration (graph.py:221–266)
```
START → authorize
authorize → {ingest, END}  [conditional: route_after_authorization]
ingest → dlp → enrich → classify  [linear edges]
classify → {escalate, END, END}  [conditional: route_after_classify]
escalate → {END}  [conditional: route_after_escalate — always "end"]
```

### Checkpointer Configuration
**Sync path** (`_create_checkpointer`, graph.py:268–284):
```python
conn = sqlite3.connect(str(db_path), check_same_thread=False)  # ✅ correct
return SqliteSaver(conn)
```
**Async path** (`run_pipeline`, graph.py:487–491):
```python
async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
    graph = builder.build().compile(with_checkpointer=False)
    graph.checkpointer = checkpointer  # ⚠️ post-compile attachment
```
`check_same_thread=False` is set correctly on sync path. Async path uses `AsyncSqliteSaver` (correct for `ainvoke`).

### Invoke Pattern (graph.py:480–494)
```python
result = await graph.ainvoke(initial_state, config)
```
`config` carries `thread_id` in `configurable` dict. Always async (`ainvoke`).

---

## 3. State Schema

`PipelineState(TypedDict, total=False)` — all fields optional by Python typing (total=False).

| Field | Type | Annotated Reducer | Phase |
|-------|------|-------------------|-------|
| `user_id` | `str \| None` | — | Ph5 |
| `project_id` | `str \| None` | — | Ph5 |
| `system_execution` | `bool` | — | Ph5 |
| `authorization_allowed` | `bool` | — | Ph5 |
| `authorization_skipped` | `bool` | — | Ph5 |
| `authorization_result` | `dict[str, object] \| None` | — | Ph5 |
| `vulnerabilities` | `list[VulnerabilityRecord]` | — | Ph1 |
| `report_path` | `str \| None` | — | Ph1 |
| `enrichments` | `dict[str, EnrichmentData]` | — | Ph2 |
| `classifications` | `dict[str, ClassificationResult]` | — | Ph3 |
| `escalated_cves` | `Annotated[list[str], operator.add]` | append-only | Ph4 |
| `llm_confidence` | `dict[str, float]` | — | Ph4 |
| `processed_count` | `int` | — | Ph4 |
| `errors` | `Annotated[list[str], operator.add]` | append-only | Ph4 |
| `dlp_result` | `dict[str, object] \| None` | — | Ph6 |
| `thread_id` | `str` | — | meta |
| `current_node` | `str` | — | meta |

**Fields needed for Phase 7 (HITL)** — do NOT add yet, informational:
- `human_decision: Literal["approve", "reject", "escalate"] | None`
- `human_review_comment: str | None`
- `hitl_requested_at: str | None`
- `hitl_resolved_at: str | None`

**Fields needed for Phase 8 (output)** — do NOT add yet, informational:
- `jira_ticket_url: str | None`
- `pdf_report_path: str | None`
- `output_generated_at: str | None`

---

## 4. Topology Map

### Current Topology
```
START
  └─► authorize ──[route_after_authorization]──► ingest
                                              └─► END (403 denied)
        ingest ──► dlp ──► enrich ──► classify
                                        └─[route_after_classify]──► escalate ──► END
                                                                └─► END (no errors, no escalation)
```

### Phase 7: interrupt() Insertion Point
**Insert AFTER `classify`, BEFORE `escalate`** — in `_add_edges()` (graph.py:246–264):

Option A — interrupt on escalate node entry:
```python
# graph.compile(checkpointer=checkpointer, interrupt_before=["escalate"])
```
Option B — interrupt inside escalate_node body using `langgraph.types.interrupt()`.

**Recommended**: Option A (compile-time `interrupt_before=["escalate"]`). Requires no node changes.
The `route_after_classify` → `"escalate"` path is the trigger. The `"continue"` path bypasses HITL.

**Prerequisite**: `AsyncSqliteSaver` with `check_same_thread=False` — already satisfied by async path (graph.py:487).

### Phase 8: output_node Insertion Point
**Insert AFTER `escalate`** and AFTER the classify `"continue"` path:

```
classify → [route_after_classify] → escalate → output → END
                                 → output → END  (continue path)
```

Changes needed in `_add_edges()`:
1. Remove: `escalate → conditional → END`
2. Add: `escalate → output` (direct edge)
3. Change: classify `"continue"` → `output` (instead of END)
4. Add: `output → END`

Node registration in `_add_nodes()`: add `self._graph.add_node("output", output_node)`.

---

## 5. edges.py Domain Logic Violation (STAGE-2 #7)

### Location: `calculate_batch_discrepancies()` (edges.py:119–200)

**Violation**: Full business domain logic embedded in edge routing module:
- Two-pass discrepancy calculation algorithm (lines 146–198)
- `DiscrepancyHistory` management (adaptive threshold via percentile, line 170)
- `ThresholdConfig` default value application (line 140)
- Import of domain dataclasses: `DiscrepancyHistory`, `DiscrepancyResult`, `ThresholdConfig`

**Severity**: LOW (per STAGE-2). The actual routing functions (`route_after_classify`, `route_after_escalate`) are clean — they delegate to `should_escalate_route` which calls `check_any_escalation_needed` from `utils.py`. The violation is in the utility functions that live in `edges.py` but belong in a domain service.

**Impact on Phase 7**: The escalation condition (`should_escalate_route`, edges.py:28–61) IS reusable as the interrupt trigger — it checks `classifications` + `llm_confidence` in state. Phase 7 can call `should_escalate_route(state)` directly to decide when to `interrupt()`.

**Fix** (not blocking Phase 7, LOW severity):
Move `calculate_discrepancy`, `calculate_batch_discrepancies`, and `should_escalate_route` to `application/orchestration/utils.py` or a new `domain/services/uncertainty_service.py`. `edges.py` should only contain thin routing functions that call the service.

---

## 6. Correlation ID / run_id Propagation

### thread_id (graph.py:448–469)
```python
initial_state = create_initial_state(
    thread_id=thread_id or str(uuid.uuid4()),  # auto-generated if None
)
config: RunnableConfig = {"configurable": {"thread_id": initial_state["thread_id"]}}
```

- `thread_id` is stored in `PipelineState["thread_id"]` (state field)
- `thread_id` is also passed in `RunnableConfig["configurable"]` (LangGraph checkpointer key)
- Both copies are in sync — same UUID value
- Every node logs `thread_id=state.get("thread_id")` for correlation

### run_id
- No separate `run_id` field exists. `thread_id` serves as both correlation ID and checkpoint key.
- LangGraph internally generates a `run_id` per `ainvoke` call but it is not surfaced in state.
- For Phase 7, the Streamlit UI will need `thread_id` to resume checkpointed state via `ainvoke(None, config)`.

### Propagation Quality
Good: `thread_id` logged at `pipeline_execution_started` and `pipeline_execution_complete` (graph.py:471–503). Each node logs its own `thread_id`. Structlog context should carry it consistently.

---

## 7. Summary

1. **Graph assembly is clean**: Builder pattern with closure-based DI is correct. `check_same_thread=False` on sync SQLite path is set correctly. Async path uses `AsyncSqliteSaver` correctly.

2. **Phase 7 interrupt point is clear**: `interrupt_before=["escalate"]` at compile time is the minimal-change insertion point. No node code changes required. Checkpointer prerequisites already satisfied.

3. **Phase 8 output_node requires 3 topology changes**: remove escalate→END conditional, add escalate→output edge, redirect classify "continue" path to output instead of END.

4. **State schema is Phase 7/8 ready**: `total=False` TypedDict means new fields can be added without breaking existing nodes. `escalated_cves` has `operator.add` reducer — correct for append-only HITL decisions.

5. **STAGE-2 #7 (edges.py domain logic) is LOW severity and non-blocking**: `route_after_classify` and `route_after_escalate` are clean routing functions. The violation is in utility functions co-located in edges.py. The `should_escalate_route` function is directly reusable as Phase 7 interrupt condition check.
