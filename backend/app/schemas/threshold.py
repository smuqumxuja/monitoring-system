from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ThresholdOut(BaseModel):
    id: int
    metric: str
    warning_value: float | None
    critical_value: float | None
    operator: str
    enabled: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ThresholdUpdate(BaseModel):
    warning_value: float | None = None
    critical_value: float | None = None
    operator: str | None = Field(default=None, pattern="^(gte|lte)$")
    enabled: bool | None = None

