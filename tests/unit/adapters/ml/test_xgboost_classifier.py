"""Unit tests for XGBoostClassifier.

Tests the ML classifier implementation including training,
prediction, SHAP/LIME integration, and model persistence.

FIXED: Uses proper mocks to avoid real XGBoost training for faster tests.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from siopv.adapters.ml.xgboost_classifier import (
    DEFAULT_DEV_RANDOM_STATE,
    DEFAULT_FEATURE_NAMES,
    XGBoostClassifier,
    _get_random_state,
)
from siopv.domain.entities.ml_feature_vector import MLFeatureVector
from siopv.domain.value_objects.risk_score import (
    LIMEExplanation,
    RiskScore,
    SHAPValues,
)

# === Fixtures ===


@pytest.fixture
def sample_feature_vector() -> MLFeatureVector:
    """Create a sample feature vector for testing."""
    return MLFeatureVector(
        cve_id="CVE-2021-44228",
        cvss_base_score=10.0,
        attack_vector=3,
        attack_complexity=1,
        privileges_required=2,
        user_interaction=1,
        scope=1,
        confidentiality_impact=2,
        integrity_impact=2,
        availability_impact=2,
        epss_score=0.975,
        epss_percentile=0.999,
        days_since_publication=1000,
        has_exploit_ref=1,
        cwe_category=0.78,
    )


@pytest.fixture
def sample_training_data() -> tuple[list[MLFeatureVector], list[int]]:
    """Create sample training data."""
    np.random.seed(42)  # For reproducibility
    X = []
    y = []

    # Create 20 positive samples
    for i in range(20):
        X.append(
            MLFeatureVector(
                cve_id=f"CVE-2021-{i:04d}",
                cvss_base_score=9.0 + np.random.random(),
                attack_vector=3,
                attack_complexity=1,
                privileges_required=2,
                user_interaction=1,
                scope=1,
                confidentiality_impact=2,
                integrity_impact=2,
                availability_impact=2,
                epss_score=0.9 + np.random.random() * 0.1,
                epss_percentile=0.95 + np.random.random() * 0.05,
                days_since_publication=500 + int(np.random.random() * 500),
                has_exploit_ref=1,
                cwe_category=0.75 + np.random.random() * 0.1,
            )
        )
        y.append(1)

    # Create 20 negative samples
    for i in range(20, 40):
        X.append(
            MLFeatureVector(
                cve_id=f"CVE-2021-{i:04d}",
                cvss_base_score=3.0 + np.random.random() * 3,
                attack_vector=1,
                attack_complexity=0,
                privileges_required=0,
                user_interaction=0,
                scope=0,
                confidentiality_impact=0,
                integrity_impact=0,
                availability_impact=1,
                epss_score=0.05 + np.random.random() * 0.1,
                epss_percentile=0.1 + np.random.random() * 0.2,
                days_since_publication=1000 + int(np.random.random() * 500),
                has_exploit_ref=0,
                cwe_category=0.3 + np.random.random() * 0.1,
            )
        )
        y.append(0)

    return X, y


@pytest.fixture
def mock_xgb_model() -> Mock:
    """Create a mock XGBoost model with all required methods."""
    mock = MagicMock()
    # Mock predict_proba to return realistic probabilities
    mock.predict_proba.return_value = np.array([[0.15, 0.85]])
    mock.predict.return_value = np.array([1])
    # Mock feature importance (14 features)
    mock.feature_importances_ = np.array(
        [0.15, 0.08, 0.03, 0.05, 0.02, 0.04, 0.06, 0.05, 0.04, 0.25, 0.10, 0.03, 0.07, 0.03]
    )
    mock.save_model = Mock()
    mock.load_model = Mock()
    # Mock fit to do nothing
    mock.fit = Mock()
    return mock


@pytest.fixture
def mock_shap_values() -> SHAPValues:
    """Create mock SHAP values."""
    return SHAPValues(
        feature_names=DEFAULT_FEATURE_NAMES,
        shap_values=[
            0.15,
            0.08,
            0.03,
            0.05,
            0.02,
            0.04,
            0.06,
            0.05,
            0.04,
            0.25,
            0.10,
            -0.02,
            0.12,
            0.03,
        ],
        base_value=0.35,
    )


@pytest.fixture
def mock_lime_explanation() -> LIMEExplanation:
    """Create mock LIME explanation."""
    return LIMEExplanation(
        feature_contributions=[
            ("epss_score > 0.9", 0.25),
            ("cvss_base_score > 9.0", 0.15),
            ("has_exploit_ref = 1", 0.12),
        ],
        prediction_local=0.85,
        intercept=0.35,
        model_score=0.92,
    )


@pytest.fixture
def temp_model_path() -> Path:
    """Create a temporary path for model saving."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        return Path(f.name)


