"""Tests for GET /reports/{facility_id}.

verify_facility_access, get_facility_assets, and get_asset_ingestion_count
are all mocked - see conftest.py's mock_facility_access fixture and the
patches below - so these tests run without a live asset-service or
telemetry-service, same approach asset-service's own tests already use
for verify_org_membership. These tests are about the aggregation logic
itself (the genuinely new code in this router), not re-proving the auth
pattern, which already mirrors verify_asset_access exactly.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.db.session import SessionLocal
from app.models.alert import Alert

FAKE_ASSETS = [
    {"id": "asset-1", "name": "RTU-1"},
    {"id": "asset-2", "name": "RTU-2"},
]


def _make_alert(**overrides):
    """Build an Alert with sane defaults, so each test only needs to
    specify the fields it actually cares about."""
    defaults = {
        "id": overrides.pop("id", None) or f"alert-{datetime.utcnow().timestamp()}",
        "asset_id": "asset-1",
        "source": "baseline_deviation",
        "severity": "warning",
        "status": "open",
        "message": "test alert",
        "created_at": datetime(2026, 8, 5, 12, 0, 0),
    }
    defaults.update(overrides)
    return Alert(**defaults)


def _patched_report_deps(assets=FAKE_ASSETS, ingestion_counts=None):
    """Patches both cross-service calls the report router makes -
    get_facility_assets and get_asset_ingestion_count - so a test can
    control both without any real network call. ingestion_counts, if
    given, is a dict of {asset_id: count}; defaults to 0 for every
    asset in `assets` if not specified for a test that doesn't care
    about this field."""
    ingestion_counts = ingestion_counts or {}

    async def _fake_ingestion_count(asset_id, start, end, token):
        return ingestion_counts.get(asset_id, 0)

    assets_patch = patch("app.routers.reports.get_facility_assets", new_callable=AsyncMock)
    ingestion_patch = patch(
        "app.routers.reports.get_asset_ingestion_count", side_effect=_fake_ingestion_count
    )
    return assets_patch, ingestion_patch, assets


def test_report_aggregates_alerts_across_all_assets_in_the_period(client, mock_facility_access):
    """The core case: two assets, several alerts inside the window with
    different severities/statuses/sources, aggregated correctly."""
    db = SessionLocal()
    db.add_all(
        [
            _make_alert(
                id="a1",
                asset_id="asset-1",
                severity="critical",
                status="open",
                source="baseline_deviation",
            ),
            _make_alert(
                id="a2",
                asset_id="asset-1",
                severity="warning",
                status="acknowledged",
                source="baseline_deviation",
            ),
            _make_alert(
                id="a3",
                asset_id="asset-2",
                severity="warning",
                status="open",
                source="threshold_breach",
            ),
        ]
    )
    db.commit()
    db.close()

    assets_patch, ingestion_patch, assets = _patched_report_deps()
    with assets_patch as mock_get_assets, ingestion_patch:
        mock_get_assets.return_value = assets
        response = client.get(
            "/reports/facility-1?period=daily&date=2026-08-05",
            headers={"Authorization": "Bearer irrelevant-mocked-out"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["asset_count"] == 2
    assert body["alerts"]["total"] == 3
    assert body["alerts"]["by_severity"] == {"critical": 1, "warning": 2}
    assert body["alerts"]["by_status"] == {"open": 2, "acknowledged": 1}
    assert body["alerts"]["by_source"] == {"baseline_deviation": 2, "threshold_breach": 1}

    per_asset = {row["asset_id"]: row["alert_count"] for row in body["per_asset"]}
    assert per_asset == {"asset-1": 2, "asset-2": 1}
    assert "asset-2" in per_asset


def test_report_includes_ingestion_count_per_asset(client, mock_facility_access):
    """The whole point of wiring in telemetry-service's volume endpoint -
    each asset's row must carry its real ingestion_count, independent
    of that asset's alert_count."""
    assets_patch, ingestion_patch, assets = _patched_report_deps(
        ingestion_counts={"asset-1": 1500, "asset-2": 0}
    )
    with assets_patch as mock_get_assets, ingestion_patch:
        mock_get_assets.return_value = assets
        response = client.get(
            "/reports/facility-1?period=daily&date=2026-08-05",
            headers={"Authorization": "Bearer irrelevant-mocked-out"},
        )

    assert response.status_code == 200
    per_asset = {row["asset_id"]: row["ingestion_count"] for row in response.json()["per_asset"]}
    assert per_asset == {"asset-1": 1500, "asset-2": 0}


def test_report_excludes_alerts_outside_the_period_window(client, mock_facility_access):
    """An alert timestamped outside the requested window must not be
    counted - this is the real behavior test for resolve_report_period's
    integration into the router, not just the unit-level date math
    already covered in test_report_period.py."""
    db = SessionLocal()
    db.add(_make_alert(id="outside", asset_id="asset-1", created_at=datetime(2026, 7, 1, 0, 0, 0)))
    db.commit()
    db.close()

    assets_patch, ingestion_patch, assets = _patched_report_deps()
    with assets_patch as mock_get_assets, ingestion_patch:
        mock_get_assets.return_value = assets
        response = client.get(
            "/reports/facility-1?period=daily&date=2026-08-05",
            headers={"Authorization": "Bearer irrelevant-mocked-out"},
        )

    assert response.status_code == 200
    assert response.json()["alerts"]["total"] == 0


def test_report_for_a_facility_with_no_assets_returns_an_empty_report_not_an_error(
    client, mock_facility_access
):
    """A facility right after onboarding has zero assets - this is a
    real, valid state, not a failure. The endpoint must return a clean
    empty report, not a 404/500. get_asset_ingestion_count is never even
    called in this path, since there's no asset to look it up for."""
    with patch(
        "app.routers.reports.get_facility_assets", new_callable=AsyncMock
    ) as mock_get_assets:
        mock_get_assets.return_value = []
        response = client.get(
            "/reports/facility-1?period=daily&date=2026-08-05",
            headers={"Authorization": "Bearer irrelevant-mocked-out"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["asset_count"] == 0
    assert body["alerts"]["total"] == 0
    assert body["per_asset"] == []


def test_report_rejects_an_invalid_period_with_422(client, mock_facility_access):
    """period is a Literal["daily", "weekly", "monthly"] - FastAPI should
    reject anything else automatically, before the route body even runs."""
    response = client.get(
        "/reports/facility-1?period=yearly",
        headers={"Authorization": "Bearer irrelevant-mocked-out"},
    )
    assert response.status_code == 422
