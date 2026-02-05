"""Authorization-specific domain exceptions for SIOPV.

These exceptions extend the base authorization errors in domain/exceptions.py
with more specific error types for the OpenFGA integration.

Per spec: "If allowed=false, return 403 Forbidden with audit log"
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from siopv.domain.exceptions import AuthorizationError

if TYPE_CHECKING:
    from siopv.domain.authorization.value_objects import (
        Action,
        Relation,
        ResourceId,
        ResourceType,
        UserId,
    )


class InvalidRelationError(AuthorizationError):
    """Raised when a relation is invalid for a given resource type.

    This occurs when trying to create a relationship that doesn't make
    sense according to the authorization model. For example, trying to
    assign the 'analyst' relation to an organization resource.
    """

    def __init__(
        self,
        relation: Relation,
        resource_type: ResourceType,
        *,
        allowed_relations: list[Relation] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize InvalidRelationError.

        Args:
            relation: The relation that was attempted
            resource_type: The resource type it was applied to
            allowed_relations: Optional list of valid relations for this type
            details: Additional error details
        """
        self.relation = relation
        self.resource_type = resource_type
        self.allowed_relations = allowed_relations or []

        # Security: Build message without exposing internal relation/resource details
        # Store details in attributes for internal debugging
        message = "Invalid relation for resource type"
        if self.allowed_relations:
            valid = ", ".join(r.value for r in self.allowed_relations)
            message += f". Valid relations: {valid}"

        super().__init__(message, details)


class InvalidResourceFormatError(AuthorizationError):
    """Raised when a resource identifier has an invalid format.

    OpenFGA resources must follow the format: <type>:<identifier>
    Example: project:siopv, vulnerability:CVE-2024-1234
    """

    def __init__(
        self,
        resource_string: str,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize InvalidResourceFormatError.

        Args:
            resource_string: The invalid resource string
            reason: Optional explanation of what's wrong
            details: Additional error details
        """
        self.resource_string = resource_string
        self.reason = reason

        # Security: Do not include user input in error message to prevent information disclosure
        message = "Invalid resource format"
        if reason:
            message += f". {reason}"

        super().__init__(message, details)


class InvalidUserFormatError(AuthorizationError):
    """Raised when a user identifier has an invalid format.

    User identifiers must contain only valid characters and follow
    the expected format for the authorization system.
    """

    def __init__(
        self,
        user_string: str,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize InvalidUserFormatError.

        Args:
            user_string: The invalid user string
            reason: Optional explanation of what's wrong
            details: Additional error details
        """
        self.user_string = user_string
        self.reason = reason

        # Security: Generic message to avoid disclosing user input
        message = "Invalid user format"
        if reason:
            message += f". {reason}"

        super().__init__(message, details)


class TupleValidationError(AuthorizationError):
    """Raised when a relationship tuple fails validation.

    This can occur when creating or writing tuples that don't
    conform to the authorization model's constraints.
    """

    def __init__(
        self,
        user: str,
        relation: str,
        resource: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize TupleValidationError.

        Args:
            user: The user in the tuple
            relation: The relation in the tuple
            resource: The resource in the tuple
            reason: Why the tuple is invalid
            details: Additional error details
        """
        self.user = user
        self.relation = relation
        self.resource = resource
        self.reason = reason

        # Security: Do not include user/relation/resource identifiers in error message
        # Store in attributes for internal debugging
        message = f"Invalid tuple: {reason}"
        super().__init__(message, details)


class AuthorizationCheckError(AuthorizationError):
    """Raised when an authorization check fails due to an error (not denial).

    This is different from PermissionDeniedError - this is for when the
    check itself couldn't be performed (e.g., OpenFGA unreachable).
    """

    def __init__(
        self,
        user: UserId | str,
        action: Action | str,
        resource: ResourceId | str,
        reason: str,
        *,
        underlying_error: Exception | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize AuthorizationCheckError.

        Args:
            user: The user being checked
            action: The action being checked
            resource: The resource being checked
            reason: Why the check failed
            underlying_error: Optional underlying exception
            details: Additional error details
        """
        self.user_str = str(user)
        self.action_str = str(action)
        self.resource_str = str(resource)
        self.reason = reason
        self.underlying_error = underlying_error

        # Security: Do not include user/resource identifiers in error message
        # Store in attributes for internal debugging
        message = f"Authorization check failed: {reason}"
        if underlying_error:
            message += f" (caused by: {type(underlying_error).__name__})"

        super().__init__(message, details)


class AuthorizationModelError(AuthorizationError):
    """Raised when there's an issue with the authorization model.

    This includes errors like:
    - Model not found
    - Model schema invalid
    - Model version mismatch
    """

    def __init__(
        self,
        model_id: str | None,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize AuthorizationModelError.

        Args:
            model_id: The authorization model ID (if known)
            reason: Why the error occurred
            details: Additional error details
        """
        self.model_id = model_id
        self.reason = reason

        if model_id:
            message = f"Authorization model error (model: {model_id}): {reason}"
        else:
            message = f"Authorization model error: {reason}"

        super().__init__(message, details)


class StoreNotFoundError(AuthorizationError):
    """Raised when the OpenFGA store is not found or not configured."""

    def __init__(
        self,
        store_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize StoreNotFoundError.

        Args:
            store_id: The store ID that wasn't found
            details: Additional error details
        """
        self.store_id = store_id

        if store_id:
            message = f"OpenFGA store not found: {store_id}"
        else:
            message = "OpenFGA store not configured"

        super().__init__(message, details)


class ActionNotMappedError(AuthorizationError):
    """Raised when an action has no relation mapping.

    This occurs when trying to check authorization for an action
    that hasn't been mapped to any relations in the permission model.
    """

    def __init__(
        self,
        action: Action,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize ActionNotMappedError.

        Args:
            action: The action that has no mapping
            details: Additional error details
        """
        self.action = action

        message = f"Action '{action.value}' has no relation mapping defined"
        super().__init__(message, details)


__all__ = [
    "ActionNotMappedError",
    "AuthorizationCheckError",
    "AuthorizationModelError",
    "InvalidRelationError",
    "InvalidResourceFormatError",
    "InvalidUserFormatError",
    "StoreNotFoundError",
    "TupleValidationError",
]
