"""Request/response schemas for the alert engine."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class AlertCreate(BaseModel):
    """Internal creation payload - only trusted callers (verified via
    verify_internal_api_key) can hit this."""

    asset_id: str
    metric_definition_id: str | None = None
    source: str
    severity: Literal["warning", "critical"]
    message: str
    details: dict[str, Any] | None = None


class AlertOut(BaseModel):
    id: str
    asset_id: str
    metric_definition_id: str | None
    source: str
    severity: str
    status: str
    message: str
    details: dict[str, Any] | None
    created_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    resolved_at: datetime | None
    resolved_by: str | None

    class Config:
        from_attributes = True
