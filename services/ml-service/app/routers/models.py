"""GET /models - list available trained models and their requirements.

Reads directly from each model's <name>.metadata.json file (see
ml/models/) - no database table, since this is static, build-time
information about what's actually been trained and saved to disk, not
something that changes at runtime the way asset/telemetry/alert data
does.
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends

from app.config import settings
from app.core.deps import verify_authenticated_user
from app.schemas.model_info import ModelInfoOut

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/models", response_model=list[ModelInfoOut])
async def list_models(
    _user_id: str = Depends(verify_authenticated_user),
) -> list[ModelInfoOut]:
    """List every trained model with a saved <name>.metadata.json.

    A model missing required_raw_metrics entirely is skipped (with a
    warning logged), not allowed to crash the whole listing - one
    malformed or partially-written metadata file shouldn't take down
    visibility into every other model that's fine. This mirrors the
    project's general approach elsewhere (e.g. CSV upload's per-row
    error handling) of a partial, honest result being better than an
    all-or-nothing failure.
    """
    models_dir = Path(settings.models_dir)
    if not models_dir.exists():
        return []

    results = []
    for metadata_path in sorted(models_dir.glob("*.metadata.json")):
        model_name = metadata_path.name.removesuffix(".metadata.json")
        try:
            metadata = json.loads(metadata_path.read_text())
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not read metadata for model '%s' - skipping", model_name)
            continue

        required_raw_metrics = metadata.get("required_raw_metrics")
        if not required_raw_metrics:
            logger.warning(
                "Model '%s' metadata is missing required_raw_metrics - skipping", model_name
            )
            continue

        results.append(
            ModelInfoOut(
                model_name=model_name,
                required_raw_metrics=required_raw_metrics,
                status=metadata.get("status"),
                algorithm=metadata.get("algorithm"),
                dataset=metadata.get("dataset"),
            )
        )

    return results
