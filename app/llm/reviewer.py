"""LLM-backed structured review generation.

Wraps the Anthropic SDK behind a narrow `LLMClient` protocol so review
logic never imports a provider SDK directly. This is a Phase 1 seam for
what becomes the full LLM Gateway (model routing, fallback, rate
limiting, cost tracking) in a later phase.
"""

import json
import logging
from typing import Protocol

from anthropic import AsyncAnthropic
from pydantic import ValidationError

from app.llm.schemas import LLMRequest, LLMResponse
from app.review.schemas import ReviewResult

logger = logging.getLogger(__name__)


class LLMReviewError(Exception):
    """Raised when the LLM cannot produce a valid structured review."""


class LLMClient(Protocol):
    async def complete(self, request: LLMRequest) -> LLMResponse: ...


class AnthropicLLMClient:
    """Thin async wrapper around the Anthropic Messages API."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete(self, request: LLMRequest) -> LLMResponse:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=request.max_tokens,
            system=request.system_prompt,
            messages=[{"role": "user", "content": request.user_prompt}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        return LLMResponse(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self._model,
        )


async def generate_structured_review(
    llm_client: LLMClient,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 4096,
) -> ReviewResult:
    """Call the LLM and parse/validate its response as a ReviewResult.

    Never trusts raw model output: on invalid JSON or a schema mismatch,
    retries once with the validation error fed back to the model. If
    that also fails, raises LLMReviewError instead of publishing
    unvalidated findings.
    """
    last_error = ""

    for attempt in range(2):
        prompt = user_prompt
        if attempt == 1:
            prompt = (
                f"{user_prompt}\n\n"
                "Your previous response was invalid JSON or did not match the "
                f"required schema. Error: {last_error}\n"
                "Return ONLY valid JSON matching the schema, with no extra text."
            )

        request = LLMRequest(system_prompt=system_prompt, user_prompt=prompt, max_tokens=max_tokens)
        response = await llm_client.complete(request)

        try:
            data = _extract_json(response.text)
            return ReviewResult.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = str(exc)
            logger.warning(
                "llm_response_validation_failed",
                extra={"event_data": {"attempt": attempt, "error": last_error}},
            )

    raise LLMReviewError(f"LLM did not return a valid ReviewResult after retry: {last_error}")


def _extract_json(text: str) -> dict:
    """Extract a JSON object from model output that may be wrapped in
    markdown code fences or surrounded by extra prose.
    """
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[len("json") :]
        text = text.strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise json.JSONDecodeError("No JSON object found in LLM response", text, 0)

    return json.loads(text[start : end + 1])
