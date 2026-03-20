"""Create a small Trivy report with ~25 CVEs for fast pipeline testing."""

from __future__ import annotations

import json
from pathlib import Path

MAX_VULNERABILITIES = 25

report = json.loads(Path("trivy-report.json").read_text())

# Take only the first result set, limit to MAX_VULNERABILITIES
small_results = []
total = 0
for result in report.get("Results", []):
    vulns = result.get("Vulnerabilities", [])
    if vulns and total < MAX_VULNERABILITIES:
        take = min(MAX_VULNERABILITIES - total, len(vulns))
        small_result = {**result, "Vulnerabilities": vulns[:take]}
        small_results.append(small_result)
        total += take

small_report = {**report, "Results": small_results}

Path("trivy-report-small.json").write_text(json.dumps(small_report, indent=2))
print(f"Created trivy-report-small.json with {total} vulnerabilities")
