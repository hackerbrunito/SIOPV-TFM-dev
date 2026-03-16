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
from siopv.application.ports.ml_classifier import (
    DatasetLoaderPort,
    MLClassifierPort,
    ModelTrainerPort,
)
from siopv.application.ports.oidc_authentication import OIDCAuthenticationPort
from siopv.application.ports.parsing import TrivyParserPort
from siopv.application.ports.vector_store import VectorStorePort

__all__ = [
    "AuthorizationModelPort",
    "AuthorizationPort",
    "AuthorizationStorePort",
    "DatasetLoaderPort",
    "EPSSClientPort",
    "FeatureEngineerPort",
    "GitHubAdvisoryClientPort",
    "MLClassifierPort",
    "ModelTrainerPort",
    "NVDClientPort",
    "OIDCAuthenticationPort",
    "OSINTSearchClientPort",
    "TrivyParserPort",
    "VectorStorePort",
]
