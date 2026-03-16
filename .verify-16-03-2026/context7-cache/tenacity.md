# tenacity — Context7 Cache

## Current Version: tenacity 8.x+

## Key API Patterns

### Decorator Usage
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
    reraise=True,
)
async def fetch_data():
    ...
```

### Stop Strategies
- `stop_after_attempt(n)` — stop after n attempts
- `stop_after_delay(seconds)` — stop after total delay
- `stop_any(stop1, stop2)` — stop on any condition

### Wait Strategies
- `wait_exponential(multiplier=1, min=1, max=60)` — exponential backoff
- `wait_fixed(seconds)` — fixed delay
- `wait_random(min=0, max=1)` — random delay
- `wait_chain(wait1, wait2, ...)` — sequential strategies

### Retry Conditions
- `retry_if_exception_type(ExceptionClass)` — retry on specific exceptions
- `retry_if_result(predicate)` — retry based on return value
- `retry_if_not_exception_type(ExceptionClass)` — retry on all except

### Callbacks
- `before_sleep=before_sleep_log(logger, logging.WARNING)` — log before retry
- `after=after_log(logger, logging.WARNING)` — log after each attempt

### Async Support
- Works with async functions natively — same decorator
- `@retry(...)` on `async def` works out of the box

### Best Practices
- Always set `reraise=True` to propagate final exception
- Use `wait_exponential` with `max` to cap backoff
- Extract retry constants to domain/constants.py
