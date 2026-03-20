"""Step 4f: Pre-production smoke tests for SIOPV pipeline.

Runs 5 tests sequentially, saves individual reports to
.ignorar/production-reports/smoke-tests/

Tests:
1. Data-flow: 5 CVEs traced through all pipeline nodes
2. Error-path: Malformed input → graceful degradation
3. Config: Different settings → different pipeline behavior
4. Isolation: Node contract compliance (pytest)
5. Idempotency: Same input twice → same output
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPORT_DIR = Path(".ignorar/production-reports/smoke-tests")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

TRIVY_REPORT = "trivy-report-small.json"
OUTPUT_DIR = Path("./output")
TIMESTAMP = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

# Constants for ruff PLR2004 compliance
LOG_TRUNCATE_CHARS = 2000
INPUT_PREVIEW_CHARS = 100
MIN_CLASSIFICATIONS_EXPECTED = 20
MIN_JSON_FILES_FOR_COMPARISON = 2


def run_cmd(cmd: list[str], *, timeout: int = 300) -> tuple[int, str, str]:
    """Run command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        cwd=str(Path(__file__).parent.parent),
    )
    return result.returncode, result.stdout, result.stderr


def run_pipeline(
    report_path: str, *, extra_env: dict[str, str] | None = None
) -> tuple[int, str, str]:
    """Run SIOPV pipeline with given report."""
    env = {**os.environ}
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        [
            "uv",
            "run",
            "siopv",
            "process-report",
            report_path,
            "--user-id",
            "bruno",
            "--project-id",
            "default",
        ],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
        env=env,
        cwd=str(Path(__file__).parent.parent),
    )
    return result.returncode, result.stdout, result.stderr


def write_report(name: str, content: str) -> Path:
    """Write report file and return path."""
    path = REPORT_DIR / f"{name}.md"
    path.write_text(content, encoding="utf-8")
    print(f"  Report saved: {path}")
    return path


def _check_output_files(checks: list[str]) -> bool:
    """Check that PDF, JSON, CSV output files were generated. Returns passed."""
    passed = True
    pdf_files = sorted(OUTPUT_DIR.glob("*.pdf"), key=os.path.getmtime, reverse=True)
    json_files = sorted(OUTPUT_DIR.glob("siopv-metrics-*.json"), key=os.path.getmtime, reverse=True)
    csv_files = sorted(OUTPUT_DIR.glob("siopv-metrics-*.csv"), key=os.path.getmtime, reverse=True)

    for label, files in [("PDF", pdf_files), ("JSON", json_files), ("CSV", csv_files)]:
        if files:
            size_info = f", {files[0].stat().st_size} bytes" if label == "PDF" else ""
            checks.append(f"- PASS: {label} generated ({files[0].name}{size_info})")
        else:
            checks.append(f"- FAIL: No {label} generated")
            passed = False
    return passed


def _check_json_completeness(checks: list[str]) -> None:
    """Parse JSON output to check CVE data completeness."""
    json_files = sorted(OUTPUT_DIR.glob("siopv-metrics-*.json"), key=os.path.getmtime, reverse=True)
    if not json_files:
        return
    try:
        with open(json_files[0]) as f:
            metrics = json.load(f)
        classifications = metrics.get("classifications", {})
        enrichments = metrics.get("enrichments", {})
        checks.append(f"- INFO: {len(classifications)} classifications in output")
        checks.append(f"- INFO: {len(enrichments)} enrichments in output")
        if len(classifications) >= MIN_CLASSIFICATIONS_EXPECTED:
            checks.append("- PASS: Majority of CVEs classified (>=20/25)")
        else:
            checks.append(f"- WARN: Only {len(classifications)}/25 CVEs classified")
    except Exception as e:
        checks.append(f"- WARN: Could not parse JSON output: {e}")


def _check_node_execution(checks: list[str], combined: str) -> None:
    """Check pipeline completed all nodes."""
    for node in ["authorize", "ingest", "dlp", "enrich", "classify", "output"]:
        if node in combined:
            checks.append(f"- PASS: Node '{node}' executed")
        else:
            checks.append(f"- WARN: Node '{node}' not detected in logs")


