"""Response schemas for per-asset baseline endpoints."""

from datetime import datetime

from pydantic import BaseModel


class BaselineOut(BaseModel):
    asset_id: str
    metric_definition_id: str
    weather_col: str
    weather_slope: float
    weather_intercept: float
    mean: float
    std: float
    n_reference_rows: int
    fit_at: datetime

    class Config:
        from_attributes = True


class BaselineScoreOut(BaseModel):
    asset_id: str
    metric_definition_id: str
    latest_value: float
    latest_weather_value: float
    residual: float
    z_score: float
    is_deviation: bool
    baseline_fit_at: datetime
