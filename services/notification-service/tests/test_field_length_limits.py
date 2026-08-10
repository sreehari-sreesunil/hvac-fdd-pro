"""Tests for max_length input validation on notification-service's
schemas - part of this project's input validation audit (previously
zero max_length constraints existed anywhere in this codebase).
"""


def test_create_alert_rejects_a_message_over_2000_characters(client):
    response = client.post(
        "/alerts",
        headers={"X-Internal-Api-Key": "test-internal-key"},
        json={
            "asset_id": "asset-1",
            "source": "baseline_deviation",
            "severity": "warning",
            "message": "a" * 2001,
        },
    )
    assert response.status_code == 422


def test_create_alert_rejects_a_source_over_255_characters(client):
    response = client.post(
        "/alerts",
        headers={"X-Internal-Api-Key": "test-internal-key"},
        json={
            "asset_id": "asset-1",
            "source": "a" * 256,
            "severity": "warning",
            "message": "A real alert message.",
        },
    )
    assert response.status_code == 422


def test_create_alert_still_works_normally_under_the_limit(client):
    """Positive control - proves the limits above aren't accidentally
    rejecting normal, well-formed input."""
    response = client.post(
        "/alerts",
        headers={"X-Internal-Api-Key": "test-internal-key"},
        json={
            "asset_id": "asset-1",
            "source": "baseline_deviation",
            "severity": "warning",
            "message": "Reading deviated from baseline.",
        },
    )
    assert response.status_code == 201
