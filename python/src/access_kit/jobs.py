"""Owner-scoped Redis job progress and bounded, reconnectable SSE streams.

Applications own queue execution (for example arq) and derive owner IDs from
verified sessions/authentication. This module stores no documents or results.
"""

import asyncio, json, math, re
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, TypedDict, cast
from uuid import UUID, uuid4

from fastapi import HTTPException, Request
from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.responses import StreamingResponse

from access_kit.errors import StorageUnavailable
from access_kit._redis import CLOCK, atomic, key_scope

_TERMINAL = frozenset({"complete", "failed", "cancelled"})
_SAVE = (
    CLOCK
    + """
local raw=redis.call('GET',KEYS[1]); local requested=cjson.decode(ARGV[2]); local job;
if ARGV[1]=='create' then
 if raw then
  job=cjson.decode(raw); if job.total~=requested.total then return {-2} end
  return {2,raw}
 end
 job=requested; job.sequence=1;
else
 if not raw then return {-1} end
 job=cjson.decode(raw);
 if job.status=='complete' or job.status=='failed' or job.status=='cancelled' then
  if job.status==requested.status and job.completed==requested.completed and job.label==requested.label then return {2,raw} end
  return {-2}
 end
 if requested.completed<job.completed or requested.completed>job.total then return {-2} end
 if requested.status=='queued' or (requested.status=='complete' and requested.completed~=job.total) then return {-2} end
 job.status=requested.status; job.completed=requested.completed; job.label=requested.label; job.sequence=job.sequence+1;
end
job.updated_at=now; job.event_id='';
local id=redis.call('XADD',KEYS[2],'MAXLEN',tonumber(ARGV[4]),'*','data',cjson.encode(job));
job.event_id=id; local encoded=cjson.encode(job);
redis.call('SET',KEYS[1],encoded,'EX',tonumber(ARGV[3])); redis.call('EXPIRE',KEYS[2],tonumber(ARGV[3]));
return {1,encoded}
"""
)


class Job(TypedDict):
    id: str
    status: str
    completed: int
    total: int
    label: str
    sequence: int
    updated_at: int
    event_id: str


class Jobs(TypedDict):
    create: Callable[..., Awaitable[Job]]
    update: Callable[..., Awaitable[Job]]
    get: Callable[[str, str], Awaitable[Job | None]]
    events: Callable[..., AsyncIterator[Job | None]]


def _decode(value: Any) -> Job:
    try:
        job = json.loads(value)
        if not isinstance(job, dict) or not {"id", "status", "completed", "total", "label", "sequence", "updated_at", "event_id"} <= job.keys():
            raise ValueError("invalid job")
        return cast(Job, job)
    except (ValueError, TypeError, RecursionError):
        raise StorageUnavailable("invalid job progress state") from None


def _stream_id(value: str) -> tuple[int, int]:
    if not re.fullmatch(r"[0-9]{1,20}-[0-9]{1,20}", value):
        raise ValueError("invalid event ID")
    pair = tuple(int(part) for part in value.split("-"))
    if max(pair) > 2**64 - 1:
        raise ValueError("invalid event ID")
    return pair[0], pair[1]


