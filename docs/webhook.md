# SIOPV Webhook Integration

The webhook adapter allows CI/CD pipelines to send Trivy vulnerability scan results directly to SIOPV for automated processing.

## How It Works

1. Your CI/CD pipeline runs `trivy image --format json` and sends the JSON output to SIOPV's webhook endpoint.
2. SIOPV verifies the HMAC-SHA256 signature, returns `202 Accepted`, and processes the report asynchronously.
3. The full pipeline runs in the background: ingest → DLP → enrich → classify → [escalate] → output.

## Configuration

Set these environment variables (all prefixed with `SIOPV_`):

| Variable | Default | Description |
|---|---|---|
| `SIOPV_WEBHOOK_ENABLED` | `false` | Enable the webhook server |
| `SIOPV_WEBHOOK_SECRET` | *(none)* | HMAC-SHA256 shared secret for signature verification |
| `SIOPV_WEBHOOK_HOST` | `0.0.0.0` | Host to bind the webhook server |
| `SIOPV_WEBHOOK_PORT` | `8080` | Port for the webhook server |

When `SIOPV_WEBHOOK_SECRET` is set, all requests must include a valid `X-Webhook-Signature-256` header. When unset, signature verification is skipped (not recommended for production).

## API Endpoint

```
POST /api/v1/webhook/trivy
```

**Headers:**
- `Content-Type: application/json`
- `X-Webhook-Signature-256: sha256=<hex-digest>` (required if secret is configured)

**Body:** Raw Trivy JSON report.

**Responses:**
- `202 Accepted` — Report received, pipeline processing enqueued
- `400 Bad Request` — Malformed JSON payload
- `401 Unauthorized` — Missing or invalid HMAC signature
- `503 Service Unavailable` — Webhook not configured

## CI/CD Usage (curl)

```bash
# Generate HMAC signature
PAYLOAD=$(cat trivy-report.json)
SIGNATURE=$(printf '%s' "$PAYLOAD" | openssl dgst -sha256 -hmac "$SIOPV_WEBHOOK_SECRET" | sed 's/^.* //')

# Send to SIOPV
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature-256: sha256=${SIGNATURE}" \
  -d "$PAYLOAD" \
  http://siopv-host:8080/api/v1/webhook/trivy
```

## Bridge Script

For convenience, use the provided bridge script:

```bash
# With secret from environment
export SIOPV_WEBHOOK_SECRET=your-shared-secret
./scripts/webhook-bridge.sh trivy-report.json

# With explicit URL and secret
./scripts/webhook-bridge.sh trivy-report.json http://localhost:8080/api/v1/webhook/trivy my-secret

# Without signature (development only)
./scripts/webhook-bridge.sh trivy-report.json http://localhost:8080/api/v1/webhook/trivy
```

## GitHub Actions Example

```yaml
- name: Run Trivy scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.IMAGE }}
    format: json
    output: trivy-report.json

- name: Send to SIOPV
  run: |
    PAYLOAD=$(cat trivy-report.json)
    SIGNATURE=$(printf '%s' "$PAYLOAD" | openssl dgst -sha256 -hmac "${{ secrets.SIOPV_WEBHOOK_SECRET }}" | sed 's/^.* //')
    curl -sf -X POST \
      -H "Content-Type: application/json" \
      -H "X-Webhook-Signature-256: sha256=${SIGNATURE}" \
      -d "$PAYLOAD" \
      "${{ vars.SIOPV_WEBHOOK_URL }}"
```
