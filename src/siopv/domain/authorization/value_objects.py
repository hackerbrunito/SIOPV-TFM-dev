"""Value objects for OpenFGA authorization in SIOPV.

These value objects represent the core concepts for ReBAC (Relationship-Based
Access Control) authorization as specified in Phase 5 of the SIOPV pipeline.

OpenFGA tuple format: (user, relation, object)
Example: user:alice, viewer, project:siopv
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Module-level regex patterns (outside classes to avoid Pydantic private attr issues)
_USER_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_@.\-]+$")
_RESOURCE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_:\-]+$")


class ResourceType(StrEnum):
    """Enum for resource types in the authorization model.

    These correspond to the "type" definitions in the OpenFGA model.
    Each type can have different relations defined.
    """

    PROJECT = "project"
    VULNERABILITY = "vulnerability"
    REPORT = "report"
    ORGANIZATION = "organization"

    def __str__(self) -> str:
        return self.value


class Relation(StrEnum):
    """Enum for relations in the ReBAC model.

    Relations define the relationship between a user and a resource.
    These map to OpenFGA relation definitions:
    - owner: Full control over the resource
    - viewer: Read-only access
    - analyst: Can analyze and modify vulnerability assessments
    - auditor: Can view and export audit trails

    Based on the spec: "User X can view vulnerabilities of project Y if owner"
    """

    OWNER = "owner"
    VIEWER = "viewer"
    ANALYST = "analyst"
    AUDITOR = "auditor"
    # Additional relations for organizational hierarchy
    MEMBER = "member"
    ADMIN = "admin"

    def __str__(self) -> str:
        return self.value


class Action(StrEnum):
    """Enum for actions that can be performed on resources.

    Actions are the operations that users can perform on resources.
    Authorization checks verify: can user X perform action Y on resource Z?

    These map to "can_*" computed relations in OpenFGA:
    - VIEW: can_view relation
    - EDIT: can_edit relation
    - REMEDIATE: can_remediate relation (analyst-level)
    - EXPORT: can_export relation (auditor-level)
    - DELETE: can_delete relation (owner-level)
    """

    VIEW = "view"
    EDIT = "edit"
    REMEDIATE = "remediate"
    EXPORT = "export"
    DELETE = "delete"
    # Additional actions for pipeline operations
    CLASSIFY = "classify"
    ESCALATE = "escalate"
    APPROVE = "approve"

    def __str__(self) -> str:
        return self.value


class UserId(BaseModel):
    """Value object representing a user identifier for OpenFGA.

    Format follows OpenFGA conventions: "user:<identifier>"
    The identifier can be a UUID, email, or any unique string.

    Example: user:81684243-9356-4421-8fbf-a4f8d36aa31b
    """

    model_config = ConfigDict(frozen=True)

    value: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="User identifier string",
    )

    @field_validator("value")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate user ID format."""
        if not _USER_ID_PATTERN.match(v):
            # Security: Generic message to avoid disclosing validation rules
            msg = "Invalid user ID format"
            raise ValueError(msg)
        return v

    @classmethod
    def from_string(cls, user_string: str) -> UserId:
        """Create UserId from a string, stripping 'user:' prefix if present.

        Args:
            user_string: User identifier, optionally with 'user:' prefix

        Returns:
            UserId instance
        """
        if user_string.startswith("user:"):
            return cls(value=user_string[5:])
        return cls(value=user_string)

    def to_openfga_format(self) -> str:
        """Return the OpenFGA-formatted user string.

        Returns:
            String in format 'user:<value>'
        """
        return f"user:{self.value}"

    def __str__(self) -> str:
        return self.to_openfga_format()

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UserId):
            return self.value == other.value
        return False


