"""Tests for MetricsExporterPort ABC interface compliance."""

from __future__ import annotations

from typing import Any

import pytest

from siopv.application.ports.metrics_exporter import MetricsExporterPort


class TestMetricsExporterPortInterface:
    """Tests for MetricsExporterPort ABC definition."""

    def test_metrics_exporter_port_is_abstract(self) -> None:
        """MetricsExporterPort should not be directly instantiable."""
        with pytest.raises(TypeError):
            MetricsExporterPort()  # type: ignore[abstract]

    def test_concrete_implementation_instantiable(self) -> None:
        """A class implementing all abstract methods should be instantiable."""

        class ConcreteExporter(MetricsExporterPort):
            def export_json(self, _state: dict[str, Any], output_path: str) -> str:  # type: ignore[override]
                return output_path

            def export_csv(self, _state: dict[str, Any], output_path: str) -> str:  # type: ignore[override]
                return output_path

        exporter = ConcreteExporter()
        assert isinstance(exporter, MetricsExporterPort)

    def test_partial_implementation_not_instantiable(self) -> None:
        """A class implementing only export_json should not be instantiable."""

        class PartialExporter(MetricsExporterPort):
            def export_json(self, _state: dict[str, Any], output_path: str) -> str:  # type: ignore[override]
                return output_path

        with pytest.raises(TypeError):
            PartialExporter()  # type: ignore[abstract]

    def test_export_json_returns_path(self) -> None:
        """export_json should return the path to the written file."""

        class StubExporter(MetricsExporterPort):
            def export_json(self, _state: dict[str, Any], output_path: str) -> str:  # type: ignore[override]
                return output_path

            def export_csv(self, _state: dict[str, Any], output_path: str) -> str:  # type: ignore[override]
                return output_path

        exporter = StubExporter()
        result = exporter.export_json({}, "/tmp/metrics.json")  # type: ignore[arg-type]
        assert result == "/tmp/metrics.json"

    def test_export_csv_returns_path(self) -> None:
        """export_csv should return the path to the written file."""

        class StubExporter(MetricsExporterPort):
            def export_json(self, _state: dict[str, Any], output_path: str) -> str:  # type: ignore[override]
                return output_path

            def export_csv(self, _state: dict[str, Any], output_path: str) -> str:  # type: ignore[override]
                return output_path

        exporter = StubExporter()
        result = exporter.export_csv({}, "/tmp/metrics.csv")  # type: ignore[arg-type]
        assert result == "/tmp/metrics.csv"

    def test_port_importable_from_ports_package(self) -> None:
        """MetricsExporterPort should be importable from the ports package."""
        from siopv.application.ports import MetricsExporterPort as PortFromPackage

        assert PortFromPackage is MetricsExporterPort
