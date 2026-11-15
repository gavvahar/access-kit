"""Shared ASGI clients and streaming HTTP fixtures."""

import httpx
import pytest
import pytest_asyncio

pytest_plugins = ["access_kit.testing.fixtures"]


@pytest_asyncio.fixture
async def client_for():
    clients = []

    def create(app):
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="https://test")
        clients.append(client)
        return client

    yield create
    for client in clients:
        await client.aclose()


class Chunks(httpx.AsyncByteStream):
    def __init__(self, parts):
        self.parts = parts
        self.closed = False

    async def __aiter__(self):
        for part in self.parts:
            if isinstance(part, Exception):
                raise part
            yield part

    async def aclose(self):
        self.closed = True


def stream_response(body=b"ok", *, status=200, headers=None, parts=None):
    return httpx.Response(status, headers=headers if headers is not None else {"content-type": "text/plain"}, stream=Chunks(parts if parts is not None else [body]))


@pytest.fixture
def patch_fetch_http(monkeypatch):
    from access_kit.safe_fetch import fetcher

    original = httpx.AsyncClient
    seen = []
    responses = []
    configurations = []

    async def handler(request):
        seen.append(request)
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if callable(response):
            return await response(request)
        return response

    def create(**kwargs):
        configurations.append(kwargs)
        return original(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(fetcher.httpx, "AsyncClient", create)
    return responses, seen, configurations


@pytest.fixture
def public_dns(monkeypatch):
    import asyncio
    import socket

    seen = []
    addresses = ["93.184.216.34"]

    async def resolve(host, port, **kwargs):
        seen.append((host, port))
        return [(socket.AF_INET6 if ":" in address else socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, port)) for address in addresses]

    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", resolve)
    return addresses, seen