# === Initialization Tests ===


class TestXGBoostClassifierInit:
    """Tests for XGBoostClassifier initialization."""

    def test_init_without_model(self):
        """Test initialization without loading a model."""
        classifier = XGBoostClassifier()

        assert not classifier.is_loaded()
        assert classifier._feature_names == DEFAULT_FEATURE_NAMES
        assert classifier._model_version == "1.0.0"

    def test_init_with_custom_features(self):
        """Test initialization with custom feature names."""
        custom_features = ["feature1", "feature2"]
        classifier = XGBoostClassifier(feature_names=custom_features)

        assert classifier._feature_names == custom_features

    def test_init_with_version(self):
        """Test initialization with custom version."""
        classifier = XGBoostClassifier(model_version="2.0.0")

        assert classifier._model_version == "2.0.0"

    def test_init_with_nonexistent_path(self):
        """Test initialization with non-existent model path."""
        classifier = XGBoostClassifier(model_path="/nonexistent/model.json")

        assert not classifier.is_loaded()

    def test_init_with_random_state(self):
        """Test initialization with custom random state."""
        classifier = XGBoostClassifier(random_state=123)

        assert classifier._configured_random_state == 123


# === Random State Tests ===


class TestRandomStateFunction:
    """Tests for _get_random_state function."""

    def test_get_random_state_with_configured_value(self):
        """Test that configured value takes priority."""
        result = _get_random_state(configured_value=123)
        assert result == 123

    def test_get_random_state_development_default(self):
        """Test default random state in development environment."""
        result = _get_random_state(environment="development")
        assert result == DEFAULT_DEV_RANDOM_STATE

    def test_get_random_state_test_default(self):
        """Test default random state in test environment."""
        result = _get_random_state(environment="test")
        assert result == DEFAULT_DEV_RANDOM_STATE

    def test_get_random_state_production_cryptographic(self):
        """Test cryptographic random state in production."""
        result = _get_random_state(environment="production")
        # Should be a valid integer
        assert isinstance(result, int)
        assert 0 <= result < 2**32


# === Training Tests with Mocks ===


def _generate_valid_feature_array(n_samples: int, seed: int = 42) -> np.ndarray:
    """Generate valid feature arrays that conform to MLFeatureVector constraints.

    Feature order: cvss_base_score, attack_vector, attack_complexity, privileges_required,
    user_interaction, scope, confidentiality_impact, integrity_impact, availability_impact,
    epss_score, epss_percentile, days_since_publication, has_exploit_ref, cwe_category
    """
    rng = np.random.default_rng(seed)
    data = np.zeros((n_samples, 14), dtype=np.float32)

    for i in range(n_samples):
        data[i] = [
            rng.uniform(0.0, 10.0),  # cvss_base_score (0-10)
            rng.integers(0, 4),  # attack_vector (0-3)
            rng.integers(0, 2),  # attack_complexity (0-1)
            rng.integers(0, 3),  # privileges_required (0-2)
            rng.integers(0, 2),  # user_interaction (0-1)
            rng.integers(0, 2),  # scope (0-1)
            rng.integers(0, 3),  # confidentiality_impact (0-2)
            rng.integers(0, 3),  # integrity_impact (0-2)
            rng.integers(0, 3),  # availability_impact (0-2)
            rng.uniform(0.0, 1.0),  # epss_score (0-1)
            rng.uniform(0.0, 1.0),  # epss_percentile (0-1)
            rng.integers(0, 1000),  # days_since_publication (>=0)
            rng.integers(0, 2),  # has_exploit_ref (0-1)
            rng.uniform(0.0, 1.0),  # cwe_category (target encoded float)
        ]

    return data


