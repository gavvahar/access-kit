"""Anthropic Messages and OpenAI-compatible Ollama/OmniRoute adapters.

Models are explicit configuration, never hard-coded to a dated model ID.
The adapters use documented HTTP APIs and share no vendor SDK dependency.
"""

from typing import Literal

import httpx

from access_kit.llm.core import build_provider
from access_kit.llm.http import check_input, endpoint, post_json, token_count, validate_limits
from access_kit.llm.types import LLMError, LLMProvider, Usage, usage


def anthropic_provider(
    *,
    api_key: str,
    model: str,
    base_url: str = "https://api.anthropic.com/v1",
    max_tokens: int = 2048,
    max_input_tokens: int = 128_000,
    timeout: float = 60,
    json_retries: int = 2,
    client: httpx.AsyncClient | None = None,
) -> LLMProvider:
    """Claude Messages adapter. Cached input tokens count toward input usage."""
    if not api_key:
        raise ValueError("Anthropic API key is required")
    validate_limits(max_tokens, max_input_tokens, timeout)
    url = endpoint(base_url, "messages")

    async def complete_text(system: str, user: str) -> tuple[str, Usage]:
        check_input(system, user, max_input_tokens)
        data = await post_json(
            url,
            {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            {"model": model, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": user}]},
            client=client,
            timeout=timeout,
        )
        raw = data.get("usage")
        if not isinstance(raw, dict):
            raise LLMError("provider returned no token usage")
        tokens = usage(
            token_count(raw, "input_tokens") + token_count(raw, "cache_creation_input_tokens", default=0) + token_count(raw, "cache_read_input_tokens", default=0),
            token_count(raw, "output_tokens"),
        )
        blocks = data.get("content")
        if data.get("stop_reason") not in ("end_turn", "stop_sequence") or not isinstance(blocks, list) or not blocks:
            raise LLMError("provider returned incomplete or unsupported output", consumed=tokens)
        if any(not isinstance(block, dict) or block.get("type") != "text" or not isinstance(block.get("text"), str) for block in blocks):
            raise LLMError("provider returned non-text output", consumed=tokens)
        return "".join(block["text"] for block in blocks), tokens

    return build_provider(name="anthropic", model=model, complete_text=complete_text, max_input_tokens=max_input_tokens, json_retries=json_retries)


def openai_compat_provider(
    *,
    model: str,
    base_url: str,
    api_key: str | None = None,
    name: Literal["ollama", "omniroute", "openai_compat"] = "openai_compat",
    max_tokens: int = 2048,
    max_input_tokens: int = 128_000,
    timeout: float = 60,
    json_retries: int = 2,
    client: httpx.AsyncClient | None = None,
) -> LLMProvider:
    """Chat Completions adapter for a trusted configured gateway or local Ollama."""
    validate_limits(max_tokens, max_input_tokens, timeout)
    url = endpoint(base_url, "chat/completions")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    async def complete_text(system: str, user: str) -> tuple[str, Usage]:
        check_input(system, user, max_input_tokens)
        data = await post_json(
            url,
            headers,
            {"model": model, "max_tokens": max_tokens, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            client=client,
            timeout=timeout,
        )
        raw = data.get("usage")
        if not isinstance(raw, dict):
            raise LLMError("provider returned no token usage")
        tokens = usage(token_count(raw, "prompt_tokens"), token_count(raw, "completion_tokens"))
        choices = data.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise LLMError("provider returned invalid choices", consumed=tokens)
        choice = choices[0]
        message = choice.get("message")
        if (
            choice.get("finish_reason") != "stop"
            or not isinstance(message, dict)
            or not isinstance(message.get("content"), str)
            or message.get("refusal")
            or message.get("tool_calls")
        ):
            raise LLMError("provider returned incomplete or unsupported output", consumed=tokens)
        return message["content"], tokens

    return build_provider(name=name, model=model, complete_text=complete_text, max_input_tokens=max_input_tokens, json_retries=json_retries)
