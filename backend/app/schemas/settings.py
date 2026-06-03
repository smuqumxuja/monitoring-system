from pydantic import BaseModel, ConfigDict


class NotificationSettingsOut(BaseModel):
    telegram_bot_token_configured: bool
    telegram_chat_id: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password_configured: bool
    smtp_from: str | None = None
    smtp_to: str | None = None
    smtp_use_tls: bool = True

    model_config = ConfigDict(from_attributes=True)


class NotificationSettingsUpdate(BaseModel):
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_to: str | None = None
    smtp_use_tls: bool | None = None