class ResourceId(BaseModel):
    """Value object representing a resource identifier for OpenFGA.

    Format follows OpenFGA conventions: "<type>:<identifier>"
    Example: project:siopv, vulnerability:CVE-2024-1234

    The resource ID combines the resource type with a unique identifier.
    """

    model_config = ConfigDict(frozen=True)

    resource_type: ResourceType = Field(
        ...,
        description="Type of the resource",
    )
    identifier: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Unique identifier within the resource type",
    )

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Validate resource identifier format."""
        if not _RESOURCE_ID_PATTERN.match(v):
            # Security: Generic message to avoid disclosing validation rules
            msg = "Invalid resource identifier format"
            raise ValueError(msg)
        return v

    @classmethod
    def from_string(cls, resource_string: str) -> ResourceId:
        """Create ResourceId from OpenFGA object string.

        Args:
            resource_string: String in format '<type>:<identifier>'

        Returns:
            ResourceId instance

        Raises:
            ValueError: If format is invalid or type is unknown
        """
        if ":" not in resource_string:
            msg = f"Invalid resource format: {resource_string}. Expected '<type>:<id>'"
            raise ValueError(msg)

        # Split only on first colon (identifiers may contain colons, e.g., CVE-2024-1234)
        type_str, identifier = resource_string.split(":", 1)

        try:
            resource_type = ResourceType(type_str)
        except ValueError as e:
            msg = f"Unknown resource type: {type_str}"
            raise ValueError(msg) from e

        return cls(resource_type=resource_type, identifier=identifier)

    @classmethod
    def for_project(cls, project_id: str) -> ResourceId:
        """Factory method for project resources.

        Args:
            project_id: Project identifier

        Returns:
            ResourceId for a project
        """
        return cls(resource_type=ResourceType.PROJECT, identifier=project_id)

    @classmethod
    def for_vulnerability(cls, cve_id: str) -> ResourceId:
        """Factory method for vulnerability resources.

        Args:
            cve_id: CVE identifier (e.g., CVE-2024-1234)

        Returns:
            ResourceId for a vulnerability
        """
        return cls(resource_type=ResourceType.VULNERABILITY, identifier=cve_id)

    @classmethod
    def for_report(cls, report_id: str) -> ResourceId:
        """Factory method for report resources.

        Args:
            report_id: Report identifier

        Returns:
            ResourceId for a report
        """
        return cls(resource_type=ResourceType.REPORT, identifier=report_id)

    def to_openfga_format(self) -> str:
        """Return the OpenFGA-formatted object string.

        Returns:
            String in format '<type>:<identifier>'
        """
        return f"{self.resource_type.value}:{self.identifier}"

    def __str__(self) -> str:
        return self.to_openfga_format()

    def __hash__(self) -> int:
        return hash((self.resource_type, self.identifier))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ResourceId):
            return self.resource_type == other.resource_type and self.identifier == other.identifier
        return False


class ActionPermissionMapping(BaseModel):
    """Value object mapping actions to required relations.

    This encapsulates the business logic of which relations grant which actions.
    Used by the authorization service to determine if a relation satisfies an action.
    """

    model_config = ConfigDict(frozen=True)

    action: Action = Field(..., description="The action to be performed")
    required_relations: Annotated[
        frozenset[Relation],
        Field(description="Relations that grant this action"),
    ]

    @classmethod
    def default_mappings(cls) -> dict[Action, ActionPermissionMapping]:
        """Return the default action-to-relation mappings.

        Returns:
            Dictionary mapping actions to their permission requirements

        Note:
            These mappings follow the principle of least privilege:
            - VIEW: viewer, analyst, auditor, owner
            - EDIT: analyst, owner
            - REMEDIATE: analyst, owner
            - EXPORT: auditor, owner
            - DELETE: owner only
            - CLASSIFY: analyst, owner
            - ESCALATE: analyst, owner
            - APPROVE: owner, admin
        """
        return {
            Action.VIEW: cls(
                action=Action.VIEW,
                required_relations=frozenset(
                    {
                        Relation.VIEWER,
                        Relation.ANALYST,
                        Relation.AUDITOR,
                        Relation.OWNER,
                        Relation.ADMIN,
                    }
                ),
            ),
            Action.EDIT: cls(
                action=Action.EDIT,
                required_relations=frozenset(
                    {
                        Relation.ANALYST,
                        Relation.OWNER,
                        Relation.ADMIN,
                    }
                ),
            ),
            Action.REMEDIATE: cls(
                action=Action.REMEDIATE,
                required_relations=frozenset(
                    {
                        Relation.ANALYST,
                        Relation.OWNER,
                    }
                ),
            ),
            Action.EXPORT: cls(
                action=Action.EXPORT,
                required_relations=frozenset(
                    {
                        Relation.AUDITOR,
                        Relation.OWNER,
                        Relation.ADMIN,
                    }
                ),
            ),
            Action.DELETE: cls(
                action=Action.DELETE,
                required_relations=frozenset({Relation.OWNER}),
            ),
            Action.CLASSIFY: cls(
                action=Action.CLASSIFY,
                required_relations=frozenset(
                    {
                        Relation.ANALYST,
                        Relation.OWNER,
                    }
                ),
            ),
            Action.ESCALATE: cls(
                action=Action.ESCALATE,
                required_relations=frozenset(
                    {
                        Relation.ANALYST,
                        Relation.OWNER,
                    }
                ),
            ),
            Action.APPROVE: cls(
                action=Action.APPROVE,
                required_relations=frozenset(
                    {
                        Relation.OWNER,
                        Relation.ADMIN,
                    }
                ),
            ),
        }


__all__ = [
    "Action",
    "ActionPermissionMapping",
    "Relation",
    "ResourceId",
    "ResourceType",
    "UserId",
]
