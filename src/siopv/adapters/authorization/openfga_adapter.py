"""OpenFGA adapter implementing authorization port interfaces.

Provides a single adapter class that implements all three authorization ports:
- AuthorizationPort: Check permissions (check, batch_check, check_relation, list_user_relations)
- AuthorizationStorePort: Manage tuples (write_tuple, write_tuples, delete_tuple, etc.)
- AuthorizationModelPort: Model management (get_model_id, validate_model, health_check)

Context7 Verified OpenFGA SDK patterns:
- ClientCheckRequest for single checks
- ClientBatchCheckRequest/ClientBatchCheckItem for batch checks
- ClientWriteRequest/ClientTuple for write/delete operations
- ReadRequestTupleKey for reading tuples

Based on spec Phase 5: check(user:X, relation:viewer, object:project:Y)
If allowed=true -> proceed; if allowed=false -> return 403 with audit log
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import structlog
from openfga_sdk import ClientConfiguration, OpenFgaClient, ReadRequestTupleKey
from openfga_sdk.client.models import (
    ClientBatchCheckItem,
    ClientBatchCheckRequest,
    ClientCheckRequest,
    ClientTuple,
    ClientWriteRequest,
)
from openfga_sdk.exceptions import FgaValidationException
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from siopv.application.ports import (
    AuthorizationModelPort,
    AuthorizationPort,
    AuthorizationStorePort,
)
from siopv.domain.authorization import (
    ActionNotMappedError,
    ActionPermissionMapping,
    AuthorizationCheckError,
    AuthorizationContext,
    AuthorizationModelError,
    AuthorizationResult,
    BatchAuthorizationResult,
    Relation,
    RelationshipTuple,
    ResourceId,
    StoreNotFoundError,
    TupleValidationError,
    UserId,
)
from siopv.infrastructure.resilience import CircuitBreaker, CircuitBreakerError

if TYPE_CHECKING:
    from siopv.infrastructure.config.settings import Settings

logger = structlog.get_logger(__name__)

# Maximum batch size for OpenFGA operations
MAX_BATCH_SIZE = 100


class OpenFGAAdapterError(Exception):
    """Base error for OpenFGA adapter operations."""


class OpenFGAAdapter(AuthorizationPort, AuthorizationStorePort, AuthorizationModelPort):
    """OpenFGA adapter implementing all authorization ports.

    Features:
    - Async operations using OpenFGA Python SDK
    - Circuit breaker for fault tolerance
    - Retry with exponential backoff
    - Comprehensive error mapping to domain exceptions
    - Structured logging with audit metadata

    Usage:
        adapter = OpenFGAAdapter(settings)
        await adapter.initialize()

        # Check permission
        result = await adapter.check(context)
        if not result.allowed:
            raise PermissionDeniedError(...)

        # Write tuple
        await adapter.write_tuple(relationship)

        # Cleanup
        await adapter.close()
    """

    def __init__(
        self,
        settings: Settings,
        *,
        client: OpenFgaClient | None = None,
    ) -> None:
        """Initialize OpenFGA adapter.

        Args:
            settings: Application settings with OpenFGA configuration
            client: Optional pre-configured OpenFGA client (for testing)
        """
        self._api_url = settings.openfga_api_url
        self._store_id = settings.openfga_store_id

        # Circuit breaker for fault tolerance
        self._circuit_breaker = CircuitBreaker(
            "openfga",
            failure_threshold=settings.circuit_breaker_failure_threshold,
            recovery_timeout=settings.circuit_breaker_recovery_timeout,
        )

        # External client (for testing) or owned client
        self._external_client = client
        self._owned_client: OpenFgaClient | None = None

        # Action-to-relation mappings
        self._action_mappings = ActionPermissionMapping.default_mappings()

        # Model ID cache
        self._cached_model_id: str | None = None

        logger.info(
            "openfga_adapter_initialized",
            api_url=self._api_url,
            store_id=self._store_id,
        )

    async def initialize(self) -> None:
        """Initialize the OpenFGA client connection.

        Must be called before using the adapter. Creates the OpenFGA client
        with the configured store and model settings.

        Raises:
            StoreNotFoundError: If store_id or api_url is not configured.
        """
        if not self._api_url:
            raise StoreNotFoundError(details={"reason": "OpenFGA API URL not configured"})

        if not self._store_id:
            raise StoreNotFoundError(details={"reason": "OpenFGA store ID not configured"})

        if self._external_client:
            # Using injected client (testing)
            logger.debug("openfga_using_external_client")
            return

        configuration = ClientConfiguration(
            api_url=self._api_url,
            store_id=self._store_id,
        )

        self._owned_client = OpenFgaClient(configuration)
        await self._owned_client.__aenter__()

        logger.info(
            "openfga_client_connected",
            api_url=self._api_url,
            store_id=self._store_id,
        )

    async def close(self) -> None:
        """Close the OpenFGA client connection.

        Should be called when the adapter is no longer needed.
        """
        if self._owned_client:
            await self._owned_client.__aexit__(None, None, None)
            await self._owned_client.close()
            self._owned_client = None
            logger.info("openfga_client_closed")

    async def _get_client(self) -> OpenFgaClient:
        """Get the OpenFGA client instance.

        Returns:
            Configured OpenFgaClient instance.

        Raises:
            StoreNotFoundError: If client is not initialized.
        """
        if self._external_client:
            return self._external_client

        if self._owned_client is None:
            raise StoreNotFoundError(
                details={"reason": "OpenFGA client not initialized. Call initialize() first."}
            )

        return self._owned_client

    def _resolve_relation_for_action(self, context: AuthorizationContext) -> Relation:
        """Resolve the relation to check based on the action or direct relation.

        Args:
            context: Authorization context with action or direct_relation.

        Returns:
            The relation to check.

        Raises:
            ActionNotMappedError: If action has no relation mapping.
        """
        # Direct relation takes precedence
        if context.direct_relation:
            return context.direct_relation

        # Look up action mapping
        mapping = self._action_mappings.get(context.action)
        if not mapping or not mapping.required_relations:
            raise ActionNotMappedError(context.action)

        # Return first required relation (primary permission)
        # The OpenFGA model should define computed relations like can_view
        # For now, we check against the first required relation
        return next(iter(mapping.required_relations))

    def _domain_tuple_to_client_tuple(self, relationship: RelationshipTuple) -> ClientTuple:
        """Convert domain RelationshipTuple to OpenFGA ClientTuple.

        Args:
            relationship: Domain relationship tuple.

        Returns:
            OpenFGA ClientTuple for API calls.
        """
        return ClientTuple(
            user=relationship.user.to_openfga_format(),
            relation=relationship.relation.value,
            object=relationship.resource.to_openfga_format(),
        )

    def _client_tuple_to_domain_tuple(
        self,
        user: str,
        relation: str,
        obj: str,
    ) -> RelationshipTuple:
        """Convert OpenFGA tuple response to domain RelationshipTuple.

        Args:
            user: OpenFGA user string (e.g., "user:alice").
            relation: Relation string (e.g., "viewer").
            obj: Object string (e.g., "project:siopv").

        Returns:
            Domain RelationshipTuple instance.
        """
        return RelationshipTuple.from_openfga_tuple(user, relation, obj)

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )  # type: ignore[misc]
    async def _execute_check(
        self,
        client: OpenFgaClient,
        user: str,
        relation: str,
        obj: str,
        contextual_tuples: list[ClientTuple] | None = None,
    ) -> bool:
        """Execute a single authorization check with retry logic.

        Args:
            client: OpenFGA client instance.
            user: User in OpenFGA format.
            relation: Relation to check.
            obj: Object in OpenFGA format.
            contextual_tuples: Optional contextual tuples.

        Returns:
            True if allowed, False otherwise.
        """
        request = ClientCheckRequest(
            user=user,
            relation=relation,
            object=obj,
        )

        if contextual_tuples:
            request.contextual_tuples = contextual_tuples

        options: dict[str, Any] = {}
        if self._cached_model_id:
            options["authorization_model_id"] = self._cached_model_id

        response = await client.check(request, options)
        return bool(response.allowed)

    # ========================================================================
    # AuthorizationPort Implementation
    # ========================================================================

    async def check(self, context: AuthorizationContext) -> AuthorizationResult:
        """Check if user can perform action on resource.

        Args:
            context: AuthorizationContext with user, resource, action.

        Returns:
            AuthorizationResult with allowed status and audit metadata.

        Raises:
            AuthorizationCheckError: If check cannot be performed.
            AuthorizationModelError: If model is invalid.
            StoreNotFoundError: If store is not configured.
        """
        start_time = time.perf_counter()

        try:
            client = await self._get_client()
            relation = self._resolve_relation_for_action(context)

            # Build contextual tuples if present
            contextual_tuples: list[ClientTuple] | None = None
            if context.contextual_tuples:
                contextual_tuples = [
                    self._domain_tuple_to_client_tuple(t) for t in context.contextual_tuples
                ]

            # Execute check with circuit breaker
            async with self._circuit_breaker:
                allowed = await self._execute_check(
                    client,
                    context.user.to_openfga_format(),
                    relation.value,
                    context.resource.to_openfga_format(),
                    contextual_tuples,
                )

            duration_ms = (time.perf_counter() - start_time) * 1000

            result = AuthorizationResult.from_openfga_response(
                context=context,
                checked_relation=relation,
                openfga_allowed=allowed,
                check_duration_ms=duration_ms,
            )

        except StoreNotFoundError:
            raise

        except ActionNotMappedError:
            raise

        except CircuitBreakerError as e:
            logger.warning(
                "authorization_circuit_open",
                user=context.user.value,
                action=context.action.value,
            )
            raise AuthorizationCheckError(
                user=context.user,
                action=context.action,
                resource=context.resource,
                reason="Authorization service unavailable (circuit breaker open)",
                underlying_error=e,
            ) from e

        except FgaValidationException as e:
            logger.exception(
                "authorization_validation_error",
                error=str(e),
            )
            raise AuthorizationModelError(
                model_id=self._cached_model_id,
                reason=f"OpenFGA validation error: {e}",
            ) from e

        except Exception as e:
            logger.exception(
                "authorization_check_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise AuthorizationCheckError(
                user=context.user,
                action=context.action,
                resource=context.resource,
                reason=f"Unexpected error during authorization check: {e}",
                underlying_error=e,
            ) from e
        else:
            logger.info(
                "authorization_check_completed",
                allowed=allowed,
                user=context.user.value,
                action=context.action.value,
                resource=str(context.resource),
                relation=relation.value,
                duration_ms=duration_ms,
            )

            return result

    def _build_batch_check_items(
        self,
        contexts: list[AuthorizationContext],
    ) -> tuple[list[ClientBatchCheckItem], list[Relation]]:
        """Build batch check items from contexts.

        Args:
            contexts: List of authorization contexts.

        Returns:
            Tuple of (check_items, relation_map).
        """
        check_items: list[ClientBatchCheckItem] = []
        relation_map: list[Relation] = []

        for ctx in contexts:
            relation = self._resolve_relation_for_action(ctx)
            relation_map.append(relation)

            item = ClientBatchCheckItem(
                user=ctx.user.to_openfga_format(),
                relation=relation.value,
                object=ctx.resource.to_openfga_format(),
            )

            if ctx.contextual_tuples:
                item.contextual_tuples = [
                    self._domain_tuple_to_client_tuple(t) for t in ctx.contextual_tuples
                ]

            check_items.append(item)

        return check_items, relation_map

    def _process_batch_response(
        self,
        response: Any,
        contexts: list[AuthorizationContext],
        relation_map: list[Relation],
        total_duration_ms: float,
    ) -> list[AuthorizationResult]:
        """Process batch check response into results.

        Args:
            response: OpenFGA batch check response.
            contexts: Original authorization contexts.
            relation_map: Map of relations for each context.
            total_duration_ms: Total duration of the batch check.

        Returns:
            List of AuthorizationResult objects.
        """
        results: list[AuthorizationResult] = []

        if hasattr(response, "result") and response.result:
            for i, check_result in enumerate(response.result):
                if i < len(contexts):
                    result = AuthorizationResult.from_openfga_response(
                        context=contexts[i],
                        checked_relation=relation_map[i],
                        openfga_allowed=bool(check_result.allowed),
                        check_duration_ms=total_duration_ms / len(contexts),
                    )
                    results.append(result)
        else:
            # Fallback: iterate response as iterable
            for _i, (ctx, relation, check_result) in enumerate(
                zip(contexts, relation_map, response, strict=False)
            ):
                allowed = getattr(check_result, "allowed", False)
                result = AuthorizationResult.from_openfga_response(
                    context=ctx,
                    checked_relation=relation,
                    openfga_allowed=bool(allowed),
                    check_duration_ms=total_duration_ms / len(contexts),
                )
                results.append(result)

        return results

    async def batch_check(
        self,
        contexts: list[AuthorizationContext],
    ) -> BatchAuthorizationResult:
        """Check multiple permissions at once.

        Args:
            contexts: List of AuthorizationContext objects to check.

        Returns:
            BatchAuthorizationResult with results for each context.

        Raises:
            AuthorizationCheckError: If any check cannot be performed.
            ValueError: If contexts is empty or exceeds max size.
        """
        if not contexts:
            msg = "contexts list cannot be empty"
            raise ValueError(msg)

        if len(contexts) > MAX_BATCH_SIZE:
            msg = f"contexts list exceeds maximum batch size of {MAX_BATCH_SIZE}"
            raise ValueError(msg)

        start_time = time.perf_counter()

        try:
            client = await self._get_client()

            # Build batch check items
            check_items, relation_map = self._build_batch_check_items(contexts)

            # Execute batch check with circuit breaker
            options: dict[str, Any] = {}
            if self._cached_model_id:
                options["authorization_model_id"] = self._cached_model_id

            async with self._circuit_breaker:
                batch_request = ClientBatchCheckRequest(checks=check_items)
                response = await client.batch_check(batch_request, options)

            total_duration_ms = (time.perf_counter() - start_time) * 1000

            # Process response into results
            results = self._process_batch_response(
                response, contexts, relation_map, total_duration_ms
            )

            batch_result = BatchAuthorizationResult(
                results=results,
                total_duration_ms=total_duration_ms,
            )

        except (StoreNotFoundError, ActionNotMappedError, ValueError):
            raise

        except CircuitBreakerError as e:
            logger.warning("batch_authorization_circuit_open")
            raise AuthorizationCheckError(
                user="batch",
                action="batch_check",
                resource="multiple",
                reason="Authorization service unavailable (circuit breaker open)",
                underlying_error=e,
            ) from e

        except Exception as e:
            logger.exception(
                "batch_authorization_check_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise AuthorizationCheckError(
                user="batch",
                action="batch_check",
                resource="multiple",
                reason=f"Batch check failed: {e}",
                underlying_error=e,
            ) from e
        else:
            logger.info(
                "batch_authorization_check_completed",
                total=len(contexts),
                allowed=batch_result.allowed_count,
                denied=batch_result.denied_count,
                duration_ms=total_duration_ms,
            )

            return batch_result

    async def check_relation(
        self,
        user: UserId,
        relation: Relation,
        resource: ResourceId,
    ) -> AuthorizationResult:
        """Check if user has a specific relation to resource.

        Args:
            user: The user to check.
            relation: The specific relation to verify.
            resource: The resource to check against.

        Returns:
            AuthorizationResult with the check outcome.

        Raises:
            AuthorizationCheckError: If check cannot be performed.
        """
        context = AuthorizationContext.for_relation_check(
            user_id=user.value,
            resource=resource,
            relation=relation,
        )

        # Override to use the specified relation directly
        start_time = time.perf_counter()

        try:
            client = await self._get_client()

            async with self._circuit_breaker:
                allowed = await self._execute_check(
                    client,
                    user.to_openfga_format(),
                    relation.value,
                    resource.to_openfga_format(),
                )

            duration_ms = (time.perf_counter() - start_time) * 1000

            return AuthorizationResult.from_openfga_response(
                context=context,
                checked_relation=relation,
                openfga_allowed=allowed,
                check_duration_ms=duration_ms,
            )

        except CircuitBreakerError as e:
            raise AuthorizationCheckError(
                user=user,
                action="check_relation",
                resource=resource,
                reason="Authorization service unavailable",
                underlying_error=e,
            ) from e

        except Exception as e:
            raise AuthorizationCheckError(
                user=user,
                action="check_relation",
                resource=resource,
                reason=f"Relation check failed: {e}",
                underlying_error=e,
            ) from e

    async def list_user_relations(
        self,
        user: UserId,
        resource: ResourceId,
    ) -> list[Relation]:
        """List all relations a user has to a resource.

        Args:
            user: The user to query.
            resource: The resource to check.

        Returns:
            List of Relation enums the user has to the resource.

        Raises:
            AuthorizationCheckError: If query cannot be performed.
        """
        relations_found: list[Relation] = []

        try:
            # Check each possible relation
            for relation in Relation:
                try:
                    result = await self.check_relation(user, relation, resource)
                    if result.allowed:
                        relations_found.append(relation)
                except AuthorizationCheckError:
                    # Skip relations that fail to check (may not be valid for resource type)
                    continue

        except Exception as e:
            logger.exception(
                "list_user_relations_failed",
                user=user.value,
                resource=str(resource),
                error=str(e),
            )
            raise AuthorizationCheckError(
                user=user,
                action="list_relations",
                resource=resource,
                reason=f"Failed to list user relations: {e}",
                underlying_error=e,
            ) from e
        else:
            logger.debug(
                "list_user_relations_completed",
                user=user.value,
                resource=str(resource),
                relations=[r.value for r in relations_found],
            )

            return relations_found

    # ========================================================================
    # AuthorizationStorePort Implementation
    # ========================================================================

    async def write_tuple(self, relationship: RelationshipTuple) -> None:
        """Create a new relationship tuple.

        Args:
            relationship: RelationshipTuple to create.

        Raises:
            TupleValidationError: If tuple is invalid.
            AuthorizationCheckError: If write fails.
        """
        try:
            client = await self._get_client()
            client_tuple = self._domain_tuple_to_client_tuple(relationship)

            body = ClientWriteRequest(writes=[client_tuple])
            options: dict[str, Any] = {}
            if self._cached_model_id:
                options["authorization_model_id"] = self._cached_model_id

            async with self._circuit_breaker:
                await client.write(body, options)

            logger.info(
                "tuple_written",
                user=relationship.user.value,
                relation=relationship.relation.value,
                resource=str(relationship.resource),
            )

        except FgaValidationException as e:
            logger.exception(
                "tuple_validation_error",
                error=str(e),
            )
            raise TupleValidationError(
                user=relationship.user.to_openfga_format(),
                relation=relationship.relation.value,
                resource=relationship.resource.to_openfga_format(),
                reason=str(e),
            ) from e

        except CircuitBreakerError as e:
            raise AuthorizationCheckError(
                user=relationship.user,
                action="write_tuple",
                resource=relationship.resource,
                reason="Authorization service unavailable",
                underlying_error=e,
            ) from e

        except Exception as e:
            logger.exception(
                "tuple_write_failed",
                error=str(e),
            )
            raise AuthorizationCheckError(
                user=relationship.user,
                action="write_tuple",
                resource=relationship.resource,
                reason=f"Failed to write tuple: {e}",
                underlying_error=e,
            ) from e

    async def write_tuples(self, tuples: list[RelationshipTuple]) -> None:
        """Create multiple relationship tuples atomically.

        Args:
            tuples: List of RelationshipTuple objects to create.

        Raises:
            TupleValidationError: If any tuple is invalid.
            AuthorizationCheckError: If write fails.
            ValueError: If tuples list is empty or exceeds max size.
        """
        if not tuples:
            msg = "tuples list cannot be empty"
            raise ValueError(msg)

        if len(tuples) > MAX_BATCH_SIZE:
            msg = f"tuples list exceeds maximum batch size of {MAX_BATCH_SIZE}"
            raise ValueError(msg)

        try:
            client = await self._get_client()
            client_tuples = [self._domain_tuple_to_client_tuple(t) for t in tuples]

            body = ClientWriteRequest(writes=client_tuples)
            options: dict[str, Any] = {}
            if self._cached_model_id:
                options["authorization_model_id"] = self._cached_model_id

            async with self._circuit_breaker:
                await client.write(body, options)

            logger.info(
                "tuples_written",
                count=len(tuples),
            )

        except FgaValidationException as e:
            raise TupleValidationError(
                user="batch",
                relation="batch",
                resource="batch",
                reason=f"Batch write validation failed: {e}",
            ) from e

        except CircuitBreakerError as e:
            raise AuthorizationCheckError(
                user="batch",
                action="write_tuples",
                resource="batch",
                reason="Authorization service unavailable",
                underlying_error=e,
            ) from e

        except Exception as e:
            raise AuthorizationCheckError(
                user="batch",
                action="write_tuples",
                resource="batch",
                reason=f"Batch write failed: {e}",
                underlying_error=e,
            ) from e

    async def delete_tuple(self, relationship: RelationshipTuple) -> None:
        """Remove a relationship tuple.

        Args:
            relationship: RelationshipTuple to delete.

        Raises:
            AuthorizationCheckError: If delete fails.
        """
        try:
            client = await self._get_client()
            client_tuple = self._domain_tuple_to_client_tuple(relationship)

            body = ClientWriteRequest(deletes=[client_tuple])
            options: dict[str, Any] = {}
            if self._cached_model_id:
                options["authorization_model_id"] = self._cached_model_id

            async with self._circuit_breaker:
                await client.write(body, options)

            logger.info(
                "tuple_deleted",
                user=relationship.user.value,
                relation=relationship.relation.value,
                resource=str(relationship.resource),
            )

        except CircuitBreakerError as e:
            raise AuthorizationCheckError(
                user=relationship.user,
                action="delete_tuple",
                resource=relationship.resource,
                reason="Authorization service unavailable",
                underlying_error=e,
            ) from e

        except Exception as e:
            logger.exception(
                "tuple_delete_failed",
                error=str(e),
            )
            raise AuthorizationCheckError(
                user=relationship.user,
                action="delete_tuple",
                resource=relationship.resource,
                reason=f"Failed to delete tuple: {e}",
                underlying_error=e,
            ) from e

    async def delete_tuples(self, tuples: list[RelationshipTuple]) -> None:
        """Remove multiple relationship tuples atomically.

        Args:
            tuples: List of RelationshipTuple objects to delete.

        Raises:
            AuthorizationCheckError: If delete fails.
            ValueError: If tuples list is empty or exceeds max size.
        """
        if not tuples:
            msg = "tuples list cannot be empty"
            raise ValueError(msg)

        if len(tuples) > MAX_BATCH_SIZE:
            msg = f"tuples list exceeds maximum batch size of {MAX_BATCH_SIZE}"
            raise ValueError(msg)

        try:
            client = await self._get_client()
            client_tuples = [self._domain_tuple_to_client_tuple(t) for t in tuples]

            body = ClientWriteRequest(deletes=client_tuples)
            options: dict[str, Any] = {}
            if self._cached_model_id:
                options["authorization_model_id"] = self._cached_model_id

            async with self._circuit_breaker:
                await client.write(body, options)

            logger.info(
                "tuples_deleted",
                count=len(tuples),
            )

        except CircuitBreakerError as e:
            raise AuthorizationCheckError(
                user="batch",
                action="delete_tuples",
                resource="batch",
                reason="Authorization service unavailable",
                underlying_error=e,
            ) from e

        except Exception as e:
            raise AuthorizationCheckError(
                user="batch",
                action="delete_tuples",
                resource="batch",
                reason=f"Batch delete failed: {e}",
                underlying_error=e,
            ) from e

    async def read_tuples(
        self,
        user: UserId | None = None,
        relation: Relation | None = None,
        resource: ResourceId | None = None,
    ) -> list[RelationshipTuple]:
        """Query existing relationship tuples with optional filters.

        Args:
            user: Optional filter by user.
            relation: Optional filter by relation type.
            resource: Optional filter by resource.

        Returns:
            List of RelationshipTuple objects matching the filters.

        Raises:
            AuthorizationCheckError: If read fails.
        """
        try:
            client = await self._get_client()

            # Build read request tuple key
            tuple_key = ReadRequestTupleKey()
            if user:
                tuple_key.user = user.to_openfga_format()
            if relation:
                tuple_key.relation = relation.value
            if resource:
                tuple_key.object = resource.to_openfga_format()

            async with self._circuit_breaker:
                response = await client.read(tuple_key)

            # Convert response tuples to domain objects
            result: list[RelationshipTuple] = []
            if hasattr(response, "tuples") and response.tuples:
                for tuple_obj in response.tuples:
                    if hasattr(tuple_obj, "key"):
                        key = tuple_obj.key
                        domain_tuple = self._client_tuple_to_domain_tuple(
                            user=key.user,
                            relation=key.relation,
                            obj=key.object,
                        )
                        result.append(domain_tuple)

        except CircuitBreakerError as e:
            raise AuthorizationCheckError(
                user=user if user else "filter",
                action="read_tuples",
                resource=resource if resource else "filter",
                reason="Authorization service unavailable",
                underlying_error=e,
            ) from e

        except Exception as e:
            logger.exception(
                "tuples_read_failed",
                error=str(e),
            )
            raise AuthorizationCheckError(
                user=user if user else "filter",
                action="read_tuples",
                resource=resource if resource else "filter",
                reason=f"Failed to read tuples: {e}",
                underlying_error=e,
            ) from e
        else:
            logger.debug(
                "tuples_read",
                count=len(result),
                user_filter=user.value if user else None,
                relation_filter=relation.value if relation else None,
                resource_filter=str(resource) if resource else None,
            )

            return result

    async def read_tuples_for_resource(
        self,
        resource: ResourceId,
    ) -> list[RelationshipTuple]:
        """Get all tuples for a specific resource.

        Args:
            resource: The resource to query.

        Returns:
            List of all RelationshipTuple objects for the resource.

        Raises:
            AuthorizationCheckError: If read fails.
        """
        return await self.read_tuples(resource=resource)

    async def read_tuples_for_user(
        self,
        user: UserId,
    ) -> list[RelationshipTuple]:
        """Get all tuples for a specific user.

        Args:
            user: The user to query.

        Returns:
            List of all RelationshipTuple objects for the user.

        Raises:
            AuthorizationCheckError: If read fails.
        """
        return await self.read_tuples(user=user)

    async def tuple_exists(
        self,
        user: UserId,
        relation: Relation,
        resource: ResourceId,
    ) -> bool:
        """Check if a specific tuple exists.

        Args:
            user: The user in the tuple.
            relation: The relation in the tuple.
            resource: The resource in the tuple.

        Returns:
            True if the tuple exists, False otherwise.

        Raises:
            AuthorizationCheckError: If check fails.
        """
        tuples = await self.read_tuples(user=user, relation=relation, resource=resource)
        return len(tuples) > 0

    # ========================================================================
    # AuthorizationModelPort Implementation
    # ========================================================================

    async def get_model_id(self) -> str:
        """Get the current authorization model ID.

        Returns:
            The ID of the currently active authorization model.

        Raises:
            AuthorizationModelError: If no model is configured.
            StoreNotFoundError: If store is not found.
        """
        try:
            client = await self._get_client()

            async with self._circuit_breaker:
                response = await client.read_authorization_models()

            if not response.authorization_models:
                raise AuthorizationModelError(  # noqa: TRY301
                    model_id=None,
                    reason="No authorization models found in store",
                )

        except StoreNotFoundError:
            raise

        except AuthorizationModelError:
            raise

        except CircuitBreakerError as e:
            raise AuthorizationModelError(
                model_id=None,
                reason="Authorization service unavailable",
                details={"underlying_error": str(e)},
            ) from e

        except Exception as e:
            raise AuthorizationModelError(
                model_id=None,
                reason=f"Failed to get model ID: {e}",
            ) from e
        else:
            # Get the most recent model (first in list)
            model = response.authorization_models[0]
            model_id: str = str(model.id)
            self._cached_model_id = model_id

            logger.debug(
                "model_id_retrieved",
                model_id=model_id,
            )

            return model_id

    async def validate_model(self) -> bool:
        """Validate the current authorization model.

        Returns:
            True if the model is valid, False otherwise.

        Raises:
            StoreNotFoundError: If store is not found.
        """
        try:
            model_id = await self.get_model_id()

        except AuthorizationModelError:
            return False

        except StoreNotFoundError:
            raise
        else:
            # If we can retrieve the model ID, the model is valid
            return model_id is not None

    async def health_check(self) -> bool:
        """Check if the authorization service is healthy.

        Returns:
            True if the service is healthy, False otherwise.
        """
        try:
            client = await self._get_client()

            # Try to read authorization models as a health check
            async with self._circuit_breaker:
                await client.read_authorization_models()

        except Exception as e:
            logger.warning(
                "openfga_health_check_failed",
                error=str(e),
            )
            return False
        else:
            logger.debug("openfga_health_check_passed")
            return True


__all__ = [
    "OpenFGAAdapter",
    "OpenFGAAdapterError",
]
