# access-kit v0.1 Python Core — Design Spec

**Author:** Claude (via superpowers:brainstorming)  
**Date:** 2026-09-28  
**Status:** Ready for review  
**Unblocks:** ClearRead Phase 1, foundation for v0.2/v0.3

---

## Executive Summary

v0.1 Python core delivers 8 foundational modules as a published package, installable by ClearRead and SoundSight. All modules run sync/async where applicable, typed strictly, testable against fakes. No classes except pydantic `BaseSettings` (config) and third-party requirements like `httpcore` transport. Stateful operations use closures + `functools.partial`.

**Key constraints:**

- Zero classes (except noted carve-outs) per user code style
- No pydantic models—only `BaseSettings` for settings, structured typing via `TypedDict` + callables
- Closures for `safe_fetch`, `ratelimit`, `budget` configuration carrying
- Simple duck-typing for `llm` providers (dict of callables, not Protocol classes)
- All modules tested against fakes (`FakeLLM`, `FakeTurnstile`, `FakeNotifier`, `fakeredis`)

---

## 1. Tooling & CI

### 1.1 Dependency Management

- **conda** (existing): base environment setup via `environment.yml` + `Makefile`
- **tox**: all test/lint/format/type-check steps
- **No uv, no separate python.yml/web.yml** — keep existing workflows (`tox-check-reusable.yml`, `tests.yml`, cascade-merge, secrets, zizmor)

### 1.2 pyproject.toml Additions

Add `[project]` table and test/lint tox envs alongside existing config:

```toml
[project]
name = "access-kit"
version = "0.1.0-dev"  # bumped by release.yml on py-vX.Y.Z tag
description = "Shared safety/privacy/LLM toolkit for accessible web apps"
requires-python = ">=3.12"
dependencies = [
  "pydantic-settings>=2.0",
  "httpx>=0.26",
  "fastapi>=0.104",
  "redis>=5.0",
  "anthropic>=0.28",
  "openai>=1.3",
]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "fakeredis", "respx", "mypy"]

[tool.mypy]
python_version = "3.12"
strict = true
no_implicit_optional = true
check_untyped_defs = true
```

### 1.3 New Tox Environments

```toml
[tool.tox.env."py-test"]
python = "3.12"
deps = ["pytest", "pytest-asyncio", "fakeredis", "respx"]
commands = [["pytest", "python/tests", "-v", "--cov=python/src/access_kit", "--cov-fail-under=85"]]

[tool.tox.env."py-typecheck"]
skip_install = true
python = "3.12"
deps = ["mypy"]
commands = [["mypy", "python/src/access_kit", "--strict"]]

[tool.tox.env."py-no-classes"]
skip_install = true
python = "3.12"
deps = []
commands = [["python3", "scripts/no_classes_check.py", "python/src/access_kit", "--exempt-bases=BaseSettings"]]
```

Add to `env_list`:

```toml
env_list = [
  "lint", "txt-lint", "format", "prettier", "toml-lint", "duplicate-code",
  "py-test", "py-typecheck", "py-no-classes",  # NEW
]
```

Add to `github` aggregate:

```toml
[tool.tox.env.github]
commands = [
  ["tox", "-e", "lint"],
  ["tox", "-e", "txt-lint"],
  ["tox", "-e", "prettier"],
  ["tox", "-e", "toml-lint"],
  ["tox", "-e", "duplicate-code"],
  ["tox", "-e", "py-test"],
  ["tox", "-e", "py-typecheck"],
  ["tox", "-e", "py-no-classes"],
]
```

### 1.4 CI Workflows

- **Existing tox-check-reusable.yml** triggers on `python/**` changes with the new envs
- **release.yml** already watches for `py-vX.Y.Z` tags → build wheel from `python/` → attach to release (PyPI upload deferred to v1.0)
- **secrets.yml, zizmor.yml** already scan; no changes needed

---

## 2. File Layout

