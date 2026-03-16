# Presidio DLP — Reference Patterns

> Extracted from SKILL.md. Full code examples for SIOPV's Presidio DLP pipeline.

---

## Setup

```python
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


# Initialize engines
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()
```

---

## Detect PII

```python
def detect_pii(text: str, language: str = "en") -> list[dict]:
    """Detect PII in text."""

    results = analyzer.analyze(
        text=text,
        language=language,
        entities=[
            "PERSON",
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "CREDIT_CARD",
            "IP_ADDRESS",
            "US_SSN",
            "IBAN_CODE",
            "AWS_ACCESS_KEY",
            "AWS_SECRET_KEY",
        ],
    )

    return [
        {
            "entity_type": r.entity_type,
            "start": r.start,
            "end": r.end,
            "score": r.score,
            "text": text[r.start:r.end],
        }
        for r in results
    ]


# Usage
text = "Contact John Doe at john.doe@example.com or 555-123-4567"
pii = detect_pii(text)
# [
#   {"entity_type": "PERSON", "text": "John Doe", ...},
#   {"entity_type": "EMAIL_ADDRESS", "text": "john.doe@example.com", ...},
#   {"entity_type": "PHONE_NUMBER", "text": "555-123-4567", ...},
# ]
```

---

## Anonymize PII

```python
def anonymize_pii(
    text: str,
    language: str = "en",
    operators: dict[str, OperatorConfig] | None = None,
) -> str:
    """Anonymize PII in text."""

    # Detect
    results = analyzer.analyze(text=text, language=language)

    # Default operators
    if operators is None:
        operators = {
            "PERSON": OperatorConfig("replace", {"new_value": "[REDACTED_NAME]"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[REDACTED_EMAIL]"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[REDACTED_PHONE]"}),
            "CREDIT_CARD": OperatorConfig("mask", {"chars_to_mask": 12, "masking_char": "*"}),
            "IP_ADDRESS": OperatorConfig("replace", {"new_value": "[REDACTED_IP]"}),
        }

    # Anonymize
    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=operators,
    )

    return anonymized.text


# Usage
text = "Contact John Doe at john.doe@example.com"
anon = anonymize_pii(text)
# "Contact [REDACTED_NAME] at [REDACTED_EMAIL]"
```

---

## Custom Recognizers

```python
# CVE ID Recognizer
cve_pattern = Pattern(
    name="cve_pattern",
    regex=r"CVE-\d{4}-\d{4,7}",
    score=0.9,
)

cve_recognizer = PatternRecognizer(
    supported_entity="CVE_ID",
    patterns=[cve_pattern],
)

analyzer.registry.add_recognizer(cve_recognizer)


# API Key Recognizer
api_key_pattern = Pattern(
    name="api_key_pattern",
    regex=r"sk-[a-zA-Z0-9]{32,}",
    score=0.95,
)

api_key_recognizer = PatternRecognizer(
    supported_entity="API_KEY",
    patterns=[api_key_pattern],
)

analyzer.registry.add_recognizer(api_key_recognizer)
```

---

## Vulnerability Report Sanitization

```python
@dataclass
class SanitizedReport:
    original_pii_count: int
    sanitized_text: str
    pii_found: list[dict]


def sanitize_vulnerability_report(report_text: str) -> SanitizedReport:
    """Sanitize vulnerability report before sharing/export."""

    # Detect all PII
    pii_found = detect_pii(report_text)

    # Anonymize
    sanitized = anonymize_pii(report_text)

    return SanitizedReport(
        original_pii_count=len(pii_found),
        sanitized_text=sanitized,
        pii_found=pii_found,
    )


# Usage example
def export_report(vulnerability_id: str, include_pii: bool = False) -> str:
    """Export vulnerability report with optional PII redaction."""

    report = generate_report(vulnerability_id)

    if not include_pii:
        sanitized = sanitize_vulnerability_report(report)
        logger.info(
            "report_sanitized",
            vulnerability_id=vulnerability_id,
            pii_redacted=sanitized.original_pii_count,
        )
        return sanitized.sanitized_text

    return report
```

---

## Audit Log Sanitization

```python
def sanitize_for_audit(data: dict) -> dict:
    """Sanitize sensitive fields in audit log entries."""

    sensitive_fields = ["email", "ip_address", "user_agent", "api_key"]
    sanitized = data.copy()

    for field in sensitive_fields:
        if field in sanitized:
            value = str(sanitized[field])
            sanitized_value = anonymize_pii(value)
            sanitized[field] = sanitized_value

    return sanitized
```

---

## Integration with LangGraph

```python
async def dlp_node(state: PipelineState) -> PipelineState:
    """DLP node in vulnerability processing pipeline."""

    # Check for PII in vulnerability description
    if state.enrichment.nvd_description:
        pii = detect_pii(state.enrichment.nvd_description)

        if pii:
            logger.warning(
                "pii_detected_in_description",
                cve_id=state.vulnerability.cve_id,
                pii_types=[p["entity_type"] for p in pii],
            )

            # Anonymize for storage
            state.enrichment.nvd_description = anonymize_pii(
                state.enrichment.nvd_description
            )

    return state
```

---

## Testing

```python
@pytest.mark.parametrize("text,expected_entities", [
    ("john@example.com", ["EMAIL_ADDRESS"]),
    ("Call 555-123-4567", ["PHONE_NUMBER"]),
    ("John Doe reported CVE-2024-1234", ["PERSON", "CVE_ID"]),
])
def test_pii_detection(text: str, expected_entities: list[str]):
    pii = detect_pii(text)
    found_entities = [p["entity_type"] for p in pii]
    for entity in expected_entities:
        assert entity in found_entities


def test_anonymization():
    text = "Contact admin@corp.com about CVE-2024-1234"
    anon = anonymize_pii(text)

    assert "admin@corp.com" not in anon
    assert "[REDACTED_EMAIL]" in anon
    # CVE IDs should NOT be redacted (they're not PII)
    assert "CVE-2024-1234" in anon
```

---

## Configuration

```python
# src/infrastructure/config/settings.py
from pydantic_settings import BaseSettings

class DLPSettings(BaseSettings):
    """DLP configuration."""

    model_config = ConfigDict(env_prefix="DLP_")

    enabled: bool = True
    default_language: str = "en"
    redact_in_logs: bool = True
    redact_in_exports: bool = True
    custom_entities: list[str] = ["CVE_ID", "API_KEY"]
```
