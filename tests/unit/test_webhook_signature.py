import hashlib
import hmac

import pytest

from app.github.webhook import InvalidSignatureError, verify_signature


def _sign(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_verify_signature_accepts_valid_signature():
    body = b'{"key": "value"}'
    secret = "topsecret"
    verify_signature(body, _sign(secret, body), secret)  # should not raise


def test_verify_signature_rejects_missing_header():
    with pytest.raises(InvalidSignatureError):
        verify_signature(b"{}", None, "secret")


def test_verify_signature_rejects_wrong_secret():
    body = b"{}"
    header = _sign("secret-a", body)
    with pytest.raises(InvalidSignatureError):
        verify_signature(body, header, "secret-b")


def test_verify_signature_rejects_malformed_header():
    with pytest.raises(InvalidSignatureError):
        verify_signature(b"{}", "not-sha256=abc", "secret")


def test_verify_signature_rejects_when_secret_not_configured():
    with pytest.raises(InvalidSignatureError):
        verify_signature(b"{}", "sha256=abc", "")
