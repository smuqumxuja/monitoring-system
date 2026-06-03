from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertOut(BaseModel):
    id: int
    source_type: str
    source_id: int | None
    metric: str
    level: str
    title: str
    message: str
    is_active: bool
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    last_notified_at: datetime | None
    notification_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
