"""External verification and notification contracts without live delivery."""

import hashlib
import hmac
import json
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import Depends, FastAPI

from access_kit.errors import ServiceUnavailable
from access_kit.notify import combine_notifiers, email_notifier, ntfy_notifier, webhook_notifier
from access_kit.turnstile import make_turnstile_verifier, require_turnstile
from conftest import stream_response


@pytest.fixture
def service():
    replies, calls = [], []

    def handle(request):
        calls.append(request)
        item = replies.pop(0)
        if isinstance(item, Exception):
            raise item
        return item if isinstance(item, httpx.Response) else stream_response(json.dumps(item).encode())

    return httpx.AsyncClient(transport=httpx.MockTransport(handle)), replies, calls


async def test_turnstile_binds_hostname_action_and_token(service):
    client, replies, calls = service
    verify = make_turnstile_verifier(secret="test-key", hostname="example.com", action="upload", client=client)
    for result, expected in [
        ({"success": True, "hostname": "example.com", "action": "upload"}, True),
        ({"success": 1, "hostname": "example.com", "action": "upload"}, False),
        ({"success": True, "hostname": "attacker.example", "action": "upload"}, False),
        ({"success": True, "hostname": "example.com", "action": "other"}, False),
        ({"success": False}, False),
    ]:
        replies.append(result)
        assert await verify("challenge", remote_ip="::ffff:8.8.8.8") is expected
    payload = json.loads(calls[0].content)
    assert payload == {"secret": "test-key", "response": "challenge", "remoteip": "8.8.8.8"}
    assert not await verify("") and not await verify("x" * 2049)
    await client.aclose()


async def test_turnstile_failures_are_closed_and_dependency_enforces(service, client_for):
    client, replies, _ = service
    verify = make_turnstile_verifier(secret="test-key", hostname="example.com", client=client)
    app = FastAPI()

    @app.post("/", dependencies=[Depends(require_turnstile(verify))])
    async def endpoint():
        return {"ok": True}

    caller = client_for(app)
    assert (await caller.post("/")).status_code == 403
    replies.extend([{"success": False}, stream_response(b"invalid"), {"success": True, "hostname": "example.com"}])
    codes = [(await caller.post("/", headers={"X-Turnstile-Token": "challenge"})).status_code for _ in range(3)]
    assert codes == [403, 503, 200]
    await client.aclose()


async def test_webhook_signs_the_actual_wire_body_and_does_not_follow_redirects(service):
    client, replies, calls = service
    replies.append(stream_response(status=204))
    send = webhook_notifier("https://notify.example/alerts", signing_secret="test-signing-key", client=client)
    await send("Budget threshold", "80 percent reserved", message_id="daily-80")
    request = calls[0]
    assert request.headers["x-access-kit-signature"] == hmac.new(b"test-signing-key", request.content, hashlib.sha256).hexdigest()
    assert json.loads(request.content)["id"] == "daily-80"
    replies.append(stream_response(status=302, headers={"location": "https://other.example"}))
    with pytest.raises(ServiceUnavailable):
        await send("Alert", "body")
    assert len(calls) == 2
    await client.aclose()


async def test_ntfy_contract_and_combined_delivery_errors(service):
    client, replies, calls = service
    replies.extend([{}, httpx.ConnectError("private endpoint")])
    send = ntfy_notifier("https://notify.example", topic="kit-alerts", token="test-token", client=client)
    await send("Threshold", "Reached")
    assert json.loads(calls[0].content) == {"topic": "kit-alerts", "title": "Threshold", "message": "Reached"}
    assert calls[0].headers["authorization"] == "Bearer test-token"
    seen = []

    async def success(title, body, **kwargs):
        seen.append(title)

    with pytest.raises(ExceptionGroup) as error:
        await combine_notifiers(send, success)("Alert", "body")
    assert seen == ["Alert"] and len(error.value.exceptions) == 1
    await client.aclose()


async def test_tls_smtp_and_message_id(monkeypatch):
    smtp = MagicMock()
    connection = smtp.return_value.__enter__.return_value
    connection.send_message.return_value = {}
    monkeypatch.setattr("smtplib.SMTP", smtp)
    send = email_notifier(host="mail.example", sender="kit@example.com", recipients=["owner@example.com"], username="test-user", password="test-password")
    await send("Budget alert", "Capacity reserved", message_id="day-80")
    connection.starttls.assert_called_once()
    connection.login.assert_called_once_with("test-user", "test-password")
    message = connection.send_message.call_args.args[0]
    assert message["Subject"] == "Budget alert"
    assert message["Message-ID"].endswith("@access-kit.local>")


@pytest.mark.parametrize(
    "factory",
    [
        lambda: webhook_notifier("http://remote.example"),
        lambda: ntfy_notifier("https://example.com", topic="bad topic"),
        lambda: make_turnstile_verifier(secret="", hostname="example.com"),
        lambda: make_turnstile_verifier(secret="key", hostname="https://bad"),
        lambda: email_notifier(host="remote", sender="a@example.com", recipients=["b@example.com"], start_tls=False),
        lambda: email_notifier(host="localhost", sender="a\r\nBcc: bad@example.com", recipients=["b@example.com"]),
        lambda: combine_notifiers(),
    ],
)
def test_invalid_delivery_configuration(factory):
    with pytest.raises(ValueError):
        factory()


async def test_verification_transport_and_response_bounds(service):
    client, replies, _ = service
    verify = make_turnstile_verifier(secret="key", hostname="example.com", client=client)
    replies.extend([httpx.ReadTimeout("secret endpoint"), stream_response(b"x" * 16385), stream_response(headers={"content-encoding": "gzip"})])
    for _ in range(3):
        with pytest.raises(ServiceUnavailable):
            await verify("token")
    await client.aclose()


@pytest.mark.parametrize("endpoint", ["https://[x]", "https://" + "user:password" + "@example.com", "file:///tmp/test"])
def test_invalid_service_endpoints(endpoint):
    with pytest.raises(ValueError):
        webhook_notifier(endpoint)


def test_unicode_hostname_rejects_invalid_encoding():
    with pytest.raises(ValueError):
        make_turnstile_verifier(secret="key", hostname="\ud800")
