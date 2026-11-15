"""Daily Redis budgets with atomic, idempotent reserve/commit/release accounting."""

from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import NamedTuple, TypedDict
from uuid import UUID, uuid4

from redis.asyncio import Redis
from redis.exceptions import RedisError

from access_kit.errors import StorageUnavailable
from access_kit._redis import CLOCK, atomic, key_scope, quantity, units

_RETENTION = 7 * 86400
_RESERVE = (
    CLOCK
    + """
local day=math.floor(now/86400000);
if tostring(day)~=ARGV[1] then return {-2} end
local capacity=tonumber(ARGV[2]); local amount=tonumber(ARGV[3]); local id=ARGV[4];
local configured=redis.call('HGET',KEYS[1],'limit');
if configured and (tonumber(configured)~=capacity or redis.call('HGET',KEYS[1],'unit')~=ARGV[5]) then return {-3} end
local used=tonumber(redis.call('HGET',KEYS[1],'used') or '0');
local held=tonumber(redis.call('HGET',KEYS[1],'held') or '0');
local previous=redis.call('HGET',KEYS[2],id);
if previous then
 local item=cjson.decode(previous); if tonumber(item.reserved)~=amount then return {-3} end
 return {2,item.status,item.actual,used,held}
end
if redis.call('HGET',KEYS[1],'blocked')=='1' or used+held+amount>capacity then return {0,'denied',0,used,held} end
held=held+amount;
redis.call('HSET',KEYS[1],'limit',ARGV[2],'unit',ARGV[5],'used',string.format('%.0f',used),'held',string.format('%.0f',held));
redis.call('HSET',KEYS[2],id,cjson.encode({reserved=ARGV[3],status='held',actual='0'}));
local expiry=(day+1)*86400+tonumber(ARGV[6]);
for _,key in ipairs(KEYS) do redis.call('EXPIREAT',key,expiry) end
return {1,'held',0,used,held}
"""
)
_FINISH = """
local previous=redis.call('HGET',KEYS[2],ARGV[1]);
local configured=redis.call('HGET',KEYS[1],'limit');
if not previous or not configured then return {-1} end
if tonumber(configured)~=tonumber(ARGV[4]) or redis.call('HGET',KEYS[1],'unit')~=ARGV[5] then return {-4} end
local item=cjson.decode(previous); local action=ARGV[2]; local actual=tonumber(ARGV[3]);
if item.status~='held' then
 if item.status==action and tonumber(item.actual)==actual then return {2,redis.call('HGET',KEYS[1],'used'),redis.call('HGET',KEYS[1],'held')} end
 return {-2}
end
local used=tonumber(redis.call('HGET',KEYS[1],'used')); local held=tonumber(redis.call('HGET',KEYS[1],'held'));
held=held-tonumber(item.reserved); used=used+actual;
item.status=action; item.actual=ARGV[3];
redis.call('HSET',KEYS[1],'used',string.format('%.0f',used),'held',string.format('%.0f',held));
redis.call('HSET',KEYS[2],ARGV[1],cjson.encode(item));
if actual>tonumber(item.reserved) then redis.call('HSET',KEYS[1],'blocked',1); return {-3,used,held} end
return {1,used,held}
"""


class BudgetExceeded(Exception):
    """The requested upper bound exceeds available daily capacity."""


class BudgetOverrun(Exception):
    """Actual usage exceeded its reservation; the day is blocked and usage recorded."""


class Reservation(NamedTuple):
    id: str
    day: int
    amount: Decimal
    scope: str
    replayed: bool
    status: str


class BudgetState(TypedDict):
    used: Decimal
    held: Decimal
    limit: Decimal
    unit: str
    thresholds: tuple[Decimal, ...]


class Budget(TypedDict):
    snapshot: Callable[[], Awaitable[BudgetState]]
    reserve: Callable[..., Awaitable[Reservation]]
    commit: Callable[[Reservation, int | float | Decimal], Awaitable[BudgetState]]
    release: Callable[[Reservation], Awaitable[BudgetState]]


