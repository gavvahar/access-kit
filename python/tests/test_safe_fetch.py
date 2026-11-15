"""Adversarial URL, DNS, transport, redirect and streaming regression tests."""

import asyncio
import socket

import httpx
import pytest
from httpcore._backends.auto import AutoBackend

from access_kit.safe_fetch.errors import BadContentType, BlockedDestination, FetchError, FetchTimeout, TooLarge, TooManyRedirects
from access_kit.safe_fetch.fetcher import make_fetcher
from access_kit.safe_fetch.ipcheck import is_public_ip, resolve_public, validate_url
from access_kit.testing.ssrf_cases import SSRF_CASES
from conftest import stream_response


@pytest.mark.parametrize("url", SSRF_CASES)
async def test_blocked_cases_never_reach_http(url, patch_fetch_http):
    _, seen, _ = patch_fetch_http
    fetch, _ = make_fetcher()
    with pytest.raises(BlockedDestination):
        await fetch(url)
    assert seen == []


@pytest.mark.parametrize(
    "value,allowed",
    [("8.8.8.8", True), ("2606:4700:4700::1111", True), ("invalid", False), ("::ffff:8.8.8.8", False), ("fe80::1%eth0", False), ("224.0.0.1", False), ("2002:808:808::1", False)],
)
def test_public_ip_rules(value, allowed):
    assert is_public_ip(value) is allowed


async def test_mixed_dns_answers_fail_closed(public_dns):
    addresses, _ = public_dns
    addresses.append("127.0.0.1")
    with pytest.raises(BlockedDestination):
        await resolve_public("example.com", 443)
    addresses.clear()
    with pytest.raises(BlockedDestination):
        await resolve_public("example.com", 443)


async def test_dns_errors_are_sanitized(monkeypatch):
    async def fail(*args, **kwargs):
        raise socket.gaierror("secret hostname")

    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", fail)
    with pytest.raises(BlockedDestination, match="could not be resolved") as error:
        await resolve_public("example.com", 80)
    assert "secret" not in str(error.value)


@pytest.mark.parametrize("value", ["http://[bad", "http://example.com:bad", "http://example.com/" + "a" * 8200])
def test_malformed_url(value):
    with pytest.raises(BlockedDestination):
        validate_url(value)


async def test_fetch_pins_ip_host_sni_and_disables_ambient_behavior(public_dns, patch_fetch_http):
    responses, seen, configs = patch_fetch_http
    responses.append(stream_response(b"hello", headers={"content-type": "Text/Plain; charset=utf-8", "content-length": "5"}))
    fetch, _ = make_fetcher()
    result = await fetch("https://example.com/document#fragment")
    assert result.content == b"hello"
    assert result.url == "https://example.com/document"
    assert result.content_type == "text/plain"
    assert seen[0].url.host == "93.184.216.34"
    assert seen[0].headers["host"] == "example.com"
    assert seen[0].extensions["sni_hostname"] == "example.com"
    assert seen[0].headers["accept-encoding"] == "identity"
    assert configs[0]["trust_env"] is False
    assert configs[0]["follow_redirects"] is False
    assert configs[0]["http2"] is False
    assert public_dns[1] == [("example.com", 443)]


async def test_redirect_revalidates_and_closes_previous_hop(public_dns, patch_fetch_http):
    responses, seen, configs = patch_fetch_http
    redirect = stream_response(status=302, headers={"location": "/final"})
    responses.extend([redirect, stream_response(b"final")])
    fetch, _ = make_fetcher()
    result = await fetch("https://example.com/start")
    assert result.url == "https://example.com/final"
    assert len(seen) == len(configs) == len(public_dns[1]) == 2
    assert redirect.is_closed


@pytest.mark.parametrize(
    "target", ["http://127.0.0.1", "https://127.0.0.1", "https://" + "user:password" + "@example.com", "file:///etc/passwd", "http://example.com", "https://example.com:22"]
)
async def test_unsafe_redirect_is_blocked(target, public_dns, patch_fetch_http):
    responses, seen, _ = patch_fetch_http
    responses.append(stream_response(status=302, headers={"location": target}))
    fetch, _ = make_fetcher()
    with pytest.raises(BlockedDestination):
        await fetch("https://example.com")
    assert len(seen) == 1


