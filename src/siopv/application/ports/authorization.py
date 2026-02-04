"""Port interfaces for OpenFGA authorization in SIOPV.

Defines the contracts for authorization service implementations.
Following hexagonal architecture, these ports define WHAT the application
needs for authorization, while adapters (in adapters/authorization/)
provide HOW it's implemented using OpenFGA.

Ports use typing.Protocol for structural subtyping, allowing any class
that implements the required methods to be used without inheritance.

Usage:
    from siopv.application.ports import AuthorizationPort, AuthorizationStorePort

    class MyService:
        def __init__(self, authz: AuthorizationPort) -> None:
            self._authz = authz

        async def do_something(self, user: UserId, resource: ResourceId) -> None:
            context = AuthorizationContext.for_action(
                user_id=user.value,
                resource=resource,
                action=Action.VIEW,
            )
            result = await self._authz.check(context)
            if not result.allowed:
                raise PermissionDeniedError(...)

OpenFGA SDK Reference (Context7 verified):
    - ClientCheckRequest: Single check request
    - ClientBatchCheckRequest/ClientBatchCheckItem: Batch checks
    - ClientWriteRequest/ClientTuple: Write/delete tuples
    - ReadRequestTupleKey: Query existing tuples
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from siopv.domain.authorization import (
        AuthorizationContext,
        AuthorizationResult,
        BatchAuthorizationResult,
        Relation,
        RelationshipTuple,
        ResourceId,
        UserId,
    )


@runtime_checkable
class AuthorizationPort(Protocol):
    """Port interface for checking authorization permissions.

    This port defines the contract for authorization check operations.
    Implementations will use OpenFGA's check and batch_check APIs.

    The port is designed to:
    - Accept domain entities (AuthorizationContext)
    - Return domain entities (AuthorizationResult)
    - Hide implementation details (OpenFGA SDK specifics)

    All methods are async to support non-blocking I/O with OpenFGA server.

    Example:
        async def check_user_access(
            authz: AuthorizationPort,
            user_id: str,
            project_id: str,
        ) -> bool:
            context = AuthorizationContext.for_action(
                user_id=user_id,
                resource=ResourceId.for_project(project_id),
                action=Action.VIEW,
            )
            result = await authz.check(context)
            return result.allowed
    """

    async def check(self, context: AuthorizationContext) -> AuthorizationResult:
        """Check if user can perform action on resource.

        This is the primary authorization method. It evaluates whether
        the user in the context has the required permission to perform
        the specified action on the resource.

        The implementation should:
        1. Resolve the action to the appropriate relation(s)
        2. Call OpenFGA check API
        3. Return a rich AuthorizationResult with audit metadata

        Args:
            context: AuthorizationContext containing:
                - user: The user requesting access (UserId)
                - resource: The resource being accessed (ResourceId)
                - action: The action to perform (Action)
                - direct_relation: Optional specific relation to check
                - contextual_tuples: Optional additional context tuples
                - authorization_model_id: Optional model version

        Returns:
            AuthorizationResult containing:
                - allowed: True if permission granted, False otherwise
                - context: The original context (for audit)
                - checked_relation: The relation that was evaluated
                - reason: Human-readable explanation
                - decision_id: UUID for audit tracking
                - check_duration_ms: Performance metric

        Raises:
            AuthorizationCheckError: If the check cannot be performed
                (e.g., OpenFGA unreachable, invalid model).
            AuthorizationModelError: If the authorization model is invalid
                or not found.
            StoreNotFoundError: If the OpenFGA store is not configured.

        Note:
            This method should NOT raise PermissionDeniedError. Instead,
            it returns AuthorizationResult with allowed=False. The caller
            is responsible for raising PermissionDeniedError if needed.

        Performance:
            Single check latency should be < 10ms for local OpenFGA,
            < 50ms for remote. Consider batch_check for multiple checks.
        """
        ...

    async def batch_check(
        self,
        contexts: list[AuthorizationContext],
    ) -> BatchAuthorizationResult:
        """Check multiple permissions at once.

        Performs multiple authorization checks in a single request,
        which is more efficient than calling check() multiple times.

        The implementation should use OpenFGA's batch_check API,
        which evaluates all checks in parallel on the server.

        Args:
            contexts: List of AuthorizationContext objects to check.
                Each context specifies a user, resource, and action.
                Maximum recommended batch size: 100 (OpenFGA limit).

        Returns:
            BatchAuthorizationResult containing:
                - results: List of AuthorizationResult (one per context)
                - batch_id: UUID for the batch operation
                - total_duration_ms: Total time for all checks
                - all_allowed: True if ALL checks passed
                - any_denied: True if ANY check was denied

        Raises:
            AuthorizationCheckError: If any check cannot be performed.
            AuthorizationModelError: If the authorization model is invalid.
            StoreNotFoundError: If the OpenFGA store is not configured.
            ValueError: If contexts list is empty or exceeds max size.

        Note:
            The order of results matches the order of input contexts.
            If any individual check fails (error, not denial), the
            entire batch operation may fail.

        Example:
            contexts = [
                AuthorizationContext.for_action(user, resource1, Action.VIEW),
                AuthorizationContext.for_action(user, resource2, Action.EDIT),
            ]
            result = await authz.batch_check(contexts)
            if result.any_denied:
                denied = result.get_denied_results()
                # Handle denials

        Performance:
            Batch operations are ~3-5x faster than individual checks
            due to reduced network overhead and parallel evaluation.
        """
        ...

    async def check_relation(
        self,
        user: UserId,
        relation: Relation,
        resource: ResourceId,
    ) -> AuthorizationResult:
        """Check if user has a specific relation to resource.

        This is a convenience method for direct relation checks,
        bypassing action-to-relation mapping.

        Args:
            user: The user to check
            relation: The specific relation to verify
            resource: The resource to check against

        Returns:
            AuthorizationResult with the check outcome.

        Raises:
            AuthorizationCheckError: If the check cannot be performed.
            InvalidRelationError: If the relation is invalid for the
                resource type.

        Example:
            result = await authz.check_relation(
                user=UserId(value="alice"),
                relation=Relation.OWNER,
                resource=ResourceId.for_project("siopv"),
            )
            if result.allowed:
                # User is an owner
        """
        ...

    async def list_user_relations(
        self,
        user: UserId,
        resource: ResourceId,
    ) -> list[Relation]:
        """List all relations a user has to a resource.

        Returns all relations the user has to the specified resource.
        Useful for building UI that shows user's permissions.

        Args:
            user: The user to query
            resource: The resource to check

        Returns:
            List of Relation enums the user has to the resource.
            Empty list if user has no relations.

        Raises:
            AuthorizationCheckError: If the query cannot be performed.

        Note:
            This method may require multiple OpenFGA calls internally.
            Consider caching results if called frequently.
        """
        ...


@runtime_checkable
class AuthorizationStorePort(Protocol):
    """Port interface for managing authorization relationship tuples.

    This port defines the contract for administrative operations on
    the authorization store. These operations modify the authorization
    state by creating or deleting relationship tuples.

    Implementations will use OpenFGA's write and read APIs.

    Security Note:
        Operations through this port modify authorization state.
        Callers must verify they have appropriate permissions
        before invoking these methods (admin/owner level).

    Example:
        async def grant_access(
            store: AuthorizationStorePort,
            user_id: str,
            project_id: str,
        ) -> None:
            tuple = RelationshipTuple.create(
                user_id=user_id,
                relation=Relation.VIEWER,
                resource_type=ResourceType.PROJECT,
                resource_id=project_id,
            )
            await store.write_tuple(tuple)
    """

    async def write_tuple(self, relationship: RelationshipTuple) -> None:
        """Create a new relationship tuple.

        Writes a single relationship tuple to the authorization store.
        This grants the specified relation from the user to the resource.

        Args:
            relationship: RelationshipTuple to create, containing:
                - user: The user being granted the relation (UserId)
                - relation: The relation being granted (Relation)
                - resource: The resource the relation applies to (ResourceId)
                - condition_context: Optional context for conditional tuples

        Raises:
            TupleValidationError: If the tuple is invalid according to
                the authorization model (e.g., invalid relation for type).
            AuthorizationStoreError: If the write operation fails.
            StoreNotFoundError: If the OpenFGA store is not configured.

        Idempotency:
            Writing the same tuple twice is idempotent - no error is
            raised if the tuple already exists.

        Example:
            tuple = RelationshipTuple.create(
                user_id="alice",
                relation=Relation.OWNER,
                resource_type=ResourceType.PROJECT,
                resource_id="my-project",
            )
            await store.write_tuple(tuple)
        """
        ...

    async def write_tuples(self, tuples: list[RelationshipTuple]) -> None:
        """Create multiple relationship tuples atomically.

        Writes multiple tuples in a single transaction. Either all
        tuples are written or none are (atomic operation).

        Args:
            tuples: List of RelationshipTuple objects to create.
                Maximum batch size: 100 (OpenFGA transaction limit).

        Raises:
            TupleValidationError: If any tuple is invalid.
            AuthorizationStoreError: If the write operation fails.
            StoreNotFoundError: If the OpenFGA store is not configured.
            ValueError: If tuples list is empty or exceeds max size.

        Atomicity:
            All tuples are written in a single transaction. If any
            tuple fails validation, the entire operation is rolled back.

        Example:
            tuples = [
                RelationshipTuple.create("alice", Relation.OWNER, ...),
                RelationshipTuple.create("bob", Relation.VIEWER, ...),
            ]
            await store.write_tuples(tuples)
        """
        ...

    async def delete_tuple(self, relationship: RelationshipTuple) -> None:
        """Remove a relationship tuple.

        Deletes a single relationship tuple from the authorization store.
        This revokes the specified relation from the user to the resource.

        Args:
            relationship: RelationshipTuple to delete. Only user, relation, and
                resource fields are used for matching.

        Raises:
            AuthorizationStoreError: If the delete operation fails.
            StoreNotFoundError: If the OpenFGA store is not configured.

        Idempotency:
            Deleting a non-existent tuple is idempotent - no error is
            raised if the tuple doesn't exist.

        Note:
            This only removes the direct tuple. Inherited relations
            (e.g., through organization membership) are not affected.
        """
        ...

    async def delete_tuples(self, tuples: list[RelationshipTuple]) -> None:
        """Remove multiple relationship tuples atomically.

        Deletes multiple tuples in a single transaction.

        Args:
            tuples: List of RelationshipTuple objects to delete.
                Maximum batch size: 100 (OpenFGA transaction limit).

        Raises:
            AuthorizationStoreError: If the delete operation fails.
            StoreNotFoundError: If the OpenFGA store is not configured.
            ValueError: If tuples list is empty or exceeds max size.
        """
        ...

    async def read_tuples(
        self,
        user: UserId | None = None,
        relation: Relation | None = None,
        resource: ResourceId | None = None,
    ) -> list[RelationshipTuple]:
        """Query existing relationship tuples with optional filters.

        Reads tuples from the store with optional filtering by user,
        relation, and/or resource. All filters are optional and combined
        with AND logic.

        Args:
            user: Optional filter by user. Returns all tuples where this
                user is the subject.
            relation: Optional filter by relation type. Returns all tuples
                with this specific relation.
            resource: Optional filter by resource. Returns all tuples for
                this resource. Can use partial matching:
                - Full: ResourceId.for_project("my-project")
                - Type only: ResourceId(ResourceType.PROJECT, "")

        Returns:
            List of RelationshipTuple objects matching the filters.
            Empty list if no matches found.

        Raises:
            AuthorizationStoreError: If the read operation fails.
            StoreNotFoundError: If the OpenFGA store is not configured.

        Note:
            With no filters, returns ALL tuples (may be large).
            Always use at least one filter in production.

        Examples:
            # All tuples for a user
            tuples = await store.read_tuples(user=UserId(value="alice"))

            # All owners of a project
            tuples = await store.read_tuples(
                relation=Relation.OWNER,
                resource=ResourceId.for_project("my-project"),
            )

            # Specific tuple existence check
            tuples = await store.read_tuples(
                user=UserId(value="alice"),
                relation=Relation.VIEWER,
                resource=ResourceId.for_project("my-project"),
            )
            exists = len(tuples) > 0
        """
        ...

    async def read_tuples_for_resource(
        self,
        resource: ResourceId,
    ) -> list[RelationshipTuple]:
        """Get all tuples for a specific resource.

        Convenience method to retrieve all relationships defined
        for a resource, regardless of user or relation type.

        Args:
            resource: The resource to query.

        Returns:
            List of all RelationshipTuple objects for the resource.

        Raises:
            AuthorizationStoreError: If the read operation fails.
        """
        ...

    async def read_tuples_for_user(
        self,
        user: UserId,
    ) -> list[RelationshipTuple]:
        """Get all tuples for a specific user.

        Convenience method to retrieve all relationships the user has,
        regardless of resource or relation type.

        Args:
            user: The user to query.

        Returns:
            List of all RelationshipTuple objects for the user.

        Raises:
            AuthorizationStoreError: If the read operation fails.
        """
        ...

    async def tuple_exists(
        self,
        user: UserId,
        relation: Relation,
        resource: ResourceId,
    ) -> bool:
        """Check if a specific tuple exists.

        Convenience method for existence checks without returning
        the full tuple data.

        Args:
            user: The user in the tuple.
            relation: The relation in the tuple.
            resource: The resource in the tuple.

        Returns:
            True if the tuple exists, False otherwise.

        Raises:
            AuthorizationStoreError: If the check fails.
        """
        ...


@runtime_checkable
class AuthorizationModelPort(Protocol):
    """Port interface for authorization model management.

    This port defines operations for managing the OpenFGA authorization
    model itself. These are administrative operations typically used
    during setup or schema migrations.

    Implementations will use OpenFGA's authorization model APIs.

    Note:
        Most applications won't need this port directly. It's primarily
        for tooling, testing, and administrative interfaces.
    """

    async def get_model_id(self) -> str:
        """Get the current authorization model ID.

        Returns:
            The ID of the currently active authorization model.

        Raises:
            AuthorizationModelError: If no model is configured.
            StoreNotFoundError: If the store is not found.
        """
        ...

    async def validate_model(self) -> bool:
        """Validate the current authorization model.

        Checks that the authorization model is valid and can be used
        for authorization checks.

        Returns:
            True if the model is valid, False otherwise.

        Raises:
            StoreNotFoundError: If the store is not found.
        """
        ...

    async def health_check(self) -> bool:
        """Check if the authorization service is healthy.

        Verifies connectivity to OpenFGA and basic functionality.

        Returns:
            True if the service is healthy, False otherwise.

        Note:
            This should be a lightweight check suitable for
            liveness/readiness probes.
        """
        ...


__all__ = [
    "AuthorizationModelPort",
    "AuthorizationPort",
    "AuthorizationStorePort",
]
