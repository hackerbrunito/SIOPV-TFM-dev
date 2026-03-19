"""Domain-level constants for SIOPV.

This module defines threshold values and magic numbers used across the domain layer.
Centralizing these values improves maintainability and makes it easier to tune
the system's behavior.
"""

# EPSS Score Thresholds
# EPSS (Exploit Prediction Scoring System) provides probability scores for CVE exploitation
EPSS_HIGH_RISK_THRESHOLD = 0.1  # >0.1 indicates high exploitation risk

# Relevance Score Thresholds
# Relevance scores measure how well enrichment data matches the vulnerability context
RELEVANCE_SCORE_OSINT_FALLBACK_THRESHOLD = 0.6  # <0.6 triggers OSINT fallback

# Risk Probability Thresholds
# These define the boundaries for risk classification levels
RISK_PROBABILITY_CRITICAL_THRESHOLD = 0.8  # >=0.8 = CRITICAL
RISK_PROBABILITY_HIGH_THRESHOLD = 0.6  # >=0.6 = HIGH
RISK_PROBABILITY_MEDIUM_THRESHOLD = 0.4  # >=0.4 = MEDIUM
RISK_PROBABILITY_LOW_THRESHOLD = 0.2  # >=0.2 = LOW (below this = MINIMAL)

# Discrepancy Sentinel
# Used when ML score is unavailable — signals maximum uncertainty, always triggers escalation
MAX_UNCERTAINTY = 1.0

# Confidence Calculation
# Used to calculate prediction confidence from probability values
CONFIDENCE_CENTER_PROBABILITY = 0.5  # Center point for confidence calculation
CONFIDENCE_SCALE_FACTOR = 2  # Scale factor: abs(prob - 0.5) * 2

# Dashboard display limits
CASE_LIST_CVE_DISPLAY_LIMIT = 3  # Max CVE IDs shown inline before "+N more"
ELAPSED_TIME_HOURS_PER_DAY = 24  # Hours threshold for switching to "Nd ago" display
