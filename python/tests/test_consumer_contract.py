"""A consuming FastAPI app can compose the Phase B modules without services."""

from typing import TypedDict

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
