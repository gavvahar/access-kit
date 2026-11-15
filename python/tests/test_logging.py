"""Redaction, correlation and async isolation through ASGI."""

import asyncio
import io
import json
import logging

import pytest
from fastapi import FastAPI
from starlette.responses import JSONResponse

from access_kit.logging import get_request_id, request_id_middleware, scrub_logs, setup_logging
from access_kit.settings import AccessKitSettings


@pytest.fixture
def log_output():
    root = logging.getLogger()
    previous_handlers, previous_level = list(root.handlers), root.level
    output = io.StringIO()
    settings = AccessKitSettings(app_name="Example", public_base_url="https://example.com", redis_url="redis://localhost", session_secret="s" * 32, ip_hash_salt="h" * 32)
    setup_logging(settings, stream=output)
    yield output
    root.handlers, root.level = previous_handlers, previous_level


def test_only_allowlisted_fields_survive():
    safe = scrub_logs(
        {
            "event": "request_done",
            "status_code": 200,
            "duration_ms": 1.5,
            "method": "POST",
            "provider": "ollama",
            "request_id": "a" * 32,
            "secret-key": "password",
            "nested": {"transcript": "pasted text"},
            "ip": "127.0.0.1",
        }
    )
    assert safe == {"event": "request_done", "status_code": 200, "duration_ms": 1.5, "method": "POST", "provider": "ollama", "request_id": "a" * 32}


@pytest.mark.parametrize("event", [None, 4, "raw user text", "127.0.0.1", "https://" + "user:password" + "@private", "a" * 65])
def test_freeform_event_is_redacted(event):
    assert scrub_logs({"event": event}) == {"event": "redacted"}


def test_untrusted_values_are_dropped():
    assert scrub_logs({"event": "safe", "status_code": True, "duration_ms": float("inf"), "method": "secret", "provider": 7, "request_id": "injected\nvalue"}) == {"event": "safe"}


def test_log_arguments_and_exceptions_are_not_formatted(log_output):
    logger = logging.getLogger("third.party")
    logger.info("user said %s", "secret-prompt")
    try:
        raise ValueError("private-token")
    except ValueError:
        logger.exception("request_failed", extra={"body": "transcript", "status_code": 500}, stack_info=True)
    text = log_output.getvalue()
    assert not any(value in text for value in ("private-token", "secret-prompt", "transcript", "Traceback"))
    events = [json.loads(line) for line in text.splitlines()]
    assert events[0]["event"] == "redacted"
    assert events[1]["event"] == "request_failed"
    assert events[1]["status_code"] == 500


async def test_request_ids_are_isolated_and_untrusted_headers_ignored(client_for, log_output):
    app = FastAPI()

    @app.get("/")
    async def endpoint():
        first = get_request_id()
        await asyncio.sleep(0)
        assert get_request_id() == first
        logging.info("request_done")
        return {"id": first}

    client = client_for(request_id_middleware(app))
    results = await asyncio.gather(*(client.get("/", headers={"X-Request-ID": "attacker-controlled"}) for _ in range(5)))
    ids = {result.headers["x-request-id"] for result in results}
    assert len(ids) == 5
    assert all(result.json()["id"] == result.headers["x-request-id"] for result in results)
    assert get_request_id() is None
    assert "attacker-controlled" not in log_output.getvalue()


async def test_error_response_has_id_and_context_resets(client_for):
    app = FastAPI()

    @app.get("/")
    async def explode():
        raise RuntimeError("failure")

    result = await client_for(request_id_middleware(app)).get("/")
    assert result.status_code == 500
    assert len(result.headers["x-request-id"]) == 32
    assert get_request_id() is None


async def test_non_http_scope_passes_through():
    seen = []

    async def app(scope, receive, send):
        seen.append(scope["type"])

    await request_id_middleware(app)({"type": "lifespan"}, None, None)
    assert seen == ["lifespan"]


async def test_existing_response_id_is_replaced(client_for):
    async def app(scope, receive, send):
        await JSONResponse({}, headers={"X-Request-ID": "old"})(scope, receive, send)

    result = await client_for(request_id_middleware(app)).get("/")
    assert len(result.headers.get_list("x-request-id")) == 1
    assert result.headers["x-request-id"] != "old"
