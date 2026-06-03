from dataclasses import dataclass
from datetime import datetime, timezone
import asyncio
import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import EsxiHost, NetworkStatus, VirtualMachine
from app.services.alert_service import resolve_alert, upsert_alert
from app.services.log_service import record_log
from app.services.ping_service import PingResult, ping_target


logger = logging.getLogger(__name__)


@dataclass
class NetworkTarget:
    entity_type: str
    entity_id: int
    entity_key: str
    name: str
    target_ip: str
    branch_id: int | None = None


class NetworkMonitor:
    probable_outage_failures = 3
    offline_failures = 5

    def __init__(self) -> None:
        self.settings = get_settings()

    def check_once(self, db: Session) -> None:
        targets = self._targets(db)
        logger.info("Network monitor checking %s target(s)", len(targets))
        for target in targets:
            try:
                self.check_target(db, target)
                db.commit()
            except Exception:
                db.rollback()
                logger.exception(
                    "Network target check failed; entity_type=%s entity_id=%s target=%s",
                    target.entity_type,
                    target.entity_id,
                    target.target_ip,
                )
                record_log(
                    db,
                    "error",
                    "network",
                    "Network target check failed",
                    branch_id=target.branch_id,
                    source=target.target_ip,
                    details={"entity_type": target.entity_type, "entity_id": target.entity_id, "name": target.name},
                )
                db.commit()

    def check_target(self, db: Session, target: NetworkTarget) -> NetworkStatus:
        now = datetime.now(timezone.utc)
        result = self._ping(target.target_ip)
        status = self._get_or_create_status(db, target)

        if result.up:
            status.consecutive_failures = 0
            status.status = "online"
            status.online = True
            status.last_success_at = now
            self._resolve_network_alerts(db, target)
        else:
            status.consecutive_failures += 1
            status.online = False
            status.status = self._status_from_failures(status.consecutive_failures)
            self._raise_network_alert(db, target, status.consecutive_failures)

        status.target_ip = target.target_ip
        status.latency_ms = result.latency_ms
        status.packet_loss_percent = result.packet_loss_percent
        status.last_checked_at = now
        status.updated_at = now
        db.flush()
        return status

    def _targets(self, db: Session) -> list[NetworkTarget]:
        targets: list[NetworkTarget] = []
        hosts = db.query(EsxiHost).filter(EsxiHost.active.is_(True)).order_by(EsxiHost.name.asc()).all()
        for host in hosts:
            targets.append(
                NetworkTarget(
                    entity_type="host",
                    entity_id=host.id,
                    entity_key=f"host:{host.id}",
                    name=host.name,
                    target_ip=host.hostname,
                    branch_id=host.branch_id,
                )
            )

        vms = (
            db.query(VirtualMachine)
            .filter(
                VirtualMachine.monitoring_enabled.is_(True),
                VirtualMachine.ip_address.isnot(None),
                VirtualMachine.ip_address != "",
            )
            .order_by(VirtualMachine.name.asc())
            .all()
        )
        for vm in vms:
            targets.append(
                NetworkTarget(
                    entity_type="vm",
                    entity_id=vm.id,
                    entity_key=f"vm:{vm.id}",
                    name=vm.name,
                    target_ip=vm.ip_address or "",
                    branch_id=vm.host.branch_id if vm.host else None,
                )
            )
        return targets

    def _get_or_create_status(self, db: Session, target: NetworkTarget) -> NetworkStatus:
        status = db.query(NetworkStatus).filter(NetworkStatus.entity_key == target.entity_key).first()
        if status:
            return status
        status = NetworkStatus(
            entity_key=target.entity_key,
            entity_type=target.entity_type,
            entity_id=target.entity_id,
            target_ip=target.target_ip,
            status="unknown",
            online=False,
            consecutive_failures=0,
        )
        db.add(status)
        db.flush()
        return status

    def _ping(self, target_ip: str) -> PingResult:
        return asyncio.run(
            ping_target(
                target_ip,
                count=self.settings.ping_count,
                timeout=self.settings.ping_timeout_seconds,
            )
        )

    def _status_from_failures(self, failures: int) -> str:
        if failures >= self.offline_failures:
            return "offline"
        if failures >= self.probable_outage_failures:
            return "probable_outage"
        return "warning"

    def _raise_network_alert(self, db: Session, target: NetworkTarget, failures: int) -> None:
        if failures >= self.offline_failures:
            resolve_alert(db, target.entity_type, target.entity_id, "network_probable_outage")
            upsert_alert(
                db,
                target.entity_type,
                target.entity_id,
                "network_offline",
                "critical",
                f"{target.name}: offline",
                f"{target.target_ip} ketma-ket {failures} marta pingga javob bermadi.",
            )
        elif failures >= self.probable_outage_failures:
            upsert_alert(
                db,
                target.entity_type,
                target.entity_id,
                "network_probable_outage",
                "warning",
                f"{target.name}: uzilish ehtimoli",
                f"{target.target_ip} ketma-ket {failures} marta pingga javob bermadi.",
            )

    def _resolve_network_alerts(self, db: Session, target: NetworkTarget) -> None:
        resolve_alert(db, target.entity_type, target.entity_id, "network_probable_outage")
        resolve_alert(db, target.entity_type, target.entity_id, "network_offline")
        resolve_alert(db, target.entity_type, target.entity_id, "ping_down")