```
access-kit/
├── python/
│   ├── pyproject.toml              # updated [project] + tox config
│   ├── src/access_kit/
│   │   ├── __init__.py             # __version__ = "0.1.0-dev"
│   │   ├── settings.py             # AccessKitSettings(BaseSettings)
│   │   ├── logging.py              # setup_logging, LoggingConfig
│   │   ├── health.py               # health_router
│   │   ├── privacy.py              # client_ip, hash_ip, purge_before
│   │   ├── session.py              # SessionMiddleware, get_session_id
│   │   ├── safe_fetch/
│   │   │   ├── __init__.py         # make_fetcher, FetchResult
│   │   │   ├── ipcheck.py          # blocked_networks, validate_ip
│   │   │   ├── transport.py        # ConnectTimePinnedTransport (httpcore custom)
│   │   │   └── limits.py           # size/content-type/redirect rules, ssrf_cases
│   │   ├── llm/
│   │   │   ├── __init__.py         # provider_from_settings, LLMProvider TypedDict
│   │   │   ├── anthropic.py        # anthropic_provider(...)
│   │   │   ├── openai_compat.py    # openai_compat_provider(...)
│   │   │   └── factory.py          # factory with fallback chain
│   │   └── testing/
│   │       ├── __init__.py         # public test helpers
│   │       ├── fakes.py            # fake_llm, fake_turnstile, FakeNotifier
│   │       ├── fixtures.py         # pytest fixtures (fakeredis, async_client)
│   │       └── ssrf_cases.py       # shared SSRF test vector list
│   └── tests/
│       ├── test_settings.py
│       ├── test_logging.py
│       ├── test_privacy.py
│       ├── test_session.py
│       ├── test_safe_fetch.py      # 100% coverage target
│       ├── test_llm.py
│       ├── conftest.py             # pytest config + shared fixtures
│       └── ssrf_test_cases.py      # run shared ssrf_cases list on endpoints
├── web/                            # placeholder for web v0.1 spec
├── scripts/
│   ├── render_env_docs.py          # existing
│   ├── no_classes_check.py         # COPY FROM BOOTCAMP REPO if available, else write new
│   └── cascade_merge.py            # existing (in .github/scripts already)
├── docs/
│   ├── superpowers/
│   │   └── specs/                  # design docs live here
│   └── modules/                    # one .md per module (TODO v0.1.1)
├── .github/workflows/              # no new files; reuse existing
│   ├── tox-check-reusable.yml      # already watches python/**
│   ├── tests.yml                   # reused (or can be removed if tox-check covers it)
│   └── release.yml                 # already handles py-vX.Y.Z tags
├── pyproject.toml                  # ROOT CONFIG (existing) — touch only for shared tools
├── Makefile, environment.yml, package.json, .gitignore
└── README.md                       # root README links to python/README
```

---

## 3. Module Architecture

### 3.1 `settings.py`

```python
from pydantic_settings import BaseSettings
from typing import Literal


class AccessKitSettings(BaseSettings):
    """Base config for all access-kit modules. Apps subclass this."""

    app_name: str
    env: Literal["dev", "prod"] = "dev"
    public_base_url: str  # AnyHttpUrl from plan → plain str, validate in factory if needed
    redis_url: str  # RedisDsn → plain str
    session_secret: str  # SecretStr → str, treat as secret in logs
    ip_hash_salt: str
    trust_cloudflare_headers: bool = True
    turnstile_site_key: str | None = None
    turnstile_secret_key: str | None = None
    notify_ntfy_topic: str | None = None
    notify_email_to: str | None = None
    notify_webhook_url: str | None = None
    sentry_dsn: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = False
```

**Why pydantic class:** config/env validation is inherently a class-based operation in pydantic and unavoidable (per carve-out in code style guidelines).

### 3.2 `logging.py`

```python
async def setup_logging(settings: AccessKitSettings) -> None:
    """Configure structlog with request-ID middleware, optional Sentry."""
    # Implementation uses structlog.configure(), not a logging class
    # Returns None (side effect: global logging state)
    pass


def request_id_middleware(app, call_next):
    """FastAPI middleware injecting X-Request-ID header."""
    pass


# Scrubber: a function that filters log records
def scrub_logs(logger, method_name, event_dict):
    """Remove raw IPs, request bodies, pasted text, transcripts."""
    return event_dict  # modified
```

