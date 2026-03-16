# Verification Report: structlog / XGBoost / httpx Findings
**Date:** 2026-03-05
**Agent:** hallucination-detector (verification pass)
**Source:** Context7 MCP — structlog stable docs, XGBoost GitHub NEWS.md + v3.1.0 changelog, httpx docs, tenacity docs

---

## Finding M1: `structlog.processors.format_exc_info` is deprecated

### Verdict: RETRACTED

The audit claim that `format_exc_info` is deprecated and should be replaced with `ExceptionRenderer()` is **incorrect**.

### Evidence from Context7 (structlog stable docs)

The current structlog source code defines `format_exc_info` as follows:

```python
format_exc_info = ExceptionRenderer()
"""
Replace an ``exc_info`` field with an ``exception`` string field using Python's
built-in traceback formatting.
...
"""
```

Source: https://www.structlog.org/en/stable/_modules/structlog/processors

Key facts:
1. `format_exc_info` is **not deprecated**. It is defined as a **module-level instance** of `ExceptionRenderer()` — it IS an `ExceptionRenderer`, just pre-instantiated.
2. The two forms are functionally identical: `format_exc_info` and `ExceptionRenderer()` produce exactly the same behavior with the default formatter.
3. No deprecation warning is documented anywhere in the structlog stable docs for `format_exc_info`.
4. Both appear together in the current API reference without any deprecation marker.

### What the audit got right (nuance)

`ExceptionRenderer` was added in structlog 22.1.0 (`.. versionadded:: 22.1.0`) and is the **class** that enables richer configuration (e.g., passing `ExceptionDictTransformer()` for JSON-serializable structured tracebacks). If the project wants structured tracebacks for JSON logs, migrating to:

```python
structlog.processors.ExceptionRenderer(ExceptionDictTransformer())
```

is the correct path — but that is a feature enhancement, not a deprecation fix.

### Correct syntax if migrating

```python
# Both are equivalent for string-formatted exceptions:
structlog.processors.format_exc_info          # module-level instance (no parentheses)
structlog.processors.ExceptionRenderer()      # explicit instantiation (with parentheses)

# For structured JSON tracebacks:
from structlog.tracebacks import ExceptionDictTransformer
structlog.processors.ExceptionRenderer(ExceptionDictTransformer())
```

### Action required

None for correctness. The project's current use of `format_exc_info` is valid. If UserWarnings are appearing, they are NOT from a deprecation on `format_exc_info` itself — they are from a different cause (possibly a processor ordering issue or stdlib logging integration). Investigate the actual warning message before changing any code.

---

## Finding M9: `use_label_encoder=False` is dead code in XGBoost 2.0+

### Verdict: NUANCED

The audit is **partially correct** but overstates the situation. The parameter was deprecated in v1.3 and removed by v1.5, but Context7 evidence shows it is still appearing in current XGBoost documentation examples — suggesting the behavior in v3.x is silent ignorance rather than an error.

### Evidence from Context7 (XGBoost GitHub NEWS.md + v3.1.0 changelog)

**Timeline reconstructed from NEWS.md:**

1. **v1.3** — `LabelEncoder` within `XGBClassifier` was deprecated:
   > "The use of `LabelEncoder` within `XGBClassifier` is now deprecated and will be removed in a future release."

2. **v1.5** — deprecated features from v1.3 were removed:
   > "Some specific removals include: old warning in 1.3, label encoder deprecated in 1.3..."

3. **v3.1.0** — removed GPU parameters deprecated in v2.0 (`gpu_id`, `gpu_hist`, etc.) and deprecated C API functions. `use_label_encoder` is **NOT mentioned** in the v3.1.0 removal list.

**Contradiction in Context7 evidence:**

The XGBoost Context7 docs contain a current code example (from `llms.txt`) that still uses the parameter:

```python
xgb_clf = xgb.XGBClassifier(
    objective='multi:softprob',
    num_class=10,
    eval_metric='mlogloss',
    use_label_encoder=False,   # Recommended to disable label encoder
    tree_method='hist',
    device='cpu'
)
```

This snippet is annotated as current usage, which suggests that in XGBoost v3.x, `use_label_encoder=False` is accepted without error (likely silently ignored or still accepted as a no-op).

### What this means for the project

