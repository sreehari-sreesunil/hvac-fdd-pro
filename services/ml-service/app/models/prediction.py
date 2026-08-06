"""Persisted prediction results.

Until now, GET /predictions/{asset_id} computed a result and returned
it directly - nothing was ever saved. This meant no history existed to
report on (a real report v2, showing fault-classification trends over
time rather than just baseline-deviation alerts, was blocked on this),
and no data existed for the argmax-based fault-attribution fix
(deciding which classifier to believe when several fire on the same
event needs to compare predictions across models for the same
asset/time window, which requires them to persist somewhere first).

No foreign key to asset-service's Asset table - logical reference
only, matching this project's established one-database-per-service,
no-cross-service-FK pattern (ADR-0001), same as AssetBaseline above.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, String

from app.db.session import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String, nullable=False, index=True)
    model_name = Column(String, nullable=False, index=True)

    # Classifier fields - null for anomaly-detector models (e.g. the
    # Isolation Forest gatekeeper), which have no predict_proba and so
    # never populate these (see inference.py's predict()).
    predicted_label = Column(String, nullable=True)
    fault_probability = Column(Float, nullable=True)
    confidence = Column(String, nullable=True)  # "high" | "moderate" | "low" - see
    # inference.py's _CONFIDENCE_THRESHOLDS: an explicitly unvalidated,
    # placeholder categorization, not a calibrated probability.

    # Anomaly-detector fields - null for classifier models.
    is_anomaly = Column(Boolean, nullable=True)
    anomaly_score = Column(Float, nullable=True)

    # The exact feature vector used for this prediction - stored for
    # audit/debugging, and because it's already computed (predict()
    # returns it as "feature_values") so persisting it costs nothing
    # extra at request time.
    feature_values = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
