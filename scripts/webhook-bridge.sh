#!/usr/bin/env bash
# webhook-bridge.sh — Send a Trivy JSON report to the SIOPV webhook endpoint.
#
# Usage:
#   ./scripts/webhook-bridge.sh <trivy-report.json> [webhook-url] [secret]
#
# Arguments:
#   trivy-report.json   Path to the Trivy JSON report file (required)
#   webhook-url         Webhook URL (default: http://localhost:8090/api/v1/webhook/trivy)
#   secret              HMAC-SHA256 shared secret (default: $SIOPV_WEBHOOK_SECRET env var)
#
# Environment variables:
#   SIOPV_WEBHOOK_SECRET  Shared secret for HMAC signature (if not passed as arg)
#
# Exit codes:
#   0  Success (HTTP 202)
#   1  Usage error or missing file
#   2  curl failed or non-202 response

set -euo pipefail

REPORT_FILE="${1:-}"
WEBHOOK_URL="${2:-http://localhost:8090/api/v1/webhook/trivy}"
SECRET="${3:-${SIOPV_WEBHOOK_SECRET:-}}"

if [[ -z "$REPORT_FILE" ]]; then
    echo "Usage: $0 <trivy-report.json> [webhook-url] [secret]" >&2
    exit 1
fi

if [[ ! -f "$REPORT_FILE" ]]; then
    echo "Error: File not found: $REPORT_FILE" >&2
    exit 1
fi

# Build signature header if secret is provided
HEADERS=(-H "Content-Type: application/json")
if [[ -n "$SECRET" ]]; then
    SIGNATURE=$(openssl dgst -sha256 -hmac "$SECRET" < "$REPORT_FILE" | sed 's/^.* //')
    HEADERS+=(-H "X-Webhook-Signature-256: sha256=${SIGNATURE}")
    echo "Sending with HMAC-SHA256 signature..."
else
    echo "Warning: No secret provided — sending without signature" >&2
fi

echo "Sending ${REPORT_FILE} to ${WEBHOOK_URL}..."

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    "${HEADERS[@]}" \
    --data-binary "@${REPORT_FILE}" \
    "$WEBHOOK_URL")

echo "Response: HTTP ${HTTP_CODE}"

if [[ "$HTTP_CODE" == "202" ]]; then
    echo "Success: Pipeline processing enqueued"
    exit 0
else
    echo "Error: Expected 202, got ${HTTP_CODE}" >&2
    exit 2
fi
