"""Port interface for feature engineering in SIOPV.

Defines the contract for ML feature extraction implementations following
hexagonal architecture. Use cases depend on this port, not on the adapter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from siopv.domain.entities import VulnerabilityRecord
    from siopv.domain.entities.ml_feature_vector import MLFeatureVector
    from siopv.domain.value_objects import EnrichmentData


@runtime_checkable
class FeatureEngineerPort(Protocol):
    """Port interface for ML feature extraction.

    Extracts the feature vector from vulnerability and enrichment data
    for consumption by an ML classifier.
    """

    def extract_features(
        self,
        vulnerability: VulnerabilityRecord,
        enrichment: EnrichmentData,
    ) -> MLFeatureVector:
        """Extract feature vector from vulnerability and enrichment data.

        Args:
            vulnerability: VulnerabilityRecord from Phase 1
            enrichment: EnrichmentData from Phase 2

        Returns:
            MLFeatureVector ready for ML model
        """
        ...


__all__ = ["FeatureEngineerPort"]
