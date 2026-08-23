"""Tests for application configuration."""

from manufacturing_mcp.config import Settings


def test_settings_have_safe_defaults(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.openai_model == "gpt-5-mini"
    assert settings.openai_embedding_model == "text-embedding-3-small"
    assert settings.openai_api_key is None
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_settings_read_environment_without_exposing_secret(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")

    settings = Settings(_env_file=None)

    assert settings.openai_api_key is not None
    assert settings.openai_api_key.get_secret_value() == "test-secret"
    assert "test-secret" not in repr(settings.openai_api_key)
