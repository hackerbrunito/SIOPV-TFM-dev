# imbalanced-learn (imblearn) — Context7 Cache

## Current Version: imbalanced-learn 0.12+

## Key API Patterns

### SMOTE (Synthetic Minority Over-sampling)
```python
from imblearn.over_sampling import SMOTE, ADASYN
from imblearn.under_sampling import RandomUnderSampler
from imblearn.combine import SMOTETomek, SMOTEENN
from imblearn.pipeline import Pipeline as ImbPipeline

smote = SMOTE(sampling_strategy="auto", random_state=42, k_neighbors=5)
X_resampled, y_resampled = smote.fit_resample(X_train, y_train)
```

### Pipeline (imblearn-specific)
```python
pipeline = ImbPipeline([
    ("smote", SMOTE(random_state=42)),
    ("scaler", StandardScaler()),
    ("clf", XGBClassifier()),
])
pipeline.fit(X_train, y_train)
```

### Strategies
- `sampling_strategy="auto"` — resample all minority classes to match majority
- `sampling_strategy=0.5` — ratio of minority to majority
- `sampling_strategy={"class_label": n_samples}` — explicit per-class

### Best Practices
- Use `imblearn.pipeline.Pipeline` NOT `sklearn.pipeline.Pipeline` (handles resampling)
- Apply SMOTE only to training data, never to test/validation
- Combine with undersampling: `SMOTETomek` or `SMOTEENN`
- Set `random_state` for reproducibility
- Use with `StratifiedKFold` for cross-validation
