from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common import utcnow


class EsxiHost(Base):
    __tablename__ = "esxi_hosts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    hostname: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(128))
    password_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    port: Mapped[int] = mapped_column(Integer, default=443)
    verify_ssl: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    snmp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    snmp_community: Mapped[str | None] = mapped_column(String(128), nullable=True)
    snmp_port: Mapped[int] = mapped_column(Integer, default=161)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    branch = relationship("Branch", back_populates="hosts")
    vms = relationship("VirtualMachine", back_populates="host", cascade="all,delete-orphan")

    @property
    def branch_name(self) -> str | None:
        return self.branch.name if self.branch else None
