"""Concurrency, accounting and fail-closed regressions for shared protections."""

import asyncio, pytest
from decimal import Decimal
from unittest.mock import AsyncMock

from fastapi import Depends, FastAPI
from redis.exceptions import ConnectionError as RedisConnectionError

from access_kit.errors import StorageUnavailable
from access_kit._redis import quantity
from access_kit.budget import BudgetExceeded, BudgetOverrun, make_budget
from access_kit.ratelimit import make_limiter, rate_limit_dependency


async def test_weighted_sliding_window_is_atomic_under_concurrency(fake_redis):
    check = make_limiter(fake_redis, name="captions", limit=10, window=60)
    results = await asyncio.gather(*(check("session", Decimal("0.5")) for _ in range(100)))
    assert sum(result["allowed"] for result in results) == 20
    assert all(result["remaining"] >= 0 for result in results)
    assert (await check("another-session", 1))["allowed"]
    denied = await check("session", 1)
    assert not denied["allowed"] and denied["retry_after"] >= 1
    short = make_limiter(fake_redis, name="short", limit=1, window=0.01)
    assert (await short("id", 1))["allowed"]
    await asyncio.sleep(0.02)
    assert (await short("id", 1))["allowed"]


async def test_limiter_memory_bound_and_configuration_conflicts(fake_redis):
    check = make_limiter(fake_redis, name="bounded", limit=100, max_events=2)
    assert (await check("id", 0.1))["allowed"]
    assert (await check("id", 0.1))["allowed"]
    assert not (await check("id", 0.1))["allowed"]
    assert not (await check("id", 101))["allowed"]
    with pytest.raises(StorageUnavailable):
        await make_limiter(fake_redis, name="bounded", limit=99)("id", 1)


async def test_daily_reservations_cannot_oversubscribe_under_load(fake_redis):
    budget = make_budget(fake_redis, name="global-tokens", limit=100)
    results = await asyncio.gather(*(budget["reserve"](3) for _ in range(200)), return_exceptions=True)
    reservations = [result for result in results if not isinstance(result, Exception)]
    assert len(reservations) == 33
    assert all(isinstance(result, BudgetExceeded) for result in results if isinstance(result, Exception))
    states = await asyncio.gather(*(budget["commit"](reservation, 2) for reservation in reservations))
    assert max(state["used"] + state["held"] for state in states) <= 100
    last = await budget["reserve"](34)
    state = await budget["commit"](last, 34)
    assert state["used"] == 100 and state["held"] == 0
    with pytest.raises(BudgetExceeded):
        await budget["reserve"](0.000001)


async def test_budget_idempotency_fractional_units_thresholds_and_release(fake_redis):
    budget = make_budget(fake_redis, name="audio", limit=10, unit="minutes")
    first = await budget["reserve"](Decimal("5.0000001"))
    assert first.amount == Decimal("5.000001")
    replay = await budget["reserve"](first.amount, reservation_id=first.id)
    assert replay.replayed and replay.id == first.id
    state = await budget["commit"](first, Decimal("4.5"))
    assert state["used"] == Decimal("4.5") and state["held"] == 0
    assert await budget["commit"](first, Decimal("4.5")) == state
    settled = await budget["reserve"](first.amount, reservation_id=first.id)
    assert settled.status == "committed" and settled.replayed
    with pytest.raises(ValueError):
        await budget["release"](first)
    second = await budget["reserve"](5)
    threshold_state = await budget["commit"](second, 4)
    assert threshold_state["thresholds"] == (Decimal("0.5"), Decimal("0.8"))
    third = await budget["reserve"](1)
    assert (await budget["release"](third))["held"] == 0
    assert (await budget["release"](third))["used"] == Decimal("8.5")


async def test_budget_conflicts_and_provider_overrun_fail_closed(fake_redis):
    budget = make_budget(fake_redis, name="overrun", limit=5)
    reservation = await budget["reserve"](2)
    with pytest.raises(BudgetOverrun):
        await budget["commit"](reservation, 6)
    with pytest.raises(BudgetExceeded):
        await budget["reserve"](1)
    with pytest.raises(StorageUnavailable):
        await make_budget(fake_redis, name="overrun", limit=6)["reserve"](1)
    with pytest.raises(StorageUnavailable):
        await make_budget(fake_redis, name="overrun", limit=6)["commit"](reservation, 6)
    with pytest.raises(ValueError):
        await make_budget(fake_redis, name="different", limit=5)["release"](reservation)
    with pytest.raises(StorageUnavailable):
        await budget["reserve"](1, reservation_id=reservation.id)


