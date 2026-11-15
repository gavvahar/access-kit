"""Bounded, SSRF-resistant HTTP fetching and atomic downloads.

Each hop resolves once, validates every DNS answer, and connects to a numeric IP.
The Host header and TLS SNI retain the original hostname. Ambient proxies, cookies,
redirect following, retries, and content decompression are disabled.
"""

import asyncio
import math
import os
import tempfile
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import NamedTuple

import httpx

from access_kit.safe_fetch.errors import BadContentType, BlockedDestination, FetchError, FetchTimeout, TooLarge, TooManyRedirects
from access_kit.safe_fetch.ipcheck import resolve_public, validate_url

__all__ = ["make_fetcher", "FetchResult", "BadContentType", "BlockedDestination", "FetchError", "FetchTimeout", "TooLarge", "TooManyRedirects"]


class FetchResult(NamedTuple):
    url: str
    content: bytes
    content_type: str
    status_code: int


type Fetch = Callable[[str], Awaitable[FetchResult]]
type Download = Callable[[str, Path], Awaitable[Path]]
_DEFAULT_TYPES = frozenset({"text/html", "application/xhtml+xml", "text/plain", "application/json"})
_REDIRECTS = frozenset({301, 302, 303, 307, 308})


def make_fetcher(
    *, max_bytes: int = 5_000_000, connect_timeout: float = 5.0,
    total_timeout: float = 15.0, max_redirects: int = 5,
    allowed_content_types: frozenset[str] = _DEFAULT_TYPES,
) -> tuple[Fetch, Download]:
    """Create fetch/download callables with shared safety rules.

    Downloads refuse existing paths and publish atomically only after success.
    Both operations enforce the configured byte cap; applications can create
    separate fetchers for document and media limits. Content types are untrusted
    headers, not proof that a file is safe to render or execute.
    """
    if type(max_bytes) is not int or max_bytes <= 0 or type(max_redirects) is not int or max_redirects < 0:
        raise ValueError("byte limit must be positive and redirect limit nonnegative")
    if any(not math.isfinite(value) or value <= 0 for value in (connect_timeout, total_timeout)):
        raise ValueError("timeouts must be finite and positive")
    media_types = frozenset(value.lower().strip() for value in allowed_content_types)
    if not media_types or any("/" not in value for value in media_types):
        raise ValueError("provide at least one valid allowed content type")

    @asynccontextmanager
    async def open_response(value: str) -> AsyncIterator[tuple[httpx.Response, httpx.URL]]:
        url = validate_url(value)
        for hop in range(max_redirects + 1):
            ip = await resolve_public(url.host, url.port or (443 if url.scheme == "https" else 80))
            pinned = url.copy_with(host=ip)
            # New client per hop prevents TLS/Host confusion across pooled origins.
            async with httpx.AsyncClient(
                trust_env=False, follow_redirects=False, http2=False,
                timeout=httpx.Timeout(total_timeout, connect=connect_timeout),
                limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
            ) as client:
                async with client.stream(
                    "GET", pinned,
                    headers={"Host": url.netloc.decode("ascii"), "Accept-Encoding": "identity", "User-Agent": "access-kit/0.1"},
                    extensions={"sni_hostname": url.raw_host.decode("ascii")},
                ) as response:
                    if response.status_code in _REDIRECTS:
                        location = response.headers.get("location")
                        if not location:
                            raise FetchError("redirect has no location")
                        if hop == max_redirects:
                            raise TooManyRedirects("redirect limit exceeded")
                        try:
                            target = validate_url(url.join(location))
                        except (httpx.InvalidURL, ValueError):
                            raise BlockedDestination("invalid redirect URL") from None
                        if url.scheme == "https" and target.scheme != "https":
                            raise BlockedDestination("HTTPS downgrade redirect is not permitted")
                        url = target
                        continue
                    if not 200 <= response.status_code < 300:
                        raise FetchError(f"upstream HTTP status {response.status_code}")
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                    if content_type not in media_types or response.headers.get("content-encoding", "identity").lower() != "identity":
                        raise BadContentType("upstream media type or encoding is not permitted")
                    length = response.headers.get("content-length")
                    if length is not None:
                        if not length.isascii() or not length.isdecimal():
                            raise FetchError("invalid response content length")
                        if int(length) > max_bytes:
                            raise TooLarge("announced body exceeds byte limit")
                    yield response, url
                    return

    async def chunks(response: httpx.Response) -> AsyncIterator[bytes]:
        size = 0
        async for chunk in response.aiter_raw(chunk_size=65_536):
            size += len(chunk)
            if size > max_bytes:
                raise TooLarge("streamed body exceeds byte limit")
            yield chunk

    @asynccontextmanager
    async def operation(value: str) -> AsyncIterator[tuple[httpx.Response, httpx.URL]]:
        try:
            async with asyncio.timeout(total_timeout), open_response(value) as result:
                yield result
        except (TimeoutError, httpx.TimeoutException):
            raise FetchTimeout("fetch deadline exceeded") from None
        except httpx.HTTPError:
            raise FetchError("upstream transport failed") from None

    async def fetch(value: str) -> FetchResult:
        async with operation(value) as (response, url):
            content = bytearray()
            async for chunk in chunks(response):
                content.extend(chunk)
            return FetchResult(str(url), bytes(content), response.headers["content-type"].split(";", 1)[0].strip().lower(), response.status_code)

    async def download(value: str, destination: Path) -> Path:
        target = Path(destination)
        if target.exists():
            raise FileExistsError("download destination already exists")
        temporary: Path | None = None
        try:
            async with operation(value) as (response, _):
                with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".access-kit-", delete=False) as output:
                    temporary = Path(output.name)
                    async for chunk in chunks(response):
                        output.write(chunk)
                # A hard link atomically refuses overwrites, including racing writers.
                os.link(temporary, target)
            return target
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    return fetch, download