class TestXGBoostClassifierTraining:
    """Tests for model training functionality using mocks."""

    @patch("siopv.adapters.ml.xgboost_classifier.XGBClassifierBase")
    @patch("siopv.adapters.ml.xgboost_classifier.SMOTE")
    @patch("siopv.adapters.ml.xgboost_classifier.train_test_split")
    def test_train_with_default_params(
        self, mock_split, mock_smote, mock_xgb_class, sample_training_data, mock_xgb_model
    ):
        """Test training with default parameters using mocks."""
        X, y = sample_training_data

        # Setup mocks - use valid feature arrays instead of random data
        mock_xgb_class.return_value = mock_xgb_model
        mock_split.return_value = (
            _generate_valid_feature_array(32, seed=1),  # X_train
            _generate_valid_feature_array(8, seed=2),  # X_test
            np.array([1] * 16 + [0] * 16),  # y_train
            np.array([1] * 4 + [0] * 4),  # y_test
        )
        mock_smote_instance = Mock()
        mock_smote_instance.fit_resample.return_value = (
            _generate_valid_feature_array(40, seed=3),
            np.array([1] * 20 + [0] * 20),
        )
        mock_smote.return_value = mock_smote_instance

        # Mock predict for evaluation
        mock_xgb_model.predict.return_value = np.array([1, 1, 1, 1, 0, 0, 0, 0])
        mock_xgb_model.predict_proba.return_value = np.array(
            [
                [0.1, 0.9],
                [0.1, 0.9],
                [0.2, 0.8],
                [0.15, 0.85],
                [0.9, 0.1],
                [0.85, 0.15],
                [0.8, 0.2],
                [0.9, 0.1],
            ]
        )

        classifier = XGBoostClassifier()
        metrics = classifier.train(X, y, optimize_hyperparams=False)

        assert classifier.is_loaded()
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics
        assert "auc_roc" in metrics
        assert "random_state_used" in metrics
        mock_xgb_class.assert_called_once()
        mock_xgb_model.fit.assert_called_once()

    @patch("siopv.adapters.ml.xgboost_classifier.XGBClassifierBase")
    @patch("siopv.adapters.ml.xgboost_classifier.SMOTE")
    @patch("siopv.adapters.ml.xgboost_classifier.train_test_split")
    def test_train_stores_training_data(
        self, mock_split, mock_smote, mock_xgb_class, sample_training_data, mock_xgb_model
    ):
        """Test that training stores data for LIME."""
        X, y = sample_training_data

        # Setup mocks - use valid feature arrays
        mock_xgb_class.return_value = mock_xgb_model
        mock_split.return_value = (
            _generate_valid_feature_array(32, seed=4),
            _generate_valid_feature_array(8, seed=5),
            np.array([1] * 16 + [0] * 16),
            np.array([1] * 4 + [0] * 4),
        )
        mock_smote_instance = Mock()
        mock_smote_instance.fit_resample.return_value = (
            _generate_valid_feature_array(40, seed=6),
            np.array([1] * 20 + [0] * 20),
        )
        mock_smote.return_value = mock_smote_instance
        mock_xgb_model.predict.return_value = np.array([1, 1, 1, 1, 0, 0, 0, 0])
        mock_xgb_model.predict_proba.return_value = np.array(
            [
                [0.1, 0.9],
                [0.1, 0.9],
                [0.2, 0.8],
                [0.15, 0.85],
                [0.9, 0.1],
                [0.85, 0.15],
                [0.8, 0.2],
                [0.9, 0.1],
            ]
        )

        classifier = XGBoostClassifier()
        classifier.train(X, y, optimize_hyperparams=False)

        assert classifier._training_data is not None
        assert classifier._training_data.shape[0] > 0

    @patch("siopv.adapters.ml.xgboost_classifier.optuna")
    @patch("siopv.adapters.ml.xgboost_classifier.XGBClassifierBase")
    @patch("siopv.adapters.ml.xgboost_classifier.SMOTE")
    @patch("siopv.adapters.ml.xgboost_classifier.train_test_split")
    def test_train_with_optimization(
        self,
        mock_split,
        mock_smote,
        mock_xgb_class,
        mock_optuna,
        sample_training_data,
        mock_xgb_model,
    ):
        """Test training with hyperparameter optimization."""
        X, y = sample_training_data

        # Setup mocks - use valid feature arrays
        mock_xgb_class.return_value = mock_xgb_model
        mock_split.return_value = (
            _generate_valid_feature_array(32, seed=7),
            _generate_valid_feature_array(8, seed=8),
            np.array([1] * 16 + [0] * 16),
            np.array([1] * 4 + [0] * 4),
        )
        mock_smote_instance = Mock()
        mock_smote_instance.fit_resample.return_value = (
            _generate_valid_feature_array(40, seed=9),
            np.array([1] * 20 + [0] * 20),
        )
        mock_smote.return_value = mock_smote_instance
        mock_xgb_model.predict.return_value = np.array([1, 1, 1, 1, 0, 0, 0, 0])
        mock_xgb_model.predict_proba.return_value = np.array(
            [
                [0.1, 0.9],
                [0.1, 0.9],
                [0.2, 0.8],
                [0.15, 0.85],
                [0.9, 0.1],
                [0.85, 0.15],
                [0.8, 0.2],
                [0.9, 0.1],
            ]
        )

        # Mock Optuna study
        mock_study = Mock()
        mock_study.best_params = {
            "n_estimators": 100,
            "max_depth": 5,
            "learning_rate": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 1,
            "gamma": 0.1,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
        }
        mock_study.best_value = 0.85
        mock_optuna.create_study.return_value = mock_study
        mock_optuna.samplers.TPESampler.return_value = Mock()

        classifier = XGBoostClassifier()
        metrics = classifier.train(X, y, optimize_hyperparams=True, n_trials=5)

        assert classifier.is_loaded()
        mock_optuna.create_study.assert_called_once()