async def test_budget_missing_reservation_and_unavailable_store(fake_redis, monkeypatch):
    budget = make_budget(fake_redis, name="missing", limit=10)
    reservation = await budget["reserve"](1)
    await fake_redis.flushall()
    with pytest.raises(ValueError):
        await budget["release"](reservation)
    monkeypatch.setattr(fake_redis, "eval", AsyncMock(side_effect=RedisConnectionError("private endpoint")))
    with pytest.raises(StorageUnavailable, match="Redis operation failed"):
        await budget["reserve"](1)
    monkeypatch.setattr(fake_redis, "time", AsyncMock(side_effect=RedisConnectionError("private endpoint")))
    with pytest.raises(StorageUnavailable, match="clock unavailable"):
        await budget["reserve"](1)


async def test_budget_rollover_retry_and_bad_script_response(fake_redis, monkeypatch):
    budget = make_budget(fake_redis, name="clock", limit=10)
    monkeypatch.setattr(fake_redis, "eval", AsyncMock(return_value=[-2]))
    with pytest.raises(StorageUnavailable, match="day changed"):
        await budget["reserve"](1)
    monkeypatch.setattr(fake_redis, "eval", AsyncMock(return_value="unexpected"))
    with pytest.raises(StorageUnavailable, match="invalid Redis"):
        await budget["reserve"](1)


async def test_rate_limit_fastapi_dependency_denies_and_storage_failures(fake_redis, client_for, monkeypatch):
    check = make_limiter(fake_redis, name="api", limit=1)

    async def identity(request):
        return "verified-session"

    app = FastAPI()

    @app.get("/", dependencies=[Depends(rate_limit_dependency(check, identity))])
    async def endpoint():
        return {"ok": True}

    client = client_for(app)
    assert (await client.get("/")).status_code == 200
    denied = await client.get("/")
    assert denied.status_code == 429 and int(denied.headers["retry-after"]) > 0
    monkeypatch.setattr(fake_redis, "eval", AsyncMock(side_effect=RedisConnectionError("secret")))
    assert (await client.get("/")).status_code == 503


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, Decimal("1e50")])
def test_invalid_quantities(value):
    with pytest.raises(ValueError):
        quantity(value)


@pytest.mark.parametrize("options", [{"window": 0}, {"window": float("inf")}, {"max_events": 0}, {"max_events": True}])
def test_invalid_limiter_configuration(fake_redis, options):
    with pytest.raises(ValueError):
        make_limiter(fake_redis, name="test", limit=1, **options)


async def test_budget_snapshot_counts_reservations_and_config(fake_redis, monkeypatch):
    budget = make_budget(fake_redis, name="snapshot", limit=10)
    assert (await budget["snapshot"]())["used"] == 0
    receipt = await budget["reserve"](8)
    state = await budget["snapshot"]()
    assert state["held"] == 8 and state["thresholds"] == (Decimal("0.5"), Decimal("0.8"))
    await budget["release"](receipt)
    assert (await budget["snapshot"]())["held"] == 0
    with pytest.raises(StorageUnavailable):
        await make_budget(fake_redis, name="snapshot", limit=9)["snapshot"]()
    monkeypatch.setattr(fake_redis, "hgetall", AsyncMock(side_effect=RedisConnectionError("private")))
    with pytest.raises(StorageUnavailable):
        await budget["snapshot"]()


@pytest.mark.parametrize("options", [{"unit": ""}, {"thresholds": (Decimal("1.1"),)}, {"thresholds": (Decimal("NaN"),)}])
def test_budget_invalid_options(fake_redis, options):
    with pytest.raises(ValueError):
        make_budget(fake_redis, name="invalid", limit=10, **options)


async def test_micro_unit_precision_at_maximum_capacity(fake_redis):
    budget = make_budget(fake_redis, name="precision", limit=1_000_000_000)
    amount = Decimal("999999999.000001")
    receipt = await budget["reserve"](amount)
    assert (await budget["snapshot"]())["held"] == amount
    replay = await budget["reserve"](amount, reservation_id=receipt.id)
    assert replay.replayed
    state = await budget["commit"](receipt, Decimal("999999998.000001"))
    assert state["used"] == Decimal("999999998.000001") and state["held"] == 0
    assert await budget["commit"](receipt, state["used"]) == state
    check = make_limiter(fake_redis, name="large-rate", limit=1_000_000_000)
    assert (await check("id", amount))["remaining"] == Decimal("0.999999")
    assert (await check("id", Decimal("0.999999")))["remaining"] == 0
    assert not (await check("id", Decimal("0.000001")))["allowed"]


def test_empty_namespace_is_rejected(fake_redis):
    with pytest.raises(ValueError):
        make_limiter(fake_redis, name="", limit=1)


async def test_settlement_remains_on_its_admission_day(fake_redis, monkeypatch):
    budget = make_budget(fake_redis, name="midnight", limit=10)
    receipt = await budget["reserve"](5)
    monkeypatch.setattr(fake_redis, "time", AsyncMock(return_value=((receipt.day + 1) * 86400, 0)))
    assert (await budget["snapshot"]())["held"] == 0
    settled = await budget["commit"](receipt, 3)
    assert settled["used"] == 3 and settled["held"] == 0
    assert (await budget["snapshot"]())["used"] == 0