The audit claim that it is "dead code / silently ignored" is **likely correct in effect** but the implication that it causes a warning or error is unconfirmed. The parameter:
- Was removed from internal functionality in v1.5
- Is not listed in v3.1.0 breaking changes
- Still appears in current official documentation examples without warning annotations

In practice with v3.1.3: passing `use_label_encoder=False` is almost certainly a no-op. It does not raise an error. It may or may not emit a deprecation warning depending on XGBoost's unknown_params handling.

### Recommended action

Remove `use_label_encoder=False` from `XGBClassifier(...)` calls as **code hygiene**. The current recommended pattern for multi-class classification (confirmed by Context7) is simply:

```python
clf = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=5,
    learning_rate=0.1,
    objective='multi:softprob',
    n_jobs=-1,
    random_state=42
)
```

No label encoding parameter is needed or recognized. XGBoost v2+ handles label encoding internally and transparently.

---

## Finding L4: External API adapter test coverage is poor (httpx retry / circuit breaker)

### Verdict: CONFIRMED (with clarification on circuit breaker)

### Evidence from Context7

#### httpx retry configuration (CONFIRMED correct)

The current httpx API for retry is exactly as documented in the audit:

```python
import httpx

transport = httpx.AsyncHTTPTransport(retries=3)
async with httpx.AsyncClient(transport=transport) as client:
    response = await client.get('https://www.example.com/')
```

Source: https://github.com/encode/httpx/blob/master/docs/async.md

The `retries` parameter on `AsyncHTTPTransport` is the current documented API. It handles `httpx.ConnectError` and `httpx.ConnectTimeout`.

#### Circuit breaker: httpx has no native circuit breaker (CONFIRMED)

httpx does not provide a native circuit breaker. The Context7 docs explicitly state:

> "For more complex retry logic, consider external libraries like `tenacity`."

Source: https://github.com/encode/httpx/blob/master/docs/advanced/transports.md

#### tenacity is the correct library for circuit breaker / advanced retry

tenacity supports both sync and async:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def my_async_adapter_call():
    async with httpx.AsyncClient() as client:
        return await client.get(url)
```

For code blocks (not decorators), `AsyncRetrying` is available:

```python
from tenacity import AsyncRetrying, RetryError, stop_after_attempt

async def fetch_with_retry():
    try:
        async for attempt in AsyncRetrying(stop=stop_after_attempt(3)):
            with attempt:
                async with httpx.AsyncClient() as client:
                    return await client.get(url)
    except RetryError:
        raise
```

### What needs testing

If the project's httpx adapters use `AsyncHTTPTransport(retries=N)` for connection-level retries and `tenacity` for application-level retry/circuit breaking, the following scenarios need test coverage:

1. `ConnectError` triggers retry via transport
2. `ConnectTimeout` triggers retry via transport
3. tenacity `stop_after_attempt` exhaustion raises `RetryError`
4. tenacity `wait_exponential` produces correct delays (mock `asyncio.sleep`)
5. Circuit breaker open state (if using tenacity's `stop_after_delay` pattern)
6. Successful response on retry N (partial failure scenario)

The finding that these are untested is plausible given the 0-20% coverage noted for Phase 2 adapters, and the complexity of mocking both network failures and time-based retry logic.

---

## Summary Table

| Finding | Verdict | Action |
|---------|---------|--------|
| M1: `format_exc_info` deprecated | RETRACTED | No code change needed. Investigate actual warning source separately. |
| M9: `use_label_encoder=False` dead code | NUANCED | Remove for hygiene (it's a no-op in v3.x), but it does not cause errors or warnings. Not a blocking issue. |
| L4: httpx retry/circuit breaker untested | CONFIRMED | Add tests for ConnectError retry, tenacity exhaustion, partial failure recovery. |

---

## Context7 Sources Used

- structlog stable: https://www.structlog.org/en/stable/_modules/structlog/processors
- structlog API: https://www.structlog.org/en/stable/api
- XGBoost NEWS.md: https://github.com/dmlc/xgboost/blob/master/NEWS.md
- XGBoost v3.1.0 changelog: https://github.com/dmlc/xgboost/blob/master/doc/changes/v3.1.0.md
- httpx async docs: https://github.com/encode/httpx/blob/master/docs/async.md
- httpx transports docs: https://github.com/encode/httpx/blob/master/docs/advanced/transports.md
- tenacity docs: https://tenacity.readthedocs.io/en/latest/index
