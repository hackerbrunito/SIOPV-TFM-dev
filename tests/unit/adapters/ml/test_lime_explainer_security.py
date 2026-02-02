"""Security unit tests for LIMEExplainer.

Tests for:
- M-03: Configurable random state
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import numpy as np
import pytest

from siopv.adapters.ml.lime_explainer import DEFAULT_RANDOM_STATE, LIMEExplainer
from siopv.domain.entities.ml_feature_vector import MLFeatureVector

# === Fixtures ===


@pytest.fixture
def feature_names() -> list[str]:
    """Standard 14 feature names."""
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
def predict_fn():
    """Create a mock prediction function."""

    def _predict(X: np.ndarray) -> np.ndarray:
        return np.array([[0.3, 0.7]] * len(X))

    return _predict


@pytest.fixture
def training_data() -> np.ndarray:
    """Create sample training data."""
    return np.random.randn(50, 14)


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


# === M-03: Random State Configuration Tests ===


class TestLIMEExplainerRandomState:
    """Tests for LIMEExplainer random state handling (M-03)."""

    def test_default_random_state_is_42(self) -> None:
        """Test that default random state is 42."""
        assert DEFAULT_RANDOM_STATE == 42

    def test_init_with_explicit_random_state(self, predict_fn, feature_names) -> None:
        """Test initialization with explicit random_state."""
        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            random_state=12345,
        )

        assert explainer._random_state == 12345

    def test_init_with_none_uses_default(self, predict_fn, feature_names) -> None:
        """Test that None random_state uses default (42)."""
        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            random_state=None,
        )

        assert explainer._random_state == DEFAULT_RANDOM_STATE

    def test_init_without_random_state_uses_default(self, predict_fn, feature_names) -> None:
        """Test that omitting random_state uses default."""
        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
        )

        assert explainer._random_state == DEFAULT_RANDOM_STATE

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_random_state_passed_to_lime(self, mock_lime_class, predict_fn, feature_names) -> None:
        """Test that random_state is passed to LIME TabularExplainer."""
        custom_random_state = 99999

        LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            random_state=custom_random_state,
        )

        # Verify LIME was initialized with the random_state
        call_kwargs = mock_lime_class.call_args[1]
        assert call_kwargs["random_state"] == custom_random_state

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_random_state_default_passed_to_lime(
        self, mock_lime_class, predict_fn, feature_names
    ) -> None:
        """Test that default random_state is passed to LIME."""
        LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
        )

        call_kwargs = mock_lime_class.call_args[1]
        assert call_kwargs["random_state"] == DEFAULT_RANDOM_STATE

    def test_from_model_accepts_random_state(self, feature_names, training_data) -> None:
        """Test that from_model factory accepts random_state."""
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.3, 0.7]])

        explainer = LIMEExplainer.from_model(
            model=mock_model,
            feature_names=feature_names,
            training_data=training_data,
            random_state=54321,
        )

        assert explainer._random_state == 54321

    def test_from_model_without_random_state_uses_default(
        self, feature_names, training_data
    ) -> None:
        """Test that from_model without random_state uses default."""
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.3, 0.7]])

        explainer = LIMEExplainer.from_model(
            model=mock_model,
            feature_names=feature_names,
            training_data=training_data,
        )

        assert explainer._random_state == DEFAULT_RANDOM_STATE


class TestLIMEExplainerReproducibility:
    """Tests for LIME explanation reproducibility with random state (M-03)."""

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_same_random_state_same_init(self, mock_lime_class, predict_fn, feature_names) -> None:
        """Test that same random_state produces same LIME initialization."""
        random_state = 42

        # Create two explainers with same random_state
        LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            random_state=random_state,
        )
        first_call_kwargs = mock_lime_class.call_args[1].copy()

        mock_lime_class.reset_mock()

        LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            random_state=random_state,
        )
        second_call_kwargs = mock_lime_class.call_args[1]

        # Both should have same random_state
        assert first_call_kwargs["random_state"] == second_call_kwargs["random_state"]

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_different_random_state_different_init(
        self, mock_lime_class, predict_fn, feature_names
    ) -> None:
        """Test that different random_state creates different LIME init."""
        LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            random_state=42,
        )
        first_random_state = mock_lime_class.call_args[1]["random_state"]

        mock_lime_class.reset_mock()

        LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            random_state=999,
        )
        second_random_state = mock_lime_class.call_args[1]["random_state"]

        assert first_random_state != second_random_state


class TestLIMEExplainerWithTrainingData:
    """Tests for LIME with training data and random state (M-03)."""

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_training_data_with_random_state(
        self, mock_lime_class, predict_fn, feature_names, training_data
    ) -> None:
        """Test that training data and random_state are both passed."""
        custom_random_state = 77777

        LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            training_data=training_data,
            random_state=custom_random_state,
        )

        call_kwargs = mock_lime_class.call_args[1]
        assert call_kwargs["random_state"] == custom_random_state
        # Training data should also be passed
        assert call_kwargs["training_data"] is not None

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_no_training_data_still_uses_random_state(
        self, mock_lime_class, predict_fn, feature_names
    ) -> None:
        """Test that random_state is used even without training data."""
        LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            random_state=88888,
        )

        call_kwargs = mock_lime_class.call_args[1]
        assert call_kwargs["random_state"] == 88888


class TestLIMEExplainerConsistencyWithClassifier:
    """Tests for LIME/Classifier random state consistency (M-03)."""

    def test_random_state_can_be_passed_from_parent(self, feature_names) -> None:
        """Test that random_state can be propagated from parent classifier."""
        # Simulate what XGBoostClassifier does
        parent_random_state = 42

        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.3, 0.7]])

        explainer = LIMEExplainer.from_model(
            model=mock_model,
            feature_names=feature_names,
            random_state=parent_random_state,
        )

        assert explainer._random_state == parent_random_state

    def test_different_explainers_can_have_same_random_state(
        self, predict_fn, feature_names
    ) -> None:
        """Test that multiple explainers can share same random_state."""
        shared_random_state = 12345

        explainer1 = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            random_state=shared_random_state,
        )

        explainer2 = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            random_state=shared_random_state,
        )

        assert explainer1._random_state == explainer2._random_state


class TestLIMEExplainerSecurityAudit:
    """Tests for LIME random state auditability (M-03)."""

    def test_random_state_is_accessible(self, predict_fn, feature_names) -> None:
        """Test that random_state is accessible for audit."""
        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            random_state=42,
        )

        # Should be able to access for logging/audit
        assert hasattr(explainer, "_random_state")
        assert explainer._random_state == 42

    def test_random_state_logged_on_init(self, predict_fn, feature_names) -> None:
        """Test that random_state is logged on initialization."""
        with patch("siopv.adapters.ml.lime_explainer.logger") as mock_logger:
            LIMEExplainer(
                predict_fn=predict_fn,
                feature_names=feature_names,
                random_state=42,
            )

            # Verify logger was called with random_state info
            mock_logger.info.assert_called_once()
            call_kwargs = mock_logger.info.call_args[1]
            assert "random_state" in call_kwargs
            assert call_kwargs["random_state"] == 42


class TestLIMEExplainerEdgeCases:
    """Edge case tests for LIME random state (M-03)."""

    def test_zero_random_state(self, predict_fn, feature_names) -> None:
        """Test that random_state=0 is valid."""
        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            random_state=0,
        )

        assert explainer._random_state == 0

    def test_large_random_state(self, predict_fn, feature_names) -> None:
        """Test that large random_state is valid."""
        large_value = 2**31 - 1

        explainer = LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            random_state=large_value,
        )

        assert explainer._random_state == large_value

    @patch("siopv.adapters.ml.lime_explainer.lime.lime_tabular.LimeTabularExplainer")
    def test_random_state_in_all_modes(self, mock_lime_class, predict_fn, feature_names) -> None:
        """Test that random_state works in both classification and regression modes."""
        # Classification mode
        LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            mode="classification",
            random_state=111,
        )

        call_kwargs = mock_lime_class.call_args[1]
        assert call_kwargs["random_state"] == 111
        assert call_kwargs["mode"] == "classification"

        mock_lime_class.reset_mock()

        # Regression mode
        LIMEExplainer(
            predict_fn=predict_fn,
            feature_names=feature_names,
            mode="regression",
            random_state=222,
        )

        call_kwargs = mock_lime_class.call_args[1]
        assert call_kwargs["random_state"] == 222
        assert call_kwargs["mode"] == "regression"
