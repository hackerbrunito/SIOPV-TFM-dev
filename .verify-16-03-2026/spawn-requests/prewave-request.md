# SPAWN REQUEST — PRE-WAVE (Library Researcher)

**Number of agents:** 1

**VERIFY_DIR:** `/Users/bruno/siopv/.verify-16-03-2026`
(Directory structure already created: context7-cache/, scans/, fixes/, reports/, handoffs/)

**Context:** This is a FORCED full /verify run. All 62 substantive Python source files in `src/siopv/` are in scope (95 total including `__init__.py`). No pending markers exist (cleared during previous failed attempts). The pre-wave researcher must build the Context7 cache that all downstream agents will read.

---

## Agent 1

- **Name:** `prewave-researcher`
- **Task:** Query Context7 for all 19 external libraries used in the project, build shared cache for downstream agents
- **Prompt:**

```
You are the pre-wave library researcher for the SIOPV /verify pipeline.

VERIFY_DIR: /Users/bruno/siopv/.verify-16-03-2026

## HANDOFF PROTOCOL (Rule 1 — mandatory first action)
Write handoff file NOW before doing anything else:
Path: /Users/bruno/siopv/.verify-16-03-2026/handoffs/handoff-prewave-researcher.md
Content:
  task: Query Context7 for all libraries, build shared cache
  libraries_to_query: anthropic, chromadb, httpx, imblearn, jwt, langchain_core, langgraph, lime, numpy, openfga_sdk, optuna, pydantic, pydantic_settings, shap, sklearn, structlog, tenacity, typer, xgboost
  start: 2026-03-16T06:00:00Z

## TOOL OUTPUT OFFLOADING (Rule 2 — mandatory)
After EVERY get-library-docs call (responses are 10,000+ tokens):
→ Write full response to /Users/bruno/siopv/.verify-16-03-2026/context7-cache/{library}.md IMMEDIATELY
→ Keep in context only: file path + one-line summary of key patterns
→ Never hold the raw response in memory past the write

## AT 65% CONTEXT
Stop querying. Write handoff with remaining libraries list. Report to orchestrator.

## YOUR TASK

Libraries to query (discovered from all source files in src/siopv/):
anthropic, chromadb, httpx, imblearn, jwt, langchain_core, langgraph, lime, numpy, openfga_sdk, optuna, pydantic, pydantic_settings, shap, sklearn, structlog, tenacity, typer, xgboost

For each library:
1. mcp__context7__resolve-library-id(libraryName="{library}")
2. mcp__context7__get-library-docs(context7CompatibleLibraryId="{id}", topic="current API patterns best practices")
3. Write full response to /Users/bruno/siopv/.verify-16-03-2026/context7-cache/{library}.md IMMEDIATELY
4. Append to handoff: "library: {name} | status: done | key_pattern: {one line}"

After all libraries are done, write BRIEFING.md:
Path: /Users/bruno/siopv/.verify-16-03-2026/context7-cache/BRIEFING.md
Content: one-line summary per library — the key pattern or API fact for that library.
Format:
  pydantic: ConfigDict replaces class Config; model_validator replaces root_validator
  httpx: AsyncClient for async HTTP; no requests library
  structlog: get_logger() + bind(); no print() or logging.getLogger()
  ...

When done:
SendMessage(to="orchestrator", message="PREWAVE AGENT prewave-researcher COMPLETE: PASS — {N} libraries cached, BRIEFING.md written")
```

---

**Awaiting your confirmation before proceeding.**
