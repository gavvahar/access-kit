"""Configuration must fail early and keep secrets out of representations."""

import pytest
from pydantic import ValidationError

from access_kit.settings import AccessKitSettings


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in AccessKitSettings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def configured_env(monkeypatch):
    values = {
        "APP_NAME": "ClearRead",
        "PUBLIC_BASE_URL": "https://clearread.example",
        "REDIS_URL": "redis://:private-password@localhost:6379/0",
        "SESSION_SECRET": "session-secret-" + "x" * 32,
        "IP_HASH_SALT": "hash-salt-" + "y" * 32,
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return values


def test_missing_configuration_fails():
    with pytest.raises(ValidationError) as error:
        AccessKitSettings()
    assert {item["loc"][0] for item in error.value.errors()} == {"app_name", "public_base_url", "redis_url", "session_secret", "ip_hash_salt"}


def test_environment_and_secret_representation(configured_env):
    settings = AccessKitSettings()
    assert settings.app_name == "ClearRead"
    assert settings.env == "dev"
    assert settings.trust_cloudflare_headers is False
    assert settings.session_secret.get_secret_value() == configured_env["SESSION_SECRET"]
    for secret in (configured_env["SESSION_SECRET"], configured_env["IP_HASH_SALT"], "private-password"):
        assert secret not in repr(settings)


@pytest.mark.parametrize(
    "key,value",
    [
        ("PUBLIC_BASE_URL", "file:///etc/passwd"),
        ("REDIS_URL", "https://example.com"),
        ("SESSION_SECRET", "tiny-secret-123"),
        ("IP_HASH_SALT", ""),
        ("APP_NAME", ""),
        ("ENV", "production-typo"),
    ],
)
def test_invalid_environment_fails(configured_env, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(ValidationError) as error:
        AccessKitSettings()
    assert value not in str(error.value) or value == ""


def test_application_can_extend_settings(configured_env, monkeypatch):
    class ClearReadSettings(AccessKitSettings):
        max_document_pages: int = 100

    monkeypatch.setenv("MAX_DOCUMENT_PAGES", "25")
    assert ClearReadSettings().max_document_pages == 25


def test_dotenv_is_opt_in(configured_env, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("APP_NAME=SoundSight\nUNRELATED_APP_OPTION=true\n")
    monkeypatch.delenv("APP_NAME")
    with pytest.raises(ValidationError):
        AccessKitSettings()
    assert AccessKitSettings(_env_file=".env").app_name == "SoundSight"
