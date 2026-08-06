"""Response schema for GET /models."""

from pydantic import BaseModel


class ModelInfoOut(BaseModel):
    """One trained model's identity and requirements.

    Surfaces exactly what's already recorded in each model's
    <name>.metadata.json (see ml/models/) as a real API, rather than
    that information only being readable by opening the file directly.
    Built for the sensor-mapping/model-readiness feature: comparing
    required_raw_metrics against an asset's actual metric definitions
    and mappings is how "is this asset ready for this model" gets
    answered.
    """

    model_name: str
    required_raw_metrics: list[str]
    status: str | None = None
    algorithm: str | None = None
    dataset: str | None = None
