# Context7 Library Cache — BRIEFING

> One-line summary per library: the key pattern or API fact for verification agents.

- **anthropic**: AsyncAnthropic for async; messages.create() with explicit max_tokens; tool_use content blocks for function calling
- **chromadb**: PersistentClient(path=) for production; get_or_create_collection(); query() with where= metadata filters
- **httpx**: AsyncClient as context manager with base_url + explicit timeout; no requests library; use tenacity for retries
- **imblearn**: imblearn.pipeline.Pipeline (NOT sklearn Pipeline) for resampling; SMOTE only on training data; set random_state
- **jwt**: ALWAYS specify algorithms=[] in decode(); PyJWKClient for OIDC/JWKS; RS256 for production; validate exp/aud/iss
- **langchain_core**: Minimal dependency; ChatPromptTemplate.from_messages(); RunnableLambda/RunnablePassthrough; import from langchain_core not langchain
- **langgraph**: interrupt() function + Command(resume=) for HITL; AsyncSqliteSaver for checkpointing; StateGraph with TypedDict state; thread_id in config
- **lime**: LimeTabularExplainer with predict_fn=model.predict_proba; explain_instance(); as_list() for audit trail
- **numpy**: NDArray[np.float64] for type hints; default_rng(seed=42) not np.random.seed(); vectorized ops over loops
- **openfga_sdk**: OpenFgaClient as async context manager (initialize once, reuse); ClientConfiguration with api_url/store_id; Credentials for auth; retries on 429/5xx
- **optuna**: create_study(direction=) + study.optimize(objective, n_trials=); trial.suggest_int/float/categorical; MedianPruner for early stopping
- **pydantic**: ConfigDict replaces class Config; model_validator replaces root_validator; field_validator replaces validator; model_dump() replaces .dict()
- **pydantic_settings**: BaseSettings + SettingsConfigDict(env_prefix=, env_file=); SecretStr for credentials with no defaults; separate pydantic-settings package
- **shap**: TreeExplainer for XGBoost (fast, exact); explainer(X) returns Explanation object; summary_plot for global importance; waterfall_plot for local
- **sklearn**: Pipeline for reproducible chains; StratifiedKFold for imbalanced data; classification_report(output_dict=True); prefer Optuna over GridSearchCV
- **structlog**: get_logger() + bind() for structured logging; configure() with processor chain; contextvars for async-safe context; NEVER print() or logging.getLogger()
- **tenacity**: @retry decorator with stop_after_attempt + wait_exponential; retry_if_exception_type(); reraise=True; native async support
- **typer**: Annotated[type, typer.Option/Argument] (modern style); Typer(no_args_is_help=True); no native async (use asyncio.run wrapper)
- **xgboost**: XGBClassifier sklearn API; enable_categorical=True; save as JSON; eval_set for early stopping; random_state for reproducibility
