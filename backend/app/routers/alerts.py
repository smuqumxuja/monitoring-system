from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, EsxiHost, User, VirtualMachine
from app.routers.deps import current_user
from app.schemas import AlertOut
from app.services.rbac import is_superadmin


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    active: bool | None = Query(default=True),
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[Alert]:
    query = scoped_alert_query(db, user)
    if active is not None:
        query = query.filter(Alert.is_active.is_(active))
    return query.order_by(Alert.created_at.desc()).limit(limit).all()


@router.patch("/{alert_id}/ack", response_model=AlertOut)
def acknowledge_alert(alert_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Alert:
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if not is_superadmin(user) and not alert_in_branch(db, alert, user.branch_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch access denied")
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert


def scoped_alert_query(db: Session, user: User):
    query = db.query(Alert)
    if is_superadmin(user):
        return query
    host_ids, vm_ids = branch_entity_ids(db, user.branch_id)
    return query.filter(
        or_(
            (Alert.source_type == "host") & (Alert.source_id.in_(host_ids)),
            (Alert.source_type == "vm") & (Alert.source_id.in_(vm_ids)),
        )
    )


def alert_in_branch(db: Session, alert: Alert, branch_id: int | None) -> bool:
    if alert.source_id is None:
        return False
    host_ids, vm_ids = branch_entity_ids(db, branch_id)
    if alert.source_type == "host":
        return alert.source_id in host_ids
    if alert.source_type == "vm":
        return alert.source_id in vm_ids
    return False


def branch_entity_ids(db: Session, branch_id: int | None) -> tuple[list[int], list[int]]:
    if branch_id is None:
        return [], []
    host_ids = [row.id for row in db.query(EsxiHost.id).filter(EsxiHost.branch_id == branch_id).all()]
    vm_ids = [
        row.id
        for row in db.query(VirtualMachine.id)
        .join(EsxiHost, VirtualMachine.host_id == EsxiHost.id)
        .filter(EsxiHost.branch_id == branch_id)
        .all()
    ]
    return host_ids, vm_ids
