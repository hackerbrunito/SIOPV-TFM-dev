# PyJWT (jwt) — Context7 Cache

## Current Version: PyJWT 2.9+

## Key API Patterns

### Encoding
```python
import jwt

token = jwt.encode(
    payload={"sub": "user_id", "exp": datetime.now(UTC) + timedelta(hours=1)},
    key="secret",
    algorithm="HS256",
)
```

### Decoding
```python
payload = jwt.decode(
    token,
    key="secret",
    algorithms=["HS256"],  # MUST specify allowed algorithms
    options={"require": ["exp", "sub"]},
)
```

### RS256 (asymmetric — production)
```python
# Encode with private key
token = jwt.encode(payload, private_key, algorithm="RS256")
# Decode with public key
payload = jwt.decode(token, public_key, algorithms=["RS256"])
```

### JWKS (OpenID Connect)
```python
from jwt import PyJWKClient

jwks_client = PyJWKClient("https://issuer/.well-known/jwks.json")
signing_key = jwks_client.get_signing_key_from_jwt(token)
payload = jwt.decode(token, signing_key.key, algorithms=["RS256"], audience="api")
```

### Error Handling
- `jwt.ExpiredSignatureError` — token expired
- `jwt.InvalidTokenError` — base class for all errors
- `jwt.DecodeError` — malformed token
- `jwt.InvalidAudienceError` — audience mismatch

### Best Practices
- ALWAYS specify `algorithms=[]` in decode (prevent algorithm confusion attacks)
- Use RS256 for production (asymmetric keys)
- Always validate `exp`, `aud`, `iss` claims
- Use `PyJWKClient` for OIDC/JWKS integration
