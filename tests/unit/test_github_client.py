import pytest
import respx
from httpx import Response

from app.github.client import GitHubClient, GitHubClientError


@respx.mock
async def test_get_pull_request_diff_returns_text_on_success():
    respx.get("https://api.github.com/repos/owner/repo/pulls/1").mock(
        return_value=Response(200, text="diff --git a/x b/x\n")
    )
    client = GitHubClient(token="tok")

    diff = await client.get_pull_request_diff("owner/repo", 1)

    assert "diff --git" in diff


@respx.mock
async def test_get_pull_request_diff_raises_on_error_status():
    respx.get("https://api.github.com/repos/owner/repo/pulls/1").mock(
        return_value=Response(404, text="not found")
    )
    client = GitHubClient(token="tok")

    with pytest.raises(GitHubClientError):
        await client.get_pull_request_diff("owner/repo", 1)


@respx.mock
async def test_create_review_returns_json_on_success():
    route = respx.post("https://api.github.com/repos/owner/repo/pulls/1/reviews").mock(
        return_value=Response(200, json={"id": 123})
    )
    client = GitHubClient(token="tok")

    result = await client.create_review("owner/repo", 1, commit_id="sha", summary="ok", comments=[])

    assert result["id"] == 123
    assert route.called


@respx.mock
async def test_create_review_raises_on_error_status():
    respx.post("https://api.github.com/repos/owner/repo/pulls/1/reviews").mock(
        return_value=Response(422, text="validation failed")
    )
    client = GitHubClient(token="tok")

    with pytest.raises(GitHubClientError):
        await client.create_review("owner/repo", 1, commit_id="sha", summary="ok", comments=[])
