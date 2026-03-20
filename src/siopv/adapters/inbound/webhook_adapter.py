"""FastAPI webhook adapter for receiving Trivy scan results from CI/CD.

Implements WebhookReceiverPort. Validates HMAC-SHA256 signatures and
triggers pipeline runs asynchronously via background tasks.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Request, Response, status

from siopv.application.ports.webhook_receiver import WebhookReceiverPort
from siopv.domain.exceptions import (
    WebhookAuthenticationError,
    WebhookPayloadError,
)

if TYPE_CHECKING:
    from pydantic import SecretStr

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/webhook", tags=["webhook"])

# Module-level state set by DI at startup
_webhook_receiver: WebhookReceiverPort | None = None

# Error messages
_ERR_MISSING_SIGNATURE = "Missing webhook signature header"
_ERR_INVALID_SIGNATURE = "Invalid webhook signature"
_ERR_MALFORMED_JSON = "Malformed JSON payload"
_ERR_NOT_OBJECT = "Payload must be a JSON object"


def set_webhook_receiver(receiver: WebhookReceiverPort) -> None:
    """Set the module-level webhook receiver (called by DI at app startup)."""
    global _webhook_receiver  # noqa: PLW0603
    _webhook_receiver = receiver


class TrivyWebhookReceiver(WebhookReceiverPort):
    """Receives Trivy scan payloads via webhook with HMAC-SHA256 verification."""

    def __init__(self, secret: SecretStr | None, output_dir: Path) -> None:
        self._secret = secret
        self._output_dir = output_dir

    async def receive_payload(
        self,
        payload: bytes,
        signature: str | None,
    ) -> dict[str, Any]:
        """Validate HMAC signature and parse payload."""
        self._verify_signature(payload, signature)
        return self._parse_payload(payload)

    def _verify_signature(self, payload: bytes, signature: str | None) -> None:
        if self._secret is None:
            return

        if signature is None:
            raise WebhookAuthenticationError(_ERR_MISSING_SIGNATURE)

        # Strip optional "sha256=" prefix
        sig_value = signature.removeprefix("sha256=")

        expected = hmac.new(
            self._secret.get_secret_value().encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(sig_value, expected):
            raise WebhookAuthenticationError(_ERR_INVALID_SIGNATURE)

    def _parse_payload(self, payload: bytes) -> dict[str, Any]:
        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise WebhookPayloadError(_ERR_MALFORMED_JSON) from exc

        if not isinstance(data, dict):
            raise WebhookPayloadError(_ERR_NOT_OBJECT)

        return data


async def _run_pipeline_background(payload: dict[str, Any], output_dir: Path) -> None:
    """Run the SIOPV pipeline in a background task."""
    from siopv.application.orchestration.graph import run_pipeline  # noqa: PLC0415

    # Write payload to a temp file for the pipeline (expects a file path)
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        dir=str(output_dir),
        delete=False,
        prefix="webhook-trivy-",
    ) as tmp:
        json.dump(payload, tmp)
        tmp_path = Path(tmp.name)

    try:
        logger.info("webhook_pipeline_started", report_path=str(tmp_path))
        await run_pipeline(report_path=tmp_path)
        logger.info("webhook_pipeline_completed", report_path=str(tmp_path))
    except Exception:
        logger.exception("webhook_pipeline_failed", report_path=str(tmp_path))
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post(
    "/trivy",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=None,
)
async def receive_trivy_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Response:
    """Receive a Trivy scan report via webhook.

    Validates HMAC-SHA256 signature and enqueues pipeline processing.
    Returns 202 Accepted immediately.
    """
    receiver = _webhook_receiver
    if receiver is None:
        return Response(
            content='{"detail":"Webhook not configured"}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json",
        )

    body = await request.body()
    signature = request.headers.get("X-Webhook-Signature-256")

    try:
        payload = await receiver.receive_payload(body, signature)
    except WebhookAuthenticationError:
        remote = request.client.host if request.client else "unknown"
        logger.warning("webhook_auth_failed", remote=remote)
        return Response(
            content='{"detail":"Unauthorized"}',
            status_code=status.HTTP_401_UNAUTHORIZED,
            media_type="application/json",
        )
    except WebhookPayloadError as exc:
        logger.warning("webhook_payload_error", error=str(exc))
        return Response(
            content='{"detail":"Bad request"}',
            status_code=status.HTTP_400_BAD_REQUEST,
            media_type="application/json",
        )

    # Get output_dir from the concrete receiver type, or fall back
    if isinstance(receiver, TrivyWebhookReceiver):
        output_dir = receiver._output_dir
    else:
        output_dir = Path("./output")

    background_tasks.add_task(_run_pipeline_background, payload, output_dir)

    return Response(
        content='{"status":"accepted","message":"Pipeline processing enqueued"}',
        status_code=status.HTTP_202_ACCEPTED,
        media_type="application/json",
    )


__all__ = [
    "TrivyWebhookReceiver",
    "router",
    "set_webhook_receiver",
]
