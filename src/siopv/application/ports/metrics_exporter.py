"""Port interface for metrics export in SIOPV Phase 8.

Defines the contract for exporting pipeline results to JSON and CSV formats.
Implementations live in adapters/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from siopv.application.orchestration.state import PipelineState


class MetricsExporterPort(ABC):
    """Port interface for metrics exporter.

    Implementations must handle:
    - Serializing pipeline state into structured JSON
    - Flattening vulnerability data into tabular CSV format
    - Writing output files to the specified paths
    """

    @abstractmethod
    def export_json(self, state: PipelineState, output_path: str) -> str:
        """Export pipeline results as a JSON file.

        Args:
            state: Complete pipeline state with all phase results
            output_path: Absolute path where the JSON should be written

        Returns:
            Absolute path to the generated JSON file

        Raises:
            ExportError: On serialization or file system errors
        """
        ...

    @abstractmethod
    def export_csv(self, state: PipelineState, output_path: str) -> str:
        """Export pipeline results as a CSV file.

        Args:
            state: Complete pipeline state with all phase results
            output_path: Absolute path where the CSV should be written

        Returns:
            Absolute path to the generated CSV file

        Raises:
            ExportError: On serialization or file system errors
        """
        ...


__all__ = [
    "MetricsExporterPort",
]
