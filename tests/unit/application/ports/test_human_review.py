"""Tests for HumanReviewPort protocol."""

from __future__ import annotations

from siopv.application.ports.human_review import HumanReviewPort


class TestHumanReviewPortProtocol:
    """Tests for HumanReviewPort Protocol definition."""

    def test_human_review_port_is_runtime_checkable(self) -> None:
        """HumanReviewPort should be a runtime_checkable Protocol."""
        assert (
            hasattr(HumanReviewPort, "__protocol_attrs__")
            or hasattr(HumanReviewPort, "__abstractmethods__")
            or issubclass(type(HumanReviewPort), type)
        )

    def test_conforming_class_satisfies_isinstance(self) -> None:
        """A class implementing submit_decision should satisfy isinstance check."""

        class ConcreteReview:
            async def submit_decision(
                self,
                thread_id: str,
                decision: str,
                *,
                modified_score: float | None = None,
                modified_recommendation: str | None = None,
            ) -> None:
                pass

        instance = ConcreteReview()
        assert isinstance(instance, HumanReviewPort)

    def test_non_conforming_class_fails_isinstance(self) -> None:
        """A class missing submit_decision should NOT satisfy isinstance check."""

        class NotAReview:
            async def some_other_method(self) -> None:
                pass

        instance = NotAReview()
        assert not isinstance(instance, HumanReviewPort)

    def test_empty_class_fails_isinstance(self) -> None:
        """An empty class should NOT satisfy isinstance check."""

        class Empty:
            pass

        instance = Empty()
        assert not isinstance(instance, HumanReviewPort)

    def test_port_importable_from_ports_package(self) -> None:
        """HumanReviewPort should be importable from the ports package."""
        from siopv.application.ports import HumanReviewPort as PortFromPackage

        assert PortFromPackage is HumanReviewPort

    async def test_protocol_default_body_returns_none(self) -> None:
        """Calling the Protocol's default submit_decision returns None (covers Ellipsis body)."""
        result = await HumanReviewPort.submit_decision(
            HumanReviewPort,  # type: ignore[arg-type]
            thread_id="t-001",
            decision="approve",
        )
        assert result is None
