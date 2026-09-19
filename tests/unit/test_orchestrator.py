import json
from typing import Any

from app.github.models import PullRequest, PullRequestRef, PullRequestWebhookPayload, Repository
from app.llm.schemas import LLMRequest, LLMResponse
from app.review.orchestrator import ReviewOrchestrator

SAMPLE_DIFF = (
    "diff --git a/app/foo.py b/app/foo.py\n"
    "index e69de29..4b825dc 100644\n"
    "--- a/app/foo.py\n"
    "+++ b/app/foo.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def foo():\n"
    "-    return 1\n"
    "+    return 2\n"
)


class FakeGitHubClient:
    def __init__(self, diff_text: str) -> None:
        self.diff_text = diff_text
        self.created_reviews: list[dict[str, Any]] = []

    async def get_pull_request_diff(self, repo_full_name: str, pr_number: int) -> str:
        return self.diff_text

    async def create_review(
        self,
        repo_full_name: str,
        pr_number: int,
        commit_id: str,
        summary: str,
        comments: list[dict[str, Any]],
        event: str = "COMMENT",
    ) -> dict[str, Any]:
        self.created_reviews.append(
            {
                "repo": repo_full_name,
                "pr_number": pr_number,
                "commit_id": commit_id,
                "summary": summary,
                "comments": comments,
            }
        )
        return {"id": 1}


class FakeLLMClient:
    def __init__(self, response_json: dict) -> None:
        self.response_json = response_json

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=json.dumps(self.response_json),
            input_tokens=10,
            output_tokens=10,
            model="fake-model",
        )


def make_payload(action: str = "opened") -> PullRequestWebhookPayload:
    return PullRequestWebhookPayload(
        action=action,
        number=1,
        pull_request=PullRequest(
            number=1,
            title="Fix bug",
            head=PullRequestRef(sha="abc123"),
            base=PullRequestRef(sha="def456"),
        ),
        repository=Repository(full_name="owner/repo"),
    )


async def test_review_pull_request_posts_line_comment_for_commentable_finding():
    github_client = FakeGitHubClient(SAMPLE_DIFF)
    llm_client = FakeLLMClient(
        {
            "findings": [
                {
                    "severity": "HIGH",
                    "category": "BUG",
                    "file": "app/foo.py",
                    "line": 2,
                    "title": "Off by one",
                    "description": "Return value changed without justification.",
                    "recommendation": "Verify intended behavior.",
                    "confidence": 0.9,
                }
            ]
        }
    )
    orchestrator = ReviewOrchestrator(github_client, llm_client)

    result = await orchestrator.review_pull_request(make_payload())

    assert len(result.findings) == 1
    assert len(github_client.created_reviews) == 1
    review = github_client.created_reviews[0]
    assert review["commit_id"] == "abc123"
    assert len(review["comments"]) == 1
    assert review["comments"][0]["path"] == "app/foo.py"
    assert review["comments"][0]["line"] == 2


async def test_review_pull_request_falls_back_to_summary_for_noncommentable_line():
    github_client = FakeGitHubClient(SAMPLE_DIFF)
    llm_client = FakeLLMClient(
        {
            "findings": [
                {
                    "severity": "LOW",
                    "category": "QUALITY",
                    "file": "app/foo.py",
                    "line": 999,
                    "title": "Unreachable line",
                    "description": "Line not part of the diff.",
                    "recommendation": "N/A",
                    "confidence": 0.5,
                }
            ]
        }
    )
    orchestrator = ReviewOrchestrator(github_client, llm_client)

    await orchestrator.review_pull_request(make_payload())

    review = github_client.created_reviews[0]
    assert review["comments"] == []
    assert "Unreachable line" in review["summary"]


async def test_review_pull_request_handles_empty_findings():
    github_client = FakeGitHubClient(SAMPLE_DIFF)
    llm_client = FakeLLMClient({"findings": []})
    orchestrator = ReviewOrchestrator(github_client, llm_client)

    result = await orchestrator.review_pull_request(make_payload())

    assert result.findings == []
    review = github_client.created_reviews[0]
    assert "no significant issues" in review["summary"].lower()
