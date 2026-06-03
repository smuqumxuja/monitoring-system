from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import utcnow


class Threshold(Base):
    __tablename__ = "thresholds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    warning_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    critical_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    operator: Mapped[str] = mapped_column(String(8), default="gte")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

