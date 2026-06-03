from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NetworkStatusOut(BaseModel):
    id: int
    entity_key: str
    entity_type: str
    entity_id: int
    target_ip: str
    status: str
    online: bool
    latency_ms: float | None
    packet_loss_percent: float | None
    consecutive_failures: int
    last_success_at: datetime | None
    last_checked_at: datetime | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
