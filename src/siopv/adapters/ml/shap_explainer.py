"""SHAP explainer wrapper for XGBoost model.

Provides global feature importance explanations using SHAP TreeExplainer.
Based on specification section 3.3 (XAI Implementation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import shap
import structlog

from siopv.domain.entities.ml_feature_vector import MLFeatureVector
from siopv.domain.value_objects.risk_score import SHAPValues

if TYPE_CHECKING:
    from xgboost import XGBClassifier

logger = structlog.get_logger(__name__)


class SHAPExplainer:
    """SHAP-based explainer for XGBoost risk classifier.

    Uses TreeExplainer for efficient computation of SHAP values
    on tree-based models. Provides global feature importance
    for answering questions like:
    "Why does the model prioritize vulnerabilities with Network Attack Vector?"
    """

    def __init__(
        self,
        model: XGBClassifier,
        feature_names: list[str],
    ) -> None:
        """Initialize SHAP explainer.

        Args:
            model: Trained XGBoost classifier
            feature_names: Ordered list of feature names
        """
        self._model = model
        self._feature_names = feature_names
        self._explainer: shap.TreeExplainer | None = None

        logger.info("shap_explainer_initialized", n_features=len(feature_names))

    def _ensure_explainer(self) -> shap.TreeExplainer:
        """Lazily initialize TreeExplainer."""
        if self._explainer is None:
            logger.debug("creating_tree_explainer")
            self._explainer = shap.TreeExplainer(self._model)
        return self._explainer

    def explain(self, feature_vector: MLFeatureVector) -> SHAPValues:
        """Generate SHAP explanation for a single prediction.

        Args:
            feature_vector: MLFeatureVector with 14 features

        Returns:
            SHAPValues with feature importance for this prediction
        """
        explainer = self._ensure_explainer()

        # Convert to 2D array for SHAP
        X = feature_vector.to_array().reshape(1, -1)

        # Get SHAP values
        shap_values = explainer.shap_values(X)

        # For binary classification, shap_values may be a list [negative_class, positive_class]
        # We want the positive class (exploited) values
        if isinstance(shap_values, list):
            # Binary classification: use positive class
            values = shap_values[1][0]
        else:
            # Single output
            values = shap_values[0]

        # Get base value (expected value)
        if isinstance(explainer.expected_value, np.ndarray):
            base_value = float(explainer.expected_value[1])  # Positive class
        else:
            base_value = float(explainer.expected_value)

        logger.debug(
            "shap_explanation_generated",
            cve_id=feature_vector.cve_id,
            base_value=base_value,
        )

        return SHAPValues(
            feature_names=self._feature_names,
            shap_values=[float(v) for v in values],
            base_value=base_value,
        )

    def explain_batch(
        self,
        feature_vectors: list[MLFeatureVector],
    ) -> list[SHAPValues]:
        """Generate SHAP explanations for multiple predictions.

        Args:
            feature_vectors: List of MLFeatureVector instances

        Returns:
            List of SHAPValues, one per input
        """
        if not feature_vectors:
            return []

        explainer = self._ensure_explainer()

        # Stack all feature vectors
        X = np.vstack([fv.to_array().reshape(1, -1) for fv in feature_vectors])

        # Get SHAP values for all
        shap_values = explainer.shap_values(X)

        # Handle binary classification
        if isinstance(shap_values, list):
            values_array = shap_values[1]  # Positive class
        else:
            values_array = shap_values

        # Get base value
        if isinstance(explainer.expected_value, np.ndarray):
            base_value = float(explainer.expected_value[1])
        else:
            base_value = float(explainer.expected_value)

        # Create SHAPValues for each
        results = []
        for i, fv in enumerate(feature_vectors):
            results.append(
                SHAPValues(
                    feature_names=self._feature_names,
                    shap_values=[float(v) for v in values_array[i]],
                    base_value=base_value,
                )
            )

        logger.info("shap_batch_complete", n_explanations=len(results))

        return results

    def get_global_importance(
        self,
        feature_vectors: list[MLFeatureVector],
    ) -> dict[str, float]:
        """Calculate global feature importance across multiple samples.

        Uses mean absolute SHAP value as importance metric.

        Args:
            feature_vectors: List of MLFeatureVector instances

        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not feature_vectors:
            return {}

        explainer = self._ensure_explainer()

        # Stack all feature vectors
        X = np.vstack([fv.to_array().reshape(1, -1) for fv in feature_vectors])

        # Get SHAP values
        shap_values = explainer.shap_values(X)

        if isinstance(shap_values, list):
            values_array = shap_values[1]
        else:
            values_array = shap_values

        # Calculate mean absolute SHAP value for each feature
        mean_abs_shap = np.mean(np.abs(values_array), axis=0)

        importance = dict(zip(self._feature_names, mean_abs_shap.tolist(), strict=True))

        logger.info("global_importance_calculated", n_samples=len(feature_vectors))

        return importance

    def generate_summary_data(
        self,
        feature_vectors: list[MLFeatureVector],
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """Generate data for SHAP summary plot.

        Returns data that can be passed to shap.summary_plot().

        Args:
            feature_vectors: List of MLFeatureVector instances

        Returns:
            Tuple of (shap_values, feature_matrix, feature_names)
        """
        if not feature_vectors:
            return np.array([]), np.array([]), []

        explainer = self._ensure_explainer()

        # Stack all feature vectors
        X = np.vstack([fv.to_array().reshape(1, -1) for fv in feature_vectors])

        # Get SHAP values
        shap_values = explainer.shap_values(X)

        if isinstance(shap_values, list):
            values_array = shap_values[1]
        else:
            values_array = shap_values

        return values_array, X, self._feature_names


__all__ = ["SHAPExplainer"]
