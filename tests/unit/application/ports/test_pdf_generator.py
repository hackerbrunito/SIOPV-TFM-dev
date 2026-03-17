"""Tests for PdfGeneratorPort ABC interface compliance."""

from __future__ import annotations

from typing import Any

import pytest

from siopv.application.ports.pdf_generator import PdfGeneratorPort


class TestPdfGeneratorPortInterface:
    """Tests for PdfGeneratorPort ABC definition."""

    def test_pdf_generator_port_is_abstract(self) -> None:
        """PdfGeneratorPort should not be directly instantiable."""
        with pytest.raises(TypeError):
            PdfGeneratorPort()  # type: ignore[abstract]

    def test_concrete_implementation_instantiable(self) -> None:
        """A class implementing generate should be instantiable."""

        class ConcretePdfGenerator(PdfGeneratorPort):
            def generate(self, _state: dict[str, Any], output_path: str) -> str:  # type: ignore[override]
                return output_path

        generator = ConcretePdfGenerator()
        assert isinstance(generator, PdfGeneratorPort)

    def test_partial_implementation_not_instantiable(self) -> None:
        """A class without generate method should not be instantiable."""

        class EmptyPdfGenerator(PdfGeneratorPort):
            pass

        with pytest.raises(TypeError):
            EmptyPdfGenerator()  # type: ignore[abstract]

    def test_generate_returns_path(self) -> None:
        """generate should return the path to the written PDF."""

        class StubPdfGenerator(PdfGeneratorPort):
            def generate(self, _state: dict[str, Any], output_path: str) -> str:  # type: ignore[override]
                return output_path

        generator = StubPdfGenerator()
        result = generator.generate({}, "/tmp/report.pdf")  # type: ignore[arg-type]
        assert result == "/tmp/report.pdf"

    def test_port_importable_from_ports_package(self) -> None:
        """PdfGeneratorPort should be importable from the ports package."""
        from siopv.application.ports import PdfGeneratorPort as PortFromPackage

        assert PortFromPackage is PdfGeneratorPort
