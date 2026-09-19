"""Structured schemas for AI review findings.

Every LLM response must be validated against these models before it is
trusted or published. Never pass raw model output directly to GitHub.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class Category(StrEnum):
    BUG = "BUG"
    SECURITY = "SECURITY"
    QUALITY = "QUALITY"
    TEST = "TEST"
    PERFORMANCE = "PERFORMANCE"
    STYLE = "STYLE"


class Finding(BaseModel):
    severity: Severity
    category: Category
    file: str
    line: int | None = Field(
        default=None,
        description="1-indexed line number in the new version of the file, if known.",
    )
    title: str
    description: str
    recommendation: str
    confidence: float = Field(ge=0.0, le=1.0)


class ReviewResult(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
