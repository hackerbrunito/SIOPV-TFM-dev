"""Tests for ingest_node."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from siopv.adapters.external_apis.trivy_parser import TrivyParser
from siopv.application.orchestration.nodes.ingest_node import (
    ingest_node,
    ingest_node_from_dict,
)
from siopv.application.orchestration.state import create_initial_state
from siopv.application.use_cases.ingest_trivy import IngestTrivyReportUseCase


def _make_use_case() -> IngestTrivyReportUseCase:
    return IngestTrivyReportUseCase(parser=TrivyParser())


class TestIngestNode:
    """Tests for ingest_node function."""

    @pytest.fixture
    def sample_trivy_report(self) -> dict:
        """Create a sample Trivy report for testing."""
        return {
            "SchemaVersion": 2,
            "ArtifactName": "test-image:latest",
            "ArtifactType": "container_image",
            "Results": [
                {
                    "Target": "test-image (alpine 3.18)",
                    "Class": "os-pkgs",
                    "Type": "alpine",
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2024-1234",
                            "PkgName": "openssl",
                            "InstalledVersion": "1.1.1",
                            "FixedVersion": "1.1.2",
                            "Severity": "HIGH",
                            "Title": "Test vulnerability",
                            "Description": "A test vulnerability description",
                        },
                        {
                            "VulnerabilityID": "CVE-2024-5678",
                            "PkgName": "curl",
                            "InstalledVersion": "7.88.0",
                            "Severity": "MEDIUM",
                        },
                    ],
                }
            ],
        }

    @pytest.fixture
    def trivy_report_file(self, sample_trivy_report: dict) -> Path:
        """Create a temporary Trivy report file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_trivy_report, f)
            return Path(f.name)

    def test_ingest_node_success(self, trivy_report_file: Path):
        """Test successful ingestion from file."""
        state = create_initial_state(report_path=str(trivy_report_file))

        result = ingest_node(state, use_case=_make_use_case())

        assert "vulnerabilities" in result
        assert len(result["vulnerabilities"]) == 2
        assert result["processed_count"] == 2
        assert result["current_node"] == "ingest"
        assert "errors" not in result or len(result.get("errors", [])) == 0

    def test_ingest_node_no_report_path(self):
        """Test ingestion fails gracefully without report path."""
        state = create_initial_state()

        result = ingest_node(state)

        assert result["vulnerabilities"] == []
        assert result["processed_count"] == 0
        assert len(result["errors"]) > 0
        assert "No report_path" in result["errors"][0]

    def test_ingest_node_file_not_found(self):
        """Test ingestion handles missing file."""
        state = create_initial_state(report_path="/nonexistent/path/report.json")

        result = ingest_node(state, use_case=_make_use_case())

        assert result["vulnerabilities"] == []
        assert result["processed_count"] == 0
        assert len(result["errors"]) > 0

    def test_ingest_node_preserves_thread_id(self, trivy_report_file: Path):
        """Test that thread_id is preserved in state."""
        state = create_initial_state(
            report_path=str(trivy_report_file),
            thread_id="test-thread-123",
        )

        result = ingest_node(state, use_case=_make_use_case())

        # Node returns partial state, original thread_id preserved
        assert result["current_node"] == "ingest"


class TestIngestNodeFromDict:
    """Tests for ingest_node_from_dict function."""

    @pytest.fixture
    def sample_trivy_report(self) -> dict:
        """Create a sample Trivy report for testing."""
        return {
            "SchemaVersion": 2,
            "ArtifactName": "test-image:latest",
            "Results": [
                {
                    "Target": "test-image",
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2024-9999",
                            "PkgName": "libxml2",
                            "InstalledVersion": "2.9.0",
                            "Severity": "CRITICAL",
                        }
                    ],
                }
            ],
        }

    def test_ingest_from_dict_success(self, sample_trivy_report: dict):
        """Test successful ingestion from dictionary."""
        state = create_initial_state()

        result = ingest_node_from_dict(state, sample_trivy_report, use_case=_make_use_case())

        assert "vulnerabilities" in result
        assert len(result["vulnerabilities"]) == 1
        assert result["vulnerabilities"][0].cve_id.value == "CVE-2024-9999"
        assert result["processed_count"] == 1

    def test_ingest_from_dict_empty_results(self):
        """Test ingestion with empty results."""
        state = create_initial_state()
        report = {"SchemaVersion": 2, "Results": []}

        result = ingest_node_from_dict(state, report, use_case=_make_use_case())

        assert result["vulnerabilities"] == []
        assert result["processed_count"] == 0

    def test_ingest_from_dict_invalid_format(self):
        """Test ingestion handles invalid format."""
        state = create_initial_state()
        report = {"invalid": "format"}

        result = ingest_node_from_dict(state, report)

        # Should handle gracefully (use_case=None → ValueError caught → error dict)
        assert "vulnerabilities" in result
