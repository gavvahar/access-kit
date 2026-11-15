"""Cookie authenticity, expiry, isolation, rotation and streaming behavior."""

import secrets

import pytest
from fastapi import Depends, FastAPI, Request
from starlette.responses import StreamingResponse

from access_kit.session import get_session_id, rotate_session, session_middleware, sign_session, verify_session

SECRET = "session-signing-key-" + "x" * 32
SID = secrets.token_urlsafe(32)


def app_with_sessions(**options):
    app = FastAPI()

    @app.get("/")
    async def read(session_id=Depends(get_session_id)):
        return {"id": session_id}

    @app.post("/rotate")
    async def rotate(request: Request):
        return {"id": rotate_session(request)}

    return session_middleware(app, secret=SECRET, **options)


def test_signed_token_and_expiry_boundaries():
    token = sign_session(SID, SECRET, issued_at=100)
    assert verify_session(token, SECRET, now=100, max_age=10) == SID
    assert verify_session(token, SECRET, now=109, max_age=10) == SID
    assert verify_session(token, SECRET, now=110, max_age=10) is None
    assert verify_session(token, SECRET, now=99) is None
    assert verify_session(token, "other" * 10, now=100) is None


@pytest.mark.parametrize("cookie", ["", "bad", "é", "a" * 161, "v2.1." + SID + ".sig", "v1.nope." + SID + ".sig", "v1.0.invalid.sig", "v1.0." + SID + ".sig"])
def test_malformed_tokens_fail_closed(cookie):
    assert verify_session(cookie, SECRET) is None


@pytest.mark.parametrize("change", [0, 5, 20, -1])
def test_cookie_tampering(change):
    token = sign_session(SID, SECRET)
    index = change % len(token)
    token = token[:index] + ("A" if token[index] != "A" else "B") + token[index + 1 :]
    assert verify_session(token, SECRET) is None


def test_invalid_configuration():
    for action in (
        lambda: sign_session(SID, "short"),
        lambda: verify_session("", SECRET, max_age=0),
        lambda: sign_session("invalid", SECRET),
        lambda: sign_session(SID, SECRET, issued_at=-1),
        lambda: session_middleware(None, secret=SECRET, max_age=0),
        lambda: session_middleware(None, secret="short"),
    ):
        with pytest.raises(ValueError):
            action()


async def test_secure_cookie_attributes_and_reuse(client_for):
    client = client_for(app_with_sessions())
    first = await client.get("/")
    cookie = first.headers["set-cookie"]
    assert all(value in cookie for value in ("HttpOnly", "Secure", "SameSite=lax", "Path=/", "Max-Age=31536000", "expires="))
    second = await client.get("/")
    assert second.json() == first.json()
    assert "set-cookie" not in second.headers


async def test_rotation_and_new_clients_are_isolated(client_for):
    app = app_with_sessions()
    client = client_for(app)
    original = (await client.get("/")).json()["id"]
    other = (await client_for(app).get("/")).json()["id"]
    assert other != original
    rotated = await client.post("/rotate")
    assert rotated.json()["id"] != original
    assert (await client.get("/")).json() == rotated.json()
    assert "set-cookie" in rotated.headers


async def test_tampered_cookie_replaced_and_local_http_opt_in(client_for):
    client = client_for(app_with_sessions(secure=False))
    result = await client.get("/", headers={"Cookie": "ak_sid=tampered"})
    assert "Secure" not in result.headers["set-cookie"]
    assert result.json()["id"] != "tampered"


def test_dependency_requires_middleware():
    request = Request({"type": "http", "headers": []})
    with pytest.raises(RuntimeError):
        get_session_id(request)


async def test_stream_cannot_rotate_after_headers(client_for):
    app = FastAPI()
    errors = []

    @app.get("/")
    async def stream(request: Request):
        async def content():
            try:
                rotate_session(request)
            except RuntimeError as error:
                errors.append(str(error))
            yield b"done"

        return StreamingResponse(content())

    result = await client_for(session_middleware(app, secret=SECRET)).get("/")
    assert result.content == b"done"
    assert errors == ["cannot rotate a session after response headers"]


async def test_session_passthrough_for_websockets():
    scopes = []

    async def app(scope, receive, send):
        scopes.append(scope)

    await session_middleware(app, secret=SECRET)({"type": "websocket"}, None, None)
    assert scopes == [{"type": "websocket"}]
