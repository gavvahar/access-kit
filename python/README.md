# access-kit Python

Typed backend primitives for ClearRead and SoundSight. Use the latest stable Python 3 release.

## Install

The PyPI distribution is `gavvahar-access-kit`; Python imports use `access_kit`.
The prepared Python release is `1.0.1` (publication status is in the roadmap).

```bash
python -m pip install 'gavvahar-access-kit==1.0.1'
```

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
accepts verified Cloudflare connections and configure trusted proxy networks in
`client_ip`; a header alone never establishes proxy trust.

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

## Logging and request IDs

```python
import logging
from access_kit.logging import request_id_middleware, setup_logging

setup_logging(settings)
app = request_id_middleware(app)
logging.info("request_done", extra={"status_code": 200, "duration_ms": 12})
```

Wrap the complete ASGI app so error responses also receive `X-Request-ID`.
IDs are generated on the server and isolated between concurrent requests.
`get_request_id()` returns the current ID and resets after the request.

The default JSON handler keeps constant event names, safe numeric fields, known
HTTP methods/provider names, and validated request IDs. It drops bodies, headers,
URLs, IPs, arbitrary metadata, formatted arguments, exception text, and tracebacks.
Use constant event names: never put user text in an event name. Configure logging
at process startup, before installing additional handlers. Separate log handlers
installed by an app must apply their own equivalent redaction.

## Privacy and anonymous sessions

```python
from access_kit.privacy import client_ip, hash_ip
from access_kit.session import session_middleware

app = session_middleware(app, secret=settings.session_secret.get_secret_value())
# Inside a request handler:
# peer = client_ip(request)
# identifier = hash_ip(peer, settings.ip_hash_salt.get_secret_value()) if peer else None
```

`client_ip` ignores forwarding headers by default. Cloudflare extraction requires
both `trust_cloudflare=True` and explicit `trusted_proxies` CIDRs. The ASGI client
address must be the actual socket peer; unconditional upstream proxy-header
rewriting would undermine that check. Keep proxy networks current in the app.
Malformed or duplicate Cloudflare headers fall back to the verified peer.

`hash_ip` uses HMAC-SHA256 and a 32-byte minimum salt, normalizing equivalent IPv6
and mapped IPv4 literals. The application owns retention/deletion; there is no
generic SQL deletion helper. Rotating the salt changes identifiers.

Use `Depends(get_session_id)` from `access_kit.session` to read the anonymous ID.
Cookies are HMAC-signed, expire after one year, and use HttpOnly, Secure,
SameSite=Lax, and Path=/. Pass `secure=False` only for local HTTP development.
Tampered or expired cookies are replaced without raising a request error.

`rotate_session(request)` changes the current ID before response headers are sent.
Stateless rotation does not revoke old signed cookies. Apps that need revocation
must reject the old ID in their data store. The cookie is not authentication or
CSRF protection.

## Safe fetching

```python
from pathlib import Path
from access_kit.safe_fetch.fetcher import make_fetcher

fetch, download = make_fetcher(max_bytes=5_000_000, total_timeout=15)
result = await fetch("https://example.com/document")
# result.url, result.content, result.content_type, result.status_code
await download("https://example.com/document", Path("document.html"))
```

HTTP(S) URLs may use only ports 80 or 443, with no credentials or local names.
Every DNS answer must be public; mixed public/private answers are rejected.
The validated numeric IP is used as the socket target, with the original Host
and TLS verification hostname preserved. Each redirect gets a new client and
fresh validation, including rejection of HTTPS-to-HTTP downgrades. Proxy settings,
ambient cookies, automatic redirects, and HTTP retries are disabled.

The default media types are HTML, XHTML, plain text, and JSON. Supply an explicit
`allowed_content_types=frozenset({...})` for other content. Content encoding must
be identity to avoid decompression bombs. Announced and streamed byte counts are
bounded, and the total timeout includes DNS, redirects, and body reads.

Downloads write to a temporary file and publish atomically after success. Existing
paths are never overwritten. Failures and cancellation remove temporary files.
Disk writes are synchronous in bounded chunks; network deadlines cannot interrupt
blocking filesystem operations. File types and fetched HTML remain untrusted:
apps must sanitize content and enforce suitable rendering/download policies.

Errors live in `access_kit.safe_fetch.errors`: `BlockedDestination`, `TooLarge`,
`BadContentType`, `TooManyRedirects`, `FetchTimeout`, and their base `FetchError`.
Error messages omit submitted URLs and response bodies.

