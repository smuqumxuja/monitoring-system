from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field("Monitoring System", validation_alias="APP_NAME")
    environment: str = Field("development", validation_alias="ENVIRONMENT")
    database_url: str = Field(
        "postgresql+psycopg2://monitor:monitor_password@postgres:5432/monitoring",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field("redis://redis:6379/0", validation_alias="REDIS_URL")

    secret_key: str = Field("change-me-in-production", validation_alias="SECRET_KEY")
    jwt_algorithm: str = "HS256"
    token_expire_minutes: int = Field(720, validation_alias="TOKEN_EXPIRE_MINUTES")

    admin_username: str = Field("admin", validation_alias="ADMIN_USERNAME")
    admin_password: str = Field("admin12345", validation_alias="ADMIN_PASSWORD")

    cors_origins: str = Field("http://localhost:3000,http://127.0.0.1:3000", validation_alias="CORS_ORIGINS")
    collect_interval_seconds: int = Field(60, validation_alias="COLLECT_INTERVAL_SECONDS")
    network_check_interval_seconds: int = Field(10, validation_alias="NETWORK_CHECK_INTERVAL_SECONDS")
    ping_count: int = Field(4, validation_alias="PING_COUNT")
    ping_timeout_seconds: float = Field(1.5, validation_alias="PING_TIMEOUT_SECONDS")
    alert_cooldown_seconds: int = Field(300, validation_alias="ALERT_COOLDOWN_SECONDS")
    cpu_warning_duration_seconds: int = Field(300, validation_alias="CPU_WARNING_DURATION_SECONDS")

    telegram_bot_token: str | None = Field(None, validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = Field(None, validation_alias="TELEGRAM_CHAT_ID")

    smtp_host: str | None = Field(None, validation_alias="SMTP_HOST")
    smtp_port: int = Field(587, validation_alias="SMTP_PORT")
    smtp_username: str | None = Field(None, validation_alias="SMTP_USERNAME")
    smtp_password: str | None = Field(None, validation_alias="SMTP_PASSWORD")
    smtp_from: str = Field("monitoring@example.com", validation_alias="SMTP_FROM")
    smtp_to: str | None = Field(None, validation_alias="SMTP_TO")
    smtp_use_tls: bool = Field(True, validation_alias="SMTP_USE_TLS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
