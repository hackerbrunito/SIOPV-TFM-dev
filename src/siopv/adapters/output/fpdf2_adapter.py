"""PDF report generator using fpdf2 for SIOPV Phase 8.

Implements PdfGeneratorPort to render a structured vulnerability audit report
from pipeline state. Sections: executive summary, vulnerability index,
detail cards with LIME charts, HITL log, ML transparency, DLP audit,
remediation timeline, and optional chain-of-thought appendix.
"""

from __future__ import annotations

import io
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import matplotlib.pyplot as plt
import structlog
from fpdf import FPDF
from fpdf.fonts import FontFace

from siopv.application.ports.pdf_generator import PdfGeneratorPort

if TYPE_CHECKING:
    from siopv.application.orchestration.state import PipelineState

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PAGE_WIDTH_MM = 190  # A4 usable width (210 - 10 left - 10 right)
_MARGIN_MM = 10
_HEADER_FONT_SIZE = 16
_SECTION_FONT_SIZE = 13
_BODY_FONT_SIZE = 9
_SMALL_FONT_SIZE = 7
_LINE_HEIGHT_MM = 5
_CARD_PADDING_MM = 3
_CARD_PAGE_BREAK_THRESHOLD_MM = 230  # Force new page if Y exceeds this

# Monochrome palette
_COLOR_BLACK = (0, 0, 0)
_COLOR_DARK_GRAY = (60, 60, 60)
_COLOR_MID_GRAY = (140, 140, 140)
_COLOR_LIGHT_GRAY = (220, 220, 220)
_COLOR_WHITE = (255, 255, 255)

# Severity display order
_SEVERITY_ORDER = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN")

