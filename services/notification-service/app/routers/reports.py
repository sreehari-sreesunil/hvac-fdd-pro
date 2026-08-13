"""Facility-level report endpoint.

GET /reports/{facility_id} aggregates alert activity across every asset
in a facility for a chosen period, instead of requiring a caller to make
one GET /alerts/{asset_id} call per asset and aggregate client-side -
that N+1 pattern doesn't scale and isn't how any other cross-service
aggregation in this project is built.
"""

import asyncio
from typing import cast

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.deps import security, verify_facility_access
from app.db.session import get_db
from app.models.alert import Alert
from app.schemas.report import FacilityReportOut, ReportAlertsSummary, ReportAssetSummary
from app.services.asset_client import get_facility_assets
from app.services.report_period import ReportPeriod, resolve_report_period
from app.services.telemetry_client import get_asset_ingestion_count

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{facility_id}", response_model=FacilityReportOut)
async def get_facility_report(
    facility_id: str,
    period: ReportPeriod,
    date: str | None = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    _user_id: str = Depends(verify_facility_access),
    db: Session = Depends(get_db),
) -> FacilityReportOut:
    """Build an alert-activity summary for every asset in a facility.

    Args:
        facility_id: Resolved via verify_facility_access before this
            function body ever runs - by the time we're here, the
            caller is already confirmed to have org-level access.
        period: "daily" | "weekly" | "monthly" - validated automatically
            by FastAPI against the ReportPeriod Literal type (a bad
            value returns a 422 before this function is even called).
        date: Optional "YYYY-MM-DD" anchor date. Defaults to today if
            omitted - see resolve_report_period for the exact window
            math per period.

    Returns a report with zero alerts and zero assets (not an error) if
    the facility genuinely has no assets yet - an empty facility is a
    real, valid state (e.g. right after onboarding), not something to
    treat as a failure.
    """
    start, end = resolve_report_period(period, date)

    token = credentials.credentials
    assets = await get_facility_assets(facility_id, token)
    asset_ids = [asset["id"] for asset in assets]
    asset_name_by_id = {asset["id"]: asset["name"] for asset in assets}

    if not asset_ids:
        return FacilityReportOut(
            facility_id=facility_id,
            period=period,
            start=start,
            end=end,
            asset_count=0,
            alerts=ReportAlertsSummary(total=0, by_severity={}, by_status={}, by_source={}),
            per_asset=[],
        )

    alerts = (
        db.query(Alert)
        .filter(Alert.asset_id.in_(asset_ids))
        .filter(Alert.created_at >= start)
        .filter(Alert.created_at < end)
        .all()
    )

    # Aggregated by hand rather than with SQL GROUP BY - alert volume per
    # facility per report period is small (this is a fault-monitoring
    # alert log, not a high-frequency events table), so the simplicity
    # of counting in Python outweighs the marginal efficiency of pushing
    # the aggregation into the database for this specific endpoint.
    by_severity: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_source: dict[str, int] = {}
    alert_count_by_asset: dict[str, int] = dict.fromkeys(asset_ids, 0)

    # SQLAlchemy legacy Column() style: mypy sees Column[str] on instance
    # attribute access, not the real runtime str - a known SQLAlchemy
    # typing limitation, not a bug here.
    for alert in alerts:
        severity = cast(str, alert.severity)
        status_ = cast(str, alert.status)
        source = cast(str, alert.source)
        asset_id = cast(str, alert.asset_id)
        by_severity[severity] = by_severity.get(severity, 0) + 1
        by_status[status_] = by_status.get(status_, 0) + 1
        by_source[source] = by_source.get(source, 0) + 1
        alert_count_by_asset[asset_id] = alert_count_by_asset.get(asset_id, 0) + 1

    # Fetched concurrently, not one asset at a time in a loop - a
    # facility could have many assets, and each is an independent
    # cross-service HTTP call; running them sequentially would make
    # this endpoint's latency scale linearly with asset count for no
    # real reason, since none of these calls depend on each other's
    # results.
    ingestion_counts = await asyncio.gather(
        *(get_asset_ingestion_count(asset_id, start, end, token) for asset_id in asset_ids)
    )
    ingestion_count_by_asset = dict(zip(asset_ids, ingestion_counts, strict=True))

    per_asset = [
        ReportAssetSummary(
            asset_id=asset_id,
            asset_name=asset_name_by_id.get(asset_id, "Unknown asset"),
            alert_count=alert_count_by_asset[asset_id],
            ingestion_count=ingestion_count_by_asset[asset_id],
        )
        for asset_id in asset_ids
    ]

    return FacilityReportOut(
        facility_id=facility_id,
        period=period,
        start=start,
        end=end,
        asset_count=len(asset_ids),
        alerts=ReportAlertsSummary(
            total=len(alerts),
            by_severity=by_severity,
            by_status=by_status,
            by_source=by_source,
        ),
        per_asset=per_asset,
    )
