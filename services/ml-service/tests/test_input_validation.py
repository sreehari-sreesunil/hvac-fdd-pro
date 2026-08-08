"""Tests for model_name's input validation - a real path-traversal-
adjacent finding from this project's input validation audit.

model_name gets interpolated directly into a file path
(models_dir / f"{model_name}.metadata.json") and passed to
joblib.load() (pickle deserialization). These tests prove FastAPI's
Query(pattern=...) constraint actually rejects a malicious value
BEFORE it ever reaches route logic - not just that the pattern exists
in the code, since query-param pattern validation for list[str] (used
by attribute_fault) is a less common case worth confirming directly
rather than assuming it behaves the same as the scalar str case.
"""

MALICIOUS_MODEL_NAMES = [
    "../../../etc/passwd",
    "../../secrets",
    "model/with/slashes",
    "model with spaces",
    "model;rm -rf",
]


def test_get_prediction_rejects_a_path_traversal_model_name(
    client, auth_headers, mock_asset_access
):
    for bad_name in MALICIOUS_MODEL_NAMES:
        response = client.get(
            "/predictions/asset-1", params={"model_name": bad_name}, headers=auth_headers
        )
        assert response.status_code == 422, f"expected 422 for malicious model_name={bad_name!r}"


def test_get_prediction_accepts_a_real_looking_model_name_at_the_validation_layer(
    client, auth_headers, mock_asset_access
):
    """A well-formed name must pass query validation (not be rejected
    with 422) - it may still 404 further in because no such model
    actually exists in this test's models_dir, and that's fine; this
    test only proves the validation layer itself isn't over-strict."""
    response = client.get(
        "/predictions/asset-1",
        params={"model_name": "simulated_condenser_fouling"},
        headers=auth_headers,
    )
    assert response.status_code != 422


def test_attribute_fault_rejects_a_path_traversal_model_name_in_the_list(
    client, auth_headers, mock_asset_access
):
    """The less-common case: model_names is a list[str] query param
    (?model_names=a&model_names=b) - confirms per-item validation is
    actually applied (via manual re.match, not Query(pattern=), which
    crashes with a 500 for list types - see attribute_fault's
    docstring for why)."""
    response = client.get(
        "/predictions/asset-1/attribute",
        params={"model_names": ["simulated_condenser_fouling", "../../../etc/passwd"]},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_explain_rejects_a_path_traversal_model_name(client, auth_headers, mock_asset_access):
    response = client.get(
        "/predictions/asset-1/explain",
        params={"model_name": "../../../etc/passwd"},
        headers=auth_headers,
    )
    assert response.status_code == 422
