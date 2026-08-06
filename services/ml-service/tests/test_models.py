"""Tests for GET /models.

Uses a temp directory + monkeypatch on settings.models_dir rather than
depending on the real ml/models directory being present - that
directory is gitignored/local-only (real trained model files aren't
committed to the repo), so a test that required it would only pass on
a machine that happened to have already trained models locally.
"""

import json


def _write_metadata(models_dir, name, **fields):
    (models_dir / f"{name}.metadata.json").write_text(json.dumps(fields))


def test_list_models_returns_models_with_required_raw_metrics(
    client, auth_headers, tmp_path, monkeypatch
):
    monkeypatch.setattr("app.routers.models.settings.models_dir", str(tmp_path))
    _write_metadata(
        tmp_path,
        "simulated_condenser_fouling",
        required_raw_metrics=["RTU_REFG_COND_PRES", "RTU_OA_TEMP"],
        status="Usable",
        algorithm="random_forest",
        dataset="simulated",
    )

    response = client.get("/models", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["model_name"] == "simulated_condenser_fouling"
    assert body[0]["required_raw_metrics"] == ["RTU_REFG_COND_PRES", "RTU_OA_TEMP"]
    assert body[0]["status"] == "Usable"
    assert body[0]["algorithm"] == "random_forest"


def test_list_models_skips_a_model_missing_required_raw_metrics_but_returns_the_rest(
    client, auth_headers, tmp_path, monkeypatch
):
    """One malformed metadata file shouldn't take down visibility into
    every other model - a partial result, not an all-or-nothing 500."""
    monkeypatch.setattr("app.routers.models.settings.models_dir", str(tmp_path))
    _write_metadata(tmp_path, "good_model", required_raw_metrics=["RTU_OA_TEMP"])
    _write_metadata(tmp_path, "bad_model", algorithm="random_forest")  # no required_raw_metrics

    response = client.get("/models", headers=auth_headers)
    assert response.status_code == 200
    model_names = [m["model_name"] for m in response.json()]
    assert model_names == ["good_model"]


def test_list_models_returns_empty_list_when_models_dir_does_not_exist(
    client, auth_headers, tmp_path, monkeypatch
):
    monkeypatch.setattr("app.routers.models.settings.models_dir", str(tmp_path / "does-not-exist"))
    response = client.get("/models", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_models_requires_auth(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.models.settings.models_dir", str(tmp_path))
    response = client.get("/models")
    assert response.status_code in (401, 403)
