from datetime import datetime, timezone
import logging

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import Alert, EsxiHost, Metric, NetworkStatus, User, VirtualMachine
from app.schemas.metric import CurrentSnapshot, HostSummary, MetricOut, VMSummary
from app.schemas.network import NetworkStatusOut
from app.services.log_service import record_log
from app.services.predictive_service import analyze_predictive_risks
from app.services.rbac import branch_scope_filter, is_superadmin


logger = logging.getLogger(__name__)


def build_snapshot(db: Session, user: User | None = None) -> CurrentSnapshot:
    query = db.query(EsxiHost)
    if user is not None:
        scope = branch_scope_filter(user, EsxiHost)
        if scope is not True:
            query = query.filter(scope)
    hosts = query.order_by(EsxiHost.name.asc()).all()
    host_summaries: list[HostSummary] = []
    for host in hosts:
        host_metric = latest_metric(db, "host", host.id)
        vms = db.query(VirtualMachine).filter(VirtualMachine.host_id == host.id).order_by(VirtualMachine.name.asc()).all()
        vm_summaries = []
        for vm in vms:
            metric = latest_metric(db, "vm", vm.id)
            network_status = get_network_status(db, "vm", vm.id)
            vm_summaries.append(
                VMSummary.model_validate(vm).model_copy(
                    update={
                        "latest_metric": MetricOut.model_validate(metric) if metric else None,
                        "network_status": NetworkStatusOut.model_validate(network_status) if network_status else None,
                    }
                )
            )
        network_status = get_network_status(db, "host", host.id)
        host_summaries.append(
            HostSummary.model_validate(host).model_copy(
                update={
                    "latest_metric": MetricOut.model_validate(host_metric) if host_metric else None,
                    "network_status": NetworkStatusOut.model_validate(network_status) if network_status else None,
                    "vms": vm_summaries,
                }
            )
        )
    alerts = visible_alerts(db, user).order_by(Alert.created_at.desc()).limit(100).all()
    try:
        risks = analyze_predictive_risks(db)
        if user is not None and not is_superadmin(user):
            risks = [risk for risk in risks if _risk_in_branch(db, risk.source_type, risk.source_id, user.branch_id)]
    except Exception:
        logger.exception("Predictive risk analysis failed while building snapshot")
        record_log(db, "error", "predictive", "Predictive risk analysis failed while building snapshot", source="snapshot")
        risks = []
    return CurrentSnapshot(generated_at=datetime.now(timezone.utc), hosts=host_summaries, active_alerts=alerts, predictive_risks=risks)


def latest_metric(db: Session, entity_type: str, entity_id: int) -> Metric | None:
    query = db.query(Metric).filter(Metric.entity_type == entity_type)
    if entity_type == "host":
        query = query.filter(Metric.host_id == entity_id)
    else:
        query = query.filter(Metric.vm_id == entity_id)
    return query.order_by(desc(Metric.collected_at)).first()


def get_network_status(db: Session, entity_type: str, entity_id: int) -> NetworkStatus | None:
    return db.query(NetworkStatus).filter(NetworkStatus.entity_type == entity_type, NetworkStatus.entity_id == entity_id).first()


def visible_alerts(db: Session, user: User | None):
    query = db.query(Alert).filter(Alert.is_active.is_(True))
    if user is None or is_superadmin(user):
        return query

    host_ids = [row.id for row in db.query(EsxiHost.id).filter(EsxiHost.branch_id == user.branch_id).all()]
    vm_ids = [
        row.id
        for row in db.query(VirtualMachine.id)
        .join(EsxiHost, VirtualMachine.host_id == EsxiHost.id)
        .filter(EsxiHost.branch_id == user.branch_id)
        .all()
    ]
    return query.filter(
        ((Alert.source_type == "host") & (Alert.source_id.in_(host_ids)))
        | ((Alert.source_type == "vm") & (Alert.source_id.in_(vm_ids)))
    )


def _risk_in_branch(db: Session, source_type: str, source_id: int, branch_id: int | None) -> bool:
    if branch_id is None:
        return False
    if source_type == "host":
        return db.query(EsxiHost).filter(EsxiHost.id == source_id, EsxiHost.branch_id == branch_id).first() is not None
    return (
        db.query(VirtualMachine)
        .join(EsxiHost, VirtualMachine.host_id == EsxiHost.id)
        .filter(VirtualMachine.id == source_id, EsxiHost.branch_id == branch_id)
        .first()
        is not None
    )
