from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Telegram ──────────────────────────────────────────────
    BOT_TOKEN: str

    # Webhook (залиште порожнім для polling)
    BOT_WEBHOOK_URL: str = ""
    WEBHOOK_PORT: int = 8443

    # ── База даних ────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./fahrtenbuch.db"

    # ── Геокодинг ─────────────────────────────────────────────
    GOOGLE_MAPS_API_KEY: str = ""

    # ── Трекінг (глобальний дефолт) ───────────────────────────
    GEOFENCE_RADIUS_METERS: int = 100

    # ── Часовий пояс ──────────────────────────────────────────
    TIMEZONE: str = "Europe/Berlin"

    # ── Адміністратор ─────────────────────────────────────────
    ADMIN_TELEGRAM_ID: Optional[int] = None

    # ── Telegram Storage Bot ──────────────────────────────────
    # Другий бот/чат для збереження backup-копій БД.
    STORAGE_BOT_TOKEN: str = ""
    STORAGE_CHAT_ID: str = ""

    # ── Sentry ────────────────────────────────────────────────
    SENTRY_DSN: str = ""

    # ── Логування ─────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/bot.log"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if isinstance(value, str):
            if value.startswith("postgres://"):
                return "postgresql+asyncpg://" + value[len("postgres://"):]
            if value.startswith("postgresql://") and "+asyncpg" not in value:
                return "postgresql+asyncpg://" + value[len("postgresql://"):]
        return value


settings = Settings()
