# LIME — Context7 Cache

## Current Version: lime 0.2+

## Key API Patterns

### Tabular Explainer
```python
from lime.lime_tabular import LimeTabularExplainer

explainer = LimeTabularExplainer(
    training_data=X_train.values,
    feature_names=feature_names,
    class_names=["low", "medium", "high", "critical"],
    mode="classification",
    discretize_continuous=True,
)
```

### Generate Explanation
```python
explanation = explainer.explain_instance(
    data_row=X_test.iloc[0].values,
    predict_fn=model.predict_proba,
    num_features=10,
    num_samples=5000,
)
```

### Access Results
- `explanation.as_list()` — list of (feature, weight) tuples
- `explanation.as_map()` — dict mapping class → list of (feature_idx, weight)
- `explanation.as_html()` — HTML visualization
- `explanation.save_to_file("explanation.html")` — save HTML
- `explanation.local_pred` — local prediction
- `explanation.intercept` — intercept of local linear model

### Best Practices
- `predict_fn` must return probabilities (use `model.predict_proba`)
- Set `num_samples` high enough for stable explanations (5000+)
- Use `num_features` to control explanation complexity
- LIME is model-agnostic — works with any classifier
- For audit: save both `as_list()` and `as_html()` outputs
