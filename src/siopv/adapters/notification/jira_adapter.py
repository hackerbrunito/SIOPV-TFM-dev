"""Jira REST API v3 adapter for creating/updating security vulnerability tickets.

Implements JiraClientPort for the SIOPV output layer (Phase 8).
Uses Jira Cloud REST API v3 with Basic Auth (email + API token).
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import httpx
import structlog

from siopv.application.ports.jira_client import JiraClientPort
from siopv.domain.exceptions import JiraIntegrationError
from siopv.infrastructure.types import JsonDict

if TYPE_CHECKING:
    from siopv.infrastructure.config import Settings

logger = structlog.get_logger(__name__)

# Priority mapping: risk_score → Jira priority name
# Uses standard Jira Cloud priority names: Highest, High, Medium, Low, Lowest
_PRIORITY_THRESHOLDS: list[tuple[float, str]] = [
    (0.9, "Highest"),
    (0.7, "High"),
    (0.4, "Medium"),
]
_DEFAULT_PRIORITY = "Low"

# SLA due dates by severity (days from creation)
_SLA_DAYS: dict[str, int] = {
    "Highest": 1,
    "High": 7,
    "Medium": 30,
    "Low": 90,
}

# SBOM ecosystem parsers: ecosystem name → dependency key in package metadata
_SBOM_DEPENDENCY_KEYS: dict[str, str] = {
    "pip": "requires-dist",
    "npm": "dependencies",
    "go": "requires",
}


def _risk_to_priority(risk_score: float) -> str:
    """Map a 0.0-1.0 risk score to a Jira priority name."""
    for threshold, priority in _PRIORITY_THRESHOLDS:
        if risk_score >= threshold:
            return priority
    return _DEFAULT_PRIORITY


def _calculate_due_date(priority: str) -> str:
    """Calculate ISO due date based on priority SLA."""
    days = _SLA_DAYS.get(priority, _SLA_DAYS[_DEFAULT_PRIORITY])
    due = datetime.now(tz=UTC) + timedelta(days=days)
    return due.strftime("%Y-%m-%d")


def _build_adf_text(text: str) -> JsonDict:
    """Build an Atlassian Document Format (ADF) document from plain text."""
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


def _parse_sbom_chain(
    vulnerability_data: dict[str, Any],
) -> str | None:
    """Parse SBOM dependency chain from Trivy-style vulnerability data.

    Supports pip (requires-dist), npm (dependencies), go (requires) ecosystems.
    Returns a formatted dependency chain string or None.
    """
    dep_chain: list[str] | None = vulnerability_data.get("dependency_chain")
    if dep_chain and len(dep_chain) > 1:
        parts = []
        for i, dep in enumerate(dep_chain):
            if i == len(dep_chain) - 1:
                parts.append(f"{dep} (VULNERABLE)")
            else:
                parts.append(dep)
        return " → ".join(parts)

    # Fallback: try to build from package + ecosystem info
    package = vulnerability_data.get("package", "")
    version = vulnerability_data.get("version", "")
    if package and version:
        return f"{package}@{version} (VULNERABLE)"

    return None


class JiraAdapter(JiraClientPort):
    """Jira REST API v3 client for security vulnerability ticket management.

    Features:
    - Async HTTP with httpx
    - Basic Auth (email + API token) per Jira Cloud standard
    - All 27+ field mappings with graceful degradation on missing custom fields
    - SLA re-scan logic: detects existing tickets, marks SLA breaches
    - SBOM dependency chain annotation
    """

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        base_url = settings.jira_base_url
        if not base_url:
            msg = "SIOPV_JIRA_BASE_URL is required for Jira integration"
            raise JiraIntegrationError(msg)
        self._base_url = base_url.rstrip("/")
        self._project_key = settings.jira_project_key or "SEC"
        self._email = settings.jira_email or ""
        self._environment = settings.environment
        self._issue_type = getattr(settings, "jira_issue_type", None) or "Task"
        self._reporter = "siopv-bot"

        # Build Basic Auth header
        token = settings.jira_api_token.get_secret_value() if settings.jira_api_token else ""
        credentials = base64.b64encode(f"{self._email}:{token}".encode()).decode()
        self._auth_header = f"Basic {credentials}"

        # Custom field IDs — all optional, gracefully skipped if not configured
        self._custom_fields = self._load_custom_field_ids(settings)

        # HTTP client
        self._timeout = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
        self._external_client = client
        self._owned_client: httpx.AsyncClient | None = None

        logger.info(
            "jira_adapter_initialized",
            base_url=self._base_url,
            project_key=self._project_key,
            custom_fields_configured=len(self._custom_fields),
        )

    @staticmethod
    def _load_custom_field_ids(settings: Settings) -> dict[str, str]:
        """Load custom field IDs from settings (SIOPV_JIRA_FIELD_* env vars).

        Reads attributes like jira_field_cve_id, jira_field_cvss_score, etc.
        Missing fields are simply omitted — the adapter skips them gracefully.
        """
        field_names = [
            "cve_id",
            "cvss_score",
            "cvss_vector",
            "epss_score",
            "epss_percentile",
            "risk_score",
            "ml_confidence",
            "llm_confidence",
            "affected_package",
            "affected_version",
            "fixed_version",
            "attack_vector",
            "exploit_available",
            "recommendation",
            "sbom_chain",
            "scan_source",
            "classification_model",
        ]
        fields: dict[str, str] = {}
        for name in field_names:
            attr = f"jira_field_{name}"
            value = getattr(settings, attr, None)
            if value:
                fields[name] = value
        return fields

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._external_client:
            return self._external_client

        if self._owned_client is None:
            self._owned_client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={
                    "Authorization": self._auth_header,
                    "Content-Type": "application/json",
                    "User-Agent": "SIOPV/1.0",
                },
                follow_redirects=True,
            )
        return self._owned_client

    async def close(self) -> None:
        """Close HTTP client if owned."""
        if self._owned_client:
            await self._owned_client.aclose()
            self._owned_client = None

    def _build_fields(self, vulnerability_data: dict[str, Any]) -> JsonDict:
        """Build the Jira issue fields payload from vulnerability data."""
        cve_id = vulnerability_data.get("cve_id", "UNKNOWN")
        package = vulnerability_data.get("package", "unknown")
        version = vulnerability_data.get("version", "unknown")
        severity = vulnerability_data.get("severity", "MEDIUM")
        risk_score = float(vulnerability_data.get("risk_score", 0.0))
        description_text = vulnerability_data.get("description", "")
        recommendation = vulnerability_data.get("recommendation", "")

        priority = _risk_to_priority(risk_score)
        due_date = _calculate_due_date(priority)

        # Summary: [CVE-ID] package@version — SEVERITY Risk
        summary = f"[{cve_id}] {package}@{version} — {severity} Risk"

        # Description: AI summary + remediation (ADF format for Jira v3)
        desc_parts = []
        if description_text:
            desc_parts.append(f"Summary: {description_text}")
        if recommendation:
            desc_parts.append(f"Remediation: {recommendation}")
        full_description = (
            "\n\n".join(desc_parts) if desc_parts else f"Security vulnerability {cve_id}"
        )

        # Labels
        labels = [
            "security-vulnerability",
            "auto-triaged",
            "siopv",
            severity.lower(),
        ]
        affected_component = vulnerability_data.get("affected_component")
        if affected_component:
            labels.append(affected_component)

        # Standard fields (1-10)
        fields: JsonDict = {
            "project": {"key": self._project_key},
            "summary": summary,
            "description": _build_adf_text(full_description),
            "issuetype": {"name": self._issue_type},
            "priority": {"name": priority},
            "labels": labels,
            "duedate": due_date,
        }

        # Environment tracked via label (Jira API v3 environment field
        # requires ADF format or may not be available on all project types)
        if self._environment:
            labels.append(f"env-{self._environment}")

        # Components (field 6) — only include if component exists in Jira project
        # Skipped by default: auto-creating components requires admin permissions
        # Package info is captured in labels instead

        # Reporter (field 8) — only if Jira allows setting reporter
        # Assignee (field 9) — skip unless configured per severity tier

        # Custom fields (11-27) - gracefully skip missing IDs
        custom_values: dict[str, Any] = {
            "cve_id": cve_id,
            "cvss_score": vulnerability_data.get("cvss_score"),
            "cvss_vector": vulnerability_data.get("cvss_vector"),
            "epss_score": vulnerability_data.get("epss_score"),
            "epss_percentile": vulnerability_data.get("epss_percentile"),
            "risk_score": risk_score,
            "ml_confidence": vulnerability_data.get("ml_confidence"),
            "llm_confidence": vulnerability_data.get("llm_confidence"),
            "affected_package": package,
            "affected_version": version,
            "fixed_version": vulnerability_data.get("fixed_version"),
            "attack_vector": vulnerability_data.get("attack_vector"),
            "exploit_available": vulnerability_data.get("exploit_available"),
            "recommendation": recommendation,
            "scan_source": vulnerability_data.get("scan_source", "trivy"),
            "classification_model": vulnerability_data.get("classification_model", "xgboost"),
        }

        # SBOM chain (field 28)
        sbom_chain = _parse_sbom_chain(vulnerability_data)
        if sbom_chain:
            custom_values["sbom_chain"] = sbom_chain

        for field_name, value in custom_values.items():
            if value is None:
                continue
            custom_field_id = self._custom_fields.get(field_name)
            if custom_field_id:
                fields[custom_field_id] = value
            else:
                logger.debug(
                    "jira_custom_field_skipped",
                    field_name=field_name,
                    reason="no_custom_field_id_configured",
                )

        return fields

    async def create_ticket(self, vulnerability_data: dict[str, Any]) -> str:
        """Create a Jira ticket for a classified vulnerability.

        Implements SLA re-scan logic: if a ticket already exists for this CVE,
        checks SLA breach status and adds comments instead of creating a duplicate.

        Args:
            vulnerability_data: Dictionary with vulnerability details

        Returns:
            Jira ticket key (e.g., 'SEC-123')

        Raises:
            JiraIntegrationError: On API errors
        """
        cve_id = vulnerability_data.get("cve_id", "")

        # SLA re-scan: check for existing ticket
        if cve_id:
            existing_key = await self.find_ticket_by_cve(cve_id)
            if existing_key:
                await self._handle_rescan(existing_key, vulnerability_data)
                return existing_key

        # Create new ticket
        fields = self._build_fields(vulnerability_data)
        payload: JsonDict = {"fields": fields}

        client = await self._get_client()
        url = f"{self._base_url}/rest/api/3/issue"

        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.exception(
                "jira_create_failed",
                cve_id=cve_id,
                status_code=e.response.status_code,
                body=e.response.text[:500],
            )
            msg = f"Failed to create Jira ticket for {cve_id}: HTTP {e.response.status_code}"
            raise JiraIntegrationError(msg) from e
        except httpx.TimeoutException as e:
            msg = f"Jira API timeout creating ticket for {cve_id}"
            raise JiraIntegrationError(msg) from e

        data: JsonDict = response.json()
        ticket_key: str = data["key"]

        logger.info(
            "jira_ticket_created",
            ticket_key=ticket_key,
            cve_id=cve_id,
            priority=fields.get("priority", {}).get("name"),
        )

        return ticket_key

    async def update_ticket(self, ticket_key: str, fields: dict[str, Any]) -> None:
        """Update fields on an existing Jira ticket.

        Args:
            ticket_key: Jira issue key (e.g., 'SEC-123')
            fields: Dictionary of field names to new values

        Raises:
            JiraIntegrationError: On API errors or if ticket not found
        """
        client = await self._get_client()
        url = f"{self._base_url}/rest/api/3/issue/{ticket_key}"
        payload: JsonDict = {"fields": fields}

        try:
            response = await client.put(url, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.exception(
                "jira_update_failed",
                ticket_key=ticket_key,
                status_code=e.response.status_code,
            )
            msg = f"Failed to update Jira ticket {ticket_key}: HTTP {e.response.status_code}"
            raise JiraIntegrationError(msg) from e
        except httpx.TimeoutException as e:
            msg = f"Jira API timeout updating ticket {ticket_key}"
            raise JiraIntegrationError(msg) from e

        logger.info("jira_ticket_updated", ticket_key=ticket_key)

    async def find_ticket_by_cve(self, cve_id: str) -> str | None:
        """Find an existing Jira ticket for a CVE identifier.

        Uses JQL search by label containing the CVE ID.

        Args:
            cve_id: CVE identifier (e.g., 'CVE-2021-44228')

        Returns:
            Jira ticket key if found, None otherwise

        Raises:
            JiraIntegrationError: On API errors during search
        """
        client = await self._get_client()
        jql = (
            f'project = "{self._project_key}" '
            f'AND summary ~ "{cve_id}" '
            f'AND labels = "siopv" '
            f"ORDER BY created DESC"
        )
        url = f"{self._base_url}/rest/api/3/search/jql"

        try:
            response = await client.get(
                url, params={"jql": jql, "maxResults": 1, "fields": "key,status,duedate"}
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.exception(
                "jira_search_failed",
                cve_id=cve_id,
                status_code=e.response.status_code,
            )
            msg = f"Failed to search Jira for {cve_id}: HTTP {e.response.status_code}"
            raise JiraIntegrationError(msg) from e
        except httpx.TimeoutException as e:
            msg = f"Jira API timeout searching for {cve_id}"
            raise JiraIntegrationError(msg) from e

        data: JsonDict = response.json()
        issues: list[JsonDict] = data.get("issues", [])

        if not issues:
            return None

        key: str = issues[0]["key"]
        logger.debug("jira_ticket_found", cve_id=cve_id, ticket_key=key)
        return key

    async def _handle_rescan(
        self,
        ticket_key: str,
        vulnerability_data: dict[str, Any],
    ) -> None:
        """Handle re-scan logic for an existing CVE ticket.

        If the ticket's due date has passed and status is not Done,
        adds an 'sla-breached' label and a comment.
        """
        client = await self._get_client()
        url = f"{self._base_url}/rest/api/3/issue/{ticket_key}"

        try:
            response = await client.get(url, params={"fields": "status,duedate,labels"})
            response.raise_for_status()
        except httpx.HTTPStatusError:
            logger.warning("jira_rescan_fetch_failed", ticket_key=ticket_key)
            return

        data: JsonDict = response.json()
        fields_data: JsonDict = data.get("fields", {})
        status_name: str = fields_data.get("status", {}).get("name", "")
        due_date_str: str | None = fields_data.get("duedate")
        current_labels: list[str] = fields_data.get("labels", [])

        # Check SLA breach: due date past AND not Done
        if due_date_str and status_name.lower() != "done":
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").replace(tzinfo=UTC)
            now = datetime.now(tz=UTC)

            if now > due_date and "sla-breached" not in current_labels:
                # Add sla-breached label
                updated_labels = [*current_labels, "sla-breached"]
                await self.update_ticket(ticket_key, {"labels": updated_labels})

                # Add comment about SLA breach
                cve_id = vulnerability_data.get("cve_id", "unknown")
                comment_body = _build_adf_text(
                    f"SLA breach detected during re-scan of {cve_id}. "
                    f"Due date {due_date_str} has passed. "
                    f"Current status: {status_name}."
                )
                comment_url = f"{self._base_url}/rest/api/3/issue/{ticket_key}/comment"
                try:
                    resp = await client.post(comment_url, json={"body": comment_body})
                    resp.raise_for_status()
                except httpx.HTTPStatusError:
                    logger.warning("jira_sla_comment_failed", ticket_key=ticket_key)

                logger.warning(
                    "jira_sla_breached",
                    ticket_key=ticket_key,
                    cve_id=cve_id,
                    due_date=due_date_str,
                    status=status_name,
                )


__all__ = ["JiraAdapter"]
