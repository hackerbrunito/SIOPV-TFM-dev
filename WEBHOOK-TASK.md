# Webhook Implementation Task — A1 to A7

## SCOPE RULES (READ FIRST)

- You MUST only create or modify files directly related to the webhook feature.
- Do NOT refactor, rename, or "improve" existing code that already works.
- Do NOT add comments, docstrings, or type annotations to files you didn't create.
- Do NOT modify any pipeline node, use case, or adapter that is not part of this task.
- Do NOT change settings.py fields that already exist — only ADD new webhook-related fields.
- Do NOT touch tests for existing features — only write NEW tests for webhook code.
- If something is not listed below, do NOT do it.

## CONTEXT

Read these files BEFORE starting:
1. `.claude/workflow/briefing.md` — project architecture, hex layers, graph flow
2. `.ignorar/research-webhook-patterns.md` — webhook design research
3. `.ignorar/research-cicd-webhook-integration.md` — CI/CD integration patterns
4. `.ignorar/research-async-job-processing.md` — async processing patterns
5. `src/siopv/infrastructure/config/settings.py` — existing settings pattern
6. `src/siopv/infrastructure/di/__init__.py` — existing DI pattern
7. `src/siopv/application/ports/` — existing port interface pattern (pick any file)
8. `src/siopv/adapters/` — existing adapter pattern (pick any file)

## ARCHITECTURE RULES

- Hexagonal architecture: domain → ports → adapters → infrastructure → interfaces
- NO cross-layer imports (e.g., adapter must not import another adapter)
- Ports are abstract classes in `src/siopv/application/ports/`
- Adapters implement ports in `src/siopv/adapters/`
- DI wiring in `src/siopv/infrastructure/di/`
- Settings via Pydantic BaseSettings in `src/siopv/infrastructure/config/settings.py`
- All configurable values in settings.py, read from env vars with `SIOPV_` prefix

## TASKS (A1 through A7)

### A1: Webhook Port (interface)
- Create `src/siopv/application/ports/webhook_receiver.py`
- Define `WebhookReceiverPort` abstract class with method to receive and validate webhook payload
- Export in `src/siopv/application/ports/__init__.py`

### A2: FastAPI Webhook Adapter
- Create `src/siopv/adapters/inbound/webhook_adapter.py`
- FastAPI router with POST endpoint `/api/v1/webhook/trivy`
- HMAC-SHA256 signature verification (header: `X-Webhook-Signature-256`)
- Accept Trivy JSON payload
- Return 202 Accepted immediately (async processing)
- Trigger pipeline run in background task
- Implement `WebhookReceiverPort`

### A3: DI Wiring + Settings
- Add to `src/siopv/infrastructure/config/settings.py`:
  - `webhook_enabled: bool = False`
  - `webhook_secret: SecretStr | None = None` (HMAC shared secret)
  - `webhook_host: str = "0.0.0.0"`
  - `webhook_port: int = 8080`
- Add DI factory function in `src/siopv/infrastructure/di/webhook.py`
- Wire in `src/siopv/infrastructure/di/__init__.py`
- Add new env vars to `.env.example`

### A4: Tests
- Create `tests/unit/adapters/inbound/test_webhook_adapter.py`
  - Test valid HMAC signature → 202
  - Test invalid HMAC signature → 401
  - Test missing signature header → 401
  - Test malformed JSON → 400
  - Test valid Trivy payload triggers pipeline
- Create `tests/unit/application/ports/test_webhook_port.py` if needed
- All tests must pass with `uv run python -m pytest tests/ -x`

### A5: Bridge Script
- Create `scripts/webhook-bridge.sh`
- Shell script that reads a Trivy JSON file and sends it to the webhook endpoint via curl
- Include HMAC-SHA256 signature generation
- Usage: `./scripts/webhook-bridge.sh <trivy-report.json> [webhook-url]`

### A6: Documentation
- Add webhook env vars to `.env.example` (ONLY add new lines, do NOT modify existing lines)
- Create `docs/webhook.md` with:
  - What the webhook does
  - How to configure (env vars)
  - How to use from CI/CD (curl example)
  - How to use the bridge script

### A7: Smoke Test
- Add a webhook smoke test to `scripts/smoke-tests.py` (add a new test function, do NOT modify existing tests)
- OR create `scripts/webhook-smoke-test.py` as a separate script
- Test: start webhook server, send signed payload, verify 202 response

## VALIDATION (run all before reporting)

```bash
uv run ruff check src/ tests/ scripts/
uv run ruff format --check src/ tests/ scripts/
uv run mypy src/
uv run python -m pytest tests/ -x -q
```

All must pass with zero errors.

## COMPLETION

When done, save a report to `.ignorar/production-reports/webhook-implementation.md` with:
- Files created (with paths)
- Files modified (with what was changed)
- Test results (copy paste output)
- Any decisions you made and why

Then STOP and wait for human review.
