#!/usr/bin/env bash
# Step 4e: Baseline Runtime Test
# Scans a vulnerable Docker image with Trivy, then runs SIOPV pipeline
# Usage: bash scripts/step4e-baseline-test.sh

set -euo pipefail

echo "=== Step 4e: Baseline Runtime Test ==="
echo ""

# Step 1: Pull vulnerable image
echo "[1/4] Pulling vulnerable Docker image (DVWA)..."
docker pull vulnerables/web-dvwa:latest

# Step 2: Scan with Trivy
echo ""
echo "[2/4] Scanning with Trivy (JSON output)..."
trivy image vulnerables/web-dvwa:latest --format json -o trivy-report.json 2>&1 | tail -5

# Step 3: Verify Trivy output
echo ""
echo "[3/4] Verifying Trivy report..."
VULN_COUNT=$(python3 -c "
import json
with open('trivy-report.json') as f:
    data = json.load(f)
total = 0
for result in data.get('Results', []):
    total += len(result.get('Vulnerabilities', []))
print(total)
")
echo "Found ${VULN_COUNT} vulnerabilities in Trivy report"

if [ "$VULN_COUNT" -eq 0 ]; then
    echo "WARNING: No vulnerabilities found. Try a different image."
    exit 1
fi

echo ""
echo "[4/4] Ready to run SIOPV pipeline."
echo ""
echo "Run this command next:"
echo "  uv run siopv process-report trivy-report.json"
echo ""
echo "This will process ${VULN_COUNT} vulnerabilities through:"
echo "  authorize → ingest → dlp → enrich → classify → escalate → output"
