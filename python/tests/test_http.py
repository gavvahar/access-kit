"""Oversized bodies are rejected before a consumer parses or dispatches work."""

import asyncio, pytest


from access_kit.http import body_limit


async def invoke(chunks, headers=(), **options):
    messages = iter(chunks)
    sent, called = [], []

    async def receive():
        return next(messages)

    async def app(scope, receive, send):
        called.append(await receive())
        called.append(await receive())

    await body_limit(app, **options)({"type": "http", "headers": headers}, receive, sent.append)
    return sent, called


async def test_bounded_body_replays_once_then_preserves_disconnect():
    sent, called = await invoke(
        [{"type": "http.request", "body": b"first", "more_body": True}, {"type": "http.request", "body": b"last"}, {"type": "http.disconnect"}], [(b"content-length", b"9")]
    )
    assert not sent
    assert called == [{"type": "http.request", "body": b"firstlast", "more_body": False}, {"type": "http.disconnect"}]


@pytest.mark.parametrize(
    "headers,body,code",
    [
        ([(b"content-length", b"9")], b"", 413),
        ([], b"123456", 413),
        ([(b"content-length", b"2")], b"x", 400),
        ([(b"content-length", b"x")], b"", 400),
        ([(b"content-length", b"9" * 5000)], b"", 400),
        ([(b"content-length", b"1"), (b"content-length", b"1")], b"x", 400),
    ],
)
async def test_rejection_happens_before_consumer(headers, body, code):
    sent, called = [], []

    async def receive():
        return {"type": "http.request", "body": body}

    async def send(message):
        sent.append(message)

    async def app(*args):
        called.append(True)

    await body_limit(app, max_bytes=5)({"type": "http", "headers": headers}, receive, send)
    assert sent[0]["status"] == code and not called


async def test_disconnect_timeout_and_non_http_lifecycle():
    called, sent = [], []

    async def app(*args):
        called.append(True)

    async def disconnected():
        return {"type": "http.disconnect"}

    async def stalled():
        await asyncio.sleep(1)

    async def send(message):
        sent.append(message)

    await body_limit(app)({"type": "websocket"}, disconnected, send)
    assert called == [True]
    called.clear()
    await body_limit(app)({"type": "http", "headers": []}, disconnected, send)
    assert not called and not sent
    await body_limit(app, read_timeout=0.001)({"type": "http", "headers": []}, stalled, send)
    assert sent[0]["status"] == 408 and not called


@pytest.mark.parametrize("options", [{"max_bytes": 0}, {"max_bytes": True}, {"read_timeout": float("inf")}, {"read_timeout": 0}])
def test_invalid_bounds(options):
    with pytest.raises(ValueError):
        body_limit(None, **options)
