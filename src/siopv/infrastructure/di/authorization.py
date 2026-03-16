"""Dependency injection container for authorization components.

Factory functions for creating and configuring authorization components
that implement the Authorization ports. Following Python 2026 standards with
proper type hints, structlog logging, and dependency injection patterns.

Usage:
    from siopv.infrastructure.di.authorization import (
        create_authorization_adapter,
        get_authorization_port,
        get_authorization_store_port,
        get_authorization_model_port,
    )

    # Get ports from factory functions (no settings argument needed)
    authz_port = get_authorization_port()
    store_port = get_authorization_store_port()
    model_port = get_authorization_model_port()

    # Or directly create the adapter
    adapter = create_authorization_adapter()
    await adapter.initialize()

    # Use in application code
    context = AuthorizationContext.for_action(user_id, resource, action)
    result = await authz_port.check(context)
"""

from __future__ import annotations

from functools import lru_cache

import structlog

from siopv.adapters.authorization import OpenFGAAdapter
from siopv.application.ports import (
    AuthorizationModelPort,
    AuthorizationPort,
    AuthorizationStorePort,
)
from siopv.infrastructure.config import get_settings

logger = structlog.get_logger(__name__)


@lru_cache(maxsize=1)
def create_authorization_adapter() -> OpenFGAAdapter:
    """Create and initialize OpenFGA authorization adapter.

    Factory function that creates a properly configured OpenFGAAdapter instance
    with settings and logging. The adapter implements all three authorization
    ports (AuthorizationPort, AuthorizationStorePort, AuthorizationModelPort).

    Uses lru_cache(maxsize=1) to ensure all three port factory functions
    (get_authorization_port, get_authorization_store_port,
    get_authorization_model_port) share the same underlying adapter instance
    rather than each creating their own separate OpenFGAAdapter.

    The returned adapter requires calling initialize() before use:
        adapter = create_authorization_adapter()
        await adapter.initialize()

    Returns:
        Cached OpenFGAAdapter singleton shared across all port factories.

    Raises:
        StoreNotFoundError: If OpenFGA settings are incomplete.

    Example:
        >>> adapter = create_authorization_adapter()
        >>> await adapter.initialize()
        >>> result = await adapter.check(context)
    """
    settings = get_settings()
    logger.debug(
        "creating_authorization_adapter",
        api_url=settings.openfga_api_url,
        store_id=settings.openfga_store_id,
        auth_method=getattr(settings, "openfga_auth_method", "none"),
        model_id=getattr(settings, "openfga_authorization_model_id", None),
    )

    adapter = OpenFGAAdapter(settings)

    logger.info(
        "authorization_adapter_created",
        adapter_class="OpenFGAAdapter",
    )

    return adapter


@lru_cache(maxsize=1)
def get_authorization_port() -> AuthorizationPort:
    """Get the authorization port (permission checking) implementation.

    Lazy factory function that returns a singleton AuthorizationPort
    implementation. Uses lru_cache to ensure only one instance is created.

    The returned port implements the authorization checking contract:
    - check(): Single permission check
    - batch_check(): Multiple permission checks
    - check_relation(): Direct relation checking
    - list_user_relations(): List all user relations

    Returns:
        AuthorizationPort implementation (OpenFGAAdapter).

    Note:
        The port is not automatically initialized. The calling code must
        initialize the adapter before use if it's a new instance.

    Example:
        >>> port = get_authorization_port()
        >>> context = AuthorizationContext.for_action(user_id, resource, action)
        >>> result = await port.check(context)
    """
    adapter = create_authorization_adapter()
    logger.debug("authorization_port_created", port_type="AuthorizationPort")
    return adapter


@lru_cache(maxsize=1)
def get_authorization_store_port() -> AuthorizationStorePort:
    """Get the authorization store port (tuple management) implementation.

    Lazy factory function that returns a singleton AuthorizationStorePort
    implementation. Uses lru_cache to ensure only one instance is created.

    The returned port implements the tuple management contract:
    - write_tuple(): Create a relationship tuple
    - write_tuples(): Create multiple tuples atomically
    - delete_tuple(): Remove a tuple
    - delete_tuples(): Remove multiple tuples atomically
    - read_tuples(): Query tuples with optional filters
    - read_tuples_for_resource(): Get tuples for a resource
    - read_tuples_for_user(): Get tuples for a user
    - tuple_exists(): Check tuple existence

    Returns:
        AuthorizationStorePort implementation (OpenFGAAdapter).

    Note:
        The port is not automatically initialized. The calling code must
        initialize the adapter before use if it's a new instance.

    Example:
        >>> store = get_authorization_store_port()
        >>> tuple = RelationshipTuple.create(user_id, Relation.VIEWER, ...)
        >>> await store.write_tuple(tuple)
    """
    adapter = create_authorization_adapter()
    logger.debug("authorization_store_port_created", port_type="AuthorizationStorePort")
    return adapter


@lru_cache(maxsize=1)
def get_authorization_model_port() -> AuthorizationModelPort:
    """Get the authorization model port (model management) implementation.

    Lazy factory function that returns a singleton AuthorizationModelPort
    implementation. Uses lru_cache to ensure only one instance is created.

    The returned port implements the model management contract:
    - get_model_id(): Retrieve current model ID
    - validate_model(): Validate current model
    - health_check(): Check service health

    Returns:
        AuthorizationModelPort implementation (OpenFGAAdapter).

    Note:
        The port is not automatically initialized. The calling code must
        initialize the adapter before use if it's a new instance.

    Example:
        >>> model_port = get_authorization_model_port()
        >>> model_id = await model_port.get_model_id()
    """
    adapter = create_authorization_adapter()
    logger.debug("authorization_model_port_created", port_type="AuthorizationModelPort")
    return adapter


__all__ = [
    "create_authorization_adapter",
    "get_authorization_model_port",
    "get_authorization_port",
    "get_authorization_store_port",
]
