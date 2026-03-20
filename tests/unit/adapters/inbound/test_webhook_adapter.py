"""Tests for the Trivy webhook adapter (A4)."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from siopv.adapters.inbound.webhook_adapter import (
    TrivyWebhookReceiver,
    router,
    set_webhook_receiver,
)
from siopv.domain.exceptions import (
    WebhookAuthenticationError,
    WebhookPayloadError,
)

SHARED_SECRET = "test-secret-key-for-hmac"
TRIVY_PAYLOAD = {
    "SchemaVersion": 2,
    "ArtifactName": "myimage:latest",
    "Results": [
        {
            "Target": "myimage:latest",
            "Vulnerabilities": [
                {
                    "VulnerabilityID": "CVE-2021-44228",
                    "PkgName": "log4j-core",
                    "Severity": "CRITICAL",
                }
            ],
        }
    ],
}

# HTTP status constants for ruff PLR2004
HTTP_202 = 202
HTTP_400 = 400
HTTP_401 = 401


def _sign_payload(payload: bytes, secret: str) -> str:
    """Generate HMAC-SHA256 signature for a payload."""
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


@pytest.fixture
def webhook_receiver(tmp_path: Path) -> TrivyWebhookReceiver:
    return TrivyWebhookReceiver(
        secret=SecretStr(SHARED_SECRET),
        output_dir=tmp_path,
    )


@pytest.fixture
def webhook_receiver_no_secret(tmp_path: Path) -> TrivyWebhookReceiver:
    return TrivyWebhookReceiver(secret=None, output_dir=tmp_path)


@pytest.fixture
def client(webhook_receiver: TrivyWebhookReceiver) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    set_webhook_receiver(webhook_receiver)
    return TestClient(app)


@pytest.fixture
def client_no_secret(webhook_receiver_no_secret: TrivyWebhookReceiver) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    set_webhook_receiver(webhook_receiver_no_secret)
    return TestClient(app)


# === Unit tests for TrivyWebhookReceiver ===


class TestTrivyWebhookReceiverUnit:
    """Unit tests for the receiver class itself."""

    @pytest.mark.asyncio
    async def test_valid_signature_parses_payload(
        self, webhook_receiver: TrivyWebhookReceiver
    ) -> None:
        body = json.dumps(TRIVY_PAYLOAD).encode()
        sig = _sign_payload(body, SHARED_SECRET)
        result = await webhook_receiver.receive_payload(body, sig)
        assert result["SchemaVersion"] == 2
        assert result["ArtifactName"] == "myimage:latest"

    @pytest.mark.asyncio
    async def test_invalid_signature_raises(self, webhook_receiver: TrivyWebhookReceiver) -> None:
        body = json.dumps(TRIVY_PAYLOAD).encode()
        with pytest.raises(WebhookAuthenticationError, match="Invalid webhook signature"):
            await webhook_receiver.receive_payload(body, "sha256=bad")

    @pytest.mark.asyncio
    async def test_missing_signature_raises(self, webhook_receiver: TrivyWebhookReceiver) -> None:
        body = json.dumps(TRIVY_PAYLOAD).encode()
        with pytest.raises(WebhookAuthenticationError, match="Missing webhook signature"):
            await webhook_receiver.receive_payload(body, None)

    @pytest.mark.asyncio
    async def test_no_secret_skips_verification(
        self, webhook_receiver_no_secret: TrivyWebhookReceiver
    ) -> None:
        body = json.dumps(TRIVY_PAYLOAD).encode()
        result = await webhook_receiver_no_secret.receive_payload(body, None)
        assert result["SchemaVersion"] == 2

    @pytest.mark.asyncio
    async def test_malformed_json_raises(
        self, webhook_receiver_no_secret: TrivyWebhookReceiver
    ) -> None:
        with pytest.raises(WebhookPayloadError, match="Malformed JSON"):
            await webhook_receiver_no_secret.receive_payload(b"not json", None)

    @pytest.mark.asyncio
    async def test_non_object_payload_raises(
        self, webhook_receiver_no_secret: TrivyWebhookReceiver
    ) -> None:
        with pytest.raises(WebhookPayloadError, match="must be a JSON object"):
            await webhook_receiver_no_secret.receive_payload(b"[1,2,3]", None)


# === Integration tests via FastAPI TestClient ===


class TestWebhookEndpoint:
    """Integration tests for the /api/v1/webhook/trivy endpoint."""

    def test_valid_hmac_returns_202(self, client: TestClient) -> None:
        body = json.dumps(TRIVY_PAYLOAD).encode()
        sig = _sign_payload(body, SHARED_SECRET)
        with patch(
            "siopv.adapters.inbound.webhook_adapter._run_pipeline_background",
            new_callable=AsyncMock,
        ):
            resp = client.post(
                "/api/v1/webhook/trivy",
                content=body,
                headers={
                    "X-Webhook-Signature-256": sig,
                    "Content-Type": "application/json",
                },
            )
        assert resp.status_code == HTTP_202
        data = resp.json()
        assert data["status"] == "accepted"

    def test_invalid_hmac_returns_401(self, client: TestClient) -> None:
        body = json.dumps(TRIVY_PAYLOAD).encode()
        resp = client.post(
            "/api/v1/webhook/trivy",
            content=body,
            headers={
                "X-Webhook-Signature-256": "sha256=invalid",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == HTTP_401

    def test_missing_signature_returns_401(self, client: TestClient) -> None:
        body = json.dumps(TRIVY_PAYLOAD).encode()
        resp = client.post(
            "/api/v1/webhook/trivy",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == HTTP_401

    def test_malformed_json_returns_400(self, client: TestClient) -> None:
        body = b"not-json"
        sig = _sign_payload(body, SHARED_SECRET)
        resp = client.post(
            "/api/v1/webhook/trivy",
            content=body,
            headers={
                "X-Webhook-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == HTTP_400

    def test_valid_payload_triggers_pipeline(self, client: TestClient) -> None:
        body = json.dumps(TRIVY_PAYLOAD).encode()
        sig = _sign_payload(body, SHARED_SECRET)
        with patch(
            "siopv.adapters.inbound.webhook_adapter._run_pipeline_background",
            new_callable=AsyncMock,
        ) as mock_run:
            resp = client.post(
                "/api/v1/webhook/trivy",
                content=body,
                headers={
                    "X-Webhook-Signature-256": sig,
                    "Content-Type": "application/json",
                },
            )
            assert resp.status_code == HTTP_202
            # Background task was enqueued
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0]["SchemaVersion"] == 2

    def test_no_secret_accepts_unsigned(self, client_no_secret: TestClient) -> None:
        body = json.dumps(TRIVY_PAYLOAD).encode()
        with patch(
            "siopv.adapters.inbound.webhook_adapter._run_pipeline_background",
            new_callable=AsyncMock,
        ):
            resp = client_no_secret.post(
                "/api/v1/webhook/trivy",
                content=body,
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == HTTP_202
