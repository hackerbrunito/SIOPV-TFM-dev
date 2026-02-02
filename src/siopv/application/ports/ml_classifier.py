"""Port interface for ML classification.

Defines the contract for ML classifier implementations.
Implementations live in adapters/ml/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from siopv.domain.entities.ml_feature_vector import MLFeatureVector
    from siopv.domain.value_objects.risk_score import (
        LIMEExplanation,
        RiskScore,
        SHAPValues,
    )


class MLClassifierPort(ABC):
    """Port interface for ML risk classifier.

    Implementations must provide:
    - Binary classification (exploited vs not exploited)
    - Probability prediction
    - SHAP global explanations
    - LIME local explanations
    """

    @abstractmethod
    def predict(self, feature_vector: MLFeatureVector) -> RiskScore:
        """Predict exploitation risk for a vulnerability.

        Args:
            feature_vector: MLFeatureVector with 14 features

        Returns:
            RiskScore with probability, SHAP values, and LIME explanation
        """
        ...

    @abstractmethod
    def predict_batch(
        self,
        feature_vectors: list[MLFeatureVector],
    ) -> list[RiskScore]:
        """Predict exploitation risk for multiple vulnerabilities.

        Args:
            feature_vectors: List of MLFeatureVector instances

        Returns:
            List of RiskScore instances
        """
        ...

    @abstractmethod
    def predict_proba(self, feature_vector: MLFeatureVector) -> float:
        """Get raw probability prediction without explanations.

        Args:
            feature_vector: MLFeatureVector with 14 features

        Returns:
            Probability of exploitation (0-1)
        """
        ...

    @abstractmethod
    def get_shap_values(self, feature_vector: MLFeatureVector) -> SHAPValues:
        """Get SHAP feature importance for a prediction.

        Args:
            feature_vector: MLFeatureVector with 14 features

        Returns:
            SHAPValues with feature importance
        """
        ...

    @abstractmethod
    def get_lime_explanation(self, feature_vector: MLFeatureVector) -> LIMEExplanation:
        """Get LIME local explanation for a prediction.

        Args:
            feature_vector: MLFeatureVector with 14 features

        Returns:
            LIMEExplanation with feature contributions
        """
        ...

    @abstractmethod
    def get_feature_importance(self) -> dict[str, float]:
        """Get global feature importance from the model.

        Returns:
            Dictionary mapping feature names to importance scores
        """
        ...

    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if model is loaded and ready for inference.

        Returns:
            True if model is ready, False otherwise
        """
        ...


class ModelTrainerPort(ABC):
    """Port interface for model training.

    Separates training concerns from inference.
    """

    @abstractmethod
    def train(
        self,
        X: list[MLFeatureVector],
        y: list[int],
        *,
        optimize_hyperparams: bool = True,
    ) -> dict[str, float]:
        """Train the classification model.

        Args:
            X: List of feature vectors
            y: List of labels (1 = exploited, 0 = not exploited)
            optimize_hyperparams: Whether to use Optuna for tuning

        Returns:
            Dictionary with training metrics
        """
        ...

    @abstractmethod
    def evaluate(
        self,
        X: list[MLFeatureVector],
        y: list[int],
    ) -> dict[str, float]:
        """Evaluate model on test data.

        Args:
            X: List of feature vectors
            y: List of true labels

        Returns:
            Dictionary with evaluation metrics
        """
        ...

    @abstractmethod
    def save_model(self, path: str) -> None:
        """Save trained model to disk.

        Args:
            path: Path to save the model
        """
        ...

    @abstractmethod
    def load_model(self, path: str) -> None:
        """Load trained model from disk.

        Args:
            path: Path to the saved model
        """
        ...


class DatasetLoaderPort(ABC):
    """Port interface for loading training datasets.

    Implementations handle CISA KEV catalog and negative sampling.
    """

    @abstractmethod
    async def load_kev_catalog(self) -> list[str]:
        """Load CISA Known Exploited Vulnerabilities catalog.

        Returns:
            List of CVE IDs confirmed as exploited
        """
        ...

    @abstractmethod
    async def sample_negative_class(
        self,
        exclude_cves: set[str],
        *,
        sample_size: int = 3600,
        max_epss: float = 0.1,
        min_age_days: int = 730,
    ) -> list[str]:
        """Sample CVEs for negative class.

        Args:
            exclude_cves: CVE IDs to exclude (from KEV)
            sample_size: Number of negative samples
            max_epss: Maximum EPSS score for negative samples
            min_age_days: Minimum age in days without exploitation

        Returns:
            List of CVE IDs for negative class
        """
        ...


__all__ = [
    "DatasetLoaderPort",
    "MLClassifierPort",
    "ModelTrainerPort",
]
