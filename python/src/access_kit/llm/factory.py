"""Construct one provider from application configuration; no implicit fallback."""

import httpx

from access_kit.llm.providers import anthropic_provider, openai_compat_provider
from access_kit.llm.types import LLMProvider
from access_kit.settings import AccessKitSettings


def provider_from_settings(settings: AccessKitSettings, *, client: httpx.AsyncClient | None = None) -> LLMProvider:
    if not settings.llm_model or settings.llm_provider is None:
        raise ValueError("configure LLM_PROVIDER and LLM_MODEL explicitly")
    key = settings.llm_api_key.get_secret_value() if settings.llm_api_key is not None else None
    if settings.llm_provider == "anthropic":
        return anthropic_provider(api_key=key or "", model=settings.llm_model, base_url=settings.llm_base_url or "https://api.anthropic.com/v1", client=client)
    if settings.llm_provider == "omniroute" and (not settings.llm_base_url or not key):
        raise ValueError("OmniRoute requires an explicit base URL and API key")
    return openai_compat_provider(name=settings.llm_provider, model=settings.llm_model, base_url=settings.llm_base_url or "http://localhost:11434/v1", api_key=key, client=client)
