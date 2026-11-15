"""Signed, expiring anonymous cookies without server-side session storage."""

import base64
import hashlib
import hmac
import re
import secrets
import time
from datetime import UTC, datetime

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_ID = re.compile(r"[A-Za-z0-9_-]{43}\Z")
_STATE_KEY = "access_kit_session"
DEFAULT_MAX_AGE = 365 * 24 * 60 * 60


def _check_secret(secret: str) -> None:
    if len(secret.encode()) < 32:
        raise ValueError("session secret must contain at least 32 bytes")


def _signature(payload: str, secret: str) -> str:
    return base64.urlsafe_b64encode(hmac.new(secret.encode(), payload.encode("ascii"), hashlib.sha256).digest()).decode().rstrip("=")


def sign_session(session_id: str, secret: str, *, issued_at: int | None = None) -> str:
    """Sign an anonymous ID. Cookie values contain no user data."""
    _check_secret(secret)
    if _ID.fullmatch(session_id) is None:
        raise ValueError("invalid session ID")
    issued = int(time.time()) if issued_at is None else issued_at
    if issued < 0:
        raise ValueError("invalid session timestamp")
    payload = f"v1.{issued}.{session_id}"
    return f"{payload}.{_signature(payload, secret)}"


def verify_session(cookie: str, secret: str, *, max_age: int = DEFAULT_MAX_AGE, now: int | None = None) -> str | None:
    """Return an authentic, unexpired ID; malformed or tampered cookies return None."""
    _check_secret(secret)
    if max_age <= 0:
        raise ValueError("max_age must be positive")
    if len(cookie) > 160 or not cookie.isascii():
        return None
    parts = cookie.split(".")
    if len(parts) != 4:
        return None
    version, timestamp, session_id, signature = parts
    if version != "v1" or not timestamp.isdecimal() or _ID.fullmatch(session_id) is None:
        return None
    if not hmac.compare_digest(_signature(".".join(parts[:3]), secret), signature):
        return None
    current = int(time.time()) if now is None else now
    age = current - int(timestamp)
    return session_id if 0 <= age < max_age else None


def _state(request: Request) -> dict[str, object]:
    state = request.scope.get("state", {}).get(_STATE_KEY)
    if not isinstance(state, dict):
        raise RuntimeError("install session_middleware before using session dependencies")
    return state


def get_session_id(request: Request) -> str:
    """FastAPI dependency: read the anonymous ID created by session middleware."""
    return str(_state(request)["id"])


def rotate_session(request: Request) -> str:
    """Replace the current ID and set a fresh cookie before response headers.

    Stateless rotation does NOT revoke previously signed cookies. Applications
    needing revocation must delete/reject the old ID in their own data store.
    """
    state = _state(request)
    if state["started"]:
        raise RuntimeError("cannot rotate a session after response headers")
    session_id = secrets.token_urlsafe(32)
    state.update(id=session_id, changed=True)
    return session_id


def session_middleware(app: ASGIApp, *, secret: str, max_age: int = DEFAULT_MAX_AGE, secure: bool = True) -> ASGIApp:
    """Create an ASGI wrapper with HttpOnly, SameSite=Lax, Path=/ cookies.

    HTTPS is required by default. Pass secure=False explicitly for local HTTP.
    Cookies are written only for new, invalid, expired, or rotated sessions.
    """
    _check_secret(secret)
    if max_age <= 0:
        raise ValueError("max_age must be positive")

    async def middleware(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await app(scope, receive, send)
            return
        request = Request(scope)
        existing = request.cookies.get("ak_sid", "")
        session_id = verify_session(existing, secret, max_age=max_age)
        state: dict[str, object] = {"id": session_id or secrets.token_urlsafe(32), "changed": session_id is None, "started": False}
        scope.setdefault("state", {})[_STATE_KEY] = state

        async def send_with_cookie(message: Message) -> None:
            if message["type"] == "http.response.start":
                state["started"] = True
                if state["changed"]:
                    issued_at = int(time.time())
                    response = Response()
                    response.set_cookie(
                        "ak_sid",
                        sign_session(str(state["id"]), secret, issued_at=issued_at),
                        max_age=max_age,
                        expires=datetime.fromtimestamp(issued_at + max_age, UTC),
                        httponly=True,
                        secure=secure,
                        samesite="lax",
                        path="/",
                    )
                    message = dict(message)
                    message["headers"] = list(message.get("headers", [])) + [(key, value) for key, value in response.raw_headers if key == b"set-cookie"]
            await send(message)

        await app(scope, receive, send_with_cookie)

    return middleware
