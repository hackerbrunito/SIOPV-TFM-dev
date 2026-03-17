# structlog — Context7 Cache (Pre-Wave Research)

> Queried: 2026-03-17 | Source: structlog.org docs + web research

## Core API

### Configuration
```python
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        # Dev: ConsoleRenderer, Prod: JSONRenderer
        structlog.dev.ConsoleRenderer(),  # or structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
```

### Logger Usage
```python
log = structlog.get_logger()

# Bind context
log = log.bind(user_id="123", request_id="abc")
log.info("processing_request", action="classify")

# Unbind
log = log.unbind("request_id")

# New context (clear + bind)
log = log.new(session="xyz")
```

### Key Functions
- `structlog.get_logger(*args, **initial_values)` — returns configured logger
- `structlog.configure(...)` — set global defaults
- `structlog.configure_once(...)` — configure only if not already done
- `structlog.is_configured()` — check config status
- `structlog.wrap_logger(logger, ...)` — wrap stdlib logger
- `structlog.get_context(bound_logger)` — extract context dict
- `structlog.make_filtering_bound_logger(min_level)` — optimized level filtering

### BoundLogger Methods
- `.bind(**kv)` — add context, returns new logger
- `.unbind(*keys)` — remove keys, returns new logger
- `.new(**kv)` — clear + bind, returns new logger
- `.info()`, `.debug()`, `.warning()`, `.error()`, `.critical()` — log methods

## Best Practices

1. **cache_logger_on_first_use=True** — always set in production
2. **Dev vs Prod renderers** — ConsoleRenderer for dev, JSONRenderer for prod
3. **contextvars for request context** — use `merge_contextvars` processor
4. **Bind early, log often** — bind request/session context at entry point
5. **make_filtering_bound_logger** — use for performance (filters at instantiation)
6. **Don't log on proxy** — avoid frequent calls on `get_logger()` result; bind first
