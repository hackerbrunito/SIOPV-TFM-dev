#!/usr/bin/env bash
# Setup OpenFGA authorization tuples for SIOPV testing
# Usage: bash scripts/setup-openfga-tuples.sh

set -euo pipefail

STORE_ID="01KM4M2R5RGY1RGG45JTKK6DEM"
MODEL_ID="01KM4M2R6M1MWP4WDARTDAW7ZV"
API_URL="http://localhost:8080"
API_TOKEN="dev-key-siopv-local-1"

echo "Writing authorization tuples to OpenFGA..."

curl -s -X POST \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  "${API_URL}/stores/${STORE_ID}/write" \
  -d "{
    \"writes\": {
      \"tuple_keys\": [
        {\"user\": \"user:siopv-system\", \"relation\": \"owner\", \"object\": \"project:default\"},
        {\"user\": \"user:siopv-system\", \"relation\": \"analyst\", \"object\": \"project:default\"},
        {\"user\": \"user:bruno\", \"relation\": \"owner\", \"object\": \"project:default\"},
        {\"user\": \"user:bruno\", \"relation\": \"analyst\", \"object\": \"project:default\"}
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
echo "Done. 4 tuples should be listed above."
