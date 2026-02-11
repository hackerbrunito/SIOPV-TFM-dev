"""Trivy JSON report parser adapter.

Parses Trivy scan reports and extracts vulnerability records.
Supports Trivy schema version 2.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from siopv.domain.entities import VulnerabilityRecord
from siopv.domain.exceptions import TrivyParseError

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = structlog.get_logger(__name__)


class TrivyParser:
    """Parser for Trivy JSON vulnerability reports.

    Handles Trivy schema version 2 reports with structure:
    - Results[]: Array of scan results per target
    - Results[].Vulnerabilities[]: Array of vulnerabilities found
    """

    SUPPORTED_SCHEMA_VERSION = 2

    def __init__(self) -> None:
        """Initialize the Trivy parser."""
        self._parsed_count = 0
        self._skipped_count = 0

    def parse_file(self, file_path: Path | str) -> list[VulnerabilityRecord]:
        """Parse a Trivy JSON report file.

        Args:
            file_path: Path to the Trivy JSON report file

        Returns:
            List of VulnerabilityRecord entities

        Raises:
            TrivyParseError: If the file cannot be parsed or has invalid format
        """
        path = Path(file_path)

        if not path.exists():
            msg = f"Trivy report file not found: {path}"
            raise TrivyParseError(msg)

        if path.suffix != ".json":
            msg = f"Expected JSON file, got: {path.suffix}"
            raise TrivyParseError(msg)

        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON in Trivy report: {e}"
            raise TrivyParseError(msg) from e

        return self.parse_dict(data)

    def parse_dict(self, data: dict[str, object]) -> list[VulnerabilityRecord]:
        """Parse a Trivy report from a dictionary.

        Args:
            data: Trivy report as dictionary

        Returns:
            List of VulnerabilityRecord entities

        Raises:
            TrivyParseError: If the report has invalid format
        """
        self._parsed_count = 0
        self._skipped_count = 0

        # Validate schema version
        schema_version = data.get("SchemaVersion")
        if schema_version != self.SUPPORTED_SCHEMA_VERSION:
            logger.warning(
                "unexpected_schema_version",
                expected=self.SUPPORTED_SCHEMA_VERSION,
                actual=schema_version,
            )

        # Extract artifact info for logging
        artifact_name = data.get("ArtifactName", "unknown")
        artifact_type = data.get("ArtifactType", "unknown")

        logger.info(
            "parsing_trivy_report",
            artifact_name=artifact_name,
            artifact_type=artifact_type,
        )

        # Parse all results
        records = list(self._iterate_vulnerabilities(data))

        logger.info(
            "trivy_parsing_complete",
            total_vulnerabilities=self._parsed_count,
            skipped=self._skipped_count,
            artifact=artifact_name,
        )

        return records

    def _iterate_vulnerabilities(self, data: dict[str, object]) -> Iterator[VulnerabilityRecord]:
        """Iterate over all vulnerabilities in the report.

        Args:
            data: Trivy report dictionary

        Yields:
            VulnerabilityRecord for each vulnerability found
        """
        results = data.get("Results", [])

        # data.get returns object; Trivy JSON Results is list[dict] at runtime
        for result in results:  # type: ignore[attr-defined]
            target = result.get("Target", "")
            vulnerabilities = result.get("Vulnerabilities", [])

            if not vulnerabilities:
                logger.debug("no_vulnerabilities_in_target", target=target)
                continue

            for vuln in vulnerabilities:
                try:
                    record = VulnerabilityRecord.from_trivy(vuln, target=target)
                    self._parsed_count += 1
                    yield record
                except (KeyError, ValueError) as e:
                    self._skipped_count += 1
                    logger.warning(
                        "skipped_vulnerability",
                        error=str(e),
                        vuln_id=vuln.get("VulnerabilityID", "unknown"),
                    )

    @property
    def parsed_count(self) -> int:
        """Return count of successfully parsed vulnerabilities."""
        return self._parsed_count

    @property
    def skipped_count(self) -> int:
        """Return count of skipped vulnerabilities due to errors."""
        return self._skipped_count


def parse_trivy_report(file_path: Path | str) -> list[VulnerabilityRecord]:
    """Convenience function to parse a Trivy report file.

    Args:
        file_path: Path to Trivy JSON report

    Returns:
        List of VulnerabilityRecord entities
    """
    parser = TrivyParser()
    return parser.parse_file(file_path)


__all__ = ["TrivyParser", "parse_trivy_report"]
