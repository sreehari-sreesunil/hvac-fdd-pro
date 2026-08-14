"""Pydantic schemas for asset-service."""

from datetime import datetime

from pydantic import BaseModel, Field


class FacilityCreate(BaseModel):
    organization_id: str
    name: str = Field(max_length=255)
    address: str | None = Field(default=None, max_length=500)
    timezone: str = Field(default="UTC", max_length=50)


class FacilityOut(BaseModel):
    id: str
    organization_id: str
    name: str
    address: str | None = None
    timezone: str

    model_config = {"from_attributes": True}


class MetricDefinitionCreate(BaseModel):
    metric_name: str = Field(max_length=255)
    display_name: str = Field(max_length=255)
    unit: str | None = Field(default=None, max_length=50)
    datatype: str = Field(default="float", max_length=50)
    chart_type: str = Field(default="line", max_length=50)
    min_value: float | None = None
    max_value: float | None = None


class MetricDefinitionOut(MetricDefinitionCreate):
    id: str
    asset_type_id: str

    model_config = {"from_attributes": True}


class AssetTypeCreate(BaseModel):
    organization_id: str
    name: str = Field(max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    metrics: list[MetricDefinitionCreate] = []


class AssetTypeOut(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str | None = None
    metric_definitions: list[MetricDefinitionOut] = []

    model_config = {"from_attributes": True}


class AssetCreate(BaseModel):
    facility_id: str
    asset_type_id: str
    name: str = Field(max_length=255)
    external_ref: str | None = Field(default=None, max_length=255)


class AssetOut(BaseModel):
    id: str
    facility_id: str
    asset_type_id: str
    name: str
    external_ref: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
