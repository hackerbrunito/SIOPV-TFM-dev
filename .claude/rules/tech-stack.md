---
paths:
  - "**/*.py"
  - "pyproject.toml"
---

# Tech Stack

- Python 3.11+ (`list[str]`, `X | None`)
- uv (not pip)
- Pydantic v2
- httpx async
- structlog
- pathlib
- langgraph (LangGraph 0.2+)
- streamlit (Phase 7 — use `@st.fragment`, `st.cache_resource`, ThreadPoolExecutor bridge)
- fpdf2 (Phase 8 — `add_font()` requires `fname` since v2.7)
- redis.asyncio (not aioredis — merged into redis-py ≥4.2)
- openfga-sdk
- presidio-analyzer / presidio-anonymizer
- langsmith (tracing — requires LANGCHAIN_API_KEY env var)

## Before Write/Edit
Query Context7 MCP for library syntax.

## After Write/Edit
Execute /verify before commit.
