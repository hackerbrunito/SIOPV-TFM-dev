"""XGBoost classifier implementation for risk classification.

Implements MLClassifierPort with XGBoost, SHAP, and LIME integration.
Based on specification section 3.3.

Security features (M-03 fix):
- Configurable random_state instead of hardcoded values
- Cryptographically secure random seeds in production
- Random state stored in model metadata for audit
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

import numpy as np
import optuna
import structlog
from imblearn.over_sampling import SMOTE
from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier as XGBClassifierBase

from siopv.adapters.ml.lime_explainer import LIMEExplainer
from siopv.adapters.ml.shap_explainer import SHAPExplainer
from siopv.application.ports.ml_classifier import MLClassifierPort, ModelTrainerPort
from siopv.domain.entities.ml_feature_vector import MLFeatureVector
from siopv.domain.value_objects.risk_score import (
    LIMEExplanation,
    RiskScore,
    SHAPValues,
)

logger = structlog.get_logger(__name__)


# Default feature names for the 14-feature vector
DEFAULT_FEATURE_NAMES = [
    "cvss_base_score",
    "attack_vector",
    "attack_complexity",
    "privileges_required",
    "user_interaction",
    "scope",
    "confidentiality_impact",
    "integrity_impact",
    "availability_impact",
    "epss_score",
    "epss_percentile",
    "days_since_publication",
    "has_exploit_ref",
    "cwe_category",
]

# Target metrics from specification
TARGET_PRECISION = 0.85
TARGET_RECALL = 0.90
TARGET_F1 = 0.87
TARGET_AUC_ROC = 0.92

# Default reproducible seed for dev/test environments
DEFAULT_DEV_RANDOM_STATE = 42


def _get_random_state(
    configured_value: int | None = None,
    *,
    environment: str | None = None,
) -> int:
    """Get random state based on configuration and environment.

    Security fix M-03: Avoids hardcoded predictable seeds in production.

    Args:
        configured_value: Explicitly configured random state (takes priority)
        environment: Override environment detection (for testing)

    Returns:
        Random state integer to use for ML operations

    Behavior:
        - If configured_value is provided: use it (explicit override)
        - In production (SIOPV_ENVIRONMENT=production): use cryptographic randomness
        - In dev/test: use DEFAULT_DEV_RANDOM_STATE (42) for reproducibility
    """
    # Explicit configuration takes priority
    if configured_value is not None:
        return configured_value

    # Detect environment
    env = environment or os.environ.get("SIOPV_ENVIRONMENT", "development")

    if env == "production":
        # Use cryptographically secure random number in production
        # secrets.randbelow is suitable for security-sensitive applications
        random_state = secrets.randbelow(2**32)
        logger.debug(
            "using_cryptographic_random_state",
            environment=env,
            random_state=random_state,
        )
        return random_state

    # Dev/test: use reproducible default
    logger.debug(
        "using_default_random_state",
        environment=env,
        random_state=DEFAULT_DEV_RANDOM_STATE,
    )
    return DEFAULT_DEV_RANDOM_STATE


class XGBoostClassifier(MLClassifierPort, ModelTrainerPort):
    """XGBoost-based risk classifier with XAI integration.

    Implements both MLClassifierPort (inference) and ModelTrainerPort (training).
    Uses SMOTE for class balancing and Optuna for hyperparameter optimization.

    Security: Random state is configurable and uses cryptographic randomness
    in production to avoid predictable ML operations.
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        *,
        feature_names: list[str] | None = None,
        model_version: str = "1.0.0",
        random_state: int | None = None,
    ) -> None:
        """Initialize XGBoost classifier.

        Args:
            model_path: Path to saved model (loads if exists)
            feature_names: Ordered list of feature names
            model_version: Version string for the model
            random_state: Random state for reproducibility.
                - If None: auto-detect based on environment
                - In production: uses cryptographic randomness
                - In dev/test: uses 42 for reproducibility
        """
        self._model_path = Path(model_path) if model_path else None
        self._feature_names = feature_names or DEFAULT_FEATURE_NAMES
        self._model_version = model_version
        self._configured_random_state = random_state

        self._model: XGBClassifierBase | None = None
        self._shap_explainer: SHAPExplainer | None = None
        self._lime_explainer: LIMEExplainer | None = None
        self._training_data: np.ndarray | None = None
        self._used_random_state: int | None = None  # Track actual random state used

        # Try to load model if path exists
        if self._model_path and self._model_path.exists():
            self.load_model(str(self._model_path))

        logger.info(
            "xgboost_classifier_initialized",
            model_path=str(self._model_path) if self._model_path else None,
            model_loaded=self._model is not None,
            random_state_configured=random_state,
        )

    def _get_training_random_state(self) -> int:
        """Get random state for training operations.

        Returns:
            Random state value, stored for audit purposes
        """
        if self._used_random_state is None:
            self._used_random_state = _get_random_state(self._configured_random_state)
        return self._used_random_state

    # === MLClassifierPort Implementation ===

    def predict(self, feature_vector: MLFeatureVector) -> RiskScore:
        """Predict exploitation risk with full XAI explanations."""
        self._ensure_model_loaded()

        # Get probability
        probability = self.predict_proba(feature_vector)

        # Get SHAP explanation
        shap_values = self.get_shap_values(feature_vector)

        # Get LIME explanation
        lime_explanation = self.get_lime_explanation(feature_vector)

        return RiskScore.from_prediction(
            cve_id=feature_vector.cve_id,
            probability=probability,
            shap_values=shap_values,
            lime_explanation=lime_explanation,
            model_version=self._model_version,
        )

    def predict_batch(
        self,
        feature_vectors: list[MLFeatureVector],
    ) -> list[RiskScore]:
        """Predict exploitation risk for multiple vulnerabilities."""
        self._ensure_model_loaded()

        if not feature_vectors:
            return []

        # Stack features
        X = np.vstack([fv.to_array().reshape(1, -1) for fv in feature_vectors])

        # Get probabilities
        if self._model is None:
            msg = "Model not loaded"
            raise RuntimeError(msg)
        probabilities = self._model.predict_proba(X)[:, 1]

        # Get SHAP explanations
        shap_values_list = self._get_shap_explainer().explain_batch(feature_vectors)

        # Get LIME explanations (can be slow for large batches)
        lime_explanations = self._get_lime_explainer().explain_batch(feature_vectors)

        # Build results
        results = []
        for i, fv in enumerate(feature_vectors):
            results.append(
                RiskScore.from_prediction(
                    cve_id=fv.cve_id,
                    probability=float(probabilities[i]),
                    shap_values=shap_values_list[i],
                    lime_explanation=lime_explanations[i],
                    model_version=self._model_version,
                )
            )

        logger.info("batch_prediction_complete", n_predictions=len(results))

        return results

    def predict_proba(self, feature_vector: MLFeatureVector) -> float:
        """Get raw probability prediction."""
        self._ensure_model_loaded()

        X = feature_vector.to_array().reshape(1, -1)
        if self._model is None:
            msg = "Model not loaded"
            raise RuntimeError(msg)
        proba = self._model.predict_proba(X)[0, 1]

        return float(proba)

    def get_shap_values(self, feature_vector: MLFeatureVector) -> SHAPValues:
        """Get SHAP feature importance for a prediction."""
        self._ensure_model_loaded()
        return self._get_shap_explainer().explain(feature_vector)

    def get_lime_explanation(self, feature_vector: MLFeatureVector) -> LIMEExplanation:
        """Get LIME local explanation for a prediction."""
        self._ensure_model_loaded()
        return self._get_lime_explainer().explain(feature_vector)

    def get_feature_importance(self) -> dict[str, float]:
        """Get global feature importance from the model."""
        self._ensure_model_loaded()
        if self._model is None:
            msg = "Model not loaded"
            raise RuntimeError(msg)
        importances = self._model.feature_importances_
        return dict(zip(self._feature_names, importances.tolist(), strict=True))

    def is_loaded(self) -> bool:
        """Check if model is loaded and ready."""
        return self._model is not None

    def get_training_metadata(self) -> dict[str, object]:
        """Get metadata about training for audit purposes.

        Returns:
            Dictionary with training configuration including random_state
        """
        return {
            "model_version": self._model_version,
            "feature_names": self._feature_names,
            "random_state_used": self._used_random_state,
            "random_state_configured": self._configured_random_state,
        }

    # === ModelTrainerPort Implementation ===

    def train(
        self,
        X: list[MLFeatureVector],
        y: list[int],
        *,
        optimize_hyperparams: bool = True,
        n_trials: int = 50,
        test_size: float = 0.2,
    ) -> dict[str, float]:
        """Train the classification model.

        Args:
            X: List of feature vectors
            y: List of labels (1 = exploited, 0 = not exploited)
            optimize_hyperparams: Whether to use Optuna
            n_trials: Number of Optuna trials
            test_size: Fraction for test split

        Returns:
            Dictionary with training metrics (includes random_state for audit)
        """
        # Get random state for this training session (M-03 fix)
        random_state = self._get_training_random_state()

        logger.info(
            "training_started",
            n_samples=len(X),
            n_positive=sum(y),
            optimize=optimize_hyperparams,
            random_state=random_state,
        )

        # Convert to numpy arrays
        X_array = np.vstack([fv.to_array().reshape(1, -1) for fv in X])
        y_array = np.array(y)

        # Store training data for LIME
        self._training_data = X_array

        # Split data (M-03 fix: use configured random_state)
        X_train, X_test, y_train, y_test = train_test_split(
            X_array, y_array, test_size=test_size, stratify=y_array, random_state=random_state
        )

        # Apply SMOTE for class balancing (M-03 fix: use configured random_state)
        logger.info("applying_smote", before_shape=X_train.shape)
        smote = SMOTE(sampling_strategy="auto", random_state=random_state)
        X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)
        logger.info(
            "smote_complete",
            after_shape=X_train_balanced.shape,
            class_distribution=dict(
                zip(*np.unique(y_train_balanced, return_counts=True), strict=True)
            ),
        )

        # Get hyperparameters (M-03 fix: pass random_state)
        if optimize_hyperparams:
            params = self._optimize_hyperparams(
                X_train_balanced,
                y_train_balanced,
                X_test,
                y_test,
                n_trials=n_trials,
                random_state=random_state,
            )
        else:
            params = self._default_params()

        # Train final model (M-03 fix: use configured random_state)
        self._model = XGBClassifierBase(
            **params,
            use_label_encoder=False,
            eval_metric="logloss",
            random_state=random_state,
        )

        self._model.fit(
            X_train_balanced,
            y_train_balanced,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )

        # Reset explainers (need to recreate with new model)
        self._shap_explainer = None
        self._lime_explainer = None

        # Evaluate on test set
        metrics = self.evaluate(
            [
                MLFeatureVector(
                    cve_id=f"eval_{i}", **dict(zip(self._feature_names, row, strict=True))
                )
                for i, row in enumerate(X_test)
            ],
            y_test.tolist(),
        )

        # Add random_state to metrics for audit (M-03 fix)
        metrics["random_state_used"] = random_state

        logger.info(
            "training_complete",
            precision=metrics["precision"],
            recall=metrics["recall"],
            f1=metrics["f1"],
            auc_roc=metrics["auc_roc"],
            random_state=random_state,
        )

        return metrics

    def evaluate(
        self,
        X: list[MLFeatureVector],
        y: list[int],
    ) -> dict[str, float]:
        """Evaluate model on test data."""
        self._ensure_model_loaded()

        X_array = np.vstack([fv.to_array().reshape(1, -1) for fv in X])
        y_array = np.array(y)
        if self._model is None:
            msg = "Model not loaded"
            raise RuntimeError(msg)
        y_pred = self._model.predict(X_array)
        y_proba = self._model.predict_proba(X_array)[:, 1]

        metrics = {
            "precision": float(precision_score(y_array, y_pred)),
            "recall": float(recall_score(y_array, y_pred)),
            "f1": float(f1_score(y_array, y_pred)),
            "auc_roc": float(roc_auc_score(y_array, y_proba)),
        }

        # Check against targets
        metrics["meets_precision_target"] = metrics["precision"] >= TARGET_PRECISION
        metrics["meets_recall_target"] = metrics["recall"] >= TARGET_RECALL
        metrics["meets_f1_target"] = metrics["f1"] >= TARGET_F1
        metrics["meets_auc_target"] = metrics["auc_roc"] >= TARGET_AUC_ROC

        return metrics

    def save_model(self, path: str) -> None:
        """Save trained model to disk."""
        self._ensure_model_loaded()

        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        if self._model is None:
            msg = "Model not loaded"
            raise RuntimeError(msg)
        self._model.save_model(str(save_path))
        logger.info("model_saved", path=str(save_path))

    def load_model(self, path: str) -> None:
        """Load trained model from disk."""
        load_path = Path(path)

        if not load_path.exists():
            msg = f"Model file not found: {load_path}"
            raise FileNotFoundError(msg)

        self._model = XGBClassifierBase()
        self._model.load_model(str(load_path))

        # Reset explainers
        self._shap_explainer = None
        self._lime_explainer = None

        logger.info("model_loaded", path=str(load_path))

    # === Private Methods ===

    def _ensure_model_loaded(self) -> None:
        """Raise error if model not loaded."""
        if self._model is None:
            msg = "Model not loaded. Call load_model() or train() first."
            raise RuntimeError(msg)

    def _get_shap_explainer(self) -> SHAPExplainer:
        """Get or create SHAP explainer."""
        if self._shap_explainer is None:
            if self._model is None:
                msg = "Model not loaded"
                raise RuntimeError(msg)
            self._shap_explainer = SHAPExplainer(
                model=self._model,
                feature_names=self._feature_names,
            )
        return self._shap_explainer

    def _get_lime_explainer(self) -> LIMEExplainer:
        """Get or create LIME explainer."""
        if self._lime_explainer is None:
            if self._model is None:
                msg = "Model not loaded"
                raise RuntimeError(msg)
            # Get random state for LIME (M-03 fix)
            random_state = self._get_training_random_state()
            self._lime_explainer = LIMEExplainer.from_model(
                model=self._model,
                feature_names=self._feature_names,
                training_data=self._training_data,
                random_state=random_state,
            )
        return self._lime_explainer

    def _default_params(self) -> dict[str, object]:
        """Return default XGBoost parameters."""
        return {
            "n_estimators": 100,
            "max_depth": 6,
            "learning_rate": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 1,
            "gamma": 0,
            "reg_alpha": 0,
            "reg_lambda": 1,
            "objective": "binary:logistic",
        }

    def _optimize_hyperparams(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        *,
        n_trials: int = 50,
        random_state: int,
    ) -> dict[str, object]:
        """Optimize hyperparameters using Optuna.

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            n_trials: Number of optimization trials
            random_state: Random state for reproducibility

        Returns:
            Best hyperparameters
        """
        logger.info("optuna_optimization_started", n_trials=n_trials, random_state=random_state)

        def objective(trial: optuna.Trial) -> float:
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 300),
                "max_depth": trial.suggest_int("max_depth", 3, 10),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                "gamma": trial.suggest_float("gamma", 0, 5),
                "reg_alpha": trial.suggest_float("reg_alpha", 0, 10),
                "reg_lambda": trial.suggest_float("reg_lambda", 0, 10),
                "objective": "binary:logistic",
                "use_label_encoder": False,
                "eval_metric": "logloss",
                "random_state": random_state,  # M-03 fix: use configured random_state
            }

            model = XGBClassifierBase(**params)
            model.fit(
                X_train,
                y_train,
                eval_set=[(X_val, y_val)],
                verbose=False,
            )

            y_pred = model.predict(X_val)
            return float(f1_score(y_val, y_pred))

        # M-03 fix: seed Optuna sampler for reproducibility
        sampler = optuna.samplers.TPESampler(seed=random_state)
        study = optuna.create_study(direction="maximize", sampler=sampler)
        study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

        best_params = study.best_params
        best_params["objective"] = "binary:logistic"

        logger.info(
            "optuna_optimization_complete",
            best_f1=study.best_value,
            best_params=best_params,
            random_state=random_state,
        )

        return best_params  # type: ignore[no-any-return]


__all__ = ["XGBoostClassifier"]
