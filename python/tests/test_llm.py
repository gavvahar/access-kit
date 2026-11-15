"""Provider wire contracts, strict JSON retries, usage and explicit fallback."""

import asyncio
import json
from typing import TypedDict

import httpx
import pytest
import pytest_asyncio

from access_kit.llm.core import with_fallback
from access_kit.llm.factory import provider_from_settings
from access_kit.llm.http import endpoint
from access_kit.llm.providers import anthropic_provider, openai_compat_provider
from access_kit.llm.types import LLMError, LLMFallbackError, LLMValidationError, usage
from access_kit.testing.fakes import fake_llm
from conftest import stream_response

Payload = TypedDict("Payload", {"count": int})


@pytest_asyncio.fixture
async def gateway():
    pending, calls = [], []

    async def handler(request):
        calls.append(request)
        item = pending.pop(0)
        if isinstance(item, Exception):
            raise item
        if callable(item):
            return await item(request)
        if isinstance(item, httpx.Response):
            return item
        return stream_response(json.dumps(item).encode(), headers={"content-type": "application/json"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        yield client, pending, calls


def provider(kind, client, **kwargs):
    common = dict(model="configured-model", client=client, **kwargs)
    if kind == "anthropic":
        return anthropic_provider(api_key="test-only", base_url="https://llm.example/v1", **common)
    return openai_compat_provider(base_url="https://llm.example/v1", name=kind, api_key="test-only", **common)


def response(kind, text="answer", **overrides):
    if kind == "anthropic":
        data = {
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 4, "cache_creation_input_tokens": 2, "cache_read_input_tokens": 3},
        }
    else:
        data = {"choices": [{"message": {"content": text}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 15, "completion_tokens": 4}}
    return {**data, **overrides}


@pytest.mark.parametrize("kind", ["anthropic", "ollama", "omniroute"])
async def test_wire_contract_and_token_usage(kind, gateway):
    client, pending, calls = gateway
    pending.append(response(kind))
    llm = provider(kind, client)
    text, consumed = await llm["complete_text"]("system instruction", "user text")
    assert text == "answer"
    assert consumed == usage(15, 4)
    request = calls[0]
    payload = json.loads(request.content)
    assert payload["model"] == "configured-model"
    assert payload["max_tokens"] == 2048
    if kind == "anthropic":
        assert request.url.path == "/v1/messages"
        assert request.headers["x-api-key"] == "test-only"
        assert payload["system"] == "system instruction"
        assert payload["messages"] == [{"role": "user", "content": "user text"}]
    else:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-only"
        assert payload["messages"][0]["role"] == "system"
    assert not client.is_closed


@pytest.mark.parametrize("kind", ["anthropic", "ollama"])
async def test_real_adapter_json_retry_and_usage(kind, gateway):
    client, pending, calls = gateway
    pending.extend([response(kind, "not JSON"), response(kind, '{"count":2}')])
    result, consumed = await provider(kind, client)["complete_json"]("system", "user", Payload)
    assert result == {"count": 2}
    assert consumed == usage(30, 8)
    assert len(calls) == 2
    assert b"previous answer failed validation" in calls[1].content


async def test_json_retries_are_strict_and_exhaustion_keeps_usage():
    llm, calls = fake_llm(['{"count":"2"}', "```json\n{}\n```", "{}"], tokens=usage(3, 2))
    with pytest.raises(LLMValidationError) as error:
        await llm["complete_json"]("private system", "private prompt", Payload)
    assert error.value.usage == usage(9, 6)
    assert len(calls) == 3
    assert "private" not in str(error.value)


async def test_provider_error_during_json_retry_is_not_silently_retried():
    llm, calls = fake_llm(["bad", LLMError("offline", consumed=usage(2, 1)), '{"count":1}'])
    with pytest.raises(LLMError) as error:
        await llm["complete_json"]("", "", Payload)
    assert error.value.usage == usage(3, 2)
    assert len(calls) == 2


async def test_explicit_fallback_keeps_known_failed_usage():
    failed, _ = fake_llm([LLMError("unavailable", consumed=usage(5, 2))])
    success, _ = fake_llm(["done"], tokens=usage(7, 3))
    result, consumed = await with_fallback([failed, success])["complete_text"]("system", "user")
    assert result == "done"
    assert consumed == usage(12, 5)


async def test_json_fallback_and_all_provider_failure():
    first, _ = fake_llm(["invalid"], json_retries=0)
    second, _ = fake_llm(['{"count":4}'])
    assert (await with_fallback([first, second])["complete_json"]("", "", Payload))[0] == {"count": 4}
    with pytest.raises(LLMFallbackError) as error:
        await with_fallback([first, second])["complete_text"]("", "")
    assert len(error.value.errors) == 2
    assert error.value.usage == usage()
    with pytest.raises(ValueError):
        with_fallback([])


@pytest.mark.parametrize(
    "kind,override",
    [
        ("anthropic", {"stop_reason": "max_tokens"}),
        ("anthropic", {"content": []}),
        ("anthropic", {"content": [{"type": "tool_use"}]}),
        ("ollama", {"choices": []}),
        ("ollama", {"choices": [{"finish_reason": "length", "message": {"content": "partial"}}]}),
        ("ollama", {"choices": [{"finish_reason": "stop", "message": {"content": "", "refusal": "refused"}}]}),
    ],
)
async def test_partial_refused_or_unsupported_output_preserves_usage(kind, override, gateway):
    client, pending, _ = gateway
    pending.append(response(kind, **override))
    with pytest.raises(LLMError) as error:
        await provider(kind, client)["complete_text"]("", "")
    assert error.value.usage == usage(15, 4)


@pytest.mark.parametrize(
    "raw", [None, {}, {"prompt_tokens": -1, "completion_tokens": 1}, {"prompt_tokens": True, "completion_tokens": 1}, {"prompt_tokens": "10", "completion_tokens": 1}]
)
@pytest.mark.parametrize("kind", ["anthropic", "ollama"])
async def test_missing_or_invalid_usage_is_rejected(raw, kind, gateway):
    client, pending, _ = gateway
    pending.append(response(kind, usage=raw))
    with pytest.raises(LLMError):
        await provider(kind, client)["complete_text"]("", "")


@pytest.mark.parametrize(
    "item",
    [
        httpx.ConnectError("secret URL"),
        httpx.ReadTimeout("secret URL"),
        stream_response(status=302, headers={"location": "https://other.example"}),
        stream_response(b"not-json"),
        stream_response(b"[]"),
        stream_response(b"x" * 1_000_001),
        stream_response(headers={"content-encoding": "gzip"}),
    ],
)
async def test_transport_errors_are_sanitized_and_redirects_not_followed(item, gateway):
    client, pending, calls = gateway
    pending.append(item)
    with pytest.raises(LLMError) as error:
        await provider("ollama", client)["complete_text"]("sensitive system", "sensitive prompt")
    assert not any(value in str(error.value) for value in ("secret", "sensitive", "not-json"))
    assert len(calls) == 1


async def test_model_timeout_is_bounded(gateway):
    client, pending, _ = gateway

    async def slow(request):
        await asyncio.sleep(10)

    pending.append(slow)
    with pytest.raises(LLMError):
        await provider("ollama", client, timeout=0.01)["complete_text"]("", "")


async def test_input_limit_checked_before_http(gateway):
    client, _, calls = gateway
    with pytest.raises(LLMError):
        await provider("ollama", client, max_input_tokens=1024)["complete_text"]("", "x")
    assert calls == []


@pytest.mark.parametrize("kwargs", [{"max_tokens": 0}, {"max_input_tokens": -1}, {"timeout": float("nan")}, {"timeout": 0}, {"json_retries": 6}, {"model": ""}])
def test_invalid_provider_configuration(kwargs):
    with pytest.raises(ValueError):
        openai_compat_provider(base_url="https://example.com/v1", **({"model": "configured"} | kwargs))
    with pytest.raises(ValueError):
        anthropic_provider(api_key="", model="configured")


@pytest.mark.parametrize(
    "url", ["http://remote.example/v1", "file:///etc/passwd", "https://example.com?q=secret", "https://example.com#fragment", "https://" + "user:password" + "@example.com"]
)
def test_provider_base_url_validation(url):
    with pytest.raises(ValueError):
        endpoint(url, "messages")


@pytest.mark.parametrize("kind", ["anthropic", "ollama", "omniroute"])
def test_settings_factory(kind, kit_settings):
    kit_settings.llm_provider = kind
    kit_settings.llm_model = "configured-model"
    if kind != "ollama":
        from pydantic import SecretStr

        kit_settings.llm_api_key = SecretStr("test-only")
        kit_settings.llm_base_url = "https://gateway.example/v1"
    assert provider_from_settings(kit_settings)["name"] == kind


def test_factory_requires_explicit_configuration(kit_settings):
    with pytest.raises(ValueError):
        provider_from_settings(kit_settings)
    kit_settings.llm_provider, kit_settings.llm_model = "omniroute", "model"
    with pytest.raises(ValueError):
        provider_from_settings(kit_settings)


async def test_optional_redis_fixture(fake_redis):
    await fake_redis.set("job", "pending")
    assert await fake_redis.get("job") == "pending"


async def test_fake_records_calls_and_refuses_exhaustion():
    llm, calls = fake_llm(["answer"])
    assert (await llm["complete_text"]("instructions", "question"))[0] == "answer"
    assert calls[0].user == "question"
    with pytest.raises(LLMError):
        await llm["complete_text"]("", "")


async def test_owned_http_client_is_closed(monkeypatch):
    raw = json.dumps(response("ollama")).encode()
    owned = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: stream_response(raw)))
    monkeypatch.setattr("access_kit.llm.http.httpx.AsyncClient", lambda **kwargs: owned)
    llm = openai_compat_provider(model="configured", base_url="http://localhost:11434/v1")
    assert (await llm["complete_text"]("", ""))[0] == "answer"
    assert owned.is_closed


@pytest.mark.parametrize("counts", [(-1, 0), (0, -1), (True, 1)])
def test_usage_refuses_invalid_counts(counts):
    with pytest.raises(ValueError):
        usage(*counts)


async def test_unknown_transport_usage_stays_incomplete_after_fallback():
    failed, _ = fake_llm([LLMError("connection reset")])
    success, _ = fake_llm(["answer"])
    _, consumed = await with_fallback([failed, success])["complete_text"]("", "")
    assert consumed["input_tokens"] == 1
    assert consumed["complete"] is False
