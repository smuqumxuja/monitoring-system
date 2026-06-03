from typing import Literal

from pydantic import BaseModel


class PredictiveRiskOut(BaseModel):
    id: str
    source_type: Literal["host", "vm"]
    source_id: int
    source_name: str
    host_id: int | None = None
    host_name: str | None = None
    metric: str
    level: Literal["warning", "critical"]
    title: str
    message: str
    recommendations: list[str]
    current_value: float | None = None
    average_7d: float | None = None
    trend_per_day: float | None = None
    forecast_7d: float | None = None
    days_to_limit: float | None = None
    sample_count: int
    confidence: float
