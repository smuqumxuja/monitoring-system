from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, EsxiHost, NetworkStatus, SystemLog, Threshold, User, VirtualMachine
from app.routers.deps import admin_user
from app.schemas import (
    BranchCreate,
    BranchOut,
    BranchUpdate,
    NotificationSettingsOut,
    NotificationSettingsUpdate,
    SystemLogOut,
    SystemLogUpdate,
    ThresholdOut,
    ThresholdUpdate,
    UserCreate,
    UserOut,
    UserUpdate,
    VMCreate,
    VMMonitoringUpdate,
    VMOut,
    VMUpdate,
)
from app.services.settings_service import notification_settings_out, update_notification_settings
from app.services.alert_service import resolve_alert
from app.services.rbac import ensure_branch_access, ensure_vm_access, is_superadmin, normalize_role
from app.utils.security import hash_password


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(admin_user)])


@router.get("/branches", response_model=list[BranchOut])
def list_branches(user: User = Depends(admin_user), db: Session = Depends(get_db)) -> list[Branch]:
    query = db.query(Branch)
    if not is_superadmin(user):
        query = query.filter(Branch.id == user.branch_id)
    return query.order_by(Branch.name.asc()).all()


@router.post("/branches", response_model=BranchOut)
def create_branch(payload: BranchCreate, user: User = Depends(admin_user), db: Session = Depends(get_db)) -> Branch:
    if not is_superadmin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin role required")
    exists = db.query(Branch).filter((Branch.name == payload.name) | (Branch.code == payload.code)).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Branch already exists")
    branch = Branch(**payload.model_dump())
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch


@router.put("/branches/{branch_id}", response_model=BranchOut)
def update_branch(branch_id: int, payload: BranchUpdate, user: User = Depends(admin_user), db: Session = Depends(get_db)) -> Branch:
    if not is_superadmin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin role required")
    branch = db.get(Branch, branch_id)
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(branch, key, value)
    branch.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(branch)
    return branch


@router.get("/thresholds", response_model=list[ThresholdOut])
def list_thresholds(db: Session = Depends(get_db)) -> list[Threshold]:
    return db.query(Threshold).order_by(Threshold.metric.asc()).all()


@router.put("/thresholds/{metric}", response_model=ThresholdOut)
def update_threshold(metric: str, payload: ThresholdUpdate, db: Session = Depends(get_db)) -> Threshold:
    threshold = db.query(Threshold).filter(Threshold.metric == metric).first()
    if not threshold:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Threshold not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(threshold, key, value)
    threshold.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(threshold)
    return threshold


@router.get("/vms", response_model=list[VMOut])
def list_vms(user: User = Depends(admin_user), db: Session = Depends(get_db)) -> list[VirtualMachine]:
    query = db.query(VirtualMachine)
    if not is_superadmin(user):
        query = query.join(EsxiHost, VirtualMachine.host_id == EsxiHost.id).filter(EsxiHost.branch_id == user.branch_id)
    return query.order_by(VirtualMachine.name.asc()).all()


@router.post("/vms", response_model=VMOut)
def create_vm(payload: VMCreate, user: User = Depends(admin_user), db: Session = Depends(get_db)) -> VirtualMachine:
    host = db.get(EsxiHost, payload.host_id)
    if not host:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host not found")
    ensure_branch_access(user, host.branch_id)
    moid = payload.moid or f"manual-{uuid4().hex[:12]}"
    exists = db.query(VirtualMachine).filter(VirtualMachine.host_id == host.id, VirtualMachine.moid == moid).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="VM already exists on this host")
    vm = VirtualMachine(
        host_id=host.id,
        moid=moid,
        name=payload.name,
        guest_os=payload.guest_os,
        ip_address=payload.ip_address,
        power_state=payload.power_state,
        uptime_seconds=payload.uptime_seconds,
        monitoring_enabled=payload.monitoring_enabled,
        last_seen_at=datetime.now(timezone.utc),
    )
    db.add(vm)
    db.commit()
    db.refresh(vm)
    return vm


@router.put("/vms/{vm_id}", response_model=VMOut)
def update_vm(vm_id: int, payload: VMUpdate, user: User = Depends(admin_user), db: Session = Depends(get_db)) -> VirtualMachine:
    vm = db.get(VirtualMachine, vm_id)
    if not vm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VM not found")
    ensure_vm_access(user, vm)
    data = payload.model_dump(exclude_unset=True)
    if data.get("host_id") is None:
        data.pop("host_id", None)
    if not data.get("moid"):
        data.pop("moid", None)
    if "host_id" in data and data["host_id"] is not None and data["host_id"] != vm.host_id:
        host = db.get(EsxiHost, data["host_id"])
        if not host:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host not found")
        ensure_branch_access(user, host.branch_id)
    target_host_id = data.get("host_id", vm.host_id)
    target_moid = data.get("moid", vm.moid)
    if target_moid != vm.moid or target_host_id != vm.host_id:
        exists = (
            db.query(VirtualMachine)
            .filter(VirtualMachine.host_id == target_host_id, VirtualMachine.moid == target_moid, VirtualMachine.id != vm.id)
            .first()
        )
        if exists:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="VM already exists on this host")
    for key, value in data.items():
        setattr(vm, key, value)
    db.commit()
    db.refresh(vm)
    return vm


