# STAGE-3 Round 1 — Aggregated Research Report
**Aggregator:** round1-aggregator
**Timestamp:** 2026-03-11-175932
**Sources:** 3 researcher reports (streamlit-lime, jira-pdf, infra)
**Status:** COMPLETE

---

## 1. Executive Summary

Round 1 covered all key library APIs required for Phase 7 (HITL Streamlit dashboard) and
Phase 8 (Jira + PDF output). Three specialized researchers verified patterns via Context7
(Tier 1) and WebSearch (Tier 3) without relying on training data. No training-data-only
patterns were used. Coverage: Streamlit 1.x, LIME, Jira REST v3, fpdf2 2.8.7, LangGraph
0.2+ interrupt/resume, LangSmith SDK, Redis asyncio, FastAPI + OpenTelemetry.

---

## 2. Key Verified Findings by Library

### 2.1 Streamlit 1.x
- **Polling pattern**: `@st.fragment(run_every="15s")` is the correct 1.x pattern. It
  reruns only the fragment (not the full page). Do NOT use `time.sleep() + st.rerun()` in
  production — blocks thread, full page rerun.
- **Port env var**: `DASHBOARD_PORT` is NOT natively recognized. Must translate to
  `STREAMLIT_SERVER_PORT` or pass `--server.port` CLI flag in launch wrapper.
- **Auth gate**: `st.context.headers.get("Authorization")` reads bearer tokens for manual
  OpenFGA validation. Native OIDC available via `st.login("keycloak")` configured in
  `.streamlit/secrets.toml`.
- **Session state machine**: Track `stage` / `current_thread_id` / `decision` in
  `st.session_state`. Call `st.rerun()` on state transitions.
- **Timeout cascade UI**: `@st.fragment(run_every="60s")` + `st.progress()` gives live
  countdown. Auto-escalation logic must live in LangGraph, NOT Streamlit.

### 2.2 LIME (lime-ml)
- **Constructor**: `LimeTabularExplainer(training_data, mode, feature_names, class_names,
  categorical_features, discretize_continuous=True, random_state=42)`
- **explain_instance**: `explainer.explain_instance(data_row, predict_fn, labels=(1,),
  num_features=10, num_samples=5000)`
- **Streamlit embedding**: `st.pyplot(fig, use_container_width=True)` — MUST call
  `plt.close(fig)` after every render to prevent memory leaks in long-running Streamlit apps.
- **Alternative**: `exp.as_list(label=1)` → `st.bar_chart(df.set_index("feature"))` for
  native Streamlit look without matplotlib.
- **Context7 note**: LIME is not in Context7 (confused with Lime Elements). Verified via
  `lime-ml.readthedocs.io` directly.

### 2.3 Jira REST API v3
- **Auth**: `Basic base64(JIRA_EMAIL:JIRA_API_TOKEN)` header — no OAuth needed.
  Env vars: `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_BASE_URL`.
- **ADF format is mandatory**: `description` must use `{"version":1,"type":"doc","content":[...]}`
  structure. Plain text strings are rejected by the API.
- **Endpoint**: `POST {JIRA_BASE_URL}/rest/api/3/issue` — fields: `project.key`,
  `summary`, `issuetype.name` (minimal required).
- **CVSS → Jira priority**: ≥9.0 → Highest, 7.0–8.9 → High, 4.0–6.9 → Medium, 0.1–3.9 → Low.
- **Client choice**: Use raw `httpx.AsyncClient` (not `jira` or `atlassian-python-api` libs).
  Both Python clients are synchronous (requests-based) and would block LangGraph's event loop.
  httpx is already a SIOPV dependency.

### 2.4 fpdf2 (current: 2.8.7)
- **Target**: `fpdf2>=2.7.0` — 2.8.7 is the Feb 2026 release.
- **Breaking change (2.6→2.7)**: `fname` parameter is NOW REQUIRED in `add_font()`.
- **Table API**: `pdf.table(col_widths=(...))` context manager — idiomatic 2.7+ API.
  Supports `colspan`, `rowspan`, image cells.
