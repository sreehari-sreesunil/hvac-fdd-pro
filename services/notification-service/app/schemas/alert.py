"""Request/response schemas for the alert engine."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    """Internal creation payload - only trusted callers (verified via
    verify_internal_api_key) can hit this. Still worth bounding, not
    just because it's currently internal-only - a future producer
    (e.g. a classifier-driven alert, flagged as planned but not yet
    built) could carry a bug that generates an unexpectedly huge
    message, and this is cheap insurance against that regardless of
    the caller's trust level."""

    asset_id: str
    metric_definition_id: str | None = None
    source: str = Field(max_length=255)
    severity: Literal["warning", "critical"]
    message: str = Field(max_length=2000)
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