def make_budget(
    redis: Redis, *, name: str, limit: int | float | Decimal, unit: str = "tokens", thresholds: tuple[Decimal, ...] = (Decimal("0.5"), Decimal("0.8"), Decimal("1"))
) -> Budget:
    """Reserve a true upper bound BEFORE work; commit known actual usage afterward.

    Fractional units round upward to six decimals. Redis server time defines UTC
    days. Reservations remain charged to their admission day across midnight.
    Do not release on unknown provider usage; retain the conservative reservation.
    Keep Redis durable with a no-eviction policy. Redis is not a durable billing DB.
    """
    capacity = quantity(limit)
    scope = key_scope(name)
    if not unit or len(unit) > 32 or any(not value.is_finite() or not 0 < value <= 1 for value in thresholds):
        raise ValueError("provide a unit and thresholds in (0, 1]")
    crossings = tuple(sorted(set(thresholds)))

    def keys(day: int) -> list[str]:
        return [f"ak:budget:{{{scope}}}:{day}:{suffix}" for suffix in ("state", "reservations")]

    def state(used: int, held: int) -> BudgetState:
        occupied = units(used + held)
        return BudgetState(
            used=units(used), held=units(held), limit=units(capacity), unit=unit, thresholds=tuple(value for value in crossings if occupied >= units(capacity) * value)
        )

    async def snapshot() -> BudgetState:
        try:
            clock = await redis.time()
            raw = await redis.hgetall(keys(int(clock[0]) // 86400)[0])
        except (RedisError, OSError):
            raise StorageUnavailable("budget state unavailable") from None
        values = {(k.decode() if isinstance(k, bytes) else k): v for k, v in raw.items()}
        if values and (int(values["limit"]) != capacity or values["unit"] not in (unit, unit.encode())):
            raise StorageUnavailable("budget configuration is inconsistent")
        return state(int(values.get("used", 0)), int(values.get("held", 0)))

    async def reserve(amount: int | float | Decimal, *, reservation_id: str | None = None) -> Reservation:
        weight = quantity(amount)
        identity = UUID(reservation_id).hex if reservation_id is not None else uuid4().hex
        for _ in range(3):
            try:
                clock = await redis.time()
            except (RedisError, OSError):
                raise StorageUnavailable("budget clock unavailable") from None
            day = int(clock[0]) // 86400
            result = await atomic(redis, _RESERVE, keys(day), [str(day), capacity, weight, identity, unit, _RETENTION])
            code = int(result[0])
            if code == -2:
                continue
            if code < 0:
                raise StorageUnavailable("budget configuration is inconsistent")
            if code == 0:
                raise BudgetExceeded("daily budget capacity is exhausted")
            status = result[1].decode() if isinstance(result[1], bytes) else str(result[1])
            return Reservation(identity, day, units(weight), scope, code == 2, status)
        raise StorageUnavailable("budget day changed during reservation")

    async def finish(reservation: Reservation, action: str, amount: int) -> BudgetState:
        if reservation.scope != scope or reservation.day < 0:
            raise ValueError("reservation belongs to another budget")
        result = await atomic(redis, _FINISH, keys(reservation.day), [reservation.id, action, amount, capacity, unit])
        code = int(result[0])
        if code == -4:
            raise StorageUnavailable("budget configuration is inconsistent")
        if code == -3:
            raise BudgetOverrun("actual usage exceeded reserved upper bound; budget blocked")
        if code < 0:
            raise ValueError("reservation expired, missing, or already settled differently")
        return state(int(result[1]), int(result[2]))

    async def commit(reservation: Reservation, actual: int | float | Decimal) -> BudgetState:
        return await finish(reservation, "committed", quantity(actual, zero=True))

    async def release(reservation: Reservation) -> BudgetState:
        return await finish(reservation, "released", 0)

    return Budget(snapshot=snapshot, reserve=reserve, commit=commit, release=release)
