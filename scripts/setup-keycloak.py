#!/usr/bin/env python3
"""
Keycloak Bootstrap Script for SIOPV

Initializes Keycloak with realm creation and confidential client configuration
for OIDC client_credentials flow. Outputs configuration variables for .env file.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# Configuration
KEYCLOAK_BASE_URL = "http://localhost:8888"
KEYCLOAK_ADMIN = "admin"
KEYCLOAK_ADMIN_PASSWORD = "admin"
HEALTH_CHECK_TIMEOUT = 30
HEALTH_CHECK_INTERVAL = 2
REALM_NAME = "siopv"
CLIENT_ID = "siopv-client"
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_CONFLICT = 409


def make_json_request(
    url: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """Make JSON HTTP request to Keycloak Admin REST API.

    Sends an HTTP request using urllib with JSON encoding/decoding
    and optional bearer token authentication.

    Args:
        url: The full URL to send the request to.
        method: HTTP method to use. Defaults to "GET".
        data: Optional JSON-serializable data to send in request body.
        token: Optional bearer token for authentication.

    Returns:
        Dictionary containing the JSON response from the server,
        or empty dict if response body is empty.

    Raises:
        urllib.error.HTTPError: If server returns an HTTP error status.
        urllib.error.URLError: If network connection fails.
    """
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request_data = json.dumps(data).encode("utf-8") if data else None
    request = urllib.request.Request(url, data=request_data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response_data = response.read().decode("utf-8")
            return json.loads(response_data) if response_data else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"  HTTP {e.code} error: {error_body}", file=sys.stderr)
        raise
    except urllib.error.URLError as e:
        print(f"  Network error: {e.reason}", file=sys.stderr)
        raise


def make_form_request(
    url: str,
    form_data: dict[str, str],
) -> dict[str, Any]:
    """Make form-encoded HTTP POST request.

    Sends an HTTP POST with application/x-www-form-urlencoded body,
    used for OAuth2 token endpoints.

    Args:
        url: The full URL to send the request to.
        form_data: Key-value pairs to encode as form data.

    Returns:
        Dictionary containing the JSON response from the server.

    Raises:
        urllib.error.HTTPError: If server returns an HTTP error status.
        urllib.error.URLError: If network connection fails.
    """
    encoded_data = urllib.parse.urlencode(form_data).encode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    request = urllib.request.Request(url, data=encoded_data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response_data = response.read().decode("utf-8")
            return json.loads(response_data) if response_data else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"  HTTP {e.code} error: {error_body}", file=sys.stderr)
        raise
    except urllib.error.URLError as e:
        print(f"  Network error: {e.reason}", file=sys.stderr)
        raise


def _require_value(value: str | None, label: str) -> str:
    """Validate that a response value is present.

    Args:
        value: The value to check.
        label: Human-readable label for error messages.

    Returns:
        The validated non-None value.

    Raises:
        ValueError: If value is None or empty.
    """
    if not value:
        msg = f"{label} not returned in response"
        raise ValueError(msg)
    return value


def wait_for_keycloak(timeout: int = HEALTH_CHECK_TIMEOUT) -> bool:
    """Wait for Keycloak server to become available.

    Polls the Keycloak health endpoint until it responds with 200 OK
    or the timeout is reached. Checks every HEALTH_CHECK_INTERVAL seconds.

    Args:
        timeout: Maximum seconds to wait before giving up. Defaults to HEALTH_CHECK_TIMEOUT.

    Returns:
        True if Keycloak becomes available within timeout, False otherwise.
    """
    print(f"Waiting for Keycloak at {KEYCLOAK_BASE_URL} (timeout: {timeout}s)...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = urllib.request.urlopen(f"{KEYCLOAK_BASE_URL}/realms/master", timeout=5)
            if response.status == HTTP_OK:
                print("Keycloak is ready")
                return True
        except (urllib.error.URLError, urllib.error.HTTPError):
            pass

        time.sleep(HEALTH_CHECK_INTERVAL)

    print(
        f"Keycloak not available after {timeout}s. Is the service running?",
        file=sys.stderr,
    )
    return False


def get_admin_token(
    base_url: str = KEYCLOAK_BASE_URL,
    admin: str = KEYCLOAK_ADMIN,
    password: str = KEYCLOAK_ADMIN_PASSWORD,
) -> str:
    """Get admin access token via password grant on master realm.

    Authenticates as the Keycloak admin user using the built-in admin-cli
    client and password grant type.

    Args:
        base_url: Keycloak base URL. Defaults to KEYCLOAK_BASE_URL.
        admin: Admin username. Defaults to KEYCLOAK_ADMIN.
        password: Admin password. Defaults to KEYCLOAK_ADMIN_PASSWORD.

    Returns:
        The admin access token string.

    Raises:
        ValueError: If access_token is not returned in the response.
        urllib.error.HTTPError: If authentication fails.
        urllib.error.URLError: If network connection fails.
    """
    print("Authenticating as Keycloak admin...")

    token_url = f"{base_url}/realms/master/protocol/openid-connect/token"
    response = make_form_request(
        token_url,
        form_data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": admin,
            "password": password,
        },
    )

    access_token = _require_value(response.get("access_token"), "Admin access token")
    print("Admin authentication successful")
    return access_token


def create_realm(
    base_url: str,
    admin_token: str,
    realm_name: str = REALM_NAME,
) -> None:
    """Create a Keycloak realm.

    Creates a new realm via the Keycloak Admin REST API.
    If the realm already exists (HTTP 409), logs a message and continues.

    Args:
        base_url: Keycloak base URL.
        admin_token: Admin bearer token for authentication.
        realm_name: Name of the realm to create. Defaults to REALM_NAME.

    Raises:
        urllib.error.HTTPError: If the API request fails (except 409 Conflict).
        urllib.error.URLError: If network connection fails.
    """
    print(f"Creating realm '{realm_name}'...")

    try:
        make_json_request(
            f"{base_url}/admin/realms",
            method="POST",
            data={"realm": realm_name, "enabled": True},
            token=admin_token,
        )
        print(f"Realm '{realm_name}' created")
    except urllib.error.HTTPError as e:
        if e.code == HTTP_CONFLICT:
            print(f"Realm '{realm_name}' already exists, continuing")
        else:
            raise


def create_client(
    base_url: str,
    admin_token: str,
    realm: str = REALM_NAME,
    client_id: str = CLIENT_ID,
) -> str:
    """Create a confidential client with client_credentials grant type.

    Creates an OAuth2 confidential client in the specified realm with
    service accounts enabled for machine-to-machine authentication.
    If the client already exists, fetches its UUID instead.

    Args:
        base_url: Keycloak base URL.
        admin_token: Admin bearer token for authentication.
        realm: Target realm name. Defaults to REALM_NAME.
        client_id: Client identifier. Defaults to CLIENT_ID.

    Returns:
        The internal UUID of the created (or existing) client.

    Raises:
        ValueError: If client UUID cannot be determined.
        urllib.error.HTTPError: If the API request fails.
        urllib.error.URLError: If network connection fails.
    """
    print(f"Creating client '{client_id}' in realm '{realm}'...")

    client_data: dict[str, Any] = {
        "clientId": client_id,
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,
        "clientAuthenticatorType": "client-secret",
        "serviceAccountsEnabled": True,
        "standardFlowEnabled": False,
        "directAccessGrantsEnabled": False,
    }

    try:
        make_json_request(
            f"{base_url}/admin/realms/{realm}/clients",
            method="POST",
            data=client_data,
            token=admin_token,
        )
        print(f"Client '{client_id}' created")
    except urllib.error.HTTPError as e:
        if e.code == HTTP_CONFLICT:
            print(f"Client '{client_id}' already exists, fetching UUID")
        else:
            raise

    # Fetch client UUID by clientId lookup
    return _find_client_uuid(base_url, admin_token, realm, client_id)


def _find_client_uuid(
    base_url: str,
    admin_token: str,
    realm: str,
    client_id: str,
) -> str:
    """Look up the internal UUID of a client by its clientId.

    Args:
        base_url: Keycloak base URL.
        admin_token: Admin bearer token for authentication.
        realm: Realm containing the client.
        client_id: The clientId to search for.

    Returns:
        The internal UUID of the matching client.

    Raises:
        ValueError: If client is not found.
        urllib.error.HTTPError: If the API request fails.
        urllib.error.URLError: If network connection fails.
    """
    encoded_client_id = urllib.parse.quote(client_id, safe="")
    url = f"{base_url}/admin/realms/{realm}/clients?clientId={encoded_client_id}"
    clients: Any = make_json_request(url, token=admin_token)

    if not isinstance(clients, list) or len(clients) == 0:
        msg = f"Client '{client_id}' not found in realm '{realm}'"
        raise ValueError(msg)

    client_uuid = _require_value(clients[0].get("id"), "Client UUID")
    print(f"Client UUID: {client_uuid}")
    return client_uuid


def get_client_secret(
    base_url: str,
    admin_token: str,
    realm: str,
    client_uuid: str,
) -> str:
    """Retrieve the generated client secret.

    Fetches the client secret from the Keycloak Admin REST API using
    the internal client UUID.

    Args:
        base_url: Keycloak base URL.
        admin_token: Admin bearer token for authentication.
        realm: Realm containing the client.
        client_uuid: Internal UUID of the client.

    Returns:
        The client secret string.

    Raises:
        ValueError: If client secret is not returned in the response.
        urllib.error.HTTPError: If the API request fails.
        urllib.error.URLError: If network connection fails.
    """
    print("Retrieving client secret...")

    response = make_json_request(
        f"{base_url}/admin/realms/{realm}/clients/{client_uuid}/client-secret",
        token=admin_token,
    )

    secret = _require_value(response.get("value"), "Client secret")
    print("Client secret retrieved")
    return secret


def print_configuration(
    realm: str,
    client_id: str,
    client_secret: str,
    issuer_url: str,
) -> None:
    """Print OIDC configuration for adding to .env file.

    Displays formatted output with realm, client credentials, and issuer URL,
    along with ready-to-copy environment variable assignments.

    Args:
        realm: The Keycloak realm name.
        client_id: The OAuth2 client identifier.
        client_secret: The client secret for authentication.
        issuer_url: The OIDC issuer URL for token validation.
    """
    print("\n" + "=" * 70)
    print("Keycloak Bootstrap Complete!")
    print("=" * 70)
    print(f"\nRealm:           {realm}")
    print(f"Client ID:       {client_id}")
    print(f"Client Secret:   {client_secret}")
    print(f"Issuer URL:      {issuer_url}")
    print("\nAdd these lines to your .env file:\n")
    print("SIOPV_OIDC_ENABLED=true")
    print(f"SIOPV_OIDC_ISSUER_URL={issuer_url}")
    print("SIOPV_OIDC_AUDIENCE=siopv-api")
    print(f"SIOPV_OIDC_CLIENT_ID={client_id}")
    print(f"SIOPV_OIDC_CLIENT_SECRET={client_secret}")
    print("\n" + "=" * 70)


def main() -> int:
    """Execute Keycloak bootstrap workflow.

    Orchestrates the complete setup process:
    1. Wait for Keycloak server availability
    2. Authenticate as admin
    3. Create realm
    4. Create confidential client
    5. Retrieve client secret
    6. Print configuration for .env file

    Returns:
        Exit code: 0 for success, 1 for failure, 130 for keyboard interrupt.
    """
    try:
        # Step 1: Wait for Keycloak availability
        if not wait_for_keycloak():
            return 1

        # Step 2: Authenticate as admin
        admin_token = get_admin_token()

        # Step 3: Create realm
        create_realm(KEYCLOAK_BASE_URL, admin_token, REALM_NAME)

        # Step 4: Create confidential client
        client_uuid = create_client(KEYCLOAK_BASE_URL, admin_token, REALM_NAME, CLIENT_ID)

        # Step 5: Retrieve client secret
        client_secret = get_client_secret(KEYCLOAK_BASE_URL, admin_token, REALM_NAME, client_uuid)

        # Step 6: Print configuration
        issuer_url = f"{KEYCLOAK_BASE_URL}/realms/{REALM_NAME}"
        print_configuration(REALM_NAME, CLIENT_ID, client_secret, issuer_url)

    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except (
        ValueError,
        urllib.error.HTTPError,
        urllib.error.URLError,
    ) as e:
        msg = f"Bootstrap failed: {e}"
        print(f"\n{msg}", file=sys.stderr)
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
