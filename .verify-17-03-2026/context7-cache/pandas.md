# Pandas — Context7 Cache (Pre-Wave Research)

> Queried: 2026-03-17 | Source: pandas docs + web research

## Pandas 3.0 (January 2026) — Key Changes

### Copy-on-Write is Now Default (and Only Mode)
- CoW is no longer opt-in — it's the only behavior in pandas 3.0
- Every DataFrame/Series derived from another always behaves as a copy
- No more SettingWithCopyWarning (removed entirely)

### Broken Patterns (AVOID)
```python
# BROKEN — chained assignment no longer works
df[df['col1'] > 10]['col2'] = 100  # silently does nothing

# CORRECT — use .loc
df.loc[df['col1'] > 10, 'col2'] = 100
```

### Key API Patterns
```python
# Filtering always returns a copy
subset = df[df['score'] > 5]  # independent copy

# Direct modification is the only way to change an object
df['new_col'] = values  # modifies df directly

# .loc for conditional updates
df.loc[mask, 'col'] = new_value
```

## Best Practices

1. **Never use chained indexing** for assignment — always `.loc[]`
2. **No need for `.copy()`** — CoW handles it automatically (internal optimization)
3. **PyArrow strings** are default backend in 3.0 — faster, nullable by default
4. **Expressions API** (new in 3.0) — use for complex transformations
5. **Direct modification only** — if you want to change df, modify df itself
