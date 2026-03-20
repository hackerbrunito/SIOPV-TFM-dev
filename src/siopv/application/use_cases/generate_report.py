"""Generate Report Use Case for Phase 8 output layer.

Orchestrates report generation across multiple output channels:
1. Create/update Jira tickets for classified vulnerabilities
2. Generate PDF vulnerability report
3. Export metrics as JSON and CSV

Handles partial failure: if one channel fails, others still execute.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from siopv.application.orchestration.state import PipelineState
    from siopv.application.ports.jira_client import JiraClientPort
    from siopv.application.ports.metrics_exporter import MetricsExporterPort
    from siopv.application.ports.pdf_generator import PdfGeneratorPort

logger = structlog.get_logger(__name__)


class GenerateReportUseCase:
    """Use case for generating output reports from pipeline results.

    Combines Jira ticket creation, PDF report generation, and metrics
    export (JSON + CSV) into a single orchestrated operation.

    Resilient to partial failures: each output channel is independent,
    so a Jira API failure does not block PDF or CSV generation.
    """

    def __init__(
        self,
        jira: JiraClientPort,
        pdf: PdfGeneratorPort,
        metrics: MetricsExporterPort,
    ) -> None:
        """Initialize the report generation use case.

        Args:
            jira: Jira client port for ticket creation/updates
            pdf: PDF generator port for report rendering
            metrics: Metrics exporter port for JSON/CSV output
        """
        self._jira = jira
        self._pdf = pdf
        self._metrics = metrics

        logger.info("generate_report_use_case_initialized")

    async def execute(self, state: PipelineState) -> dict[str, Any]:
        """Execute report generation across all output channels.

        Args:
            state: Complete pipeline state with all phase results

        Returns:
            Dictionary with keys matching PipelineState output fields:
            - output_jira_keys: list[str]
            - output_pdf_path: str | None
            - output_csv_path: str | None
            - output_json_path: str | None
            - output_errors: list[str]
        """
        logger.info(
            "report_generation_started",
            thread_id=state.get("thread_id"),
            vulnerability_count=len(state.get("vulnerabilities", [])),
        )

        jira_keys: list[str] = []
        pdf_path: str | None = None
        csv_path: str | None = None
        json_path: str | None = None
        errors: list[str] = []

        # Channel 1: Jira tickets
        jira_keys, jira_errors = await self._create_jira_tickets(state)
        errors.extend(jira_errors)

        # Channel 2: PDF report
        pdf_path, pdf_errors = self._generate_pdf(state)
        errors.extend(pdf_errors)

        # Channel 3: Metrics export (JSON + CSV)
        json_path, json_errors = self._export_json(state)
        errors.extend(json_errors)

        csv_path, csv_errors = self._export_csv(state)
        errors.extend(csv_errors)

        logger.info(
            "report_generation_complete",
            jira_tickets_created=len(jira_keys),
            pdf_generated=pdf_path is not None,
            json_exported=json_path is not None,
            csv_exported=csv_path is not None,
            error_count=len(errors),
        )

        return {
            "output_jira_keys": jira_keys,
            "output_pdf_path": pdf_path,
            "output_csv_path": csv_path,
            "output_json_path": json_path,
            "output_errors": errors,
        }

    async def _create_jira_tickets(self, state: PipelineState) -> tuple[list[str], list[str]]:
        """Create Jira tickets for classified vulnerabilities.

        Builds a rich vulnerability_data dict for each CVE, combining data
        from all pipeline phases: ingestion (vulnerability metadata),
        enrichment (NVD, EPSS, GitHub), classification (ML + LLM), and
        output (PDF report path). This ensures Jira tickets contain the
        full intelligence SIOPV produces, not just a classification label.

        Args:
            state: Pipeline state with all phase results

        Returns:
            Tuple of (created ticket keys, error messages)
        """
        keys: list[str] = []
        errors: list[str] = []

        classifications = state.get("classifications", {})
        if not classifications:
            logger.warning("no_classifications_for_jira")
            return keys, errors

        # Gather all available data from pipeline state
        vuln_list = state.get("vulnerabilities", [])
        vulnerabilities: dict[str, Any] = {}
        for v in vuln_list:
            if hasattr(v, "cve_id") and hasattr(v.cve_id, "value"):
                vulnerabilities[v.cve_id.value] = v
        enrichments = state.get("enrichments", {})
        llm_confidence = state.get("llm_confidence", {})
        pdf_path = state.get("output_pdf_path")

        for cve_id, classification in classifications.items():
            try:
                existing_key = await self._jira.find_ticket_by_cve(cve_id)
                if existing_key is not None:
                    logger.info(
                        "jira_ticket_exists",
                        cve_id=cve_id,
                        ticket_key=existing_key,
                    )
                    keys.append(existing_key)
                    continue

                # Build rich vulnerability data from all pipeline phases
                vulnerability_data = self._build_jira_vulnerability_data(
                    cve_id=cve_id,
                    classification=classification,
                    vulnerability=vulnerabilities.get(cve_id),
                    enrichment=enrichments.get(cve_id),
                    llm_conf=llm_confidence.get(cve_id),
                    pdf_path=pdf_path,
                )
                ticket_key = await self._jira.create_ticket(vulnerability_data)
                keys.append(ticket_key)
                logger.info(
                    "jira_ticket_created",
                    cve_id=cve_id,
                    ticket_key=ticket_key,
                )
            except Exception as exc:
                error_msg = f"Jira ticket creation failed for {cve_id}: {exc}"
                logger.exception("jira_ticket_failed", cve_id=cve_id, error=str(exc))
                errors.append(error_msg)

        return keys, errors

    def _build_jira_vulnerability_data(
        self,
        *,
        cve_id: str,
        classification: Any,
        vulnerability: Any | None,
        enrichment: Any | None,
        llm_conf: float | None,
        pdf_path: str | None,
    ) -> dict[str, Any]:
        """Build rich vulnerability data dict for Jira ticket creation.

        Combines data from all pipeline phases so the Jira ticket contains
        the full intelligence SIOPV produces: vulnerability metadata,
        enrichment data (NVD, EPSS, GitHub), ML classification, LLM
        confidence, remediation guidance, and a link to the PDF report.
        """
        data: dict[str, Any] = {
            "cve_id": cve_id,
            "classification": classification,
        }

        # Vulnerability metadata from ingestion (Phase 1)
        if vulnerability is not None:
            data["package"] = getattr(vulnerability, "package_name", "unknown")
            installed = getattr(vulnerability, "installed_version", None)
            data["version"] = str(getattr(installed, "value", None) or installed or "unknown")
            fixed = getattr(vulnerability, "fixed_version", None)
            data["fixed_version"] = str(getattr(fixed, "value", None) or fixed or "")
            data["severity"] = getattr(vulnerability, "severity", "MEDIUM")
            cvss = getattr(vulnerability, "cvss_v3_score", None)
            data["cvss_score"] = getattr(cvss, "value", cvss)
            data["description"] = getattr(vulnerability, "description", "")
            data["primary_url"] = getattr(vulnerability, "primary_url", "")

        # Enrichment data from CRAG (Phase 2) — NVD, EPSS, GitHub
        if enrichment is not None:
            if hasattr(enrichment, "epss_score"):
                data["epss_score"] = enrichment.epss_score
            if hasattr(enrichment, "epss_percentile"):
                data["epss_percentile"] = enrichment.epss_percentile
            if hasattr(enrichment, "cvss_vector"):
                data["cvss_vector"] = enrichment.cvss_vector
            if hasattr(enrichment, "exploit_available"):
                data["exploit_available"] = enrichment.exploit_available
            if hasattr(enrichment, "attack_vector"):
                data["attack_vector"] = enrichment.attack_vector
            if hasattr(enrichment, "remediation") and enrichment.remediation:
                data["recommendation"] = enrichment.remediation

        # ML + LLM classification (Phase 3)
        if hasattr(classification, "risk_score") and classification.risk_score is not None:
            data["risk_score"] = classification.risk_score.risk_probability
            data["ml_confidence"] = getattr(classification.risk_score, "confidence", None)
        if llm_conf is not None:
            data["llm_confidence"] = llm_conf

        # PDF report link (Phase 8)
        if pdf_path:
            data["pdf_report_path"] = pdf_path

        return data

    def _generate_pdf(self, state: PipelineState) -> tuple[str | None, list[str]]:
        """Generate PDF report from pipeline state.

        Args:
            state: Pipeline state

        Returns:
            Tuple of (pdf path or None, error messages)
        """
        try:
            thread_id = state.get("thread_id", "unknown")
            output_path = f"/tmp/siopv-report-{thread_id}.pdf"
            path = self._pdf.generate(state, output_path)
        except Exception as exc:
            error_msg = f"PDF generation failed: {exc}"
            logger.exception("pdf_generation_failed", error=str(exc))
            return None, [error_msg]
        else:
            logger.info("pdf_generated", path=path)
            return path, []

    def _export_json(self, state: PipelineState) -> tuple[str | None, list[str]]:
        """Export pipeline results as JSON.

        Args:
            state: Pipeline state

        Returns:
            Tuple of (json path or None, error messages)
        """
        try:
            thread_id = state.get("thread_id", "unknown")
            output_path = f"/tmp/siopv-metrics-{thread_id}.json"
            path = self._metrics.export_json(state, output_path)
        except Exception as exc:
            error_msg = f"JSON export failed: {exc}"
            logger.exception("json_export_failed", error=str(exc))
            return None, [error_msg]
        else:
            logger.info("json_exported", path=path)
            return path, []

    def _export_csv(self, state: PipelineState) -> tuple[str | None, list[str]]:
        """Export pipeline results as CSV.

        Args:
            state: Pipeline state

        Returns:
            Tuple of (csv path or None, error messages)
        """
        try:
            thread_id = state.get("thread_id", "unknown")
            output_path = f"/tmp/siopv-metrics-{thread_id}.csv"
            path = self._metrics.export_csv(state, output_path)
        except Exception as exc:
            error_msg = f"CSV export failed: {exc}"
            logger.exception("csv_export_failed", error=str(exc))
            return None, [error_msg]
        else:
            logger.info("csv_exported", path=path)
            return path, []


def create_generate_report_use_case(
    jira: JiraClientPort,
    pdf: PdfGeneratorPort,
    metrics: MetricsExporterPort,
) -> GenerateReportUseCase:
    """Factory function to create GenerateReportUseCase.

    Args:
        jira: Jira client port implementation
        pdf: PDF generator port implementation
        metrics: Metrics exporter port implementation

    Returns:
        Configured GenerateReportUseCase
    """
    return GenerateReportUseCase(jira=jira, pdf=pdf, metrics=metrics)


__all__ = [
    "GenerateReportUseCase",
    "create_generate_report_use_case",
]
