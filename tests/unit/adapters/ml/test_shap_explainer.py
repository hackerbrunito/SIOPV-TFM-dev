"""Unit tests for SHAPExplainer.

Tests SHAP-based explanations for XGBoost model predictions.

FIXED: Proper mock structure for TreeExplainer with correct shap_values return format.
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from siopv.adapters.ml.shap_explainer import SHAPExplainer
from siopv.domain.entities.ml_feature_vector import MLFeatureVector
from siopv.domain.value_objects.risk_score import SHAPValues

# === Fixtures ===


@pytest.fixture()
def mock_xgboost_model() -> MagicMock:
    """Create a mock XGBoost model."""
    mock = MagicMock()
    mock.predict_proba.return_value = np.array([[0.2, 0.8]])
    return mock


@pytest.fixture()
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


@pytest.fixture()
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


@pytest.fixture()
def mock_tree_explainer() -> Mock:
    """Create a properly configured mock TreeExplainer.

    FIXED: Returns proper structure that matches SHAP TreeExplainer output.
    For binary classification, shap_values returns a list with [negative_class, positive_class].
    Each element is a 2D array of shape (n_samples, n_features).
    """
    mock = Mock()

    # For binary classification: list of [negative_class_values, positive_class_values]
    # Each is shape (n_samples, n_features)
    mock.shap_values.return_value = [
        np.array([[0.0] * 14]),  # Negative class (we ignore this)
        np.array(
            [
                [
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
                ]
            ]
        ),  # Positive class
    ]
    # Expected value is also array for binary classification
    mock.expected_value = np.array([0.65, 0.35])
    return mock


@pytest.fixture()
def shap_explainer(mock_xgboost_model, feature_names) -> SHAPExplainer:
    """Create a SHAP explainer with mocked model."""
    return SHAPExplainer(model=mock_xgboost_model, feature_names=feature_names)


# === Initialization Tests ===


class TestSHAPExplainerInit:
    """Tests for SHAPExplainer initialization."""

    def test_init(self, mock_xgboost_model, feature_names):
        """Test basic initialization."""
        explainer = SHAPExplainer(model=mock_xgboost_model, feature_names=feature_names)

        assert explainer._model is mock_xgboost_model
        assert explainer._feature_names == feature_names
        assert explainer._explainer is None  # Lazy initialization

    def test_init_with_custom_features(self, mock_xgboost_model):
        """Test initialization with custom feature names."""
        custom_features = ["f1", "f2", "f3"]
        explainer = SHAPExplainer(model=mock_xgboost_model, feature_names=custom_features)

        assert explainer._feature_names == custom_features


# === Explanation Tests ===


class TestSHAPExplainerExplanations:
    """Tests for SHAP explanation generation."""

    @patch("siopv.adapters.ml.shap_explainer.shap.TreeExplainer")
    def test_explain_single_binary_classification(
        self, mock_tree_explainer_class, mock_xgboost_model, feature_names, sample_feature_vector
    ):
        """Test explaining a single prediction with binary classification output."""
        # Setup: TreeExplainer returns list format [neg_class, pos_class]
        mock_tree_explainer = Mock()
        mock_tree_explainer.shap_values.return_value = [
            np.array([[0.0] * 14]),  # Negative class
            np.array(
                [
                    [
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
                    ]
                ]
            ),  # Positive class
        ]
        mock_tree_explainer.expected_value = np.array([0.65, 0.35])
        mock_tree_explainer_class.return_value = mock_tree_explainer

        explainer = SHAPExplainer(model=mock_xgboost_model, feature_names=feature_names)
        shap_values = explainer.explain(sample_feature_vector)

        assert isinstance(shap_values, SHAPValues)
        assert len(shap_values.feature_names) == 14
        assert len(shap_values.shap_values) == 14
        assert shap_values.base_value == 0.35  # Positive class expected value
        # Verify specific SHAP values
        assert shap_values.shap_values[0] == pytest.approx(0.15)  # cvss_base_score
        assert shap_values.shap_values[9] == pytest.approx(0.25)  # epss_score (highest)

    @patch("siopv.adapters.ml.shap_explainer.shap.TreeExplainer")
    def test_explain_single_with_single_output(
        self, mock_tree_explainer_class, mock_xgboost_model, feature_names, sample_feature_vector
    ):
        """Test explaining with single output format (not list)."""
        # Some SHAP versions return single array instead of list
        mock_tree_explainer = Mock()
        mock_tree_explainer.shap_values.return_value = np.array(
            [
                [
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
                ]
            ]
        )
        mock_tree_explainer.expected_value = 0.35  # Scalar expected value
        mock_tree_explainer_class.return_value = mock_tree_explainer

        explainer = SHAPExplainer(model=mock_xgboost_model, feature_names=feature_names)
        shap_values = explainer.explain(sample_feature_vector)

        assert isinstance(shap_values, SHAPValues)
        assert len(shap_values.shap_values) == 14
        assert shap_values.base_value == 0.35

    @patch("siopv.adapters.ml.shap_explainer.shap.TreeExplainer")
    def test_explain_batch(self, mock_tree_explainer_class, mock_xgboost_model, feature_names):
        """Test explaining multiple predictions."""
        # Setup batch SHAP values
        np.random.seed(42)
        batch_shap_values = np.random.randn(3, 14)

        mock_tree_explainer = Mock()
        mock_tree_explainer.shap_values.return_value = [
            np.zeros((3, 14)),  # Negative class
            batch_shap_values,  # Positive class
        ]
        mock_tree_explainer.expected_value = np.array([0.65, 0.35])
        mock_tree_explainer_class.return_value = mock_tree_explainer

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

        explainer = SHAPExplainer(model=mock_xgboost_model, feature_names=feature_names)
        shap_values_list = explainer.explain_batch(feature_vectors)

        assert len(shap_values_list) == 3
        assert all(isinstance(sv, SHAPValues) for sv in shap_values_list)
        assert all(len(sv.shap_values) == 14 for sv in shap_values_list)
        assert all(sv.base_value == 0.35 for sv in shap_values_list)

    @patch("siopv.adapters.ml.shap_explainer.shap.TreeExplainer")
    def test_explain_batch_empty(
        self, mock_tree_explainer_class, mock_xgboost_model, feature_names
    ):
        """Test explaining empty batch."""
        explainer = SHAPExplainer(model=mock_xgboost_model, feature_names=feature_names)
        shap_values_list = explainer.explain_batch([])

        assert shap_values_list == []
        # TreeExplainer should not be created for empty batch
        mock_tree_explainer_class.assert_not_called()


# === Global Importance Tests ===


class TestSHAPExplainerGlobalImportance:
    """Tests for global feature importance calculation."""

    @patch("siopv.adapters.ml.shap_explainer.shap.TreeExplainer")
    def test_get_global_importance(
        self, mock_tree_explainer_class, mock_xgboost_model, feature_names
    ):
        """Test calculating global feature importance."""
        # Create SHAP values where epss_score (index 9) has highest mean absolute value
        np.random.seed(42)
        shap_array = np.random.randn(5, 14) * 0.1
        shap_array[:, 9] = 0.5  # Make epss_score most important

        mock_tree_explainer = Mock()
        mock_tree_explainer.shap_values.return_value = [
            np.zeros((5, 14)),
            shap_array,
        ]
        mock_tree_explainer.expected_value = np.array([0.65, 0.35])
        mock_tree_explainer_class.return_value = mock_tree_explainer

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
            for i in range(5)
        ]

        explainer = SHAPExplainer(model=mock_xgboost_model, feature_names=feature_names)
        importance = explainer.get_global_importance(feature_vectors)

        assert len(importance) == 14
        assert all(name in importance for name in feature_names)
        assert "epss_score" in importance
        # epss_score should have highest importance
        assert importance["epss_score"] == max(importance.values())

    def test_get_global_importance_empty(
        self,
        mock_xgboost_model,
        feature_names,
    ):
        """Test global importance with empty input."""
        explainer = SHAPExplainer(model=mock_xgboost_model, feature_names=feature_names)
        importance = explainer.get_global_importance([])

        assert importance == {}


# === Summary Data Tests ===


class TestSHAPExplainerSummaryData:
    """Tests for summary plot data generation."""

    @patch("siopv.adapters.ml.shap_explainer.shap.TreeExplainer")
    def test_generate_summary_data(
        self, mock_tree_explainer_class, mock_xgboost_model, feature_names
    ):
        """Test generating summary plot data."""
        np.random.seed(42)
        shap_array = np.random.randn(3, 14)

        mock_tree_explainer = Mock()
        mock_tree_explainer.shap_values.return_value = [
            np.zeros((3, 14)),
            shap_array,
        ]
        mock_tree_explainer.expected_value = np.array([0.65, 0.35])
        mock_tree_explainer_class.return_value = mock_tree_explainer

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

        explainer = SHAPExplainer(model=mock_xgboost_model, feature_names=feature_names)
        shap_values, feature_matrix, names = explainer.generate_summary_data(feature_vectors)

        assert shap_values.shape == (3, 14)
        assert feature_matrix.shape == (3, 14)
        assert names == feature_names

    def test_generate_summary_data_empty(self, mock_xgboost_model, feature_names):
        """Test summary data generation with empty input."""
        explainer = SHAPExplainer(model=mock_xgboost_model, feature_names=feature_names)
        shap_values, feature_matrix, names = explainer.generate_summary_data([])

        assert shap_values.shape == (0,)
        assert feature_matrix.shape == (0,)
        assert names == []


# === Lazy Initialization Tests ===


class TestSHAPExplainerLazyInit:
    """Tests for lazy explainer initialization."""

    @patch("siopv.adapters.ml.shap_explainer.shap.TreeExplainer")
    def test_explainer_created_on_first_use(
        self,
        mock_tree_explainer_class,
        mock_xgboost_model,
        feature_names,
        sample_feature_vector,
    ):
        """Test that TreeExplainer is created lazily."""
        mock_tree_explainer = Mock()
        # FIXED: Use 2D arrays (n_samples, n_features) instead of 1D
        mock_tree_explainer.shap_values.return_value = [
            np.zeros((1, 14)),
            np.random.randn(1, 14),
        ]
        mock_tree_explainer.expected_value = np.array([0.65, 0.35])
        mock_tree_explainer_class.return_value = mock_tree_explainer

        explainer = SHAPExplainer(model=mock_xgboost_model, feature_names=feature_names)

        # Explainer not created yet
        assert explainer._explainer is None

        # First call creates explainer
        explainer.explain(sample_feature_vector)

        # Explainer now exists
        assert explainer._explainer is not None
        mock_tree_explainer_class.assert_called_once_with(mock_xgboost_model)

    @patch("siopv.adapters.ml.shap_explainer.shap.TreeExplainer")
    def test_explainer_reused_on_subsequent_calls(
        self,
        mock_tree_explainer_class,
        mock_xgboost_model,
        feature_names,
        sample_feature_vector,
    ):
        """Test that TreeExplainer is reused after creation."""
        mock_tree_explainer = Mock()
        # FIXED: Use 2D arrays (n_samples, n_features) instead of 1D
        mock_tree_explainer.shap_values.return_value = [
            np.zeros((1, 14)),
            np.random.randn(1, 14),
        ]
        mock_tree_explainer.expected_value = np.array([0.65, 0.35])
        mock_tree_explainer_class.return_value = mock_tree_explainer

        explainer = SHAPExplainer(model=mock_xgboost_model, feature_names=feature_names)

        # First call
        explainer.explain(sample_feature_vector)

        # Second call
        explainer.explain(sample_feature_vector)

        # TreeExplainer created only once
        assert mock_tree_explainer_class.call_count == 1


# === Edge Cases ===


class TestSHAPExplainerEdgeCases:
    """Tests for edge cases and error handling."""

    @patch("siopv.adapters.ml.shap_explainer.shap.TreeExplainer")
    def test_explain_with_zero_shap_values(
        self, mock_tree_explainer_class, mock_xgboost_model, feature_names, sample_feature_vector
    ):
        """Test explanation with all-zero SHAP values."""
        mock_tree_explainer = Mock()
        mock_tree_explainer.shap_values.return_value = [
            np.zeros((1, 14)),
            np.zeros((1, 14)),
        ]
        mock_tree_explainer.expected_value = np.array([0.5, 0.5])
        mock_tree_explainer_class.return_value = mock_tree_explainer

        explainer = SHAPExplainer(model=mock_xgboost_model, feature_names=feature_names)
        shap_values = explainer.explain(sample_feature_vector)

        assert isinstance(shap_values, SHAPValues)
        assert all(v == 0 for v in shap_values.shap_values)

    @patch("siopv.adapters.ml.shap_explainer.shap.TreeExplainer")
    def test_explain_with_negative_shap_values(
        self, mock_tree_explainer_class, mock_xgboost_model, feature_names, sample_feature_vector
    ):
        """Test explanation with negative SHAP values."""
        mock_tree_explainer = Mock()
        mock_tree_explainer.shap_values.return_value = [
            np.zeros((1, 14)),
            np.full((1, 14), -0.1),  # All negative
        ]
        mock_tree_explainer.expected_value = np.array([0.5, 0.5])
        mock_tree_explainer_class.return_value = mock_tree_explainer

        explainer = SHAPExplainer(model=mock_xgboost_model, feature_names=feature_names)
        shap_values = explainer.explain(sample_feature_vector)

        assert isinstance(shap_values, SHAPValues)
        assert all(v < 0 for v in shap_values.shap_values)

    @patch("siopv.adapters.ml.shap_explainer.shap.TreeExplainer")
    def test_explain_with_large_shap_values(
        self, mock_tree_explainer_class, mock_xgboost_model, feature_names, sample_feature_vector
    ):
        """Test explanation with large SHAP values."""
        mock_tree_explainer = Mock()
        mock_tree_explainer.shap_values.return_value = [
            np.zeros((1, 14)),
            np.full((1, 14), 10.0),  # Large positive values
        ]
        mock_tree_explainer.expected_value = np.array([0.5, 0.5])
        mock_tree_explainer_class.return_value = mock_tree_explainer

        explainer = SHAPExplainer(model=mock_xgboost_model, feature_names=feature_names)
        shap_values = explainer.explain(sample_feature_vector)

        assert isinstance(shap_values, SHAPValues)
        assert all(v == 10.0 for v in shap_values.shap_values)


# === Integration Tests ===


class TestSHAPExplainerIntegration:
    """Integration tests for SHAP explainer."""

    @patch("siopv.adapters.ml.shap_explainer.shap.TreeExplainer")
    def test_full_explanation_workflow(
        self, mock_tree_explainer_class, mock_xgboost_model, feature_names
    ):
        """Test complete explanation workflow."""
        # Setup realistic SHAP values
        mock_tree_explainer = Mock()
        mock_tree_explainer.shap_values.return_value = [
            np.zeros((1, 14)),
            np.array(
                [
                    [
                        0.15,  # cvss_base_score
                        0.08,  # attack_vector
                        0.03,  # attack_complexity
                        0.05,  # privileges_required
                        0.02,  # user_interaction
                        0.04,  # scope
                        0.06,  # confidentiality_impact
                        0.05,  # integrity_impact
                        0.04,  # availability_impact
                        0.25,  # epss_score (highest)
                        0.10,  # epss_percentile
                        -0.02,  # days_since_publication (negative)
                        0.12,  # has_exploit_ref
                        0.03,  # cwe_category
                    ]
                ]
            ),
        ]
        mock_tree_explainer.expected_value = np.array([0.65, 0.35])
        mock_tree_explainer_class.return_value = mock_tree_explainer

        # Create explainer
        explainer = SHAPExplainer(model=mock_xgboost_model, feature_names=feature_names)

        # Create feature vector for Log4Shell
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

        # Get explanation
        shap_values = explainer.explain(feature_vector)

        # Verify explanation quality
        assert isinstance(shap_values, SHAPValues)
        assert len(shap_values.feature_names) == 14
        assert len(shap_values.shap_values) == 14
        assert shap_values.base_value == 0.35

        # Verify top contributors
        top_contributors = shap_values.top_contributors
        assert len(top_contributors) == 5
        # epss_score should be top contributor
        assert top_contributors[0][0] == "epss_score"
        assert top_contributors[0][1] == pytest.approx(0.25)

        # Verify to_dict works
        shap_dict = shap_values.to_dict()
        assert shap_dict["epss_score"] == pytest.approx(0.25)
        assert shap_dict["days_since_publication"] == pytest.approx(-0.02)
