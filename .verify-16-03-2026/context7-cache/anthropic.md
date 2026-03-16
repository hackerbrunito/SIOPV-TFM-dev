# Anthropic — Context7 Cache

## Current Version: anthropic 0.39+

## Key API Patterns

### Client Setup
- `from anthropic import Anthropic, AsyncAnthropic`
- `client = AsyncAnthropic(api_key="...")` — async preferred
- `client = Anthropic()` — reads `ANTHROPIC_API_KEY` env var

### Messages API
```python
message = await client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system="System prompt",
    messages=[{"role": "user", "content": "Hello"}],
)
text = message.content[0].text
```

### Streaming
```python
async with client.messages.stream(model=..., messages=...) as stream:
    async for text in stream.text_stream:
        print(text)
```

### Tool Use
- `tools=[{"name": "...", "description": "...", "input_schema": {...}}]`
- Response has `content` blocks with `type="tool_use"` containing `id`, `name`, `input`
- Return tool results via `{"role": "user", "content": [{"type": "tool_result", "tool_use_id": id, "content": "..."}]}`

### Best Practices
- Use `AsyncAnthropic` for async applications
- Set `max_tokens` explicitly (required parameter)
- Use structured `system` parameter (not in messages array)
- Handle `anthropic.APIError`, `anthropic.RateLimitError`
