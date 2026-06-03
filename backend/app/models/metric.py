from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import utcnow


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(16), index=True)
    host_id: Mapped[int | None] = mapped_column(ForeignKey("esxi_hosts.id", ondelete="CASCADE"), nullable=True, index=True)
    vm_id: Mapped[int | None] = mapped_column(ForeignKey("virtual_machines.id", ondelete="CASCADE"), nullable=True, index=True)

    cpu_total_mhz: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpu_used_mhz: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpu_usage_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    ram_total_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    ram_used_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    ram_usage_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_size_bytes: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_usage_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    datastore_total_bytes: Mapped[float | None] = mapped_column(Float, nullable=True)
    datastore_free_bytes: Mapped[float | None] = mapped_column(Float, nullable=True)
    datastore_usage_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    nic_status: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    network_rx_kbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    network_tx_kbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    uptime_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    power_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ping_up: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    packet_loss_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    datastore_details: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