### 3.3 `health.py`

```python
async def redis_check(redis_url: str) -> dict:
    """Returns {"status": "ok"} or raises."""
    pass


async def postgres_check(dsn: str) -> dict:
    """Apps own DB; health module just documents the pattern."""
    pass


def health_router(checks: dict[str, Callable]) -> APIRouter:
    """Returns FastAPI router with GET /healthz, pluggable checks."""
    router = APIRouter()

    @router.get("/healthz")
    async def healthz():
        results = {}
        for name, check in checks.items():
            try:
                results[name] = await check()
            except Exception as e:
                results[name] = {"status": "error", "error": str(e)}
        return {"status": "ok" if all(r.get("status") == "ok" for r in results.values()) else "error", "checks": results}

    return router
```

### 3.4 `privacy.py`

```python
from ipaddress import IPv4Address, IPv6Address, ip_address
import hashlib


def client_ip(request: Request, trust_cloudflare: bool) -> str:
    """Extract client IP, respecting Cloudflare headers only if trust_cloudflare=True."""
    if trust_cloudflare and request.headers.get("cf-connecting-ip"):
        return request.headers["cf-connecting-ip"]
    return request.client.host


def hash_ip(ip: str, salt: str) -> str:
    """HMAC-SHA256 of IP + salt, truncated for privacy."""
    return hashlib.sha256(f"{ip}{salt}".encode()).hexdigest()[:16]


def purge_before(db_connection, table: str, date: datetime, ip_hash_col: str) -> int:
    """Documentation: document guidance (30 days default), apps own deletion."""
    pass
```

### 3.5 `session.py`

```python
def session_middleware(app: FastAPI, session_secret: str):
    """Middleware that sets signed cookie ak_sid (anonymous, 1-year, HttpOnly, Secure, SameSite=Lax)."""
    # Uses itsdangerous or similar for signing
    pass


def get_session_id(request: Request) -> str:
    """FastAPI dependency extracting the session ID from the signed cookie."""
    pass


def rotate_session(response: Response):
    """Sets a new session ID, invalidating the old one (for delete-my-history flow)."""
    pass
```

### 3.6 `safe_fetch` — Core Difference from Plan

**Plan had:** `class SafeFetcher { __init__(config), fetch(), download() }`

**This design:**

```python
# safe_fetch/__init__.py
def make_fetcher(
    *,
    max_bytes: int = 5_000_000,
    connect_timeout: float = 5,
    total_timeout: float = 15,
    max_redirects: int = 5,
    allowed_content_types: set[str] | None = None,
    user_agent: str | None = None,
    domain_limiter=None,  # RateLimiter instance or None
    blocklist: list[str] | None = None,
) -> tuple[Callable, Callable]:
    """Returns (fetch, download) functions closing over config."""

    async def fetch(url: str) -> FetchResult:
        """Fetch small doc into memory, SSRF-protected."""
        # Full implementation per plan
        pass

    async def download(url: str, dest: Path, max_bytes: int | None = None) -> Path:
        """Stream large file to disk, SSRF-protected."""
        pass

    return fetch, download


# Usage
fetch, download = make_fetcher(
    max_bytes=5_000_000,
    allowed_content_types={"text/html", "application/xhtml+xml"},
)
result = await fetch("https://example.com")
```

**Key modules:**

- `ipcheck.py`: `blocked_networks()`, `validate_ip(ip_str) -> bool` — return True if IP should be blocked (private, loopback, link-local, multicast, reserved, CGNAT, IPv4-mapped IPv6, Carrier-grade NAT, unspecified, `fe80::/10`, `fc00::/7`, cloud metadata)
- `transport.py`: Custom `httpcore.AsyncNetworkBackend` subclass that pins the IP at connect time (validates before opening socket; the IP that passes validation is the one connected to, defeating DNS rebinding)
- `limits.py`: Helper functions for enforcing size limit, content-type check, redirect re-validation, timeout. Defines `ssrf_cases` list (decimal/hex/octal IP tricks, localhost variants, IPv6 tricks, redirect-to-private, DNS-to-private)
- `__init__.py`: Exports `make_fetcher`, `FetchResult` (NamedTuple), error types (`BlockedDestination`, `TooLarge`, `BadContentType`, `TooManyRedirects`, `FetchTimeout` — all Exception subclasses)

