# access-kit Python

Typed backend primitives for ClearRead and SoundSight. Requires Python 3.12+.

## Install

From the repository root:

```bash
python -m pip install -e './python[dev]'
pytest
mypy
python -m build python
```

## Settings

Subclass `access_kit.settings.AccessKitSettings` for application-specific fields.
Process environment is loaded case-insensitively. Required fields:

| Variable          | Validation                     |
| ----------------- | ------------------------------ |
| `APP_NAME`        | Nonempty string                |
| `PUBLIC_BASE_URL` | HTTP or HTTPS URL              |
| `REDIS_URL`       | Redis DSN                      |
| `SESSION_SECRET`  | Secret, at least 32 characters |
| `IP_HASH_SALT`    | Secret, at least 32 characters |

`ENV` is `dev`, `test`, or `prod` (default `dev`).
`TRUST_CLOUDFLARE_HEADERS` defaults to false. Enable it only when the origin
accepts verified Cloudflare connections. Header extraction is not implemented yet.

Dotenv loading is opt-in: `Settings(_env_file=".env")`.
Secret fields are redacted in representations; do not log full settings objects,
validation error dictionaries, connection URLs, or raw input.

The configuration uses [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).

## Health

```python
from fastapi import FastAPI
from access_kit.health import health_router

app = FastAPI()


async def database_ready() -> bool:
    # Replace with the app's asynchronous database ping.
    return True


app.include_router(health_router({"database": database_ready}, timeout=2.0))
```

Checks run concurrently. Any exception, timeout, or return value other than
`True` yields HTTP 503. A healthy response is:

```json
{ "status": "ok", "checks": { "database": "ok" } }
```

Responses use `Cache-Control: no-store` and never contain exception messages.
Check names are public: use names such as `database`, not connection strings.
Checks must use asynchronous I/O and cooperate with cancellation. Timeouts cannot
interrupt blocking code. Without checks, `/healthz` is a liveness endpoint.

HTTP status handling follows [FastAPI's response API](https://fastapi.tiangolo.com/advanced/additional-status-codes/).

## Planned modules

Logging, privacy, sessions, safe fetching, LLM providers, and testing fakes are
not implemented yet. See [the roadmap](../docs/roadmap.md).
