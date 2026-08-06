"""Tests for GET /predictions/{asset_id}/attribute.

_run_and_persist_prediction is mocked (not build_buffer/load_model/
predict individually, since it's now the single extracted helper both
GET /predictions/{asset_id} and this endpoint call) - these tests are
about the argmax comparison logic itself, which is the genuinely new
part, not re-proving the inference pipeline (already covered by
test_prediction_persistence.py and real live testing).
"""

from unittest.mock import patch

from fastapi import HTTPException


def _classifier_result(predicted_label, fault_probability, confidence="high"):
    return {
        "model": "irrelevant",
        "status": "Usable",
        "notes": "",
        "feature_values": {},
        "predicted_label": predicted_label,
        "fault_probability": fault_probability,
        "confidence": confidence,
    }


def _anomaly_result():
    return {
        "model": "irrelevant",
        "status": "Usable",
        "notes": "",
        "feature_values": {},
        "is_anomaly": True,
        "anomaly_score": -0.2,
    }


def test_attributes_fault_to_the_highest_probability_classifier_among_those_that_fired(
    client, auth_headers, mock_asset_access
):
    """The real problem this endpoint fixes: three classifiers all
    claim the same event. condenser_fouling has the highest probability
    among the ones that actually predicted a fault - it should win, not
    whichever happened to be listed first."""

    async def fake_run(asset_id, model_name, token, db):
        return {
            "condenser_fouling": _classifier_result(1, 0.94),
            "liquidline_restriction": _classifier_result(1, 0.72),
            "overcharge": _classifier_result(1, 0.65),
        }[model_name]

    with patch("app.routers.predictions._run_and_persist_prediction", side_effect=fake_run):
        response = client.get(
            "/predictions/asset-1/attribute",
            params={"model_names": ["condenser_fouling", "liquidline_restriction", "overcharge"]},
            headers=auth_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["fault_detected"] is True
    assert body["attributed_model"] == "condenser_fouling"
    assert body["attributed_fault_probability"] == 0.94
    assert len(body["all_results"]) == 3


def test_no_fault_detected_when_zero_classifiers_predict_a_fault(
    client, auth_headers, mock_asset_access
):
    """Must be reported honestly - not silently picking the
    least-unlikely non-fault result as if it were a real attribution."""

    async def fake_run(asset_id, model_name, token, db):
        return _classifier_result(0, 0.03)

    with patch("app.routers.predictions._run_and_persist_prediction", side_effect=fake_run):
        response = client.get(
            "/predictions/asset-1/attribute",
            params={"model_names": ["model_a", "model_b"]},
            headers=auth_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["fault_detected"] is False
    assert body["attributed_model"] is None
    assert body["attributed_fault_probability"] is None


def test_a_higher_probability_non_fault_result_does_not_beat_a_lower_probability_fault_result(
    client, auth_headers, mock_asset_access
):
    """The exact bug the docstring warns against: a model that
    correctly says 'no fault, 40% probability' must NOT win against a
    model that says 'fault, 30% probability' just because 40 > 30 -
    argmax only applies among models that actually predicted a fault."""

    async def fake_run(asset_id, model_name, token, db):
        return {
            "confident_no_fault": _classifier_result(0, 0.40),
            "weak_fault": _classifier_result(1, 0.30),
        }[model_name]

    with patch("app.routers.predictions._run_and_persist_prediction", side_effect=fake_run):
        response = client.get(
            "/predictions/asset-1/attribute",
            params={"model_names": ["confident_no_fault", "weak_fault"]},
            headers=auth_headers,
        )

    body = response.json()
    assert body["fault_detected"] is True
    assert body["attributed_model"] == "weak_fault"


def test_anomaly_detector_model_is_skipped_with_a_clear_reason(
    client, auth_headers, mock_asset_access
):
    """A model with no fault_probability (e.g. the Isolation Forest
    gatekeeper) doesn't fit the argmax comparison - skipped, not
    silently ignored or crashing the request."""

    async def fake_run(asset_id, model_name, token, db):
        return {
            "classifier": _classifier_result(1, 0.8),
            "gatekeeper": _anomaly_result(),
        }[model_name]

    with patch("app.routers.predictions._run_and_persist_prediction", side_effect=fake_run):
        response = client.get(
            "/predictions/asset-1/attribute",
            params={"model_names": ["classifier", "gatekeeper"]},
            headers=auth_headers,
        )

    body = response.json()
    assert body["attributed_model"] == "classifier"
    assert len(body["models_skipped"]) == 1
    assert body["models_skipped"][0]["model_name"] == "gatekeeper"


def test_one_failing_model_does_not_fail_the_whole_request(client, auth_headers, mock_asset_access):
    """Matches this project's established partial-success philosophy -
    one bad model_name shouldn't take down a comparison across several
    others that are fine."""

    async def fake_run(asset_id, model_name, token, db):
        if model_name == "does_not_exist":
            raise HTTPException(status_code=404, detail="No saved model named 'does_not_exist'")
        return _classifier_result(1, 0.85)

    with patch("app.routers.predictions._run_and_persist_prediction", side_effect=fake_run):
        response = client.get(
            "/predictions/asset-1/attribute",
            params={"model_names": ["real_model", "does_not_exist"]},
            headers=auth_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["attributed_model"] == "real_model"
    assert len(body["models_skipped"]) == 1
    assert "does_not_exist" in body["models_skipped"][0]["reason"]
