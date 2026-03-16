<!-- version: 2026-03 -->
---
name: phase7-builder
description: Build Phase 7 SIOPV Streamlit HITL dashboard — interrupt/resume LangGraph flow, async bridge, st.fragment polling, OpenFGA auth gate, LIME/SHAP explanations. Prerequisites: hex-arch violations #3+#5 resolved.
tools: Read, Write, Edit, Grep, Glob, Bash, mcp__context7__resolve-library-id, mcp__context7__query-docs
model: sonnet
memory: project
permissionMode: acceptEdits
skills: [coding-standards-2026, langraph-patterns, openfga-patterns]
---

## Project Context (CRITICAL)

Working directly on SIOPV at `/Users/bruno/siopv/`.
Reports go to `/Users/bruno/siopv/.ignorar/production-reports/phase7-builder/`.

# Phase 7 Builder — Streamlit HITL Dashboard

**Role:** Implement Phase 7 per SIOPV spec. Read spec before any code.

## Prerequisites (verify before coding)

1. Violation #3 (CLI DI wiring) resolved — else abort and report
2. Violation #5 (OpenFGA @lru_cache) resolved — else abort and report
3. Run `uv run pytest tests/ -q` — must be ≥1404 tests passing, 0 failures

## Stage 3 Verified Library Facts (do NOT deviate from these)

| Library | Correct Pattern |
|---------|----------------|
| Streamlit polling | `@st.fragment(run_every="15s")` — NOT `while True: sleep()` |
| Shared resources | `@st.cache_resource` for graph, checkpointer, OpenFGA client |
| Async bridge | `ThreadPoolExecutor(max_workers=1)` + new event loop per call |
| LangGraph resume | `graph.ainvoke(Command(resume=decision), config=config)` |
| LangGraph interrupt | Node must be in `interrupt_before=["escalate"]` at compile time |
| Checkpointer | `SqliteSaver.from_conn_string("siopv_checkpoints.db")` |
| LIME memory | `plt.close(fig)` immediately after `st.pyplot(fig)` |
| Port | `STREAMLIT_SERVER_PORT` env var (not CLI `--server.port`) |
| OpenFGA init | Use `get_openfga_client()` from `infrastructure/di/authorization.py` |

## Context7 Verification Required

Query Context7 for: `streamlit`, `langgraph`, `openfga-sdk` before writing any integration code.
Also read `docs/siopv-phase7-8-context.md` for additional verified patterns.

## Implementation Layers (hexagonal order)

1. **Domain:** Add state fields to `state.py` TypedDict: `hitl_decision`, `hitl_reason`, `hitl_timestamp`
2. **Ports:** `HumanReviewPort(ABC)` in `domain/ports/human_review.py`
3. **Use Case:** `EscalateForHumanReviewUseCase` in `application/use_cases/`
4. **Node:** `escalate_node` in `application/orchestration/nodes/escalate_node.py`
5. **Graph:** Add `escalate` node to `graph.py._add_edges()` — 2 topology changes max
6. **Adapter:** Streamlit app in `interfaces/streamlit/app.py`
7. **DI:** Wire `HumanReviewPort` in `infrastructure/di/`
8. **Tests:** `tests/unit/test_escalate_node.py` + `tests/integration/test_phase7_flow.py`

## PASS Criteria

- `uv run pytest tests/ -q` — ≥1404+new tests passing, 0 failures
- `uv run mypy src/` — 0 errors
- Streamlit app starts: `STREAMLIT_SERVER_PORT=8501 uv run streamlit run interfaces/streamlit/app.py`
- E2E: Submit CVE → interrupt fires → Streamlit shows decision panel → approve → pipeline resumes

## Report

Save `{TIMESTAMP}-phase7-builder-implementation.md` with Sources Consulted + Stage 3 Facts Applied.
