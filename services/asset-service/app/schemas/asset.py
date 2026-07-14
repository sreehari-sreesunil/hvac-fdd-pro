"""Pydantic schemas for asset-service."""

from datetime import datetime

from pydantic import BaseModel


class FacilityCreate(BaseModel):
    organization_id: str
    name: str
    address: str | None = None
    timezone: str = "UTC"


class FacilityOut(BaseModel):
    id: str
    organization_id: str
    name: str
    address: str | None = None
    timezone: str

    model_config = {"from_attributes": True}


class MetricDefinitionCreate(BaseModel):
    metric_name: str
    display_name: str
    unit: str | None = None
    datatype: str = "float"
    chart_type: str = "line"


class MetricDefinitionOut(MetricDefinitionCreate):
    id: str
    asset_type_id: str

    model_config = {"from_attributes": True}


class AssetTypeCreate(BaseModel):
    name: str
    description: str | None = None
    metrics: list[MetricDefinitionCreate] = []


class AssetTypeOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    metric_definitions: list[MetricDefinitionOut] = []

    model_config = {"from_attributes": True}


class AssetCreate(BaseModel):
    facility_id: str
    asset_type_id: str
    name: str
    external_ref: str | None = None


class AssetOut(BaseModel):
    id: str
    facility_id: str
    asset_type_id: str
    name: str
    external_ref: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
