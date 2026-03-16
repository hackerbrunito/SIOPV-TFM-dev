# Context7 MCP: Agent Integration Research Report

**Date:** 2026-03-16
**Topic:** Using Context7 MCP in agent teams for code verification
**Researcher:** Claude Sonnet 4.6 (deep web research, 15+ sources)

---

## 1. What is Context7 MCP?

Context7 is an MCP (Model Context Protocol) server developed by Upstash that solves LLM knowledge cutoff problems. It fetches **up-to-date, version-specific documentation and code examples** from official sources and injects them directly into the LLM's context window at query time.

### Core Architecture

```
LLM Client → Context7 MCP Server → API Backend → Indexed Documentation DB
              (protocol adapter)    (service layer)  (GitHub + official docs)
```

Key design properties:
- **Stateless backend**: Enables concurrent requests and parallel agent use
- **Serverless infrastructure**: Each component scales independently
- **Privacy-first**: Query-only, no user data stored
- **Real-time fetching**: No stale training data; docs fetched on demand

### Why it matters for code verification agents

Without Context7, agents use training data (cutoff mid-2025) to verify library usage. With Context7, agents verify against current official documentation — catching deprecated APIs, changed signatures, and new version-specific patterns that training data cannot know about.

---

## 2. MCP Tools Exposed

Context7 exposes exactly **two tools** via the MCP protocol:

### Tool 1: `resolve-library-id`

**Purpose:** Converts a human-readable library name into a Context7-compatible library ID.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `libraryName` | string | yes | Library name (e.g., "pydantic", "httpx") |
| `query` | string | yes | User's question/task — used to rank results by relevance |

**Response format:** Structured metadata per matched library:
- Library ID (format: `/org/project` or `/org/project/vX.Y.Z`)
- Name, description
- Code snippet count
- Source reputation (High/Medium/Low/Unknown)
- Benchmark score (0–100)
- Available versions list

**Built-in constraint documented in source:** "Do not call this tool more than 3 times per question." This prevents infinite resolution loops.

**API call:** `GET https://context7.com/api/v2/libs/search?query={query}&libraryName={libraryName}`

---

### Tool 2: `get-library-docs` (also called `query-docs`)

**Purpose:** Retrieves documentation snippets for a resolved library ID.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `libraryId` | string | yes | — | Context7 ID from `resolve-library-id` (e.g., `/pydantic/pydantic`) |
| `query` | string | yes | — | Topic/question to focus the documentation |
| `tokens` | integer | no | 10,000 | Maximum tokens to return |

**API call:** `GET https://context7.com/api/v2/context?libraryId={id}&query={query}`

---

## 3. Response Sizes and Token Costs

### Default token limit