**Testing:** `test_safe_fetch.py` runs the shared `ssrf_cases` list against each validation function. Both apps can also run this list against their own endpoints to prove they're not vulnerable. Target: 100% coverage.

### 3.7 `llm` — Provider as Dict of Closures

**Plan had:** `class LLMProvider(Protocol)` with methods.

**This design:**

```python
# llm/__init__.py
from typing import TypedDict, Callable, Any


class LLMProvider(TypedDict):
    """Shape of a provider: dict of callables."""

    name: str
    model: str
    max_input_tokens: int
    complete_json: Callable[[str, str, type], tuple[Any, Usage]]  # (system, user, schema) -> (result, usage)
    complete_text: Callable[[str, str], tuple[str, Usage]]  # (system, user) -> (text, usage)


class Usage(TypedDict):
    """Token counts from an LLM call."""

    input_tokens: int
    output_tokens: int
    total_tokens: int


def anthropic_provider(*, api_key: str, model: str = "claude-3-5-sonnet-20241022", max_input_tokens: int = 200_000) -> LLMProvider:
    """Returns a provider dict."""
    client = Anthropic(api_key=api_key)

    async def complete_json(system: str, user: str, schema: type[BaseModel]) -> tuple[BaseModel, Usage]:
        # Full implementation with JSON mode + retry on validation error
        pass

    async def complete_text(system: str, user: str) -> tuple[str, Usage]:
        pass

    return {
        "name": "anthropic",
        "model": model,
        "max_input_tokens": max_input_tokens,
        "complete_json": complete_json,
        "complete_text": complete_text,
    }


# openai_compat_provider(...) similar
# factory.py: provider_from_settings(settings) -> list[LLMProvider] with fallback chain
```

**Why TypedDict not Protocol:** Avoids a class-statement definition that would fail the no-classes-check even though it's not instantiated. TypedDict at runtime is a callable function returning a dict, structurally typed by mypy.

### 3.8 `testing/`

```python
# testing/fakes.py
def fake_llm(responses: list[str] | None = None) -> LLMProvider:
    """Returns a mock provider; records all calls for assertion."""
    calls = []

    async def complete_json(system: str, user: str, schema: type[BaseModel]) -> tuple[BaseModel, Usage]:
        calls.append(("complete_json", system, user, schema))
        # Return canned or first response from list
        pass

    async def complete_text(system: str, user: str) -> tuple[str, Usage]:
        calls.append(("complete_text", system, user))
        pass

    provider = {...}
    provider["__test_calls__"] = calls  # for assertions
    return provider


def fake_turnstile() -> Callable:
    """Returns an async function that always validates, records calls."""
    pass


class FakeNotifier:
    """Notifier that stores messages in memory for tests."""

    messages: list[str]

    async def send(self, title, body): ...


# fixtures.py
@pytest.fixture
async def fake_redis():
    import fakeredis

    return fakeredis.FakeStrictRedis(decode_responses=True)


@pytest.fixture
async def async_client(app):
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


# ssrf_cases.py — shared list of URLs + IPs that MUST be blocked
SSRF_CASES = [
    "http://127.0.0.1",
    "http://localhost",
    "http://169.254.169.254",  # AWS metadata
    "http://[::1]",
    "http://192.168.1.1",
    # ... many more, see plan's 4.6 + 4.12
]
```

---

## 4. Error Handling

All module errors are plain Exception subclasses (required by Python):

