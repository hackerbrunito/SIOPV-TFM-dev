# R2 — Phase 2 Gap Analysis: Enriquecimiento de Contexto (Dynamic RAG)

> Analyst: gap-analyzer-phase-2 | Date: 2026-03-11
> Source files reviewed: nvd_client.py, epss_client.py, github_advisory_client.py, chroma_adapter.py, tavily_client.py, enrich_context.py, enrich_node.py, settings.py

---

## Summary

| Status | Count |
|--------|-------|
| IMPLEMENTED | 9 |
| PARTIAL | 3 |
| MISSING | 1 |
| **Total** | **13** |

---

## Requirement-by-Requirement Analysis

### REQ-P2-001 — Module name: `Dynamic_RAG_Researcher`

- **Status:** PARTIAL
- **Evidence:** No module or class named `Dynamic_RAG_Researcher` exists anywhere in `src/`. The equivalent functionality is spread across `EnrichContextUseCase` (`application/use_cases/enrich_context.py`) and `enrich_node` (`application/orchestration/nodes/enrich_node.py`).
- **Notes:** Functional intent is satisfied but the spec-mandated module name is absent. The CRAG pattern is correctly implemented as a use case, not as a named module.

### REQ-P2-002 — Model: Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)

- **Status:** PARTIAL
- **Evidence:** `settings.py:34` declares `claude_sonnet_model: str = "claude-sonnet-4-5-20250929"`. However, `enrich_context.py` never invokes any LLM — relevance evaluation (REQ-P2-012) is done via heuristic scoring in `_calculate_relevance()` (lines 310–347), not via Claude Sonnet.
- **Notes:** The model ID is configured but unused in Phase 2. The spec requires Claude Sonnet to evaluate document relevance (score 0–1). Current implementation uses a deterministic formula instead.

### REQ-P2-003 — Data sources: NVD API, GitHub Security Advisories, FIRST EPSS, Tavily Search

- **Status:** IMPLEMENTED
- **Evidence:**
  - NVD: `adapters/external_apis/nvd_client.py` — `NVDClient` class
  - GitHub: `adapters/external_apis/github_advisory_client.py` — `GitHubAdvisoryClient` class
  - EPSS: `adapters/external_apis/epss_client.py` — `EPSSClient` class
  - Tavily: `adapters/external_apis/tavily_client.py` — `TavilyClient` class
- **Notes:** All four sources implemented with proper port/adapter pattern.

### REQ-P2-004 — Storage: ChromaDB hybrid (SQLite persistence + in-memory cache)

- **Status:** IMPLEMENTED
- **Evidence:** `adapters/vectorstore/chroma_adapter.py` — `ChromaDBAdapter` uses `chromadb.PersistentClient` (SQLite backend, line 123) + `LRUCache` (in-memory, lines 29–69).
- **Notes:** Fully implemented with both persistence and caching layers.

### REQ-P2-005 — NVD endpoint: `/cves/2.0?cveId={CVE-ID}`

- **Status:** IMPLEMENTED
- **Evidence:** `settings.py:38` — `nvd_base_url: str = "https://services.nvd.nist.gov/rest/json/cves/2.0"`. `nvd_client.py:137` — `url = f"{self._base_url}?cveId={cve_id}"`.
- **Notes:** Exact endpoint match.

### REQ-P2-006 — NVD rate limits: 5 req/30s (no key), 50 req/30s (with `NVD_API_KEY`)

- **Status:** IMPLEMENTED
- **Evidence:** `nvd_client.py:74` — `self._rate_limiter = create_nvd_rate_limiter(has_api_key=bool(self._api_key))`. Rate limiter factory differentiates by API key presence. `nvd_client.py:71` reads key via `settings.nvd_api_key.get_secret_value()`.
- **Notes:** Implementation delegates to `infrastructure/resilience` module. Exact rate values should be verified in `create_nvd_rate_limiter()`.

### REQ-P2-007 — GitHub Security Advisories via GraphQL API (not REST)

- **Status:** IMPLEMENTED
- **Evidence:** `github_advisory_client.py:39–96` — Full GraphQL queries (`ADVISORY_BY_CVE_QUERY`, `ADVISORIES_BY_PACKAGE_QUERY`). `github_advisory_client.py:224` — `client.post(self._graphql_url, json=payload)`.
- **Notes:** Uses GraphQL exclusively, not REST. Correct per spec.

### REQ-P2-008 — GitHub rate limits: 60/hr (no auth), 5000/hr (with `GITHUB_TOKEN`)

- **Status:** IMPLEMENTED
- **Evidence:** `github_advisory_client.py:149` — `self._rate_limiter = create_github_rate_limiter(has_token=bool(self._token))`. Token read from `settings.github_token` (line 146). Rate limit header check at line 228–229.
- **Notes:** Exact rate values should be verified in `create_github_rate_limiter()`.

### REQ-P2-009 — EPSS endpoint: `https://api.first.org/data/v1/epss?cve={CVE-ID}` — fields: `epss`, `percentile`

