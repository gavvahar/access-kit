"""Fail-closed Cloudflare Turnstile validation with hostname/action binding."""

import json
import math
import re
from collections.abc import Awaitable, Callable

import httpx
from fastapi import HTTPException, Request

from access_kit.errors import ServiceUnavailable
from access_kit._http import request_bytes
from access_kit.privacy import canonical_ip

_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
_HOST = re.compile(r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")


def make_turnstile_verifier(
    *, secret: str, hostname: str, action: str | None = None, timeout: float = 5, client: httpx.AsyncClient | None = None
) -> Callable[..., Awaitable[bool]]:
    """Validate single-use tokens on Cloudflare; never accept client-side claims.

    Test keys still require explicit test hostname/action expectations. No test
    bypass exists. The optional remote IP must come from a verified socket peer.
    """
    try:
        expected = hostname.rstrip(".").encode("idna").decode().lower()
    except UnicodeError:
        raise ValueError("invalid Turnstile hostname") from None
    if not secret or not _HOST.fullmatch(expected) or not math.isfinite(timeout) or timeout <= 0 or (action is not None and not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", action)):
        raise ValueError("configure a secret, hostname, positive timeout, and valid action")

    async def verify(token: str, *, remote_ip: str | None = None) -> bool:
        if not isinstance(token, str) or not token.strip() or len(token) > 2048:
            return False
        payload = {"secret": secret, "response": token}
        if remote_ip is not None:
            payload["remoteip"] = canonical_ip(remote_ip)
        raw = await request_bytes(_VERIFY_URL, client=client, timeout=timeout, payload=payload, max_bytes=16384)
        try:
            result = json.loads(raw)
        except (ValueError, RecursionError):
            raise ServiceUnavailable("invalid Turnstile validation response") from None
        return bool(isinstance(result, dict) and result.get("success") is True and result.get("hostname") == expected and (action is None or result.get("action") == action))

    return verify


def require_turnstile(verify: Callable[..., Awaitable[bool]], *, token_header: str = "x-turnstile-token") -> Callable[[Request], Awaitable[None]]:
    """FastAPI dependency. Apps put the widget's token in the configured header."""

    async def require(request: Request) -> None:
        tokens = request.headers.getlist(token_header)
        if len(tokens) != 1:
            raise HTTPException(403, "Bot verification required")
        try:
            accepted = await verify(tokens[0])
        except ServiceUnavailable:
            raise HTTPException(503, "Bot verification temporarily unavailable") from None
        if not accepted:
            raise HTTPException(403, "Bot verification failed")

    return require
