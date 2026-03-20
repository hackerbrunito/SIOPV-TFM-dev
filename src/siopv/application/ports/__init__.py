"""Application ports (interfaces) for SIOPV.

Ports define contracts that adapters must implement.
Following hexagonal architecture (Ports & Adapters pattern).
"""

from siopv.application.ports.authorization import (
    AuthorizationModelPort,
    AuthorizationPort,
    AuthorizationStorePort,
)
from siopv.application.ports.enrichment_clients import (
    EPSSClientPort,
    GitHubAdvisoryClientPort,
    NVDClientPort,
    OSINTSearchClientPort,
)
from siopv.application.ports.feature_engineering import FeatureEngineerPort
from siopv.application.ports.human_review import HumanReviewPort
from siopv.application.ports.jira_client import JiraClientPort
from siopv.application.ports.metrics_exporter import MetricsExporterPort
from siopv.application.ports.ml_classifier import (
    DatasetLoaderPort,
    MLClassifierPort,
    ModelTrainerPort,
)
from siopv.application.ports.oidc_authentication import OIDCAuthenticationPort
from siopv.application.ports.parsing import TrivyParserPort
from siopv.application.ports.pdf_generator import PdfGeneratorPort
from siopv.application.ports.vector_store import VectorStorePort
from siopv.application.ports.webhook_receiver import WebhookReceiverPort

__all__ = [
    "AuthorizationModelPort",
    "AuthorizationPort",
    "AuthorizationStorePort",
    "DatasetLoaderPort",
    "EPSSClientPort",
    "FeatureEngineerPort",
    "GitHubAdvisoryClientPort",
    "HumanReviewPort",
    "JiraClientPort",
    "MLClassifierPort",
    "MetricsExporterPort",
    "ModelTrainerPort",
    "NVDClientPort",
    "OIDCAuthenticationPort",
    "OSINTSearchClientPort",
    "PdfGeneratorPort",
    "TrivyParserPort",
    "VectorStorePort",
    "WebhookReceiverPort",
]
