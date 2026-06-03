from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EsxiHost, NetworkStatus, User, VirtualMachine
from app.routers.deps import current_user
from app.schemas import NetworkStatusOut
from app.services.rbac import is_superadmin


router = APIRouter(prefix="/network", tags=["network"])


@router.get("/status", response_model=list[NetworkStatusOut])
def list_network_statuses(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[NetworkStatus]:
    query = db.query(NetworkStatus)
    if not is_superadmin(user):
        host_ids = [row.id for row in db.query(EsxiHost.id).filter(EsxiHost.branch_id == user.branch_id).all()]
        vm_ids = [
            row.id
            for row in db.query(VirtualMachine.id)
            .join(EsxiHost, VirtualMachine.host_id == EsxiHost.id)
            .filter(EsxiHost.branch_id == user.branch_id)
            .all()
        ]
        query = query.filter(
            or_(
                (NetworkStatus.entity_type == "host") & (NetworkStatus.entity_id.in_(host_ids)),
                (NetworkStatus.entity_type == "vm") & (NetworkStatus.entity_id.in_(vm_ids)),
            )
        )
    return query.order_by(NetworkStatus.entity_type.asc(), NetworkStatus.entity_id.asc()).all()
