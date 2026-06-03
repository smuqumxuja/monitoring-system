from fastapi import HTTPException, status

from app.models import EsxiHost, User, VirtualMachine


ROLE_SUPERADMIN = "superadmin"
ROLE_ADMIN = "admin"
ROLE_OBSERVER = "kuzatuvchi"
ROLE_LEGACY_VIEWER = "viewer"

ADMIN_ROLES = {ROLE_SUPERADMIN, ROLE_ADMIN}
ALL_ROLES = {ROLE_SUPERADMIN, ROLE_ADMIN, ROLE_OBSERVER}


def normalize_role(role: str | None) -> str:
    if role == ROLE_LEGACY_VIEWER:
        return ROLE_OBSERVER
    return role or ROLE_OBSERVER


def can_manage(user: User) -> bool:
    return normalize_role(user.role) in ADMIN_ROLES


def is_superadmin(user: User) -> bool:
    return normalize_role(user.role) == ROLE_SUPERADMIN


def require_admin_role(user: User) -> None:
    if not can_manage(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


def branch_scope_filter(user: User, model):
    if is_superadmin(user):
        return True
    return model.branch_id == user.branch_id


def ensure_branch_access(user: User, branch_id: int | None) -> None:
    if is_superadmin(user):
        return
    if branch_id != user.branch_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch access denied")


def ensure_host_access(user: User, host: EsxiHost) -> None:
    ensure_branch_access(user, host.branch_id)


def ensure_vm_access(user: User, vm: VirtualMachine) -> None:
    ensure_branch_access(user, vm.host.branch_id if vm.host else None)