def make_jobs(redis: Redis, *, name: str, retention: int = 86400, history: int = 1000) -> Jobs:
    """Create a progress store. Updates cannot regress or reopen terminal jobs."""
    scope = key_scope(name)
    if type(retention) is not int or not 1 <= retention <= 604800 or type(history) is not int or not 1 <= history <= 10_000:
        raise ValueError("retention must be 1..604800 seconds and history 1..10000 events")

    def keys(owner: str, job_id: str) -> list[str]:
        identity = UUID(job_id).hex
        prefix = f"ak:job:{{{scope}:{key_scope(owner)}:{identity}}}"
        return [prefix + ":state", prefix + ":events"]

    async def save(owner: str, job_id: str, action: str, value: dict[str, Any]) -> Job:
        result = await atomic(redis, _SAVE, keys(owner, job_id), [action, json.dumps(value, ensure_ascii=False), retention, history])
        if int(result[0]) == -1:
            raise KeyError("job not found")
        if int(result[0]) == -2:
            raise ValueError("invalid job progress transition")
        return _decode(result[1])

    async def create(owner: str, *, total: int = 100, job_id: str | None = None) -> Job:
        if type(total) is not int or not 1 <= total <= 1_000_000:
            raise ValueError("job total must be a positive integer up to one million")
        identity = UUID(job_id).hex if job_id is not None else uuid4().hex
        return await save(owner, identity, "create", {"id": identity, "total": total, "status": "queued", "completed": 0, "label": "Waiting"})

    async def update(owner: str, job_id: str, *, completed: int, label: str, status: str = "running") -> Job:
        if type(completed) is not int or completed < 0 or status not in {"running", *_TERMINAL} or not label or len(label) > 180:
            raise ValueError("invalid job progress values")
        return await save(owner, job_id, "update", {"completed": completed, "label": label, "status": status})

    async def get(owner: str, job_id: str) -> Job | None:
        try:
            raw = await redis.get(keys(owner, job_id)[0])
        except (RedisError, OSError):
            raise StorageUnavailable("job progress unavailable") from None
        return None if raw is None else _decode(raw)

    async def events(owner: str, job_id: str, *, after: str | None = None, heartbeat: float = 5) -> AsyncIterator[Job | None]:
        if not math.isfinite(heartbeat) or not 0.01 <= heartbeat <= 30:
            raise ValueError("heartbeat must be 0.01..30 seconds")
        if after is not None:
            _stream_id(after)
        snapshot = await get(owner, job_id)
        if snapshot is None:
            raise KeyError("job not found")
        event_key = keys(owner, job_id)[1]
        try:
            first = await redis.xrange(event_key, count=1)
            oldest = first[0][0] if first else snapshot["event_id"]
            oldest = oldest.decode() if isinstance(oldest, bytes) else str(oldest)
            if after is None or _stream_id(after) < _stream_id(oldest) or _stream_id(after) >= _stream_id(snapshot["event_id"]):
                yield snapshot
                if snapshot["status"] in _TERMINAL:
                    return
                cursor = snapshot["event_id"]
            else:
                cursor = after
            while True:
                batches = cast(list[tuple[Any, list[tuple[Any, dict[Any, Any]]]]], await redis.xread({event_key: cursor}, count=100, block=max(1, math.ceil(heartbeat * 1000))))
                if not batches:
                    if await get(owner, job_id) is None:
                        return
                    yield None
                    continue
                for _, entries in batches:
                    for identifier, fields in entries:
                        cursor = identifier.decode() if isinstance(identifier, bytes) else str(identifier)
                        job = _decode(fields.get("data", fields.get(b"data")))
                        job["event_id"] = cursor
                        yield job
                        if job["status"] in _TERMINAL:
                            return
        except (RedisError, OSError):
            raise StorageUnavailable("job event stream unavailable") from None

    return Jobs(create=create, update=update, get=get, events=events)


async def job_response(request: Request, jobs: Jobs, *, owner: str, job_id: str, heartbeat: float = 5, max_duration: float = 300) -> StreamingResponse:
    """Owner-bound SSE endpoint helper with Last-Event-ID and finite connections.

    Determine owner on the server. Never accept an owner from a query parameter.
    Reconnecting after history was trimmed receives a fresh snapshot instead.
    """
    if not math.isfinite(heartbeat) or not 0.01 <= heartbeat <= 30:
        raise ValueError("heartbeat must be 0.01..30 seconds")
    if not math.isfinite(max_duration) or max_duration <= 0:
        raise ValueError("SSE connection duration must be positive")
    ids = request.headers.getlist("last-event-id")
    try:
        if len(ids) > 1:
            raise ValueError("duplicate event IDs")
        if ids:
            _stream_id(ids[0])
        current = await jobs["get"](owner, job_id)
    except ValueError:
        raise HTTPException(400, "Invalid progress request") from None
    except StorageUnavailable:
        raise HTTPException(503, "Progress temporarily unavailable") from None
    if current is None:
        raise HTTPException(404, "Job not found")

    async def stream() -> AsyncIterator[str]:
        try:
            async with asyncio.timeout(max_duration):
                async for event in jobs["events"](owner, job_id, after=ids[0] if ids else None, heartbeat=heartbeat):
                    if await request.is_disconnected():
                        return
                    if event is None:
                        yield ": keep-alive\n\n"
                    else:
                        kind = event["status"] if event["status"] in _TERMINAL else "progress"
                        yield f"id: {event['event_id']}\nevent: {kind}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
        except TimeoutError:
            yield "event: reconnect\ndata: {}\n\n"
        except (StorageUnavailable, KeyError):
            yield "event: unavailable\ndata: {}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
