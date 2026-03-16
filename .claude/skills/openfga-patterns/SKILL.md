---
name: openfga-patterns
description: "OpenFGA ReBAC authorization patterns: tuples, permission checks, decorators. USE WHEN code imports openfga_sdk or user asks about OpenFGA authorization."
user-invocable: false
---

# OpenFGA Patterns

OpenFGA relationship-based access control (ReBAC) patterns for SIOPV vulnerability authorization.
Covers authorization models, client setup, permission checks, relationship management, and testing.

## When to use

Apply these patterns when implementing or modifying OpenFGA authorization logic in the SIOPV pipeline
(Phase 5 — authorize node, DI wiring, integration tests).

## Quick checklist

1. Define authorization model in `model.fga` (schema 1.1)
2. Configure `OpenFgaClient` via DI — use `${OPENFGA_API_URL}` from settings, never hardcode
3. Write relationship tuples with `client.write(writes=[...])`
4. Check permissions with `client.check(ClientCheckRequest(...))`
5. Use `require_permission` decorator for endpoint-level authorization
6. Test with real OpenFGA server in integration tests (not mocks)
7. Docker Compose: use `${OPENFGA_DATASTORE_URI}` env var for DB connection

## Key patterns (quick reference)

- **Auth model**: `type user`, `type organization`, `type vulnerability` with relation hierarchy
- **Client setup**: `ClientConfiguration(api_url=..., store_id=...)`
- **Check**: `ClientCheckRequest(user=f"user:{id}", relation=..., object=f"{type}:{id}")`
- **Write tuple**: `client.write(writes=[ClientTuple(...)])`
- **Delete tuple**: `client.write(deletes=[ClientTuple(...)])`
- **List objects**: `client.list_objects(user=..., relation=..., type=...)`
- **Decorator**: `@require_permission("editor", "vulnerability")`

## Full reference

For complete code examples, Docker Compose config, and testing patterns, see:
@./openfga-patterns-reference.md
