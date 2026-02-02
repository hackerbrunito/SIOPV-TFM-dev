"""ML adapters for SIOPV Phase 3.

Contains implementations of ML-related ports:
- XGBoostClassifier: XGBoost-based risk classifier
- FeatureEngineer: Feature extraction from enrichment data
- SHAPExplainer: SHAP-based global explanations
- LIMEExplainer: LIME-based local explanations
"""

from siopv.adapters.ml.feature_engineer import FeatureEngineer
from siopv.adapters.ml.lime_explainer import LIMEExplainer
from siopv.adapters.ml.shap_explainer import SHAPExplainer
from siopv.adapters.ml.xgboost_classifier import XGBoostClassifier

__all__ = [
    "FeatureEngineer",
    "LIMEExplainer",
    "SHAPExplainer",
    "XGBoostClassifier",
]
