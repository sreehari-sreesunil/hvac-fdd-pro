from datetime import datetime, timedelta

from jose import jwt

from common.security import decode_and_verify_token

SECRET = "test-secret"


def _make_token(sub: str, token_type: str, expired: bool = False) -> str:
    exp = datetime.utcnow() + (timedelta(minutes=-5) if expired else timedelta(minutes=30))
    return jwt.encode({"sub": sub, "type": token_type, "exp": exp}, SECRET, algorithm="HS256")


def test_valid_access_token_returns_subject() -> None:
    token = _make_token("user-123", "access")
    assert decode_and_verify_token(token, SECRET, expected_type="access") == "user-123"


def test_wrong_token_type_returns_none() -> None:
    token = _make_token("user-123", "refresh")
    assert decode_and_verify_token(token, SECRET, expected_type="access") is None


def test_expired_token_returns_none() -> None:
    token = _make_token("user-123", "access", expired=True)
    assert decode_and_verify_token(token, SECRET, expected_type="access") is None


def test_garbage_token_returns_none() -> None:
    assert decode_and_verify_token("not-a-real-token", SECRET, expected_type="access") is None