# === Prediction Tests with Mocks ===


class TestXGBoostClassifierPrediction:
    """Tests for prediction functionality using mocks."""

    def test_predict_proba(self, sample_feature_vector, mock_xgb_model):
        """Test probability prediction."""
        classifier = XGBoostClassifier()
        classifier._model = mock_xgb_model

        proba = classifier.predict_proba(sample_feature_vector)

        assert isinstance(proba, float)
        assert 0 <= proba <= 1
        assert proba == 0.85  # From mock

    @patch("siopv.adapters.ml.xgboost_classifier.SHAPExplainer")
    @patch("siopv.adapters.ml.xgboost_classifier.LIMEExplainer")
    def test_predict_with_explanations(
        self,
        mock_lime_class,
        mock_shap_class,
        sample_feature_vector,
        mock_xgb_model,
        mock_shap_values,
        mock_lime_explanation,
    ):
        """Test full prediction with XAI explanations."""
        classifier = XGBoostClassifier()
        classifier._model = mock_xgb_model

        # Setup SHAP mock
        mock_shap_instance = Mock()
        mock_shap_instance.explain.return_value = mock_shap_values
        mock_shap_class.return_value = mock_shap_instance

        # Setup LIME mock
        mock_lime_instance = Mock()
        mock_lime_instance.explain.return_value = mock_lime_explanation
        mock_lime_class.from_model.return_value = mock_lime_instance

        risk_score = classifier.predict(sample_feature_vector)

        assert isinstance(risk_score, RiskScore)
        assert risk_score.cve_id == "CVE-2021-44228"
        assert 0 <= risk_score.risk_probability <= 1
        assert risk_score.shap_values is not None
        assert risk_score.lime_explanation is not None

    @patch("siopv.adapters.ml.xgboost_classifier.SHAPExplainer")
    @patch("siopv.adapters.ml.xgboost_classifier.LIMEExplainer")
    def test_predict_batch(
        self,
        mock_lime_class,
        mock_shap_class,
        mock_xgb_model,
        mock_shap_values,
        mock_lime_explanation,
    ):
        """Test batch prediction."""
        classifier = XGBoostClassifier()
        classifier._model = mock_xgb_model

        # Mock batch predictions
        mock_xgb_model.predict_proba.return_value = np.array(
            [[0.15, 0.85], [0.20, 0.80], [0.10, 0.90]]
        )

        # Setup SHAP mock
        mock_shap_instance = Mock()
        mock_shap_instance.explain_batch.return_value = [mock_shap_values] * 3
        mock_shap_class.return_value = mock_shap_instance

        # Setup LIME mock
        mock_lime_instance = Mock()
        mock_lime_instance.explain_batch.return_value = [mock_lime_explanation] * 3
        mock_lime_class.from_model.return_value = mock_lime_instance

        feature_vectors = [
            MLFeatureVector(
                cve_id=f"CVE-2021-{i:04d}",
                cvss_base_score=8.0 + i,
                attack_vector=3,
                attack_complexity=1,
                privileges_required=2,
                user_interaction=1,
                scope=1,
                confidentiality_impact=2,
                integrity_impact=2,
                availability_impact=2,
                epss_score=0.9,
                epss_percentile=0.95,
                days_since_publication=500,
                has_exploit_ref=1,
                cwe_category=0.78,
            )
            for i in range(3)
        ]

        results = classifier.predict_batch(feature_vectors)

        assert len(results) == 3
        assert all(isinstance(r, RiskScore) for r in results)
        assert all(0 <= r.risk_probability <= 1 for r in results)

    def test_predict_batch_empty(self, mock_xgb_model):
        """Test batch prediction with empty input."""
        classifier = XGBoostClassifier()
        classifier._model = mock_xgb_model

        results = classifier.predict_batch([])

        assert results == []

    def test_predict_without_model_raises_error(self, sample_feature_vector):
        """Test that prediction without loaded model raises error."""
        classifier = XGBoostClassifier()

        with pytest.raises(RuntimeError, match="Model not loaded"):
            classifier.predict_proba(sample_feature_vector)


