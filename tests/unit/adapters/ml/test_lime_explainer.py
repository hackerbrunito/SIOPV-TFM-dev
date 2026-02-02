"""Unit tests for LIMEExplainer.

Tests LIME-based local explanations for XGBoost model predictions.

FIXED: Proper mock configuration for LimeTabularExplainer and Explanation objects.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import numpy as np
import pytest

from siopv.adapters.ml.lime_explainer import DEFAULT_RANDOM_STATE, LIMEExplainer
from siopv.domain.entities.ml_feature_vector import MLFeatureVector
from siopv.domain.value_objects.risk_score import LIMEExplanation

# === Fixtures ===


@pytest.fixture
def feature_names() -> list[str]:
    """Standard feature names."""
    return [
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


@pytest.fixture
def sample_feature_vector() -> MLFeatureVector:
    """Create a sample feature vector."""
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
def predict_fn():
    """Create a mock prediction function."""

    def _predict(X: np.ndarray) -> np.ndarray:
        # Return probabilities for not_exploited, exploited
        return np.array([[0.2, 0.8]] * len(X))

    return _predict


@pytest.fixture
def training_data() -> np.ndarray:
    """Create sample training data."""
    np.random.seed(42)
    return np.random.randn(100, 14)


@pytest.fixture
def mock_lime_explanation() -> Mock:
    """Create a properly configured mock LIME Explanation object.

    FIXED: Includes all required attributes that the LIMEExplainer expects.
    """
    mock = Mock()
    # as_list returns list of (feature_condition, contribution) tuples
    mock.as_list.return_value = [
        ("epss_score > 0.9", 0.25),
        ("cvss_base_score > 9.0", 0.15),
        ("has_exploit_ref = 1", 0.12),
    ]
    # local_pred is a list/array with prediction value
    mock.local_pred = np.array([0.85])
    # score is the R-squared of local model
    mock.score = 0.92
    # intercept is a list/array with intercept per class
    mock.intercept = np.array([0.25, 0.35])
    return mock


# === Initialization Tests ===


class TestLIMEExplainerInit:
    """Tests for LIMEExplainer initialization."""

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_init_with_training_data(
        self, mock_lime_class, predict_fn, feature_names, training_data
    ):
        """Test initialization with training data."""
        mock_lime_class.return_value = Mock()

        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            training_data=training_data,
        )

        assert explainer._predict_fn is predict_fn
        assert explainer._feature_names == feature_names
        assert explainer._class_names == ["not_exploited", "exploited"]
        assert explainer._mode == "classification"
        assert explainer._random_state == DEFAULT_RANDOM_STATE

        # Verify LimeTabularExplainer was called with correct args
        mock_lime_class.assert_called_once()
        call_kwargs = mock_lime_class.call_args[1]
        assert call_kwargs["feature_names"] == feature_names
        assert call_kwargs["random_state"] == DEFAULT_RANDOM_STATE

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_init_without_training_data(self, mock_lime_class, predict_fn, feature_names):
        """Test initialization without training data."""
        mock_lime_class.return_value = Mock()

        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
        )

        assert explainer._predict_fn is predict_fn
        assert explainer._explainer is not None

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_init_with_custom_class_names(self, mock_lime_class, predict_fn, feature_names):
        """Test initialization with custom class names."""
        mock_lime_class.return_value = Mock()
        custom_names = ["safe", "dangerous"]

        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            class_names=custom_names,
        )

        assert explainer._class_names == custom_names

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_init_regression_mode(self, mock_lime_class, predict_fn, feature_names):
        """Test initialization in regression mode."""
        mock_lime_class.return_value = Mock()

        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            mode="regression",
        )

        assert explainer._mode == "regression"

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_init_with_custom_random_state(self, mock_lime_class, predict_fn, feature_names):
        """Test initialization with custom random state."""
        mock_lime_class.return_value = Mock()

        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            random_state=123,
        )

        assert explainer._random_state == 123
        call_kwargs = mock_lime_class.call_args[1]
        assert call_kwargs["random_state"] == 123


# === Explanation Tests ===


class TestLIMEExplainerExplanations:
    """Tests for LIME explanation generation."""

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_explain_single(
        self,
        mock_lime_class,
        predict_fn,
        feature_names,
        sample_feature_vector,
        mock_lime_explanation,
    ):
        """Test explaining a single prediction."""
        # Setup mock
        mock_explainer_instance = Mock()
        mock_explainer_instance.explain_instance.return_value = mock_lime_explanation
        mock_lime_class.return_value = mock_explainer_instance

        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
        )
        lime_explanation = explainer.explain(sample_feature_vector)

        assert isinstance(lime_explanation, LIMEExplanation)
        assert len(lime_explanation.feature_contributions) == 3
        assert 0 <= lime_explanation.prediction_local <= 1
        assert lime_explanation.prediction_local == pytest.approx(0.85)
        assert lime_explanation.model_score == pytest.approx(0.92)
        assert lime_explanation.intercept == pytest.approx(0.35)

        # Verify explain_instance was called correctly
        mock_explainer_instance.explain_instance.assert_called_once()
        call_args = mock_explainer_instance.explain_instance.call_args
        assert call_args[1]["num_features"] == 10  # default
        assert call_args[1]["num_samples"] == 5000  # default
        assert call_args[1]["labels"] == (1,)  # Positive class

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_explain_with_custom_params(
        self,
        mock_lime_class,
        predict_fn,
        feature_names,
        sample_feature_vector,
        mock_lime_explanation,
    ):
        """Test explanation with custom parameters."""
        mock_explainer_instance = Mock()
        mock_explainer_instance.explain_instance.return_value = mock_lime_explanation
        mock_lime_class.return_value = mock_explainer_instance

        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
        )
        lime_explanation = explainer.explain(
            sample_feature_vector, num_features=5, num_samples=1000
        )

        assert isinstance(lime_explanation, LIMEExplanation)
        # Verify explain_instance was called with correct params
        call_kwargs = mock_explainer_instance.explain_instance.call_args[1]
        assert call_kwargs["num_features"] == 5
        assert call_kwargs["num_samples"] == 1000

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_explain_batch(self, mock_lime_class, predict_fn, feature_names, mock_lime_explanation):
        """Test explaining multiple predictions."""
        mock_explainer_instance = Mock()
        mock_explainer_instance.explain_instance.return_value = mock_lime_explanation
        mock_lime_class.return_value = mock_explainer_instance

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

        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
        )
        explanations = explainer.explain_batch(feature_vectors)

        assert len(explanations) == 3
        assert all(isinstance(exp, LIMEExplanation) for exp in explanations)
        # explain_instance should be called 3 times
        assert mock_explainer_instance.explain_instance.call_count == 3

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_explain_batch_with_error_handling(
        self, mock_lime_class, predict_fn, feature_names, mock_lime_explanation
    ):
        """Test batch explanation with error handling."""
        mock_explainer_instance = Mock()
        # First call succeeds, second fails, third succeeds
        mock_explainer_instance.explain_instance.side_effect = [
            mock_lime_explanation,
            RuntimeError("LIME failed"),
            mock_lime_explanation,
        ]
        mock_lime_class.return_value = mock_explainer_instance

        feature_vectors = [
            MLFeatureVector(
                cve_id=f"CVE-2021-{i:04d}",
                cvss_base_score=8.0,
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

        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
        )
        explanations = explainer.explain_batch(feature_vectors)

        # Should return 3 explanations, with default for the failed one
        assert len(explanations) == 3
        assert explanations[1].feature_contributions == []  # Failed explanation
        assert explanations[1].prediction_local == 0.5
        assert explanations[1].model_score == 0.0

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_explain_batch_empty(self, mock_lime_class, predict_fn, feature_names):
        """Test explaining empty batch."""
        mock_lime_class.return_value = Mock()

        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
        )
        explanations = explainer.explain_batch([])

        assert explanations == []


# === Factory Method Tests ===


class TestLIMEExplainerFactory:
    """Tests for from_model factory method."""

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_from_model(self, mock_lime_class, feature_names, training_data):
        """Test creating explainer from model."""
        mock_lime_class.return_value = Mock()

        # Mock model with predict_proba
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.2, 0.8]])

        explainer = LIMEExplainer.from_model(
            model=mock_model,
            feature_names=feature_names,
            training_data=training_data,
        )

        assert isinstance(explainer, LIMEExplainer)
        assert explainer._feature_names == feature_names

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_from_model_with_random_state(self, mock_lime_class, feature_names):
        """Test from_model with custom random state."""
        mock_lime_class.return_value = Mock()
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.2, 0.8]])

        explainer = LIMEExplainer.from_model(
            model=mock_model,
            feature_names=feature_names,
            random_state=123,
        )

        assert explainer._random_state == 123

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_from_model_predict_fn_works(self, mock_lime_class, feature_names):
        """Test that predict_fn created from model works."""
        mock_lime_class.return_value = Mock()

        # Mock model
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.3, 0.7], [0.4, 0.6]])

        explainer = LIMEExplainer.from_model(
            model=mock_model,
            feature_names=feature_names,
        )

        # Call predict_fn
        X = np.random.randn(2, 14)
        predictions = explainer._predict_fn(X)

        assert predictions.shape == (2, 2)
        mock_model.predict_proba.assert_called_once()


# === Edge Cases ===


class TestLIMEExplainerEdgeCases:
    """Tests for edge cases and error handling."""

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_explain_with_missing_attributes(
        self, mock_lime_class, predict_fn, feature_names, sample_feature_vector
    ):
        """Test explanation when LIME result missing optional attributes."""
        # Mock LIME explanation without optional attributes
        mock_explanation = Mock()
        mock_explanation.as_list.return_value = [("feature1", 0.5)]
        # Simulate missing attributes by using spec that doesn't have them
        mock_explanation.configure_mock(
            local_pred=Mock(side_effect=AttributeError), score=Mock(side_effect=AttributeError), intercept=Mock(side_effect=AttributeError)
        )
        # Override hasattr behavior
        del mock_explanation.local_pred
        del mock_explanation.score
        del mock_explanation.intercept

        mock_explainer_instance = Mock()
        mock_explainer_instance.explain_instance.return_value = mock_explanation
        mock_lime_class.return_value = mock_explainer_instance

        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
        )
        lime_explanation = explainer.explain(sample_feature_vector)

        # Should use defaults for missing attributes
        assert lime_explanation.prediction_local == 0.5
        assert lime_explanation.model_score == 0.0
        assert lime_explanation.intercept == 0.0

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_explain_with_out_of_bounds_prediction(
        self, mock_lime_class, predict_fn, feature_names, sample_feature_vector
    ):
        """Test explanation with prediction outside [0, 1]."""
        # Mock LIME explanation with invalid prediction
        mock_explanation = Mock()
        mock_explanation.as_list.return_value = [("feature1", 0.5)]
        mock_explanation.local_pred = np.array([1.5])  # Invalid: > 1
        mock_explanation.score = 0.9
        mock_explanation.intercept = np.array([0.3, 0.4])

        mock_explainer_instance = Mock()
        mock_explainer_instance.explain_instance.return_value = mock_explanation
        mock_lime_class.return_value = mock_explainer_instance

        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
        )
        lime_explanation = explainer.explain(sample_feature_vector)

        # Should be clipped to [0, 1]
        assert 0 <= lime_explanation.prediction_local <= 1
        assert lime_explanation.prediction_local == 1.0

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_explain_with_negative_prediction(
        self, mock_lime_class, predict_fn, feature_names, sample_feature_vector
    ):
        """Test explanation with negative prediction value."""
        mock_explanation = Mock()
        mock_explanation.as_list.return_value = [("feature1", 0.5)]
        mock_explanation.local_pred = np.array([-0.5])  # Invalid: < 0
        mock_explanation.score = 0.9
        mock_explanation.intercept = np.array([0.3, 0.4])

        mock_explainer_instance = Mock()
        mock_explainer_instance.explain_instance.return_value = mock_explanation
        mock_lime_class.return_value = mock_explainer_instance

        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
        )
        lime_explanation = explainer.explain(sample_feature_vector)

        # Should be clipped to [0, 1]
        assert lime_explanation.prediction_local == 0.0

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_explain_with_zero_contributions(
        self, mock_lime_class, predict_fn, feature_names, sample_feature_vector
    ):
        """Test explanation with zero feature contributions."""
        mock_explanation = Mock()
        mock_explanation.as_list.return_value = []  # Empty contributions
        mock_explanation.local_pred = np.array([0.5])
        mock_explanation.score = 1.0
        mock_explanation.intercept = np.array([0.5, 0.5])

        mock_explainer_instance = Mock()
        mock_explainer_instance.explain_instance.return_value = mock_explanation
        mock_lime_class.return_value = mock_explainer_instance

        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
        )
        lime_explanation = explainer.explain(sample_feature_vector)

        assert lime_explanation.feature_contributions == []

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_explain_with_many_contributions(
        self, mock_lime_class, predict_fn, feature_names, sample_feature_vector
    ):
        """Test explanation with many feature contributions."""
        # Generate contributions for all 14 features
        contributions = [(f"feature_{i} > 0", 0.1 * (i + 1)) for i in range(14)]

        mock_explanation = Mock()
        mock_explanation.as_list.return_value = contributions
        mock_explanation.local_pred = np.array([0.9])
        mock_explanation.score = 0.95
        mock_explanation.intercept = np.array([0.2, 0.3])

        mock_explainer_instance = Mock()
        mock_explainer_instance.explain_instance.return_value = mock_explanation
        mock_lime_class.return_value = mock_explainer_instance

        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
        )
        lime_explanation = explainer.explain(sample_feature_vector)

        assert len(lime_explanation.feature_contributions) == 14


# === Integration Tests ===


class TestLIMEExplainerIntegration:
    """Integration tests for LIME explainer."""

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_full_explanation_pipeline(
        self, mock_lime_class, predict_fn, feature_names, training_data
    ):
        """Test complete explanation pipeline."""
        # Create realistic LIME explanation
        mock_explanation = Mock()
        mock_explanation.as_list.return_value = [
            ("epss_score > 0.9", 0.30),
            ("cvss_base_score > 9.0", 0.20),
            ("has_exploit_ref = 1", 0.15),
            ("attack_vector = Network", 0.10),
        ]
        mock_explanation.local_pred = np.array([0.92])
        mock_explanation.score = 0.88
        mock_explanation.intercept = np.array([0.25, 0.35])

        mock_explainer_instance = Mock()
        mock_explainer_instance.explain_instance.return_value = mock_explanation
        mock_lime_class.return_value = mock_explainer_instance

        # Create explainer
        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            training_data=training_data,
        )

        # Generate explanation
        feature_vector = MLFeatureVector(
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

        lime_explanation = explainer.explain(feature_vector)

        # Verify explanation quality
        assert isinstance(lime_explanation, LIMEExplanation)
        assert len(lime_explanation.feature_contributions) == 4
        assert lime_explanation.prediction_local > 0.9
        assert lime_explanation.model_score > 0.8

        # Verify top contributor is EPSS
        top_contributor = lime_explanation.feature_contributions[0]
        assert "epss_score" in top_contributor[0]
        assert top_contributor[1] == pytest.approx(0.30)

        # Verify positive/negative contributors work
        assert len(lime_explanation.positive_contributors) == 4
        assert len(lime_explanation.negative_contributors) == 0

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_explanation_with_negative_contributions(
        self, mock_lime_class, predict_fn, feature_names
    ):
        """Test explanation with mixed positive/negative contributions."""
        mock_explanation = Mock()
        mock_explanation.as_list.return_value = [
            ("epss_score > 0.9", 0.30),
            ("cvss_base_score > 9.0", 0.20),
            ("days_since_publication > 500", -0.15),  # Negative
            ("privileges_required = High", -0.10),  # Negative
        ]
        mock_explanation.local_pred = np.array([0.75])
        mock_explanation.score = 0.85
        mock_explanation.intercept = np.array([0.3, 0.4])

        mock_explainer_instance = Mock()
        mock_explainer_instance.explain_instance.return_value = mock_explanation
        mock_lime_class.return_value = mock_explainer_instance

        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
        )

        feature_vector = MLFeatureVector(
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

        lime_explanation = explainer.explain(feature_vector)

        # Verify mixed contributions
        assert len(lime_explanation.positive_contributors) == 2
        assert len(lime_explanation.negative_contributors) == 2

        # Verify explain_top_factors works
        top_factors = lime_explanation.explain_top_factors(n=2)
        assert "epss_score" in top_factors
        assert "increased" in top_factors