The `DEFAULT_MINIMUM_TOKENS` environment variable controls the floor:

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"],
      "env": {
        "DEFAULT_MINIMUM_TOKENS": "10000"
      }
    }
  }
}
```

- **Default minimum:** 10,000 tokens (as of npm package `@upstash/context7-mcp`)
- **Important:** Any `tokens` value passed below the configured minimum is **automatically raised** to the minimum — you cannot request fewer tokens than the floor.
- **Maximum reported:** 100,000 tokens (via GitHub issue #480 — Upstash imposed this cap for cost control; higher limits planned for paid API)

### Practical token estimates for SIOPV-relevant libraries

| Library | Recommended query | Estimated tokens |
|---------|-------------------|-----------------|
| pydantic | "model validators field_validator" | 10,000–15,000 |
| httpx | "async client timeout retry" | 8,000–12,000 |
| structlog | "configure processors contextvars" | 5,000–10,000 |
| langchain / langgraph | "interrupt checkpoint state" | 10,000–20,000 |
| presidio | "analyzer engine recognizer" | 8,000–15,000 |
| openfga | "check tuple write" | 8,000–12,000 |

**Context window cost per agent call:** ~10,000–20,000 tokens per `get-library-docs` call. For a verification team of 5 agents each querying 3 libraries: **150,000–300,000 tokens of documentation overhead** if each agent queries independently. This is the primary argument for a centralized researcher agent.

### Context7 ranking logic

Context7's backend applies proprietary relevance ranking within the token budget:
- Code examples rank higher than prose
- API signatures rank higher than descriptions
- This means you get maximum signal per token when queries are specific

---

## 4. Rate Limits (Critical for Agent Teams)

**Current Free Plan (as of January 2026):**

| Plan | Limit | Notes |
|------|-------|-------|
| Free (no API key) | 60 requests/hour | No auth required |
| Free (with API key) | 60 requests/hour | Same limit, adds private repo access |
| Pro | Higher (undisclosed) | Scales with team size |
| Enterprise | Custom | Negotiated |

**Critical change:** In January 2026, Context7 cut the free tier from ~6,000 to **1,000 requests/month** while adding a 60 req/hour cap. For a 5-agent verification team running 3 queries each per session, that's 15 requests per invocation — easily hitting the hourly cap during parallel execution.

**Rate limit behavior:**
- Returns HTTP 429 with `Retry-After` header when exceeded
- MCP server propagates these errors to the calling agent
- Exponential backoff is the recommended handling pattern

**Implication for multi-agent teams:** With 60 requests/hour shared across all agents using the same API key, a team of 5 agents querying 4 libraries each would consume 40 of 60 available requests per hour in a single verification run. **A centralized researcher agent is not just a convenience — it is a rate-limit necessity.**

---

## 5. Caching — What Exists and What Doesn't

### Official guidance

From Context7's API guide:
> "Store documentation locally to reduce API calls and improve performance. Documentation updates are infrequent, making caching appropriate for hours or days."

Context7 itself does **not** provide a built-in cross-agent caching layer. The MCP server is stateless — each `get-library-docs` call hits the API backend.

### What the MCP server provides

- **15-minute in-process cache** on the WebFetch side (for the MCP server process itself)
- **HTTP transport with AsyncLocalStorage** for request isolation in concurrent HTTP mode
- No persistent cache, no cross-process cache, no cross-agent shared memory

### What must be implemented externally

There is no native mechanism for Agent A's Context7 result to be reused by Agent B without explicit sharing. The patterns for cross-agent sharing:

1. **File-based cache:** Researcher agent writes docs to `.ignorar/context7-cache/{library}-{version}.md`; downstream agents read from file instead of calling Context7
2. **Message-passing:** Orchestrator passes documentation text directly in agent spawn prompts
3. **Shared briefing document:** Researcher populates a briefing file that all subsequent agents receive

---

## 6. Recommended Agent Architecture for Multi-Agent Context7 Integration

### Option A: Each agent queries independently (anti-pattern)

```
orchestrator
├── scanner-agent → calls resolve-library-id + get-library-docs (pydantic, httpx)
├── fixer-agent   → calls resolve-library-id + get-library-docs (pydantic, httpx)
└── reviewer-agent → calls resolve-library-id + get-library-docs (pydantic, httpx)
```

**Problems:**
- 3× rate limit consumption (same libraries queried 3 times)
- 3× token overhead in each agent's context window
- Risk of inconsistent documentation versions across agents
- At 60 req/hour free limit, this pattern exhausts quota fast

### Option B: Centralized Library Researcher Agent (recommended)

```
orchestrator
└── researcher-agent (runs first, sequentially)
    ├── Queries Context7 for all required libraries
    ├── Writes results to: .ignorar/context7-cache/{YYYY-MM-DD}/{library}.md
    └── Produces briefing.md with doc summaries
        └── (then in parallel)
            ├── scanner-agent   ← reads briefing.md, does NOT call Context7
            ├── fixer-agent     ← reads briefing.md, does NOT call Context7
            └── reviewer-agent  ← reads briefing.md, does NOT call Context7
```

**Benefits:**
- Single rate-limit consumption per library per session
- Consistent docs across all agents (same fetched snapshot)
- Docs cached to disk for same-day re-runs
- Downstream agents receive targeted excerpts, not raw 10k-token dumps

### Option C: MCP Passthrough (advanced, for HTTP transport)

Run Context7 MCP server in HTTP mode and have agents share a single MCP server instance. This allows the server-side 15-minute process cache to be shared. Requires:
- Context7 configured with `--http` transport
- All agents connected to same server endpoint
- More complex setup; not natively supported in Claude Code's stdio MCP mode

**Verdict for SIOPV:** Use Option B (centralized researcher). It is the only pattern compatible with Claude Code's stdio MCP transport, the 60 req/hour free plan, and the requirement for reproducible verification runs.

---

## 7. Concrete Researcher Agent Prompt Template

The following is a ready-to-use researcher agent prompt for SIOPV's verification pipeline:

```markdown
# Library Researcher Agent

You are the Library Researcher Agent for the SIOPV verification pipeline.
Your sole responsibility: fetch current official documentation for all libraries
used in this project and persist it to disk for downstream agents to consume.

## Instructions

