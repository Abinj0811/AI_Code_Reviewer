"""GitHub webhook endpoint.

Receives `pull_request` events, verifies the webhook signature, and runs
the review pipeline synchronously. Background/queued processing is a
later phase (see CLAUDE.md Phase 6) — for Phase 1 the request simply
awaits the full review before responding.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import ValidationError

from app.api.dependencies import get_orchestrator
from app.core.config import Settings, get_settings
from app.github.models import REVIEWABLE_ACTIONS, PullRequestWebhookPayload
from app.github.webhook import InvalidSignatureError, verify_signature
from app.review.orchestrator import ReviewOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    orchestrator: ReviewOrchestrator = Depends(get_orchestrator),
) -> dict[str, str]:
    body = await request.body()

    try:
        verify_signature(body, x_hub_signature_256, settings.github_webhook_secret)
    except InvalidSignatureError as exc:
        raise HTTPException(status_code=401, detail="Invalid webhook signature") from exc

    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": f"unsupported event: {x_github_event}"}

    try:
        payload = PullRequestWebhookPayload.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid payload") from exc

    if payload.action not in REVIEWABLE_ACTIONS:
        return {"status": "ignored", "reason": f"unsupported action: {payload.action}"}

    try:
        review_result = await orchestrator.review_pull_request(payload)
    except Exception:
        logger.exception("review_pipeline_failed")
        raise HTTPException(status_code=502, detail="Review pipeline failed") from None

    return {"status": "reviewed", "finding_count": str(len(review_result.findings))}
