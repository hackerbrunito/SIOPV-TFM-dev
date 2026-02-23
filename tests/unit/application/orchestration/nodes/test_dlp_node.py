"""Unit tests for dlp_node (Phase 6: DLP guardrail node).

Tests cover:
- dlp_node with no DLP port configured (skip path)
- dlp_node with empty vulnerability list
- dlp_node happy path — clean vulnerability (no PII)
- dlp_node happy path — redacted vulnerability (contains PII)
- dlp_node with multiple vulnerabilities
- dlp_node error path — DLP port raises exception (propagation behavior)
- State update structure verification
- _build_dlp_result helper function
- _run_dlp_for_vulns async function (context, structure, None description)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from siopv.application.orchestration.nodes.dlp_node import (
    _build_dlp_result,
    _run_dlp_for_vulns,
    dlp_node,
)
from siopv.domain.entities import VulnerabilityRecord
from siopv.domain.privacy.entities import DLPResult, SanitizationContext
from siopv.domain.value_objects import CVEId

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vuln(
    cve_id: str = "CVE-2024-1234",
    description: str | None = "Buffer overflow in libssl.",
) -> MagicMock:
    """Create a MagicMock that mimics VulnerabilityRecord for DLP node tests.

    Uses MagicMock(spec=VulnerabilityRecord) so attribute access is realistic
    without constructing a full Pydantic model.
    """
    mock = MagicMock(spec=VulnerabilityRecord)
    mock.cve_id = CVEId(value=cve_id)
    mock.description = description
    return mock


def _make_clean_dlp_result(text: str = "Buffer overflow in libssl.") -> DLPResult:
    """DLPResult with no detections (safe text)."""
    return DLPResult.safe_text(text)


def _make_per_cve_clean(cve_id: str = "CVE-2024-1234") -> dict[str, object]:
    """Per-CVE entry as produced by _sanitize_one when no PII is found."""
    return {
        cve_id: {
            "redactions": 0,
            "presidio_passed": True,
            "semantic_passed": True,
            "contains_pii": False,
        }
    }


def _make_per_cve_redacted(cve_id: str = "CVE-2024-5678") -> dict[str, object]:
    """Per-CVE entry as produced by _sanitize_one when PII is found."""
    return {
        cve_id: {
            "redactions": 1,
            "presidio_passed": True,
            "semantic_passed": True,
            "contains_pii": True,
        }
    }


# ---------------------------------------------------------------------------
# TestDlpNodeNoPort
# ---------------------------------------------------------------------------


class TestDlpNodeNoPort:
    """dlp_node behaviour when no DLP port is configured."""

    def test_dlp_node_no_port_returns_skipped(self) -> None:
        """dlp_port=None → dlp_result.skipped is True."""
        state: dict[str, object] = {"vulnerabilities": [_make_vuln()]}

        result = dlp_node(state, dlp_port=None)  # type: ignore[arg-type]

        assert result["dlp_result"]["skipped"] is True
        assert result["dlp_result"]["reason"] == "no_dlp_port"

    def test_dlp_node_no_port_current_node_is_dlp(self) -> None:
        """dlp_port=None still sets current_node to 'dlp'."""
        state: dict[str, object] = {"vulnerabilities": []}

        result = dlp_node(state, dlp_port=None)  # type: ignore[arg-type]

        assert result["current_node"] == "dlp"

    def test_dlp_node_default_port_is_none(self) -> None:
        """Calling dlp_node without dlp_port defaults to skip path."""
        state: dict[str, object] = {"vulnerabilities": []}

        result = dlp_node(state)  # type: ignore[arg-type]

        assert result["dlp_result"]["skipped"] is True


# ---------------------------------------------------------------------------
# TestDlpNodeEmptyVulnerabilities
# ---------------------------------------------------------------------------


class TestDlpNodeEmptyVulnerabilities:
    """dlp_node behaviour with an empty vulnerability list."""

    def test_dlp_node_empty_vulns_returns_processed_zero(self) -> None:
        """Empty vulnerabilities list → processed=0, total_redactions=0."""
        mock_port = AsyncMock()
        state: dict[str, object] = {"vulnerabilities": []}

        result = dlp_node(state, dlp_port=mock_port)  # type: ignore[arg-type]

        assert result["dlp_result"]["skipped"] is False
        assert result["dlp_result"]["processed"] == 0
        assert result["dlp_result"]["total_redactions"] == 0
        assert result["dlp_result"]["per_cve"] == {}

    def test_dlp_node_empty_vulns_does_not_call_port(self) -> None:
        """DLP port is never called when there are no vulnerabilities."""
        mock_port = AsyncMock()
        state: dict[str, object] = {"vulnerabilities": []}

        dlp_node(state, dlp_port=mock_port)  # type: ignore[arg-type]

        mock_port.sanitize.assert_not_called()

    def test_dlp_node_missing_vulnerabilities_key_treated_as_empty(self) -> None:
        """State without 'vulnerabilities' key defaults to empty list."""
        mock_port = AsyncMock()
        state: dict[str, object] = {}

        result = dlp_node(state, dlp_port=mock_port)  # type: ignore[arg-type]

        assert result["dlp_result"]["processed"] == 0


# ---------------------------------------------------------------------------
# TestDlpNodeHappyPath
# ---------------------------------------------------------------------------


class TestDlpNodeHappyPath:
    """dlp_node happy-path: vulnerabilities processed successfully."""

    def test_dlp_node_clean_vuln_no_redactions(self) -> None:
        """Clean vulnerability (no PII) produces total_redactions=0."""
        mock_port = AsyncMock()
        per_cve = _make_per_cve_clean("CVE-2024-1234")
        state: dict[str, object] = {"vulnerabilities": [_make_vuln("CVE-2024-1234")]}

        with patch(
            "siopv.application.orchestration.nodes.dlp_node.asyncio.run",
            return_value=per_cve,
        ):
            result = dlp_node(state, dlp_port=mock_port)  # type: ignore[arg-type]

        assert result["dlp_result"]["skipped"] is False
        assert result["dlp_result"]["processed"] == 1
        assert result["dlp_result"]["total_redactions"] == 0
        assert "CVE-2024-1234" in result["dlp_result"]["per_cve"]

    def test_dlp_node_redacted_vuln_has_redactions(self) -> None:
        """Vulnerability with PII produces total_redactions > 0."""
        mock_port = AsyncMock()
        per_cve = _make_per_cve_redacted("CVE-2024-5678")
        state: dict[str, object] = {"vulnerabilities": [_make_vuln("CVE-2024-5678")]}

        with patch(
            "siopv.application.orchestration.nodes.dlp_node.asyncio.run",
            return_value=per_cve,
        ):
            result = dlp_node(state, dlp_port=mock_port)  # type: ignore[arg-type]

        assert result["dlp_result"]["total_redactions"] == 1
        assert result["dlp_result"]["per_cve"]["CVE-2024-5678"]["contains_pii"] is True

    def test_dlp_node_multiple_vulns_all_processed(self) -> None:
        """Multiple vulnerabilities are all processed; redactions are summed."""
        mock_port = AsyncMock()
        per_cve = {
            **_make_per_cve_clean("CVE-2024-0001"),
            **_make_per_cve_redacted("CVE-2024-0002"),
        }
        vulns = [_make_vuln("CVE-2024-0001"), _make_vuln("CVE-2024-0002")]
        state: dict[str, object] = {"vulnerabilities": vulns}

        with patch(
            "siopv.application.orchestration.nodes.dlp_node.asyncio.run",
            return_value=per_cve,
        ):
            result = dlp_node(state, dlp_port=mock_port)  # type: ignore[arg-type]

        assert result["dlp_result"]["processed"] == 2
        assert result["dlp_result"]["total_redactions"] == 1
        assert "CVE-2024-0001" in result["dlp_result"]["per_cve"]
        assert "CVE-2024-0002" in result["dlp_result"]["per_cve"]

    def test_dlp_node_current_node_is_dlp_on_success(self) -> None:
        """Successful execution sets current_node to 'dlp'."""
        mock_port = AsyncMock()
        per_cve = _make_per_cve_clean()
        state: dict[str, object] = {"vulnerabilities": [_make_vuln()]}

        with patch(
            "siopv.application.orchestration.nodes.dlp_node.asyncio.run",
            return_value=per_cve,
        ):
            result = dlp_node(state, dlp_port=mock_port)  # type: ignore[arg-type]

        assert result["current_node"] == "dlp"


# ---------------------------------------------------------------------------
# TestDlpNodeErrorPath
# ---------------------------------------------------------------------------


class TestDlpNodeErrorPath:
    """dlp_node error handling when the DLP port raises an exception."""

    def test_dlp_node_port_raises_exception_propagates(self) -> None:
        """Exceptions from asyncio.run propagate — no silent swallowing."""
        mock_port = AsyncMock()
        state: dict[str, object] = {"vulnerabilities": [_make_vuln()]}

        with (
            patch(
                "siopv.application.orchestration.nodes.dlp_node.asyncio.run",
                side_effect=RuntimeError("DLP service unavailable"),
            ),
            pytest.raises(RuntimeError, match="DLP service unavailable"),
        ):
            dlp_node(state, dlp_port=mock_port)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestBuildDlpResult
# ---------------------------------------------------------------------------


class TestBuildDlpResult:
    """Tests for the _build_dlp_result helper function."""

    def test_build_dlp_result_sums_redactions_across_all_cves(self) -> None:
        """Total redactions are summed across all CVE entries."""
        per_cve: dict[str, object] = {
            "CVE-2024-0001": {
                "redactions": 2,
                "presidio_passed": True,
                "semantic_passed": True,
                "contains_pii": True,
            },
            "CVE-2024-0002": {
                "redactions": 0,
                "presidio_passed": True,
                "semantic_passed": True,
                "contains_pii": False,
            },
            "CVE-2024-0003": {
                "redactions": 3,
                "presidio_passed": True,
                "semantic_passed": True,
                "contains_pii": True,
            },
        }

        result = _build_dlp_result(per_cve, vuln_count=3)

        assert result["dlp_result"]["total_redactions"] == 5

    def test_build_dlp_result_structure_has_expected_keys(self) -> None:
        """Returned dict contains current_node and dlp_result with required keys."""
        per_cve: dict[str, object] = {}

        result = _build_dlp_result(per_cve, vuln_count=0)

        assert "current_node" in result
        assert "dlp_result" in result
        assert result["current_node"] == "dlp"
        dlp = result["dlp_result"]
        assert dlp["skipped"] is False
        assert "processed" in dlp
        assert "total_redactions" in dlp
        assert "per_cve" in dlp

    def test_build_dlp_result_processed_count_matches_vuln_count(self) -> None:
        """processed field equals the vuln_count argument passed in."""
        per_cve: dict[str, object] = {
            "CVE-2024-0001": {
                "redactions": 0,
                "presidio_passed": True,
                "semantic_passed": True,
                "contains_pii": False,
            },
        }

        result = _build_dlp_result(per_cve, vuln_count=5)

        assert result["dlp_result"]["processed"] == 5

    def test_build_dlp_result_non_dict_values_ignored_in_sum(self) -> None:
        """Non-dict values in per_cve are skipped when summing redactions."""
        per_cve: dict[str, object] = {
            "CVE-2024-0001": {
                "redactions": 1,
                "presidio_passed": True,
                "semantic_passed": True,
                "contains_pii": True,
            },
            "CVE-2024-0002": "unexpected_string_value",  # type: ignore[dict-item]
        }

        result = _build_dlp_result(per_cve, vuln_count=2)

        assert result["dlp_result"]["total_redactions"] == 1


# ---------------------------------------------------------------------------
# TestRunDlpForVulns
# ---------------------------------------------------------------------------


class TestRunDlpForVulns:
    """Tests for the _run_dlp_for_vulns async function."""

    async def test_run_dlp_for_vulns_calls_sanitize_for_each_vuln(self) -> None:
        """sanitize() is called once per vulnerability in the list."""
        clean_result = _make_clean_dlp_result()
        mock_port = AsyncMock()
        mock_port.sanitize = AsyncMock(return_value=clean_result)

        vuln1 = _make_vuln("CVE-2024-0001", description="First vulnerability.")
        vuln2 = _make_vuln("CVE-2024-0002", description="Second vulnerability.")

        result = await _run_dlp_for_vulns([vuln1, vuln2], mock_port)

        assert mock_port.sanitize.call_count == 2
        assert "CVE-2024-0001" in result
        assert "CVE-2024-0002" in result

    async def test_run_dlp_for_vulns_passes_description_as_sanitization_context(self) -> None:
        """_run_dlp_for_vulns wraps vuln description in SanitizationContext."""
        clean_result = _make_clean_dlp_result("Test description text.")
        mock_port = AsyncMock()
        mock_port.sanitize = AsyncMock(return_value=clean_result)

        vuln = _make_vuln("CVE-2024-1234", description="Test description text.")

        await _run_dlp_for_vulns([vuln], mock_port)

        call_arg = mock_port.sanitize.call_args[0][0]
        assert isinstance(call_arg, SanitizationContext)
        assert call_arg.text == "Test description text."

    async def test_run_dlp_for_vulns_none_description_uses_empty_string(self) -> None:
        """None description is coerced to empty string before sanitization."""
        clean_result = _make_clean_dlp_result("")
        mock_port = AsyncMock()
        mock_port.sanitize = AsyncMock(return_value=clean_result)

        vuln = _make_vuln("CVE-2024-9999", description=None)

        await _run_dlp_for_vulns([vuln], mock_port)

        call_arg = mock_port.sanitize.call_args[0][0]
        assert call_arg.text == ""

    async def test_run_dlp_for_vulns_result_has_expected_per_cve_structure(self) -> None:
        """Each CVE entry in the result dict has the four expected fields."""
        clean_result = _make_clean_dlp_result()
        mock_port = AsyncMock()
        mock_port.sanitize = AsyncMock(return_value=clean_result)

        vuln = _make_vuln("CVE-2024-1234")

        result = await _run_dlp_for_vulns([vuln], mock_port)

        entry = result["CVE-2024-1234"]
        assert isinstance(entry, dict)
        assert "redactions" in entry
        assert "presidio_passed" in entry
        assert "semantic_passed" in entry
        assert "contains_pii" in entry

    async def test_run_dlp_for_vulns_empty_list_returns_empty_dict(self) -> None:
        """Empty vulnerability list produces an empty per-CVE dict."""
        mock_port = AsyncMock()

        result = await _run_dlp_for_vulns([], mock_port)

        assert result == {}
        mock_port.sanitize.assert_not_called()
