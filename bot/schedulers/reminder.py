"""
reminder.py — APScheduler задачі.

Завдання:
1. Щомісячне нагадування (1-го числа в 08:00) — нагадати про звіт
2. Щотижневе нагадування (понеділок 09:00) — якщо не було поїздок >5 днів
3. Авто-очищення «зависших» LiveSession (старші 12 годин)
"""

import asyncio
from datetime import datetime, timedelta, timezone
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, and_
from loguru import logger

from ..database import async_session_maker
from ..models import User, Trip, LiveSession


async def _send_monthly_reminder(bot: Bot):
    """1-го числа кожного місяця — нагадування зробити звіт за минулий місяць."""
    async with async_session_maker() as session:
        result = await session.execute(select(User))
        users = list(result.scalars().all())

    now = datetime.now()
    prev_month = (now.replace(day=1) - timedelta(days=1))
    month_label = prev_month.strftime("%B %Y")

    for user in users:
        try:
            from ..i18n import t
            await bot.send_message(
                chat_id=user.telegram_id,
                text=t("remind_monthly", user.lang, month=month_label),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"Monthly reminder failed for user {user.telegram_id}: {e}")


async def _send_inactivity_reminder(bot: Bot):
    """Нагадування якщо користувач не додавав поїздок >5 днів."""
    threshold = datetime.now() - timedelta(days=5)

    async with async_session_maker() as session:
        result = await session.execute(select(User))
        users = list(result.scalars().all())

        for user in users:
            last_trip = await session.execute(
                select(Trip)
                .where(Trip.user_id == user.id)
                .order_by(Trip.created_at.desc())
                .limit(1)
            )
            trip = last_trip.scalar_one_or_none()

            # Пропускаємо якщо поїздка є і вона свіжа
            if trip and trip.created_at > threshold:
                continue
            # Пропускаємо нових користувачів (акаунт < 5 днів)
            if user.created_at > threshold:
                continue

            try:
                from ..i18n import t
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=t("remind_inactive", user.lang),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(f"Inactivity reminder failed for {user.telegram_id}: {e}")


async def _cleanup_stale_sessions():
    """Завершує LiveSession які відкриті > 12 годин (бот перезапустився або збій)."""
    threshold = datetime.now() - timedelta(hours=12)
    async with async_session_maker() as session:
        result = await session.execute(
            select(LiveSession).where(
                LiveSession.ended_at.is_(None),
                LiveSession.started_at < threshold,
            )
        )
        stale = result.scalars().all()
        for s in stale:
            s.ended_at = datetime.now()
            logger.info(f"Cleaned up stale LiveSession id={s.id} user_id={s.user_id}")
        await session.commit()


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Berlin")

    # 1-го числа щомісяця о 08:00
    scheduler.add_job(
        _send_monthly_reminder,
        CronTrigger(day=1, hour=8, minute=0),
        args=[bot],
        id="monthly_reminder",
        replace_existing=True,
    )

    # Щопонеділка о 09:00 — перевірка неактивних
    scheduler.add_job(
        _send_inactivity_reminder,
        CronTrigger(day_of_week="mon", hour=9, minute=0),
        args=[bot],
        id="inactivity_reminder",
        replace_existing=True,
    )

    # Кожні 6 годин — очищення зависших сесій
    scheduler.add_job(
        _cleanup_stale_sessions,
        CronTrigger(hour="*/6"),
        id="cleanup_sessions",
        replace_existing=True,
    )

    # Щовечора о 20:00 — нагадування внести чеки
    scheduler.add_job(
        _send_daily_receipt_reminder,
        CronTrigger(hour=20, minute=0),
        args=[bot],
        id="daily_receipt_reminder",
        replace_existing=True,
    )

    # 10-го числа щомісяця — USt-Voranmeldung нагадування
    scheduler.add_job(
        _send_ust_reminder,
        CronTrigger(day=10, hour=9, minute=0),
        args=[bot],
        id="ust_reminder",
        replace_existing=True,
    )

    return scheduler


async def _send_daily_receipt_reminder(bot):
    """Щовечора о 20:00 — нагадування внести чеки за сьогодні."""
    from datetime import date, timedelta
    from ..models import User, Receipt
    today     = date.today()
    yesterday = today - timedelta(days=1)

    async with async_session_maker() as session:
        result = await session.execute(select(User))
        users  = list(result.scalars().all())

    for user in users:
        try:
            # Перевіряємо чи є чеки за сьогодні
            async with async_session_maker() as session:
                r = await session.execute(
                    select(Receipt)
                    .where(Receipt.user_id == user.id)
                    .where(Receipt.date == today)
                    .limit(1)
                )
                has_today = r.scalar_one_or_none() is not None

            if not has_today:
                from ..i18n import t
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        "🧾 <b>Нагадування про чеки</b>\n\n"
                        "Ви вносили чеки сьогодні? "
                        "Не забудьте зафіксувати всі витрати!\n\n"
                        "📸 Надішліть фото чека або /newreceipt"
                    ),
                    parse_mode="HTML",
                )
        except Exception as e:
            logger.warning(f"Daily receipt reminder failed for {user.telegram_id}: {e}")


async def _send_ust_reminder(bot):
    """10-го числа кожного місяця — нагадування про USt-Voranmeldung."""
    from datetime import date
    today = date.today()
    # Попередній місяць
    if today.month == 1:
        prev_month = date(today.year - 1, 12, 1).strftime("%B %Y")
    else:
        prev_month = date(today.year, today.month - 1, 1).strftime("%B %Y")

    async with async_session_maker() as session:
        result = await session.execute(select(User))
        users  = list(result.scalars().all())

    for user in users:
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=(
                    f"📋 <b>USt-Voranmeldung</b>\n\n"
                    f"Термін подачі декларації за <b>{prev_month}</b> — до 10-го числа.\n\n"
                    f"Завантажте звіт для бухгалтера:\n"
                    f"📤 /export — CSV для DATEV\n"
                    f"💰 /taxreport — EÜR PDF"
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"USt reminder failed for {user.telegram_id}: {e}")
