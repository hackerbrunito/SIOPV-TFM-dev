"""Metrics exporter adapter for CSV and JSON output.

Implements MetricsExporterPort for Phase 8 pipeline result export.
Writes pipeline state to structured JSON and flat CSV files with
atomic write semantics (write to .tmp then os.replace).
"""

from __future__ import annotations

import csv
import io
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from siopv.application.ports.metrics_exporter import MetricsExporterPort
from siopv.domain.exceptions import OutputError

if TYPE_CHECKING:
    from siopv.application.orchestration.state import PipelineState

logger = structlog.get_logger(__name__)

# CSV columns spec — one row per vulnerability
CSV_COLUMNS: list[str] = [
    "run_id",
    "timestamp",
    "cve_id",
    "package",
    "version",
    "severity",
    "cvss_score",
    "epss_score",
    "risk_score",
    "confidence",
    "priority",
    "fix_available",
    "human_review_required",
    "human_decision",
    "sla_deadline",
    "dlp_applied",
]


def _strip_secret_values(obj: Any) -> Any:
    """Recursively strip SecretStr values from a nested structure.

    Replaces any pydantic SecretStr (or object with get_secret_value)
    with the string "**REDACTED**" to prevent credential leakage.
    """
    if hasattr(obj, "get_secret_value"):
        return "**REDACTED**"
    if isinstance(obj, dict):
        return {k: _strip_secret_values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_secret_values(item) for item in obj]
    if isinstance(obj, tuple):
        return tuple(_strip_secret_values(item) for item in obj)
    return obj


