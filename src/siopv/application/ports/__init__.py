"""Application ports (interfaces) for SIOPV.

Ports define contracts that adapters must implement.
Following hexagonal architecture (Ports & Adapters pattern).
"""

from siopv.application.ports.enrichment_clients import (
    EPSSClientPort,
    GitHubAdvisoryClientPort,
    NVDClientPort,
    OSINTSearchClientPort,
)
from siopv.application.ports.ml_classifier import (
    DatasetLoaderPort,
    MLClassifierPort,
    ModelTrainerPort,
)
from siopv.application.ports.vector_store import VectorStorePort

__all__ = [
    # Enrichment API clients
    "EPSSClientPort",
    "GitHubAdvisoryClientPort",
    "NVDClientPort",
    "OSINTSearchClientPort",
    # Vector store
    "VectorStorePort",
    # ML Classification
    "DatasetLoaderPort",
    "MLClassifierPort",
    "ModelTrainerPort",
]
