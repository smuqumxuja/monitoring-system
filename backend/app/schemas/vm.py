from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VMCreate(BaseModel):
    host_id: int = Field(ge=1)
    moid: str | None = Field(default=None, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    guest_os: str | None = Field(default=None, max_length=255)
    ip_address: str | None = Field(default=None, max_length=64)
    power_state: str | None = Field(default="manual", max_length=64)
    uptime_seconds: int | None = Field(default=None, ge=0)
    monitoring_enabled: bool = True


class VMUpdate(BaseModel):
    host_id: int | None = Field(default=None, ge=1)
    moid: str | None = Field(default=None, max_length=128)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    guest_os: str | None = Field(default=None, max_length=255)
    ip_address: str | None = Field(default=None, max_length=64)
    power_state: str | None = Field(default=None, max_length=64)
    uptime_seconds: int | None = Field(default=None, ge=0)
    monitoring_enabled: bool | None = None


class VMOut(BaseModel):
    id: int
    host_id: int
    moid: str
    name: str
    guest_os: str | None
    ip_address: str | None
    power_state: str | None
    uptime_seconds: int | None
    monitoring_enabled: bool
    last_seen_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class VMMonitoringUpdate(BaseModel):
    monitoring_enabled: bool
