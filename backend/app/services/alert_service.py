from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import logging
import smtplib

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Alert, Metric, Threshold
from app.services.settings_service import notification_config


logger = logging.getLogger(__name__)


def threshold_map(db: Session) -> dict[str, Threshold]:
    return {item.metric: item for item in db.query(Threshold).filter(Threshold.enabled.is_(True)).all()}


def evaluate_metric(
    db: Session,
    thresholds: dict[str, Threshold],
    source_type: str,
    source_id: int | None,
    name: str,
    metric: Metric,
) -> None:
    evaluate_cpu(db, thresholds, source_type, source_id, name, metric)
    evaluate_simple_threshold(db, thresholds, source_type, source_id, name, metric, "ram_usage_percent")
    evaluate_datastore_free(db, thresholds, source_type, source_id, name, metric)
    evaluate_simple_threshold(db, thresholds, source_type, source_id, name, metric, "latency_ms")
    evaluate_simple_threshold(db, thresholds, source_type, source_id, name, metric, "packet_loss_percent")
    if source_type == "vm":
        evaluate_vm_power(db, source_id, name, metric.power_state)


def evaluate_cpu(
    db: Session,
    thresholds: dict[str, Threshold],
    source_type: str,
    source_id: int | None,
    name: str,
    metric: Metric,
) -> None:
    threshold = thresholds.get("cpu_usage_percent")
    value = metric.cpu_usage_percent
    if value is None or not threshold:
        resolve_alert(db, source_type, source_id, "cpu_usage_percent")
        return

    critical = threshold.critical_value
    warning = threshold.warning_value
    if critical is not None and value > critical:
        upsert_alert(
            db,
            source_type,
            source_id,
            "cpu_usage_percent",
            "critical",
            f"{name}: CPU critical",
            f"CPU usage {value:.2f}% > {critical:.2f}%.",
        )
        return

    if warning is not None and value > warning and cpu_warning_sustained(db, metric, warning):
        minutes = get_settings().cpu_warning_duration_seconds // 60
        upsert_alert(
            db,
            source_type,
            source_id,
            "cpu_usage_percent",
            "warning",
            f"{name}: CPU warning",
            f"CPU usage {value:.2f}% > {warning:.2f}% for at least {minutes} minutes.",
        )
        return

    resolve_alert(db, source_type, source_id, "cpu_usage_percent")


def cpu_warning_sustained(db: Session, metric: Metric, warning_value: float) -> bool:
    source_filter = [Metric.entity_type == metric.entity_type]
    if metric.entity_type == "host":
        source_filter.append(Metric.host_id == metric.host_id)
    else:
        source_filter.append(Metric.vm_id == metric.vm_id)

    since = datetime.now(timezone.utc) - timedelta(seconds=get_settings().cpu_warning_duration_seconds)
    below_recent = (
        db.query(Metric)
        .filter(*source_filter, Metric.collected_at >= since, Metric.cpu_usage_percent <= warning_value)
        .first()
    )
    if below_recent:
        return False

    high_before_window = (
        db.query(Metric)
        .filter(*source_filter, Metric.collected_at <= since, Metric.cpu_usage_percent > warning_value)
        .first()
    )
    return high_before_window is not None


def evaluate_simple_threshold(
    db: Session,
    thresholds: dict[str, Threshold],
    source_type: str,
    source_id: int | None,
    name: str,
    metric: Metric,
    field: str,
) -> None:
    threshold = thresholds.get(field)
    value = getattr(metric, field)
    level = threshold_level(value, threshold)
    if not level:
        resolve_alert(db, source_type, source_id, field)
        return
    upsert_alert(
        db,
        source_type,
        source_id,
        field,
        level,
        f"{name}: {field} {level}",
        threshold_message(field, value, threshold),
    )


def evaluate_datastore_free(
    db: Session,
    thresholds: dict[str, Threshold],
    source_type: str,
    source_id: int | None,
    name: str,
    metric: Metric,
) -> None:
    if source_type != "host" or not metric.datastore_total_bytes:
        resolve_alert(db, source_type, source_id, "datastore_free_percent")
        return
    free_percent = (metric.datastore_free_bytes or 0) / metric.datastore_total_bytes * 100
    threshold = thresholds.get("datastore_free_percent")
    level = threshold_level(free_percent, threshold)
    if not level:
        resolve_alert(db, source_type, source_id, "datastore_free_percent")
        return
    upsert_alert(
        db,
        source_type,
        source_id,
        "datastore_free_percent",
        level,
        f"{name}: datastore free {level}",
        threshold_message("datastore_free_percent", free_percent, threshold),
    )


