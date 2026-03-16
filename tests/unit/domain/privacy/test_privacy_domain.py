"""Unit tests for the privacy/DLP domain layer.

Covers: entities, value_objects, exceptions, and the __init__ re-exports.
Target coverage: >= 95%
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from siopv.domain.privacy import (
    DLPError,
    DLPResult,
    PIIDetection,
    PIIEntityType,
    SanitizationContext,
    SanitizationError,
)
from siopv.domain.privacy.exceptions import (
    PresidioUnavailableError,
    SemanticValidationError,
)

# ---------------------------------------------------------------------------
# PIIEntityType
# ---------------------------------------------------------------------------


class TestPIIEntityType:
    """Tests for the PIIEntityType StrEnum."""

    def test_all_members_exist(self) -> None:
        expected = {
            "PERSON",
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "CREDIT_CARD",
            "IP_ADDRESS",
            "URL",
            "CRYPTO",
            "API_KEY",
            "SECRET_TOKEN",
            "PASSWORD",
            "NRP",
        }
        actual = {e.value for e in PIIEntityType}
        assert actual == expected

    def test_str_enum_values_match_names(self) -> None:
        for member in PIIEntityType:
            assert str(member) == member.value

    def test_lookup_by_value(self) -> None:
        assert PIIEntityType("PERSON") == PIIEntityType.PERSON
        assert PIIEntityType("API_KEY") == PIIEntityType.API_KEY

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError, match="is not a valid"):
            PIIEntityType("NOT_A_REAL_TYPE")

    @pytest.mark.parametrize(
        "member",
        list(PIIEntityType),
    )
    def test_members_are_strings(self, member: PIIEntityType) -> None:
        assert isinstance(member, str)


# ---------------------------------------------------------------------------
# PIIDetection
# ---------------------------------------------------------------------------


class TestPIIDetection:
    """Tests for the PIIDetection value object."""

    def _make(self, **overrides: object) -> PIIDetection:
        defaults: dict[str, object] = {
            "entity_type": PIIEntityType.EMAIL_ADDRESS,
            "start": 0,
            "end": 20,
            "score": 0.95,
            "text": "user@example.com",
            "replacement": "<EMAIL_ADDRESS>",
        }
        defaults.update(overrides)
        return PIIDetection(**defaults)  # type: ignore[arg-type]

    # ---- happy path -------------------------------------------------------

    def test_create_happy_path(self) -> None:
        det = self._make()
        assert det.entity_type == PIIEntityType.EMAIL_ADDRESS
        assert det.start == 0
        assert det.end == 20
        assert det.score == 0.95
        assert det.text == "user@example.com"
        assert det.replacement == "<EMAIL_ADDRESS>"

    def test_frozen_model_cannot_mutate(self) -> None:
        det = self._make()
        with pytest.raises(ValidationError, match="frozen"):
            det.score = 0.5  # type: ignore[misc]

    # ---- score validation -------------------------------------------------

    def test_score_minimum_boundary(self) -> None:
        det = self._make(score=0.0)
        assert det.score == 0.0

    def test_score_maximum_boundary(self) -> None:
        det = self._make(score=1.0)
        assert det.score == 1.0

    def test_score_below_minimum_raises(self) -> None:
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            self._make(score=-0.01)

    def test_score_above_maximum_raises(self) -> None:
        with pytest.raises(ValidationError, match="less than or equal to 1"):
            self._make(score=1.01)

    # ---- offset validation ------------------------------------------------

    def test_start_zero_is_valid(self) -> None:
        det = self._make(start=0)
        assert det.start == 0

    def test_start_negative_raises(self) -> None:
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            self._make(start=-1)

    def test_end_zero_is_valid(self) -> None:
        det = self._make(end=0)
        assert det.end == 0

    def test_end_negative_raises(self) -> None:
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            self._make(end=-1)

    # ---- from_presidio factory --------------------------------------------

    @pytest.mark.parametrize(
        ("presidio_type", "expected_enum"),
        [
            ("PERSON", PIIEntityType.PERSON),
            ("EMAIL_ADDRESS", PIIEntityType.EMAIL_ADDRESS),
            ("PHONE_NUMBER", PIIEntityType.PHONE_NUMBER),
            ("CREDIT_CARD", PIIEntityType.CREDIT_CARD),
            ("IP_ADDRESS", PIIEntityType.IP_ADDRESS),
            ("URL", PIIEntityType.URL),
            ("CRYPTO", PIIEntityType.CRYPTO),
            ("API_KEY", PIIEntityType.API_KEY),
            ("SECRET_TOKEN", PIIEntityType.SECRET_TOKEN),
            ("PASSWORD", PIIEntityType.PASSWORD),
            ("NRP", PIIEntityType.NRP),
        ],
    )
    def test_from_presidio_known_types(
        self, presidio_type: str, expected_enum: PIIEntityType
    ) -> None:
        original = "hello world padded text here"
        det = PIIDetection.from_presidio(
            entity_type=presidio_type,
            start=0,
            end=5,
            score=0.8,
            original_text=original,
        )
        assert det.entity_type == expected_enum

    @pytest.mark.parametrize(
        ("presidio_type", "expected_enum"),
        [
            ("US_SSN", PIIEntityType.NRP),
            ("US_DRIVER_LICENSE", PIIEntityType.NRP),
            ("US_PASSPORT", PIIEntityType.NRP),
            ("MEDICAL_LICENSE", PIIEntityType.NRP),
            ("DATE_TIME", PIIEntityType.NRP),
            ("LOCATION", PIIEntityType.NRP),
            ("US_BANK_NUMBER", PIIEntityType.CREDIT_CARD),
            ("IBAN_CODE", PIIEntityType.CREDIT_CARD),
            ("ORGANIZATION", PIIEntityType.PERSON),
        ],
    )
    def test_from_presidio_aliased_types(
        self, presidio_type: str, expected_enum: PIIEntityType
    ) -> None:
        det = PIIDetection.from_presidio(
            entity_type=presidio_type,
            start=0,
            end=3,
            score=0.7,
            original_text="abc xyz",
        )
        assert det.entity_type == expected_enum

    def test_from_presidio_unknown_type_defaults_to_secret_token(self) -> None:
        det = PIIDetection.from_presidio(
            entity_type="UNKNOWN_ENTITY",
            start=0,
            end=5,
            score=0.5,
            original_text="hello world",
        )
        assert det.entity_type == PIIEntityType.SECRET_TOKEN

    def test_from_presidio_extracts_text_span(self) -> None:
        original = "My email is user@example.com end"
        det = PIIDetection.from_presidio(
            entity_type="EMAIL_ADDRESS",
            start=12,
            end=28,
            score=0.99,
            original_text=original,
        )
        assert det.text == original[12:28]

    def test_from_presidio_start_beyond_text_length_returns_empty(self) -> None:
        original = "short"
        det = PIIDetection.from_presidio(
            entity_type="EMAIL_ADDRESS",
            start=100,
            end=120,
            score=0.9,
            original_text=original,
        )
        assert det.text == ""

    def test_from_presidio_sets_replacement_from_entity_type(self) -> None:
        det = PIIDetection.from_presidio(
            entity_type="EMAIL_ADDRESS",
            start=0,
            end=3,
            score=0.9,
            original_text="abc",
        )
        assert det.replacement == "<EMAIL_ADDRESS>"

    def test_from_presidio_score_preserved(self) -> None:
        det = PIIDetection.from_presidio(
            entity_type="PERSON",
            start=0,
            end=4,
            score=0.75,
            original_text="John Doe",
        )
        assert det.score == 0.75

    def test_from_presidio_offsets_preserved(self) -> None:
        det = PIIDetection.from_presidio(
            entity_type="PERSON",
            start=3,
            end=7,
            score=0.9,
            original_text="Hi John there",
        )
        assert det.start == 3
        assert det.end == 7


# ---------------------------------------------------------------------------
# SanitizationContext
# ---------------------------------------------------------------------------


class TestSanitizationContext:
    """Tests for the SanitizationContext domain entity."""

    def test_create_with_defaults(self) -> None:
        ctx = SanitizationContext(text="Hello world")
        assert ctx.text == "Hello world"
        assert ctx.language == "en"
        assert ctx.entities_to_detect is None
        assert ctx.score_threshold == 0.5

    def test_create_with_all_fields(self) -> None:
        ctx = SanitizationContext(
            text="Bonjour",
            language="fr",
            entities_to_detect=["EMAIL_ADDRESS", "PERSON"],
            score_threshold=0.8,
        )
        assert ctx.language == "fr"
        assert ctx.entities_to_detect == ["EMAIL_ADDRESS", "PERSON"]
        assert ctx.score_threshold == 0.8

    def test_frozen_model_cannot_mutate(self) -> None:
        ctx = SanitizationContext(text="hi")
        with pytest.raises(ValidationError, match="frozen"):
            ctx.text = "new text"  # type: ignore[misc]

    def test_score_threshold_minimum_boundary(self) -> None:
        ctx = SanitizationContext(text="t", score_threshold=0.0)
        assert ctx.score_threshold == 0.0

    def test_score_threshold_maximum_boundary(self) -> None:
        ctx = SanitizationContext(text="t", score_threshold=1.0)
        assert ctx.score_threshold == 1.0

    def test_score_threshold_below_minimum_raises(self) -> None:
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            SanitizationContext(text="t", score_threshold=-0.1)

    def test_score_threshold_above_maximum_raises(self) -> None:
        with pytest.raises(ValidationError, match="less than or equal to 1"):
            SanitizationContext(text="t", score_threshold=1.1)

    def test_text_required(self) -> None:
        with pytest.raises(ValidationError, match="Field required"):
            SanitizationContext()  # type: ignore[call-arg]

    def test_empty_text_is_valid(self) -> None:
        ctx = SanitizationContext(text="")
        assert ctx.text == ""

    def test_entities_to_detect_none_means_detect_all(self) -> None:
        ctx = SanitizationContext(text="test", entities_to_detect=None)
        assert ctx.entities_to_detect is None

    def test_entities_to_detect_empty_list(self) -> None:
        ctx = SanitizationContext(text="test", entities_to_detect=[])
        assert ctx.entities_to_detect == []

    def test_entities_to_detect_single_entity(self) -> None:
        ctx = SanitizationContext(text="test", entities_to_detect=["PERSON"])
        assert ctx.entities_to_detect == ["PERSON"]


# ---------------------------------------------------------------------------
# DLPResult
# ---------------------------------------------------------------------------


def _make_detection(
    entity_type: PIIEntityType = PIIEntityType.EMAIL_ADDRESS,
    start: int = 0,
    end: int = 5,
    score: float = 0.9,
    text: str = "a@b.c",
    replacement: str = "<EMAIL_ADDRESS>",
) -> PIIDetection:
    return PIIDetection(
        entity_type=entity_type,
        start=start,
        end=end,
        score=score,
        text=text,
        replacement=replacement,
    )


class TestDLPResult:
    """Tests for the DLPResult domain entity."""

    def test_create_happy_path(self) -> None:
        result = DLPResult(
            original_text="My email is a@b.c",
            sanitized_text="My email is <EMAIL_ADDRESS>",
            detections=[_make_detection()],
            presidio_passed=False,
        )
        assert result.original_text == "My email is a@b.c"
        assert result.sanitized_text == "My email is <EMAIL_ADDRESS>"
        assert len(result.detections) == 1
        assert result.presidio_passed is False
        assert result.semantic_passed is True  # default

    def test_default_empty_detections(self) -> None:
        result = DLPResult(
            original_text="clean text",
            sanitized_text="clean text",
            presidio_passed=True,
        )
        assert result.detections == []

    def test_frozen_model_cannot_mutate(self) -> None:
        result = DLPResult(
            original_text="x",
            sanitized_text="x",
            presidio_passed=True,
        )
        with pytest.raises(ValidationError):
            result.presidio_passed = False  # type: ignore[misc]

    # ---- computed field: total_redactions ----------------------------------

    def test_total_redactions_zero_when_no_detections(self) -> None:
        result = DLPResult(
            original_text="clean",
            sanitized_text="clean",
            presidio_passed=True,
        )
        assert result.total_redactions == 0

    def test_total_redactions_single_detection(self) -> None:
        result = DLPResult(
            original_text="text",
            sanitized_text="redacted",
            detections=[_make_detection()],
            presidio_passed=False,
        )
        assert result.total_redactions == 1

    def test_total_redactions_multiple_detections(self) -> None:
        detections = [
            _make_detection(entity_type=PIIEntityType.EMAIL_ADDRESS),
            _make_detection(entity_type=PIIEntityType.PERSON, start=10, end=14),
            _make_detection(entity_type=PIIEntityType.PHONE_NUMBER, start=20, end=30),
        ]
        result = DLPResult(
            original_text="some text with pii",
            sanitized_text="redacted",
            detections=detections,
            presidio_passed=False,
        )
        assert result.total_redactions == 3

    # ---- computed field: contains_pii -------------------------------------

    def test_contains_pii_false_when_no_detections(self) -> None:
        result = DLPResult(
            original_text="clean",
            sanitized_text="clean",
            presidio_passed=True,
        )
        assert result.contains_pii is False

    def test_contains_pii_true_when_detections_present(self) -> None:
        result = DLPResult(
            original_text="text",
            sanitized_text="redacted",
            detections=[_make_detection()],
            presidio_passed=False,
        )
        assert result.contains_pii is True

    # ---- classmethod: safe_text -------------------------------------------

    def test_safe_text_factory_creates_clean_result(self) -> None:
        text = "This is completely safe text"
        result = DLPResult.safe_text(text)
        assert result.original_text == text
        assert result.sanitized_text == text
        assert result.detections == []
        assert result.presidio_passed is True
        assert result.semantic_passed is True
        assert result.total_redactions == 0
        assert result.contains_pii is False

    def test_safe_text_with_empty_string(self) -> None:
        result = DLPResult.safe_text("")
        assert result.original_text == ""
        assert result.sanitized_text == ""
        assert result.detections == []
        assert result.presidio_passed is True

    def test_safe_text_with_unicode_content(self) -> None:
        text = "Texto seguro con acentos: áéíóú ñ"
        result = DLPResult.safe_text(text)
        assert result.original_text == text
        assert result.sanitized_text == text

    # ---- semantic_passed flag --------------------------------------------

    def test_semantic_passed_default_true(self) -> None:
        result = DLPResult(
            original_text="x",
            sanitized_text="x",
            presidio_passed=True,
        )
        assert result.semantic_passed is True

    def test_semantic_passed_can_be_false(self) -> None:
        result = DLPResult(
            original_text="x",
            sanitized_text="x",
            presidio_passed=True,
            semantic_passed=False,
        )
        assert result.semantic_passed is False


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TestExceptions:
    """Tests for the DLP exception hierarchy."""

    def test_dlp_error_is_exception(self) -> None:
        err = DLPError("base error")
        assert isinstance(err, Exception)
        assert str(err) == "base error"

    def test_sanitization_error_is_dlp_error(self) -> None:
        err = SanitizationError("sanitization failed")
        assert isinstance(err, DLPError)
        assert isinstance(err, Exception)

    def test_presidio_unavailable_error_is_dlp_error(self) -> None:
        err = PresidioUnavailableError("presidio down")
        assert isinstance(err, DLPError)
        assert isinstance(err, Exception)

    def test_semantic_validation_error_is_dlp_error(self) -> None:
        err = SemanticValidationError("semantic check failed")
        assert isinstance(err, DLPError)
        assert isinstance(err, Exception)

    def test_can_raise_and_catch_dlp_error(self) -> None:
        with pytest.raises(DLPError, match="test"):
            raise DLPError("test")

    def test_can_catch_sanitization_error_as_dlp_error(self) -> None:
        with pytest.raises(DLPError, match="oops"):
            raise SanitizationError("oops")

    def test_can_catch_presidio_unavailable_as_dlp_error(self) -> None:
        with pytest.raises(DLPError, match="unavailable"):
            raise PresidioUnavailableError("unavailable")

    def test_can_catch_semantic_validation_error_as_dlp_error(self) -> None:
        with pytest.raises(DLPError, match="invalid"):
            raise SemanticValidationError("invalid")

    def test_sanitization_error_not_caught_by_unrelated_exception(self) -> None:
        with pytest.raises(SanitizationError, match="specific catch works"):
            raise SanitizationError("specific catch works")

    def test_exceptions_accept_no_message(self) -> None:
        err = DLPError()
        assert isinstance(err, DLPError)

    def test_exceptions_accept_multiple_args(self) -> None:
        err = SanitizationError("msg", "extra_context", 42)
        assert isinstance(err, SanitizationError)
        assert err.args == ("msg", "extra_context", 42)


# ---------------------------------------------------------------------------
# __init__ re-exports
# ---------------------------------------------------------------------------


class TestPrivacyInitReexports:
    """Tests that the __init__ re-exports all expected symbols."""

    def test_dlp_error_importable_from_package(self) -> None:
        from siopv.domain.privacy import DLPError as E

        assert E is DLPError

    def test_dlp_result_importable_from_package(self) -> None:
        from siopv.domain.privacy import DLPResult as R

        assert R is DLPResult

    def test_pii_detection_importable_from_package(self) -> None:
        from siopv.domain.privacy import PIIDetection as D

        assert D is PIIDetection

    def test_pii_entity_type_importable_from_package(self) -> None:
        from siopv.domain.privacy import PIIEntityType as T

        assert T is PIIEntityType

    def test_sanitization_context_importable_from_package(self) -> None:
        from siopv.domain.privacy import SanitizationContext as C

        assert C is SanitizationContext

    def test_sanitization_error_importable_from_package(self) -> None:
        from siopv.domain.privacy import SanitizationError as SErr

        assert SErr is SanitizationError
