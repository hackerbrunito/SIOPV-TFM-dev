"""Tests for Phase 7 HITL fields in PipelineState."""

from __future__ import annotations

import json

from siopv.application.orchestration.state import create_initial_state


class TestPipelineStateHITLFields:
    """Tests for Phase 7 Human-in-the-Loop fields in PipelineState."""

    def test_create_initial_state_has_hitl_defaults(self) -> None:
        """create_initial_state() should include all Phase 7 fields with correct defaults."""
        state = create_initial_state()

        assert state["escalation_required"] is False
        assert state["human_decision"] is None
        assert state["human_modified_score"] is None
        assert state["human_modified_recommendation"] is None
        assert state["escalation_timestamp"] is None
        assert state["escalation_level"] == 0
        assert state["review_deadline"] is None

    def test_pipeline_state_accepts_hitl_fields(self) -> None:
        """PipelineState TypedDict should accept all Phase 7 field values."""
        state = create_initial_state()

        # Simulate setting Phase 7 fields as the escalation node would
        state["escalation_required"] = True
        state["human_decision"] = "approve"
        state["human_modified_score"] = 8.5
        state["human_modified_recommendation"] = "Patch immediately"
        state["escalation_timestamp"] = "2026-03-17T10:30:00Z"
        state["escalation_level"] = 2
        state["review_deadline"] = "2026-03-18T10:30:00Z"

        assert state["escalation_required"] is True
        assert state["human_decision"] == "approve"
        assert state["human_modified_score"] == 8.5
        assert state["human_modified_recommendation"] == "Patch immediately"
        assert state["escalation_timestamp"] == "2026-03-17T10:30:00Z"
        assert state["escalation_level"] == 2
        assert state["review_deadline"] == "2026-03-18T10:30:00Z"

    def test_hitl_fields_are_json_serializable(self) -> None:
        """All Phase 7 fields must be JSON-serializable for LangGraph checkpointing."""
        state = create_initial_state()

        # Extract only Phase 7 fields
        hitl_fields = {
            "escalation_required": state["escalation_required"],
            "human_decision": state["human_decision"],
            "human_modified_score": state["human_modified_score"],
            "human_modified_recommendation": state["human_modified_recommendation"],
            "escalation_timestamp": state["escalation_timestamp"],
            "escalation_level": state["escalation_level"],
            "review_deadline": state["review_deadline"],
        }

        # json.dumps should not raise for JSON-serializable values
        serialized = json.dumps(hitl_fields)
        deserialized = json.loads(serialized)

        assert deserialized == hitl_fields

    def test_full_state_json_round_trip(self) -> None:
        """The full initial state (including HITL) should survive JSON round-trip."""
        state = create_initial_state(thread_id="test-thread-1")

        # Remove non-serializable fields (VulnerabilityRecord, EnrichmentData, etc.)
        # Test only the scalar/primitive fields for JSON round-trip
        serializable_subset = {
            k: v
            for k, v in state.items()
            if k
            in {
                "escalation_required",
                "human_decision",
                "human_modified_score",
                "human_modified_recommendation",
                "escalation_timestamp",
                "escalation_level",
                "review_deadline",
                "thread_id",
                "current_node",
                "processed_count",
                "authorization_allowed",
                "authorization_skipped",
                "system_execution",
            }
        }

        serialized = json.dumps(serializable_subset)
        deserialized = json.loads(serialized)

        assert deserialized == serializable_subset

    def test_escalation_level_default_is_zero(self) -> None:
        """Default escalation_level should be 0 (no escalation)."""
        state = create_initial_state()

        assert state["escalation_level"] == 0
        assert isinstance(state["escalation_level"], int)

    def test_escalation_required_default_is_false(self) -> None:
        """Default escalation_required should be False."""
        state = create_initial_state()

        assert state["escalation_required"] is False
        assert isinstance(state["escalation_required"], bool)