async def test_redirect_to_hostname_with_private_dns(public_dns, patch_fetch_http):
    responses, seen, _ = patch_fetch_http

    async def redirect(request):
        public_dns[0][:] = ["169.254.169.254"]
        return stream_response(status=307, headers={"location": "https://other.example.com"})

    responses.append(redirect)
    with pytest.raises(BlockedDestination):
        await make_fetcher()[0]("https://example.com")
    assert len(seen) == 1


@pytest.mark.parametrize(
    "header,error",
    [
        ({}, FetchError),
        ({"location": "/next"}, TooManyRedirects),
        ({"location": "http://[invalid"}, BlockedDestination),
        ({"location": "http://example.com:invalid"}, FetchError),
    ],
)
async def test_redirect_errors(header, error, public_dns, patch_fetch_http):
    patch_fetch_http[0].append(stream_response(status=301, headers=header))
    # Invalid URL must be evaluated before the redirect-limit branch.
    fetch, _ = make_fetcher(max_redirects=1 if error is BlockedDestination else 0)
    with pytest.raises(error):
        await fetch("https://example.com")


@pytest.mark.parametrize(
    "headers,error",
    [
        ({"content-type": "image/svg+xml"}, BadContentType),
        ({}, BadContentType),
        ({"content-type": "text/plain", "content-encoding": "gzip"}, BadContentType),
        ({"content-type": "text/plain", "content-length": "9999999999"}, TooLarge),
        ({"content-type": "text/plain", "content-length": "9" * 5000}, TooLarge),
        ({"content-type": "text/plain", "content-length": "-1"}, FetchError),
        ({"content-type": "text/plain", "content-length": "nonsense"}, FetchError),
    ],
)
async def test_headers_rejected_before_reading_body(headers, error, public_dns, patch_fetch_http):
    response = stream_response(headers=headers, parts=[AssertionError("body must not be read")])
    patch_fetch_http[0].append(response)
    with pytest.raises(error):
        await make_fetcher()[0]("https://example.com")
    assert response.is_closed


async def test_stream_size_limit_applies_without_content_length(public_dns, patch_fetch_http):
    patch_fetch_http[0].append(stream_response(parts=[b"123", b"456"]))
    with pytest.raises(TooLarge):
        await make_fetcher(max_bytes=5)[0]("https://example.com")


async def test_http_status_and_transport_errors(public_dns, patch_fetch_http):
    responses, _, _ = patch_fetch_http
    responses.extend([stream_response(status=404), httpx.ConnectError("secret upstream")])
    fetch, _ = make_fetcher()
    for _ in range(2):
        with pytest.raises(FetchError) as error:
            await fetch("https://example.com")
        assert "secret" not in str(error.value)


async def test_total_timeout_includes_dns(monkeypatch):
    async def slow(*args, **kwargs):
        await asyncio.sleep(10)

    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", slow)
    with pytest.raises(FetchTimeout):
        await make_fetcher(total_timeout=0.01)[0]("https://example.com")


async def test_http_timeout_translated(public_dns, patch_fetch_http):
    patch_fetch_http[0].append(httpx.ReadTimeout("private endpoint"))
    with pytest.raises(FetchTimeout):
        await make_fetcher()[0]("https://example.com")


@pytest.mark.parametrize(
    "options",
    [
        {"max_bytes": 0},
        {"max_bytes": True},
        {"max_redirects": -1},
        {"max_redirects": False},
        {"total_timeout": float("nan")},
        {"connect_timeout": 0},
        {"allowed_content_types": frozenset()},
        {"allowed_content_types": frozenset({"bad"})},
    ],
)
def test_invalid_fetcher_configuration(options):
    with pytest.raises(ValueError):
        make_fetcher(**options)


async def test_download_atomic_success_and_refusal_to_overwrite(tmp_path, public_dns, patch_fetch_http):
    destination = tmp_path / "document.txt"
    patch_fetch_http[0].append(stream_response(b"downloaded"))
    _, download = make_fetcher()
    assert await download("https://example.com", destination) == destination
    assert destination.read_bytes() == b"downloaded"
    with pytest.raises(FileExistsError):
        await download("https://example.com", destination)
    assert list(tmp_path.iterdir()) == [destination]


