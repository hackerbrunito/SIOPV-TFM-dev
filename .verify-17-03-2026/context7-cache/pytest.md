# pytest — Context7 Cache (Pre-Wave Research)

> Queried: 2026-03-17 | Source: pytest docs + web research

## Core API Patterns

### Fixtures
```python
import pytest

@pytest.fixture
def db_session():
    session = create_session()
    yield session
    session.close()

@pytest.fixture(scope="module")
def shared_resource():
    return expensive_setup()

# Parametrized fixtures
@pytest.fixture(params=["sqlite", "postgres"])
def database(request):
    return create_db(request.param)
```

### Parametrize
```python
@pytest.mark.parametrize("input,expected", [
    ("CVE-2026-001", True),
    ("invalid", False),
    pytest.param("edge-case", None, marks=pytest.mark.xfail),
])
def test_validate(input, expected):
    assert validate(input) == expected

# Indirect parametrization (pass to fixture)
@pytest.mark.parametrize("db_type", ["sqlite", "postgres"], indirect=True)
def test_with_db(db_type):
    ...
```

### Factory Pattern
```python
@pytest.fixture
def make_vulnerability():
    def _factory(cve_id="CVE-2026-001", severity="HIGH", **overrides):
        defaults = {"cve_id": cve_id, "severity": severity, "score": 7.5}
        defaults.update(overrides)
        return Vulnerability(**defaults)
    return _factory
```

### Async Testing (pytest-asyncio)
```python
import pytest

@pytest.mark.asyncio
async def test_async_node():
    result = await classify_node(state)
    assert result["classification"] == "CRITICAL"
```

## Best Practices

1. **Factory fixtures** over complex parametrization for object creation
2. **Scope wisely** — `session` for expensive setup, `function` (default) for isolation
3. **conftest.py** for shared fixtures — pytest auto-discovers them
4. **pytest.param** with marks for expected failures and IDs
5. **Indirect parametrize** to pass params through fixtures
6. **Strict mode** — enable `--strict-markers` and `--strict-config`
7. **tmp_path** fixture for temp files (built-in, auto-cleanup)
8. **monkeypatch** over unittest.mock.patch where possible
