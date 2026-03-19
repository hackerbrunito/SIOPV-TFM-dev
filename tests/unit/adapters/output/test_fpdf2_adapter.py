"""Unit tests for Fpdf2Adapter PDF report generator.

Tests each section renders without error, file naming, CoT flag,
and output directory creation.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from siopv.adapters.output.fpdf2_adapter import Fpdf2Adapter, _render_lime_chart, _safe_str

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_vuln(cve_id: str = "CVE-2024-1234", severity: str = "HIGH") -> MagicMock:
    """Create a mock VulnerabilityRecord."""
    vuln = MagicMock()
    vuln.cve_id.value = cve_id
    vuln.package_name = "openssl"
    vuln.severity = severity
    vuln.description = "A test vulnerability description for PDF rendering."
    vuln.installed_version.value = "1.1.1"
    vuln.fixed_version.value = "1.1.2"
    vuln.cvss_v3_score.value = 8.5
    return vuln


def _make_enrichment(cve_id: str = "CVE-2024-1234") -> MagicMock:
    """Create a mock EnrichmentData."""
    enrichment = MagicMock()
    enrichment.cve_id = cve_id
    enrichment.nvd.cvss_v3_score = 8.5
    enrichment.nvd.cvss_v3_vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    enrichment.nvd.description = "NVD description for the vulnerability."
    enrichment.epss.score = 0.45
    enrichment.github_advisory = None
    enrichment.osint_results = []
    return enrichment


def _make_classification(
    probability: float = 0.85,
    label: str = "CRITICAL",
) -> MagicMock:
    """Create a mock ClassificationResult with RiskScore and LIME."""
    classification = MagicMock()
    rs = MagicMock()
    rs.risk_probability = probability
    rs.risk_label = label
    rs.confidence = 0.7
    rs.lime_explanation.feature_contributions = [
        ("cvss_score > 7.0", 0.35),
        ("epss_score > 0.1", 0.20),
        ("has_exploit_ref = True", 0.15),
        ("days_since_pub <= 30", -0.10),
        ("attack_vector = N", 0.08),
    ]
    rs.shap_values.top_contributors = [
        ("cvss_score", 0.4),
        ("epss_score", 0.25),
        ("has_exploit_ref", 0.15),
    ]
    classification.risk_score = rs
    return classification


def _make_state(
    num_vulns: int = 3,
    with_escalation: bool = False,
    with_dlp: bool = False,
    with_errors: bool = False,
) -> dict:
    """Build a mock PipelineState dict."""
    vulns = [
        _make_vuln("CVE-2024-0001", "CRITICAL"),
        _make_vuln("CVE-2024-0002", "HIGH"),
        _make_vuln("CVE-2024-0003", "MEDIUM"),
    ][:num_vulns]

    enrichments = {}
    classifications = {}
    for v in vulns:
        cve = v.cve_id.value
        enrichments[cve] = _make_enrichment(cve)
        classifications[cve] = _make_classification()

    state: dict = {
        "thread_id": "test-thread-001",
        "current_node": "output",
        "vulnerabilities": vulns,
        "enrichments": enrichments,
        "classifications": classifications,
        "escalated_cves": [],
        "llm_confidence": {},
        "processed_count": num_vulns,
        "errors": [],
        "dlp_result": None,
        "escalation_required": False,
        "human_decision": None,
        "escalation_timestamp": None,
        "escalation_level": 0,
        "review_deadline": None,
    }

    if with_escalation:
        state["escalated_cves"] = ["CVE-2024-0001"]
        state["escalation_timestamp"] = "2026-03-17T10:00:00Z"
        state["escalation_level"] = 2
        state["human_decision"] = "approve"
        state["review_deadline"] = "2026-03-17T18:00:00Z"

    if with_dlp:
        state["dlp_result"] = {
            "sanitized": True,
            "detections": [
                {"entity_type": "EMAIL_ADDRESS"},
                {"entity_type": "EMAIL_ADDRESS"},
                {"entity_type": "PHONE_NUMBER"},
            ],
            "total_fields_sanitized": 5,
            "anonymization_method": "Presidio + Haiku dual-layer",
        }

    if with_errors:
        state["errors"] = [
            "Step 1: Analyzed CVE-2024-0001 context from NVD and EPSS sources.",
            "Step 2: Applied XGBoost classification with LIME explanation.",
        ]

    return state


_MODEL_PATH = Path("./models/xgboost_risk_model.json")


@pytest.fixture
def adapter() -> Fpdf2Adapter:
    return Fpdf2Adapter(
        pdf_include_cot=False,
        model_path=_MODEL_PATH,
    )


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------


class TestSafeStr:
    def test_none_returns_na(self) -> None:
        assert _safe_str(None) == "N/A"

    def test_string_passthrough(self) -> None:
        assert _safe_str("hello") == "hello"

    def test_number_converted(self) -> None:
        assert _safe_str(42) == "42"

    def test_float_converted(self) -> None:
        assert _safe_str(3.14) == "3.14"


class TestRenderLimeChart:
    def test_returns_png_bytes(self) -> None:
        contributions = [("feat_a", 0.3), ("feat_b", -0.2), ("feat_c", 0.1)]
        result = _render_lime_chart(contributions)
        assert isinstance(result, bytes)
        assert len(result) > 0
        # PNG magic bytes
        assert result[:4] == b"\x89PNG"

    def test_empty_contributions_returns_empty(self) -> None:
        result = _render_lime_chart([])
        assert result == b""

    def test_max_features_limit(self) -> None:
        contributions = [(f"feat_{i}", 0.1 * i) for i in range(10)]
        result = _render_lime_chart(contributions, max_features=3)
        assert isinstance(result, bytes)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Adapter tests
# ---------------------------------------------------------------------------


def _generate_pdf(
    adapter: Fpdf2Adapter,
    tmp_path: Path,
    state: dict,
) -> str:
    """Generate PDF and return the result path."""
    output_path = str(tmp_path / "report.pdf")
    result = adapter.generate(state, output_path)
    assert Path(result).exists()
    return result


class TestFpdf2AdapterGenerate:
    def test_generates_pdf_file(self, adapter: Fpdf2Adapter, tmp_path: Path) -> None:
        state = _make_state()
        output_path = str(tmp_path / "reports" / "report.pdf")

        result = adapter.generate(state, output_path)

        assert Path(result).exists()
        assert result.endswith(".pdf")
        # Verify it's a valid PDF (starts with %PDF)
        with open(result, "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-"

    def test_file_naming_convention(self, adapter: Fpdf2Adapter, tmp_path: Path) -> None:
        state = _make_state()
        output_path = str(tmp_path / "report.pdf")

        result = adapter.generate(state, output_path)

        filename = Path(result).name
        assert filename.startswith("audit-report-test-thread-001-")
        assert filename.endswith(".pdf")

    def test_output_dir_creation(self, adapter: Fpdf2Adapter, tmp_path: Path) -> None:
        nested_dir = tmp_path / "deep" / "nested" / "dir"
        output_path = str(nested_dir / "report.pdf")

        result = adapter.generate(_make_state(), output_path)

        assert nested_dir.exists()
        assert Path(result).exists()

    def test_empty_vulnerabilities(self, adapter: Fpdf2Adapter, tmp_path: Path) -> None:
        state = _make_state(num_vulns=0)
        output_path = str(tmp_path / "report.pdf")

        result = adapter.generate(state, output_path)

        assert Path(result).exists()


class TestSectionExecutiveSummary:
    def test_renders_without_error(self, adapter: Fpdf2Adapter, tmp_path: Path) -> None:
        state = _make_state()
        result = _generate_pdf(adapter, tmp_path, state)
        assert Path(result).stat().st_size > 1000

    def test_renders_with_no_vulns(self, adapter: Fpdf2Adapter, tmp_path: Path) -> None:
        state = _make_state(num_vulns=0)
        result = _generate_pdf(adapter, tmp_path, state)
        assert Path(result).stat().st_size > 500


class TestSectionVulnerabilityIndex:
    def test_renders_table(self, adapter: Fpdf2Adapter, tmp_path: Path) -> None:
        state = _make_state()
        result = _generate_pdf(adapter, tmp_path, state)
        # PDF with 3 vulns should be larger than empty
        assert Path(result).stat().st_size > 2000


class TestSectionDetailCards:
    def test_renders_cards(self, adapter: Fpdf2Adapter, tmp_path: Path) -> None:
        state = _make_state(num_vulns=2)
        result = _generate_pdf(adapter, tmp_path, state)
        assert Path(result).stat().st_size > 2000


class TestSectionHitlLog:
    def test_no_escalations(self, adapter: Fpdf2Adapter, tmp_path: Path) -> None:
        state = _make_state(with_escalation=False)
        result = _generate_pdf(adapter, tmp_path, state)
        assert Path(result).exists()

    def test_with_escalations(self, adapter: Fpdf2Adapter, tmp_path: Path) -> None:
        state = _make_state(with_escalation=True)
        result = _generate_pdf(adapter, tmp_path, state)
        # Escalation data adds content, so PDF should be larger
        no_esc_state = _make_state(with_escalation=False)
        no_esc_path = str(tmp_path / "no_esc")
        Path(no_esc_path).mkdir()
        no_esc_result = _generate_pdf(adapter, Path(no_esc_path), no_esc_state)
        assert Path(result).stat().st_size >= Path(no_esc_result).stat().st_size


class TestSectionMlTransparency:
    def test_renders_ml_section(self, adapter: Fpdf2Adapter, tmp_path: Path) -> None:
        state = _make_state()
        result = _generate_pdf(adapter, tmp_path, state)
        assert Path(result).stat().st_size > 2000


class TestSectionDlpAudit:
    def test_no_dlp(self, adapter: Fpdf2Adapter, tmp_path: Path) -> None:
        state = _make_state(with_dlp=False)
        result = _generate_pdf(adapter, tmp_path, state)
        assert Path(result).exists()

    def test_with_dlp(self, adapter: Fpdf2Adapter, tmp_path: Path) -> None:
        state = _make_state(with_dlp=True)
        result = _generate_pdf(adapter, tmp_path, state)
        assert Path(result).exists()


class TestSectionRemediationTimeline:
    def test_renders_timeline(self, adapter: Fpdf2Adapter, tmp_path: Path) -> None:
        state = _make_state()
        result = _generate_pdf(adapter, tmp_path, state)
        assert Path(result).stat().st_size > 2000


class TestCotFlag:
    def test_cot_disabled_by_default(self, adapter: Fpdf2Adapter, tmp_path: Path) -> None:
        state = _make_state(with_errors=True)
        result = _generate_pdf(adapter, tmp_path, state)
        size_without = Path(result).stat().st_size
        # CoT enabled = more pages
        cot_adapter = Fpdf2Adapter(pdf_include_cot=True, model_path=_MODEL_PATH)
        cot_path = tmp_path / "cot"
        cot_path.mkdir()
        result_with = _generate_pdf(cot_adapter, cot_path, state)
        size_with = Path(result_with).stat().st_size
        assert size_with > size_without

    def test_cot_enabled(self, tmp_path: Path) -> None:
        state = _make_state(with_errors=True)
        cot_adapter = Fpdf2Adapter(pdf_include_cot=True, model_path=_MODEL_PATH)
        result = _generate_pdf(cot_adapter, tmp_path, state)
        assert Path(result).stat().st_size > 2000


class TestFullReport:
    def test_all_features_combined(self, tmp_path: Path) -> None:
        """Generate a full report with all features enabled."""
        state = _make_state(num_vulns=3, with_escalation=True, with_dlp=True, with_errors=True)
        cot_adapter = Fpdf2Adapter(pdf_include_cot=True, model_path=_MODEL_PATH)
        result = _generate_pdf(cot_adapter, tmp_path, state)
        content = Path(result).read_bytes()
        assert content[:5] == b"%PDF-"
        # Full report with 3 vulns + all features should be substantial
        assert len(content) > 5000
