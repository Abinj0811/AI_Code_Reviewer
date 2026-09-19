import hashlib
import hmac
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_orchestrator
from app.core.config import Settings, get_settings
from app.github.models import PullRequestWebhookPayload
from app.main import app
from app.review.schemas import ReviewResult

WEBHOOK_SECRET = "test-secret"

PR_PAYLOAD = {
    "action": "opened",
    "number": 1,
    "pull_request": {
        "number": 1,
        "title": "Add feature",
        "head": {"sha": "abc123"},
        "base": {"sha": "def456"},
    },
    "repository": {"full_name": "owner/repo"},
}


class FakeOrchestrator:
    def __init__(self, result: ReviewResult) -> None:
        self.result = result
        self.received_payloads: list[PullRequestWebhookPayload] = []

    async def review_pull_request(self, payload: PullRequestWebhookPayload) -> ReviewResult:
        self.received_payloads.append(payload)
        return self.result


def _sign(body: bytes) -> str:
    digest = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _override_settings() -> Settings:
    return Settings(github_webhook_secret=WEBHOOK_SECRET)


@pytest.fixture
def fake_orchestrator() -> FakeOrchestrator:
    return FakeOrchestrator(ReviewResult(findings=[]))


@pytest.fixture
def client(fake_orchestrator: FakeOrchestrator):
    app.dependency_overrides[get_settings] = _override_settings
    app.dependency_overrides[get_orchestrator] = lambda: fake_orchestrator
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _post(client: TestClient, payload: dict[str, Any], event: str = "pull_request") -> Any:
    body = json.dumps(payload).encode()
    return client.post(
        "/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": _sign(body),
            "X-GitHub-Event": event,
            "Content-Type": "application/json",
        },
    )


def test_webhook_valid_signature_runs_review(client, fake_orchestrator):
    response = _post(client, PR_PAYLOAD)

    assert response.status_code == 200
    assert response.json()["status"] == "reviewed"
    assert len(fake_orchestrator.received_payloads) == 1


def test_webhook_rejects_invalid_signature(client):
    body = json.dumps(PR_PAYLOAD).encode()
    response = client.post(
        "/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": "sha256=" + "0" * 64,
            "X-GitHub-Event": "pull_request",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 401


def test_webhook_ignores_non_pull_request_event(client, fake_orchestrator):
    response = _post(client, PR_PAYLOAD, event="ping")

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    assert fake_orchestrator.received_payloads == []


def test_webhook_ignores_unreviewable_action(client, fake_orchestrator):
    payload = {**PR_PAYLOAD, "action": "closed"}

    response = _post(client, payload)

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    assert fake_orchestrator.received_payloads == []


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