def evaluate_vm_power(db: Session, vm_id: int | None, name: str, power_state: str | None) -> None:
    if power_state and "poweredOn" in power_state:
        resolve_alert(db, "vm", vm_id, "vm_offline")
        resolve_alert(db, "vm", vm_id, "power_state")
        return
    upsert_alert(
        db,
        "vm",
        vm_id,
        "vm_offline",
        "critical",
        f"{name}: VM offline",
        f"VM power state is {power_state or 'unknown'}.",
    )


def threshold_level(value: float | None, threshold: Threshold | None) -> str | None:
    if value is None or threshold is None:
        return None
    if threshold.operator == "lte":
        if threshold.critical_value is not None and value < threshold.critical_value:
            return "critical"
        if threshold.warning_value is not None and value < threshold.warning_value:
            return "warning"
        return None
    if threshold.critical_value is not None and value > threshold.critical_value:
        return "critical"
    if threshold.warning_value is not None and value > threshold.warning_value:
        return "warning"
    return None


def threshold_message(field: str, value: float | None, threshold: Threshold | None) -> str:
    if value is None or not threshold:
        return f"{field} has no current value."
    operator = "<" if threshold.operator == "lte" else ">"
    if threshold_level(value, threshold) == "critical" and threshold.critical_value is not None:
        limit = threshold.critical_value
    else:
        limit = threshold.warning_value
    if limit is None:
        return f"{field} current value {value:.2f} crossed configured threshold."
    return f"{field} current value {value:.2f} {operator} {limit:.2f}."


def upsert_alert(
    db: Session,
    source_type: str,
    source_id: int | None,
    metric: str,
    level: str,
    title: str,
    message: str,
) -> Alert:
    now = datetime.now(timezone.utc)
    alert = (
        db.query(Alert)
        .filter(
            Alert.source_type == source_type,
            Alert.source_id == source_id,
            Alert.metric == metric,
            Alert.is_active.is_(True),
        )
        .first()
    )

    is_new = alert is None
    level_changed = False
    if not alert:
        alert = Alert(
            source_type=source_type,
            source_id=source_id,
            metric=metric,
            level=level,
            title=title,
            message=message,
            is_active=True,
            notification_count=0,
        )
        db.add(alert)
    else:
        level_changed = alert.level != level
        alert.level = level
        alert.title = title
        alert.message = message
        alert.updated_at = now

    db.flush()
    if should_notify(alert, now, is_new, level_changed):
        notify(db, alert)
        alert.last_notified_at = now
        alert.notification_count = (alert.notification_count or 0) + 1
        db.flush()
    return alert


def should_notify(alert: Alert, now: datetime, is_new: bool, level_changed: bool) -> bool:
    if is_new or (level_changed and alert.level == "critical"):
        return True
    if not alert.last_notified_at:
        return True
    cooldown = timedelta(seconds=get_settings().alert_cooldown_seconds)
    last_notified_at = alert.last_notified_at
    if last_notified_at.tzinfo is None:
        last_notified_at = last_notified_at.replace(tzinfo=timezone.utc)
    return now - last_notified_at >= cooldown


def resolve_alert(db: Session, source_type: str, source_id: int | None, metric: str) -> None:
    now = datetime.now(timezone.utc)
    alerts = (
        db.query(Alert)
        .filter(
            Alert.source_type == source_type,
            Alert.source_id == source_id,
            Alert.metric == metric,
            Alert.is_active.is_(True),
        )
        .all()
    )
    for alert in alerts:
        alert.is_active = False
        alert.resolved_at = now
        alert.updated_at = now


def notify(db: Session, alert: Alert) -> None:
    text = f"[{alert.level.upper()}] {alert.title}\n{alert.message}"
    send_telegram(db, text)
    send_email(db, text)


def send_telegram(db: Session, text: str) -> None:
    settings = notification_config(db)
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    try:
        httpx.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            json={"chat_id": settings.telegram_chat_id, "text": text},
            timeout=5,
        )
    except Exception:
        logger.exception("Telegram alert notification failed")


def send_email(db: Session, text: str) -> None:
    settings = notification_config(db)
    if not settings.smtp_host or not settings.smtp_to:
        return
    message = EmailMessage()
    message["Subject"] = "Monitoring System alert"
    message["From"] = settings.smtp_from
    message["To"] = settings.smtp_to
    message.set_content(text)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except Exception:
        logger.exception("Email alert notification failed")
