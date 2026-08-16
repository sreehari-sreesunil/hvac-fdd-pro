"""Tests for the diagnose_fault tool executor.

Mocks httpx.AsyncClient with URL-based dispatch, since this executor
makes three sequential calls to different ml-service endpoints (list
models, run attribution, explain the winner) - each test configures
which fake response each URL returns, then asserts on both the
combined result AND (where it matters) which calls actually happened,
not just the final output.

Uses asyncio.run() rather than @pytest.mark.asyncio - pytest-asyncio
isn't configured for this service (confirmed, not assumed), matching
the same pattern already established elsewhere this session for
testing async functions directly without adding a new dependency.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.tools.executors import diagnose_fault

MODELS_URL = "http://unused-in-tests:8003/models"
ATTRIBUTE_URL = "http://unused-in-tests:8003/predictions/asset-1/attribute"
EXPLAIN_URL = "http://unused-in-tests:8003/predictions/asset-1/explain"


def _fake_response(status_code, json_body):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    return resp


def _mock_client_returning(url_to_response):
    """A mock httpx.AsyncClient whose .get() returns a different fake
    response depending on which URL (prefix-matched) was requested."""
    mock_client = AsyncMock()

    async def _get(url, **kwargs):
        for prefix, response in url_to_response.items():
            if url.startswith(prefix):
                return response
        raise AssertionError(f"Unexpected URL requested in test: {url}")

    mock_client.get.side_effect = _get
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    return mock_client


def test_full_success_combines_attribution_and_explanation():
    models = [{"model_name": "simulated_condenser_fouling"}, {"model_name": "simulated_overcharge"}]
    attribution = {
        "asset_id": "asset-1",
        "models_evaluated": ["simulated_condenser_fouling", "simulated_overcharge"],
        "models_skipped": [],
        "fault_detected": True,
        "attributed_model": "simulated_condenser_fouling",
        "attributed_fault_probability": 0.94,
        "all_results": [
            {
                "model_name": "simulated_condenser_fouling",
                "predicted_label": 1,
                "fault_probability": 0.94,
                "confidence": "high",
            }
        ],
    }
    explanation = {
        "model": "simulated_condenser_fouling",
        "feature_contributions": [
            {"feature": "RTU_REFG_COND_PRES_residual", "value": 3.1, "shap_contribution": 0.4}
        ],
    }

    mock_client = _mock_client_returning(
        {
            MODELS_URL: _fake_response(200, models),
            ATTRIBUTE_URL: _fake_response(200, attribution),
            EXPLAIN_URL: _fake_response(200, explanation),
        }
    )

    with patch("app.tools.executors.httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(diagnose_fault("asset-1", "fake-token"))

    assert result["fault_detected"] is True
    assert result["attributed_model"] == "simulated_condenser_fouling"
    assert result["attributed_fault_probability"] == 0.94
    assert result["feature_contributions"] == explanation["feature_contributions"]
    assert "explanation_error" not in result


def test_no_fault_detected_does_not_call_explain():
    """If attribution finds no fault, explaining a non-existent 'winner'
    would be meaningless - explain must never be called in this case."""
    models = [{"model_name": "simulated_condenser_fouling"}]
    attribution = {
        "asset_id": "asset-1",
        "models_evaluated": ["simulated_condenser_fouling"],
        "models_skipped": [],
        "fault_detected": False,
        "attributed_model": None,
        "attributed_fault_probability": None,
        "all_results": [],
    }

    mock_client = _mock_client_returning(
        {
            MODELS_URL: _fake_response(200, models),
            ATTRIBUTE_URL: _fake_response(200, attribution),
            # Deliberately no EXPLAIN_URL entry - if diagnose_fault
            # calls it anyway, the test's own _get dispatcher will
            # raise AssertionError("Unexpected URL requested").
        }
    )

    with patch("app.tools.executors.httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(diagnose_fault("asset-1", "fake-token"))

    assert result["fault_detected"] is False


def test_no_models_evaluated_gives_an_honest_insufficient_data_summary():
    """Real bug fixed here: when EVERY model is skipped (missing metric
    mappings, not evaluated at all), the summary must say so plainly -
    not the generic 'no fault was detected' text, which reads as 'ran
    diagnostics, unit is fine' when the true state is 'we don't have
    enough sensor data to run diagnostics at all'. Found live during a
    walkthrough with a genuinely new asset."""
    models = [{"model_name": "simulated_condenser_fouling"}]
    attribution = {
        "asset_id": "asset-1",
        "models_evaluated": [],
        "models_skipped": [
            {
                "model_name": "simulated_condenser_fouling",
                "reason": "Asset asset-1's asset type is missing metric definitions for: "
                "['RTU_REFG_COND_PRES', 'RTU_REFG_COND_TEMP']. Add these metrics to the "
                "asset type before requesting a prediction that requires them.",
            }
        ],
        "fault_detected": False,
        "attributed_model": None,
        "attributed_fault_probability": None,
        "all_results": [],
    }

    mock_client = _mock_client_returning(
        {
            MODELS_URL: _fake_response(200, models),
            ATTRIBUTE_URL: _fake_response(200, attribution),
        }
    )

    with patch("app.tools.executors.httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(diagnose_fault("asset-1", "fake-token"))

    assert result["fault_detected"] is False
    assert result["models_evaluated"] == []
    assert len(result["models_skipped"]) == 1
    assert "no fault was detected" not in result["summary"].lower()
    assert "missing" in result["summary"].lower()
    assert "feature_contributions" not in result


def test_models_list_failure_returns_error_without_further_calls():
    mock_client = _mock_client_returning({MODELS_URL: _fake_response(503, {})})

    with patch("app.tools.executors.httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(diagnose_fault("asset-1", "fake-token"))

    assert "error" in result
    assert "503" in result["error"]


def test_attribution_failure_returns_error():
    models = [{"model_name": "simulated_condenser_fouling"}]
    mock_client = _mock_client_returning(
        {
            MODELS_URL: _fake_response(200, models),
            ATTRIBUTE_URL: _fake_response(500, {}),
        }
    )

    with patch("app.tools.executors.httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(diagnose_fault("asset-1", "fake-token"))

    assert "error" in result
    assert "500" in result["error"]


def test_explanation_failure_still_returns_the_real_attribution_result():
    """A secondary failure (explain) must not discard a real, useful
    result (attribution) that already succeeded."""
    models = [{"model_name": "simulated_condenser_fouling"}]
    attribution = {
        "asset_id": "asset-1",
        "models_evaluated": ["simulated_condenser_fouling"],
        "models_skipped": [],
        "fault_detected": True,
        "attributed_model": "simulated_condenser_fouling",
        "attributed_fault_probability": 0.9,
        "all_results": [],
    }

    mock_client = _mock_client_returning(
        {
            MODELS_URL: _fake_response(200, models),
            ATTRIBUTE_URL: _fake_response(200, attribution),
            EXPLAIN_URL: _fake_response(500, {}),
        }
    )

    with patch("app.tools.executors.httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(diagnose_fault("asset-1", "fake-token"))

    assert result["fault_detected"] is True
    assert result["attributed_model"] == "simulated_condenser_fouling"
    assert "explanation_error" in result
    assert "feature_contributions" not in result
