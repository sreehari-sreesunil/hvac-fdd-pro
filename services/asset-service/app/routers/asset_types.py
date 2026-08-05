"""Asset type endpoints for asset-service.

Unlike Facility, AssetType is global — not scoped to any organization. Any
authenticated user can view or define asset types (e.g. "RTU", "Chiller"),
so these endpoints only require a valid login, never verify_org_membership.
"""

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id
from app.db.session import get_db
from app.models.asset import AssetType, MetricDefinition
from app.schemas.asset import (
    AssetTypeCreate,
    AssetTypeOut,
    MetricDefinitionCreate,
    MetricDefinitionOut,
)

router = APIRouter(prefix="/asset-types", tags=["asset-types"])


@router.post("", response_model=AssetTypeOut, status_code=201)
async def create_asset_type(
    payload: AssetTypeCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> AssetType:
    """Create a new asset type along with its metric definitions.

    Args:
        payload: Asset type name/description plus a list of metrics to
            define for it (drives dynamic dashboards downstream).
        user_id: Confirms the caller is authenticated — no org check needed,
            asset types are global.
        db: Database session.

    Returns:
        The newly created AssetType, with its metric_definitions populated.
    """
    asset_type = AssetType(name=payload.name, description=payload.description)
    db.add(asset_type)
    db.flush()  # assigns asset_type.id without committing yet

    for metric in payload.metrics:
        db.add(
            MetricDefinition(
                asset_type_id=asset_type.id,
                metric_name=metric.metric_name,
                display_name=metric.display_name,
                unit=metric.unit,
                datatype=metric.datatype,
                chart_type=metric.chart_type,
                min_value=metric.min_value,
                max_value=metric.max_value,
            )
        )

    db.commit()
    db.refresh(asset_type)
    return asset_type


@router.get("", response_model=list[AssetTypeOut])
async def list_asset_types(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[AssetType]:
    """List every asset type defined on the platform."""
    return cast(list[AssetType], db.query(AssetType).all())


@router.post("/{asset_type_id}/metrics", response_model=MetricDefinitionOut, status_code=201)
async def add_metric_definition(
    asset_type_id: str,
    payload: MetricDefinitionCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> MetricDefinition:
    """Add a metric definition to an EXISTING asset type.

    Until now, metrics could only be defined all at once, at asset-type
    creation time (POST /asset-types's `metrics` list) - there was no
    way to add one later. This is the real gap that blocked the
    sensor-mapping/model-readiness feature: a trained ML model's
    required_raw_metrics (e.g. "RTU_OA_TEMP") has to exist as a real
    MetricDefinition with that exact metric_name before an asset can be
    scored by that model, and previously the only fix for a missing one
    was deleting and recreating the whole asset type.

    metric_name must be unique within this asset type - two
    MetricDefinitions with the same metric_name on the same type would
    make metric-mapping genuinely ambiguous (which one does an incoming
    external_key resolve to?), so this is enforced here at the
    application layer rather than left as a silent footgun.
    """
    asset_type = db.query(AssetType).filter(AssetType.id == asset_type_id).first()
    if asset_type is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset type not found")

    existing = (
        db.query(MetricDefinition)
        .filter(
            MetricDefinition.asset_type_id == asset_type_id,
            MetricDefinition.metric_name == payload.metric_name,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Asset type '{asset_type.name}' already has a metric definition "
                f"named '{payload.metric_name}'"
            ),
        )

    metric = MetricDefinition(
        asset_type_id=asset_type_id,
        metric_name=payload.metric_name,
        display_name=payload.display_name,
        unit=payload.unit,
        datatype=payload.datatype,
        chart_type=payload.chart_type,
        min_value=payload.min_value,
        max_value=payload.max_value,
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric
