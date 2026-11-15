"""Schema validation, bounded JSON retries, and explicit fallback chains."""

import json
from collections.abc import Sequence
from typing import Any

from pydantic import TypeAdapter, ValidationError

from access_kit.llm.types import CompleteText, LLMError, LLMFallbackError, LLMProvider, LLMValidationError, Usage, add_usage, usage


def build_provider(*, name: str, model: str, complete_text: CompleteText, max_input_tokens: int = 128_000, json_retries: int = 2) -> LLMProvider:
    """Add common JSON behavior to a provider's text completion callable.

    Retries apply only to invalid JSON/schema output, not transport errors.
    Usage includes every attempt, including attempts that failed validation.
    Schema validation is strict: strings are not coerced to integers.
    """
    if not name or not model or type(max_input_tokens) is not int or max_input_tokens <= 0 or type(json_retries) is not int or not 0 <= json_retries <= 5:
        raise ValueError("provider name/model and positive limits are required; retries must be 0..5")

    async def complete_json(system: str, user: str, schema: Any) -> tuple[Any, Usage]:
        adapter: TypeAdapter[Any] = TypeAdapter(schema)
        instruction = "\nReturn only JSON matching this schema: " + json.dumps(adapter.json_schema(), separators=(",", ":"))
        consumed = usage()
        for attempt in range(json_retries + 1):
            prompt = user + instruction + ("\nThe previous answer failed validation. Try again." if attempt else "")
            try:
                text, tokens = await complete_text(system, prompt)
            except LLMError as error:
                raise LLMError("provider failed during JSON completion", consumed=add_usage(consumed, error.usage)) from None
            consumed = add_usage(consumed, tokens)
            try:
                return adapter.validate_json(text, strict=True), consumed
            except (ValidationError, ValueError):
                pass
        raise LLMValidationError("JSON output failed schema validation after all attempts", consumed=consumed)

    return LLMProvider(name=name, model=model, max_input_tokens=max_input_tokens, complete_text=complete_text, complete_json=complete_json)


def with_fallback(providers: Sequence[LLMProvider]) -> LLMProvider:
    """Try providers in order. Fallback sends prompts to additional providers.

    No fallback is enabled implicitly. Applications must explicitly opt in to
    sending the same prompt to each provider. Known usage is accumulated across
    failures and the successful attempt. Unknown transport-side usage stays unknown.
    """
    chain = tuple(providers)
    if not chain:
        raise ValueError("at least one provider is required")

    async def call(method: str, args: tuple[Any, ...]) -> tuple[Any, Usage]:
        errors: list[LLMError] = []
        consumed = usage()
        for provider in chain:
            try:
                if method == "text":
                    result, tokens = await provider["complete_text"](*args)
                else:
                    result, tokens = await provider["complete_json"](*args)
                return result, add_usage(consumed, tokens)
            except LLMError as error:
                errors.append(error)
                consumed = add_usage(consumed, error.usage)
        raise LLMFallbackError(tuple(errors))

    async def complete_text(system: str, user: str) -> tuple[str, Usage]:
        result, tokens = await call("text", (system, user))
        return str(result), tokens

    async def complete_json(system: str, user: str, schema: Any) -> tuple[Any, Usage]:
        return await call("json", (system, user, schema))

    return LLMProvider(
        name="fallback", model=chain[0]["model"], max_input_tokens=min(p["max_input_tokens"] for p in chain), complete_text=complete_text, complete_json=complete_json
    )
