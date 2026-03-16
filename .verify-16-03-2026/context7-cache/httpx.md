# httpx — Context7 Cache

## Current Version: httpx 0.27+

## Key API Patterns

### Async Client (preferred)
- `import httpx`
- `async with httpx.AsyncClient(base_url="...", timeout=30.0) as client:`
- `response = await client.get("/path", params={...})`
- `response = await client.post("/path", json={...})`
- `response.raise_for_status()` — raise on 4xx/5xx
- `response.json()` — parse JSON response

### Sync Client
- `with httpx.Client(base_url="...") as client:` — for sync contexts only

### Configuration
- `httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=10.0)` — granular timeouts
- `httpx.Limits(max_connections=100, max_keepalive_connections=20)` — connection pool
- `headers={"Authorization": f"Bearer {token}"}` — default headers

### Retry Pattern (with tenacity)
- httpx does NOT have built-in retry — use tenacity for retries
- Retry on `httpx.HTTPStatusError`, `httpx.ConnectError`, `httpx.TimeoutException`

### Best Practices
- Always use context manager (ensures connection cleanup)
- Use `AsyncClient` for async code, never `requests` library
- Set explicit timeouts (no implicit infinite waits)
- Use `base_url` to avoid URL duplication

### Deprecated / Avoid
- `requests` library → use `httpx` (async-native, HTTP/2 support)
- Global `httpx.get()` / `httpx.post()` → use client instance (connection reuse)
