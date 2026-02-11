"""Domain entities for OpenFGA authorization in SIOPV.

These entities represent the core authorization concepts:
- AuthorizationContext: Input for a permission check
- AuthorizationResult: Output from a permission check
- RelationshipTuple: An OpenFGA tuple representing a relationship

Based on the Phase 5 spec:
- check(user:X, relation:viewer, object:project:Y)
- If allowed=true -> proceed; if allowed=false -> return 403 with audit log
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field

from siopv.domain.authorization.value_objects import (
    Action,
    Relation,
    ResourceId,
    ResourceType,
    UserId,
)


class RelationshipTuple(BaseModel):
    """Entity representing an OpenFGA relationship tuple.

    This is the fundamental unit of authorization in OpenFGA.
    A tuple expresses: "user U has relation R to object O"

    Example:
        user:alice, owner, project:siopv
        -> "user alice is an owner of project siopv"

    OpenFGA SDK format:
        ClientCheckRequest(
            user="user:alice",
            relation="owner",
            object="project:siopv",
        )
    """

    model_config = ConfigDict(frozen=True)

    user: UserId = Field(
        ...,
        description="The user in the relationship",
    )
    relation: Relation = Field(
        ...,
        description="The relation between user and object",
    )
    resource: ResourceId = Field(
        ...,
        description="The object/resource in the relationship",
    )
    # Optional condition context for conditional tuples
    condition_context: dict[str, Any] | None = Field(
        default=None,
        description="Optional context for conditional tuple evaluation",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this tuple was created",
    )

    @classmethod
    def from_openfga_tuple(
        cls,
        user: str,
        relation: str,
        obj: str,
        *,
        condition_context: dict[str, Any] | None = None,
    ) -> RelationshipTuple:
        """Create a RelationshipTuple from OpenFGA string format.

        Args:
            user: User string (e.g., "user:alice")
            relation: Relation string (e.g., "owner")
            obj: Object string (e.g., "project:siopv")
            condition_context: Optional context for conditions

        Returns:
            RelationshipTuple instance

        Raises:
            ValueError: If any component is invalid
        """
        return cls(
            user=UserId.from_string(user),
            relation=Relation(relation),
            resource=ResourceId.from_string(obj),
            condition_context=condition_context,
        )

    @classmethod
    def create(
        cls,
        user_id: str,
        relation: Relation,
        resource_type: ResourceType,
        resource_id: str,
    ) -> RelationshipTuple:
        """Convenience factory for creating tuples with separate components.

        Args:
            user_id: User identifier (without 'user:' prefix)
            relation: The relation type
            resource_type: Type of the resource
            resource_id: Resource identifier

        Returns:
            RelationshipTuple instance
        """
        return cls(
            user=UserId(value=user_id),
            relation=relation,
            resource=ResourceId(resource_type=resource_type, identifier=resource_id),
        )

    def to_openfga_dict(self) -> dict[str, str]:
        """Convert to OpenFGA API dictionary format.

        Returns:
            Dictionary with 'user', 'relation', 'object' keys
        """
        return {
            "user": self.user.to_openfga_format(),
            "relation": self.relation.value,
            "object": self.resource.to_openfga_format(),
        }

    def __str__(self) -> str:
        return f"({self.user}, {self.relation}, {self.resource})"

    def __hash__(self) -> int:
        return hash((self.user, self.relation, self.resource))


class AuthorizationContext(BaseModel):
    """Entity representing the context for an authorization check.

    This encapsulates all information needed to perform a permission check:
    - Who is requesting (user)
    - What resource they want to access
    - What action they want to perform

    Maps to OpenFGA check() call:
        check(user:X, relation:Y, object:Z)

    The relation is derived from the action using ActionPermissionMapping,
    or can be explicitly provided for direct relation checks.
    """

    model_config = ConfigDict(frozen=True)

    user: UserId = Field(
        ...,
        description="The user requesting access",
    )
    resource: ResourceId = Field(
        ...,
        description="The resource being accessed",
    )
    action: Action = Field(
        ...,
        description="The action the user wants to perform",
    )
    # Optional: direct relation check (bypasses action-to-relation mapping)
    direct_relation: Relation | None = Field(
        default=None,
        description="Optional: check for a specific relation directly",
    )
    # Contextual tuples for conditional evaluation
    contextual_tuples: Annotated[
        list[RelationshipTuple],
        Field(default_factory=list, description="Additional context tuples"),
    ]
    # Request metadata
    request_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this authorization request",
    )
    requested_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the authorization was requested",
    )
    # Optional authorization model ID for OpenFGA
    authorization_model_id: str | None = Field(
        default=None,
        description="Optional OpenFGA authorization model ID",
    )

    @classmethod
    def for_action(
        cls,
        user_id: str,
        resource: ResourceId,
        action: Action,
        *,
        contextual_tuples: list[RelationshipTuple] | None = None,
        authorization_model_id: str | None = None,
    ) -> AuthorizationContext:
        """Factory method for action-based authorization.

        Args:
            user_id: User identifier (without 'user:' prefix)
            resource: The resource being accessed
            action: The action to perform
            contextual_tuples: Optional additional context
            authorization_model_id: Optional OpenFGA model ID

        Returns:
            AuthorizationContext instance
        """
        return cls(
            user=UserId(value=user_id),
            resource=resource,
            action=action,
            contextual_tuples=contextual_tuples or [],
            authorization_model_id=authorization_model_id,
        )

    @classmethod
    def for_relation_check(
        cls,
        user_id: str,
        resource: ResourceId,
        relation: Relation,
        *,
        authorization_model_id: str | None = None,
    ) -> AuthorizationContext:
        """Factory method for direct relation checks.

        This bypasses action-to-relation mapping for cases where
        you want to check a specific relation directly.

        Args:
            user_id: User identifier (without 'user:' prefix)
            resource: The resource being accessed
            relation: The relation to check
            authorization_model_id: Optional OpenFGA model ID

        Returns:
            AuthorizationContext instance
        """
        # Use VIEW as placeholder action since we're doing direct relation check
        return cls(
            user=UserId(value=user_id),
            resource=resource,
            action=Action.VIEW,
            direct_relation=relation,
            contextual_tuples=[],
            authorization_model_id=authorization_model_id,
        )

    def to_openfga_check_request(self) -> dict[str, Any]:
        """Convert to OpenFGA ClientCheckRequest format.

        Note: The relation must be determined externally based on
        the action-to-relation mapping.

        Returns:
            Dictionary compatible with OpenFGA SDK
        """
        result: dict[str, Any] = {
            "user": self.user.to_openfga_format(),
            "object": self.resource.to_openfga_format(),
        }
        if self.contextual_tuples:
            result["contextual_tuples"] = [t.to_openfga_dict() for t in self.contextual_tuples]
        return result

    def __str__(self) -> str:
        return f"AuthzContext({self.user} -> {self.action} -> {self.resource})"


class AuthorizationResult(BaseModel):
    """Entity representing the result of an authorization check.

    Contains:
    - The decision (allowed/denied)
    - Reasoning for the decision
    - Audit metadata for compliance logging

    Per spec: "If allowed=false, return 403 Forbidden with audit log"
    """

    model_config = ConfigDict(frozen=True)

    # Core decision
    allowed: bool = Field(
        ...,
        description="Whether the authorization was granted",
    )
    # Context that was checked
    context: AuthorizationContext = Field(
        ...,
        description="The authorization context that was evaluated",
    )
    # Relation that was checked (resolved from action)
    checked_relation: Relation = Field(
        ...,
        description="The relation that was actually checked",
    )
    # Reasoning and metadata
    reason: str = Field(
        default="",
        description="Human-readable reason for the decision",
    )
    # Audit trail information
    decision_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this decision (audit purposes)",
    )
    decided_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the decision was made",
    )
    # Performance metadata
    check_duration_ms: Annotated[
        float,
        Field(ge=0.0, default=0.0, description="Time taken for the check in milliseconds"),
    ]
    # Additional metadata for auditing
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for audit logging",
    )

    @classmethod
    def allowed_result(
        cls,
        context: AuthorizationContext,
        checked_relation: Relation,
        *,
        reason: str = "Permission granted",
        check_duration_ms: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> AuthorizationResult:
        """Factory method for creating an allowed result.

        Args:
            context: The authorization context that was checked
            checked_relation: The relation that was verified
            reason: Human-readable reason
            check_duration_ms: Time taken for the check
            metadata: Additional audit metadata

        Returns:
            AuthorizationResult with allowed=True
        """
        return cls(
            allowed=True,
            context=context,
            checked_relation=checked_relation,
            reason=reason,
            check_duration_ms=check_duration_ms,
            metadata=metadata or {},
        )

    @classmethod
    def denied_result(
        cls,
        context: AuthorizationContext,
        checked_relation: Relation,
        *,
        reason: str = "Permission denied",
        check_duration_ms: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> AuthorizationResult:
        """Factory method for creating a denied result.

        Args:
            context: The authorization context that was checked
            checked_relation: The relation that was checked
            reason: Human-readable reason for denial
            check_duration_ms: Time taken for the check
            metadata: Additional audit metadata

        Returns:
            AuthorizationResult with allowed=False
        """
        return cls(
            allowed=False,
            context=context,
            checked_relation=checked_relation,
            reason=reason,
            check_duration_ms=check_duration_ms,
            metadata=metadata or {},
        )

    @classmethod
    def from_openfga_response(
        cls,
        context: AuthorizationContext,
        checked_relation: Relation,
        openfga_allowed: bool,
        *,
        check_duration_ms: float = 0.0,
    ) -> AuthorizationResult:
        """Create result from OpenFGA check response.

        Args:
            context: The authorization context that was checked
            checked_relation: The relation that was checked
            openfga_allowed: The 'allowed' field from OpenFGA response
            check_duration_ms: Time taken for the check

        Returns:
            AuthorizationResult instance
        """
        if openfga_allowed:
            return cls.allowed_result(
                context=context,
                checked_relation=checked_relation,
                reason=f"User has {checked_relation.value} relation",
                check_duration_ms=check_duration_ms,
            )
        return cls.denied_result(
            context=context,
            checked_relation=checked_relation,
            reason=f"User lacks {checked_relation.value} relation",
            check_duration_ms=check_duration_ms,
        )

    # Pydantic @computed_field + @property known mypy incompatibility
    @computed_field  # type: ignore[prop-decorator]
    @property
    def audit_log_entry(self) -> dict[str, Any]:
        """Generate a structured audit log entry with PII redaction.

        Returns:
            Dictionary suitable for audit logging (PII redacted by default)

        Note:
            For GDPR compliance, user identifiers are pseudonymized using
            SHA-256 hash truncated to 16 characters. Resource identifiers
            have their specific ID redacted while preserving the resource type.
            Use _build_audit_entry(include_pii=True) for internal debugging.
        """
        return self._build_audit_entry(include_pii=False)

    def _build_audit_entry(self, *, include_pii: bool = False) -> dict[str, Any]:
        """Build audit log entry with configurable PII handling.

        Args:
            include_pii: If True, include full user/resource identifiers.
                        If False (default), pseudonymize/redact PII.

        Returns:
            Dictionary suitable for audit logging
        """

        if include_pii:
            user_str = self.context.user.to_openfga_format()
            resource_str = self.context.resource.to_openfga_format()
        else:
            # Pseudonymize user ID using SHA-256 hash (first 16 chars)
            user_hash = hashlib.sha256(self.context.user.value.encode()).hexdigest()[:16]
            user_str = f"user:{user_hash}"
            # Redact resource identifier while preserving type for analytics
            resource_str = f"{self.context.resource.resource_type.value}:<redacted>"

        return {
            "decision_id": str(self.decision_id),
            "allowed": self.allowed,
            "user": user_str,
            "action": self.context.action.value,
            "resource": resource_str,
            "checked_relation": self.checked_relation.value,
            "reason": self.reason,
            "request_id": str(self.context.request_id),
            "requested_at": self.context.requested_at.isoformat(),
            "decided_at": self.decided_at.isoformat(),
            "check_duration_ms": self.check_duration_ms,
            **self.metadata,
        }

    def __str__(self) -> str:
        status = "ALLOWED" if self.allowed else "DENIED"
        user = self.context.user
        action = self.context.action
        resource = self.context.resource
        return f"AuthzResult({status}: {user} {action} {resource})"


class BatchAuthorizationResult(BaseModel):
    """Entity representing results of a batch authorization check.

    Used when checking multiple permissions at once (OpenFGA batch_check).
    """

    model_config = ConfigDict(frozen=True)

    results: list[AuthorizationResult] = Field(
        ...,
        description="List of individual authorization results",
    )
    batch_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this batch",
    )
    total_duration_ms: Annotated[
        float,
        Field(ge=0.0, default=0.0, description="Total time for batch check"),
    ]

    # Pydantic @computed_field + @property known mypy incompatibility
    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_allowed(self) -> bool:
        """Check if all authorizations in the batch were allowed."""
        return all(r.allowed for r in self.results)

    # Pydantic @computed_field + @property known mypy incompatibility
    @computed_field  # type: ignore[prop-decorator]
    @property
    def any_denied(self) -> bool:
        """Check if any authorization in the batch was denied."""
        return any(not r.allowed for r in self.results)

    @property
    def allowed_count(self) -> int:
        """Count of allowed results."""
        return sum(1 for r in self.results if r.allowed)

    @property
    def denied_count(self) -> int:
        """Count of denied results."""
        return sum(1 for r in self.results if not r.allowed)

    def get_denied_results(self) -> list[AuthorizationResult]:
        """Get all denied authorization results."""
        return [r for r in self.results if not r.allowed]

    def get_allowed_results(self) -> list[AuthorizationResult]:
        """Get all allowed authorization results."""
        return [r for r in self.results if r.allowed]

    def __str__(self) -> str:
        return f"BatchAuthzResult({self.allowed_count} allowed, {self.denied_count} denied)"


__all__ = [
    "AuthorizationContext",
    "AuthorizationResult",
    "BatchAuthorizationResult",
    "RelationshipTuple",
]