# === XAI Tests with Mocks ===


class TestXGBoostClassifierXAI:
    """Tests for XAI functionality using mocks."""

    @patch("siopv.adapters.ml.xgboost_classifier.SHAPExplainer")
    def test_get_shap_values(
        self, mock_shap_class, sample_feature_vector, mock_xgb_model, mock_shap_values
    ):
        """Test SHAP value generation."""
        classifier = XGBoostClassifier()
        classifier._model = mock_xgb_model

        mock_shap_instance = Mock()
        mock_shap_instance.explain.return_value = mock_shap_values
        mock_shap_class.return_value = mock_shap_instance

        shap_values = classifier.get_shap_values(sample_feature_vector)

        assert isinstance(shap_values, SHAPValues)
        assert len(shap_values.feature_names) == 14
        assert len(shap_values.shap_values) == 14
        assert shap_values.base_value is not None

    @patch("siopv.adapters.ml.xgboost_classifier.LIMEExplainer")
    def test_get_lime_explanation(
        self, mock_lime_class, sample_feature_vector, mock_xgb_model, mock_lime_explanation
    ):
        """Test LIME explanation generation."""
        classifier = XGBoostClassifier()
        classifier._model = mock_xgb_model

        mock_lime_instance = Mock()
        mock_lime_instance.explain.return_value = mock_lime_explanation
        mock_lime_class.from_model.return_value = mock_lime_instance

        lime_explanation = classifier.get_lime_explanation(sample_feature_vector)

        assert isinstance(lime_explanation, LIMEExplanation)
        assert len(lime_explanation.feature_contributions) > 0
        assert 0 <= lime_explanation.prediction_local <= 1

    def test_get_feature_importance(self, mock_xgb_model):
        """Test global feature importance."""
        classifier = XGBoostClassifier()
        classifier._model = mock_xgb_model

        importance = classifier.get_feature_importance()

        assert len(importance) == 14
        assert all(name in importance for name in DEFAULT_FEATURE_NAMES)

    @patch("siopv.adapters.ml.xgboost_classifier.SHAPExplainer")
    def test_explainers_are_cached(
        self, mock_shap_class, sample_feature_vector, mock_xgb_model, mock_shap_values
    ):
        """Test that explainers are cached after first use."""
        classifier = XGBoostClassifier()
        classifier._model = mock_xgb_model

        mock_shap_instance = Mock()
        mock_shap_instance.explain.return_value = mock_shap_values
        mock_shap_class.return_value = mock_shap_instance

        # First call creates explainer
        classifier.get_shap_values(sample_feature_vector)
        shap_explainer_1 = classifier._shap_explainer

        # Second call reuses same explainer
        classifier.get_shap_values(sample_feature_vector)
        shap_explainer_2 = classifier._shap_explainer

        assert shap_explainer_1 is shap_explainer_2
        # SHAPExplainer should only be instantiated once
        assert mock_shap_class.call_count == 1


# === Persistence Tests ===


