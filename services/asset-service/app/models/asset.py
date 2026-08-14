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

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, UniqueConstraint
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
    """e.g. 'RTU', 'AHU', 'Chiller' — defines which metrics an asset of this type has.

    Org-scoped (organization_id), not global - each organization has its
    own private catalog of asset types. This was NOT the original design
    (asset types used to be a shared, platform-wide catalog visible to
    every org) - changed after a real live walkthrough with a genuinely
    new organization surfaced that a brand-new org could see and use
    every other org's asset types, a real multi-tenancy gap given this
    project's own "Multi-Tenant Foundation" phase-1 goal.
    """

    __tablename__ = "asset_types"
    __table_args__ = (
        # Uniqueness is per-organization, not global - two different
        # orgs should each be free to have their own "RTU" asset type
        # without colliding, the same way two orgs can each have a
        # facility named the same thing.
        UniqueConstraint("organization_id", "name", name="uq_asset_type_org_name"),
    )

    id = Column(String(36), primary_key=True, default=gen_uuid)
    organization_id = Column(String(36), nullable=False, index=True)  # logical FK to auth-service
    name = Column(String, nullable=False)
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
