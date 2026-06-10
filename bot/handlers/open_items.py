from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import LiveSession, Receipt, Trip, User

router = Router(name="open_items")


@router.message(Command("open"))
async def cmd_open_items(message: Message, session: AsyncSession, user: User):
    live_result = await session.execute(
        select(LiveSession)
        .where(LiveSession.user_id == user.id, LiveSession.ended_at.is_(None))
        .order_by(LiveSession.started_at.desc())
        .limit(5)
    )
    live_sessions = live_result.scalars().all()

    receipt_result = await session.execute(
        select(Receipt)
        .where(Receipt.user_id == user.id, Receipt.is_verified == False)  # noqa: E712
        .order_by(Receipt.date.desc())
        .limit(5)
    )
    receipts = receipt_result.scalars().all()

    trip_result = await session.execute(
        select(Trip)
        .where(Trip.user_id == user.id, Trip.notes.is_(None))
        .order_by(Trip.date.desc(), Trip.id.desc())
        .limit(5)
    )
    trips_without_notes = trip_result.scalars().all()

    if not live_sessions and not receipts and not trips_without_notes:
        await message.answer("✅ Немає відкритих задач. Дані виглядають готовими до звіту.")
        return

    lines = ["📌 <b>Відкриті задачі перед звітом</b>"]

    if live_sessions:
        lines.append("\n📡 <b>Активні GPS-сесії</b>")
        for item in live_sessions:
            started = item.started_at.strftime("%d.%m.%Y %H:%M") if item.started_at else "—"
            lines.append(f"• #{item.id} старт: {started}, km: {item.start_mileage:.1f}")

    if receipts:
        lines.append("\n🧾 <b>Чеки без підтвердження</b>")
        for item in receipts:
            lines.append(f"• #{item.id} {item.date.strftime('%d.%m.%Y')} — {item.amount_gross:.2f} €")

    if trips_without_notes:
        lines.append("\n🚗 <b>Поїздки без нотатки</b>")
        for item in trips_without_notes:
            lines.append(f"• #{item.id} {item.date.strftime('%d.%m.%Y')} — {item.distance:.1f} km")

    lines.append("\nПісля перевірки можна формувати `/report`, `/taxreport` або export package.")
    await message.answer("\n".join(lines), parse_mode="HTML")
