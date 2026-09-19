"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api.routes.webhook import router as webhook_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="AI Code Reviewer",
    description="Automated AI-powered review for GitHub Pull Requests.",
    version="0.1.0",
)

app.include_router(webhook_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
