"""Tests for prediction persistence (GET /predictions/{asset_id}).

build_buffer, load_model, and predict are all mocked - this test isn't
about re-proving the inference pipeline works (that's proven separately
via SHAP/prediction live-testing against real trained models), it's
about the genuinely new behavior added here: does a Prediction row
actually get written to the database with the right fields, for both
the classifier and anomaly-detector response shapes.
"""

import json
from unittest.mock import AsyncMock, patch

from app.db.session import Base, SessionLocal, engine
from app.models.prediction import Prediction


def _write_fake_metadata(models_dir, model_name):
    (models_dir / f"{model_name}.metadata.json").write_text(
        json.dumps({"required_raw_metrics": ["RTU_OA_TEMP"], "status": "Usable"})
    )


def _setup_db():
    Base.metadata.create_all(bind=engine)


def _teardown_db():
    Base.metadata.drop_all(bind=engine)


def test_classifier_prediction_is_persisted_with_correct_fields(
    client, auth_headers, mock_asset_access, tmp_path, monkeypatch
):
    _setup_db()
    try:
        monkeypatch.setattr("app.routers.predictions.settings.models_dir", str(tmp_path))
        _write_fake_metadata(tmp_path, "fake_classifier")

        fake_result = {
            "model": "fake_classifier",
            "status": "Usable",
            "notes": "",
            "feature_values": {"RTU_OA_TEMP_residual": 3.14},
            "fault_probability": 0.91,
            "predicted_label": "fault",
            "confidence": "high",
        }

        with (
            patch("app.routers.predictions.build_buffer", new_callable=AsyncMock),
            patch(
                "app.routers.predictions.load_model",
                return_value=(None, {"required_raw_metrics": ["RTU_OA_TEMP"]}),
            ),
            patch("app.routers.predictions.predict", return_value=fake_result),
        ):
            response = client.get(
                "/predictions/asset-1",
                params={"model_name": "fake_classifier"},
                headers=auth_headers,
            )

        assert response.status_code == 200

        db = SessionLocal()
        rows = db.query(Prediction).filter(Prediction.asset_id == "asset-1").all()
        db.close()

        assert len(rows) == 1
        row = rows[0]
        assert row.model_name == "fake_classifier"
        assert row.predicted_label == "fault"
        assert row.fault_probability == 0.91
        assert row.confidence == "high"
        assert row.is_anomaly is None
        assert row.anomaly_score is None
        assert row.feature_values == {"RTU_OA_TEMP_residual": 3.14}
    finally:
        _teardown_db()


def test_anomaly_detector_prediction_is_persisted_with_correct_fields(
    client, auth_headers, mock_asset_access, tmp_path, monkeypatch
):
    """The anomaly-detector response shape (is_anomaly/anomaly_score) is
    genuinely different from the classifier shape - both must persist
    correctly, not just whichever one was tested first."""
    _setup_db()
    try:
        monkeypatch.setattr("app.routers.predictions.settings.models_dir", str(tmp_path))
        _write_fake_metadata(tmp_path, "fake_gatekeeper")

        fake_result = {
            "model": "fake_gatekeeper",
            "status": "Usable",
            "notes": "",
            "feature_values": {"RTU_OA_TEMP_residual": 1.02},
            "is_anomaly": True,
            "anomaly_score": -0.15,
        }

        with (
            patch("app.routers.predictions.build_buffer", new_callable=AsyncMock),
            patch(
                "app.routers.predictions.load_model",
                return_value=(None, {"required_raw_metrics": ["RTU_OA_TEMP"]}),
            ),
            patch("app.routers.predictions.predict", return_value=fake_result),
        ):
            response = client.get(
                "/predictions/asset-1",
                params={"model_name": "fake_gatekeeper"},
                headers=auth_headers,
            )

        assert response.status_code == 200

        db = SessionLocal()
        row = db.query(Prediction).filter(Prediction.asset_id == "asset-1").first()
        db.close()

        assert row.is_anomaly is True
        assert row.anomaly_score == -0.15
        assert row.predicted_label is None
        assert row.fault_probability is None
    finally:
        _teardown_db()


def test_response_body_is_unchanged_by_persistence(
    client, auth_headers, mock_asset_access, tmp_path, monkeypatch
):
    """Persistence is purely additive - the endpoint's response contract
    (what predict() returns) must be identical to before this change."""
    _setup_db()
    try:
        monkeypatch.setattr("app.routers.predictions.settings.models_dir", str(tmp_path))
        _write_fake_metadata(tmp_path, "fake_model")

        fake_result = {
            "model": "fake_model",
            "status": "Usable",
            "notes": "some notes",
            "feature_values": {"x": 1.0},
            "fault_probability": 0.5,
            "predicted_label": "no_fault",
            "confidence": "moderate",
        }

        with (
            patch("app.routers.predictions.build_buffer", new_callable=AsyncMock),
            patch(
                "app.routers.predictions.load_model",
                return_value=(None, {"required_raw_metrics": ["RTU_OA_TEMP"]}),
            ),
            patch("app.routers.predictions.predict", return_value=fake_result),
        ):
            response = client.get(
                "/predictions/asset-1",
                params={"model_name": "fake_model"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert response.json() == fake_result
    finally:
        _teardown_db()