def _serialize_default(obj: Any) -> str:
    """JSON serialization fallback for datetime, enums, and other non-serializable types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "value"):
        return str(obj.value)
    return str(obj)


def _now_iso() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.now(UTC).isoformat()


class MetricsExporterAdapter(MetricsExporterPort):
    """Adapter that exports pipeline metrics to JSON and CSV files.

    Features:
    - Atomic writes via .tmp + os.replace
    - SecretStr stripping from JSON output
    - Flat CSV with one row per vulnerability
    - Auto-creates output directory if missing
    """

    def __init__(self, output_dir: str | Path) -> None:
        """Initialize metrics exporter.

        Args:
            output_dir: Directory for output files. Injected from settings.output_dir via DI.
        """
        self._output_dir = Path(output_dir)

        logger.info("metrics_exporter_initialized", output_dir=str(self._output_dir))

    def _ensure_output_dir(self) -> None:
        """Create output directory if it does not exist."""
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _build_state_dict(self, state: PipelineState) -> dict[str, Any]:
        """Build a serializable dict from PipelineState, stripping secrets.

        Args:
            state: Pipeline state (TypedDict)

        Returns:
            Sanitized dictionary safe for JSON serialization
        """
        raw: dict[str, Any] = dict(state)

        # Serialize nested pydantic models via model_dump where available
        serialized: dict[str, Any] = {}
        for key, value in raw.items():
            if hasattr(value, "model_dump"):
                serialized[key] = value.model_dump(mode="json")
            elif isinstance(value, dict):
                inner: dict[str, Any] = {}
                for k, v in value.items():
                    if hasattr(v, "model_dump"):
                        inner[k] = v.model_dump(mode="json")
                    else:
                        inner[k] = v
                serialized[key] = inner
            elif isinstance(value, list):
                items: list[Any] = []
                for item in value:
                    if hasattr(item, "model_dump"):
                        items.append(item.model_dump(mode="json"))
                    else:
                        items.append(item)
                serialized[key] = items
            else:
                serialized[key] = value

        result: dict[str, Any] = _strip_secret_values(serialized)
        return result

    def export_json(self, state: PipelineState, output_path: str) -> str:
        """Export pipeline results as a JSON file.

        Args:
            state: Complete pipeline state with all phase results
            output_path: Absolute path where the JSON should be written

        Returns:
            Absolute path to the generated JSON file

        Raises:
            OutputError: On serialization or file system errors
        """
        try:
            self._ensure_output_dir()
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)

            data = self._build_state_dict(state)
            json_content = json.dumps(data, indent=2, default=_serialize_default)

            # Atomic write: write to .tmp then os.replace
            tmp_path = target.with_suffix(target.suffix + ".tmp")
            tmp_path.write_text(json_content, encoding="utf-8")
            os.replace(str(tmp_path), str(target))

            logger.info("json_export_complete", path=str(target))
            return str(target)

        except Exception as e:
            msg = f"Failed to export JSON: {e}"
            logger.exception("json_export_failed", error=str(e))
            raise OutputError(msg) from e

    def export_csv(self, state: PipelineState, output_path: str) -> str:
        """Export pipeline results as a CSV file.

        One row per vulnerability with columns matching the spec.

        Args:
            state: Complete pipeline state with all phase results
            output_path: Absolute path where the CSV should be written

        Returns:
            Absolute path to the generated CSV file

        Raises:
            OutputError: On serialization or file system errors
        """
        try:
            self._ensure_output_dir()
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)

            vulnerabilities: list[Any] = state.get("vulnerabilities", [])
            enrichments: dict[str, Any] = state.get("enrichments", {})
            classifications: dict[str, Any] = state.get("classifications", {})
            thread_id: str = state.get("thread_id", "")
            human_decision: str | None = state.get("human_decision")
            review_deadline: str | None = state.get("review_deadline")
            escalation_required: bool = state.get("escalation_required", False)
            dlp_result: dict[str, object] | None = state.get("dlp_result")

            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS)
            writer.writeheader()

            for vuln in vulnerabilities:
                cve_id = _extract_cve_id(vuln)
                enrichment = enrichments.get(cve_id)
                classification = classifications.get(cve_id)

                row: dict[str, Any] = {
                    "run_id": thread_id,
                    "timestamp": _now_iso(),
                    "cve_id": cve_id,
                    "package": _extract_attr(vuln, "package_name", ""),
                    "version": _extract_version(vuln),
                    "severity": _extract_attr(vuln, "severity", "UNKNOWN"),
                    "cvss_score": _extract_cvss(vuln),
                    "epss_score": _extract_epss(enrichment),
                    "risk_score": _extract_risk_score(classification),
                    "confidence": _extract_confidence(classification),
                    "priority": _extract_risk_label(classification),
                    "fix_available": _has_fix(vuln),
                    "human_review_required": escalation_required,
                    "human_decision": human_decision or "",
                    "sla_deadline": review_deadline or "",
                    "dlp_applied": dlp_result is not None,
                }
                writer.writerow(row)

            csv_content = buf.getvalue()

            # Atomic write: write to .tmp then os.replace
            tmp_path = target.with_suffix(target.suffix + ".tmp")
            tmp_path.write_text(csv_content, encoding="utf-8")
            os.replace(str(tmp_path), str(target))

            logger.info("csv_export_complete", path=str(target), rows=len(vulnerabilities))
            return str(target)

        except Exception as e:
            msg = f"Failed to export CSV: {e}"
            logger.exception("csv_export_failed", error=str(e))
            raise OutputError(msg) from e


# === Helper functions for extracting data from state objects ===


def _extract_cve_id(vuln: Any) -> str:
    """Extract CVE ID string from a VulnerabilityRecord or dict."""
    if hasattr(vuln, "cve_id"):
        cve = vuln.cve_id
        if hasattr(cve, "value"):
            return str(cve.value)
        return str(cve)
    if isinstance(vuln, dict):
        cve = vuln.get("cve_id", "")
        if isinstance(cve, dict):
            return str(cve.get("value", ""))
        return str(cve)
    return ""


def _extract_attr(obj: Any, attr: str, default: str) -> str:
    """Extract an attribute from a pydantic model or dict."""
    if hasattr(obj, attr):
        return str(getattr(obj, attr))
    if isinstance(obj, dict):
        return str(obj.get(attr, default))
    return default


def _extract_version(vuln: Any) -> str:
    """Extract installed version string."""
    if hasattr(vuln, "installed_version"):
        ver = vuln.installed_version
        if hasattr(ver, "value"):
            return str(ver.value)
        return str(ver)
    if isinstance(vuln, dict):
        ver = vuln.get("installed_version", "")
        if isinstance(ver, dict):
            return str(ver.get("value", ""))
        return str(ver)
    return ""


def _resolve_nested(obj: Any, attr: str) -> Any | None:
    """Resolve a value from a pydantic model or dict, returning None if missing."""
    if hasattr(obj, attr):
        return getattr(obj, attr)
    if isinstance(obj, dict):
        return obj.get(attr)
    return None


def _unwrap_value(obj: Any, attr: str = "value") -> str:
    """Unwrap a value object (pydantic model with .value or dict with 'value' key)."""
    if obj is None:
        return ""
    if hasattr(obj, attr):
        return str(getattr(obj, attr))
    if isinstance(obj, dict):
        return str(obj.get(attr, ""))
    return str(obj)


def _extract_cvss(vuln: Any) -> str:
    """Extract CVSS score as string."""
    score = _resolve_nested(vuln, "cvss_v3_score")
    if score is None:
        return ""
    return _unwrap_value(score)


def _extract_epss(enrichment: Any) -> str:
    """Extract EPSS score from enrichment data."""
    if enrichment is None:
        return ""
    epss = _resolve_nested(enrichment, "epss_score")
    if epss is None:
        return ""
    return _unwrap_value(epss, "score")


def _extract_from_risk_score(classification: Any, attr: str) -> str:
    """Extract a field from the nested risk_score inside a classification result."""
    if classification is None:
        return ""
    rs = _resolve_nested(classification, "risk_score")
    if rs is None:
        return ""
    return _unwrap_value(rs, attr)


def _extract_risk_score(classification: Any) -> str:
    """Extract risk probability from classification result."""
    return _extract_from_risk_score(classification, "risk_probability")


def _extract_confidence(classification: Any) -> str:
    """Extract confidence from classification result."""
    return _extract_from_risk_score(classification, "confidence")


def _extract_risk_label(classification: Any) -> str:
    """Extract risk label (priority) from classification result."""
    return _extract_from_risk_score(classification, "risk_label")


def _has_fix(vuln: Any) -> bool:
    """Check if a fix version is available."""
    if hasattr(vuln, "fixed_version"):
        return vuln.fixed_version is not None
    if isinstance(vuln, dict):
        return vuln.get("fixed_version") is not None
    return False


__all__ = [
    "CSV_COLUMNS",
    "MetricsExporterAdapter",
]
