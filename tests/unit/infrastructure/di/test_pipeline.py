"""Unit tests for the pipeline port builder."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from siopv.infrastructure.di.pipeline import _build_optional, build_pipeline_ports

# ---------------------------------------------------------------------------
# _build_optional
# ---------------------------------------------------------------------------


class TestBuildOptional:
    """Tests for the _build_optional helper."""

    def test_returns_result_on_success(self) -> None:
        factory = MagicMock(return_value="adapter")
        settings = MagicMock()
        result = _build_optional(factory, settings, "test_adapter")
        assert result == "adapter"
        factory.assert_called_once_with(settings)

    def test_returns_none_on_failure(self) -> None:
        factory = MagicMock(side_effect=ValueError("Missing config"))
        settings = MagicMock()
        result = _build_optional(factory, settings, "test_adapter")
        assert result is None

    def test_returns_none_on_runtime_error(self) -> None:
        factory = MagicMock(side_effect=RuntimeError("Connection refused"))
        settings = MagicMock()
        result = _build_optional(factory, settings, "test_adapter")
        assert result is None


# ---------------------------------------------------------------------------
# build_pipeline_ports
# ---------------------------------------------------------------------------

_PIPELINE_PATCHES = [
    "siopv.infrastructure.di.dlp.get_dual_layer_dlp_port",
    "siopv.infrastructure.di.authorization.get_authorization_port",
    "siopv.infrastructure.di.pipeline.build_metrics_exporter",
    "siopv.infrastructure.di.pipeline.build_pdf_adapter",
    "siopv.infrastructure.di.pipeline.build_jira_adapter",
    "siopv.infrastructure.di.pipeline.build_escalation_config",
    "siopv.infrastructure.di.pipeline.build_threshold_config",
    "siopv.infrastructure.di.pipeline.build_llm_analysis",
    "siopv.infrastructure.di.pipeline.build_classifier",
    "siopv.infrastructure.di.pipeline.build_vector_store",
    "siopv.infrastructure.di.pipeline.build_osint_client",
    "siopv.infrastructure.di.pipeline.build_github_client",
    "siopv.infrastructure.di.pipeline.build_epss_client",
    "siopv.infrastructure.di.pipeline.build_nvd_client",
    "siopv.infrastructure.di.pipeline.build_trivy_parser",
]


class TestBuildPipelinePorts:
    """Tests for build_pipeline_ports."""

    def test_builds_all_ports(self) -> None:
        mocks: dict[str, MagicMock] = {}
        patches = [patch(target) for target in _PIPELINE_PATCHES]

        for p in patches:
            mock = p.start()
            mocks[p.attribute] = mock

        try:
            settings = MagicMock()
            settings.checkpoint_db_path = "test.db"
            settings.output_dir = Path("./output")

            ports = build_pipeline_ports(settings, batch_size=25)

            assert ports.checkpoint_db_path == "test.db"
            assert ports.batch_size == 25
            assert ports.output_dir == Path("./output")
            mocks["build_trivy_parser"].assert_called_once()
            mocks["get_authorization_port"].assert_called_once()
            mocks["get_dual_layer_dlp_port"].assert_called_once()
        finally:
            for p in patches:
                p.stop()

    def test_graceful_degradation(self) -> None:
        """Output ports should be None when their factories fail."""
        patches = [patch(target) for target in _PIPELINE_PATCHES]
        mocks: dict[str, MagicMock] = {}

        for p in patches:
            mock = p.start()
            mocks[p.attribute] = mock

        # Make output ports fail
        mocks["build_jira_adapter"].side_effect = ValueError("No config")
        mocks["build_pdf_adapter"].side_effect = ValueError("No config")
        mocks["build_metrics_exporter"].side_effect = ValueError("No config")

        try:
            settings = MagicMock()
            settings.checkpoint_db_path = "test.db"
            settings.output_dir = Path("./output")

            ports = build_pipeline_ports(settings)

            assert ports.jira is None
            assert ports.pdf is None
            assert ports.metrics is None
        finally:
            for p in patches:
                p.stop()
