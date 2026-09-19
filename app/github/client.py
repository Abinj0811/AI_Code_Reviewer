"""Minimal async GitHub REST API client.

Wraps only what Phase 1 needs: fetching a PR's diff and publishing a
review. Kept behind this interface so callers never depend on `httpx`
directly, and so this can later be swapped for a GitHub App client
without touching the orchestrator.
"""

from typing import Any

import httpx

GITHUB_API_BASE = "https://api.github.com"


class GitHubClientError(Exception):
    """Raised when the GitHub API returns an unexpected response."""


class GitHubClient:
    def __init__(self, token: str, base_url: str = GITHUB_API_BASE) -> None:
        self._token = token
        self._base_url = base_url

    def _headers(self, accept: str = "application/vnd.github+json") -> dict[str, str]:
        headers = {
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def get_pull_request_diff(self, repo_full_name: str, pr_number: int) -> str:
        """Fetch the raw unified diff for a pull request."""
        url = f"{self._base_url}/repos/{repo_full_name}/pulls/{pr_number}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url, headers=self._headers(accept="application/vnd.github.v3.diff")
            )
        if response.status_code != 200:
            raise GitHubClientError(
                f"Failed to fetch PR diff ({response.status_code}): {response.text[:500]}"
            )
        return response.text

    async def create_review(
        self,
        repo_full_name: str,
        pr_number: int,
        commit_id: str,
        summary: str,
        comments: list[dict[str, Any]],
        event: str = "COMMENT",
    ) -> dict[str, Any]:
        """Publish a PR review with a summary body and optional line comments.

        `comments` entries must be dicts shaped like
        {"path": str, "line": int, "body": str} — each `line` must refer
        to a line actually present in the PR diff or GitHub will reject it.
        """
        url = f"{self._base_url}/repos/{repo_full_name}/pulls/{pr_number}/reviews"
        payload: dict[str, Any] = {
            "commit_id": commit_id,
            "body": summary,
            "event": event,
            "comments": comments,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
        if response.status_code not in (200, 201):
            raise GitHubClientError(
                f"Failed to create review ({response.status_code}): {response.text[:500]}"
            )
        return response.json()
