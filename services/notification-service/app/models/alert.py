"""Alert model - a generic sink for any detector to write into.

`source` is a free string (e.g. "baseline_deviation", later
"threshold_breach", "classifier:overcharge"), deliberately not an enum -
new detector types can start writing alerts without a schema migration.
Matches the established pattern of this project favoring real,
demonstrated need over premature rigidity (see docs/TECH_DEBT.md's
MLflow deferral for the same reasoning applied elsewhere).
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, String

from app.db.session import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String, nullable=False, index=True)
    metric_definition_id = Column(String, nullable=True, index=True)
    source = Column(String, nullable=False, index=True)
    severity = Column(String, nullable=False)  # "warning" | "critical"
    status = Column(
        String, nullable=False, default="open", index=True
    )  # "open" | "acknowledged" | "resolved"
    message = Column(String, nullable=False)
    details = Column(JSON, nullable=True)  # e.g. {"z_score": 18.09, "k_std": 3.0}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)
