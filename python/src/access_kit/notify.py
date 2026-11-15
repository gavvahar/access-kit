"""Explicit ntfy, webhook, and TLS SMTP alerts. No transport retries by default."""

import asyncio, hashlib, hmac, json, math, smtplib, ssl, httpx
from collections.abc import Awaitable, Callable, Sequence
from email.message import EmailMessage
from email.utils import getaddresses
from uuid import uuid4


from access_kit.errors import ServiceUnavailable
from access_kit._http import request_bytes, service_url


def _message(title: str, body: str) -> None:
    if not title or len(title) > 256 or any(char in title for char in "\r\n") or len(body) > 4096:
        raise ValueError("notification title/body exceeds safe bounds")


type Notifier = Callable[..., Awaitable[None]]


def webhook_notifier(url: str, *, signing_secret: str | None = None, timeout: float = 10, client: httpx.AsyncClient | None = None) -> Notifier:
    target = service_url(url)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("notification timeout must be positive")

    async def send(title: str, body: str, *, message_id: str | None = None) -> None:
        _message(title, body)
        payload = {"id": message_id or uuid4().hex, "title": title, "message": body}
        headers = {}
        if signing_secret is not None:
            encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
            headers["X-Access-Kit-Signature"] = hmac.new(signing_secret.encode(), encoded, hashlib.sha256).hexdigest()
        await request_bytes(target, payload=payload, headers=headers, client=client, timeout=timeout)

    return send


def ntfy_notifier(url: str, *, topic: str, token: str | None = None, timeout: float = 10, client: httpx.AsyncClient | None = None) -> Notifier:
    target = service_url(url)
    if not topic or len(topic) > 64 or not all(char.isalnum() or char in "_-" for char in topic) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("configure a bounded topic and positive timeout")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    async def send(title: str, body: str, *, message_id: str | None = None) -> None:
        _message(title, body)
        # The API's message ID is informational; ntfy does not promise deduplication.
        await request_bytes(target, payload={"topic": topic, "title": title, "message": body}, headers=headers, client=client, timeout=timeout)

    return send


def email_notifier(
    *,
    host: str,
    sender: str,
    recipients: Sequence[str],
    port: int = 587,
    username: str | None = None,
    password: str | None = None,
    start_tls: bool = True,
    use_tls: bool = False,
    timeout: float = 10,
) -> Notifier:
    addresses = (sender, *recipients)
    if not host or not recipients or len(recipients) > 10 or not 1 <= port <= 65535 or not math.isfinite(timeout) or timeout <= 0 or (start_tls and use_tls):
        raise ValueError("invalid SMTP configuration")
    if not (start_tls or use_tls) and host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("remote SMTP requires TLS")
    if any(any(char in value for char in "\r\n") for value in addresses) or any("@" not in address for _, address in getaddresses(addresses)):
        raise ValueError("invalid notification email address")
    if (username is None) != (password is None):
        raise ValueError("provide both SMTP username and password")

    def deliver(message: EmailMessage) -> None:
        try:
            transport = smtplib.SMTP_SSL(host, port, timeout=timeout, context=ssl.create_default_context()) if use_tls else smtplib.SMTP(host, port, timeout=timeout)
            with transport as connection:
                if start_tls:
                    connection.starttls(context=ssl.create_default_context())
                if username is not None and password is not None:
                    connection.login(username, password)
                if connection.send_message(message):
                    raise ServiceUnavailable("SMTP refused one or more recipients")
        except (smtplib.SMTPException, OSError):
            raise ServiceUnavailable("SMTP delivery failed") from None

    async def send(title: str, body: str, *, message_id: str | None = None) -> None:
        _message(title, body)
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = sender, ", ".join(recipients), title
        identity = hashlib.sha256((message_id or uuid4().hex).encode()).hexdigest()
        message["Message-ID"] = f"<{identity}@access-kit.local>"
        message.set_content(body)
        await asyncio.to_thread(deliver, message)

    return send


def combine_notifiers(*notifiers: Notifier) -> Notifier:
    if not notifiers:
        raise ValueError("at least one notifier is required")

    async def send(title: str, body: str, *, message_id: str | None = None) -> None:
        results = await asyncio.gather(*(notify(title, body, message_id=message_id) for notify in notifiers), return_exceptions=True)
        errors = [result for result in results if isinstance(result, Exception)]
        if errors:
            raise ExceptionGroup("notification delivery failed for some transports", errors)

    return send
