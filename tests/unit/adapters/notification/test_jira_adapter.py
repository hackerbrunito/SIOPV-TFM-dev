"""Unit tests for JiraAdapter.

Coverage targets:
- __init__: happy path, missing base_url
- _build_fields: all 10 standard fields, custom fields, SBOM chain
- create_ticket: new ticket, re-scan existing, HTTP error, timeout
- update_ticket: happy path, HTTP error, timeout
- find_ticket_by_cve: found, not found, HTTP error, timeout
- _handle_rescan: SLA breached, not breached, status Done, fetch failure
- _parse_sbom_chain: pip/npm/go chains, fallback, no data
- _risk_to_priority: all 4 tiers
- _calculate_due_date: all 4 SLA durations
- Graceful degradation: missing custom field IDs
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from siopv.adapters.notification.jira_adapter import (
    JiraAdapter,
    _build_adf_text,
    _calculate_due_date,
    _parse_sbom_chain,
    _risk_to_priority,
)
from siopv.domain.exceptions import JiraIntegrationError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_settings(
    *,
    base_url: str | None = "https://jira.example.com",
    project_key: str = "SEC",
    email: str = "bot@example.com",
    token: str = "test-token",
    custom_fields: dict[str, str] | None = None,
) -> MagicMock:
    settings = MagicMock()
    settings.jira_base_url = base_url
    settings.jira_project_key = project_key
    settings.jira_email = email
    settings.jira_api_token = MagicMock(get_secret_value=lambda: token)
    settings.jira_issue_type = "Task"
    settings.environment = "production"

    # Custom field attrs — default: none configured
    cf = custom_fields or {}
    for name in [
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
    ]:
        attr = f"jira_field_{name}"
        setattr(settings, attr, cf.get(name))

    return settings


def _vuln_data(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "cve_id": "CVE-2021-44228",
        "package": "log4j-core",
        "version": "2.14.1",
        "severity": "CRITICAL",
        "risk_score": 0.95,
        "description": "Log4Shell remote code execution vulnerability",
        "recommendation": "Upgrade to log4j-core 2.17.1 or later",
        "cvss_score": 10.0,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        "epss_score": 0.975,
        "epss_percentile": 0.99,
        "ml_confidence": 0.98,
        "llm_confidence": 0.96,
        "fixed_version": "2.17.1",
        "attack_vector": "NETWORK",
        "exploit_available": True,
    }
    base.update(overrides)
    return base


def _mock_response(
    status_code: int = 200,
    json_data: Any = None,
    text: str = "",
) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.text = text
    response.request = MagicMock()
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=response.request,
            response=response,
        )
    return response


@pytest.fixture
def mock_client() -> AsyncMock:
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def adapter(mock_client: AsyncMock) -> JiraAdapter:
    settings = _make_settings()
    return JiraAdapter(settings, client=mock_client)


@pytest.fixture
def adapter_with_custom_fields(mock_client: AsyncMock) -> JiraAdapter:
    settings = _make_settings(
        custom_fields={
            "cve_id": "customfield_10100",
            "cvss_score": "customfield_10101",
            "risk_score": "customfield_10102",
            "sbom_chain": "customfield_10103",
            "recommendation": "customfield_10104",
        },
    )
    return JiraAdapter(settings, client=mock_client)


# ---------------------------------------------------------------------------
# Init tests
# ---------------------------------------------------------------------------


class TestInit:
    def test_init_happy_path(self) -> None:
        settings = _make_settings()
        adapter = JiraAdapter(settings)
        assert adapter._base_url == "https://jira.example.com"
        assert adapter._project_key == "SEC"

    def test_init_strips_trailing_slash(self) -> None:
        settings = _make_settings(base_url="https://jira.example.com/")
        adapter = JiraAdapter(settings)
        assert adapter._base_url == "https://jira.example.com"

    def test_init_missing_base_url_raises(self) -> None:
        settings = _make_settings(base_url=None)
        with pytest.raises(JiraIntegrationError, match="SIOPV_JIRA_BASE_URL"):
            JiraAdapter(settings)

    def test_init_empty_base_url_raises(self) -> None:
        settings = _make_settings(base_url="")
        with pytest.raises(JiraIntegrationError, match="SIOPV_JIRA_BASE_URL"):
            JiraAdapter(settings)


# ---------------------------------------------------------------------------
# Priority mapping tests
# ---------------------------------------------------------------------------


class TestRiskToPriority:
    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (1.0, "Highest"),
            (0.95, "Highest"),
            (0.9, "Highest"),
            (0.89, "High"),
            (0.7, "High"),
            (0.69, "Medium"),
            (0.4, "Medium"),
            (0.39, "Low"),
            (0.1, "Low"),
            (0.0, "Low"),
        ],
    )
    def test_risk_to_priority(self, score: float, expected: str) -> None:
        assert _risk_to_priority(score) == expected


# ---------------------------------------------------------------------------
# Due date / SLA tests
# ---------------------------------------------------------------------------


class TestCalculateDueDate:
    @pytest.mark.parametrize(
        ("priority", "expected_days"),
        [
            ("Highest", 1),
            ("High", 7),
            ("Medium", 30),
            ("Low", 90),
        ],
    )
    def test_due_date_by_priority(self, priority: str, expected_days: int) -> None:
        result = _calculate_due_date(priority)
        expected = (datetime.now(tz=UTC) + timedelta(days=expected_days)).strftime("%Y-%m-%d")
        assert result == expected

    def test_unknown_priority_defaults_to_low(self) -> None:
        result = _calculate_due_date("Unknown")
        expected = (datetime.now(tz=UTC) + timedelta(days=90)).strftime("%Y-%m-%d")
        assert result == expected


# ---------------------------------------------------------------------------
# ADF builder tests
# ---------------------------------------------------------------------------


class TestBuildAdfText:
    def test_produces_valid_adf(self) -> None:
        result = _build_adf_text("Hello world")
        assert result["type"] == "doc"
        assert result["version"] == 1
        assert result["content"][0]["type"] == "paragraph"
        assert result["content"][0]["content"][0]["text"] == "Hello world"


# ---------------------------------------------------------------------------
# SBOM chain parser tests
# ---------------------------------------------------------------------------


class TestParseSbomChain:
    def test_full_dependency_chain(self) -> None:
        data = _vuln_data(
            dependency_chain=["my-app", "library-A@2.1", "library-B@1.3"],
        )
        result = _parse_sbom_chain(data)
        assert result == "my-app → library-A@2.1 → library-B@1.3 (VULNERABLE)"

    def test_two_item_chain(self) -> None:
        data = _vuln_data(dependency_chain=["app", "vuln-pkg@1.0"])
        result = _parse_sbom_chain(data)
        assert result == "app → vuln-pkg@1.0 (VULNERABLE)"

    def test_single_item_chain_falls_back(self) -> None:
        data = _vuln_data(dependency_chain=["only-one"])
        result = _parse_sbom_chain(data)
        # Single item chain → fallback to package@version
        assert result == "log4j-core@2.14.1 (VULNERABLE)"

    def test_no_chain_uses_package_version(self) -> None:
        data = _vuln_data()
        result = _parse_sbom_chain(data)
        assert result == "log4j-core@2.14.1 (VULNERABLE)"

    def test_no_package_no_version_returns_none(self) -> None:
        data: dict[str, Any] = {"cve_id": "CVE-2021-44228"}
        result = _parse_sbom_chain(data)
        assert result is None

    def test_empty_package_returns_none(self) -> None:
        data: dict[str, Any] = {"package": "", "version": ""}
        result = _parse_sbom_chain(data)
        assert result is None


# ---------------------------------------------------------------------------
# _build_fields tests
# ---------------------------------------------------------------------------


class TestBuildFields:
    def test_standard_fields_present(self, adapter: JiraAdapter) -> None:
        fields = adapter._build_fields(_vuln_data())
        assert fields["project"] == {"key": "SEC"}
        assert "[CVE-2021-44228]" in fields["summary"]
        assert "log4j-core@2.14.1" in fields["summary"]
        assert "CRITICAL" in fields["summary"]
        assert fields["issuetype"] == {"name": "Task"}
        assert fields["priority"] == {"name": "Highest"}
        assert "siopv" in fields["labels"]
        assert "security-vulnerability" in fields["labels"]
        assert "auto-triaged" in fields["labels"]
        assert "critical" in fields["labels"]
        assert "env-production" in fields["labels"]
        # Components removed — package info in labels instead
        # Environment moved to label (Jira API v3 compatibility)

    def test_description_adf_format(self, adapter: JiraAdapter) -> None:
        fields = adapter._build_fields(_vuln_data())
        desc = fields["description"]
        assert desc["type"] == "doc"
        text = desc["content"][0]["content"][0]["text"]
        assert "Log4Shell" in text
        assert "REMEDIATION" in text

    def test_duedate_set(self, adapter: JiraAdapter) -> None:
        fields = adapter._build_fields(_vuln_data(risk_score=0.95))
        # Critical → 1 day
        expected = (datetime.now(tz=UTC) + timedelta(days=1)).strftime("%Y-%m-%d")
        assert fields["duedate"] == expected

    def test_unknown_package_no_components(self, adapter: JiraAdapter) -> None:
        fields = adapter._build_fields(_vuln_data(package="unknown"))
        assert "components" not in fields

    def test_affected_component_label(self, adapter: JiraAdapter) -> None:
        fields = adapter._build_fields(_vuln_data(affected_component="backend"))
        assert "backend" in fields["labels"]

    def test_custom_fields_mapped_when_configured(
        self, adapter_with_custom_fields: JiraAdapter
    ) -> None:
        fields = adapter_with_custom_fields._build_fields(_vuln_data())
        assert fields["customfield_10100"] == "CVE-2021-44228"
        assert fields["customfield_10101"] == 10.0
        assert fields["customfield_10102"] == 0.95

    def test_custom_fields_skipped_when_not_configured(self, adapter: JiraAdapter) -> None:
        fields = adapter._build_fields(_vuln_data())
        # No customfield_* keys should be present
        custom_keys = [k for k in fields if k.startswith("customfield_")]
        assert custom_keys == []

    def test_sbom_chain_in_custom_fields(self, adapter_with_custom_fields: JiraAdapter) -> None:
        data = _vuln_data(dependency_chain=["app", "lib@1.0", "vuln@2.0"])
        fields = adapter_with_custom_fields._build_fields(data)
        assert fields["customfield_10103"] == "app → lib@1.0 → vuln@2.0 (VULNERABLE)"

    def test_no_description_still_has_enrichment(self, adapter: JiraAdapter) -> None:
        """Even without description/recommendation, enrichment data appears."""
        fields = adapter._build_fields(_vuln_data(description="", recommendation=""))
        text = fields["description"]["content"][0]["content"][0]["text"]
        # Rich description includes risk assessment even without summary text
        assert "Generated by SIOPV for CVE-2021-44228" in text


# ---------------------------------------------------------------------------
# create_ticket tests
# ---------------------------------------------------------------------------


class TestCreateTicket:
    @pytest.mark.asyncio
    async def test_create_new_ticket(self, adapter: JiraAdapter, mock_client: AsyncMock) -> None:
        # find_ticket_by_cve returns nothing
        mock_client.get.return_value = _mock_response(json_data={"issues": []})
        # create returns key
        mock_client.post.return_value = _mock_response(json_data={"key": "SEC-42"})

        result = await adapter.create_ticket(_vuln_data())
        assert result == "SEC-42"
        mock_client.post.assert_called_once()
        call_url = mock_client.post.call_args[0][0]
        assert call_url.endswith("/rest/api/3/issue")

    @pytest.mark.asyncio
    async def test_create_ticket_rescan_existing(
        self, adapter: JiraAdapter, mock_client: AsyncMock
    ) -> None:
        # find_ticket_by_cve returns existing
        search_resp = _mock_response(
            json_data={
                "issues": [{"key": "SEC-10"}],
            }
        )
        # _handle_rescan fetches ticket details
        detail_resp = _mock_response(
            json_data={
                "fields": {
                    "status": {"name": "In Progress"},
                    "duedate": "2020-01-01",
                    "labels": ["siopv"],
                }
            }
        )
        # update_ticket + comment both succeed
        put_resp = _mock_response()
        comment_resp = _mock_response()

        mock_client.get.side_effect = [search_resp, detail_resp]
        mock_client.put.return_value = put_resp
        mock_client.post.return_value = comment_resp

        result = await adapter.create_ticket(_vuln_data())
        assert result == "SEC-10"
        # Should NOT call POST to create a new issue
        # But SHOULD call POST for the SLA comment
        post_calls = mock_client.post.call_args_list
        assert len(post_calls) == 1
        assert "/comment" in post_calls[0][0][0]

    @pytest.mark.asyncio
    async def test_create_ticket_http_error(
        self, adapter: JiraAdapter, mock_client: AsyncMock
    ) -> None:
        mock_client.get.return_value = _mock_response(json_data={"issues": []})
        mock_client.post.return_value = _mock_response(status_code=400, text="Bad Request")

        with pytest.raises(JiraIntegrationError, match="HTTP 400"):
            await adapter.create_ticket(_vuln_data())

    @pytest.mark.asyncio
    async def test_create_ticket_timeout(
        self, adapter: JiraAdapter, mock_client: AsyncMock
    ) -> None:
        mock_client.get.return_value = _mock_response(json_data={"issues": []})
        mock_client.post.side_effect = httpx.TimeoutException("timed out")

        with pytest.raises(JiraIntegrationError, match="timeout"):
            await adapter.create_ticket(_vuln_data())


# ---------------------------------------------------------------------------
# update_ticket tests
# ---------------------------------------------------------------------------


class TestUpdateTicket:
    @pytest.mark.asyncio
    async def test_update_success(self, adapter: JiraAdapter, mock_client: AsyncMock) -> None:
        mock_client.put.return_value = _mock_response(status_code=204)
        await adapter.update_ticket("SEC-42", {"labels": ["new-label"]})
        mock_client.put.assert_called_once()
        call_url = mock_client.put.call_args[0][0]
        assert "SEC-42" in call_url

    @pytest.mark.asyncio
    async def test_update_http_error(self, adapter: JiraAdapter, mock_client: AsyncMock) -> None:
        mock_client.put.return_value = _mock_response(status_code=404)
        with pytest.raises(JiraIntegrationError, match="HTTP 404"):
            await adapter.update_ticket("SEC-999", {"labels": []})

    @pytest.mark.asyncio
    async def test_update_timeout(self, adapter: JiraAdapter, mock_client: AsyncMock) -> None:
        mock_client.put.side_effect = httpx.TimeoutException("timed out")
        with pytest.raises(JiraIntegrationError, match="timeout"):
            await adapter.update_ticket("SEC-42", {})


# ---------------------------------------------------------------------------
# find_ticket_by_cve tests
# ---------------------------------------------------------------------------


class TestFindTicketByCve:
    @pytest.mark.asyncio
    async def test_found(self, adapter: JiraAdapter, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = _mock_response(json_data={"issues": [{"key": "SEC-55"}]})
        result = await adapter.find_ticket_by_cve("CVE-2021-44228")
        assert result == "SEC-55"

    @pytest.mark.asyncio
    async def test_not_found(self, adapter: JiraAdapter, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = _mock_response(json_data={"issues": []})
        result = await adapter.find_ticket_by_cve("CVE-2099-99999")
        assert result is None

    @pytest.mark.asyncio
    async def test_search_http_error(self, adapter: JiraAdapter, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = _mock_response(status_code=500)
        with pytest.raises(JiraIntegrationError, match="HTTP 500"):
            await adapter.find_ticket_by_cve("CVE-2021-44228")

    @pytest.mark.asyncio
    async def test_search_timeout(self, adapter: JiraAdapter, mock_client: AsyncMock) -> None:
        mock_client.get.side_effect = httpx.TimeoutException("timed out")
        with pytest.raises(JiraIntegrationError, match="timeout"):
            await adapter.find_ticket_by_cve("CVE-2021-44228")


# ---------------------------------------------------------------------------
# _handle_rescan tests
# ---------------------------------------------------------------------------


class TestHandleRescan:
    @pytest.mark.asyncio
    async def test_sla_breached_adds_label_and_comment(
        self, adapter: JiraAdapter, mock_client: AsyncMock
    ) -> None:
        past_date = (datetime.now(tz=UTC) - timedelta(days=5)).strftime("%Y-%m-%d")
        mock_client.get.return_value = _mock_response(
            json_data={
                "fields": {
                    "status": {"name": "In Progress"},
                    "duedate": past_date,
                    "labels": ["siopv"],
                }
            }
        )
        mock_client.put.return_value = _mock_response(status_code=204)
        mock_client.post.return_value = _mock_response()

        await adapter._handle_rescan("SEC-10", _vuln_data())

        # Should update labels
        mock_client.put.assert_called_once()
        put_payload = mock_client.put.call_args[1]["json"]
        assert "sla-breached" in put_payload["fields"]["labels"]

        # Should post comment
        mock_client.post.assert_called_once()
        comment_url = mock_client.post.call_args[0][0]
        assert "/comment" in comment_url

    @pytest.mark.asyncio
    async def test_sla_not_breached_no_action(
        self, adapter: JiraAdapter, mock_client: AsyncMock
    ) -> None:
        future_date = (datetime.now(tz=UTC) + timedelta(days=30)).strftime("%Y-%m-%d")
        mock_client.get.return_value = _mock_response(
            json_data={
                "fields": {
                    "status": {"name": "Open"},
                    "duedate": future_date,
                    "labels": ["siopv"],
                }
            }
        )

        await adapter._handle_rescan("SEC-10", _vuln_data())
        mock_client.put.assert_not_called()
        mock_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_status_done_no_action(
        self, adapter: JiraAdapter, mock_client: AsyncMock
    ) -> None:
        past_date = (datetime.now(tz=UTC) - timedelta(days=5)).strftime("%Y-%m-%d")
        mock_client.get.return_value = _mock_response(
            json_data={
                "fields": {
                    "status": {"name": "Done"},
                    "duedate": past_date,
                    "labels": ["siopv"],
                }
            }
        )

        await adapter._handle_rescan("SEC-10", _vuln_data())
        mock_client.put.assert_not_called()

    @pytest.mark.asyncio
    async def test_already_sla_breached_no_duplicate(
        self, adapter: JiraAdapter, mock_client: AsyncMock
    ) -> None:
        past_date = (datetime.now(tz=UTC) - timedelta(days=5)).strftime("%Y-%m-%d")
        mock_client.get.return_value = _mock_response(
            json_data={
                "fields": {
                    "status": {"name": "In Progress"},
                    "duedate": past_date,
                    "labels": ["siopv", "sla-breached"],
                }
            }
        )

        await adapter._handle_rescan("SEC-10", _vuln_data())
        mock_client.put.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_failure_graceful(
        self, adapter: JiraAdapter, mock_client: AsyncMock
    ) -> None:
        mock_client.get.return_value = _mock_response(status_code=500)
        # Should not raise — graceful degradation
        await adapter._handle_rescan("SEC-10", _vuln_data())

    @pytest.mark.asyncio
    async def test_no_duedate_no_action(self, adapter: JiraAdapter, mock_client: AsyncMock) -> None:
        mock_client.get.return_value = _mock_response(
            json_data={
                "fields": {
                    "status": {"name": "Open"},
                    "duedate": None,
                    "labels": [],
                }
            }
        )

        await adapter._handle_rescan("SEC-10", _vuln_data())
        mock_client.put.assert_not_called()


# ---------------------------------------------------------------------------
# close tests
# ---------------------------------------------------------------------------


class TestClose:
    @pytest.mark.asyncio
    async def test_close_owned_client(self) -> None:
        settings = _make_settings()
        adapter = JiraAdapter(settings)
        # Force creation of owned client
        await adapter._get_client()
        assert adapter._owned_client is not None
        await adapter.close()
        assert adapter._owned_client is None

    @pytest.mark.asyncio
    async def test_close_no_owned_client(self) -> None:
        settings = _make_settings()
        adapter = JiraAdapter(settings, client=AsyncMock())
        # No owned client — close should be a no-op
        await adapter.close()


# ---------------------------------------------------------------------------
# DI output module tests
# ---------------------------------------------------------------------------


class TestDIOutput:
    def test_build_jira_adapter(self) -> None:
        from siopv.infrastructure.di.output import build_jira_adapter

        settings = _make_settings()
        adapter = build_jira_adapter(settings)
        assert isinstance(adapter, JiraAdapter)

    def test_build_pdf_adapter(self) -> None:
        from siopv.adapters.output.fpdf2_adapter import Fpdf2Adapter
        from siopv.infrastructure.di.output import build_pdf_adapter

        adapter = build_pdf_adapter(_make_settings())
        assert isinstance(adapter, Fpdf2Adapter)

    def test_build_metrics_exporter(self) -> None:
        from siopv.adapters.output.metrics_exporter_adapter import MetricsExporterAdapter
        from siopv.infrastructure.di.output import build_metrics_exporter

        settings = _make_settings()
        settings.output_dir = "/tmp/siopv-test"
        adapter = build_metrics_exporter(settings)
        assert isinstance(adapter, MetricsExporterAdapter)
