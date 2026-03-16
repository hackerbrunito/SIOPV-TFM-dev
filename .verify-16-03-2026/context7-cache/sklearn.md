# scikit-learn — Context7 Cache

## Current Version: scikit-learn 1.5+

## Key API Patterns

### Pipeline
- `from sklearn.pipeline import Pipeline`
- `Pipeline([("scaler", StandardScaler()), ("clf", XGBClassifier())])`
- `.fit(X, y)`, `.predict(X)`, `.predict_proba(X)`

### Preprocessing
- `from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder`
- `from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold`
- `from sklearn.impute import SimpleImputer`

### Metrics
- `from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score`
- `from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score`
- `classification_report(y_true, y_pred, output_dict=True)` — dict output

### Model Selection
- `cross_val_score(model, X, y, cv=5, scoring="f1_weighted")`
- `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`
- `GridSearchCV` / `RandomizedSearchCV` — or use Optuna instead

### Feature Engineering
- `from sklearn.feature_extraction.text import TfidfVectorizer`
- `from sklearn.decomposition import PCA`

### Best Practices
- Use `set_output(transform="pandas")` for DataFrame output (1.2+)
- Use `StratifiedKFold` for imbalanced classification
- Prefer Optuna over GridSearchCV for hyperparameter tuning
- Use `Pipeline` for reproducible preprocessing + model chains