- **TOC**: `pdf.insert_toc_placeholder(toc.render_toc, allow_extra_pages=True)` — correct
  2.7+ API for compliance report navigation.
- **Unbreakable rows**: `pdf.unbreakable()` context manager — use for audit tables to
  prevent row splits across pages.
- **Total pages**: `pdf.alias_nb_pages()` must be called BEFORE any `add_page()`.
  Use `{nb}` in footer string.
- **Removed**: `open()` and `close()` methods removed in 2.7. Never call them.
- **SVG support**: `image()` now inserts SVG as PDF vector paths — requires `defusedxml`.

### 2.5 LangGraph 0.2+ (interrupt / resume)
- **interrupt API**: `interrupt(payload)` inside a node surfaces payload to caller.
  Returns the resume value when `Command(resume=...)` is invoked.
- **Resume**: `graph.invoke(Command(resume={"action": "approve"}), config=config)`.
  Async streaming: `graph.astream(initial_input, stream_mode=["messages","updates"])`.
- **Checkpointer requirement**: `interrupt()` requires checkpointer at compile time.
  Without it, raises at runtime.
- **SQLite**: `SqliteSaver(sqlite3.connect("db.db", check_same_thread=False))` —
  `check_same_thread=False` is CRITICAL for async FastAPI/Streamlit contexts.
- **State serialization**: All TypedDict state values must be JSON-serializable.
  Do not store httpx clients, file handles, etc. in state.
- **Phase 8 topology**: Adding `output_node` at END is safe for all threads.
  In-flight interrupted threads can safely enter new downstream nodes.

### 2.6 LangSmith SDK
- **Client init**: `Client()` reads `LANGSMITH_API_KEY` + `LANGSMITH_PROJECT` from env.
  Also needs `LANGSMITH_TRACING_V2=true` for auto-tracing LangGraph.
- **list_runs**: `client.list_runs(project_name=..., filter='eq(status,"success")',
  is_root=True, limit=50)` — returns iterator.
- **Tag for retrieval**: Set `config={"metadata": {"thread_id": ...}}` at invocation time.
  Retrieve via `filter=f'eq(metadata_key,"thread_id","{thread_id}")'`.
- **CoT trace for PDF**: Extract `llm_calls` with `name`, `start_time`, `end_time`,
  `inputs`, `outputs`, `total_tokens` per run.

### 2.7 Redis asyncio
- **Import**: `import redis.asyncio as redis` — NOT `aioredis` (deprecated, merged into
  redis-py >= 4.2). Do NOT add `aioredis` as a dependency.
- **Connection**: `redis.from_url(REDIS_URL)` handles connection pooling automatically.
- **Set+expire atomic**: `await client.setex(key, ttl_seconds, json.dumps(data))`.
- **Key convention**: `epss:score:{CVE_ID_UPPERCASE}` — 24h TTL (EPSS updates daily).
- **Close**: `await client.aclose()` (not `close()`).

### 2.8 FastAPI + OpenTelemetry
- **Instrument order**: TracerProvider setup → `FastAPI()` creation → `FastAPIInstrumentor.instrument_app(app)`.
  Order is mandatory.
- **excluded_urls**: Pass `excluded_urls="healthz,readyz,metrics"` to avoid noise.
- **httpx OTel**: `HTTPXClientInstrumentor().instrument()` once at startup covers all
  `AsyncClient` instances. Module-level `httpx.get()` / `httpx.post()` are NOT covered.
  Issue: opentelemetry-python-contrib #1742.

---

## 3. Critical API Facts Confirmed

