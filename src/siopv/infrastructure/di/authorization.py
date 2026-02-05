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
    from siopv.infrastructure.config import get_settings

    settings = get_settings()

    # Get ports from factory functions
    authz_port = get_authorization_port(settings)
    store_port = get_authorization_store_port(settings)
    model_port = get_authorization_model_port(settings)

    # Or directly create the adapter
    adapter = create_authorization_adapter(settings)
    await adapter.initialize()

    # Use in application code
    context = AuthorizationContext.for_action(user_id, resource, action)
    result = await authz_port.check(context)
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

import structlog

from siopv.adapters.authorization import OpenFGAAdapter
from siopv.application.ports import (
    AuthorizationModelPort,
    AuthorizationPort,
    AuthorizationStorePort,
)

if TYPE_CHECKING:
    from siopv.infrastructure.config.settings import Settings

logger = structlog.get_logger(__name__)


def create_authorization_adapter(settings: Settings) -> OpenFGAAdapter:
    """Create and initialize OpenFGA authorization adapter.

    Factory function that creates a properly configured OpenFGAAdapter instance
    with settings and logging. The adapter implements all three authorization
    ports (AuthorizationPort, AuthorizationStorePort, AuthorizationModelPort).

    The returned adapter requires calling initialize() before use:
        adapter = create_authorization_adapter(settings)
        await adapter.initialize()

    Args:
        settings: Application settings containing OpenFGA configuration:
            - openfga_api_url: Base URL for OpenFGA service
            - openfga_store_id: OpenFGA store identifier
            - circuit_breaker_failure_threshold: Failure threshold before opening
            - circuit_breaker_recovery_timeout: Timeout before recovery attempt

    Returns:
        Initialized OpenFGAAdapter instance ready for use.

    Raises:
        StoreNotFoundError: If OpenFGA settings are incomplete.

    Example:
        >>> settings = get_settings()
        >>> adapter = create_authorization_adapter(settings)
        >>> await adapter.initialize()
        >>> result = await adapter.check(context)
    """
    logger.debug(
        "creating_authorization_adapter",
        api_url=settings.openfga_api_url,
        store_id=settings.openfga_store_id,
    )

    adapter = OpenFGAAdapter(settings)

    logger.info(
        "authorization_adapter_created",
        adapter_class="OpenFGAAdapter",
    )

    return adapter


@lru_cache(maxsize=1)
def get_authorization_port(settings: Settings) -> AuthorizationPort:
    """Get the authorization port (permission checking) implementation.

    Lazy factory function that returns a singleton AuthorizationPort
    implementation. Uses lru_cache to ensure only one instance is created
    for a given settings object.

    The returned port implements the authorization checking contract:
    - check(): Single permission check
    - batch_check(): Multiple permission checks
    - check_relation(): Direct relation checking
    - list_user_relations(): List all user relations

    Args:
        settings: Application settings instance.

    Returns:
        AuthorizationPort implementation (OpenFGAAdapter).

    Note:
        The port is not automatically initialized. The calling code must
        initialize the adapter before use if it's a new instance.

    Example:
        >>> settings = get_settings()
        >>> port = get_authorization_port(settings)
        >>> context = AuthorizationContext.for_action(user_id, resource, action)
        >>> result = await port.check(context)
    """
    adapter = create_authorization_adapter(settings)
    logger.debug("authorization_port_created", port_type="AuthorizationPort")
    return adapter


@lru_cache(maxsize=1)
def get_authorization_store_port(settings: Settings) -> AuthorizationStorePort:
    """Get the authorization store port (tuple management) implementation.

    Lazy factory function that returns a singleton AuthorizationStorePort
    implementation. Uses lru_cache to ensure only one instance is created
    for a given settings object.

    The returned port implements the tuple management contract:
    - write_tuple(): Create a relationship tuple
    - write_tuples(): Create multiple tuples atomically
    - delete_tuple(): Remove a tuple
    - delete_tuples(): Remove multiple tuples atomically
    - read_tuples(): Query tuples with optional filters
    - read_tuples_for_resource(): Get tuples for a resource
    - read_tuples_for_user(): Get tuples for a user
    - tuple_exists(): Check tuple existence

    Args:
        settings: Application settings instance.

    Returns:
        AuthorizationStorePort implementation (OpenFGAAdapter).

    Note:
        The port is not automatically initialized. The calling code must
        initialize the adapter before use if it's a new instance.

    Example:
        >>> settings = get_settings()
        >>> store = get_authorization_store_port(settings)
        >>> tuple = RelationshipTuple.create(user_id, Relation.VIEWER, ...)
        >>> await store.write_tuple(tuple)
    """
    adapter = create_authorization_adapter(settings)
    logger.debug("authorization_store_port_created", port_type="AuthorizationStorePort")
    return adapter


@lru_cache(maxsize=1)
def get_authorization_model_port(settings: Settings) -> AuthorizationModelPort:
    """Get the authorization model port (model management) implementation.

    Lazy factory function that returns a singleton AuthorizationModelPort
    implementation. Uses lru_cache to ensure only one instance is created
    for a given settings object.

    The returned port implements the model management contract:
    - get_model_id(): Retrieve current model ID
    - validate_model(): Validate current model
    - health_check(): Check service health

    Args:
        settings: Application settings instance.

    Returns:
        AuthorizationModelPort implementation (OpenFGAAdapter).

    Note:
        The port is not automatically initialized. The calling code must
        initialize the adapter before use if it's a new instance.

    Example:
        >>> settings = get_settings()
        >>> model_port = get_authorization_model_port(settings)
        >>> model_id = await model_port.get_model_id()
    """
    adapter = create_authorization_adapter(settings)
    logger.debug("authorization_model_port_created", port_type="AuthorizationModelPort")
    return adapter


__all__ = [
    "create_authorization_adapter",
    "get_authorization_model_port",
    "get_authorization_port",
    "get_authorization_store_port",
]
