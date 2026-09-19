"""FastAPI dependency providers.

Centralizes construction of the GitHub client, LLM client, and
orchestrator so routes stay thin and tests can override these easily.
"""

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.github.client import GitHubClient
from app.llm.reviewer import AnthropicLLMClient, LLMClient
from app.review.orchestrator import ReviewOrchestrator


def get_github_client(settings: Settings | None = None) -> GitHubClient:
    settings = settings or get_settings()
    return GitHubClient(token=settings.github_token)


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    return AnthropicLLMClient(api_key=settings.llm_api_key, model=settings.llm_model)


@lru_cache
def get_orchestrator() -> ReviewOrchestrator:
    settings = get_settings()
    return ReviewOrchestrator(
        github_client=get_github_client(settings),
        llm_client=get_llm_client(settings),
        max_diff_chars=settings.max_diff_chars,
    )