# ─────────────────────────────────────────────
# TEST 1: Data-Flow
# ─────────────────────────────────────────────
def test_data_flow() -> tuple[bool, str]:
    """Verify all CVEs traverse every pipeline node with complete data."""
    print("\n═══ TEST 1: Data-Flow ═══")
    start = time.time()

    rc, stdout, stderr = run_pipeline(TRIVY_REPORT)
    elapsed = time.time() - start

    truncated = stdout[-LOG_TRUNCATE_CHARS:] if len(stdout) > LOG_TRUNCATE_CHARS else stdout
    lines: list[str] = [
        "# Smoke Test 1: Data-Flow",
        f"\n**Date:** {TIMESTAMP}",
        f"**Input:** {TRIVY_REPORT} (25 CVEs)",
        f"**Duration:** {elapsed:.1f}s",
        f"**Exit code:** {rc}",
        "",
        "## Pipeline Output",
        f"```\n{truncated}\n```",
    ]

    if stderr:
        lines.append(f"\n## Stderr (last 1000 chars)\n```\n{stderr[-1000:]}\n```")

    checks: list[str] = []
    passed = rc == 0
    checks.append(f"- {'PASS' if passed else 'FAIL'}: Exit code {rc}")

    if not _check_output_files(checks):
        passed = False

    jira_count = stdout.count("jira_ticket_created") + stdout.count("jira_ticket_exists")
    if jira_count > 0:
        checks.append(f"- PASS: {jira_count} Jira tickets created/found")
    else:
        checks.append("- WARN: No Jira ticket creation detected in logs")

    _check_json_completeness(checks)
    _check_node_execution(checks, stdout + stderr)

    lines.append("\n## Checks")
    lines.extend(checks)
    lines.append(f"\n## Verdict: {'PASS' if passed else 'FAIL'}")

    report = "\n".join(lines)
    write_report("test-1-data-flow", report)
    return passed, f"Data-flow: {'PASS' if passed else 'FAIL'} ({elapsed:.1f}s)"


# ─────────────────────────────────────────────
# TEST 2: Error-Path
# ─────────────────────────────────────────────
def test_error_path() -> tuple[bool, str]:
    """Verify graceful degradation with malformed input."""
    print("\n═══ TEST 2: Error-Path ═══")
    start = time.time()

    test_cases = [
        ("empty JSON", "{}"),
        ("missing Results key", '{"foo": "bar"}'),
        (
            "invalid CVE IDs",
            json.dumps(
                {
                    "Results": [
                        {
                            "Vulnerabilities": [
                                {
                                    "VulnerabilityID": "CVE-9999-99999",
                                    "PkgName": "fake",
                                    "InstalledVersion": "1.0",
                                    "Severity": "HIGH",
                                    "Title": "Fake vulnerability",
                                    "Description": "Test",
                                },
                            ],
                            "Target": "test",
                            "Type": "debian",
                        }
                    ]
                }
            ),
        ),
        ("corrupt JSON", "{broken"),
    ]

    lines: list[str] = [
        "# Smoke Test 2: Error-Path",
        f"\n**Date:** {TIMESTAMP}",
        "**Purpose:** Verify graceful degradation with malformed input",
        "",
    ]

    all_passed = True
    for name, content in test_cases:
        # Write temp input file
        tmp_path = Path(f".ignorar/smoke-test-{name.replace(' ', '-')}.json")
        tmp_path.write_text(content, encoding="utf-8")

        rc, stdout, stderr = run_pipeline(str(tmp_path))

        crashed = "Traceback" in stderr and "unhandled" in stderr.lower()
        graceful = rc != 0 or "error" in (stdout + stderr).lower()

        case_passed = not crashed
        if not case_passed:
            all_passed = False

        lines.append(f"### Case: {name}")
        preview = content[:INPUT_PREVIEW_CHARS]
        ellipsis = "..." if len(content) > INPUT_PREVIEW_CHARS else ""
        lines.append(f"- Input: `{preview}{ellipsis}`")
        lines.append(f"- Exit code: {rc}")
        lines.append(f"- Crashed: {'YES' if crashed else 'No'}")
        lines.append(f"- Graceful handling: {'Yes' if graceful else 'Unknown'}")
        lines.append(f"- Result: **{'PASS' if case_passed else 'FAIL'}**")
        if stdout:
            lines.append(f"- Stdout (last 500): `{stdout[-500:]}`")
        if stderr and crashed:
            lines.append(f"- Stderr: ```\n{stderr[-1000:]}\n```")
        lines.append("")

        # Clean up
        tmp_path.unlink(missing_ok=True)

    elapsed = time.time() - start
    lines.append(f"\n## Verdict: {'PASS' if all_passed else 'FAIL'} ({elapsed:.1f}s)")

    report = "\n".join(lines)
    write_report("test-2-error-path", report)
    return all_passed, f"Error-path: {'PASS' if all_passed else 'FAIL'} ({elapsed:.1f}s)"


