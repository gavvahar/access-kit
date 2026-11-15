"""Bounded outbound requests to application-configured service endpoints."""

import asyncio, json, httpx
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any


from access_kit.errors import ServiceUnavailable


@asynccontextmanager
async def borrow_client(existing: httpx.AsyncClient | None) -> AsyncIterator[httpx.AsyncClient]:
    if existing is not None:
        yield existing
    else:
        async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as owned:
            yield owned


def service_url(value: str) -> str:
    try:
        url = httpx.URL(value)
    except httpx.InvalidURL:
        raise ValueError("invalid service endpoint") from None
    local = url.host in {"localhost", "127.0.0.1", "::1"}
    if not url.host or url.userinfo or url.fragment or (url.scheme != "https" and not (url.scheme == "http" and local)):
        raise ValueError("service endpoint must use HTTPS, or HTTP on loopback, without URL credentials")
    return str(url)


async def request_bytes(
    url: str, *, client: httpx.AsyncClient | None, timeout: float, headers: Mapping[str, str] | None = None, payload: dict[str, Any], max_bytes: int = 65536
) -> bytes:
    try:
        async with asyncio.timeout(timeout), borrow_client(client) as connection:
            async with connection.stream(
                "POST",
                url,
                content=json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(),
                headers={"Content-Type": "application/json", **(headers or {}), "Accept-Encoding": "identity"},
                follow_redirects=False,
                timeout=timeout,
            ) as response:
                if not 200 <= response.status_code < 300 or response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise ServiceUnavailable("service returned an unsuccessful response")
                result = bytearray()
                async for chunk in response.aiter_raw(chunk_size=16384):
                    result.extend(chunk)
                    if len(result) > max_bytes:
                        raise ServiceUnavailable("service response exceeded its byte limit")
                return bytes(result)
    except (TimeoutError, httpx.HTTPError):
        raise ServiceUnavailable("service request failed") from None