IP pinning uses HTTPX's documented
[`sni_hostname` extension](https://www.python-httpx.org/advanced/extensions/).
The regression suite tests actual HTTPX/httpcore socket arguments and TLS names,
not only mocked responses. Reusable attack URLs live in
`access_kit.testing.ssrf_cases.SSRF_CASES`; redirect, rebinding, cancellation,
streaming-limit, and TLS tests are maintained in `python/tests/test_safe_fetch.py`.

## LLM providers and strict JSON

```python
from typing import TypedDict
from access_kit.llm.factory import provider_from_settings

Summary = TypedDict("Summary", {"summary": str})
provider = provider_from_settings(settings)
result, tokens = await provider["complete_json"]("Summarize the document.", "Document content", Summary)
```

Configure `LLM_PROVIDER` (`anthropic`, `ollama`, or `omniroute`) and `LLM_MODEL`
explicitly. Remote models and credentials are never selected implicitly.
`LLM_API_KEY` is a redacted secret. `LLM_BASE_URL` overrides the trusted provider
endpoint. Ollama defaults to `http://localhost:11434/v1`; OmniRoute requires an
explicit base URL and API key. Remote endpoints must use HTTPS; HTTP is allowed
only on loopback. Provider endpoint configuration is trusted app configuration,
not a place to pass user-submitted URLs.

Direct factories live in `access_kit.llm.providers`. Both adapters expose a dict
with `complete_text`, `complete_json`, provider name, model, and an input limit.
They use the [Anthropic Messages API](https://platform.claude.com/docs/en/api/messages/create)
and [Ollama's OpenAI-compatible Chat Completions API](https://docs.ollama.com/api/openai-compatibility).
Models are always caller-selected. The input limit is enforced as a conservative
UTF-8 byte cap plus 1,024 bytes of framing allowance, not a tokenizer or a billing
estimate. The provider remains responsible for its actual model context limit.

`complete_json` validates with a Pydantic TypeAdapter in strict mode. It retries
invalid JSON/schema responses twice by default; fences and string-to-integer
coercion are not accepted. Retry limits are configurable from zero to five.
Transport failures, refusals, truncation, and tool calls fail explicitly.
HTTP responses are bounded to one MB and have a total timeout; HTTP retries and
redirect following are disabled. Injected HTTPX clients remain caller-owned.

`Usage` contains `input_tokens`, `output_tokens`, `total_tokens`, and `complete`.
Anthropic cached input tokens are included. JSON retries and explicit provider
fallbacks accumulate usage across failed attempts. Errors also carry `.usage`.
`complete=False` means some usage could not be established, for example after a
connection reset. Do not interpret unknown usage as zero spending.

`with_fallback([...])` in `access_kit.llm.core` is opt-in: it sends the prompt to
each configured provider in order until one succeeds. If every provider fails,
`LLMFallbackError` retains sanitized errors and accumulated known usage.
Weighted rate limiting and daily budgets are available as explicit protection
modules. Provider factories do not silently apply a cap: reserve a verified upper
bound before dispatch, including every possible retry and fallback attempt.

## Consumer test helpers

Install `gavvahar-access-kit[testing]` for pytest/fakeredis support. Fixtures are opt-in:

```python
# conftest.py
pytest_plugins = ["access_kit.testing.fixtures"]
```

The async `fake_redis` fixture closes its in-memory client after each test.
`fake_llm` in `access_kit.testing.fakes` returns `(provider, calls)` and runs the
same JSON validation and retry logic as real providers. Supply strings or
`LLMError` instances as deterministic responses; exhausted responses fail clearly.
The call records retain prompts in test memory and must not be used in production.

All Python `__init__.py` files are empty. Import from named modules rather than
package-level re-exports. Read the installed version with
`importlib.metadata.version("access-kit")`.

## Release acceptance

The library core and a consumer-style FastAPI integration test are implemented.
ClearRead's Phase 1 pipeline is not present in its current template repository,
so the planned `py-v0.1.0` consuming-app acceptance check is still pending.
The protection and progress modules are implemented and tested locally; real
consuming-app acceptance and authenticated registry uploads remain pending.
See [the roadmap](https://github.com/gavvahar/access-kit/blob/main/docs/roadmap.md).

## Protection, delivery, and job progress

`ratelimit`, `turnstile`, `budget`, and `notify` are documented with configuration,
error handling and operating constraints in [the protection guide](https://github.com/gavvahar/access-kit/blob/main/docs/protection.md).
`jobs` provides owner-scoped worker progress and a FastAPI SSE response helper;
see [job integration](https://github.com/gavvahar/access-kit/blob/main/docs/jobs.md). Public infrastructure exceptions live in
`access_kit.errors`. Storage failure must deny protected work.

Install `[testing]` or `[dev]` to run Redis Lua scripts with fakeredis. On the
latest Python, a native Lua wheel may need the compiler toolchain supplied by
`environment.yml`; no sudo is required. The real Redis CI check independently
exercises concurrent budget admission, weighted limits and job event replay.
The [API inventory](https://github.com/gavvahar/access-kit/blob/main/docs/api.md) covers every supported module; the
[architecture decisions](https://github.com/gavvahar/access-kit/blob/main/docs/decisions.md) explain ownership and lifecycle.

## Bounded HTTP requests

Wrap an ASGI app with `access_kit.http.body_limit(app, max_bytes=1_000_000,
read_timeout=15)` before exposing JSON/document endpoints. Oversized declared or
streamed bodies receive 413 before framework parsing. Duplicate/invalid/mismatched
Content-Length receives 400; body-read timeout receives 408. Non-HTTP scopes pass
through. Valid bodies replay once, then preserve the original disconnect stream.
This buffers bounded requests; use a separate design for streaming uploads.

`provider_from_settings` accepts explicit `max_tokens`, `max_input_tokens`,
`timeout` and `json_retries` overrides. Consumer budgets can reserve the true
upper bound across those bounded attempts instead of guessing factory defaults.
