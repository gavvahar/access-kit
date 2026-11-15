"""Structured stdlib logs with conservative redaction and ASGI request IDs."""

import json
import logging
import math
import re
from collections.abc import Mapping
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import TextIO
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from access_kit.settings import AccessKitSettings

_request_id: ContextVar[str | None] = ContextVar("access_kit_request_id", default=None)
_EVENT = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}\Z")
_REQUEST_ID = re.compile(r"[0-9a-f]{32}\Z")
_NUMBERS = frozenset({"status_code", "duration_ms", "input_tokens", "output_tokens", "total_tokens", "attempt"})
_ENUMS = {"method": {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}, "provider": {"anthropic", "ollama", "omniroute", "openai_compat", "fake"}}


def get_request_id() -> str | None:
    """Return the ID bound to the current async request, if any."""
    return _request_id.get()


def scrub_logs(event: Mapping[str, object]) -> dict[str, object]:
    """Allow only fixed event names and a small set of safe scalar fields.

    Bodies, transcripts, URLs, IPs, headers, secrets, arbitrary nested metadata,
    exception text and free-form messages never pass through. Event names must
    be developer-defined constants; never interpolate user input into them.
    """
    message = event.get("event")
    result: dict[str, object] = {"event": message if isinstance(message, str) and _EVENT.fullmatch(message) else "redacted"}
    for key in _NUMBERS:
        value = event.get(key)
        if type(value) in (int, float) and math.isfinite(value):
            result[key] = value
    for key, allowed in _ENUMS.items():
        value = event.get(key)
        if isinstance(value, str) and value in allowed:
            result[key] = value
    request_id = event.get("request_id")
    if isinstance(request_id, str) and _REQUEST_ID.fullmatch(request_id):
        result["request_id"] = request_id
    return result


def setup_logging(settings: AccessKitSettings, *, level: int = logging.INFO, stream: TextIO | None = None) -> None:
    """Replace root handlers with one scrubbed JSON handler. Call at startup."""
    handler = logging.StreamHandler(stream)

    def scrub_record(record: logging.LogRecord) -> bool:
        event = dict(record.__dict__)
        # Formatting an exception or %-arguments can reveal secrets; omit both.
        event["event"] = record.msg if not record.args else None
        event["request_id"] = get_request_id()
        safe = scrub_logs(event)
        safe["timestamp"] = datetime.now(UTC).isoformat()
        safe["level"] = record.levelname
        safe["app"] = settings.app_name if _EVENT.fullmatch(settings.app_name) else "redacted"
        record.msg, record.args = json.dumps(safe), ()
        record.exc_info = record.exc_text = record.stack_info = None
        return True

    handler.addFilter(scrub_record)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.basicConfig(level=level, handlers=[handler], force=True)


def request_id_middleware(app: ASGIApp) -> ASGIApp:
    """Wrap the ASGI application, including its error handler, with request IDs.

    IDs are server-generated; incoming headers cannot inject arbitrary log data.
    Pure ASGI wrapping preserves streaming and context-variable isolation.
    """
    async def middleware(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await app(scope, receive, send)
            return
        request_id = uuid4().hex
        token = _request_id.set(request_id)

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                message = dict(message)
                message["headers"] = [(key, value) for key, value in message.get("headers", []) if key.lower() != b"x-request-id"]
                message["headers"].append((b"x-request-id", request_id.encode("ascii")))
            await send(message)

        try:
            await app(scope, receive, send_with_id)
        finally:
            _request_id.reset(token)

    return middleware
