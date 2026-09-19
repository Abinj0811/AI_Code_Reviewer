"""GitHub webhook signature verification.

GitHub signs each webhook delivery with HMAC-SHA256 over the raw request
body, using the shared webhook secret. We must verify this before trusting
or processing the payload at all.
"""

import hashlib
import hmac


class InvalidSignatureError(Exception):
    """Raised when a webhook request's signature does not match."""


def verify_signature(payload_body: bytes, signature_header: str | None, secret: str) -> None:
    """Verify the `X-Hub-Signature-256` header for a webhook delivery.

    Raises InvalidSignatureError if the header is missing, malformed, or
    does not match the computed HMAC digest.
    """
    if not secret:
        raise InvalidSignatureError("Webhook secret is not configured")

    if not signature_header or not signature_header.startswith("sha256="):
        raise InvalidSignatureError("Missing or malformed signature header")

    expected_digest = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    expected_header = f"sha256={expected_digest}"

    if not hmac.compare_digest(expected_header, signature_header):
        raise InvalidSignatureError("Signature mismatch")
