"""Application configuration loaded from environment variables.

Centralizing configuration here keeps secrets and deployment settings out
of business logic, per the project's configuration guidelines.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings.

    All secrets (tokens, API keys) are read from the environment and must
    never be hardcoded or logged.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # GitHub
    github_token: str = ""
    github_webhook_secret: str = ""

    # LLM
    llm_provider: str = "anthropic"
    llm_api_key: str = ""
    llm_model: str = "claude-sonnet-5"

    # Cost / safety controls
    max_diff_chars: int = 60_000

    # Observability
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so the environment is only parsed once per process; tests can
    bypass this by constructing Settings() directly or clearing the cache.
    """
    return Settings()
