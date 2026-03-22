"""Dependency injection container for SIOPV infrastructure.

Provides factory functions for creating and configuring application components
that implement hexagonal architecture ports. This is the central place for
component wiring.

Sub-port factories (``create_oidc_adapter``, ``create_oidc_middleware``,
``get_oidc_authentication_port``, ``create_authorization_adapter``,
``get_authorization_model_port``, ``get_authorization_store_port``,
``get_dlp_port``) are public API for integration testing and component-level
wiring. The CLI entry point uses higher-level wrappers (``get_authorization_port``,
``get_dual_layer_dlp_port``), but the granular factories are intentionally
exported for tests that need to construct individual Phase 5/6 components
without full pipeline wiring.

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
from siopv.infrastructure.di.enrichment import (
    build_epss_client,
    build_github_client,
    build_llm_analysis,
    build_nvd_client,
    build_osint_client,
    build_vector_store,
)
from siopv.infrastructure.di.ml import (
    build_classifier,
    build_feature_engineer,
    build_trivy_parser,
)
from siopv.infrastructure.di.orchestration import (
    EscalationConfig,
    build_escalation_config,
    build_threshold_config,
)
from siopv.infrastructure.di.output import (
    build_jira_adapter,
    build_metrics_exporter,
    build_pdf_adapter,
)
from siopv.infrastructure.di.pipeline import build_pipeline_ports
from siopv.infrastructure.di.webhook import build_webhook_receiver

__all__ = [
    "EscalationConfig",
    "build_classifier",
    "build_epss_client",
    "build_escalation_config",
    "build_feature_engineer",
    "build_github_client",
    "build_jira_adapter",
    "build_llm_analysis",
    "build_metrics_exporter",
    "build_nvd_client",
    "build_osint_client",
    "build_pdf_adapter",
    "build_pipeline_ports",
    "build_threshold_config",
    "build_trivy_parser",
    "build_vector_store",
    "build_webhook_receiver",
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
