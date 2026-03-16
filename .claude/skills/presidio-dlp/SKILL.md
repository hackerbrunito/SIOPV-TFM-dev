---
name: presidio-dlp
description: "Presidio DLP patterns: PII detection, anonymization, custom recognizers. USE WHEN code imports presidio_analyzer/anonymizer or user asks about PII/DLP."
user-invocable: false
---

# Presidio DLP

Microsoft Presidio patterns for PII detection and anonymization in SIOPV's vulnerability pipeline.

## When to use

Apply these patterns when adding or modifying DLP nodes, PII detection, anonymization logic,
or custom recognizers in the SIOPV pipeline.

## Quick checklist

1. Initialize `AnalyzerEngine` and `AnonymizerEngine` — never create per-request
2. Define entity list explicitly (PERSON, EMAIL, PHONE, CREDIT_CARD, IP, SSN, IBAN, AWS keys)
3. Use `OperatorConfig` for per-entity anonymization strategy (replace, mask, hash)
4. Register SIOPV custom recognizers: CVE_ID (`CVE-\d{4}-\d{4,7}`) and API_KEY (`sk-[a-zA-Z0-9]{32,}`)
5. Sanitize vulnerability reports BEFORE export — use `SanitizedReport` dataclass pattern
6. Sanitize audit log entries — check sensitive_fields list (email, ip_address, user_agent, api_key)
7. In LangGraph DLP node: detect PII in `state.enrichment.nvd_description`, log warning, anonymize
8. Configure via `DLPSettings(BaseSettings)` with `env_prefix="DLP_"` — never hardcode settings

## Key patterns (quick reference)

- **Detect PII:** `analyzer.analyze(text=text, language=language, entities=[...])`
- **Anonymize PII:** `anonymizer.anonymize(text=text, analyzer_results=results, operators=operators)`
- **Custom recognizer:** `PatternRecognizer(supported_entity="CVE_ID", patterns=[Pattern(...)])`
- **DLP node:** async node that checks + anonymizes PII in pipeline state before downstream processing

## Full reference

For complete code examples (setup, detection, anonymization, custom recognizers, LangGraph
integration, testing, configuration), see [presidio-dlp-reference.md](presidio-dlp-reference.md).
