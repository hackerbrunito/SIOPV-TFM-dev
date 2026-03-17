"""Tests for MetricsExporterAdapter — CSV and JSON export.

Covers:
- JSON export strips SecretStr values
- CSV columns match spec exactly
- Atomic write pattern (write to .tmp then rename)
- Output dir creation
- File naming convention
"""

from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from siopv.adapters.output.metrics_exporter_adapter import (
    CSV_COLUMNS,
    MetricsExporterAdapter,
    _strip_secret_values,
)
from siopv.application.orchestration.state import PipelineState, create_initial_state

# === Fixtures ===


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Provide a temporary output directory."""
    return tmp_path / "output"


@pytest.fixture
def exporter(tmp_output_dir: Path) -> MetricsExporterAdapter:
    """Create a MetricsExporterAdapter pointed at tmp dir."""
    return MetricsExporterAdapter(output_dir=tmp_output_dir)


@pytest.fixture
def sample_state() -> PipelineState:
    """Create a minimal PipelineState for testing."""
    return create_initial_state(
        thread_id="test-thread-001",
        report_path="/tmp/trivy-report.json",
    )


@pytest.fixture
def state_with_vulns() -> PipelineState:
    """Create a PipelineState with vulnerability dicts (serialized form)."""
    state = create_initial_state(thread_id="test-thread-002")
    # Use dict form (as would come from LangGraph serialization)
    state["vulnerabilities"] = [
        {
            "cve_id": {"value": "CVE-2024-1234"},
            "package_name": "openssl",
            "installed_version": {"value": "1.1.1"},
            "fixed_version": {"value": "1.1.2"},
            "severity": "HIGH",
            "cvss_v3_score": {"value": 8.1},
        },
        {
            "cve_id": {"value": "CVE-2024-5678"},
            "package_name": "curl",
            "installed_version": {"value": "7.80.0"},
            "fixed_version": None,
            "severity": "MEDIUM",
            "cvss_v3_score": None,
        },
    ]
    state["escalation_required"] = True
    state["human_decision"] = "approve"
    state["review_deadline"] = "2026-03-20T12:00:00Z"
    state["dlp_result"] = {"applied": True}
    return state


# === JSON Export Tests ===


class TestExportJson:
    """Tests for JSON export functionality."""

    def test_json_export_creates_file(
        self, exporter: MetricsExporterAdapter, tmp_output_dir: Path, sample_state: PipelineState
    ) -> None:
        """JSON export creates a valid JSON file at the specified path."""
        output_path = str(tmp_output_dir / "metrics-test-001.json")
        result = exporter.export_json(sample_state, output_path)

        assert result == output_path
        assert Path(output_path).exists()

        data = json.loads(Path(output_path).read_text())
        assert data["thread_id"] == "test-thread-001"

    def test_json_export_strips_secret_str(
        self, exporter: MetricsExporterAdapter, tmp_output_dir: Path
    ) -> None:
        """JSON export replaces SecretStr values with **REDACTED**."""
        state = create_initial_state(thread_id="secret-test")
        # Inject a SecretStr into state dict
        state["authorization_result"] = {
            "token": SecretStr("super-secret-token"),
            "user": "test-user",
        }

        output_path = str(tmp_output_dir / "metrics-secret.json")
        exporter.export_json(state, output_path)

        data = json.loads(Path(output_path).read_text())
        auth_result = data["authorization_result"]
        assert auth_result["token"] == "**REDACTED**"
        assert auth_result["user"] == "test-user"

    def test_json_export_no_tmp_file_remains(
        self, exporter: MetricsExporterAdapter, tmp_output_dir: Path, sample_state: PipelineState
    ) -> None:
        """After JSON export, no .tmp file should remain (atomic write)."""
        output_path = str(tmp_output_dir / "metrics-atomic.json")
        exporter.export_json(sample_state, output_path)

        tmp_file = Path(output_path + ".tmp")
        assert not tmp_file.exists()

    def test_json_export_valid_json(
        self, exporter: MetricsExporterAdapter, tmp_output_dir: Path, sample_state: PipelineState
    ) -> None:
        """Exported file must be valid JSON."""
        output_path = str(tmp_output_dir / "metrics-valid.json")
        exporter.export_json(sample_state, output_path)

        content = Path(output_path).read_text()
        data = json.loads(content)
        assert isinstance(data, dict)

    def test_json_export_creates_parent_dirs(
        self, exporter: MetricsExporterAdapter, tmp_output_dir: Path, sample_state: PipelineState
    ) -> None:
        """JSON export creates intermediate directories if needed."""
        output_path = str(tmp_output_dir / "nested" / "deep" / "metrics.json")
        result = exporter.export_json(sample_state, output_path)

        assert result == output_path
        assert Path(output_path).exists()


# === CSV Export Tests ===


class TestExportCsv:
    """Tests for CSV export functionality."""

    def test_csv_columns_match_spec(
        self,
        exporter: MetricsExporterAdapter,
        tmp_output_dir: Path,
        state_with_vulns: PipelineState,
    ) -> None:
        """CSV header columns must exactly match the spec."""
        output_path = str(tmp_output_dir / "metrics-cols.csv")
        exporter.export_csv(state_with_vulns, output_path)

        content = Path(output_path).read_text()
        reader = csv.DictReader(StringIO(content))
        assert reader.fieldnames is not None
        assert list(reader.fieldnames) == CSV_COLUMNS

    def test_csv_one_row_per_vulnerability(
        self,
        exporter: MetricsExporterAdapter,
        tmp_output_dir: Path,
        state_with_vulns: PipelineState,
    ) -> None:
        """CSV should have one data row per vulnerability."""
        output_path = str(tmp_output_dir / "metrics-rows.csv")
        exporter.export_csv(state_with_vulns, output_path)

        content = Path(output_path).read_text()
        reader = csv.DictReader(StringIO(content))
        rows = list(reader)
        assert len(rows) == 2

    def test_csv_vulnerability_data_extracted(
        self,
        exporter: MetricsExporterAdapter,
        tmp_output_dir: Path,
        state_with_vulns: PipelineState,
    ) -> None:
        """CSV rows contain correct vulnerability data."""
        output_path = str(tmp_output_dir / "metrics-data.csv")
        exporter.export_csv(state_with_vulns, output_path)

        content = Path(output_path).read_text()
        reader = csv.DictReader(StringIO(content))
        rows = list(reader)

        first_row = rows[0]
        assert first_row["cve_id"] == "CVE-2024-1234"
        assert first_row["package"] == "openssl"
        assert first_row["version"] == "1.1.1"
        assert first_row["severity"] == "HIGH"
        assert first_row["cvss_score"] == "8.1"
        assert first_row["fix_available"] == "True"
        assert first_row["human_review_required"] == "True"
        assert first_row["human_decision"] == "approve"
        assert first_row["dlp_applied"] == "True"

        second_row = rows[1]
        assert second_row["cve_id"] == "CVE-2024-5678"
        assert second_row["fix_available"] == "False"
        assert second_row["cvss_score"] == ""

    def test_csv_run_id_from_thread_id(
        self,
        exporter: MetricsExporterAdapter,
        tmp_output_dir: Path,
        state_with_vulns: PipelineState,
    ) -> None:
        """CSV run_id column should match state thread_id."""
        output_path = str(tmp_output_dir / "metrics-runid.csv")
        exporter.export_csv(state_with_vulns, output_path)

        content = Path(output_path).read_text()
        reader = csv.DictReader(StringIO(content))
        rows = list(reader)
        for row in rows:
            assert row["run_id"] == "test-thread-002"

    def test_csv_no_tmp_file_remains(
        self,
        exporter: MetricsExporterAdapter,
        tmp_output_dir: Path,
        state_with_vulns: PipelineState,
    ) -> None:
        """After CSV export, no .tmp file should remain (atomic write)."""
        output_path = str(tmp_output_dir / "metrics-atomic.csv")
        exporter.export_csv(state_with_vulns, output_path)

        tmp_file = Path(output_path + ".tmp")
        assert not tmp_file.exists()

    def test_csv_empty_vulnerabilities(
        self, exporter: MetricsExporterAdapter, tmp_output_dir: Path, sample_state: PipelineState
    ) -> None:
        """CSV with no vulnerabilities should only have a header row."""
        output_path = str(tmp_output_dir / "metrics-empty.csv")
        exporter.export_csv(sample_state, output_path)

        content = Path(output_path).read_text()
        reader = csv.DictReader(StringIO(content))
        rows = list(reader)
        assert len(rows) == 0
        # But header must still be present
        assert content.startswith(",".join(CSV_COLUMNS)[:20])


# === Output Directory Tests ===


class TestOutputDirectory:
    """Tests for output directory creation."""

    def test_creates_output_dir_on_json_export(self, tmp_path: Path) -> None:
        """Output directory is created automatically on JSON export."""
        output_dir = tmp_path / "new_output_dir"
        assert not output_dir.exists()

        exporter = MetricsExporterAdapter(output_dir=output_dir)
        state = create_initial_state(thread_id="dir-test")
        exporter.export_json(state, str(output_dir / "test.json"))

        assert output_dir.exists()

    def test_creates_output_dir_on_csv_export(self, tmp_path: Path) -> None:
        """Output directory is created automatically on CSV export."""
        output_dir = tmp_path / "new_csv_dir"
        assert not output_dir.exists()

        exporter = MetricsExporterAdapter(output_dir=output_dir)
        state = create_initial_state(thread_id="dir-test-csv")
        exporter.export_csv(state, str(output_dir / "test.csv"))

        assert output_dir.exists()

    def test_env_var_output_dir(self, tmp_path: Path) -> None:
        """SIOPV_OUTPUT_DIR env var sets the output directory."""
        env_dir = str(tmp_path / "env_output")
        with patch.dict("os.environ", {"SIOPV_OUTPUT_DIR": env_dir}):
            exporter = MetricsExporterAdapter()
            assert str(exporter._output_dir) == env_dir

    def test_explicit_dir_overrides_env(self, tmp_path: Path) -> None:
        """Explicit output_dir parameter overrides SIOPV_OUTPUT_DIR."""
        explicit = tmp_path / "explicit"
        with patch.dict("os.environ", {"SIOPV_OUTPUT_DIR": "/some/env/path"}):
            exporter = MetricsExporterAdapter(output_dir=explicit)
            assert exporter._output_dir == explicit


# === Atomic Write Tests ===


class TestAtomicWrite:
    """Tests for atomic write pattern."""

    def test_json_atomic_write_uses_tmp(
        self, tmp_output_dir: Path, sample_state: PipelineState
    ) -> None:
        """Verify atomic write creates .tmp then replaces."""
        exporter = MetricsExporterAdapter(output_dir=tmp_output_dir)
        output_path = str(tmp_output_dir / "atomic-test.json")

        original_replace = __builtins__["__import__"]  # noqa: F841
        replace_calls: list[tuple[str, str]] = []

        original_os_replace = __import__("os").replace

        def tracking_replace(src: str, dst: str) -> None:
            replace_calls.append((src, dst))
            original_os_replace(src, dst)

        with patch(
            "siopv.adapters.output.metrics_exporter_adapter.os.replace",
            side_effect=tracking_replace,
        ):
            exporter.export_json(sample_state, output_path)

        assert len(replace_calls) == 1
        src, dst = replace_calls[0]
        assert src.endswith(".json.tmp")
        assert dst == output_path

    def test_csv_atomic_write_uses_tmp(
        self, tmp_output_dir: Path, state_with_vulns: PipelineState
    ) -> None:
        """Verify CSV atomic write creates .tmp then replaces."""
        exporter = MetricsExporterAdapter(output_dir=tmp_output_dir)
        output_path = str(tmp_output_dir / "atomic-test.csv")

        replace_calls: list[tuple[str, str]] = []
        original_os_replace = __import__("os").replace

        def tracking_replace(src: str, dst: str) -> None:
            replace_calls.append((src, dst))
            original_os_replace(src, dst)

        with patch(
            "siopv.adapters.output.metrics_exporter_adapter.os.replace",
            side_effect=tracking_replace,
        ):
            exporter.export_csv(state_with_vulns, output_path)

        assert len(replace_calls) == 1
        src, dst = replace_calls[0]
        assert src.endswith(".csv.tmp")
        assert dst == output_path


# === File Naming Convention Tests ===


class TestFileNaming:
    """Tests for file naming convention."""

    def test_json_file_naming(
        self, exporter: MetricsExporterAdapter, tmp_output_dir: Path, sample_state: PipelineState
    ) -> None:
        """JSON file can be named with thread_id and timestamp pattern."""
        thread_id = sample_state["thread_id"]
        output_path = str(tmp_output_dir / f"metrics-{thread_id}-20260317.json")
        result = exporter.export_json(sample_state, output_path)

        assert result.endswith(".json")
        assert thread_id in result

    def test_csv_file_naming(
        self,
        exporter: MetricsExporterAdapter,
        tmp_output_dir: Path,
        state_with_vulns: PipelineState,
    ) -> None:
        """CSV file can be named with thread_id and timestamp pattern."""
        thread_id = state_with_vulns["thread_id"]
        output_path = str(tmp_output_dir / f"metrics-{thread_id}-20260317.csv")
        result = exporter.export_csv(state_with_vulns, output_path)

        assert result.endswith(".csv")
        assert thread_id in result


# === Strip SecretStr Tests ===


class TestStripSecretValues:
    """Tests for the _strip_secret_values helper."""

    def test_strips_secret_str(self) -> None:
        """SecretStr values are replaced with **REDACTED**."""
        data: dict[str, Any] = {"key": SecretStr("secret"), "plain": "visible"}
        result = _strip_secret_values(data)
        assert result["key"] == "**REDACTED**"
        assert result["plain"] == "visible"

    def test_strips_nested_secrets(self) -> None:
        """SecretStr values in nested dicts/lists are stripped."""
        data: dict[str, Any] = {
            "outer": {
                "inner_secret": SecretStr("hidden"),
                "inner_plain": 42,
            },
            "list_with_secret": [SecretStr("also-hidden"), "visible"],
        }
        result = _strip_secret_values(data)
        assert result["outer"]["inner_secret"] == "**REDACTED**"
        assert result["outer"]["inner_plain"] == 42
        assert result["list_with_secret"][0] == "**REDACTED**"
        assert result["list_with_secret"][1] == "visible"

    def test_preserves_non_secret_values(self) -> None:
        """Non-SecretStr values pass through unchanged."""
        data: dict[str, Any] = {"num": 123, "text": "hello", "flag": True}
        result = _strip_secret_values(data)
        assert result == data

    def test_handles_tuple(self) -> None:
        """Tuples with SecretStr are handled."""
        data = (SecretStr("s1"), "plain")
        result = _strip_secret_values(data)
        assert result == ("**REDACTED**", "plain")


# === Serialize Default Tests ===


class TestSerializeDefault:
    """Tests for the _serialize_default JSON fallback."""

    def test_datetime_serialized_to_iso(self) -> None:
        from datetime import UTC, datetime

        from siopv.adapters.output.metrics_exporter_adapter import _serialize_default

        dt = datetime(2026, 3, 17, 10, 0, 0, tzinfo=UTC)
        result = _serialize_default(dt)
        assert result == "2026-03-17T10:00:00+00:00"

    def test_enum_like_value(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _serialize_default

        obj = type("FakeEnum", (), {"value": "CRITICAL"})()
        result = _serialize_default(obj)
        assert result == "CRITICAL"

    def test_fallback_to_str(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _serialize_default

        result = _serialize_default(42)
        assert result == "42"


# === Default Output Dir Tests ===


class TestDefaultOutputDir:
    """Tests for default output dir when no env var and no explicit dir."""

    def test_default_output_dir_no_env_no_explicit(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            # Remove SIOPV_OUTPUT_DIR if present
            import os

            os.environ.pop("SIOPV_OUTPUT_DIR", None)
            exporter = MetricsExporterAdapter()
            assert exporter._output_dir == Path("./output")


# === Build State Dict Tests ===


class TestBuildStateDict:
    """Tests for _build_state_dict with pydantic model_dump branches."""

    def test_top_level_model_dump(self, tmp_path: Path) -> None:
        """State values with model_dump are serialized via model_dump."""
        from unittest.mock import MagicMock

        exporter = MetricsExporterAdapter(output_dir=tmp_path)
        mock_model = MagicMock()
        mock_model.model_dump.return_value = {"field": "value"}

        state: dict[str, Any] = {
            "thread_id": "test",
            "pydantic_obj": mock_model,
        }
        result = exporter._build_state_dict(state)  # type: ignore[arg-type]
        assert result["pydantic_obj"] == {"field": "value"}
        mock_model.model_dump.assert_called_once_with(mode="json")

    def test_nested_dict_model_dump(self, tmp_path: Path) -> None:
        """Dict values containing pydantic models use model_dump."""
        from unittest.mock import MagicMock

        exporter = MetricsExporterAdapter(output_dir=tmp_path)
        inner_model = MagicMock()
        inner_model.model_dump.return_value = {"nested": True}

        state: dict[str, Any] = {
            "thread_id": "test",
            "enrichments": {"CVE-1": inner_model, "plain": "value"},
        }
        result = exporter._build_state_dict(state)  # type: ignore[arg-type]
        assert result["enrichments"]["CVE-1"] == {"nested": True}
        assert result["enrichments"]["plain"] == "value"

    def test_list_model_dump(self, tmp_path: Path) -> None:
        """List values containing pydantic models use model_dump."""
        from unittest.mock import MagicMock

        exporter = MetricsExporterAdapter(output_dir=tmp_path)
        item_model = MagicMock()
        item_model.model_dump.return_value = {"item": 1}

        state: dict[str, Any] = {
            "thread_id": "test",
            "vulnerabilities": [item_model, "plain_item"],
        }
        result = exporter._build_state_dict(state)  # type: ignore[arg-type]
        assert result["vulnerabilities"][0] == {"item": 1}
        assert result["vulnerabilities"][1] == "plain_item"


# === Error Path Tests ===


class TestExportErrorPaths:
    """Tests for export error paths that raise OutputError."""

    def test_json_export_raises_output_error(self, tmp_path: Path) -> None:
        from siopv.domain.exceptions import OutputError

        exporter = MetricsExporterAdapter(output_dir=tmp_path)
        state = create_initial_state(thread_id="error-test")

        # Use a path that will fail (write to a directory path)
        with (
            patch.object(
                exporter,
                "_build_state_dict",
                side_effect=RuntimeError("serialization boom"),
            ),
            pytest.raises(OutputError, match="Failed to export JSON"),
        ):
            exporter.export_json(state, str(tmp_path / "test.json"))

    def test_csv_export_raises_output_error(self, tmp_path: Path) -> None:
        from siopv.domain.exceptions import OutputError

        exporter = MetricsExporterAdapter(output_dir=tmp_path)
        state = create_initial_state(thread_id="error-test")
        # Add vulns that will cause extraction to fail
        state["vulnerabilities"] = [object()]  # Not a dict or model

        with (
            patch(
                "siopv.adapters.output.metrics_exporter_adapter._extract_cve_id",
                side_effect=RuntimeError("extract boom"),
            ),
            pytest.raises(OutputError, match="Failed to export CSV"),
        ):
            exporter.export_csv(state, str(tmp_path / "test.csv"))


# === Helper Function Tests ===


class TestExtractCveId:
    """Tests for _extract_cve_id helper."""

    def test_obj_with_cve_id_value(self) -> None:
        from unittest.mock import MagicMock

        from siopv.adapters.output.metrics_exporter_adapter import _extract_cve_id

        obj = MagicMock()
        obj.cve_id.value = "CVE-2024-9999"
        assert _extract_cve_id(obj) == "CVE-2024-9999"

    def test_obj_with_cve_id_no_value(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_cve_id

        obj = type("Vuln", (), {"cve_id": "CVE-2024-PLAIN"})()
        assert _extract_cve_id(obj) == "CVE-2024-PLAIN"

    def test_dict_with_string_cve_id(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_cve_id

        assert _extract_cve_id({"cve_id": "CVE-2024-1111"}) == "CVE-2024-1111"

    def test_dict_with_dict_cve_id(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_cve_id

        assert _extract_cve_id({"cve_id": {"value": "CVE-2024-2222"}}) == "CVE-2024-2222"

    def test_unknown_type_returns_empty(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_cve_id

        assert _extract_cve_id(42) == ""


class TestExtractAttr:
    """Tests for _extract_attr helper."""

    def test_obj_with_attr(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_attr

        obj = type("Pkg", (), {"package_name": "openssl"})()
        assert _extract_attr(obj, "package_name", "") == "openssl"

    def test_dict_with_attr(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_attr

        assert _extract_attr({"severity": "HIGH"}, "severity", "UNKNOWN") == "HIGH"

    def test_fallback_default(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_attr

        assert _extract_attr(42, "missing", "DEFAULT") == "DEFAULT"


class TestExtractVersion:
    """Tests for _extract_version helper."""

    def test_obj_with_version_value(self) -> None:
        from unittest.mock import MagicMock

        from siopv.adapters.output.metrics_exporter_adapter import _extract_version

        obj = MagicMock()
        obj.installed_version.value = "1.2.3"
        assert _extract_version(obj) == "1.2.3"

    def test_obj_with_version_no_value(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_version

        obj = type("Vuln", (), {"installed_version": "1.0.0"})()
        assert _extract_version(obj) == "1.0.0"

    def test_dict_with_string_version(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_version

        assert _extract_version({"installed_version": "2.0.0"}) == "2.0.0"

    def test_dict_with_dict_version(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_version

        assert _extract_version({"installed_version": {"value": "3.0.0"}}) == "3.0.0"

    def test_unknown_type_returns_empty(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_version

        assert _extract_version(42) == ""


class TestResolveNested:
    """Tests for _resolve_nested helper."""

    def test_obj_with_attr(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _resolve_nested

        obj = type("Obj", (), {"score": 9.5})()
        assert _resolve_nested(obj, "score") == 9.5

    def test_dict_with_key(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _resolve_nested

        assert _resolve_nested({"score": 7.0}, "score") == 7.0

    def test_returns_none_for_unknown(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _resolve_nested

        assert _resolve_nested(42, "score") is None


class TestUnwrapValue:
    """Tests for _unwrap_value helper."""

    def test_none_returns_empty(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _unwrap_value

        assert _unwrap_value(None) == ""

    def test_obj_with_value_attr(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _unwrap_value

        obj = type("Val", (), {"value": "8.5"})()
        assert _unwrap_value(obj) == "8.5"

    def test_dict_with_value_key(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _unwrap_value

        assert _unwrap_value({"value": "7.0"}) == "7.0"

    def test_plain_value_str_fallback(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _unwrap_value

        assert _unwrap_value(3.14) == "3.14"

    def test_custom_attr(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _unwrap_value

        obj = type("Epss", (), {"score": 0.45})()
        assert _unwrap_value(obj, "score") == "0.45"


class TestExtractCvss:
    """Tests for _extract_cvss helper."""

    def test_returns_value_when_present(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_cvss

        vuln = type("V", (), {"cvss_v3_score": type("S", (), {"value": "8.1"})()})()
        assert _extract_cvss(vuln) == "8.1"

    def test_returns_empty_when_none(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_cvss

        assert _extract_cvss({"cvss_v3_score": None}) == ""

    def test_returns_empty_when_missing(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_cvss

        assert _extract_cvss({}) == ""


class TestExtractEpss:
    """Tests for _extract_epss helper."""

    def test_returns_empty_when_none(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_epss

        assert _extract_epss(None) == ""

    def test_returns_value_when_present(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_epss

        enrichment = type(
            "E",
            (),
            {"epss_score": type("S", (), {"score": "0.45"})()},
        )()
        assert _extract_epss(enrichment) == "0.45"

    def test_returns_empty_when_epss_none(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_epss

        enrichment = {"epss_score": None}
        assert _extract_epss(enrichment) == ""


class TestExtractFromRiskScore:
    """Tests for _extract_from_risk_score helper."""

    def test_returns_empty_when_none(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_from_risk_score

        assert _extract_from_risk_score(None, "risk_probability") == ""

    def test_returns_value_when_present(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_from_risk_score

        rs = type("RS", (), {"risk_probability": "0.85"})()
        classification = type("C", (), {"risk_score": rs})()
        assert _extract_from_risk_score(classification, "risk_probability") == "0.85"

    def test_returns_empty_when_risk_score_none(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _extract_from_risk_score

        classification = {"risk_score": None}
        assert _extract_from_risk_score(classification, "risk_probability") == ""


class TestHasFix:
    """Tests for _has_fix helper."""

    def test_obj_with_fixed_version(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _has_fix

        obj = type("V", (), {"fixed_version": "1.2.3"})()
        assert _has_fix(obj) is True

    def test_obj_with_none_fixed_version(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _has_fix

        obj = type("V", (), {"fixed_version": None})()
        assert _has_fix(obj) is False

    def test_dict_with_fixed_version(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _has_fix

        assert _has_fix({"fixed_version": "1.0.0"}) is True

    def test_dict_with_none_fixed_version(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _has_fix

        assert _has_fix({"fixed_version": None}) is False

    def test_unknown_type_returns_false(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import _has_fix

        assert _has_fix(42) is False
