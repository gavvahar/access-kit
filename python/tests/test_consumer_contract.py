"""A consuming FastAPI app can compose the Phase B modules without services."""

from typing import TypedDict
from decimal import Decimal
import pytest

from fastapi import Body, Depends, FastAPI, Request

from access_kit.health import health_router
from access_kit.logging import get_request_id, request_id_middleware
from access_kit.privacy import client_ip, hash_ip
from access_kit.safe_fetch.fetcher import make_fetcher
from access_kit.session import get_session_id, session_middleware
from access_kit.testing.fakes import fake_llm
from conftest import stream_response

Summary = TypedDict("Summary", {"summary": str})


async def test_application_pipeline(client_for, kit_settings, public_dns, patch_fetch_http):
    patch_fetch_http[0].append(stream_response(b"A short source document."))
    fetch, _ = make_fetcher()
    llm, calls = fake_llm(['{"summary":"A short summary."}'])
    api = FastAPI()
    api.include_router(health_router())

    @api.post("/document")
    async def process(request: Request, url: str = Body(embed=True), session_id: str = Depends(get_session_id)):
        source = await fetch(url)
        result, tokens = await llm["complete_json"]("Summarize the document.", source.content.decode(), Summary)
        peer = client_ip(request)
        return {
            "summary": result["summary"],
            "usage": tokens,
            "session": session_id,
            "request_id": get_request_id(),
            "ip_hash": hash_ip(peer, kit_settings.ip_hash_salt.get_secret_value()) if peer else None,
        }

    client = client_for(request_id_middleware(session_middleware(api, secret=kit_settings.session_secret.get_secret_value())))
    result = await client.post("/document", json={"url": "https://example.com/document"})
    assert result.status_code == 200
    data = result.json()
    assert data["summary"] == "A short summary."
    assert data["usage"]["complete"] is True
    assert data["request_id"] == result.headers["x-request-id"]
    assert len(data["ip_hash"]) == 64
    assert "HttpOnly" in result.headers["set-cookie"]
    assert "source document" in calls[0].user
    assert (await client.get("/healthz")).status_code == 200


@pytest.mark.parametrize("unit,cost", [("tokens", Decimal(5)), ("minutes", Decimal("0.5"))])
async def test_protected_job_pipeline_enforces_shared_cap_before_provider_dispatch(fake_redis, client_for, kit_settings, unit, cost):
    """Compose the public modules as a consumer; changing owners cannot reset a cap."""
    import asyncio
    from fastapi import HTTPException
    from access_kit.budget import BudgetExceeded, make_budget
    from access_kit.jobs import job_response, make_jobs
    from access_kit.ratelimit import make_limiter, rate_limit_dependency
    from access_kit.turnstile import require_turnstile

    budget = make_budget(fake_redis, name=f"consumer-{unit}", limit=cost * 4, unit=unit)
    jobs = make_jobs(fake_redis, name=f"consumer-{unit}-jobs")
    check = make_limiter(fake_redis, name=f"consumer-{unit}-rate", limit=1000)
    provider, calls = fake_llm(['{"summary":"Ready"}'] * 4, json_retries=0)

    async def verify(token):
        return token == "test-challenge"

    async def identify(request):
        return get_session_id(request)

    api = FastAPI()
    api.include_router(health_router())

    @api.post("/work", dependencies=[Depends(require_turnstile(verify)), Depends(rate_limit_dependency(check, identify))])
    async def work(request: Request):
        try:
            receipt = await budget["reserve"](cost)
        except BudgetExceeded:
            raise HTTPException(503, "Daily capacity reached") from None
        owner = get_session_id(request)
        job = await jobs["create"](owner, total=1)
        await provider["complete_json"]("Return the structured result.", "Test input", Summary)
        await budget["commit"](receipt, cost)
        await jobs["update"](owner, job["id"], completed=1, label="Ready", status="complete")
        return {"job_id": job["id"]}

    @api.get("/progress/{identity}")
    async def progress(request: Request, identity: str):
        return await job_response(request, jobs, owner=get_session_id(request), job_id=identity)

    app = session_middleware(api, secret=kit_settings.session_secret.get_secret_value())
    client = client_for(app)
    await client.get("/healthz")
    assert (await client.post("/work")).status_code == 403
    assert not calls
    results = await asyncio.gather(*(client.post("/work", headers={"X-Turnstile-Token": "test-challenge"}) for _ in range(100)))
    accepted = [response for response in results if response.status_code == 200]
    assert len(accepted) == len(calls) == 4
    assert all(response.status_code in (200, 503) for response in results)
    assert (await budget["snapshot"]())["used"] == cost * 4
    identity = accepted[0].json()["job_id"]
    response = await client.get(f"/progress/{identity}")
    assert response.status_code == 200 and "event: complete" in response.text
    outsider = client_for(app)
    assert (await outsider.get(f"/progress/{identity}")).status_code == 404
    assert (await outsider.post("/work", headers={"X-Turnstile-Token": "test-challenge"})).status_code == 503
    assert len(calls) == 4
