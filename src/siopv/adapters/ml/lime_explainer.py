"""LIME explainer wrapper for XGBoost model.

Provides local per-prediction explanations using LIME.
Based on specification section 3.3 (XAI Implementation).

Security features (M-03 fix):
- Configurable random_state instead of hardcoded value
- Random state passed from parent classifier for consistency
"""

from __future__ import annotations

from collections.abc import Callable

import lime
import lime.lime_tabular
import numpy as np
import structlog

from siopv.domain.entities.ml_feature_vector import MLFeatureVector
from siopv.domain.value_objects.risk_score import LIMEExplanation

logger = structlog.get_logger(__name__)

# Default random state for dev/test (matches xgboost_classifier default)
DEFAULT_RANDOM_STATE = 42


class LIMEExplainer:
    """LIME-based explainer for XGBoost risk classifier.

    Uses LimeTabularExplainer for generating local interpretable
    explanations. For each prediction, LIME shows which features
    contributed most to the classification decision.

    Example output: "EPSS > 0.7 contributed +0.35 to the score"

    Security: Random state is configurable to avoid predictable explanations
    in production environments.
    """

    def __init__(
        self,
        predict_fn: Callable[[np.ndarray], np.ndarray],
        feature_names: list[str],
        training_data: np.ndarray | None = None,
        *,
        class_names: list[str] | None = None,
        mode: str = "classification",
        random_state: int | None = None,
    ) -> None:
        """Initialize LIME explainer.

        Args:
            predict_fn: Function that takes features and returns probabilities
            feature_names: Ordered list of feature names
            training_data: Training data for computing statistics (optional)
            class_names: Names for classes (default: ["not_exploited", "exploited"])
            mode: "classification" or "regression"
            random_state: Random state for reproducibility.
                If None, uses DEFAULT_RANDOM_STATE (42).
                Should be passed from parent classifier for consistency.
        """
        self._predict_fn = predict_fn
        self._feature_names = feature_names
        self._class_names = class_names or ["not_exploited", "exploited"]
        self._mode = mode
        self._random_state = random_state if random_state is not None else DEFAULT_RANDOM_STATE

        # Initialize LIME explainer (M-03 fix: use configured random_state)
        self._explainer = lime.lime_tabular.LimeTabularExplainer(
            training_data=training_data
            if training_data is not None
            else np.zeros((1, len(feature_names))),
            feature_names=feature_names,
            class_names=self._class_names,
            mode=mode,
            discretize_continuous=True,
            random_state=self._random_state,
        )

        logger.info(
            "lime_explainer_initialized",
            n_features=len(feature_names),
            mode=mode,
            random_state=self._random_state,
        )

    def explain(
        self,
        feature_vector: MLFeatureVector,
        *,
        num_features: int = 10,
        num_samples: int = 5000,
    ) -> LIMEExplanation:
        """Generate LIME explanation for a single prediction.

        Args:
            feature_vector: MLFeatureVector with 14 features
            num_features: Number of top features to include
            num_samples: Number of samples for local model

        Returns:
            LIMEExplanation with feature contributions
        """
        # Convert to array
        X = feature_vector.to_array()

        # Generate explanation
        explanation = self._explainer.explain_instance(
            X,
            self._predict_fn,
            num_features=num_features,
            num_samples=num_samples,
            labels=(1,),  # Explain positive class (exploited)
        )

        # Extract feature contributions for positive class
        contributions = explanation.as_list(label=1)

        # Get local prediction and model score
        local_pred = explanation.local_pred[0] if hasattr(explanation, "local_pred") else 0.5

        # Get R-squared score of local model (fidelity)
        model_score = explanation.score if hasattr(explanation, "score") else 0.0

        # Get intercept
        intercept = explanation.intercept[1] if hasattr(explanation, "intercept") else 0.0

        logger.debug(
            "lime_explanation_generated",
            cve_id=feature_vector.cve_id,
            n_contributions=len(contributions),
            local_pred=local_pred,
        )

        return LIMEExplanation(
            feature_contributions=contributions,
            prediction_local=float(np.clip(local_pred, 0.0, 1.0)),
            intercept=float(intercept),
            model_score=float(np.clip(model_score, 0.0, 1.0)),
        )

    def explain_batch(
        self,
        feature_vectors: list[MLFeatureVector],
        *,
        num_features: int = 10,
        num_samples: int = 3000,
    ) -> list[LIMEExplanation]:
        """Generate LIME explanations for multiple predictions.

        Note: LIME explanations are independent per sample,
        so this loops through each. Consider parallelization
        for large batches.

        Args:
            feature_vectors: List of MLFeatureVector instances
            num_features: Number of top features per explanation
            num_samples: Number of samples per explanation

        Returns:
            List of LIMEExplanation instances
        """
        results = []

        for i, fv in enumerate(feature_vectors):
            try:
                explanation = self.explain(
                    fv,
                    num_features=num_features,
                    num_samples=num_samples,
                )
                results.append(explanation)
            except Exception as e:
                logger.warning(
                    "lime_explanation_failed",
                    cve_id=fv.cve_id,
                    error=str(e),
                    index=i,
                )
                # Return a default explanation on error
                results.append(
                    LIMEExplanation(
                        feature_contributions=[],
                        prediction_local=0.5,
                        intercept=0.0,
                        model_score=0.0,
                    )
                )

        logger.info("lime_batch_complete", n_explanations=len(results))

        return results

    @classmethod
    def from_model(
        cls,
        model: object,
        feature_names: list[str],
        training_data: np.ndarray | None = None,
        *,
        random_state: int | None = None,
    ) -> LIMEExplainer:
        """Create LIME explainer from a trained model.

        Args:
            model: Trained model with predict_proba method
            feature_names: Ordered list of feature names
            training_data: Training data for computing statistics
            random_state: Random state for reproducibility (M-03 fix)

        Returns:
            Configured LIMEExplainer
        """

        def predict_fn(X: np.ndarray) -> np.ndarray:
            """Wrapper for model's predict_proba."""
            # model typed as object; sklearn API has predict_proba at runtime
            result: np.ndarray = model.predict_proba(X)  # type: ignore[attr-defined]
            return result

        return cls(
            predict_fn=predict_fn,
            feature_names=feature_names,
            training_data=training_data,
            random_state=random_state,
        )


__all__ = ["LIMEExplainer"]
