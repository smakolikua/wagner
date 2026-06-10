"""
logging_setup.py — структуроване логування + Sentry інтеграція.

Loguru пише:
  - у stdout (розробка)
  - у файл logs/bot.log з ротацією 10 MB / 7 днів
Sentry підключається якщо SENTRY_DSN задано.
"""
import sys
import os
from loguru import logger


def setup_logging(log_level: str = "INFO", log_file: str = "logs/bot.log"):
    logger.remove()

    # Stdout — кольоровий, читабельний
    logger.add(
        sys.stdout,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # Файл — ротація 10 MB, зберігати 7 днів
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logger.add(
        log_file,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8",
    )
    logger.info(f"Logging configured: level={log_level}, file={log_file}")


def setup_sentry(dsn: str, environment: str = "production"):
    if not dsn:
        logger.info("Sentry DSN not set — skipping Sentry setup.")
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.aiohttp import AioHttpIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            integrations=[
                AioHttpIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1,   # 10% транзакцій для performance
            profiles_sample_rate=0.0,
            send_default_pii=False,   # не надсилати PII
        )
        logger.info(f"Sentry initialized (env={environment})")
    except ImportError:
        logger.warning("sentry-sdk not installed — Sentry disabled")
    except Exception as e:
        logger.error(f"Sentry init failed: {e}")
