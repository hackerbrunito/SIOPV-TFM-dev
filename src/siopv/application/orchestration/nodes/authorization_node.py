"""Authorization gatekeeper node for LangGraph pipeline.

Handles Phase 5: Intercepts pipeline execution to verify user permissions
before processing sensitive operations. Implements Zero Trust access control
using OpenFGA ReBAC authorization.

Security principles:
- Fail-secure: If authorization service unavailable, DENY access (not allow)
- Explicit system execution: Anonymous access requires explicit flag
- PII protection: User identifiers are pseudonymized in logs

Per spec section 3.5:
- "El nodo Authorization_Gatekeeper intercepta cada request antes de
  ejecutar operaciones sensibles."
- "Se construye una query de autorización: check(user:X, relation:viewer, object:project:Y)"
- "Si allowed=true, la operación procede. Si allowed=false, se retorna
  403 Forbidden con audit log."
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import TYPE_CHECKING

import structlog

from siopv.domain.authorization import (
    Action,
    AuthorizationCheckError,
    AuthorizationContext,
    AuthorizationResult,
    ResourceId,
    ResourceType,
)

if TYPE_CHECKING:
    from siopv.application.orchestration.state import PipelineState
    from siopv.application.ports.authorization import AuthorizationPort

logger = structlog.get_logger(__name__)

# Default project ID when none provided - used for system-wide operations
DEFAULT_PROJECT_ID = "default"


class _LogEvent:
    """Structured log event names for authorization node."""

    STARTED = "authorization_node_started"
    SKIPPED_SYSTEM = "authorization_node_skipped_system_execution"
    DENIED_ANONYMOUS = "authorization_node_denied_anonymous"
    DENIED_NO_PORT = "authorization_node_denied_no_port"
    ALLOWED = "authorization_node_allowed"
    DENIED = "authorization_node_denied"
    CHECK_FAILED = "authorization_node_check_failed"
    FAILED = "authorization_node_failed"
    USING_DEFAULT = "authorization_node_using_default_project"
    PIPELINE_HALTED = "pipeline_halted_unauthorized"


def _create_error_state(
    error_msg: str,
    *,
    authorization_result: dict[str, object] | None = None,
    skipped: bool = False,
) -> dict[str, object]:
    """Create standardized error state for authorization failures.

    Args:
        error_msg: Error message to include in errors list
        authorization_result: Optional authorization result dict
        skipped: Whether authorization was skipped (default False)

    Returns:
        State dict with authorization_allowed=False
    """
    return {
        "authorization_allowed": False,
        "authorization_skipped": skipped,
        "authorization_result": authorization_result,
        "current_node": "authorize",
        "errors": [error_msg],
    }


def _create_success_state(
    *,
    authorization_result: dict[str, object] | None = None,
    skipped: bool = False,
) -> dict[str, object]:
    """Create standardized success state for authorization.

    Args:
        authorization_result: Optional authorization result dict
        skipped: Whether authorization was skipped (default False)

    Returns:
        State dict with authorization_allowed=True
    """
    return {
        "authorization_allowed": True,
        "authorization_skipped": skipped,
        "authorization_result": authorization_result,
        "current_node": "authorize",
    }


def _pseudonymize(value: str | None) -> str:
    """Pseudonymize a value using SHA-256 hash for GDPR compliance.

    Args:
        value: The value to pseudonymize (e.g., user_id)

    Returns:
        First 32 characters of SHA-256 hash, or "unknown" if value is None
    """
    if not value:
        return "unknown"
    return hashlib.sha256(value.encode()).hexdigest()[:32]


def _handle_anonymous_access(state: PipelineState) -> dict[str, object] | None:
    """Handle authorization when no user_id is provided.

    Args:
        state: Pipeline state to check for system_execution flag

    Returns:
        State dict if handled (allowed or denied), None if user_id exists
    """
    user_id = state.get("user_id")
    if user_id:
        return None  # Has user_id, not anonymous

    system_execution = state.get("system_execution", False)
    if system_execution:
        logger.info(
            _LogEvent.SKIPPED_SYSTEM,
            reason="Explicit system_execution flag set",
        )
        return _create_success_state(skipped=True)

    logger.warning(
        _LogEvent.DENIED_ANONYMOUS,
        reason="No user_id and system_execution not explicitly enabled",
    )
    return _create_error_state(
        "Authorization denied: anonymous access requires explicit system_execution flag"
    )


def _handle_no_port(user_id: str, project_id: str | None) -> dict[str, object]:
    """Handle fail-secure when no authorization port is configured.

    Args:
        user_id: User identifier (for logging, pseudonymized)
        project_id: Project identifier

    Returns:
        Error state with fail-secure denial
    """
    logger.error(
        _LogEvent.DENIED_NO_PORT,
        reason="No authorization_port configured - fail-secure denial",
        user_id_hash=_pseudonymize(user_id),
        project_id=project_id,
    )
    return _create_error_state(
        "Authorization denied: authorization service unavailable (fail-secure)"
    )


def _run_authorization_check(
    port: AuthorizationPort,
    context: AuthorizationContext,
) -> AuthorizationResult:
    """Run async authorization check in sync context.

    LangGraph nodes are synchronous, but the authorization port is async.
    This helper bridges the gap using asyncio.run().

    Args:
        port: Authorization port (async)
        context: Authorization context to check

    Returns:
        AuthorizationResult from the port

    Note:
        If called from an async context, the caller should use the async
        port.check() method directly instead of this helper.
    """
    return asyncio.run(port.check(context))


def _log_and_create_allowed_state(
    user_id: str,
    project_id: str,
    result: AuthorizationResult,
) -> dict[str, object]:
    """Log allowed authorization and create success state.

    Args:
        user_id: User identifier (pseudonymized in logs)
        project_id: Project identifier
        result: Authorization result from the check

    Returns:
        Success state dict with authorization details
    """
    logger.info(
        _LogEvent.ALLOWED,
        user_id_hash=_pseudonymize(user_id),
        project_id=project_id,
        action=Action.VIEW.value,
        decision_id=str(result.decision_id),
        duration_ms=result.check_duration_ms,
    )
    return _create_success_state(
        authorization_result={
            "allowed": True,
            "user_id_hash": _pseudonymize(user_id),
            "project_id": project_id,
            "action": Action.VIEW.value,
            "decision_id": str(result.decision_id),
            "checked_relation": result.checked_relation.value,
        },
    )


def _log_and_create_denied_state(
    user_id: str,
    project_id: str,
    result: AuthorizationResult,
) -> dict[str, object]:
    """Log denied authorization and create error state.

    Args:
        user_id: User identifier (pseudonymized in logs)
        project_id: Project identifier
        result: Authorization result from the check

    Returns:
        Error state dict with denial details
    """
    logger.warning(
        _LogEvent.DENIED,
        user_id_hash=_pseudonymize(user_id),
        project_id=project_id,
        action=Action.VIEW.value,
        decision_id=str(result.decision_id),
    )
    return _create_error_state(
        "Authorization denied: insufficient permissions",
        authorization_result={
            "allowed": False,
            "user_id_hash": _pseudonymize(user_id),
            "project_id": project_id,
            "action": Action.VIEW.value,
            "decision_id": str(result.decision_id),
            "reason": "User does not have permission to view this project",
        },
    )


def _execute_authorization_check(
    user_id: str,
    project_id: str,
    authorization_port: AuthorizationPort,
) -> dict[str, object]:
    """Execute the authorization check and return result state.

    Args:
        user_id: User identifier for the check
        project_id: Project identifier for the resource
        authorization_port: Port for authorization checks (OpenFGA adapter)

    Returns:
        State dict with authorization result (success or denial)
    """
    resource = ResourceId(
        resource_type=ResourceType.PROJECT,
        identifier=project_id,
    )
    context = AuthorizationContext.for_action(
        user_id=user_id,
        resource=resource,
        action=Action.VIEW,
    )
    result = _run_authorization_check(authorization_port, context)

    if result.allowed:
        return _log_and_create_allowed_state(user_id, project_id, result)
    return _log_and_create_denied_state(user_id, project_id, result)


def authorization_node(
    state: PipelineState,
    *,
    authorization_port: AuthorizationPort | None = None,
) -> dict[str, object]:
    """Execute authorization check as a LangGraph node (gatekeeper).

    This node implements the Authorization_Gatekeeper from spec section 3.5.
    It intercepts pipeline execution to verify the user has permission to
    process vulnerability reports before allowing subsequent operations.

    Authorization checks performed:
    - user can perform 'view' action on project resource
    - If authorization fails, pipeline halts with 403 error

    Args:
        state: Current pipeline state with user_id and project_id
        authorization_port: Port for authorization checks (OpenFGA adapter)

    Returns:
        State updates with authorization_result and authorization_allowed
    """
    logger.info(
        _LogEvent.STARTED,
        thread_id=state.get("thread_id"),
        user_id_hash=_pseudonymize(state.get("user_id")),
        project_id=state.get("project_id"),
    )

    # Handle anonymous access (no user_id)
    anonymous_result = _handle_anonymous_access(state)
    if anonymous_result is not None:
        return anonymous_result

    # Get context from state (user_id guaranteed non-None after anonymous check)
    user_id = state.get("user_id")
    if user_id is None:
        raise RuntimeError("user_id must exist after anonymous check")
    project_id = state.get("project_id") or DEFAULT_PROJECT_ID

    # Handle missing authorization port (fail-secure)
    if authorization_port is None:
        return _handle_no_port(user_id, project_id)

    if project_id == DEFAULT_PROJECT_ID:
        logger.debug(_LogEvent.USING_DEFAULT, project_id=project_id)

    # Delegate core logic with exception handling
    try:
        return _execute_authorization_check(user_id, project_id, authorization_port)
    except AuthorizationCheckError as e:
        logger.exception(
            _LogEvent.CHECK_FAILED,
            error_type=type(e).__name__,
            user_id_hash=_pseudonymize(user_id),
            project_id=project_id,
        )
        return _create_error_state("Authorization check failed: service error")
    except Exception as e:
        logger.exception(
            _LogEvent.FAILED,
            error_type=type(e).__name__,
        )
        return _create_error_state("Authorization node error: unexpected failure")


def route_after_authorization(state: dict[str, object]) -> str:
    """Conditional routing function after authorization node.

    Determines next node based on authorization result:
    - If authorized -> continue to ingest
    - If denied -> end pipeline

    Args:
        state: Current pipeline state dict with authorization_allowed

    Returns:
        Next node name: "ingest" or "end"
    """
    if state.get("authorization_allowed", False):
        return "ingest"
    user_id = state.get("user_id")
    logger.info(
        _LogEvent.PIPELINE_HALTED,
        user_id_hash=_pseudonymize(str(user_id) if user_id else None),
        project_id=state.get("project_id"),
    )
    return "end"


__all__ = [
    "authorization_node",
    "route_after_authorization",
]
