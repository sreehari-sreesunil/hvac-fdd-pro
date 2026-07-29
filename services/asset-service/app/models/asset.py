"""SQLAlchemy models owned by asset-service: Facility, AssetType,
MetricDefinition, Asset.

Note: organization_id fields below are foreign-key-shaped (a string UUID)
but do NOT have an actual ForeignKey constraint to auth-service's
Organization table — that table lives in a different database entirely.
This is normal and expected in a microservices architecture: cross-service
references are logical, not enforced at the database level. Validity is
enforced by calling auth-service's API instead (see app/core/deps.py).
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.session import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Facility(Base):
    __tablename__ = "facilities"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    organization_id = Column(String(36), nullable=False, index=True)  # logical FK to auth-service
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    timezone = Column(String, default="UTC")

    assets = relationship("Asset", back_populates="facility", cascade="all, delete-orphan")


class AssetType(Base):
    """e.g. 'RTU', 'AHU', 'Chiller' — defines which metrics an asset of this type has."""

    __tablename__ = "asset_types"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)

    metric_definitions = relationship(
        "MetricDefinition", back_populates="asset_type", cascade="all, delete-orphan"
    )
    assets = relationship("Asset", back_populates="asset_type")


class MetricDefinition(Base):
    """Drives dynamic dashboards: which metrics exist per asset type, units, chart type."""

    __tablename__ = "metric_definitions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    asset_type_id = Column(String(36), ForeignKey("asset_types.id"), nullable=False)
    metric_name = Column(String, nullable=False)  # e.g. "supply_air_temp"
    display_name = Column(String, nullable=False)  # e.g. "Supply Air Temp"
    unit = Column(String, nullable=True)  # e.g. "°C"
    datatype = Column(String, default="float")
    chart_type = Column(String, default="line")  # line, gauge, kpi
    # Only meaningful for chart_type="gauge" - the expected engineering-unit
    # range for this metric (e.g. 50-90 for a Supply Air Temp gauge), set
    # once per asset type. Nullable: line/kpi charts ignore these entirely,
    # and a gauge with no range set falls back to a simple numeric display
    # rather than guessing bounds from whatever data happens to be visible.
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)

    asset_type = relationship("AssetType", back_populates="metric_definitions")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=False)
    asset_type_id = Column(String(36), ForeignKey("asset_types.id"), nullable=False)
    name = Column(String, nullable=False)  # e.g. "RTU-4"
    external_ref = Column(String, nullable=True)  # e.g. BACnet device instance, Modbus unit id
    created_at = Column(DateTime, default=datetime.utcnow)

    facility = relationship("Facility", back_populates="assets")
    asset_type = relationship("AssetType", back_populates="assets")
