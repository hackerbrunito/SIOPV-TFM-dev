# Pydantic — Context7 Cache

## Current Version: Pydantic v2.x (2.11+)

## Key API Patterns

### Configuration
- `model_config = ConfigDict(...)` replaces `class Config:`
- Common settings: `frozen=True` (replaces `allow_mutation=False`), `str_strip_whitespace=True`, `validate_default=True`, `arbitrary_types_allowed=True`
- `ConfigDict` is a TypedDict — provides IDE autocompletion

### Validators
- `@field_validator("field_name")` replaces `@validator`
- `@model_validator(mode="before")` / `@model_validator(mode="after")` replaces `@root_validator`
- `mode="before"` receives raw dict; `mode="after"` receives model instance
- `@field_validator` must be `@classmethod`

### Model Methods
- `model_dump()` replaces `.dict()`
- `model_dump_json()` replaces `.json()`
- `model_validate(data)` replaces `parse_obj(data)`
- `model_validate_json(json_str)` replaces `parse_raw(json_str)`
- `model_json_schema()` replaces `schema()`

### Field Definitions
- `Field(default=..., description=..., alias=...)` — same as v1 but with additional params
- `Field(exclude=True)` to exclude from serialization
- `Field(validate_default=True)` to validate defaults
- `validate_by_alias` and `validate_by_name` (v2.11+) for fine-grained control

### Type Annotations
- Use `Annotated[type, Field(...)]` pattern for complex field metadata
- `SecretStr` for sensitive values — `.get_secret_value()` to access
- Generic models: `class MyModel(BaseModel, Generic[T])`

### Serialization
- `model_serializer` decorator for custom serialization
- `@field_serializer("field")` for per-field custom serialization
- `SerializationInfo` context available in serializers

### Deprecated (DO NOT USE)
- `class Config:` → use `model_config = ConfigDict(...)`
- `@validator` → use `@field_validator`
- `@root_validator` → use `@model_validator`
- `.dict()` → use `.model_dump()`
- `.json()` → use `.model_dump_json()`
- `parse_obj()` → use `model_validate()`
- `update_forward_refs()` → use `model_rebuild()`
