# Protection and operating contracts

Install the Python package and create a long-lived `redis.asyncio.Redis` client
in the application's lifespan. Close it when the app shuts down. Use Redis 7+
with server scripting enabled. All workers enforcing one cap must use the same
namespace and configuration. Each namespace's script keys share a cluster hash
slot. Tests run the scripts in fakeredis with Lua, plus a separate real Redis
load check in CI.

## Weighted rate limits

`access_kit.ratelimit.make_limiter(redis, name=..., limit=..., window=60,
max_events=1000)` returns `await check(identity, cost=1)`. The result contains
`allowed`, Decimal `remaining`, and integer `retry_after` seconds. Costs round
up to six decimals; accepted events expire individually over the rolling window.
`max_events` bounds per-identity memory and can reject before the weighted cap.
Retry-After is the earliest event expiry, not a guarantee that a later request
will fit. An individual cost larger than the cap is always denied.

Use a server-verified session identifier or an HMAC IP identifier. An arbitrary
header or query parameter lets clients evade per-identity limits. Namespace and
identity values are hashed before they enter Redis keys. Different apps may use
separate names, or share a name to enforce a common ceiling. Reusing a name with
different limit/window values fails closed while its state exists.

`rate_limit_dependency(check, identify, cost=1)` adapts the limiter to FastAPI.
`identify` is an async function taking `Request` and returning the verified ID.
Denied requests receive 429 with Retry-After; storage failures receive 503.

## Turnstile

`access_kit.turnstile.make_turnstile_verifier(secret=..., hostname=...,
action=None, timeout=5, client=None)` returns `await verify(token,
remote_ip=None)`. Validation always calls Cloudflare's fixed Siteverify endpoint.
The response must have boolean success, the configured hostname, and the
configured action when supplied. Missing/oversized tokens return false.
Unavailable or malformed services raise `ServiceUnavailable`.

`require_turnstile(verify, token_header="x-turnstile-token")` is a FastAPI
dependency: duplicate/missing/invalid tokens yield 403; service failures yield 503. Pass the widget's fresh token in that header. The helper does not extract
an IP from request headers; direct verifier callers may supply a verified peer.
Cloudflare tokens expire and are single-use; do not cache successful tokens or
silently retry a paid action using the same token. See the official
[server validation contract](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/).

## Daily budgets

`access_kit.budget.make_budget(redis, name=..., limit=..., unit="tokens",
thresholds=(Decimal("0.5"), Decimal("0.8"), Decimal("1")))` returns four async
operations: `reserve`, `commit`, `release`, and `snapshot`.

```python
from access_kit.budget import make_budget

budget = make_budget(redis, name="shared-daily-tokens", limit=100_000)
receipt = await budget["reserve"](2_000)
# Bound the provider's input AND maximum output within the reserved 2,000 units.
# Perform paid work here, then obtain its trustworthy actual usage.
state = await budget["commit"](receipt, 1_250)
```

Reserve the TRUE upper bound before dispatching work. Atomic admission enforces
`used + held + requested <= limit`; concurrent workers cannot oversubscribe it.
No library can undo a provider charge that exceeded its declared upper bound.
If actual usage exceeds the reservation, commit records the charge, blocks the
rest of that admission day, and raises `BudgetOverrun`.

1. `reserve(amount, reservation_id=None)` returns a `Reservation` receipt. The
   optional UUID makes admission idempotent within the UTC day. A replay has
   `replayed=True` and its current status; it does not authorize paid work again.
   Apps must durably associate their own operation ID and receipt with the job.
2. `commit(receipt, actual)` charges actual usage and releases unused capacity.
   Repeating the identical commit is harmless; conflicting settlement fails.
3. `release(receipt)` is only for work known not to incur usage. Unknown usage,
   a lost provider response, and a worker crash retain the conservative hold.
   Do not put unconditional release in `finally`.
4. `snapshot()` returns the current UTC day's Decimal `used`, `held`, `limit`,
   `unit`, and reached `thresholds`. Settlement returns the same state shape.
   Thresholds describe current occupied capacity; the app owns deduplication and
   sending alerts with `notify`, ideally from a durable outbox.

Redis server time defines UTC days. A receipt remains charged to its original
admission day after midnight. State and receipts expire seven days after that
day ends. Preserve the receipt for delayed settlement; it is not a cross-day
idempotency key. Namespace limit or unit conflicts fail closed. Fractional
quantities round upward to six decimals; amounts are bounded to one billion.
`BudgetExceeded` signals denied admission. `StorageUnavailable` must deny paid
work, never fall back to an in-memory per-process counter.

Keep accounting Redis durable, private, and configured with no eviction. A
flush, data loss, stale replica promotion, manual edit, or namespace change can
reset a cap. Budget accounting is admission control, not a billing ledger or an
exactly-once executor. Use provider-side caps and a durable app ledger for those
requirements. Redis [script execution](https://redis.io/docs/latest/develop/programmability/eval-intro/)
is atomic; [cluster keys must share a hash slot](https://redis.io/docs/latest/management/scaling/).

## Notifications

`access_kit.notify` supplies async callable factories. All senders accept
`await send(title, body, message_id=None)`. Titles are nonempty, single-line and
at most 256 characters; bodies are at most 4096. Never include document content,
prompts, session tokens, credentials, or raw IPs in alerts.

| Factory                                                               | Configuration                                                |
| --------------------------------------------------------------------- | ------------------------------------------------------------ |
| `ntfy_notifier(url, topic=..., token=None, timeout=10, client=None)`  | JSON publish endpoint; optional bearer token                 |
| `webhook_notifier(url, signing_secret=None, timeout=10, client=None)` | JSON `{id, title, message}`; optional HMAC SHA-256 header    |
| `email_notifier(host=..., sender=..., recipients=..., ...)`           | TLS SMTP; port 587 and STARTTLS by default                   |
| `combine_notifiers(*senders)`                                         | Attempts every transport; raises ExceptionGroup for failures |

Webhook `X-Access-Kit-Signature` is the lowercase hex digest of the exact UTF-8
JSON body. Verify it with a constant-time comparison. `message_id` is an app
operation ID, not a universal delivery guarantee. SMTP uses a deterministic
Message-ID, and ntfy does not guarantee deduplication. Retries are explicit and
can deliver duplicates; a timeout can happen after remote acceptance.

Endpoints are trusted operator configuration, never user-supplied fetch URLs.
HTTP is allowed only on loopback; HTTPS is required elsewhere. Redirects are
rejected, responses are bounded, and owned HTTP clients ignore environment
proxies. These senders do not perform SSRF-safe fetching; use `safe_fetch` for
untrusted URLs. Injected HTTP clients remain caller-owned. SMTP requires TLS
for remote servers (`start_tls=True`, or `use_tls=True, start_tls=False`).
No messages are sent during import or factory construction.

## Repeat the real Redis load check

Against a dedicated local Redis server:

```bash
python scripts/check_redis_load.py redis://127.0.0.1:6379/0
```

It submits 1,000 competing operations for each of token and minute budgets
through four independent clients, checks weighted admission, and verifies owner
isolation and job replay. Only the run's randomly named keys are removed.
The CI workflow `redis-integration.yml` repeats this independently of unit tests.
