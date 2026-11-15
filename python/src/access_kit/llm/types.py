"""Provider callables and accumulated token usage; no prompt data in errors."""

from collections.abc import Awaitable, Callable
from typing import Any, TypedDict


class Usage(TypedDict):
    input_tokens: int
    output_tokens: int
    total_tokens: int


def usage(input_tokens: int = 0, output_tokens: int = 0) -> Usage:
    if type(input_tokens) is not int or type(output_tokens) is not int or min(input_tokens, output_tokens) < 0:
        raise ValueError("token counts must be nonnegative integers")
    return Usage(input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=input_tokens + output_tokens)


def add_usage(left: Usage, right: Usage) -> Usage:
    return usage(left["input_tokens"] + right["input_tokens"], left["output_tokens"] + right["output_tokens"])


class LLMError(Exception):
    """Provider failure with any known billable usage, never raw provider output."""

    def __init__(self, message: str, *, consumed: Usage | None = None) -> None:
        super().__init__(message)
        self.usage = consumed if consumed is not None else usage()


class LLMValidationError(LLMError):
    """All JSON validation attempts failed."""


class LLMFallbackError(LLMError):
    """Every explicitly configured provider failed."""

    def __init__(self, errors: tuple[LLMError, ...]) -> None:
        consumed = usage()
        for error in errors:
            consumed = add_usage(consumed, error.usage)
        super().__init__("all configured providers failed", consumed=consumed)
        self.errors = errors


type CompleteText = Callable[[str, str], Awaitable[tuple[str, Usage]]]
type CompleteJSON = Callable[[str, str, Any], Awaitable[tuple[Any, Usage]]]


class LLMProvider(TypedDict):
    name: str
    model: str
    max_input_tokens: int
    complete_text: CompleteText
    complete_json: CompleteJSON
