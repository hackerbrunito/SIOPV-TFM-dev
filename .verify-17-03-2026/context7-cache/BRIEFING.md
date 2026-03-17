# Pre-Wave Library Research — BRIEFING

> Generated: 2026-03-17 | All cache files in this directory

| Library | Cache File | Key Pattern |
|---------|-----------|-------------|
| langgraph | langgraph.md | `interrupt()` pauses execution, `Command(resume=value)` resumes; node restarts from beginning on resume; always use durable checkpointer (SQLite/Postgres) with consistent `thread_id` |
| pandas | pandas.md | Pandas 3.0 (Jan 2026): Copy-on-Write is only mode; chained assignment broken — always use `.loc[]`; PyArrow strings default; no need for `.copy()` |
| streamlit | streamlit.md | `@st.dialog(title)` creates modal inheriting `@st.fragment` behavior (partial reruns); one dialog at a time; close with `st.rerun()`; store results in `st.session_state` |
| structlog | structlog.md | `get_logger().bind(**ctx)` for context; `cache_logger_on_first_use=True` in production; `JSONRenderer` for prod, `ConsoleRenderer` for dev; `make_filtering_bound_logger(level)` for performance |
| pytest | pytest.md | Factory fixtures for object creation; `@pytest.mark.parametrize` with `pytest.param` for IDs/marks; indirect parametrize for fixture params; `--strict-markers` in config; `@pytest.mark.asyncio` for async tests |