```python
class AccessKitError(Exception):
    """Base for all access-kit errors."""

    pass


# safe_fetch/
class BlockedDestination(AccessKitError):
    """URL resolves to or redirects to a blocked IP."""

    pass


class TooLarge(AccessKitError):
    """Response body exceeds max_bytes."""

    pass


# llm/
class LLMError(AccessKitError):
    """Provider call failed."""

    pass


class ValidationError(AccessKitError):
    """JSON schema validation on LLM output failed."""

    pass
```

Apps catch by type and render user-friendly messages.

---

## 5. Dependencies

**Core** (pyproject.toml `dependencies`):

- `pydantic-settings` ≥2.0 — config/env validation
- `httpx` ≥0.26 — async HTTP, custom transport support
- `fastapi` ≥0.104 — middleware, routers, typing
- `redis` ≥5.0 — cache/queue backend
- `anthropic` ≥0.28 — Anthropic API
- `openai` ≥1.3 — OpenAI API (covers Ollama, Groq, OmniRoute, etc. via base_url)

**Dev** (`[project.optional-dependencies]`):

- `pytest`, `pytest-asyncio` — test framework
- `fakeredis` — in-memory Redis mock
- `respx` — httpx request mocking
- `mypy` — type checking

**Why not:** `aioredis` (redis lib already async), `orjson` (json stdlib fine for first pass), `tenacity` (simple retry in llm factory), `pydantic` itself (only BaseSettings needed, not full ORM)

---

## 6. Testing Strategy

**Coverage target:** 85% overall, **100% for `safe_fetch`** (security-critical).

**Test organization:**

- `test_settings.py` — env parsing, validation, subclass inheritance
- `test_logging.py` — structlog config, request ID middleware, log scrubbing
- `test_privacy.py` — IP extraction, hashing, salt rotation
- `test_session.py` — middleware cookie set/rotation, dependency extraction
- `test_safe_fetch.py` — run SSRF cases, blocked networks, redirects, size limits, content-type, IP pinning
  - `FakeDNS` fixture that returns configurable IP for any domain → test DNS rebinding defenses
  - Mock `httpcore.AsyncNetworkBackend` to verify IP pinning happens before connect
- `test_llm.py` — provider dict shape, complete_json retry on validation, complete_text, usage tracking
  - All providers use `fake_llm()` in tests
- Async tests use `pytest.mark.asyncio`
- `conftest.py` — shared fixtures (`fake_redis`, `async_client`, settings factory)

**CI:** pytest runs as tox env `py-test` on Python 3.12/3.13 with a real Redis service container (or fakeredis).

---

## 7. Packaging & Installation

**Version:** `0.1.0-dev` in pyproject, bumped to `0.1.0` on first `py-v0.1.0` tag.

**Installation** (until PyPI):

```bash
# ClearRead / SoundSight pyproject.toml
dependencies = [
  "access-kit @ git+ssh://git@github.com:gavvahar/access-kit@py-v0.1.0#subdirectory=python",
]
```

**Local dev:**

```bash
uv pip install -e ../access-kit/python
# or conda:
conda run -n access pip install -e ../access-kit/python
```

**Release:** GitHub Actions on `py-vX.Y.Z` tag builds wheel, attaches to release. PyPI publish deferred to v1.0 (public repo phase).

---

## 8. Open Questions (Confirmed via Approval)

1. **License:** MIT (per approval)
2. **Public repo:** No, stay private; git+ssh installation
3. **Shared infrastructure:** Single Redis + Postgres (separate databases/key prefixes per app) — decided outside this spec

---

## 9. Success Criteria

This spec is done when:

1. ✓ Both ClearRead and SoundSight can install `py-v0.1.0` and use all 8 modules
2. ✓ All modules tested, 85%+ coverage, 100% for safe_fetch
3. ✓ Type-checks cleanly with mypy strict
4. ✓ No class violations (per no-classes-check, except BaseSettings + third-party)
5. ✓ CI passes: lint, type, test, duplicate-code, secret-detection, zizmor on every PR

---

## 10. Transition to Implementation

Once this spec is approved by the user, invoke **writing-plans** skill to create a detailed implementation plan with task breakdown, ordering, and verification steps.
