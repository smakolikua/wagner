"""
admin.py — /backup та /broadcast команди для адміністратора.
"""
import shutil
import os
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User
from ..config import settings
from ..i18n import t
from ..services.telegram_storage import (
    send_sqlite_backup_to_storage,
    storage_enabled,
    storage_status_text,
)

router = Router(name="admin")


def _is_admin(user: User) -> bool:
    return settings.ADMIN_TELEGRAM_ID is not None and user.telegram_id == settings.ADMIN_TELEGRAM_ID


@router.message(Command("backup"))
async def cmd_backup(message: Message, session: AsyncSession, user: User):
    if not _is_admin(user):
        await message.answer(t("backup_no_access", user.lang))
        return

    db_url = settings.DATABASE_URL
    if "sqlite" not in db_url:
        await message.answer("⚠️ Backup доступний тільки для SQLite. Для PostgreSQL використайте pg_dump.")
        return

    # Шлях до SQLite файлу
    db_path = db_url.split("///")[-1]
    if not os.path.exists(db_path):
        await message.answer("⚠️ БД файл не знайдено.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"/tmp/fahrtenbuch_backup_{timestamp}.db"
    shutil.copy2(db_path, backup_path)

    # Статистика
    res = await session.execute(select(User))
    users_count = len(res.scalars().all())

    size_kb = os.path.getsize(backup_path) / 1024

    await message.answer_document(
        FSInputFile(backup_path, filename=f"fahrtenbuch_backup_{timestamp}.db"),
        caption=(
            f"✅ <b>Database Backup</b>\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            f"👥 Users: {users_count}\n"
            f"💾 Size: {size_kb:.1f} KB"
        ),
        parse_mode="HTML",
    )
    os.remove(backup_path)


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, session: AsyncSession, user: User):
    if not _is_admin(user):
        await message.answer(t("backup_no_access", user.lang))
        return

    # Текст після команди
    text_to_send = message.text.replace("/broadcast", "").strip()
    if not text_to_send:
        await message.answer("Використання: /broadcast Текст повідомлення")
        return

    res = await session.execute(select(User))
    users = list(res.scalars().all())

    sent = failed = 0
    for u in users:
        try:
            await message.bot.send_message(u.telegram_id, text_to_send, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1

    await message.answer(
        f"📢 <b>Broadcast завершено</b>\n✅ Надіслано: {sent}\n❌ Помилок: {failed}",
        parse_mode="HTML",
    )


@router.message(Command("storage_status"))
async def cmd_storage_status(message: Message, user: User):
    if not _is_admin(user):
        await message.answer(t("backup_no_access", user.lang))
        return
    await message.answer(storage_status_text())


@router.message(Command("storage_backup"))
async def cmd_storage_backup(message: Message, session: AsyncSession, user: User):
    if not _is_admin(user):
        await message.answer(t("backup_no_access", user.lang))
        return
    if not storage_enabled():
        await message.answer(storage_status_text())
        return

    res = await session.execute(select(User))
    users_count = len(res.scalars().all())

    try:
        result = await send_sqlite_backup_to_storage(users_count=users_count)
    except Exception as e:
        await message.answer(f"❌ Storage backup failed:\n<code>{e}</code>", parse_mode="HTML")
        return

    await message.answer(
        "✅ <b>Storage backup sent</b>\n"
        f"📦 {result['filename']}\n"
        f"💾 {result['size_kb']:.1f} KB",
        parse_mode="HTML",
    )


@router.message(Command("admin_stats"))
async def cmd_admin_stats(message: Message, session: AsyncSession, user: User):
    if not _is_admin(user):
        await message.answer(t("backup_no_access", user.lang))
        return

    from ..models import Vehicle, Address, Trip, LiveSession
    users_count   = (await session.execute(select(User))).scalars().all()
    trips_count   = (await session.execute(select(Trip))).scalars().all()
    active_sess   = (await session.execute(
        select(LiveSession).where(LiveSession.ended_at.is_(None))
    )).scalars().all()

    await message.answer(
        f"📊 <b>Admin Stats</b>\n\n"
        f"👥 Users: {len(users_count)}\n"
        f"🚗 Trips total: {len(trips_count)}\n"
        f"📡 Active tracking sessions: {len(active_sess)}",
        parse_mode="HTML",
    )
