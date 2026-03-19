"""Ingest Trivy Report Use Case.

Orchestrates the ingestion pipeline for Trivy vulnerability reports:
1. Parse Trivy JSON report
2. Deduplicate vulnerabilities
3. Group by package for batch processing
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from siopv.domain.services import (
    deduplicate_vulnerabilities,
    group_by_package,
    sort_by_severity,
)

if TYPE_CHECKING:
    from siopv.application.ports.parsing import TrivyParserPort
    from siopv.domain.entities import VulnerabilityRecord

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class IngestionResult:
    """Result of the ingestion use case."""

    records: list[VulnerabilityRecord]
    by_package: dict[str, list[VulnerabilityRecord]]
    stats: IngestionStats


@dataclass(frozen=True)
class IngestionStats:
    """Statistics from the ingestion process."""

    total_parsed: int
    total_skipped: int
    total_after_dedup: int
    unique_packages: int
    by_severity: dict[str, int]


class IngestTrivyReportUseCase:
    """Use case for ingesting Trivy vulnerability reports.

    This is the main entry point for Phase 1 of the SIOPV pipeline.
    It parses, validates, deduplicates, and organizes vulnerability data.
    """

    def __init__(self, parser: TrivyParserPort) -> None:
        """Initialize the use case with a Trivy parser port.

        Args:
            parser: Implementation of TrivyParserPort to use for parsing.
        """
        self._parser = parser

    def execute(self, report_path: Path | str) -> IngestionResult:
        """Execute the ingestion pipeline.

        Args:
            report_path: Path to Trivy JSON report file

        Returns:
            IngestionResult with processed records and statistics

        Raises:
            TrivyParseError: If the report cannot be parsed
        """
        path = Path(report_path)
        logger.info("starting_ingestion", report_path=str(path))

        raw_records = self._parser.parse_file(path)
        return self._build_result(raw_records, log_completion=True)

    def execute_from_dict(self, data: dict[str, object]) -> IngestionResult:
        """Execute ingestion from a dictionary (already parsed JSON).

        Useful for testing or when JSON is received via API.

        Args:
            data: Trivy report as dictionary

        Returns:
            IngestionResult with processed records and statistics
        """
        logger.info("starting_ingestion_from_dict")

        raw_records = self._parser.parse_dict(data)
        return self._build_result(raw_records, log_completion=False)

    def _build_result(
        self,
        raw_records: list[VulnerabilityRecord],
        *,
        log_completion: bool = True,
    ) -> IngestionResult:
        """Build ingestion result from raw records.

        Common processing pipeline: deduplicate → sort → group → stats.

        Args:
            raw_records: Parsed vulnerability records
            log_completion: Whether to log completion info

        Returns:
            IngestionResult with processed records and statistics
        """
        # Process records through pipeline
        sorted_records, by_package = self._process_records(raw_records)

        # Build statistics
        stats = IngestionStats(
            total_parsed=self._parser.parsed_count,
            total_skipped=self._parser.skipped_count,
            total_after_dedup=len(sorted_records),
            unique_packages=len(by_package),
            by_severity=self._calculate_severity_counts(sorted_records),
        )

        if log_completion:
            logger.info(
                "ingestion_complete",
                total_vulnerabilities=stats.total_after_dedup,
                unique_packages=stats.unique_packages,
                severity_breakdown=stats.by_severity,
            )

        return IngestionResult(
            records=sorted_records,
            by_package=by_package,
            stats=stats,
        )

    def _process_records(
        self,
        raw_records: list[VulnerabilityRecord],
    ) -> tuple[list[VulnerabilityRecord], dict[str, list[VulnerabilityRecord]]]:
        """Process raw records through deduplication, sorting, and grouping.

        Args:
            raw_records: Parsed vulnerability records

        Returns:
            Tuple of (sorted_records, records_by_package)
        """
        deduped_records = deduplicate_vulnerabilities(raw_records)
        sorted_records = sort_by_severity(deduped_records, descending=True)
        by_package = group_by_package(sorted_records)
        return sorted_records, by_package

    @staticmethod
    def _calculate_severity_counts(records: list[VulnerabilityRecord]) -> dict[str, int]:
        """Calculate count of records per severity level.

        Args:
            records: List of vulnerability records

        Returns:
            Dictionary mapping severity level to count
        """
        counts: dict[str, int] = {}
        for record in records:
            counts[record.severity] = counts.get(record.severity, 0) + 1
        return counts


def ingest_trivy_report(
    report_path: Path | str,
    parser: TrivyParserPort,
) -> IngestionResult:
    """Convenience function for direct invocation of Trivy report ingestion.

    Production code uses ``IngestTrivyReportUseCase`` via DI. This wrapper
    is provided for scripting, one-off invocations, and integration tests
    where full DI wiring is unnecessary.

    Args:
        report_path: Path to Trivy JSON report
        parser: TrivyParserPort implementation to use for parsing.

    Returns:
        IngestionResult with processed records and statistics
    """
    use_case = IngestTrivyReportUseCase(parser=parser)
    return use_case.execute(report_path)


__all__ = [
    "IngestTrivyReportUseCase",
    "IngestionResult",
    "IngestionStats",
    "ingest_trivy_report",
]