# SLA days by severity
_SLA_DAYS: dict[str, int] = {
    "CRITICAL": 7,
    "HIGH": 14,
    "MEDIUM": 30,
    "LOW": 90,
    "UNKNOWN": 90,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _severity_sort_key(severity: str) -> int:
    """Return sort key for severity (lower = more severe)."""
    order = {s: i for i, s in enumerate(_SEVERITY_ORDER)}
    return order.get(severity.upper(), len(_SEVERITY_ORDER))


def _safe_str(value: object) -> str:
    """Convert any value to a safe string for PDF rendering."""
    if value is None:
        return "N/A"
    return str(value)


def _render_lime_chart(
    feature_contributions: list[tuple[str, float]], max_features: int = 5
) -> bytes:
    """Render a horizontal bar chart of LIME feature contributions as PNG bytes.

    Uses matplotlib with Agg backend to avoid GUI requirements.
    """
    import matplotlib as mpl  # noqa: PLC0415

    mpl.use("Agg")

    contributions = sorted(feature_contributions, key=lambda x: abs(x[1]), reverse=True)[
        :max_features
    ]
    if not contributions:
        return b""

    labels = [c[0][:40] for c in contributions]
    values = [c[1] for c in contributions]

    fig, ax = plt.subplots(figsize=(4, max(1.5, len(contributions) * 0.45)))
    colors = ["#333333" if v >= 0 else "#999999" for v in values]
    ax.barh(labels, values, color=colors, height=0.6)
    ax.set_xlabel("Contribution", fontsize=7)
    ax.set_title("LIME - Top Feature Contributions", fontsize=8)
    ax.tick_params(axis="both", labelsize=7)
    ax.invert_yaxis()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# PDF Builder (internal)
# ---------------------------------------------------------------------------


class _SiopvPdf(FPDF):
    """Custom FPDF subclass with SIOPV header/footer."""

    def __init__(self, run_id: str, app_name: str = "SIOPV") -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self._run_id = run_id
        self._app_name = app_name
        self.set_margins(_MARGIN_MM, _MARGIN_MM, _MARGIN_MM)
        self.set_auto_page_break(auto=True, margin=15)

    def header(self) -> None:
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*_COLOR_MID_GRAY)
        self.cell(
            0, 5, f"{self._app_name} Vulnerability Audit Report", new_x="LMARGIN", new_y="NEXT"
        )
        self.set_draw_color(*_COLOR_LIGHT_GRAY)
        self.line(_MARGIN_MM, self.get_y(), _MARGIN_MM + _PAGE_WIDTH_MM, self.get_y())
        self.ln(3)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*_COLOR_MID_GRAY)
        self.cell(0, 5, f"Run: {self._run_id}  |  Page {self.page_no()}/{{nb}}", align="C")

    # ------ convenience ------ #

    def section_title(self, title: str) -> None:
        """Render a numbered section heading."""
        self.ln(4)
        self.set_font("Helvetica", "B", _SECTION_FONT_SIZE)
        self.set_text_color(*_COLOR_BLACK)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*_COLOR_DARK_GRAY)
        self.line(_MARGIN_MM, self.get_y(), _MARGIN_MM + _PAGE_WIDTH_MM, self.get_y())
        self.ln(3)

    def body_font(self) -> None:
        self.set_font("Helvetica", "", _BODY_FONT_SIZE)
        self.set_text_color(*_COLOR_BLACK)

    def bold_font(self) -> None:
        self.set_font("Helvetica", "B", _BODY_FONT_SIZE)
        self.set_text_color(*_COLOR_BLACK)

    def kv_line(self, key: str, value: str) -> None:
        """Render a key: value line."""
        self.bold_font()
        self.cell(45, _LINE_HEIGHT_MM, f"{key}:", new_x="END")
        self.body_font()
        self.cell(0, _LINE_HEIGHT_MM, value, new_x="LMARGIN", new_y="NEXT")


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class Fpdf2Adapter(PdfGeneratorPort):
    """fpdf2-based PDF audit report generator.

    Reads pipeline state and renders an 8-section vulnerability audit PDF.
    """

    def __init__(
        self,
        *,
        pdf_include_cot: bool = False,
        model_path: Path | None = None,
        app_name: str = "SIOPV",
    ) -> None:
        self._pdf_include_cot = pdf_include_cot
        self._model_path = model_path
        self._app_name = app_name

    def generate(self, state: PipelineState, output_path: str) -> str:
        """Generate the PDF audit report.

        Args:
            state: Complete pipeline state with all phase results.
            output_path: Absolute path where the PDF should be written.

        Returns:
            Absolute path to the generated PDF file.
        """
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        thread_id = state.get("thread_id", "unknown")
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        filename = f"audit-report-{thread_id}-{timestamp}.pdf"
        dest = output_dir / filename

        pdf = _SiopvPdf(run_id=thread_id, app_name=self._app_name)
        pdf.alias_nb_pages()
        pdf.add_page()

        vulnerabilities = state.get("vulnerabilities", [])
        enrichments = state.get("enrichments", {})
        classifications = state.get("classifications", {})
        escalated_cves = state.get("escalated_cves", [])
        dlp_result = state.get("dlp_result")

        self._section_executive_summary(pdf, state, vulnerabilities, escalated_cves)
        self._section_vulnerability_index(pdf, vulnerabilities, enrichments, classifications)
        self._section_detail_cards(pdf, vulnerabilities, enrichments, classifications, dlp_result)
        self._section_hitl_log(pdf, state, escalated_cves)
        self._section_ml_transparency(pdf, classifications)
        self._section_dlp_audit(pdf, dlp_result)
        self._section_remediation_timeline(pdf, vulnerabilities, classifications)
        if self._pdf_include_cot:
            self._section_cot_appendix(pdf, state)

        pdf.output(str(dest))

        logger.info(
            "pdf_report_generated",
            path=str(dest),
            pages=pdf.page_no(),
            vulnerabilities=len(vulnerabilities),
        )
        return str(dest)

    # ------------------------------------------------------------------ #
    # Section 1: Executive Summary
    # ------------------------------------------------------------------ #

    def _section_executive_summary(
        self,
        pdf: _SiopvPdf,
        state: PipelineState,
        vulnerabilities: list[Any],
        escalated_cves: list[str],
    ) -> None:
        pdf.set_font("Helvetica", "B", _HEADER_FONT_SIZE)
        pdf.set_text_color(*_COLOR_BLACK)
        pdf.cell(
            0,
            10,
            f"{self._app_name} Vulnerability Audit Report",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(2)

        pdf.section_title("1. Executive Summary")

        thread_id = state.get("thread_id", "unknown")
        timestamp_now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

        pdf.kv_line("Run ID", thread_id)
        pdf.kv_line("Generated", timestamp_now)
        pdf.kv_line("Pipeline Version", f"{self._app_name} v1.0 - Phase 8")
        pdf.kv_line("Vulnerabilities Processed", str(len(vulnerabilities)))

        # Severity breakdown
        severity_counts: dict[str, int] = dict.fromkeys(_SEVERITY_ORDER, 0)
        for vuln in vulnerabilities:
            sev = getattr(vuln, "severity", "UNKNOWN")
            if isinstance(sev, str):
                sev = sev.upper()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        breakdown = ", ".join(
            f"{s}: {severity_counts[s]}" for s in _SEVERITY_ORDER if severity_counts[s]
        )
        pdf.kv_line("By Severity", breakdown or "None")

        # Auto-resolved vs escalated
        total = len(vulnerabilities) or 1
        escalated_count = len(escalated_cves)
        auto_resolved = total - escalated_count
        pct_auto = (auto_resolved / total) * 100
        pdf.kv_line("Auto-Resolved", f"{auto_resolved} ({pct_auto:.0f}%)")
        pdf.kv_line("Escalated to Human", str(escalated_count))

        # Risk posture
        critical_count = severity_counts.get("CRITICAL", 0)
        high_count = severity_counts.get("HIGH", 0)
        if critical_count > 0:
            posture = "CRITICAL - Immediate remediation required for critical vulnerabilities."
        elif high_count > 0:
            posture = "HIGH - High-severity vulnerabilities require prompt attention."
        elif severity_counts.get("MEDIUM", 0) > 0:
            posture = "MODERATE - Medium-severity issues should be scheduled for remediation."
        else:
            posture = "LOW - No high-severity vulnerabilities detected."

        pdf.ln(2)
        pdf.bold_font()
        pdf.cell(45, _LINE_HEIGHT_MM, "Risk Posture:", new_x="END")
        pdf.body_font()
        pdf.multi_cell(0, _LINE_HEIGHT_MM, posture, new_x="LMARGIN", new_y="NEXT")

    # ------------------------------------------------------------------ #
    # Section 2: Vulnerability Index
    # ------------------------------------------------------------------ #

    def _section_vulnerability_index(
        self,
        pdf: _SiopvPdf,
        vulnerabilities: list[Any],
        enrichments: dict[str, Any],
        classifications: dict[str, Any],
    ) -> None:
        pdf.section_title("2. Vulnerability Index")

        if not vulnerabilities:
            pdf.body_font()
            pdf.cell(
                0, _LINE_HEIGHT_MM, "No vulnerabilities to display.", new_x="LMARGIN", new_y="NEXT"
            )
            return

        rows = self._build_index_rows(vulnerabilities, enrichments, classifications)
        # Sort: priority desc (severity), then CVSS desc
        rows.sort(key=lambda r: (_severity_sort_key(r[4]), -(r[2] or 0)))

        headings_style = FontFace(emphasis="BOLD", color=_COLOR_WHITE, fill_color=_COLOR_DARK_GRAY)
        col_widths = (25, 25, 12, 12, 15, 18, 15, 15)

        pdf.set_font("Helvetica", "", _SMALL_FONT_SIZE)

        with pdf.table(
            headings_style=headings_style,
            col_widths=col_widths,
            text_align="CENTER",
            borders_layout="MINIMAL",
            cell_fill_color=_COLOR_LIGHT_GRAY,
            cell_fill_mode="ROWS",
            padding=1,
        ) as table:
            header = table.row()
            for h in (
                "CVE ID",
                "Package",
                "CVSS",
                "EPSS",
                "ML Score",
                "Priority",
                "Status",
                "Due Date",
            ):
                header.cell(h)

            for row_data in rows:
                row = table.row()
                for val in row_data:
                    row.cell(_safe_str(val))

    def _build_index_rows(
        self,
        vulnerabilities: list[Any],
        enrichments: dict[str, Any],
        classifications: dict[str, Any],
    ) -> list[tuple[str, str, float | None, float | None, str, str, str, str]]:
        """Build index table rows from state data."""
        rows: list[tuple[str, str, float | None, float | None, str, str, str, str]] = []
        for vuln in vulnerabilities:
            cve_id = vuln.cve_id.value if hasattr(vuln.cve_id, "value") else str(vuln.cve_id)
            package = vuln.package_name

            enrichment = enrichments.get(cve_id)
            cvss: float | None = None
            epss: float | None = None
            if enrichment is not None:
                if hasattr(enrichment, "nvd") and enrichment.nvd:
                    cvss = enrichment.nvd.cvss_v3_score
                if hasattr(enrichment, "epss") and enrichment.epss:
                    epss = enrichment.epss.score

            classification = classifications.get(cve_id)
            ml_score: str = "N/A"
            if (
                classification is not None
                and hasattr(classification, "risk_score")
                and classification.risk_score
            ):
                ml_score = f"{classification.risk_score.risk_probability:.2f}"

            severity = vuln.severity if isinstance(vuln.severity, str) else str(vuln.severity)
            status = "Classified" if classification else "Pending"

            due_date = self._compute_due_date(severity)

            rows.append((cve_id, package, cvss, epss, severity, ml_score, status, due_date))
        return rows

    @staticmethod
    def _compute_due_date(severity: str) -> str:
        """Compute SLA due date from now based on severity."""

        days = _SLA_DAYS.get(severity.upper(), 90)
        due = datetime.now(UTC) + timedelta(days=days)
        return due.strftime("%Y-%m-%d")

    # ------------------------------------------------------------------ #
    # Section 3: Per-Vulnerability Detail Cards
    # ------------------------------------------------------------------ #

    def _section_detail_cards(
        self,
        pdf: _SiopvPdf,
        vulnerabilities: list[Any],
        enrichments: dict[str, Any],
        classifications: dict[str, Any],
        dlp_result: dict[str, object] | None,
    ) -> None:
        pdf.section_title("3. Vulnerability Detail Cards")

        if not vulnerabilities:
            pdf.body_font()
            pdf.cell(
                0, _LINE_HEIGHT_MM, "No vulnerabilities to display.", new_x="LMARGIN", new_y="NEXT"
            )
            return

        for vuln in vulnerabilities:
            cve_id = vuln.cve_id.value if hasattr(vuln.cve_id, "value") else str(vuln.cve_id)
            self._render_card(pdf, vuln, cve_id, enrichments, classifications, dlp_result)

    def _render_card(
        self,
        pdf: _SiopvPdf,
        vuln: Any,
        cve_id: str,
        enrichments: dict[str, Any],
        classifications: dict[str, Any],
        dlp_result: dict[str, object] | None,
    ) -> None:
        if pdf.get_y() > _CARD_PAGE_BREAK_THRESHOLD_MM:
            pdf.add_page()

        # Card header
        y_start = pdf.get_y()
        pdf.set_draw_color(*_COLOR_MID_GRAY)
        pdf.set_fill_color(*_COLOR_LIGHT_GRAY)
        pdf.rect(_MARGIN_MM, y_start, _PAGE_WIDTH_MM, 4, style="F")
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*_COLOR_BLACK)
        pdf.set_xy(_MARGIN_MM + _CARD_PADDING_MM, y_start + 0.5)
        pdf.cell(0, 4, cve_id, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        enrichment = enrichments.get(cve_id)
        classification = classifications.get(cve_id)

        self._render_card_description(pdf, vuln, enrichment)
        lime_explanation = self._render_card_metrics(pdf, enrichment, classification)
        self._render_card_sources(pdf, enrichment)
        self._render_card_dlp(pdf, dlp_result)
        self._render_card_lime_chart(pdf, lime_explanation)

        # Bottom border
        pdf.set_draw_color(*_COLOR_MID_GRAY)
        pdf.line(_MARGIN_MM, pdf.get_y(), _MARGIN_MM + _PAGE_WIDTH_MM, pdf.get_y())
        pdf.ln(4)

    @staticmethod
    def _render_card_description(pdf: _SiopvPdf, vuln: Any, enrichment: Any) -> None:
        description = vuln.description or ""
        if (
            enrichment
            and hasattr(enrichment, "nvd")
            and enrichment.nvd
            and enrichment.nvd.description
        ):
            description = enrichment.nvd.description
        pdf.body_font()
        if description:
            pdf.multi_cell(0, _LINE_HEIGHT_MM, description[:500], new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

    @staticmethod
    def _render_card_metrics(pdf: _SiopvPdf, enrichment: Any, classification: Any) -> Any:
        """Render key metrics and return lime_explanation for chart rendering."""
        cvss_str = "N/A"
        epss_str = "N/A"
        cvss_vector_str = "N/A"
        if enrichment:
            if hasattr(enrichment, "nvd") and enrichment.nvd:
                if enrichment.nvd.cvss_v3_score is not None:
                    cvss_str = f"{enrichment.nvd.cvss_v3_score:.1f}"
                if enrichment.nvd.cvss_v3_vector:
                    cvss_vector_str = str(enrichment.nvd.cvss_v3_vector)
            if hasattr(enrichment, "epss") and enrichment.epss:
                epss_str = f"{enrichment.epss.score:.4f}"

        ml_score_str = "N/A"
        confidence_str = "N/A"
        lime_explanation = None
        if classification and hasattr(classification, "risk_score") and classification.risk_score:
            rs = classification.risk_score
            ml_score_str = f"{rs.risk_probability:.3f} ({rs.risk_label})"
            confidence_str = f"{rs.confidence:.2f}"
            lime_explanation = rs.lime_explanation

        pdf.kv_line("CVSS v3", cvss_str)
        pdf.kv_line("CVSS Vector", cvss_vector_str)
        pdf.kv_line("EPSS", epss_str)
        pdf.kv_line("ML Risk Score", ml_score_str)
        pdf.kv_line("Confidence", confidence_str)
        return lime_explanation

    @staticmethod
    def _render_card_sources(pdf: _SiopvPdf, enrichment: Any) -> None:
        sources: list[str] = []
        if enrichment:
            if hasattr(enrichment, "nvd") and enrichment.nvd:
                sources.append("NVD")
            if hasattr(enrichment, "epss") and enrichment.epss:
                sources.append("EPSS")
            if hasattr(enrichment, "github_advisory") and enrichment.github_advisory:
                sources.append("GitHub Advisory")
            if hasattr(enrichment, "osint_results") and enrichment.osint_results:
                sources.append("OSINT")
        pdf.kv_line("Data Sources", ", ".join(sources) if sources else "None")

    @staticmethod
    def _render_card_dlp(pdf: _SiopvPdf, dlp_result: dict[str, object] | None) -> None:
        dlp_applied = "No"
        if dlp_result and isinstance(dlp_result, dict):
            dlp_applied = "Yes" if dlp_result.get("sanitized", False) else "No"
        pdf.kv_line("DLP Applied", dlp_applied)

    @staticmethod
    def _render_card_lime_chart(pdf: _SiopvPdf, lime_explanation: Any) -> None:
        if not lime_explanation or not hasattr(lime_explanation, "feature_contributions"):
            return
        contributions = lime_explanation.feature_contributions
        if not contributions:
            return
        chart_bytes = _render_lime_chart(contributions)
        if not chart_bytes:
            return
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(chart_bytes)
            tmp_path = tmp.name
        pdf.ln(1)
        pdf.image(tmp_path, x=_MARGIN_MM + 2, w=80)
        Path(tmp_path).unlink(missing_ok=True)
        pdf.ln(1)

    # ------------------------------------------------------------------ #
    # Section 4: HITL Escalation Log
    # ------------------------------------------------------------------ #

    def _section_hitl_log(
        self,
        pdf: _SiopvPdf,
        state: PipelineState,
        escalated_cves: list[str],
    ) -> None:
        pdf.section_title("4. HITL Escalation Log")

        if not escalated_cves:
            pdf.body_font()
            pdf.cell(
                0,
                _LINE_HEIGHT_MM,
                "No escalations during this pipeline run.",
                new_x="LMARGIN",
                new_y="NEXT",
            )
            return

        escalation_timestamp = state.get("escalation_timestamp", "N/A")
        escalation_level = state.get("escalation_level", 0)
        human_decision = state.get("human_decision", "N/A")
        review_deadline = state.get("review_deadline", "N/A")

        headings_style = FontFace(emphasis="BOLD", color=_COLOR_WHITE, fill_color=_COLOR_DARK_GRAY)

        pdf.set_font("Helvetica", "", _SMALL_FONT_SIZE)

        with pdf.table(
            headings_style=headings_style,
            col_widths=(30, 35, 25, 30, 30),
            text_align="CENTER",
            borders_layout="MINIMAL",
            padding=1,
        ) as table:
            header = table.row()
            for h in ("CVE ID", "Escalation Time", "Level", "Decision", "Deadline"):
                header.cell(h)

            for cve_id in escalated_cves:
                row = table.row()
                row.cell(cve_id)
                row.cell(_safe_str(escalation_timestamp))
                row.cell(str(escalation_level))
                row.cell(_safe_str(human_decision))
                row.cell(_safe_str(review_deadline))

    # ------------------------------------------------------------------ #
    # Section 5: ML Model Transparency
    # ------------------------------------------------------------------ #

    def _section_ml_transparency(
        self,
        pdf: _SiopvPdf,
        classifications: dict[str, Any],
    ) -> None:
        pdf.section_title("5. ML Model Transparency")
        pdf.body_font()

        # Model version
        model_version = "1.0.0"
        if self._model_path is not None:
            model_version = str(self._model_path.stem).replace("xgboost_risk_model", "XGBoost v1.0")
        pdf.kv_line("Model", "XGBoost Risk Classifier")
        pdf.kv_line("Version", model_version)

        # Average confidence per severity
        severity_confidences: dict[str, list[float]] = {s: [] for s in _SEVERITY_ORDER}
        global_lime_features: dict[str, float] = {}

        for _cve_id, result in classifications.items():
            if not hasattr(result, "risk_score") or result.risk_score is None:
                continue
            rs = result.risk_score
            label = rs.risk_label if hasattr(rs, "risk_label") else "UNKNOWN"
            if label in severity_confidences:
                severity_confidences[label].append(rs.confidence)

            # Accumulate LIME features globally
            if hasattr(rs, "lime_explanation") and rs.lime_explanation:
                for feat, contrib in rs.lime_explanation.feature_contributions:
                    global_lime_features[feat] = global_lime_features.get(feat, 0.0) + abs(contrib)

        pdf.ln(2)
        pdf.bold_font()
        pdf.cell(
            0, _LINE_HEIGHT_MM, "Average Confidence by Severity:", new_x="LMARGIN", new_y="NEXT"
        )
        pdf.body_font()
        for sev in _SEVERITY_ORDER:
            vals = severity_confidences[sev]
            if vals:
                avg = sum(vals) / len(vals)
                pdf.cell(
                    0,
                    _LINE_HEIGHT_MM,
                    f"  {sev}: {avg:.2f} (n={len(vals)})",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )

        # Top 5 global LIME features
        if global_lime_features:
            pdf.ln(2)
            pdf.bold_font()
            pdf.cell(
                0, _LINE_HEIGHT_MM, "Top 5 Global LIME Features:", new_x="LMARGIN", new_y="NEXT"
            )
            pdf.body_font()
            sorted_feats = sorted(global_lime_features.items(), key=lambda x: x[1], reverse=True)[
                :5
            ]
            for feat, importance in sorted_feats:
                pdf.cell(
                    0,
                    _LINE_HEIGHT_MM,
                    f"  {feat[:60]}: {importance:.4f}",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )

    # ------------------------------------------------------------------ #
    # Section 6: DLP Audit Trail
    # ------------------------------------------------------------------ #

    def _section_dlp_audit(
        self,
        pdf: _SiopvPdf,
        dlp_result: dict[str, object] | None,
    ) -> None:
        pdf.section_title("6. DLP Audit Trail")
        pdf.body_font()

        if not dlp_result or not isinstance(dlp_result, dict):
            pdf.cell(
                0, _LINE_HEIGHT_MM, "No DLP processing was applied.", new_x="LMARGIN", new_y="NEXT"
            )
            return

        # PII entities redacted by type
        entity_counts: dict[str, int] = {}
        detections = dlp_result.get("detections", [])
        if isinstance(detections, list):
            for detection in detections:
                if isinstance(detection, dict):
                    etype = detection.get("entity_type", "UNKNOWN")
                elif hasattr(detection, "entity_type"):
                    etype = str(detection.entity_type)
                else:
                    etype = "UNKNOWN"
                entity_counts[etype] = entity_counts.get(etype, 0) + 1

        if entity_counts:
            pdf.bold_font()
            pdf.cell(0, _LINE_HEIGHT_MM, "PII Entities Redacted:", new_x="LMARGIN", new_y="NEXT")
            pdf.body_font()
            for etype, count in sorted(entity_counts.items()):
                pdf.cell(0, _LINE_HEIGHT_MM, f"  {etype}: {count}", new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.cell(0, _LINE_HEIGHT_MM, "No PII entities detected.", new_x="LMARGIN", new_y="NEXT")

        total_sanitized = dlp_result.get("total_fields_sanitized", 0)
        method = dlp_result.get("anonymization_method", "Presidio + Haiku dual-layer")

        pdf.kv_line("Total Fields Sanitized", str(total_sanitized))
        pdf.kv_line("Anonymization Method", str(method))

    # ------------------------------------------------------------------ #
    # Section 7: Remediation Timeline
    # ------------------------------------------------------------------ #

    def _section_remediation_timeline(
        self,
        pdf: _SiopvPdf,
        vulnerabilities: list[Any],
        classifications: dict[str, Any],
    ) -> None:
        pdf.section_title("7. Remediation Timeline")

        if not vulnerabilities:
            pdf.body_font()
            pdf.cell(
                0, _LINE_HEIGHT_MM, "No vulnerabilities to display.", new_x="LMARGIN", new_y="NEXT"
            )
            return

        now = datetime.now(UTC)
        rows: list[tuple[str, str, str, str, str, bool]] = []

        for vuln in vulnerabilities:
            vid = vuln.cve_id.value if hasattr(vuln.cve_id, "value") else str(vuln.cve_id)
            sev = vuln.severity if isinstance(vuln.severity, str) else str(vuln.severity)
            sla_days = _SLA_DAYS.get(sev.upper(), 90)
            due = now + timedelta(days=sla_days)

            classification = classifications.get(vid)
            status = "Classified" if classification else "Pending"

            sla_breached = sla_days <= 0
            rows.append((vid, sev, due.strftime("%Y-%m-%d"), status, str(sla_days), sla_breached))

        # Sort by due date ascending
        rows.sort(key=lambda r: r[2])

        headings_style = FontFace(emphasis="BOLD", color=_COLOR_WHITE, fill_color=_COLOR_DARK_GRAY)

        pdf.set_font("Helvetica", "", _SMALL_FONT_SIZE)

        with pdf.table(
            headings_style=headings_style,
            col_widths=(30, 20, 25, 20, 25),
            text_align="CENTER",
            borders_layout="MINIMAL",
            cell_fill_color=_COLOR_LIGHT_GRAY,
            cell_fill_mode="ROWS",
            padding=1,
        ) as table:
            header = table.row()
            for h in ("CVE ID", "Severity", "Due Date", "Status", "Days Remaining"):
                header.cell(h)

            for r_cve, r_sev, r_due, r_status, r_remaining, r_breached in rows:
                row = table.row()
                if r_breached:
                    row.cell(f"**{r_cve}**")
                    row.cell(f"**{r_sev}**")
                    row.cell(f"**{r_due}**")
                    row.cell(f"**{r_status}**")
                    row.cell(f"**{r_remaining}**")
                else:
                    row.cell(r_cve)
                    row.cell(r_sev)
                    row.cell(r_due)
                    row.cell(r_status)
                    row.cell(r_remaining)

    # ------------------------------------------------------------------ #
    # Section 8: Chain-of-Thought Appendix (optional)
    # ------------------------------------------------------------------ #

    def _section_cot_appendix(
        self,
        pdf: _SiopvPdf,
        state: PipelineState,
    ) -> None:
        pdf.add_page()
        pdf.section_title("8. Appendix - Chain-of-Thought Logs")
        pdf.body_font()

        errors = state.get("errors", [])
        if not errors:
            pdf.cell(
                0,
                _LINE_HEIGHT_MM,
                "No chain-of-thought logs available.",
                new_x="LMARGIN",
                new_y="NEXT",
            )
            return

        pdf.set_font("Courier", "", _SMALL_FONT_SIZE)
        for i, entry in enumerate(errors):
            pdf.multi_cell(
                0,
                _LINE_HEIGHT_MM - 1,
                f"[{i + 1}] {str(entry)[:1000]}",
                new_x="LMARGIN",
                new_y="NEXT",
            )
            pdf.ln(1)


__all__ = [
    "Fpdf2Adapter",
]
