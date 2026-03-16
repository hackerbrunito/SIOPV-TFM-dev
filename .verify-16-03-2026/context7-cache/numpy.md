# NumPy — Context7 Cache

## Current Version: numpy 2.x

## Key API Patterns

### Array Creation
- `np.array([1, 2, 3])`, `np.zeros(shape)`, `np.ones(shape)`
- `np.arange(start, stop, step)`, `np.linspace(start, stop, num)`
- `np.random.default_rng(seed=42)` — new random generator (preferred over np.random.seed)

### Type Hints
- `import numpy as np`
- `from numpy.typing import NDArray`
- `NDArray[np.float64]` — typed array annotation
- `np.floating[Any]` for generic float types

### Operations
- Vectorized operations preferred over loops
- Broadcasting rules for shape-compatible arrays
- `np.where(condition, x, y)` — conditional selection

### Best Practices
- Use `numpy.typing.NDArray` for type annotations
- Use `default_rng()` instead of legacy `np.random.seed()`
- Prefer vectorized ops over Python loops
- Use `np.float64` explicitly (not Python `float`) for array dtypes
