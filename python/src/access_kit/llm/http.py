"""Bounded HTTP JSON calls shared by provider adapters."""

import asyncio
import json
import math
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any

import httpx

from access_kit.llm.types import LLMError, Usage, usage


def endpoint(base_url: str, path: str) -> str:
    url = httpx.URL(base_url)
    local = url.host in {"localhost", "127.0.0.1", "::1"}
    if (url.scheme != "https" and not (url.scheme == "http" and local)) or not url.host or url.userinfo or url.query or url.fragment:
        raise ValueError("provider URL must be HTTPS (HTTP allowed only for loopback), without credentials/query/fragment")
    return str(url).rstrip("/") + "/" + path.lstrip("/")


@asynccontextmanager
async def _client(existing: httpx.AsyncClient | None) -> AsyncIterator[httpx.AsyncClient]:
    if existing is not None:
        yield existing
    else:
        async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as owned:
            yield owned


async def post_json(
    url: str, headers: Mapping[str, str], payload: dict[str, object], *, client: httpx.AsyncClient | None, timeout: float, max_response_bytes: int = 1_000_000
) -> dict[str, Any]:
    """No automatic HTTP retries or redirects. Injected clients remain caller-owned."""
    try:
        async with asyncio.timeout(timeout), _client(client) as connection:
            async with connection.stream("POST", url, headers={**headers, "Accept-Encoding": "identity"}, json=payload, follow_redirects=False, timeout=timeout) as response:
                if response.status_code != 200:
                    raise LLMError(f"provider HTTP status {response.status_code}")
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise LLMError("encoded provider response is not supported")
                body = bytearray()
                async for chunk in response.aiter_raw(chunk_size=65_536):
                    body.extend(chunk)
                    if len(body) > max_response_bytes:
                        raise LLMError("provider response exceeds byte limit")
        data = json.loads(body)
        if not isinstance(data, dict):
            raise ValueError("not an object")
        return data
    except (TimeoutError, httpx.HTTPError, ValueError):
        raise LLMError("provider transport or JSON response failed") from None


def validate_limits(max_tokens: int, max_input_tokens: int, timeout: float) -> None:
    if type(max_tokens) is not int or max_tokens <= 0 or type(max_input_tokens) is not int or max_input_tokens <= 0 or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("provider limits and timeout must be positive")


def check_input(system: str, user: str, max_input_tokens: int) -> None:
    # A conservative byte cap, not a tokenizer or a billing estimate. Leave room
    # for message framing; actual model context limits remain provider-enforced.
    if len(system.encode()) + len(user.encode()) + 1024 > max_input_tokens:
        raise LLMError("input exceeds conservative provider byte limit", consumed=usage())


def token_count(data: dict[str, Any], key: str, *, default: int | None = None) -> int:
    value = data.get(key, default)
    if type(value) is not int or value < 0:
        raise LLMError("provider returned invalid or missing token usage")
    return int(value)


def read_usage(data: dict[str, Any], *, input_key: str, output_key: str, extra_input_keys: tuple[str, ...] = ()) -> Usage:
    raw = data.get("usage")
    if not isinstance(raw, dict):
        raise LLMError("provider returned no token usage")
    inputs = token_count(raw, input_key) + sum(token_count(raw, key, default=0) for key in extra_input_keys)
    return usage(inputs, token_count(raw, output_key))
