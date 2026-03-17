"""Tests for Ingest Trivy Report Use Case."""

from pathlib import Path

import pytest

from siopv.adapters.external_apis.trivy_parser import TrivyParser
from siopv.application.use_cases.ingest_trivy import (
    IngestionResult,
    IngestionStats,
    IngestTrivyReportUseCase,
    ingest_trivy_report,
)
from siopv.domain.exceptions import TrivyParseError


class TestIngestTrivyReportUseCase:
    """Tests for IngestTrivyReportUseCase."""

    @pytest.fixture
    def use_case(self) -> IngestTrivyReportUseCase:
        """Create a use case instance."""
        return IngestTrivyReportUseCase(parser=TrivyParser())

    @pytest.fixture
    def fixtures_path(self) -> Path:
        """Path to test fixtures."""
        return Path(__file__).parent.parent.parent / "fixtures"

    def test_execute_alpine_report(
        self, use_case: IngestTrivyReportUseCase, fixtures_path: Path
    ) -> None:
        """Test ingestion of Alpine report (no vulnerabilities)."""
        report_path = fixtures_path / "trivy-alpine-report.json"

        result = use_case.execute(report_path)

        assert isinstance(result, IngestionResult)
        assert len(result.records) == 0
        assert len(result.by_package) == 0
        assert result.stats.total_parsed == 0
        assert result.stats.total_after_dedup == 0

    def test_execute_python_report(
        self, use_case: IngestTrivyReportUseCase, fixtures_path: Path
    ) -> None:
        """Test ingestion of Python report (with vulnerabilities)."""
        report_path = fixtures_path / "trivy-python-report.json"

        result = use_case.execute(report_path)

        assert isinstance(result, IngestionResult)
        assert len(result.records) > 0
        assert len(result.by_package) > 0
        assert result.stats.total_parsed > 0
        assert result.stats.unique_packages > 0

    def test_execute_returns_sorted_records(
        self, use_case: IngestTrivyReportUseCase, fixtures_path: Path
    ) -> None:
        """Test that records are sorted by severity."""
        report_path = fixtures_path / "trivy-python-report.json"

        result = use_case.execute(report_path)

        if len(result.records) > 1:
            # Verify descending severity order
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}
            for i in range(len(result.records) - 1):
                current_order = severity_order.get(result.records[i].severity, 5)
                next_order = severity_order.get(result.records[i + 1].severity, 5)
                assert current_order <= next_order

    def test_execute_groups_by_package(
        self, use_case: IngestTrivyReportUseCase, fixtures_path: Path
    ) -> None:
        """Test that records are grouped by package."""
        report_path = fixtures_path / "trivy-python-report.json"

        result = use_case.execute(report_path)

        # All records should be in some package group
        total_in_groups = sum(len(vulns) for vulns in result.by_package.values())
        assert total_in_groups == len(result.records)

    def test_execute_stats_accuracy(
        self, use_case: IngestTrivyReportUseCase, fixtures_path: Path
    ) -> None:
        """Test that stats are accurate."""
        report_path = fixtures_path / "trivy-python-report.json"

        result = use_case.execute(report_path)

        # Stats should match actual data
        assert result.stats.total_after_dedup == len(result.records)
        assert result.stats.unique_packages == len(result.by_package)

        # Severity counts should sum to total
        severity_sum = sum(result.stats.by_severity.values())
        assert severity_sum == len(result.records)

    def test_execute_file_not_found(self, use_case: IngestTrivyReportUseCase) -> None:
        """Test error on non-existent file."""
        with pytest.raises(TrivyParseError):
            use_case.execute("/nonexistent/path/report.json")

    def test_execute_from_dict(self, use_case: IngestTrivyReportUseCase) -> None:
        """Test ingestion from dictionary."""
        data = {
            "SchemaVersion": 2,
            "Results": [
                {
                    "Target": "test-image",
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2024-0001",
                            "PkgName": "openssl",
                            "InstalledVersion": "1.1.1",
                            "Severity": "CRITICAL",
                        },
                        {
                            "VulnerabilityID": "CVE-2024-0002",
                            "PkgName": "openssl",
                            "InstalledVersion": "1.1.1",
                            "Severity": "HIGH",
                        },
                        {
                            "VulnerabilityID": "CVE-2024-0003",
                            "PkgName": "curl",
                            "InstalledVersion": "7.68.0",
                            "Severity": "MEDIUM",
                        },
                    ],
                }
            ],
        }

        result = use_case.execute_from_dict(data)

        assert len(result.records) == 3
        assert len(result.by_package) == 2
        assert "openssl" in result.by_package
        assert "curl" in result.by_package
        assert len(result.by_package["openssl"]) == 2
        assert len(result.by_package["curl"]) == 1

    def test_execute_from_dict_deduplicates(self, use_case: IngestTrivyReportUseCase) -> None:
        """Test that duplicates are removed."""
        data = {
            "SchemaVersion": 2,
            "Results": [
                {
                    "Target": "target1",
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2024-0001",
                            "PkgName": "pkg",
                            "InstalledVersion": "1.0",
                            "Severity": "HIGH",
                            "PkgPath": "path1",
                        }
                    ],
                },
                {
                    "Target": "target2",
                    "Vulnerabilities": [
                        {
                            # Same CVE, same package, same version - duplicate
                            "VulnerabilityID": "CVE-2024-0001",
                            "PkgName": "pkg",
                            "InstalledVersion": "1.0",
                            "Severity": "HIGH",
                            "PkgPath": "path2",
                        }
                    ],
                },
            ],
        }

        result = use_case.execute_from_dict(data)

        # Should be deduplicated to 1 record
        assert len(result.records) == 1
        # But locations should be merged
        assert len(result.records[0].locations) == 2


class TestIngestionStats:
    """Tests for IngestionStats dataclass."""

    def test_stats_creation(self) -> None:
        """Test creating stats object."""
        stats = IngestionStats(
            total_parsed=100,
            total_skipped=5,
            total_after_dedup=80,
            unique_packages=20,
            by_severity={"CRITICAL": 10, "HIGH": 30, "MEDIUM": 40},
        )

        assert stats.total_parsed == 100
        assert stats.total_skipped == 5
        assert stats.total_after_dedup == 80
        assert stats.unique_packages == 20
        assert stats.by_severity["CRITICAL"] == 10

    def test_stats_is_frozen(self) -> None:
        """Test that stats are immutable."""
        stats = IngestionStats(
            total_parsed=100,
            total_skipped=5,
            total_after_dedup=80,
            unique_packages=20,
            by_severity={},
        )

        with pytest.raises(AttributeError):
            stats.total_parsed = 200  # type: ignore[misc]


class TestIngestTrivyReportFunction:
    """Tests for the convenience function."""

    @pytest.fixture
    def fixtures_path(self) -> Path:
        """Path to test fixtures."""
        return Path(__file__).parent.parent.parent / "fixtures"

    def test_convenience_function(self, fixtures_path: Path) -> None:
        """Test the convenience function works."""
        report_path = fixtures_path / "trivy-alpine-report.json"

        result = ingest_trivy_report(report_path, parser=TrivyParser())

        assert isinstance(result, IngestionResult)
        assert isinstance(result.stats, IngestionStats)
