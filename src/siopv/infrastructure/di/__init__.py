"""Dependency injection container for SIOPV infrastructure.

Provides factory functions for creating and configuring application components
that implement hexagonal architecture ports. This is the central place for
component wiring.

Usage:
    from siopv.infrastructure.di import (
        get_authorization_port,
        get_authorization_store_port,
        get_authorization_model_port,
        get_oidc_authentication_port,
        create_oidc_middleware,
    )
    from siopv.infrastructure.config import get_settings

    settings = get_settings()

    # Get ports from DI container
    authz = get_authorization_port(settings)
    store = get_authorization_store_port(settings)
    model = get_authorization_model_port(settings)
    oidc = get_oidc_authentication_port(settings)

    # Use in application code
    await authz.initialize()
    context = AuthorizationContext.for_action(user_id, resource, action)
    result = await authz.check(context)

    # OIDC authentication
    middleware = create_oidc_middleware(settings)
    identity = await middleware.authenticate(auth_header)
"""

from siopv.infrastructure.di.authentication import (
    create_oidc_adapter,
    create_oidc_middleware,
    get_oidc_authentication_port,
)
from siopv.infrastructure.di.authorization import (
    create_authorization_adapter,
    get_authorization_model_port,
    get_authorization_port,
    get_authorization_store_port,
)
from siopv.infrastructure.di.dlp import (
    get_dlp_port,
    get_dual_layer_dlp_port,
)
from siopv.infrastructure.di.output import (
    build_jira_adapter,
    build_metrics_exporter,
    build_pdf_adapter,
)

__all__ = [
    "build_jira_adapter",
    "build_metrics_exporter",
    "build_pdf_adapter",
    "create_authorization_adapter",
    "create_oidc_adapter",
    "create_oidc_middleware",
    "get_authorization_model_port",
    "get_authorization_port",
    "get_authorization_store_port",
    "get_dlp_port",
    "get_dual_layer_dlp_port",
    "get_oidc_authentication_port",
]
