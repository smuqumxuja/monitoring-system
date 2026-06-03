from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, engine
from app.models import Branch, Threshold, User
from app.utils.security import hash_password


DEFAULT_THRESHOLDS = [
    ("cpu_usage_percent", 85.0, 95.0, "gte"),
    ("ram_usage_percent", 85.0, 95.0, "gte"),
    ("datastore_free_percent", 15.0, 5.0, "lte"),
    ("latency_ms", 100.0, None, "gte"),
    ("packet_loss_percent", 10.0, 30.0, "gte"),
]

LEGACY_DEFAULTS = {
    "cpu_usage_percent": (75.0, 90.0, "gte"),
    "ram_usage_percent": (75.0, 90.0, "gte"),
    "latency_ms": (100.0, 250.0, "gte"),
    "packet_loss_percent": (5.0, 20.0, "gte"),
}


def init_database(db: Session) -> None:
    Base.metadata.create_all(bind=engine)
    seed_default_branch(db)
    ensure_branch_columns(db)
    ensure_metric_columns(db)
    ensure_alert_columns(db)
    ensure_vm_columns(db)
    seed_admin(db)
    seed_thresholds(db)
    db.commit()


def ensure_metric_columns(db: Session) -> None:
    for column in [
        "cpu_total_mhz",
        "cpu_used_mhz",
        "cpu_usage_percent",
        "ram_total_mb",
        "ram_used_mb",
        "ram_usage_percent",
        "disk_size_bytes",
        "disk_usage_percent",
        "datastore_total_bytes",
        "datastore_free_bytes",
        "datastore_usage_percent",
        "network_rx_kbps",
        "network_tx_kbps",
        "latency_ms",
        "packet_loss_percent",
    ]:
        db.execute(text(f"ALTER TABLE metrics ADD COLUMN IF NOT EXISTS {column} DOUBLE PRECISION"))
    db.execute(text("ALTER TABLE metrics ADD COLUMN IF NOT EXISTS uptime_seconds INTEGER"))
    db.execute(text("ALTER TABLE metrics ADD COLUMN IF NOT EXISTS power_state VARCHAR(64)"))
    db.execute(text("ALTER TABLE metrics ADD COLUMN IF NOT EXISTS ping_up BOOLEAN"))
    db.execute(text("ALTER TABLE metrics ADD COLUMN IF NOT EXISTS nic_status JSONB"))
    db.execute(text("ALTER TABLE metrics ADD COLUMN IF NOT EXISTS datastore_details JSONB"))
    db.execute(text("ALTER TABLE metrics ADD COLUMN IF NOT EXISTS extra JSONB"))


def ensure_alert_columns(db: Session) -> None:
    db.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS last_notified_at TIMESTAMP WITH TIME ZONE"))
    db.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS notification_count INTEGER DEFAULT 0"))
    db.execute(text("UPDATE alerts SET notification_count = 0 WHERE notification_count IS NULL"))


def ensure_vm_columns(db: Session) -> None:
    db.execute(text("ALTER TABLE virtual_machines ADD COLUMN IF NOT EXISTS monitoring_enabled BOOLEAN DEFAULT TRUE"))
    db.execute(text("UPDATE virtual_machines SET monitoring_enabled = TRUE WHERE monitoring_enabled IS NULL"))


def ensure_branch_columns(db: Session) -> None:
    default_branch = default_branch_row(db)
    db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
    db.execute(text("ALTER TABLE esxi_hosts ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
    db.execute(text("ALTER TABLE system_logs ADD COLUMN IF NOT EXISTS branch_id INTEGER"))
    db.execute(text("UPDATE users SET role = 'kuzatuvchi' WHERE role = 'viewer'"))
    db.execute(text("UPDATE users SET branch_id = :branch_id WHERE branch_id IS NULL AND role != 'superadmin'"), {"branch_id": default_branch.id})
    db.execute(text("UPDATE esxi_hosts SET branch_id = :branch_id WHERE branch_id IS NULL"), {"branch_id": default_branch.id})


def seed_default_branch(db: Session) -> None:
    if default_branch_row(db):
        return
    db.add(Branch(name="Markaz", code="HQ", address="Bosh ofis", active=True))
    db.flush()


def default_branch_row(db: Session) -> Branch:
    branch = db.query(Branch).filter(Branch.code == "HQ").first()
    if branch:
        return branch
    branch = db.query(Branch).order_by(Branch.id.asc()).first()
    if branch:
        return branch
    branch = Branch(name="Markaz", code="HQ", address="Bosh ofis", active=True)
    db.add(branch)
    db.flush()
    return branch


def seed_admin(db: Session) -> None:
    settings = get_settings()
    exists = db.query(User).filter(User.username == settings.admin_username).first()
    if exists:
        if exists.role in {"admin", "viewer"}:
            exists.role = "superadmin"
            exists.branch_id = None
        return
    db.add(
        User(
            username=settings.admin_username,
            hashed_password=hash_password(settings.admin_password),
            role="superadmin",
            branch_id=None,
            is_active=True,
        )
    )


def seed_thresholds(db: Session) -> None:
    existing = {item.metric: item for item in db.query(Threshold).all()}
    for metric, warning, critical, operator in DEFAULT_THRESHOLDS:
        threshold = existing.get(metric)
        if not threshold:
            db.add(
                Threshold(
                    metric=metric,
                    warning_value=warning,
                    critical_value=critical,
                    operator=operator,
                    enabled=True,
                )
            )
            continue
        legacy = LEGACY_DEFAULTS.get(metric)
        if legacy and (threshold.warning_value, threshold.critical_value, threshold.operator) == legacy:
            threshold.warning_value = warning
            threshold.critical_value = critical
            threshold.operator = operator
