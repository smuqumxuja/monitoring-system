from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EsxiHost, Metric, User, VirtualMachine
from app.routers.deps import current_user
from app.schemas import CurrentSnapshot, MetricOut, PredictiveRiskOut
from app.services.predictive_service import analyze_predictive_risks
from app.services.rbac import is_superadmin
from app.services.snapshot_service import build_snapshot


router = APIRouter(prefix="/metrics", tags=["metrics"])

RANGES = {
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


@router.get("/current", response_model=CurrentSnapshot)
def current_metrics(user: User = Depends(current_user), db: Session = Depends(get_db)) -> CurrentSnapshot:
    return build_snapshot(db, user)


@router.get("/risks", response_model=list[PredictiveRiskOut])
def predictive_risks(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[PredictiveRiskOut]:
    risks = analyze_predictive_risks(db)
    if is_superadmin(user):
        return risks
    return [risk for risk in risks if _risk_in_user_branch(db, risk.source_type, risk.source_id, user.branch_id)]


@router.get("/history", response_model=list[MetricOut])
def metric_history(
    entity_type: str = Query(pattern="^(host|vm)$"),
    entity_id: int = Query(ge=1),
    range: str = Query(default="1h", pattern="^(1h|24h|7d|30d)$"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[Metric]:
    since = datetime.now(timezone.utc) - RANGES[range]
    query = db.query(Metric).filter(Metric.entity_type == entity_type, Metric.collected_at >= since)
    if entity_type == "host":
        query = query.filter(Metric.host_id == entity_id)
        if not is_superadmin(user) and not db.query(EsxiHost).filter(EsxiHost.id == entity_id, EsxiHost.branch_id == user.branch_id).first():
            return []
    else:
        query = query.filter(Metric.vm_id == entity_id)
        if not is_superadmin(user) and not _vm_in_branch(db, entity_id, user.branch_id):
            return []
    return query.order_by(Metric.collected_at.asc()).all()


def _risk_in_user_branch(db: Session, source_type: str, source_id: int, branch_id: int | None) -> bool:
    if source_type == "host":
        return db.query(EsxiHost).filter(EsxiHost.id == source_id, EsxiHost.branch_id == branch_id).first() is not None
    return _vm_in_branch(db, source_id, branch_id)


def _vm_in_branch(db: Session, vm_id: int, branch_id: int | None) -> bool:
    return (
        db.query(VirtualMachine)
        .join(EsxiHost, VirtualMachine.host_id == EsxiHost.id)
        .filter(VirtualMachine.id == vm_id, EsxiHost.branch_id == branch_id)
        .first()
        is not None
    )
