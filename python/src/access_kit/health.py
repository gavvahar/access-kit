"""A bounded readiness endpoint with application-owned async checks."""

import asyncio, math
from collections.abc import Awaitable, Callable, Mapping

from fastapi import APIRouter
from fastapi.responses import JSONResponse

HealthCheck = Callable[[], Awaitable[bool]]


def health_router(checks: Mapping[str, HealthCheck] | None = None, *, timeout: float = 2.0) -> APIRouter:
    """Create GET /healthz; async checks return True when ready.

    Checks run concurrently with a per-check timeout. Exceptions and failures
    return HTTP 503 without exposing exception messages or connection details.
    No checks means this is a basic liveness endpoint. A timeout requires checks
    to cooperate with cancellation; blocking I/O belongs in a worker thread.
    """
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and positive")
    registered = dict(checks or {})
    router = APIRouter()

    async def run_check(name: str, check: HealthCheck) -> tuple[str, str]:
        try:
            ready = await asyncio.wait_for(check(), timeout=timeout)
            return name, "ok" if ready is True else "error"
        except Exception:
            return name, "error"

    @router.get("/healthz", responses={503: {"description": "A readiness check failed"}})
    async def healthz() -> JSONResponse:
        results = dict(await asyncio.gather(*(run_check(name, check) for name, check in registered.items())))
        ready = all(status == "ok" for status in results.values())
        return JSONResponse(
            {"status": "ok" if ready else "error", "checks": results},
            status_code=200 if ready else 503,
            headers={"Cache-Control": "no-store"},
        )

    return router
