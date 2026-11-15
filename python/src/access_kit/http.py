"""Bounded ASGI request bodies for applications accepting documents or captions."""

import asyncio
import math

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


def body_limit(app: ASGIApp, *, max_bytes: int = 1_000_000, read_timeout: float = 15) -> ASGIApp:
    """Reject oversized/ambiguous bodies before framework JSON parsing.

    Buffer at most max_bytes before calling the application. This is intended
    for bounded JSON/forms, not streaming upload endpoints or WebSockets.
    """
    if type(max_bytes) is not int or max_bytes < 1 or not math.isfinite(read_timeout) or not 0 < read_timeout <= 120:
        raise ValueError("provide a positive byte cap and timeout up to 120 seconds")

    async def bounded(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await app(scope, receive, send)
            return
        lengths = [value for name, value in scope["headers"] if name.lower() == b"content-length"]
        declared = None
        if lengths:
            if len(lengths) != 1 or len(lengths[0]) > 20 or not lengths[0].isdigit():
                await JSONResponse({"detail": "Invalid content length"}, status_code=400)(scope, receive, send)
                return
            declared = int(lengths[0])
            if declared > max_bytes:
                await JSONResponse({"detail": "Request body too large"}, status_code=413)(scope, receive, send)
                return
        body = bytearray()
        try:
            async with asyncio.timeout(read_timeout):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > max_bytes:
                        await JSONResponse({"detail": "Request body too large"}, status_code=413)(scope, receive, send)
                        return
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            await JSONResponse({"detail": "Request body timed out"}, status_code=408)(scope, receive, send)
            return
        if declared is not None and declared != len(body):
            await JSONResponse({"detail": "Body length does not match"}, status_code=400)(scope, receive, send)
            return
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await app(scope, replay, send)

    return bounded
