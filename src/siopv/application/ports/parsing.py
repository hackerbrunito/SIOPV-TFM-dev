"""Port interface for Trivy report parsing in SIOPV.

Defines the contract that parsing adapters must implement following
hexagonal architecture. Use cases depend on this port, not on concrete
TrivyParser adapter implementations.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from siopv.domain.entities import VulnerabilityRecord


@runtime_checkable
class TrivyParserPort(Protocol):
    """Port interface for Trivy vulnerability report parsing.

    Implementations parse Trivy JSON reports and return VulnerabilityRecord
    entities. Both file-based and dict-based parsing are supported.
    """

    def parse_file(self, path: Path) -> list[VulnerabilityRecord]:
        """Parse a Trivy JSON report from a file path.

        Args:
            path: Path to the Trivy JSON report file.

        Returns:
            List of VulnerabilityRecord entities.

        Raises:
            TrivyParseError: If the file cannot be parsed or has invalid format.
        """
        ...

    def parse_dict(self, data: dict[str, object]) -> list[VulnerabilityRecord]:
        """Parse a Trivy report from an already-loaded dictionary.

        Args:
            data: Trivy report as a dictionary (pre-parsed JSON).

        Returns:
            List of VulnerabilityRecord entities.

        Raises:
            TrivyParseError: If the report has invalid format.
        """
        ...

    @property
    def parsed_count(self) -> int:
        """Number of successfully parsed vulnerabilities in the last parse call."""
        ...

    @property
    def skipped_count(self) -> int:
        """Number of skipped vulnerabilities (parse errors) in the last parse call."""
        ...


__all__ = ["TrivyParserPort"]
