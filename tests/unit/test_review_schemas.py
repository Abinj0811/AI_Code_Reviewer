import pytest
from pydantic import ValidationError

from app.review.schemas import Category, Finding, ReviewResult, Severity


def test_finding_accepts_valid_data():
    finding = Finding(
        severity=Severity.HIGH,
        category=Category.SECURITY,
        file="a.py",
        line=1,
        title="t",
        description="d",
        recommendation="r",
        confidence=0.8,
    )
    assert finding.severity == Severity.HIGH
    assert finding.category == Category.SECURITY


def test_finding_rejects_invalid_severity():
    with pytest.raises(ValidationError):
        Finding(
            severity="NOT_A_SEVERITY",
            category=Category.BUG,
            file="a.py",
            line=1,
            title="t",
            description="d",
            recommendation="r",
            confidence=0.5,
        )


def test_finding_rejects_confidence_out_of_range():
    with pytest.raises(ValidationError):
        Finding(
            severity=Severity.LOW,
            category=Category.STYLE,
            file="a.py",
            line=None,
            title="t",
            description="d",
            recommendation="r",
            confidence=1.5,
        )


def test_finding_line_is_optional():
    finding = Finding(
        severity=Severity.INFO,
        category=Category.QUALITY,
        file="a.py",
        title="t",
        description="d",
        recommendation="r",
        confidence=0.5,
    )
    assert finding.line is None


def test_review_result_parses_nested_findings():
    data = {
        "findings": [
            {
                "severity": "MEDIUM",
                "category": "QUALITY",
                "file": "b.py",
                "line": 10,
                "title": "t",
                "description": "d",
                "recommendation": "r",
                "confidence": 0.6,
            }
        ]
    }
    result = ReviewResult.model_validate(data)
    assert len(result.findings) == 1
    assert result.findings[0].file == "b.py"


def test_review_result_defaults_to_empty_findings():
    result = ReviewResult()
    assert result.findings == []
