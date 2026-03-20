"""Webhook smoke test — starts the webhook server and sends a signed payload.

Usage:
    uv run python scripts/webhook-smoke-test.py

Verifies:
1. FastAPI webhook server starts on the configured port
2. A signed Trivy payload returns HTTP 202
3. An unsigned payload returns HTTP 401 (when secret is set)
4. Malformed JSON returns HTTP 400
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
import tempfile
import time
from multiprocessing import Process
from pathlib import Path

import httpx

# Test configuration
HOST = "127.0.0.1"
PORT = 18_765  # Unusual port to avoid conflicts
SECRET = "smoke-test-secret"
BASE_URL = f"http://{HOST}:{PORT}"
ENDPOINT = f"{BASE_URL}/api/v1/webhook/trivy"
MAX_RETRIES = 10
RETRY_DELAY_SECONDS = 0.5
REQUEST_TIMEOUT = 5.0

# Expected HTTP status codes
HTTP_202_ACCEPTED = 202
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401

TRIVY_PAYLOAD = {
    "SchemaVersion": 2,
    "ArtifactName": "smoke-test:latest",
    "Results": [
        {
            "Target": "smoke-test:latest",
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


def _sign(payload: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), payload, hashlib.sha256).hexdigest()


def _start_server() -> None:
    """Start the webhook FastAPI server in a subprocess."""
    import uvicorn  # noqa: PLC0415
    from fastapi import FastAPI  # noqa: PLC0415
    from pydantic import SecretStr  # noqa: PLC0415

    from siopv.adapters.inbound.webhook_adapter import (  # noqa: PLC0415
        TrivyWebhookReceiver,
        router,
        set_webhook_receiver,
    )

    app = FastAPI()
    app.include_router(router)

    output_dir = Path(tempfile.mkdtemp(prefix="siopv-smoke-"))
    receiver = TrivyWebhookReceiver(secret=SecretStr(SECRET), output_dir=output_dir)
    set_webhook_receiver(receiver)

    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def _wait_for_server() -> bool:
    """Wait until the server is accepting connections."""
    for _ in range(MAX_RETRIES):
        try:
            resp = httpx.get(BASE_URL, timeout=1.0)  # noqa: F841
        except httpx.ConnectError:
            time.sleep(RETRY_DELAY_SECONDS)
        except httpx.HTTPError:
            return True  # Server is up, just returned an error
        else:
            return True
    return False


def run_tests() -> bool:
    """Run all smoke tests. Returns True if all pass."""
    passed = 0
    failed = 0

    # Test 1: Valid HMAC -> 202
    body = json.dumps(TRIVY_PAYLOAD).encode()
    sig = _sign(body)
    resp = httpx.post(
        ENDPOINT,
        content=body,
        headers={"Content-Type": "application/json", "X-Webhook-Signature-256": sig},
        timeout=REQUEST_TIMEOUT,
    )
    if resp.status_code == HTTP_202_ACCEPTED:
        print("  PASS: Valid HMAC signature -> 202 Accepted")
        passed += 1
    else:
        print(f"  FAIL: Valid HMAC signature -> expected 202, got {resp.status_code}")
        failed += 1

    # Test 2: Invalid HMAC -> 401
    resp = httpx.post(
        ENDPOINT,
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature-256": "sha256=bad",
        },
        timeout=REQUEST_TIMEOUT,
    )
    if resp.status_code == HTTP_401_UNAUTHORIZED:
        print("  PASS: Invalid HMAC signature -> 401 Unauthorized")
        passed += 1
    else:
        print(f"  FAIL: Invalid HMAC signature -> expected 401, got {resp.status_code}")
        failed += 1

    # Test 3: Missing signature -> 401
    resp = httpx.post(
        ENDPOINT,
        content=body,
        headers={"Content-Type": "application/json"},
        timeout=REQUEST_TIMEOUT,
    )
    if resp.status_code == HTTP_401_UNAUTHORIZED:
        print("  PASS: Missing signature -> 401 Unauthorized")
        passed += 1
    else:
        print(f"  FAIL: Missing signature -> expected 401, got {resp.status_code}")
        failed += 1

    # Test 4: Malformed JSON -> 400
    bad_body = b"not json"
    bad_sig = _sign(bad_body)
    resp = httpx.post(
        ENDPOINT,
        content=bad_body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature-256": bad_sig,
        },
        timeout=REQUEST_TIMEOUT,
    )
    if resp.status_code == HTTP_400_BAD_REQUEST:
        print("  PASS: Malformed JSON -> 400 Bad Request")
        passed += 1
    else:
        print(f"  FAIL: Malformed JSON -> expected 400, got {resp.status_code}")
        failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def main() -> None:
    print("=== SIOPV Webhook Smoke Test ===\n")
    print(f"Starting webhook server on {HOST}:{PORT}...")

    server = Process(target=_start_server, daemon=True)
    server.start()

    if not _wait_for_server():
        print("ERROR: Server did not start within timeout")
        server.terminate()
        sys.exit(1)

    print("Server is up. Running tests...\n")

    try:
        success = run_tests()
    finally:
        server.terminate()
        server.join(timeout=5)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
