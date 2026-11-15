"""Worker transitions, owner isolation and reconnectable SSE contracts."""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from redis.exceptions import ConnectionError as RedisConnectionError
from starlette.requests import Request

from access_kit.errors import StorageUnavailable
from access_kit.jobs import job_response, make_jobs


def request(headers=(), *, disconnected=False):
    async def receive():
        return {"type": "http.disconnect" if disconnected else "http.request", "body": b""}

    return Request({"type": "http", "headers": headers}, receive=receive)


async def test_worker_transitions_idempotency_and_ownership(fake_redis):
    jobs = make_jobs(fake_redis, name="read")
    first = await jobs["create"]("alice", total=3)
    identity = first["id"]
    assert await jobs["create"]("alice", total=3, job_id=identity) == first
    assert await jobs["get"]("bob", identity) is None
    with pytest.raises(KeyError):
        await jobs["update"]("bob", identity, completed=1, label="Reading")
    step = await jobs["update"]("alice", identity, completed=2, label="Reading")
    assert step["sequence"] == 2 and step["status"] == "running"
    for completed, status in [(1, "running"), (2, "complete"), (4, "running")]:
        with pytest.raises(ValueError):
            await jobs["update"]("alice", identity, completed=completed, label="Next", status=status)
    done = await jobs["update"]("alice", identity, completed=3, label="Ready", status="complete")
    assert await jobs["update"]("alice", identity, completed=3, label="Ready", status="complete") == done
    with pytest.raises(ValueError):
        await jobs["update"]("alice", identity, completed=3, label="Reopened")
    with pytest.raises(ValueError):
        await jobs["create"]("alice", total=4, job_id=identity)


async def test_replay_stream_and_trimmed_snapshot(fake_redis):
    jobs = make_jobs(fake_redis, name="events", history=2)
    first = await jobs["create"]("owner", total=2)
    second = await jobs["update"]("owner", first["id"], completed=1, label="First")
    last = await jobs["update"]("owner", first["id"], completed=2, label="Finished", status="complete")
    assert [event async for event in jobs["events"]("owner", first["id"], after=second["event_id"])] == [last]
    for cursor in [None, first["event_id"], last["event_id"], "18446744073709551615-0"]:
        assert [event async for event in jobs["events"]("owner", first["id"], after=cursor)] == [last]
    assert len(await fake_redis.keys("*:events")) == 1
    assert await fake_redis.xlen((await fake_redis.keys("*:events"))[0]) == 2


async def test_live_stream_heartbeat_and_terminal_delivery(fake_redis):
    jobs = make_jobs(fake_redis, name="live")
    first = await jobs["create"]("owner", total=1)
    stream = jobs["events"]("owner", first["id"], heartbeat=0.01)
    assert await anext(stream) == first
    assert await asyncio.wait_for(anext(stream), 1) is None
    await jobs["update"]("owner", first["id"], completed=0, label="Stopped", status="cancelled")
    assert (await anext(stream))["status"] == "cancelled"
    with pytest.raises(StopAsyncIteration):
        await anext(stream)


async def test_sse_framing_private_owner_and_headers(fake_redis):
    jobs = make_jobs(fake_redis, name="sse")
    first = await jobs["create"]("verified-owner", total=1)
    done = await jobs["update"]("verified-owner", first["id"], completed=1, label="Done\nevent: evil", status="complete")
    response = await job_response(request(), jobs, owner="verified-owner", job_id=first["id"])
    frames = [frame async for frame in response.body_iterator]
    assert len(frames) == 1 and frames[0].count("\nevent:") == 1
    assert json.loads(frames[0].split("\ndata: ")[1]) == done
    assert response.headers["cache-control"] == "no-store"
    with pytest.raises(HTTPException) as error:
        await job_response(request(), jobs, owner="outsider", job_id=first["id"])
    assert error.value.status_code == 404
    for headers in [[(b"last-event-id", b"evil")], [(b"last-event-id", b"1-0"), (b"last-event-id", b"2-0")]]:
        with pytest.raises(HTTPException) as error:
            await job_response(request(headers), jobs, owner="verified-owner", job_id=first["id"])
        assert error.value.status_code == 400
    response = await job_response(request(disconnected=True), jobs, owner="verified-owner", job_id=first["id"])
    assert [frame async for frame in response.body_iterator] == []


async def test_stream_timeout_and_store_failure(fake_redis, monkeypatch):
    jobs = make_jobs(fake_redis, name="failure")
    first = await jobs["create"]("owner")
    response = await job_response(request(), jobs, owner="owner", job_id=first["id"], heartbeat=0.01, max_duration=0.03)
    assert "event: reconnect" in "".join([frame async for frame in response.body_iterator])
    monkeypatch.setattr(fake_redis, "get", AsyncMock(side_effect=RedisConnectionError("private")))
    with pytest.raises(HTTPException) as error:
        await job_response(request(), jobs, owner="owner", job_id=first["id"])
    assert error.value.status_code == 503 and "private" not in str(error.value)
    with pytest.raises(StorageUnavailable):
        await jobs["get"]("owner", first["id"])


@pytest.mark.parametrize("options", [{"history": 0}, {"retention": 0}, {"history": True}])
def test_invalid_store_options(fake_redis, options):
    with pytest.raises(ValueError):
        make_jobs(fake_redis, name="invalid", **options)
