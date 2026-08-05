"""Response schemas for the facility-level report endpoint
(GET /reports/{facility_id}).

Kept separate from schemas/alert.py even though this endpoint is built
entirely from Alert rows - a report is a different kind of object (an
aggregate over many alerts across many assets), not a list of AlertOut,
so it gets its own schema module rather than being bolted onto the
existing one.
"""

from datetime import datetime

from pydantic import BaseModel


class ReportAlertsSummary(BaseModel):
    """Aggregate alert counts for one facility over one report period."""

    total: int
    by_severity: dict[str, int]
    by_status: dict[str, int]
    by_source: dict[str, int]


class ReportAssetSummary(BaseModel):
    """Per-asset breakdown within a facility report."""

    asset_id: str
    asset_name: str
    alert_count: int
    ingestion_count: int


class FacilityReportOut(BaseModel):
    """Full response body for GET /reports/{facility_id}."""

    facility_id: str
    period: str
    start: datetime
    end: datetime
    asset_count: int
    alerts: ReportAlertsSummary
    per_asset: list[ReportAssetSummary]
