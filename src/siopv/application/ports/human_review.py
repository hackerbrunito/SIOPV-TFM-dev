"""Port interface for human review in SIOPV Phase 7.

Defines the contract for human review decision submission.
Following hexagonal architecture (Ports & Adapters pattern).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class HumanReviewPort(Protocol):
    """Port interface for submitting human review decisions.

    This port defines the contract for human review operations
    in the HITL (Human-in-the-Loop) workflow. Implementations
    will handle persisting decisions and resuming the pipeline.
    """

    async def submit_decision(
        self,
        thread_id: str,
        decision: str,
        *,
        modified_score: float | None = None,
        modified_recommendation: str | None = None,
    ) -> None:
        """Submit a human review decision for an escalated case.

        Args:
            thread_id: The pipeline thread ID for the escalated case
            decision: One of "approve", "reject", or "modify"
            modified_score: Override risk score (only when decision == "modify")
            modified_recommendation: Override recommendation (only when decision == "modify")

        Raises:
            ValueError: If decision is not one of the allowed values
            ValueError: If decision is "modify" but no modifications provided
        """
        ...


__all__ = [
    "HumanReviewPort",
]
