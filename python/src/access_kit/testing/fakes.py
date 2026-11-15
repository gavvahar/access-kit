"""Deterministic provider fakes that run the real JSON retry/validation logic."""

from collections import deque
from collections.abc import Sequence
from typing import NamedTuple

from access_kit.llm.core import build_provider
from access_kit.llm.types import LLMError, LLMProvider, Usage, usage


class LLMCall(NamedTuple):
    system: str
    user: str


def fake_llm(responses: Sequence[str | LLMError], *, tokens: Usage | None = None, json_retries: int = 2) -> tuple[LLMProvider, list[LLMCall]]:
    """Return (provider, recorded calls). Exhausted responses fail explicitly.

    Calls intentionally retain prompts in test memory. Never use this fake or
    its call records for production logs or real user data.
    """
    pending = deque(responses)
    calls: list[LLMCall] = []
    consumed = tokens if tokens is not None else usage(1, 1)

    async def complete_text(system: str, user: str) -> tuple[str, Usage]:
        calls.append(LLMCall(system, user))
        if not pending:
            raise LLMError("fake provider has no remaining responses", consumed=usage())
        result = pending.popleft()
        if isinstance(result, LLMError):
            raise result
        return result, consumed.copy()

    return build_provider(name="fake", model="fake-model", complete_text=complete_text, json_retries=json_retries), calls
