# OpenFGA Patterns — Full Reference

Complete code examples for OpenFGA authorization in SIOPV.

---

## Authorization Model

```yaml
# model.fga
model
  schema 1.1

type user

type organization
  relations
    define admin: [user]
    define member: [user] or admin

type team
  relations
    define org: [organization]
    define lead: [user]
    define member: [user] or lead

type vulnerability
  relations
    define org: [organization]
    define viewer: member from org
    define editor: admin from org or lead from team
    define owner: [user]
```

---

## OpenFGA Client Setup

```python
from openfga_sdk import ClientConfiguration, OpenFgaClient
from openfga_sdk.client.models import ClientCheckRequest, ClientTuple


async def create_fga_client(
    api_url: str,
    store_id: str | None = None,
) -> OpenFgaClient:
    """Create OpenFGA client.

    Args:
        api_url: OpenFGA server URL (from settings.openfga_api_url).
        store_id: Optional store ID.
    """

    config = ClientConfiguration(
        api_url=api_url,
        store_id=store_id,
    )

    return OpenFgaClient(config)
```

---

## Check Permission

```python
async def check_permission(
    client: OpenFgaClient,
    user_id: str,
    relation: str,
    object_type: str,
    object_id: str,
) -> bool:
    """Check if user has permission on object."""

    request = ClientCheckRequest(
        user=f"user:{user_id}",
        relation=relation,
        object=f"{object_type}:{object_id}",
    )

    response = await client.check(request)
    return response.allowed


# Usage
can_view = await check_permission(
    client,
    user_id="alice",
    relation="viewer",
    object_type="vulnerability",
    object_id="CVE-2024-1234",
)
```

---

## Write Relationship

```python
async def grant_permission(
    client: OpenFgaClient,
    user_id: str,
    relation: str,
    object_type: str,
    object_id: str,
) -> None:
    """Grant permission to user on object."""

    await client.write(
        writes=[
            ClientTuple(
                user=f"user:{user_id}",
                relation=relation,
                object=f"{object_type}:{object_id}",
            )
        ]
    )


# Grant editor access
await grant_permission(
    client,
    user_id="bob",
    relation="editor",
    object_type="vulnerability",
    object_id="CVE-2024-1234",
)
```

---

## Delete Relationship

```python
async def revoke_permission(
    client: OpenFgaClient,
    user_id: str,
    relation: str,
    object_type: str,
    object_id: str,
) -> None:
    """Revoke permission from user on object."""

    await client.write(
        deletes=[
            ClientTuple(
                user=f"user:{user_id}",
                relation=relation,
                object=f"{object_type}:{object_id}",
            )
        ]
    )
```

---

## List Objects User Can Access

```python
async def list_accessible_vulnerabilities(
    client: OpenFgaClient,
    user_id: str,
    relation: str = "viewer",
) -> list[str]:
    """List all vulnerabilities user can access."""

    response = await client.list_objects(
        user=f"user:{user_id}",
        relation=relation,
        type="vulnerability",
    )

    return [obj.replace("vulnerability:", "") for obj in response.objects]
```

---

## Authorization Decorator

```python
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def require_permission(
    relation: str,
    object_type: str,
    object_id_param: str = "object_id",
):
    """Decorator to require permission before executing function."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Get user from context
            user_id = get_current_user_id()
            object_id = kwargs.get(object_id_param)

            # Check permission
            client = await get_fga_client()
            allowed = await check_permission(
                client, user_id, relation, object_type, object_id
            )

            if not allowed:
                raise PermissionDeniedError(
                    f"User {user_id} cannot {relation} {object_type}:{object_id}"
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Usage
@require_permission("editor", "vulnerability")
async def update_vulnerability(object_id: str, data: dict) -> None:
    """Update vulnerability - requires editor permission."""
    ...
```

---

## Example: Vulnerability Management Authorization

```yaml
# Example authorization model for vulnerability management systems
model
  schema 1.1

type user

type organization
  relations
    define admin: [user]
    define security_analyst: [user]
    define developer: [user]
    define viewer: [user] or developer or security_analyst or admin

type vulnerability_report
  relations
    define org: [organization]
    define can_view: viewer from org
    define can_edit: security_analyst from org or admin from org
    define can_approve: admin from org
    define can_export: security_analyst from org or admin from org

type audit_log
  relations
    define org: [organization]
    define can_view: admin from org
```

---

## Docker Compose

```yaml
# docker-compose.yml
services:
  openfga:
    image: openfga/openfga:latest
    container_name: openfga
    ports:
      - "8080:8080"
      - "8081:8081"
    command: run
    environment:
      - OPENFGA_DATASTORE_ENGINE=postgres
      - OPENFGA_DATASTORE_URI=${OPENFGA_DATASTORE_URI}  # Set in .env
    depends_on:
      - postgres
```

---

## Testing

```python
@pytest.fixture
async def fga_client():
    client = await create_fga_client(api_url=settings.openfga_api_url)
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_permission_check(fga_client):
    # Setup
    await grant_permission(fga_client, "alice", "viewer", "vulnerability", "CVE-2024-1234")

    # Test
    can_view = await check_permission(
        fga_client, "alice", "viewer", "vulnerability", "CVE-2024-1234"
    )
    assert can_view is True

    cannot_edit = await check_permission(
        fga_client, "alice", "editor", "vulnerability", "CVE-2024-1234"
    )
    assert cannot_edit is False
```
