"""Opt-in pytest fixtures. Install access-kit[testing] to use them.

In your conftest.py: pytest_plugins = ["access_kit.testing.fixtures"]
"""

from collections.abc import AsyncIterator

import pytest_asyncio
from fakeredis.aioredis import FakeRedis


@pytest_asyncio.fixture
async def fake_redis() -> AsyncIterator[FakeRedis]:
    client = FakeRedis(decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()