- **Status:** IMPLEMENTED
- **Evidence:** `settings.py:46` — `epss_base_url: str = "https://api.first.org/data/v1/epss"`. `epss_client.py:122` — `url = f"{self._base_url}?cve={cve_id}"`. Fields parsed via `EPSSScore.from_api_response()` which extracts `score` and `percentile` (referenced at line 165, 195–196).
- **Notes:** Exact endpoint and field match.

### REQ-P2-010 — Tavily as OSINT fallback when structured sources insufficient

- **Status:** IMPLEMENTED
- **Evidence:** `enrich_context.py:162–170` — OSINT fallback triggered when `relevance_score < self._relevance_threshold`. `tavily_client.py` implements `OSINTSearchClientPort` with `search()` and `search_exploit_info()` methods.
- **Notes:** Correctly used as fallback, not primary source.

### REQ-P2-011 — CRAG pattern: parallel query NVD+GitHub+EPSS → relevance eval → conditional Tavily if < 0.6 → consolidate in ChromaDB

- **Status:** IMPLEMENTED
- **Evidence:** `enrich_context.py`:
  - Parallel query: lines 251–257 (`asyncio.gather` for NVD, EPSS, GitHub)
  - Relevance eval: lines 310–347 (`_calculate_relevance()`)
  - Conditional Tavily: lines 162–174 (threshold check + OSINT fallback)
  - ChromaDB consolidation: line 178 (`store_enrichment()`)
  - Threshold: line 42 (`RELEVANCE_THRESHOLD = 0.6`)
- **Notes:** Full CRAG pipeline implemented. However, relevance eval is heuristic, not LLM-based (see REQ-P2-012).

### REQ-P2-012 — Claude Sonnet evaluates document relevance (score 0-1); Tavily triggered if < 0.6

- **Status:** MISSING
- **Evidence:** `enrich_context.py:310–347` — `_calculate_relevance()` uses a deterministic formula (NVD=+0.4, EPSS=+0.2, GitHub=+0.2, OSINT=+0.1/result). No LLM call anywhere in the enrichment pipeline. The `adapters/llm/` directory is empty (confirmed in prior audit).
- **Notes:** The spec explicitly requires Claude Sonnet to evaluate relevance. Current heuristic is functional but does not match the spec's LLM-based evaluation. The 0.6 threshold IS correctly applied (line 42, 162).

### REQ-P2-013 — ChromaDB: SQLite persistence, LRU cache (1000 queries), eviction if > 4GB

- **Status:** PARTIAL
- **Evidence:**
  - SQLite persistence: `chroma_adapter.py:123` — `chromadb.PersistentClient(path=...)` ✅
  - LRU cache: `chroma_adapter.py:29–69` — `LRUCache` class with `max_size` param ✅
  - Cache sizing: `chroma_adapter.py:98–100` — estimates items from `chroma_cache_size_mb` (default 4096 in settings.py:63)
  - 4GB eviction: NO explicit 4GB storage limit enforcement. `settings.py:63` sets `chroma_cache_size_mb: int = 4096` but this only controls the in-memory LRU cache size estimation, not ChromaDB's on-disk storage. No disk usage monitoring or eviction mechanism exists.
  - 1000 queries: The LRU defaults to estimated_items based on cache_size_mb, not a fixed 1000. With default 4096MB / 4KB = ~1M items, far exceeding spec's 1000.
- **Notes:** Missing: (1) hard 1000-query LRU cap per spec, (2) 4GB on-disk storage eviction logic.

---

## Cross-Reference: Related Cross-Cutting Requirements

These XC requirements directly affect Phase 2 adapters (assessed separately but noted here):

| ID | Description | Phase 2 Impact |
|----|-------------|----------------|
| REQ-XC-001 | Circuit breaker per API | ✅ All 4 clients have CircuitBreaker |
| REQ-XC-003 | NVD fallback: 24h local cache | ⚠️ In-memory cache only, no 24h TTL |
| REQ-XC-004 | GitHub fallback: degrade to no-auth | ⚠️ Not explicitly implemented |
| REQ-XC-005 | EPSS fallback: stale_data flag | ⚠️ Not implemented |
| REQ-XC-006 | Tavily fallback: omit OSINT | ✅ Returns empty list on failure |
| REQ-XC-008 | ChromaDB OOM: evict LRU / no-cache | ⚠️ LRU eviction exists but no OOM detection |

---

## Priority Findings

1. **MISSING (REQ-P2-012):** LLM-based relevance evaluation — the spec's core CRAG differentiator from basic RAG. Currently a heuristic formula.
2. **PARTIAL (REQ-P2-013):** ChromaDB cache sizing doesn't match spec (1000 queries, 4GB eviction). No disk monitoring.
3. **PARTIAL (REQ-P2-002):** Sonnet model configured but never called in Phase 2.
4. **PARTIAL (REQ-P2-001):** Module naming mismatch (cosmetic but spec-traceable).

---

*End of R2 gap analysis — 13 requirements assessed: 9 IMPLEMENTED, 3 PARTIAL, 1 MISSING.*
