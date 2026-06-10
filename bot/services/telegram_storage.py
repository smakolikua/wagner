"""Telegram storage mirror for database backups.

Telegram is not a queryable database, but it works well as an append-only
storage channel for encrypted/private backups and demo-safe audit messages.
"""
import os
import shutil
from datetime import datetime
from typing import Optional

from aiogram import Bot
from aiogram.types import FSInputFile

from ..config import settings


def storage_enabled() -> bool:
    return bool(settings.STORAGE_BOT_TOKEN and settings.STORAGE_CHAT_ID)


def storage_status_text() -> str:
    if storage_enabled():
        return "✅ Telegram storage configured."
    return (
        "⚠️ Telegram storage is not configured.\n\n"
        "Set STORAGE_BOT_TOKEN and STORAGE_CHAT_ID in .env."
    )


def _sqlite_db_path() -> Optional[str]:
    if "sqlite" not in settings.DATABASE_URL:
        return None
    path = settings.DATABASE_URL.split("///")[-1]
    return path


def create_sqlite_backup_copy() -> tuple[str, str, float]:
    db_path = _sqlite_db_path()
    if not db_path:
        raise RuntimeError("Storage backup currently supports SQLite files only.")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"SQLite database file not found: {db_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"fahrtenbuch_backup_{timestamp}.db"
    backup_path = f"/tmp/{filename}"
    shutil.copy2(db_path, backup_path)
    size_kb = os.path.getsize(backup_path) / 1024
    return backup_path, filename, size_kb


async def send_storage_message(text: str) -> None:
    if not storage_enabled():
        raise RuntimeError("Telegram storage is not configured.")

    bot = Bot(settings.STORAGE_BOT_TOKEN)
    try:
        await bot.send_message(
            chat_id=settings.STORAGE_CHAT_ID,
            text=text,
            parse_mode="HTML",
        )
    finally:
        await bot.session.close()


async def send_storage_document(path: str, filename: str, caption: str) -> None:
    if not storage_enabled():
        raise RuntimeError("Telegram storage is not configured.")

    bot = Bot(settings.STORAGE_BOT_TOKEN)
    try:
        await bot.send_document(
            chat_id=settings.STORAGE_CHAT_ID,
            document=FSInputFile(path, filename=filename),
            caption=caption,
            parse_mode="HTML",
        )
    finally:
        await bot.session.close()


async def send_sqlite_backup_to_storage(users_count: int = 0) -> dict:
    backup_path, filename, size_kb = create_sqlite_backup_copy()
    try:
        caption = (
            "✅ <b>Fahrtenbuch Database Backup</b>\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"👥 Users: {users_count}\n"
            f"💾 Size: {size_kb:.1f} KB\n\n"
            "Stored via Telegram Storage Bot."
        )
        await send_storage_document(backup_path, filename, caption)
        return {"filename": filename, "size_kb": size_kb}
    finally:
        if os.path.exists(backup_path):
            os.remove(backup_path)
