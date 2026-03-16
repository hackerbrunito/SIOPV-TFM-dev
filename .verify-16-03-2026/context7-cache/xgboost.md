# XGBoost — Context7 Cache

## Current Version: xgboost 2.1+

## Key API Patterns

### Scikit-Learn API (preferred)
```python
from xgboost import XGBClassifier, XGBRegressor

model = XGBClassifier(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    objective="binary:logistic",
    eval_metric="logloss",
    enable_categorical=True,
    random_state=42,
)
model.fit(X_train, y_train, eval_set=[(X_val, y_val)])
predictions = model.predict(X_test)
probabilities = model.predict_proba(X_test)
```

### Native API
- `xgb.DMatrix(X, label=y)` — data container
- `xgb.train(params, dtrain, num_boost_round=100)` — training
- `model.save_model("model.json")` / `xgb.Booster().load_model("model.json")`

### Feature Importance
- `model.feature_importances_` — array of importance scores
- `model.get_booster().get_score(importance_type="weight|gain|cover")`

### Hyperparameter Tuning (with Optuna)
- `learning_rate`, `max_depth`, `n_estimators`, `subsample`, `colsample_bytree`
- `min_child_weight`, `gamma`, `reg_alpha`, `reg_lambda`

### Best Practices
- Use sklearn API for pipeline compatibility
- `enable_categorical=True` for native categorical support
- Save as JSON format (portable, human-readable)
- Set `random_state` for reproducibility
- Use `eval_set` with early stopping for optimal iterations