| Fact | Library | Confirmed |
|------|---------|-----------|
| `@st.fragment(run_every="Xs")` for polling | Streamlit | Context7 + WebSearch |
| `STREAMLIT_SERVER_PORT` (not `DASHBOARD_PORT`) | Streamlit | WebSearch |
| `st.context.headers` for auth gate | Streamlit | Context7 |
| `plt.close(fig)` after `st.pyplot()` is mandatory | LIME+Streamlit | WebSearch |
| ADF format mandatory for Jira v3 description | Jira API | Atlassian docs |
| `httpx.AsyncClient` not jira/atlassian-python-api | Jira API | Verified |
| `fname` required in `add_font()` since fpdf2 2.7 | fpdf2 | Context7 + CHANGELOG |
| `pdf.alias_nb_pages()` before any `add_page()` | fpdf2 | Context7 |
| `interrupt()` requires checkpointer at compile time | LangGraph | Context7 |
| `check_same_thread=False` for async SQLite | LangGraph | Context7 |
| `redis.asyncio` replaces `aioredis` (redis-py>=4.2) | Redis | WebSearch |
| `HTTPXClientInstrumentor` doesn't cover `httpx.get()` | OTel | Issue #1742 |

---

## 4. Conflicts / Discrepancies Between Agents

**None found.** All three agents used non-overlapping library domains and produced
consistent patterns where they touched shared infrastructure:

- LangGraph SQLite resume: researcher-streamlit-lime and researcher-infra agree on
  `SqliteSaver.from_conn_string` / `SqliteSaver(conn)` variants — both are valid;
  from_conn_string is a convenience wrapper.
- CVSS mapping: researcher-jira-pdf defined it; no contradictions from other agents.
- httpx async pattern: both researcher-jira-pdf and researcher-infra recommend
  `httpx.AsyncClient` for all external calls — consistent.

---

## 5. Gaps / Unresolved Questions for Round 2

1. **Streamlit authentication session persistence**: `st.context.headers` vs `st.user` —
   which integrates better with SIOPV's existing Keycloak + OpenFGA setup? Round 2 should
   verify the `.streamlit/secrets.toml` OIDC config format for Keycloak specifically.

2. **LIME performance under load**: `num_samples=3000` was suggested for live dashboards.
   Is 3000 samples sufficient for XGBoost with ~30 features? Needs empirical verification
   or benchmarking guidance.

3. **LangSmith filter syntax for metadata**: The filter string
   `eq(metadata_key,"thread_id","value")` — exact syntax needs confirmation against
   current SDK (filter DSL has changed across versions).

4. **fpdf2 image embedding for LIME plots**: Can LIME matplotlib figures be embedded
   directly as PNG bytes (in-memory) without writing to disk? Round 2 should verify
   `pdf.image(io.BytesIO(...))` support in fpdf2 2.7+.

5. **Redis connection pooling limits**: `redis.from_url()` defaults — what is the default
   pool size? Is it sufficient for concurrent graph threads?

6. **OTel + LangGraph span correlation**: How to correlate OTel traces (FastAPI request
   span) with LangSmith traces (LangGraph run)? Need W3C trace context propagation pattern.

---

## 6. Libraries Verified Summary

| Researcher | Libraries | Context7 | WebSearch | Training Data Used? |
|------------|-----------|----------|-----------|---------------------|
| researcher-streamlit-lime | Streamlit, LIME | ✅ (Streamlit only) | ✅ Both | NO |
| researcher-jira-pdf | fpdf2, Jira v3, jira/atlassian libs | ✅ (fpdf2) | ✅ All | NO |
| researcher-infra | LangGraph, LangSmith, Redis, FastAPI, OTel | ✅ (LangGraph, LangSmith, FastAPI, OTel) | ✅ All | NO |

**Tier 1 (Context7) gaps:**
- LIME: not in Context7 (confused with Lime Elements) → used readthedocs.io
- Jira REST API: not a Python lib → used developer.atlassian.com
- Redis asyncio: not in Context7 → used WebSearch

All gaps were filled by Tier 3 (WebSearch) using authoritative sources (official docs,
official GitHub repos, readthedocs). No training-data-only patterns used.

---

*Report generated by round1-aggregator | Stage 3 Round 1 | 2026-03-11-175932*
