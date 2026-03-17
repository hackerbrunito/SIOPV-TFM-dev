"""Port interface for PDF report generation in SIOPV Phase 8.

Defines the contract for generating PDF vulnerability reports
from pipeline state. Implementations live in adapters/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from siopv.application.orchestration.state import PipelineState


class PdfGeneratorPort(ABC):
    """Port interface for PDF report generator.

    Implementations must handle:
    - Rendering vulnerability data into a structured PDF layout
    - Including classification results, enrichment data, and recommendations
    - Writing the PDF to the specified output path
    """

    @abstractmethod
    def generate(self, state: PipelineState, output_path: str) -> str:
        """Generate a PDF vulnerability report from pipeline state.

        Args:
            state: Complete pipeline state with all phase results
            output_path: Absolute path where the PDF should be written

        Returns:
            Absolute path to the generated PDF file

        Raises:
            PdfGenerationError: On rendering or file system errors
        """
        ...


__all__ = [
    "PdfGeneratorPort",
]