@router.put("/vms/{vm_id}/monitoring", response_model=VMOut)
def update_vm_monitoring(vm_id: int, payload: VMMonitoringUpdate, user: User = Depends(admin_user), db: Session = Depends(get_db)) -> VirtualMachine:
    vm = db.get(VirtualMachine, vm_id)
    if not vm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VM not found")
    ensure_vm_access(user, vm)
    vm.monitoring_enabled = payload.monitoring_enabled
    if not payload.monitoring_enabled:
        for metric in [
            "cpu_usage_percent",
            "ram_usage_percent",
            "disk_usage_percent",
            "latency_ms",
            "packet_loss_percent",
            "vm_offline",
            "power_state",
            "network_probable_outage",
            "network_offline",
        ]:
            resolve_alert(db, "vm", vm.id, metric)
        network_status = db.query(NetworkStatus).filter(NetworkStatus.entity_type == "vm", NetworkStatus.entity_id == vm.id).first()
        if network_status:
            network_status.status = "disabled"
            network_status.online = False
    db.commit()
    db.refresh(vm)
    return vm


@router.delete("/vms/{vm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vm(vm_id: int, user: User = Depends(admin_user), db: Session = Depends(get_db)) -> None:
    vm = db.get(VirtualMachine, vm_id)
    if not vm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VM not found")
    ensure_vm_access(user, vm)
    network_status = db.query(NetworkStatus).filter(NetworkStatus.entity_type == "vm", NetworkStatus.entity_id == vm.id).first()
    if network_status:
        db.delete(network_status)
    db.delete(vm)
    db.commit()


@router.get("/notification-settings", response_model=NotificationSettingsOut)
def get_notification_settings(db: Session = Depends(get_db)) -> NotificationSettingsOut:
    return notification_settings_out(db)


@router.put("/notification-settings", response_model=NotificationSettingsOut)
def save_notification_settings(
    payload: NotificationSettingsUpdate,
    db: Session = Depends(get_db),
) -> NotificationSettingsOut:
    return update_notification_settings(db, payload)


@router.get("/users", response_model=list[UserOut])
def list_users(user: User = Depends(admin_user), db: Session = Depends(get_db)) -> list[User]:
    query = db.query(User)
    if not is_superadmin(user):
        query = query.filter(User.branch_id == user.branch_id, User.role != "superadmin")
    return query.order_by(User.username.asc()).all()


@router.post("/users", response_model=UserOut)
def create_user(payload: UserCreate, user: User = Depends(admin_user), db: Session = Depends(get_db)) -> User:
    exists = db.query(User).filter(User.username == payload.username).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    role = normalize_role(payload.role)
    branch_id = payload.branch_id
    if not is_superadmin(user):
        if role == "superadmin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin role required")
        branch_id = user.branch_id
    elif role == "superadmin":
        branch_id = None
    elif branch_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Branch is required for admin/kuzatuvchi")
    if branch_id and not db.get(Branch, branch_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    user = User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=role,
        branch_id=branch_id,
        is_active=payload.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, actor: User = Depends(admin_user), db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not is_superadmin(actor):
        ensure_branch_access(actor, user.branch_id)
        if user.role == "superadmin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin role required")
    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    if password:
        user.hashed_password = hash_password(password)
    if "role" in data and data["role"] is not None:
        data["role"] = normalize_role(data["role"])
        if data["role"] == "superadmin" and not is_superadmin(actor):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin role required")

    target_role = data.get("role", user.role)
    if target_role == "superadmin":
        if not is_superadmin(actor):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin role required")
        data["branch_id"] = None
    elif "branch_id" in data:
        if not is_superadmin(actor):
            data["branch_id"] = actor.branch_id
        elif data["branch_id"] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Branch is required for admin/kuzatuvchi")
        if data["branch_id"] and not db.get(Branch, data["branch_id"]):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    elif is_superadmin(actor) and user.branch_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Branch is required for admin/kuzatuvchi")
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


@router.get("/logs", response_model=list[SystemLogOut])
def list_system_logs(
    level: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    user: User = Depends(admin_user),
    db: Session = Depends(get_db),
) -> list[SystemLog]:
    query = db.query(SystemLog)
    if not is_superadmin(user):
        query = query.filter(SystemLog.branch_id == user.branch_id)
    if level:
        query = query.filter(SystemLog.level == level)
    if status_filter:
        query = query.filter(SystemLog.status == status_filter)
    if category:
        query = query.filter(SystemLog.category == category)
    return query.order_by(SystemLog.created_at.desc()).limit(limit).all()


@router.put("/logs/{log_id}", response_model=SystemLogOut)
def update_system_log(log_id: int, payload: SystemLogUpdate, user: User = Depends(admin_user), db: Session = Depends(get_db)) -> SystemLog:
    row = db.get(SystemLog, log_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log entry not found")
    if not is_superadmin(user) and row.branch_id != user.branch_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch access denied")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row