class TestXGBoostClassifierPersistence:
    """Tests for model save/load functionality."""

    def test_save_model(self, mock_xgb_model, temp_model_path):
        """Test model saving."""
        classifier = XGBoostClassifier()
        classifier._model = mock_xgb_model

        classifier.save_model(str(temp_model_path))

        mock_xgb_model.save_model.assert_called_once()

    @patch("siopv.adapters.ml.xgboost_classifier.XGBClassifierBase")
    def test_load_model(self, mock_xgb_class, temp_model_path):
        """Test model loading."""
        # Create a mock file
        temp_model_path.touch()

        mock_xgb_instance = Mock()
        mock_xgb_class.return_value = mock_xgb_instance

        classifier = XGBoostClassifier()
        classifier.load_model(str(temp_model_path))

        assert classifier.is_loaded()
        mock_xgb_instance.load_model.assert_called_once()

    def test_load_nonexistent_model_raises_error(self):
        """Test loading non-existent model raises error."""
        classifier = XGBoostClassifier()

        with pytest.raises(FileNotFoundError):
            classifier.load_model("/nonexistent/model.json")

    def test_save_creates_directory(self, mock_xgb_model):
        """Test that save creates parent directories."""
        classifier = XGBoostClassifier()
        classifier._model = mock_xgb_model

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dir" / "model.json"
            classifier.save_model(str(path))

            mock_xgb_model.save_model.assert_called_once()
            assert path.parent.exists()


# === Edge Cases ===


class TestXGBoostClassifierEdgeCases:
    """Tests for edge cases and error handling."""

    def test_default_params_returns_dict(self):
        """Test default parameters method."""
        classifier = XGBoostClassifier()
        params = classifier._default_params()

        assert isinstance(params, dict)
        assert "n_estimators" in params
        assert "max_depth" in params
        assert "learning_rate" in params
        assert params["objective"] == "binary:logistic"

    def test_get_training_metadata(self):
        """Test training metadata retrieval."""
        classifier = XGBoostClassifier(random_state=42, model_version="2.0.0")

        metadata = classifier.get_training_metadata()

        assert metadata["model_version"] == "2.0.0"
        assert metadata["random_state_configured"] == 42
        assert metadata["feature_names"] == DEFAULT_FEATURE_NAMES

    def test_ensure_model_loaded_raises_error(self):
        """Test that _ensure_model_loaded raises error when no model."""
        classifier = XGBoostClassifier()

        with pytest.raises(RuntimeError, match="Model not loaded"):
            classifier._ensure_model_loaded()


# === Evaluation Tests ===


class TestXGBoostClassifierEvaluation:
    """Tests for model evaluation."""

    def test_evaluate(self, mock_xgb_model, sample_training_data):
        """Test model evaluation."""
        X, y = sample_training_data
        classifier = XGBoostClassifier()
        classifier._model = mock_xgb_model

        # Setup mock predictions
        mock_xgb_model.predict.return_value = np.array([1] * 20 + [0] * 20)
        mock_xgb_model.predict_proba.return_value = np.vstack(
            [np.array([[0.1, 0.9]] * 20), np.array([[0.9, 0.1]] * 20)]
        )

        metrics = classifier.evaluate(X, y)

        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics
        assert "auc_roc" in metrics
        assert "meets_precision_target" in metrics
        assert "meets_recall_target" in metrics
        assert "meets_f1_target" in metrics
        assert "meets_auc_target" in metrics
        # Perfect predictions
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0


# === Integration Tests with Mocks ===


class TestXGBoostClassifierIntegration:
    """Integration tests for complete workflows using mocks."""

    @patch("siopv.adapters.ml.xgboost_classifier.SHAPExplainer")
    @patch("siopv.adapters.ml.xgboost_classifier.LIMEExplainer")
    def test_full_prediction_pipeline(
        self,
        mock_lime_class,
        mock_shap_class,
        sample_feature_vector,
        mock_xgb_model,
        mock_shap_values,
        mock_lime_explanation,
    ):
        """Test complete prediction pipeline with mocks."""
        classifier = XGBoostClassifier(model_version="test-1.0")
        classifier._model = mock_xgb_model

        # Setup SHAP mock
        mock_shap_instance = Mock()
        mock_shap_instance.explain.return_value = mock_shap_values
        mock_shap_class.return_value = mock_shap_instance

        # Setup LIME mock
        mock_lime_instance = Mock()
        mock_lime_instance.explain.return_value = mock_lime_explanation
        mock_lime_class.from_model.return_value = mock_lime_instance

        # Make prediction
        risk_score = classifier.predict(sample_feature_vector)

        # Verify prediction
        assert isinstance(risk_score, RiskScore)
        assert risk_score.shap_values is not None
        assert risk_score.lime_explanation is not None
        assert risk_score.model_version == "test-1.0"
        assert risk_score.risk_probability == 0.85
