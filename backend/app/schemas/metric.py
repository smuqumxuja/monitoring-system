from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.alert import AlertOut
from app.schemas.host import HostOut
from app.schemas.network import NetworkStatusOut
from app.schemas.predictive import PredictiveRiskOut
from app.schemas.vm import VMOut


class MetricOut(BaseModel):
    id: int
    entity_type: str
    host_id: int | None
    vm_id: int | None
    cpu_total_mhz: float | None
    cpu_used_mhz: float | None
    cpu_usage_percent: float | None
    ram_total_mb: float | None
    ram_used_mb: float | None
    ram_usage_percent: float | None
    disk_size_bytes: float | None
    disk_usage_percent: float | None
    datastore_total_bytes: float | None
    datastore_free_bytes: float | None
    datastore_usage_percent: float | None
    nic_status: list[dict] | None
    network_rx_kbps: float | None
    network_tx_kbps: float | None
    uptime_seconds: int | None
    power_state: str | None
    ping_up: bool | None
    latency_ms: float | None
    packet_loss_percent: float | None
    datastore_details: list[dict] | None
    extra: dict | None
    collected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VMSummary(VMOut):
    latest_metric: MetricOut | None = None
    network_status: NetworkStatusOut | None = None


class HostSummary(HostOut):
    latest_metric: MetricOut | None = None
    network_status: NetworkStatusOut | None = None
    vms: list[VMSummary] = Field(default_factory=list)


class CurrentSnapshot(BaseModel):
    generated_at: datetime
    hosts: list[HostSummary]
    active_alerts: list[AlertOut]
    predictive_risks: list[PredictiveRiskOut] = Field(default_factory=list)