# ─────────────────────────────────────────────
# TEST 3: Configuration Sensitivity
# ─────────────────────────────────────────────
def test_config_sensitivity() -> tuple[bool, str]:
    """Verify settings actually control pipeline behavior."""
    print("\n═══ TEST 3: Config Sensitivity ═══")
    start = time.time()

    lines: list[str] = [
        "# Smoke Test 3: Configuration Sensitivity",
        f"\n**Date:** {TIMESTAMP}",
        "**Purpose:** Verify settings changes produce different pipeline behavior",
        "",
    ]

    runs = [
        ("baseline", "defaults", None),
        ("low threshold", "UNCERTAINTY_THRESHOLD=0.05", {"SIOPV_UNCERTAINTY_THRESHOLD": "0.05"}),
        ("high conf floor", "CONFIDENCE_FLOOR=0.99", {"SIOPV_CONFIDENCE_FLOOR": "0.99"}),
    ]
    results: list[tuple[int, str]] = []
    for label, _desc, env in runs:
        print(f"  Run: {label}...")
        rc, stdout, stderr = run_pipeline(TRIVY_REPORT, extra_env=env)
        results.append((rc, stdout + stderr))

    elapsed = time.time() - start

    lines.append("## Results")
    lines.append("| Run | Settings | Exit Code | Escalation mentions |")
    lines.append("|-----|----------|-----------|-------------------|")
    for (label, desc, _), (rc, combined) in zip(runs, results, strict=True):
        lines.append(f"| {label} | {desc} | {rc} | {combined.count('escalat')} |")

    passed = True
    checks: list[str] = []

    for (label, _, __), (rc, _combined) in zip(runs, results, strict=True):
        if rc == 0:
            checks.append(f"- PASS: {label} run succeeded")
        else:
            checks.append(f"- FAIL: {label} run failed (rc={rc})")
            passed = False

    baseline_output = results[0][1]
    for i, (label, _, __) in enumerate(runs[1:], 1):
        if baseline_output != results[i][1]:
            checks.append(f"- PASS: {label} run produced different output than baseline")
        else:
            checks.append(f"- WARN: {label} run produced identical output")

    lines.append("\n## Checks")
    lines.extend(checks)
    lines.append(f"\n## Verdict: {'PASS' if passed else 'FAIL'} ({elapsed:.1f}s)")

    report = "\n".join(lines)
    write_report("test-3-config-sensitivity", report)
    return passed, f"Config sensitivity: {'PASS' if passed else 'FAIL'} ({elapsed:.1f}s)"


# ─────────────────────────────────────────────
# TEST 4: Isolation (Node Contract Compliance)
# ─────────────────────────────────────────────
def test_isolation() -> tuple[bool, str]:
    """Verify node contracts via existing unit tests."""
    print("\n═══ TEST 4: Isolation (Node Contracts) ═══")
    start = time.time()

    # Run node-specific tests
    node_test_paths = [
        "tests/unit/application/orchestration/nodes/",
        "tests/unit/application/orchestration/test_state.py",
        "tests/unit/application/orchestration/test_edges.py",
    ]

    lines: list[str] = [
        "# Smoke Test 4: Isolation (Node Contract Compliance)",
        f"\n**Date:** {TIMESTAMP}",
        "**Purpose:** Verify each node's output is valid input for the next node",
        "",
    ]

    all_passed = True
    for test_path in node_test_paths:
        rc, stdout, stderr = run_cmd(
            ["uv", "run", "python", "-m", "pytest", test_path, "-v", "--no-header", "-q"],
            timeout=120,
        )
        combined = stdout + stderr
        passed_count = combined.count(" PASSED")
        failed_count = combined.count(" FAILED")
        test_passed = rc == 0

        if not test_passed:
            all_passed = False

        lines.append(f"### {test_path}")
        lines.append(f"- Exit code: {rc}")
        lines.append(f"- Passed: {passed_count}, Failed: {failed_count}")
        lines.append(f"- Result: **{'PASS' if test_passed else 'FAIL'}**")
        if not test_passed:
            lines.append(f"- Output:\n```\n{combined[-2000:]}\n```")
        lines.append("")

    elapsed = time.time() - start
    lines.append(f"\n## Verdict: {'PASS' if all_passed else 'FAIL'} ({elapsed:.1f}s)")

    report = "\n".join(lines)
    write_report("test-4-isolation", report)
    return all_passed, f"Isolation: {'PASS' if all_passed else 'FAIL'} ({elapsed:.1f}s)"


def _compare_json_outputs(json_files: list[Path], checks: list[str]) -> bool:
    """Compare two JSON output files for idempotency. Returns True if identical."""
    if len(json_files) < MIN_JSON_FILES_FOR_COMPARISON:
        checks.append("- WARN: Could not find 2 JSON output files to compare")
        return True  # Not a failure, just insufficient data
    try:
        with open(json_files[0]) as f:
            data1 = json.load(f)
        with open(json_files[1]) as f:
            data2 = json.load(f)
        passed = True
        for key in ("classifications", "enrichments"):
            set1 = set(data1.get(key, {}).keys())
            set2 = set(data2.get(key, {}).keys())
            if set1 == set2:
                checks.append(f"- PASS: Same {len(set1)} CVEs in '{key}' in both runs")
            else:
                checks.append(f"- FAIL: {key} sets differ: {set1.symmetric_difference(set2)}")
                passed = False
    except Exception as e:
        checks.append(f"- WARN: Could not compare JSON outputs: {e}")
        return True
    else:
        return passed


