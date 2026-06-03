from datetime import datetime, timezone
import asyncio
import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import EsxiHost, Metric, VirtualMachine
from app.services.alert_service import evaluate_metric, resolve_alert, threshold_map, upsert_alert
from app.services.esxi_service import EsxiSample, collect_esxi
from app.services.log_service import record_log
from app.services.ping_service import PingResult, ping_target
from app.services.predictive_service import sync_predictive_alerts
from app.services.snmp_service import collect_snmp_metrics
from app.utils.security import decrypt_secret


logger = logging.getLogger(__name__)


class MonitoringCollector:
    def __init__(self) -> None:
        self.settings = get_settings()

    def collect_once(self, db: Session) -> None:
        thresholds = threshold_map(db)
        hosts = db.query(EsxiHost).filter(EsxiHost.active.is_(True)).order_by(EsxiHost.name.asc()).all()
        for host in hosts:
            self.collect_host(db, host, thresholds)
            db.commit()
        try:
            sync_predictive_alerts(db)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Predictive alert sync failed")
            record_log(db, "error", "predictive", "Predictive alert sync failed", source="collector-worker")
            db.commit()

    def collect_host(self, db: Session, host: EsxiHost, thresholds: dict) -> None:
        now = datetime.now(timezone.utc)
        ping = self._ping(host.hostname)
        sample = self._collect_esxi(db, host)
        snmp = asyncio.run(collect_snmp_metrics(host.hostname, host.snmp_community, host.snmp_port)) if host.snmp_enabled else None

        host_metric = Metric(
            entity_type="host",
            host_id=host.id,
            cpu_total_mhz=sample.host.cpu_total_mhz if sample else None,
            cpu_used_mhz=sample.host.cpu_used_mhz if sample else None,
            cpu_usage_percent=sample.host.cpu_usage_percent if sample else None,
            ram_total_mb=sample.host.ram_total_mb if sample else None,
            ram_used_mb=sample.host.ram_used_mb if sample else None,
            ram_usage_percent=sample.host.ram_usage_percent if sample else None,
            datastore_total_bytes=sample.host.datastore_total_bytes if sample else None,
            datastore_free_bytes=sample.host.datastore_free_bytes if sample else None,
            datastore_usage_percent=sample.host.datastore_usage_percent if sample else None,
            nic_status=sample.host.nic_status if sample else None,
            network_rx_kbps=sample.host.network_rx_kbps if sample else None,
            network_tx_kbps=sample.host.network_tx_kbps if sample else None,
            uptime_seconds=(sample.host.uptime_seconds if sample else None) or (snmp.uptime_seconds if snmp else None),
            ping_up=ping.up,
            latency_ms=ping.latency_ms,
            packet_loss_percent=ping.packet_loss_percent,
            datastore_details=sample.host.datastore_details if sample else None,
            extra={
                "snmp": snmp.raw if snmp else {},
            },
            collected_at=now,
        )
        db.add(host_metric)
        db.flush()
        evaluate_metric(db, thresholds, "host", host.id, host.name, host_metric)

        if not sample:
            return
        for vm_sample in sample.vms:
            vm = self._upsert_vm(db, host.id, vm_sample, now)
            db.flush()
            if not vm.monitoring_enabled:
                self._resolve_vm_alerts(db, vm.id)
                continue
            vm_ping = self._ping(vm_sample.ip_address) if vm_sample.ip_address else PingResult(False, None, 100.0)
            vm_metric = Metric(
                entity_type="vm",
                host_id=host.id,
                vm_id=vm.id,
                cpu_total_mhz=vm_sample.cpu_total_mhz,
                cpu_used_mhz=vm_sample.cpu_used_mhz,
                cpu_usage_percent=vm_sample.cpu_usage_percent,
                ram_total_mb=vm_sample.ram_total_mb,
                ram_used_mb=vm_sample.ram_used_mb,
                ram_usage_percent=vm_sample.ram_usage_percent,
                disk_size_bytes=vm_sample.disk_size_bytes,
                disk_usage_percent=vm_sample.disk_usage_percent,
                network_rx_kbps=vm_sample.network_rx_kbps,
                network_tx_kbps=vm_sample.network_tx_kbps,
                uptime_seconds=vm_sample.uptime_seconds,
                power_state=vm_sample.power_state,
                ping_up=vm_ping.up,
                latency_ms=vm_ping.latency_ms,
                packet_loss_percent=vm_ping.packet_loss_percent,
                collected_at=now,
            )
            db.add(vm_metric)
            db.flush()
            evaluate_metric(db, thresholds, "vm", vm.id, vm.name, vm_metric)

    def _collect_esxi(self, db: Session, host: EsxiHost) -> EsxiSample | None:
        password = decrypt_secret(host.password_ciphertext)
        if not password:
            logger.warning("ESXi credential decryption failed for host_id=%s hostname=%s", host.id, host.hostname)
            record_log(
                db,
                "error",
                "esxi",
                "ESXi credential decryption failed",
                branch_id=host.branch_id,
                source=host.hostname,
                details={"host_id": host.id, "host_name": host.name},
            )
            upsert_alert(db, "host", host.id, "esxi_connection", "critical", f"{host.name}: password error", "Credential cannot be decrypted.")
            return None
        try:
            sample = collect_esxi(host.hostname, host.username, password, host.port, host.verify_ssl)
            resolve_alert(db, "host", host.id, "esxi_connection")
            return sample
        except Exception as exc:
            logger.exception("ESXi collection failed for host_id=%s hostname=%s", host.id, host.hostname)
            record_log(
                db,
                "error",
                "esxi",
                "ESXi collection failed",
                branch_id=host.branch_id,
                source=host.hostname,
                details={"host_id": host.id, "host_name": host.name, "error": str(exc)},
            )
            upsert_alert(db, "host", host.id, "esxi_connection", "critical", f"{host.name}: ESXi connection failed", str(exc))
            return None

    def _ping(self, target: str | None) -> PingResult:
        return asyncio.run(ping_target(target, self.settings.ping_count, self.settings.ping_timeout_seconds))

    def _upsert_vm(self, db: Session, host_id: int, sample, now: datetime) -> VirtualMachine:
        vm = db.query(VirtualMachine).filter(VirtualMachine.host_id == host_id, VirtualMachine.moid == sample.moid).first()
        if not vm:
            vm = VirtualMachine(host_id=host_id, moid=sample.moid, name=sample.name)
            db.add(vm)
        vm.name = sample.name
        vm.guest_os = sample.guest_os
        vm.ip_address = sample.ip_address
        vm.power_state = sample.power_state
        vm.uptime_seconds = sample.uptime_seconds
        vm.last_seen_at = now
        return vm

    def _resolve_vm_alerts(self, db: Session, vm_id: int) -> None:
        for metric in [
            "cpu_usage_percent",
            "ram_usage_percent",
            "disk_usage_percent",
            "latency_ms",
            "packet_loss_percent",
            "vm_offline",
            "power_state",
        ]:
            resolve_alert(db, "vm", vm_id, metric)
