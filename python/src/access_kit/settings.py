"""Environment-backed settings that applications can extend."""

from typing import Literal

from pydantic import Field, HttpUrl, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AccessKitSettings(BaseSettings):
    """Required application configuration; no secrets are generated implicitly.

    Load process environment by default. Apps can opt into a dotenv file with
    ``Settings(_env_file=".env")``. Only trust Cloudflare headers when the origin
    is restricted to verified Cloudflare connections.
    """

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore", hide_input_in_errors=True)

    app_name: str = Field(min_length=1)
    env: Literal["dev", "test", "prod"] = "dev"
    public_base_url: HttpUrl
    redis_url: RedisDsn = Field(repr=False)
    session_secret: SecretStr = Field(min_length=32)
    ip_hash_salt: SecretStr = Field(min_length=32)
    trust_cloudflare_headers: bool = False

    llm_provider: Literal["anthropic", "ollama", "omniroute"] | None = None
    llm_model: str | None = None
    llm_base_url: str | None = Field(default=None, repr=False)
    llm_api_key: SecretStr | None = None
