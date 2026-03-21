#!/usr/bin/env bash
# Setup OpenFGA authorization tuples for SIOPV
#
# Usage:
#   bash scripts/setup-openfga-tuples.sh [username] [project]
#
# Arguments:
#   username    SIOPV user identity (default: $USER)
#   project     Project name (default: "default")
#
# Environment variables (override defaults):
#   SIOPV_OPENFGA_STORE_ID    OpenFGA store ID
#   SIOPV_OPENFGA_MODEL_ID    OpenFGA authorization model ID
#   SIOPV_OPENFGA_API_URL     OpenFGA API URL
#   SIOPV_OPENFGA_API_TOKEN   OpenFGA API token

set -euo pipefail

USERNAME="${1:-${USER:-siopv-user}}"
PROJECT="${2:-default}"

STORE_ID="${SIOPV_OPENFGA_STORE_ID:-01KM4M2R5RGY1RGG45JTKK6DEM}"
MODEL_ID="${SIOPV_OPENFGA_MODEL_ID:-01KM4M2R6M1MWP4WDARTDAW7ZV}"
API_URL="${SIOPV_OPENFGA_API_URL:-http://localhost:8080}"
API_TOKEN="${SIOPV_OPENFGA_API_TOKEN:-dev-key-siopv-local-1}"

echo "Writing authorization tuples to OpenFGA..."
echo "  User:    ${USERNAME}"
echo "  Project: ${PROJECT}"
echo ""

curl -s -X POST \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  "${API_URL}/stores/${STORE_ID}/write" \
  -d "{
    \"writes\": {
      \"tuple_keys\": [
        {\"user\": \"user:siopv-system\", \"relation\": \"owner\", \"object\": \"project:${PROJECT}\"},
        {\"user\": \"user:siopv-system\", \"relation\": \"analyst\", \"object\": \"project:${PROJECT}\"},
        {\"user\": \"user:${USERNAME}\", \"relation\": \"owner\", \"object\": \"project:${PROJECT}\"},
        {\"user\": \"user:${USERNAME}\", \"relation\": \"analyst\", \"object\": \"project:${PROJECT}\"}
      ]
    },
    \"authorization_model_id\": \"${MODEL_ID}\"
  }" | python3 -m json.tool

echo ""
echo "Verifying tuples..."

curl -s \
  -H "Authorization: Bearer ${API_TOKEN}" \
  "${API_URL}/stores/${STORE_ID}/read" \
  -d '{}' | python3 -m json.tool

echo ""
echo "Done. Tuples created for user:${USERNAME} on project:${PROJECT}."
