"""Domain exceptions for SIOPV.

All business logic exceptions inherit from SIOPVError.
"""

from typing import Any


class SIOPVError(Exception):
    """Base exception for all SIOPV errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# === Ingestion Errors ===


class IngestionError(SIOPVError):
    """Error during vulnerability ingestion."""


class TrivyParseError(IngestionError):
    """Failed to parse Trivy JSON report."""


class ValidationError(IngestionError):
    """Pydantic validation failed for vulnerability record."""


# === Enrichment Errors ===


class EnrichmentError(SIOPVError):
    """Error during context enrichment (RAG)."""


class ExternalAPIError(EnrichmentError):
    """Base error for external API operations."""


class APIClientError(ExternalAPIError):
    """External API call failed."""

    def __init__(
        self,
        message: str,
        api_name: str,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.api_name = api_name
        self.status_code = status_code
        super().__init__(message, details)


class RateLimitError(APIClientError):
    """Rate limit exceeded for external API."""

    def __init__(
        self,
        api_name: str,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(
            message=f"Rate limit exceeded for {api_name}",
            api_name=api_name,
            status_code=429,
            details=details,
        )


class CircuitBreakerOpenError(EnrichmentError):
    """Circuit breaker is open, API calls blocked."""


# === Classification Errors ===


class ClassificationError(SIOPVError):
    """Error during ML classification."""


class ModelNotFoundError(ClassificationError):
    """Trained ML model not found."""


class InferenceError(ClassificationError):
    """ML inference failed."""


# === Orchestration Errors ===


class OrchestrationError(SIOPVError):
    """Error in LangGraph orchestration."""


class CheckpointError(OrchestrationError):
    """Failed to save/restore checkpoint."""


class NodeExecutionError(OrchestrationError):
    """A graph node failed to execute."""


# === Authorization Errors ===


class AuthorizationError(SIOPVError):
    """Authorization check failed."""


class PermissionDeniedError(AuthorizationError):
    """User lacks permission for operation."""

    def __init__(
        self,
        user: str,
        resource: str,
        action: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.user = user
        self.resource = resource
        self.action = action
        super().__init__(
            message=f"Permission denied: {user} cannot {action} on {resource}",
            details=details,
        )


# === Privacy/DLP Errors ===


class PrivacyError(SIOPVError):
    """Error in DLP sanitization."""


class SensitiveDataDetectedError(PrivacyError):
    """Sensitive data found that could not be sanitized."""


# === Output Errors ===


class OutputError(SIOPVError):
    """Error generating output (Jira, PDF)."""


class JiraIntegrationError(OutputError):
    """Failed to create/update Jira ticket."""


class ReportGenerationError(OutputError):
    """Failed to generate PDF report."""


# === Security Errors ===


class SecurityError(SIOPVError):
    """Base error for security-related issues."""


class PathTraversalError(SecurityError):
    """Attempted path traversal detected."""


class IntegrityError(SecurityError):
    """Model or data integrity verification failed."""


class SchemaValidationError(SecurityError):
    """External data schema validation failed."""


# === Webhook Errors ===


class WebhookError(SIOPVError):
    """Base error for webhook operations."""


class WebhookAuthenticationError(WebhookError):
    """Webhook signature verification failed."""


class WebhookPayloadError(WebhookError):
    """Webhook payload is malformed or invalid."""
