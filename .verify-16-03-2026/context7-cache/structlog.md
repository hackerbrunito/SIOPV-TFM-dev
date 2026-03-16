# structlog — Context7 Cache

## Current Version: structlog 25.5.0

## Key API Patterns

### Logger Creation
- `import structlog`
- `logger = structlog.get_logger()` — returns proxy bound logger
- `logger = structlog.get_logger("module_name")` — with logger name
- `logger.bind(key="value")` — add context to logger instance
- `logger.unbind("key")` — remove context key
- `logger.new(key="value")` — create new logger with fresh context

### Configuration
```python
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer(),  # dev
        # structlog.processors.JSONRenderer(),  # prod
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
```

### Common Processors
- `structlog.processors.add_log_level` — adds log level
- `structlog.processors.TimeStamper(fmt="iso")` — ISO timestamps
- `structlog.processors.StackInfoRenderer()` — stack info
- `structlog.processors.JSONRenderer()` — JSON output (production)
- `structlog.dev.ConsoleRenderer()` — colored console output (dev)
- `structlog.contextvars.merge_contextvars` — merge contextvars into event
- `structlog.stdlib.filter_by_level` — filter by log level
- `structlog.stdlib.add_logger_name` — add logger name

### Context Variables (async-safe)
- `structlog.contextvars.bind_contextvars(request_id="abc")` — bind across async calls
- `structlog.contextvars.unbind_contextvars("request_id")`
- `structlog.contextvars.clear_contextvars()`

### Logging Calls
- `logger.info("event_name", key=value)` — structured event
- `logger.warning(...)`, `logger.error(...)`, `logger.debug(...)`
- NEVER use `print()` or `logging.getLogger()`

### stdlib Integration
- `structlog.stdlib.ProcessorFormatter` for stdlib handler integration
- `structlog.stdlib.BoundLogger` as wrapper class
