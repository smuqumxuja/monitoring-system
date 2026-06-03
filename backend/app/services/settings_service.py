from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AppSetting
from app.schemas.settings import NotificationSettingsOut, NotificationSettingsUpdate
from app.utils.security import decrypt_secret, encrypt_secret


SETTING_KEYS = [
    "telegram_bot_token",
    "telegram_chat_id",
    "smtp_host",
    "smtp_port",
    "smtp_username",
    "smtp_password",
    "smtp_from",
    "smtp_to",
    "smtp_use_tls",
]


@dataclass
class NotificationConfig:
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    smtp_host: str | None
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    smtp_from: str
    smtp_to: str | None
    smtp_use_tls: bool


def get_setting(db: Session, key: str) -> str | None:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if not row:
        return None
    return decrypt_secret(row.value_ciphertext)


def set_setting(db: Session, key: str, value: str | None) -> None:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if not row:
        row = AppSetting(key=key)
        db.add(row)
    row.value_ciphertext = encrypt_secret(value) if value not in (None, "") else None
    row.updated_at = datetime.now(timezone.utc)


def notification_config(db: Session) -> NotificationConfig:
    settings = get_settings()
    values = {key: get_setting(db, key) for key in SETTING_KEYS}
    return NotificationConfig(
        telegram_bot_token=values["telegram_bot_token"] or settings.telegram_bot_token,
        telegram_chat_id=values["telegram_chat_id"] or settings.telegram_chat_id,
        smtp_host=values["smtp_host"] or settings.smtp_host,
        smtp_port=_int(values["smtp_port"], settings.smtp_port),
        smtp_username=values["smtp_username"] or settings.smtp_username,
        smtp_password=values["smtp_password"] or settings.smtp_password,
        smtp_from=values["smtp_from"] or settings.smtp_from,
        smtp_to=values["smtp_to"] or settings.smtp_to,
        smtp_use_tls=_bool(values["smtp_use_tls"], settings.smtp_use_tls),
    )


def notification_settings_out(db: Session) -> NotificationSettingsOut:
    config = notification_config(db)
    return NotificationSettingsOut(
        telegram_bot_token_configured=bool(config.telegram_bot_token),
        telegram_chat_id=config.telegram_chat_id,
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_username=config.smtp_username,
        smtp_password_configured=bool(config.smtp_password),
        smtp_from=config.smtp_from,
        smtp_to=config.smtp_to,
        smtp_use_tls=config.smtp_use_tls,
    )


def update_notification_settings(db: Session, payload: NotificationSettingsUpdate) -> NotificationSettingsOut:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        set_setting(db, key, None if value is None else str(value))
    db.commit()
    return notification_settings_out(db)


def _int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}
