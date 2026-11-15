# Background progress and SSE

The application owns task execution, retries, authorization, cancellation and
results. `access_kit.jobs` stores bounded progress metadata in Redis; it is not
a queue or worker runner. An arq task, coroutine, or other worker can publish
updates through the same interface.

## Store and worker API

`make_jobs(redis, name=..., retention=86400, history=1000)` returns async
`create(owner, total=100, job_id=None)`, `update(owner, job_id, completed=...,
label=..., status="running")`, `get(owner, job_id)`, and an `events` async iterator.

```python
from access_kit.jobs import make_jobs

jobs = make_jobs(redis, name="reader-progress")
job = await jobs["create"](owner_id, total=3)
await jobs["update"](owner_id, job["id"], completed=1, label="Preparing")
# The application runs the next work step and stores its result separately.
await jobs["update"](owner_id, job["id"], completed=3, label="Ready", status="complete")
```

Progress is monotonic. `queued` transitions to `running` or a terminal status:
`complete`, `failed`, `cancelled`. Completion requires completed == total.
Terminal state cannot reopen; identical terminal updates are idempotent.
A repeated create with the same optional UUID and total returns the existing job.
Concurrent updates are serialized by Redis Lua; stale regressions fail rather
than erase earned progress. A new attempt requiring a fresh counter gets a new
job ID. A UI cancellation label does not terminate the worker; the app must do so.

A job has `id`, `status`, `completed`, `total`, `label`, `sequence`, `updated_at`
(Redis epoch milliseconds), and `event_id` (Redis stream ID). Labels are bounded
to 180 characters. Never store documents, raw errors, credentials, or results in
labels. Keys hash namespace and owner. A missing job or wrong owner returns
None from get; no shared public job index exists.

Retention is 1..604800 seconds since the last write; history is 1..10000 events
with exact trimming. Expiration means progress is unavailable, not that a task
was cancelled. The app should retain its durable result/operation state elsewhere.

## FastAPI endpoint

```python
from fastapi import Depends, Request
from access_kit.jobs import job_response


@app.get("/jobs/{job_id}/events")
async def progress(request: Request, job_id: str, owner=Depends(verified_owner)):
    return await job_response(request, jobs, owner=owner, job_id=job_id)
```

`verified_owner` is supplied by the app's authentication/session dependency.
Never accept owner IDs from a client query or an unsigned cookie. Limit access
and concurrent connections at the application edge. Helpers do not set CORS or
turn public IDs into authorization. Unknown/wrong-owner jobs yield 404; malformed
IDs yield 400; unavailable storage yields 503 before the stream begins.

The stream uses `text/event-stream`, no-store caching, and disables nginx
buffering with X-Accel-Buffering. Reverse proxies still need streaming enabled.
Each JSON frame has an `id` and `event`: `progress`, `complete`, `failed`, or
`cancelled`. JSON escaping prevents labels from injecting SSE fields. Terminal
frames end the stream; the client must close EventSource on terminal events to
stop the browser's automatic reconnect.

`events(owner, job_id, after=None, heartbeat=5)` sends a snapshot on initial
connection, replays retained events after Last-Event-ID, and sends a fresh
snapshot when the cursor is too old or ahead of current state. Delivery may
repeat: clients should apply snapshots by sequence, not increment counters for
every received message. `None` indicates a heartbeat. Storage failure during
streaming produces `unavailable`; reconnect with backoff. Do not render labels
with innerHTML.

`job_response(..., heartbeat=5, max_duration=300)` emits comment heartbeats and
ends finite connections with `reconnect`. Disconnects stop iteration, releasing
the blocked read. Heartbeats must be 0.01..30 seconds. Browsers reconnect with
Last-Event-ID; the helper does not implement result downloads or queue retries.
A deleted/expired progress store does not authorize executing work again.
