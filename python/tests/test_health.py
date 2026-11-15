"""Exercise readiness through the ASGI interface without external services."""

import asyncio

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from access_kit.health import health_router


async def get_health(checks=None, **kwargs):
    app = FastAPI()
    app.include_router(health_router(checks, **kwargs))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get("/healthz")


async def test_liveness_without_checks():
    response = await get_health()
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {}}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("ready,code,status", [(True, 200, "ok"), (False, 503, "error")])
async def test_check_result(ready, code, status):
    async def check():
        return ready

    response = await get_health({"redis": check})
    assert response.status_code == code
    assert response.json() == {"status": status, "checks": {"redis": status}}


async def test_errors_do_not_expose_secrets():
    async def broken():
        raise RuntimeError("redis://" + "user:secret" + "@internal")

    response = await get_health({"redis": broken})
    assert response.status_code == 503
    assert "secret" not in response.text
    assert response.json()["checks"]["redis"] == "error"


async def test_timeout_cancels_check():
    cancelled = asyncio.Event()

    async def slow():
        try:
            await asyncio.sleep(10)
        finally:
            cancelled.set()
        return True

    response = await get_health({"slow": slow}, timeout=0.01)
    assert response.status_code == 503
    assert cancelled.is_set()


async def test_checks_run_concurrently():
    started = 0
    both_started = asyncio.Event()

    async def check():
        nonlocal started
        started += 1
        if started == 2:
            both_started.set()
        await both_started.wait()
        return True

    response = await get_health({"first": check, "second": check}, timeout=1)
    assert response.status_code == 200


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_invalid_timeout(timeout):
    with pytest.raises(ValueError):
        health_router(timeout=timeout)
