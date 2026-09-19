"""Request/response types exchanged between review logic and the LLM client.

Kept separate from any provider SDK so review logic never depends on a
specific model SDK directly (see CLAUDE.md's LLM Gateway design
principle). In a later phase this seam becomes the full LLM Gateway
(model routing, fallback, rate limiting, cost tracking); for Phase 1 it
is intentionally minimal.
"""

from pydantic import BaseModel


class LLMRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    max_tokens: int = 4096


class LLMResponse(BaseModel):
    text: str
    input_tokens: int
    output_tokens: int
    model: str