### Step 1 — Determine libraries to research
Read the following files to identify all external libraries in use:
- /Users/bruno/siopv/pyproject.toml (dependencies section)
- /Users/bruno/siopv/src/siopv/infrastructure/config/settings.py

For this session, research the following libraries (adjust as needed):
- pydantic (v2) — focus: model validators, field_validator, model_config
- httpx — focus: async client, timeout, retry, connection pooling
- structlog — focus: configure, get_logger, processors, contextvars
- langchain-core / langgraph — focus: interrupt, checkpoint, CompiledGraph
- presidio-analyzer — focus: AnalyzerEngine, RecognizerRegistry, EntityRecognizer
- openfga-sdk — focus: ClientConfiguration, check, write_tuples

### Step 2 — Fetch documentation via Context7 MCP

For each library:
1. Call `resolve-library-id` with the library name and a relevant query
2. Pick the result with the highest benchmark score and matching version
3. Call `get-library-docs` with:
   - The resolved library ID
   - A focused query (e.g., "validators field types model_config")
   - tokens: 10000 (default minimum)
4. Save the raw result to:
   `/Users/bruno/siopv/.ignorar/context7-cache/2026-03-16/{library-slug}.md`

### Step 3 — Produce consolidated briefing

Write a consolidated briefing to:
`/Users/bruno/siopv/.ignorar/context7-cache/2026-03-16/BRIEFING.md`

The briefing must contain:
- For each library: library ID used, version, key API patterns found, critical gotchas
- Token count fetched per library
- Any libraries that failed to resolve (with fallback recommendation)

### Step 4 — Report to orchestrator

Send a message to the orchestrator confirming:
- Libraries successfully documented
- Path to BRIEFING.md
- Any libraries that could not be resolved (so orchestrator can use WebSearch instead)

## Constraints

- Do NOT call `resolve-library-id` more than 3 times for any single library
- Do NOT call `get-library-docs` without first successfully resolving the library ID
- If Context7 returns 429 (rate limit), wait 60 seconds and retry once
- If retry also fails, note the failure in the briefing and continue with remaining libraries
- Do NOT attempt to fix code or audit anything — documentation research only

## Output files

All output goes to: `/Users/bruno/siopv/.ignorar/context7-cache/2026-03-16/`
- `{library-slug}.md` — raw Context7 response per library
- `BRIEFING.md` — consolidated summary for downstream agents
```

---

## 8. How Downstream Agents Use the Cache

Scanner, fixer, and reviewer agents should receive this instruction in their spawn prompts:

```markdown
## Library Documentation (do NOT call Context7 yourself)

The Library Researcher Agent has pre-fetched current official documentation for all
relevant libraries. Read the briefing at:
  /Users/bruno/siopv/.ignorar/context7-cache/2026-03-16/BRIEFING.md

For detailed docs on a specific library, read:
  /Users/bruno/siopv/.ignorar/context7-cache/2026-03-16/{library-slug}.md

Use this documentation to verify API usage. Do NOT call Context7 MCP tools
directly — the rate limit is shared across all agents and must be preserved.
```

---

## 9. Cache Invalidation Strategy

| Trigger | Action |
|---------|--------|
| Same day, same library | Read from `.ignorar/context7-cache/YYYY-MM-DD/{lib}.md` (skip API call) |
| New day | Delete previous day's cache dir; researcher agent fetches fresh |
| Library version change in pyproject.toml | Delete that library's cache file only; researcher re-fetches |
| Context7 returns 429 and retry fails | Keep existing cache file if it exists; log warning in briefing |
| Cache file > 7 days old | Force re-fetch regardless of date |

Implement as a simple shell check in the researcher agent:
```bash
CACHE_FILE="/Users/bruno/siopv/.ignorar/context7-cache/$(date +%Y-%m-%d)/${LIBRARY}.md"
if [ -f "$CACHE_FILE" ]; then
  echo "Cache hit: $CACHE_FILE"
  # Read from file, skip Context7 call
else
  echo "Cache miss: fetching from Context7"
  # Call resolve-library-id + get-library-docs
