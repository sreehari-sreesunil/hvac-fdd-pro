from common.schemas import ErrorResponse


def test_error_response_defaults() -> None:
    err = ErrorResponse(detail="Something went wrong")
    assert err.detail == "Something went wrong"
    assert err.error_code is None
