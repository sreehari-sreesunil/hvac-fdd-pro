"""Per-asset, per-metric frozen baseline reference.

Deliberately NOT continuously recalculated - see
ml/src/features/rolling_baseline.py's module docstring and
PER_ASSET_BASELINE_VALIDATION_LOG.md for why a continuously-adapting
window fails at this task (it "forgets" true normal within its own
window length once it starts seeing fault-affected data). Re-fitting is
a deliberate action (POST /baselines/{asset_id} again), not automatic.

No foreign key to asset-service's Asset table or telemetry-service's
MetricDefinition table - logical reference only, matching this project's
established one-database-per-service, no-cross-service-FK pattern
(ADR-0001).
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.db.session import Base


class AssetBaseline(Base):
    __tablename__ = "asset_baselines"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String, nullable=False, index=True)
    metric_definition_id = Column(String, nullable=False, index=True)
    # mean/std are of the WEATHER-RESIDUALIZED value, not the raw reading -
    # a raw-pressure validation badly understated the real signal (see
    # PER_ASSET_BASELINE_VALIDATION_LOG.md). weather_slope/intercept are
    # fit ONCE from the reference period and only ever APPLIED, never
    # refit, at serving time - matching the same discipline every
    # classifier/gatekeeper already follows for this exact reason.
    mean = Column(Float, nullable=False)
    std = Column(Float, nullable=False)
    weather_col = Column(String, nullable=False, default="RTU_OA_TEMP")
    weather_slope = Column(Float, nullable=False)
    weather_intercept = Column(Float, nullable=False)
    n_reference_rows = Column(Integer, nullable=False)
    fit_at = Column(DateTime, default=datetime.utcnow, nullable=False)
