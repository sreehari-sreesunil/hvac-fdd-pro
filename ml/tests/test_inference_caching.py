"""Tests for load_model's caching behavior (ml/src/models/inference.py)."""

import json

import joblib
from src.models.inference import _model_cache, load_model


def _write_fake_model(models_dir, name, model_obj, metadata):
    joblib.dump(model_obj, models_dir / f"{name}.joblib")
    (models_dir / f"{name}.metadata.json").write_text(json.dumps(metadata))


def setup_function():
    """Clear the module-level cache before each test - otherwise a
    model_name reused across tests (e.g. "fake_model") could hit an
    earlier test's cache entry and mask a real bug."""
    _model_cache.clear()


def test_second_call_returns_the_same_cached_object_not_a_fresh_load(tmp_path):
    """The core behavior this cache exists for: loading the same model
    twice should return the identical object the second time, not read
    the file from disk again."""
    _write_fake_model(tmp_path, "fake_model", {"fake": "model"}, {"status": "Usable"})

    model1, metadata1 = load_model("fake_model", tmp_path)
    model2, metadata2 = load_model("fake_model", tmp_path)

    assert model1 is model2, "expected the exact same cached object, not a fresh load"
    assert metadata1 is metadata2


def test_different_models_dir_does_not_return_a_stale_cross_directory_result(tmp_path):
    """The real correctness case the cache key was designed around: two
    different directories, same model_name, must NOT share a cache
    entry - this is exactly the scenario the test suite itself hits
    (different tests monkeypatch models_dir to different tmp_path
    directories)."""
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    _write_fake_model(dir_a, "fake_model", {"source": "a"}, {"status": "from_a"})
    _write_fake_model(dir_b, "fake_model", {"source": "b"}, {"status": "from_b"})

    model_a, metadata_a = load_model("fake_model", dir_a)
    model_b, metadata_b = load_model("fake_model", dir_b)

    assert metadata_a["status"] == "from_a"
    assert metadata_b["status"] == "from_b"
    assert model_a is not model_b


def test_cached_metadata_is_correct_not_just_present(tmp_path):
    """A cache that returns SOMETHING isn't enough - it must be the
    actual correct data, unchanged by caching."""
    real_metadata = {
        "required_raw_metrics": ["RTU_OA_TEMP", "RTU_STG_STA"],
        "status": "Usable",
        "algorithm": "random_forest",
    }
    _write_fake_model(tmp_path, "fake_model", {"weights": [1, 2, 3]}, real_metadata)

    _, metadata = load_model("fake_model", tmp_path)
    _, metadata_cached = load_model("fake_model", tmp_path)

    assert metadata == real_metadata
    assert metadata_cached == real_metadata
