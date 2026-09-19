"""Pydantic models for the subset of GitHub webhook payloads we use.

Only the fields Phase 1 actually needs are modeled; GitHub payloads are
much larger than this, but we should not couple to more than we use.
"""

from pydantic import BaseModel, ConfigDict


class Repository(BaseModel):
    model_config = ConfigDict(extra="ignore")

    full_name: str  # e.g. "owner/repo"


class PullRequestRef(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sha: str


class PullRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    number: int
    title: str = ""
    head: PullRequestRef
    base: PullRequestRef


class PullRequestWebhookPayload(BaseModel):
    """Payload for the `pull_request` webhook event.

    We only care about actions that mean "there is new/updated code to
    review": opened, reopened, and synchronize (new commits pushed).
    """

    model_config = ConfigDict(extra="ignore")

    action: str
    number: int
    pull_request: PullRequest
    repository: Repository


REVIEWABLE_ACTIONS = {"opened", "reopened", "synchronize"}
