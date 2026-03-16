# Optuna — Context7 Cache

## Current Version: optuna 3.x+

## Key API Patterns

### Study Creation
```python
import optuna

study = optuna.create_study(
    direction="maximize",  # or "minimize"
    study_name="siopv-xgboost",
    storage="sqlite:///optuna.db",  # optional persistence
    pruner=optuna.pruners.MedianPruner(),
)
study.optimize(objective, n_trials=100)
```

### Objective Function
```python
def objective(trial: optuna.Trial) -> float:
    params = {
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
        "n_estimators": trial.suggest_int("n_estimators", 50, 500),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
    }
    model = XGBClassifier(**params)
    score = cross_val_score(model, X, y, cv=5, scoring="f1_weighted")
    return score.mean()
```

### Suggest Methods
- `trial.suggest_int("name", low, high)` — integer
- `trial.suggest_float("name", low, high, log=True)` — float (log scale)
- `trial.suggest_categorical("name", ["a", "b"])` — categorical

### Results
- `study.best_params` — best hyperparameters dict
- `study.best_value` — best objective value
- `study.best_trial` — best trial object

### Best Practices
- Use `log=True` for learning rates and regularization
- Use `MedianPruner` for early stopping of bad trials
- Persist with SQLite for reproducibility
- Prefer over sklearn GridSearchCV/RandomizedSearchCV
