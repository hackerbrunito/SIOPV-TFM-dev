# OpenFGA SDK — Context7 Cache

## Current Version: openfga-sdk 0.9.3

## Key API Patterns

### Client Setup
- `from openfga_sdk import ClientConfiguration, OpenFgaClient`
- `from openfga_sdk.credentials import Credentials, CredentialConfiguration`
- Initialize `OpenFgaClient` once, reuse throughout app (connection pooling)
- Use as async context manager: `async with OpenFgaClient(config) as client:`

### Configuration
```python
config = ClientConfiguration(
    api_url="http://localhost:8080",
    store_id="store-id",
    authorization_model_id="model-id",
)
```

### Authentication Methods
1. **API Token**: `Credentials(method="api_token", configuration=CredentialConfiguration(api_token="token"))`
2. **Client Credentials (OIDC)**: `Credentials(method="client_credentials", configuration=CredentialConfiguration(api_issuer="...", api_audience="...", client_id="...", client_secret="..."))`

### Core Operations
- **Check**: `client.check(ClientCheckRequest(user="user:anne", relation="viewer", object="document:budget"))`
- **Write tuples**: `client.write(ClientWriteRequest(writes=[ClientTupleKey(user=..., relation=..., object=...)]))`
- **Read tuples**: `client.read(ClientReadRequest(...))`
- **ListObjects**: `client.list_objects(ClientListObjectsRequest(user=..., relation=..., type=...))`
- **Expand**: `client.expand(ClientExpandRequest(...))`

### Retry Behavior
- Default: retries up to 3 times on 429 and 5xx errors
- Configurable via `ClientConfiguration`

### Best Practices
- Single client instance per application
- Use `store_id` and `authorization_model_id` in config, not per-request
- Close client properly (use context manager)
