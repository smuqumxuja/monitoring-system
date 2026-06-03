from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, EsxiHost, User
from app.routers.deps import admin_user, current_user
from app.schemas import HostCreate, HostOut, HostUpdate
from app.services.rbac import branch_scope_filter, ensure_branch_access, is_superadmin
from app.utils.security import encrypt_secret


router = APIRouter(prefix="/hosts", tags=["hosts"])


@router.get("", response_model=list[HostOut])
def list_hosts(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[EsxiHost]:
    query = db.query(EsxiHost)
    scope = branch_scope_filter(user, EsxiHost)
    if scope is not True:
        query = query.filter(scope)
    return query.order_by(EsxiHost.name.asc()).all()


@router.post("", response_model=HostOut)
def create_host(payload: HostCreate, user: User = Depends(admin_user), db: Session = Depends(get_db)) -> EsxiHost:
    exists = db.query(EsxiHost).filter(EsxiHost.hostname == payload.hostname).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Host already exists")
    branch_id = payload.branch_id if is_superadmin(user) else user.branch_id
    ensure_branch_access(user, branch_id)
    if branch_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Branch is required")
    if branch_id and not db.get(Branch, branch_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    host = EsxiHost(
        branch_id=branch_id,
        name=payload.name,
        hostname=payload.hostname,
        username=payload.username,
        password_ciphertext=encrypt_secret(payload.password),
        port=payload.port,
        verify_ssl=payload.verify_ssl,
        active=payload.active,
        snmp_enabled=payload.snmp_enabled,
        snmp_community=payload.snmp_community,
        snmp_port=payload.snmp_port,
    )
    db.add(host)
    db.commit()
    db.refresh(host)
    return host


@router.put("/{host_id}", response_model=HostOut)
def update_host(host_id: int, payload: HostUpdate, user: User = Depends(admin_user), db: Session = Depends(get_db)) -> EsxiHost:
    host = db.get(EsxiHost, host_id)
    if not host:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host not found")
    ensure_branch_access(user, host.branch_id)
    data = payload.model_dump(exclude_unset=True)
    if "branch_id" in data:
        ensure_branch_access(user, data["branch_id"])
        if data["branch_id"] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Branch is required")
        if data["branch_id"] and not db.get(Branch, data["branch_id"]):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    password = data.pop("password", None)
    for key, value in data.items():
        setattr(host, key, value)
    if password:
        host.password_ciphertext = encrypt_secret(password)
    host.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(host)
    return host


@router.delete("/{host_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_host(host_id: int, user: User = Depends(admin_user), db: Session = Depends(get_db)) -> None:
    host = db.get(EsxiHost, host_id)
    if not host:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host not found")
    ensure_branch_access(user, host.branch_id)
    db.delete(host)
    db.commit()
