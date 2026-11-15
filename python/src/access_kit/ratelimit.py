"""Atomic Redis sliding-window limits with fractional weighted cost."""

import math
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import TypedDict
from uuid import uuid4

from fastapi import HTTPException, Request
from redis.asyncio import Redis

from access_kit.errors import StorageUnavailable
from access_kit._redis import CLOCK, atomic, key_scope, quantity, units

_SCRIPT = (
    CLOCK
    + """
local window=tonumber(ARGV[1]); local limit=tonumber(ARGV[2]); local cost=tonumber(ARGV[3]);
local maximum=tonumber(ARGV[5]);
local configured=redis.call('HGET',KEYS[3],'limit');
if configured and (tonumber(configured)~=limit or tonumber(redis.call('HGET',KEYS[3],'window'))~=window) then return {-2} end
if not configured and (redis.call('ZCARD',KEYS[1])>0 or redis.call('HLEN',KEYS[2])>0) then return {-2} end
local used=tonumber(redis.call('HGET',KEYS[3],'used') or '0');
local expired=redis.call('ZRANGEBYSCORE',KEYS[1],'-inf',now-window);
for _,id in ipairs(expired) do
 local weight=redis.call('HGET',KEYS[2],id); if not weight then return {-2} end
 used=used-tonumber(weight); redis.call('HDEL',KEYS[2],id);
end
redis.call('ZREMRANGEBYSCORE',KEYS[1],'-inf',now-window);
redis.call('HSET',KEYS[3],'used',string.format('%.0f',used),'limit',ARGV[2],'window',window);
local allowed=0; local retry=0;
if used+cost<=limit and redis.call('ZCARD',KEYS[1])<maximum then
 allowed=1; used=used+cost;
 redis.call('ZADD',KEYS[1],now,ARGV[4]); redis.call('HSET',KEYS[2],ARGV[4],ARGV[3]);
 redis.call('HSET',KEYS[3],'used',string.format('%.0f',used));
else
 local oldest=redis.call('ZRANGE',KEYS[1],0,0,'WITHSCORES');
 retry=window; if #oldest>0 then retry=math.max(1,tonumber(oldest[2])+window-now) end
end
for _,key in ipairs(KEYS) do redis.call('PEXPIRE',key,window+1) end
return {allowed,math.max(0,limit-used),retry}
"""
)


class LimitResult(TypedDict):
    allowed: bool
    remaining: Decimal
    retry_after: int


type Limiter = Callable[[str, int | float | Decimal], Awaitable[LimitResult]]


def make_limiter(redis: Redis, *, name: str, limit: int | float | Decimal, window: float = 60, max_events: int = 1000) -> Limiter:
    """Return check(identity, cost=1). Redis TIME defines the rolling window.

    All workers sharing a name must use the same limit/window. Identity should
    be a signed session ID or an HMAC IP identifier, not an untrusted header.
    Each accepted cost remains in the window; rejected requests add no weight.
    max_events independently bounds memory even for very small weighted costs.
    """
    capacity = quantity(limit)
    if not math.isfinite(window) or not 0.001 <= window <= 86400 or type(max_events) is not int or not 1 <= max_events <= 10_000:
        raise ValueError("window must be 0.001..86400 seconds and max_events 1..10000")
    scope = key_scope(name)
    milliseconds = math.ceil(window * 1000)

    async def check(identity: str, cost: int | float | Decimal = 1) -> LimitResult:
        weight = quantity(cost)
        if weight > capacity:
            return LimitResult(allowed=False, remaining=Decimal(0), retry_after=math.ceil(window))
        prefix = f"ak:rate:{{{scope}:{key_scope(identity)}}}"
        result = await atomic(redis, _SCRIPT, [prefix + suffix for suffix in (":events", ":costs", ":state")], [milliseconds, capacity, weight, uuid4().hex, max_events])
        if len(result) != 3 or int(result[0]) < 0:
            raise StorageUnavailable("rate limit configuration or state is inconsistent")
        return LimitResult(allowed=bool(result[0]), remaining=units(result[1]), retry_after=math.ceil(int(result[2]) / 1000))

    return check


def rate_limit_dependency(check: Limiter, identify: Callable[[Request], Awaitable[str]], *, cost: int | float | Decimal = 1) -> Callable[[Request], Awaitable[None]]:
    """FastAPI dependency. Unavailable Redis produces 503, never an allow."""
    quantity(cost)

    async def require(request: Request) -> None:
        try:
            result = await check(await identify(request), cost)
        except StorageUnavailable:
            raise HTTPException(503, "Rate limiting temporarily unavailable") from None
        if not result["allowed"]:
            raise HTTPException(429, "Too many requests", headers={"Retry-After": str(result["retry_after"])})

    return require
