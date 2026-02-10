"""Tests for Trivy JSON parser adapter."""

from pathlib import Path

import pytest

from siopv.adapters.external_apis.trivy_parser import TrivyParser, parse_trivy_report
from siopv.domain.exceptions import TrivyParseError


class TestTrivyParser:
    """Tests for TrivyParser class."""

    @pytest.fixture
    def parser(self) -> TrivyParser:
        """Create a parser instance."""
        return TrivyParser()

    @pytest.fixture
    def fixtures_path(self) -> Path:
        """Path to test fixtures."""
        return Path(__file__).parent.parent.parent / "fixtures"

    def test_parse_alpine_report_no_vulnerabilities(
        self, parser: TrivyParser, fixtures_path: Path
    ) -> None:
        """Test parsing Alpine report with no vulnerabilities."""
        report_path = fixtures_path / "trivy-alpine-report.json"

        records = parser.parse_file(report_path)

        # Alpine latest should have no vulnerabilities
        assert len(records) == 0
        assert parser.parsed_count == 0
        assert parser.skipped_count == 0

    def test_parse_python_report_with_vulnerabilities(
        self, parser: TrivyParser, fixtures_path: Path
    ) -> None:
        """Test parsing Python report with vulnerabilities."""
        report_path = fixtures_path / "trivy-python-report.json"

        records = parser.parse_file(report_path)

        # Should have multiple vulnerabilities
        assert len(records) > 0
        assert parser.parsed_count > 0

        # Check first record structure
        record = records[0]
        assert record.cve_id.value.startswith("CVE-")
        assert record.package_name != ""
        assert record.installed_version.value != ""
        assert record.severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN")

    def test_parse_file_not_found(self, parser: TrivyParser) -> None:
        """Test parsing non-existent file raises error."""
        with pytest.raises(TrivyParseError) as exc_info:
            parser.parse_file("/nonexistent/path/report.json")

        assert "not found" in str(exc_info.value)

    def test_parse_non_json_file(self, parser: TrivyParser, tmp_path: Path) -> None:
        """Test parsing non-JSON file raises error."""
        txt_file = tmp_path / "report.txt"
        txt_file.write_text("not json")

        with pytest.raises(TrivyParseError) as exc_info:
            parser.parse_file(txt_file)

        assert "Expected JSON" in str(exc_info.value)

    def test_parse_invalid_json(self, parser: TrivyParser, tmp_path: Path) -> None:
        """Test parsing invalid JSON raises error."""
        json_file = tmp_path / "report.json"
        json_file.write_text("{invalid json")

        with pytest.raises(TrivyParseError) as exc_info:
            parser.parse_file(json_file)

        assert "Invalid JSON" in str(exc_info.value)

    def test_parse_dict_basic(self, parser: TrivyParser) -> None:
        """Test parsing from dictionary."""
        data = {
            "SchemaVersion": 2,
            "ArtifactName": "test-image",
            "ArtifactType": "container_image",
            "Results": [
                {
                    "Target": "test-image (debian 11)",
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2024-12345",
                            "PkgName": "openssl",
                            "InstalledVersion": "1.1.1",
                            "Severity": "HIGH",
                        }
                    ],
                }
            ],
        }

        records = parser.parse_dict(data)

        assert len(records) == 1
        assert records[0].cve_id.value == "CVE-2024-12345"
        assert records[0].package_name == "openssl"
        assert records[0].target == "test-image (debian 11)"

    def test_parse_dict_multiple_targets(self, parser: TrivyParser) -> None:
        """Test parsing with multiple targets."""
        data = {
            "SchemaVersion": 2,
            "Results": [
                {
                    "Target": "target1",
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2024-0001",
                            "PkgName": "pkg1",
                            "InstalledVersion": "1.0",
                            "Severity": "HIGH",
                        }
                    ],
                },
                {
                    "Target": "target2",
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2024-0002",
                            "PkgName": "pkg2",
                            "InstalledVersion": "2.0",
                            "Severity": "CRITICAL",
                        }
                    ],
                },
            ],
        }

        records = parser.parse_dict(data)

        assert len(records) == 2
        assert records[0].target == "target1"
        assert records[1].target == "target2"

    def test_parse_dict_target_without_vulnerabilities(self, parser: TrivyParser) -> None:
        """Test parsing target with no vulnerabilities."""
        data = {
            "SchemaVersion": 2,
            "Results": [
                {
                    "Target": "clean-target",
                    # No Vulnerabilities key
                }
            ],
        }

        records = parser.parse_dict(data)

        assert len(records) == 0

    def test_parse_dict_empty_vulnerabilities(self, parser: TrivyParser) -> None:
        """Test parsing target with empty vulnerabilities list."""
        data = {
            "SchemaVersion": 2,
            "Results": [
                {
                    "Target": "clean-target",
                    "Vulnerabilities": [],
                }
            ],
        }

        records = parser.parse_dict(data)

        assert len(records) == 0

    def test_parse_dict_with_cvss_scores(self, parser: TrivyParser) -> None:
        """Test parsing vulnerability with CVSS scores."""
        data = {
            "SchemaVersion": 2,
            "Results": [
                {
                    "Target": "test",
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2024-12345",
                            "PkgName": "test-pkg",
                            "InstalledVersion": "1.0",
                            "Severity": "HIGH",
                            "CVSS": {
                                "nvd": {
                                    "V3Score": 7.5,
                                }
                            },
                        }
                    ],
                }
            ],
        }

        records = parser.parse_dict(data)

        assert len(records) == 1
        assert records[0].cvss_v3_score is not None
        assert records[0].cvss_v3_score.value == 7.5

    def test_parse_dict_skips_invalid_vulnerability(self, parser: TrivyParser) -> None:
        """Test that invalid vulnerabilities are skipped."""
        data = {
            "SchemaVersion": 2,
            "Results": [
                {
                    "Target": "test",
                    "Vulnerabilities": [
                        {
                            # Missing VulnerabilityID - should be skipped
                            "PkgName": "test-pkg",
                            "InstalledVersion": "1.0",
                            "Severity": "HIGH",
                        },
                        {
                            "VulnerabilityID": "CVE-2024-12345",
                            "PkgName": "valid-pkg",
                            "InstalledVersion": "1.0",
                            "Severity": "HIGH",
                        },
                    ],
                }
            ],
        }

        records = parser.parse_dict(data)

        assert len(records) == 1
        assert parser.skipped_count == 1
        assert records[0].package_name == "valid-pkg"

    def test_parse_dict_warns_on_schema_mismatch(self, parser: TrivyParser) -> None:
        """Test warning on schema version mismatch."""
        data = {
            "SchemaVersion": 99,  # Unexpected version
            "Results": [],
        }

        parser.parse_dict(data)

        # Should log a warning but not fail
        assert parser.parsed_count == 0


class TestParseTrivyReportFunction:
    """Tests for the convenience function."""

    def test_parse_trivy_report_function(self, tmp_path: Path) -> None:
        """Test the convenience function works."""
        json_file = tmp_path / "report.json"
        json_file.write_text(
            """{
            "SchemaVersion": 2,
            "Results": [
                {
                    "Target": "test",
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2024-99999",
                            "PkgName": "test-pkg",
                            "InstalledVersion": "1.0",
                            "Severity": "LOW"
                        }
                    ]
                }
            ]
        }"""
        )

        records = parse_trivy_report(json_file)

        assert len(records) == 1
        assert records[0].cve_id.value == "CVE-2024-99999"