async def test_download_cleans_up_partial_file_on_failure(tmp_path, public_dns, patch_fetch_http):
    destination = tmp_path / "failed"
    patch_fetch_http[0].append(stream_response(parts=[b"x" * 65_536, httpx.ReadError("connection lost")]))
    _, download = make_fetcher()
    with pytest.raises(FetchError):
        await download("https://example.com", destination)
    assert list(tmp_path.iterdir()) == []


async def test_cancelled_download_removes_temporary_file(tmp_path, public_dns, patch_fetch_http):
    started = asyncio.Event()

    class BlockingStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"x" * 65_536
            started.set()
            await asyncio.sleep(10)

    patch_fetch_http[0].append(httpx.Response(200, headers={"content-type": "text/plain"}, stream=BlockingStream()))
    _, download = make_fetcher()
    task = asyncio.create_task(download("https://example.com", tmp_path / "cancelled"))
    await asyncio.wait_for(started.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert list(tmp_path.iterdir()) == []


async def test_actual_httpcore_socket_target_and_tls_name_are_pinned(public_dns, monkeypatch):
    """Exercise real HTTPX/httpcore serialization, not only a mock HTTP handler."""
    calls = []
    written = bytearray()

    class NetworkStream:
        async def read(self, max_bytes, timeout=None):
            return b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nok"

        async def write(self, buffer, timeout=None):
            written.extend(buffer)

        async def start_tls(self, ssl_context, server_hostname=None, timeout=None):
            calls.append(("tls", server_hostname, ssl_context.check_hostname))
            return self

        def get_extra_info(self, name):
            return None

        async def aclose(self):
            calls.append(("closed",))

    async def connect(self, host, port, **kwargs):
        calls.append(("connect", host, port))
        # DNS rebinds after validation. The socket must still use the first IP.
        public_dns[0][:] = ["127.0.0.1"]
        return NetworkStream()

    monkeypatch.setattr(AutoBackend, "connect_tcp", connect)
    result = await make_fetcher()[0]("https://example.com/data")
    assert result.content == b"ok"
    assert calls[:2] == [("connect", "93.184.216.34", 443), ("tls", "example.com", True)]
    assert b"Host: example.com\r\n" in written
    assert len(public_dns[1]) == 1
    assert ("closed",) in calls


async def test_redirect_does_not_carry_upstream_cookies(public_dns, patch_fetch_http):
    responses, seen, _ = patch_fetch_http
    responses.extend(
        [
            stream_response(status=302, headers={"location": "https://other.example.com/final", "set-cookie": "credential=private; Domain=.example.com; Path=/"}),
            stream_response(),
        ]
    )
    await make_fetcher()[0]("https://example.com/start")
    assert "cookie" not in seen[1].headers
    assert seen[1].headers["host"] == "other.example.com"


async def test_download_refuses_racing_writer(tmp_path, public_dns, patch_fetch_http, monkeypatch):
    import os

    patch_fetch_http[0].append(stream_response(b"download"))
    destination = tmp_path / "raced"
    link = os.link

    def race(source, target):
        destination.write_bytes(b"other writer")
        link(source, target)

    monkeypatch.setattr(os, "link", race)
    with pytest.raises(FileExistsError):
        await make_fetcher()[1]("https://example.com", destination)
    assert destination.read_bytes() == b"other writer"
    assert list(tmp_path.iterdir()) == [destination]


@pytest.mark.parametrize("url,host", [("http://8.8.8.8/path", "8.8.8.8"), ("https://[2606:4700:4700::1111]", "[2606:4700:4700::1111]"), ("https://bücher.de", "xn--bcher-kva.de")])
async def test_literal_and_idna_hosts(url, host, public_dns, patch_fetch_http):
    patch_fetch_http[0].append(stream_response())
    assert (await make_fetcher()[0](url)).content == b"ok"
    assert patch_fetch_http[1][0].headers["host"] == host
