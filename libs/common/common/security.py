from jose import JWTError, jwt


def decode_and_verify_token(
    token: str, secret_key: str, algorithm: str = "HS256", expected_type: str = "access"
) -> str | None:
    """
    Retruns the subject (user id) if the token is valid and of the expected
    type, else None. Every service that needs to know 'who is making this
    request' calls this - but only auth-service issues tokens.
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        if payload.get("type") != expected_type:
            return None
        subject = payload.get("sub")
        return str(subject) if subject is not None else None
    except JWTError:
        return None