fi
```

---

## 10. Published Examples and References

### n8n + Context7 workflow
An n8n workflow template ("Documentation Lookup AI Agent using Context7 and Gemini") demonstrates wrapping Context7 into a callable multi-agent tool. The Context7 agent node runs in isolation, preventing context window growth in the main agent, and returns only the relevant documentation excerpt. Source: https://n8n.io/workflows/4547-documentation-lookup-ai-agent-using-context7-and-gemini/

### GitHub Copilot agent-skills integration
Microsoft's `awesome-copilot` repository includes a `context7.agent.md` defining an agent role with these principles:
- "ALWAYS use Context7 tools for all library and framework questions"
- "NEVER guess — ALWAYS verify with Context7 before responding"
- Uses a three-tier loading strategy: metadata at startup (50–100 tokens), full bodies on activation (500–2,000 tokens), references on-demand

### Claude Code CLAUDE.md pattern
Published Claude Code integrations use CLAUDE.md to force Context7 invocation:
```markdown
Always use context7 when I need code generation, setup or configuration steps,
or library/API documentation without me having to explicitly ask.
Always prioritize Context7 over training data if there is a conflict.
```

### Local-first alternative (for rate-limit-constrained teams)
A local alternative called **Context** (`@neuledge/context` on npm) was published in early 2026 specifically because of Context7's free tier cuts. It uses SQLite + FTS5 + BM25 for offline documentation search. This is relevant when running many verification cycles per day against the same libraries (100+ requests). Source: https://github.com/neuledge/context

---

## 11. Summary: Key Decisions for SIOPV

| Question | Answer |
|----------|--------|
| One researcher or each agent queries? | **One dedicated researcher agent** — mandatory for rate limit compliance |
| Default tokens per `get-library-docs` call? | **10,000 tokens** (minimum floor; cannot go lower) |
| Does Context7 provide a caching layer? | **No** — implement file-based cache under `.ignorar/context7-cache/` |
| Free plan sufficient for verification team? | **Marginal** — 60 req/hour with 6 libraries = 12 requests; leaves 48 for retries. Centralized researcher keeps this safe |
| Token overhead if 5 agents query independently? | **~300,000 tokens of docs** (vs. 60,000 with centralized researcher) |
| Rate limit if 5 agents query independently? | **30 requests** per run — half the hourly free quota in one shot |
| When to call `resolve-library-id`? | Once per library per session; re-use the ID for all subsequent `get-library-docs` calls |
| Version pinning? | Prefer explicit version IDs (`/pydantic/pydantic/v2.10.0`) over generic IDs for deployment consistency |
| Fallback if Context7 is unavailable? | Use `WebSearch` for current docs; log the fallback in briefing.md |

---

## Sources

- [Context7 GitHub (upstash/context7)](https://github.com/upstash/context7)
- [Context7 API Guide](https://context7.com/api-guide)
- [DeepWiki: resolve-library-id](https://deepwiki.com/upstash/context7/4.1-resolve-library-id)
- [DeepWiki: Rate Limits and Quotas](https://deepwiki.com/upstash/context7/10.4-rate-limits-and-quotas)
- [DeepWiki: Plans and Pricing](https://deepwiki.com/upstash/context7/10-plans-and-pricing)
- [DeepWiki: Usage Guide](https://deepwiki.com/upstash/context7/10-usage-guide)
- [GitHub Issue #480: Token limit](https://github.com/upstash/context7/issues/480)
- [GitHub Issue #808: Rate limiting bug](https://github.com/upstash/context7/issues/808)
- [Context7 MCP: Stop LLM Hallucinations (Trevor Lasn)](https://www.trevorlasn.com/blog/context7-mcp)
- [Context7 MCP Documentation Automation 20x (EF-Map)](https://ef-map.com/blog/context7-mcp-documentation-automation)
- [Context7 Quietly Slashed Free Tier by 92% (DevGenius)](https://blog.devgenius.io/context7-quietly-slashed-its-free-tier-by-92-16fa05ddce03)
- [n8n: Documentation Lookup AI Agent with Context7 and Gemini](https://n8n.io/workflows/4547-documentation-lookup-ai-agent-using-context7-and-gemini/)
- [Microsoft agent-skills: Context7 integration (DeepWiki)](https://deepwiki.com/microsoft/agent-skills/6.3-context7-integration)
- [Local-first Context7 alternative (@neuledge/context)](https://github.com/neuledge/context)
- [Context7 MCP: ClaudeFast](https://claudefa.st/blog/tools/mcp-extensions/context7-mcp)
- [Context7 Free Tier alternatives (Neuledge)](https://neuledge.com/blog/2026-02-06/top-7-mcp-alternatives-for-context7-in-2026)
- [Upstash Blog: Introducing Context7](https://upstash.com/blog/context7-llmtxt-cursor)
- [MCP 2026 Roadmap](http://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/)
- [Claude Code Context Engineering (HuggingFace)](https://huggingface.co/blog/kobe0938/context-engineering-reuse-pattern-claude-code)
