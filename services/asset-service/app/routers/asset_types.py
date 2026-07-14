"""Asset type endpoints for asset-service.

Unlike Facility, AssetType is global — not scoped to any organization. Any
authenticated user can view or define asset types (e.g. "RTU", "Chiller"),
so these endpoints only require a valid login, never verify_org_membership.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id
from app.db.session import get_db
from app.models.asset import AssetType, MetricDefinition
from app.schemas.asset import AssetTypeCreate, AssetTypeOut

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
    return db.query(AssetType).all()
