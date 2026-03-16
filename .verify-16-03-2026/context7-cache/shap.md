# SHAP — Context7 Cache

## Current Version: shap 0.45+

## Key API Patterns

### TreeExplainer (for XGBoost)
```python
import shap

explainer = shap.TreeExplainer(model)  # XGBoost, LightGBM, RandomForest
shap_values = explainer.shap_values(X)  # or explainer(X) for Explanation object
```

### Explanation Object (modern API)
```python
explanation = explainer(X)
explanation.values  # SHAP values array
explanation.base_values  # expected value
explanation.data  # input features
```

### Plots
- `shap.summary_plot(shap_values, X)` — global feature importance
- `shap.waterfall_plot(explanation[0])` — single prediction breakdown
- `shap.force_plot(explainer.expected_value, shap_values[0], X.iloc[0])` — force plot
- `shap.dependence_plot("feature", shap_values, X)` — feature dependence
- `shap.bar_plot(explanation)` — bar chart of mean |SHAP|

### Best Practices
- Use `TreeExplainer` for tree models (fast, exact)
- Use `KernelExplainer` as fallback for any model (slow, approximate)
- `explainer(X)` returns `Explanation` object (preferred over `.shap_values()`)
- For binary classification, `shap_values` may be list of 2 arrays (one per class)
- Save explanations for audit trail
