"""Exercise real Redis atomic admission and job replay without paid services.

Run: python scripts/check_redis_load.py redis://127.0.0.1:6379/0
Only this run's randomly named keys are deleted. Redis 7+ is required.
"""

import argparse
import asyncio
from uuid import uuid4
from decimal import Decimal

from redis.asyncio import Redis

from access_kit.budget import BudgetExceeded, make_budget
from access_kit.jobs import make_jobs
from access_kit.ratelimit import make_limiter


async def check(url: str) -> None:
    identifier = uuid4().hex
    redis = Redis.from_url(url, max_connections=256)
    # Separate clients model independent workers rather than a process-local lock.
    workers = [Redis.from_url(url, max_connections=256) for _ in range(4)]
    names = [f"load-{identifier}-{index}" for index in range(4)]
    try:
        for unit in ("tokens", "minutes"):
            budgets = [make_budget(worker, name=f"load-{identifier}-{unit}", limit=100, unit=unit) for worker in workers]

            async def attempt(index: int, budgets=budgets) -> bool:
                budget = budgets[index % len(budgets)]
                try:
                    receipt = await budget["reserve"](3)
                except BudgetExceeded:
                    return False
                await asyncio.sleep(0)
                state = await budget["commit"](receipt, 3)
                assert state["used"] + state["held"] <= 100
                return True

            results = await asyncio.gather(*(attempt(index) for index in range(1000)))
            assert sum(results) == 33, results
            state = await budgets[0]["snapshot"]()
            assert state["used"] == 99 and state["held"] == 0
            print(f"{unit}: 1000 requests / 4 clients; 33 admitted, used=99, held=0, cap=100")
        limits = [make_limiter(worker, name=names[0], limit=10) for worker in workers]
        results = await asyncio.gather(*(limits[index % 4]("session", 0.5) for index in range(200)))
        assert sum(result["allowed"] for result in results) == 20
        jobs = make_jobs(redis, name=names[1])
        first = await jobs["create"]("owner", total=1)
        await jobs["update"]("owner", first["id"], completed=1, label="Ready", status="complete")
        assert await jobs["get"]("other-owner", first["id"]) is None
        replay = [event async for event in jobs["events"]("owner", first["id"], after=first["event_id"])]
        assert len(replay) == 1 and replay[0]["status"] == "complete"
        precision = make_budget(redis, name=names[2], limit=Decimal("999999999.000001"))
        receipt = await precision["reserve"](Decimal("999999998.000001"))
        assert (await precision["snapshot"]())["held"] == receipt.amount
        assert (await precision["reserve"](receipt.amount, reservation_id=receipt.id)).replayed
        await precision["commit"](receipt, receipt.amount)
        assert (await precision["snapshot"]())["used"] == receipt.amount
        print("Weighted limits, exact micro-unit accounting, job ownership and terminal replay passed on real Redis.")
    finally:
        # Match hashes of our namespace only, never delete another client's keys.
        from access_kit._redis import key_scope

        scopes = [key_scope(name) for name in [*names, f"load-{identifier}-tokens", f"load-{identifier}-minutes"]]
        owned = [key async for key in redis.scan_iter(match="ak:*") if any(scope.encode() in key for scope in scopes)]
        if owned:
            await redis.delete(*owned)
        await asyncio.gather(redis.aclose(), *(worker.aclose() for worker in workers))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    asyncio.run(check(parser.parse_args().url))


if __name__ == "__main__":
    main()
