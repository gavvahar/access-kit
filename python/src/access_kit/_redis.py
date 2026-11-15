"""Shared Redis script execution, bounded fixed-point quantities and key isolation."""

import hashlib
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from access_kit.errors import StorageUnavailable

SCALE = 1_000_000
CLOCK = "local t=redis.call('TIME'); local now=tonumber(t[1])*1000+math.floor(tonumber(t[2])/1000);\n"


def quantity(value: int | float | Decimal, *, zero: bool = False) -> int:
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ValueError("quantity must be a finite nonnegative number") from None
    if isinstance(value, bool) or not number.is_finite() or number < 0 or (not zero and number == 0) or number > 1_000_000_000:
        raise ValueError("quantity must be positive, finite, and at most one billion")
    return int((number * SCALE).to_integral_value(rounding=ROUND_CEILING))


def units(value: Any) -> Decimal:
    return Decimal(int(value)) / SCALE


def key_scope(name: str) -> str:
    if not name or len(name) > 1024:
        raise ValueError("provide a bounded nonempty namespace")
    return hashlib.sha256(name.encode()).hexdigest()


async def atomic(redis: Redis, script: str, keys: list[str], args: list[str | int]) -> list[Any]:
    try:
        result = await redis.eval(script, len(keys), *keys, *args)
    except (RedisError, OSError):
        raise StorageUnavailable("Redis operation failed") from None
    if not isinstance(result, list):
        raise StorageUnavailable("invalid Redis script response")
    return result