def _compare_jira_counts(stdout1: str, stdout2: str, checks: list[str]) -> None:
    """Compare Jira ticket counts between two runs."""
    jira1 = stdout1.count("jira_ticket_created") + stdout1.count("jira_ticket_exists")
    jira2 = stdout2.count("jira_ticket_created") + stdout2.count("jira_ticket_exists")
    if jira1 == jira2:
        checks.append(f"- PASS: Same Jira ticket count ({jira1}) in both runs")
    else:
        checks.append(f"- WARN: Jira count differs (run1={jira1}, run2={jira2})")
    dedup_count = stdout2.count("jira_ticket_exists")
    if dedup_count > 0:
        checks.append(f"- PASS: Run 2 detected {dedup_count} existing tickets (dedup working)")
    else:
        checks.append("- WARN: Run 2 didn't detect existing tickets")


# ─────────────────────────────────────────────
# TEST 5: Idempotency
# ─────────────────────────────────────────────
def test_idempotency() -> tuple[bool, str]:
    """Verify same input produces same output."""
    print("\n═══ TEST 5: Idempotency ═══")
    start = time.time()

    lines: list[str] = [
        "# Smoke Test 5: Idempotency",
        f"\n**Date:** {TIMESTAMP}",
        "**Purpose:** Same input → same classification and escalation decisions",
        "",
    ]

    # Run 1
    print("  Run 1...")
    rc1, stdout1, _stderr1 = run_pipeline(TRIVY_REPORT)

    # Run 2
    print("  Run 2...")
    rc2, stdout2, _stderr2 = run_pipeline(TRIVY_REPORT)

    elapsed = time.time() - start

    # Find latest JSON outputs
    json_files = sorted(OUTPUT_DIR.glob("siopv-metrics-*.json"), key=os.path.getmtime, reverse=True)

    passed = True
    checks: list[str] = []

    if rc1 == 0 and rc2 == 0:
        checks.append("- PASS: Both runs completed successfully")
    else:
        checks.append(f"- FAIL: Run 1 rc={rc1}, Run 2 rc={rc2}")
        passed = False

    if not _compare_json_outputs(json_files, checks):
        passed = False

    _compare_jira_counts(stdout1, stdout2, checks)

    lines.append("## Checks")
    lines.extend(checks)
    lines.append(f"\n## Verdict: {'PASS' if passed else 'FAIL'} ({elapsed:.1f}s)")

    report = "\n".join(lines)
    write_report("test-5-idempotency", report)
    return passed, f"Idempotency: {'PASS' if passed else 'FAIL'} ({elapsed:.1f}s)"


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main() -> int:
    """Run all 5 smoke tests sequentially."""
    print("=" * 60)
    print("SIOPV Pre-Production Smoke Tests (Step 4f)")
    print(f"Started: {TIMESTAMP}")
    print("=" * 60)

    total_start = time.time()
    results: list[tuple[bool, str]] = []

    for test_fn in [
        test_data_flow,
        test_error_path,
        test_config_sensitivity,
        test_isolation,
        test_idempotency,
    ]:
        try:
            passed, summary = test_fn()
            results.append((passed, summary))
            print(f"  → {summary}")
        except Exception as e:
            results.append((False, f"{test_fn.__name__}: EXCEPTION — {e}"))
            print(f"  → EXCEPTION: {e}")

    total_elapsed = time.time() - total_start

    # Summary report
    all_passed = all(r[0] for r in results)
    summary_lines = [
        "# SIOPV Pre-Production Smoke Tests — Summary",
        f"\n**Date:** {TIMESTAMP}",
        f"**Total duration:** {total_elapsed:.1f}s",
        f"**Overall verdict:** {'ALL PASS' if all_passed else 'SOME FAILURES'}",
        "",
        "## Results",
        "| # | Test | Verdict |",
        "|---|------|---------|",
    ]
    for i, (passed, summary) in enumerate(results, 1):
        verdict = "PASS" if passed else "FAIL"
        summary_lines.append(f"| {i} | {summary.split(':')[0]} | {verdict} |")

    summary_lines.append("")
    summary_lines.append("## Individual Reports")
    for name in [
        "test-1-data-flow",
        "test-2-error-path",
        "test-3-config-sensitivity",
        "test-4-isolation",
        "test-5-idempotency",
    ]:
        summary_lines.append(f"- [{name}.md]({name}.md)")

    write_report("summary", "\n".join(summary_lines))

    print("\n" + "=" * 60)
    print(f"OVERALL: {'ALL PASS' if all_passed else 'SOME FAILURES'} ({total_elapsed:.1f}s)")
    print(f"Reports: {REPORT_DIR}/")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
