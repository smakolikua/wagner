from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Income, LiveSession, Receipt, Trip, TripPurpose, User

router = Router(name="dashboard")


def _month_bounds(today: date) -> tuple[date, date]:
    start = today.replace(day=1)
    end = date(today.year + (today.month == 12), 1 if today.month == 12 else today.month + 1, 1)
    return start, end


async def _scalar(session: AsyncSession, query, default=0):
    value = await session.scalar(query)
    return value if value is not None else default


@router.message(Command("dashboard"))
async def cmd_dashboard(message: Message, session: AsyncSession, user: User):
    start, end = _month_bounds(date.today())

    trips_count = await _scalar(
        session,
        select(func.count()).where(Trip.user_id == user.id, Trip.date >= start, Trip.date < end),
    )
    business_km = await _scalar(
        session,
        select(func.sum(Trip.end_mileage - Trip.start_mileage)).where(
            Trip.user_id == user.id,
            Trip.date >= start,
            Trip.date < end,
            Trip.purpose == TripPurpose.BUSINESS,
        ),
        0.0,
    )
    private_km = await _scalar(
        session,
        select(func.sum(Trip.end_mileage - Trip.start_mileage)).where(
            Trip.user_id == user.id,
            Trip.date >= start,
            Trip.date < end,
            Trip.purpose == TripPurpose.PRIVATE,
        ),
        0.0,
    )
    expenses = await _scalar(
        session,
        select(func.sum(Receipt.amount_gross)).where(
            Receipt.user_id == user.id,
            Receipt.date >= start,
            Receipt.date < end,
            Receipt.is_business == True,  # noqa: E712
        ),
        0.0,
    )
    incomes = await _scalar(
        session,
        select(func.sum(Income.amount + Income.vat_amount)).where(
            Income.user_id == user.id,
            Income.date >= start,
            Income.date < end,
        ),
        0.0,
    )
    open_sessions = await _scalar(
        session,
        select(func.count()).where(LiveSession.user_id == user.id, LiveSession.ended_at.is_(None)),
    )
    unverified_receipts = await _scalar(
        session,
        select(func.count()).where(Receipt.user_id == user.id, Receipt.is_verified == False),  # noqa: E712
    )

    total_km = round(float(business_km or 0) + float(private_km or 0), 1)
    net = round(float(incomes or 0) - float(expenses or 0), 2)
    month_label = start.strftime("%m.%Y")

    await message.answer(
        "\n".join(
            [
                f"📊 <b>Dashboard {month_label}</b>",
                "",
                f"🚗 Поїздки: <b>{trips_count}</b>",
                f"💼 Business km: <b>{float(business_km or 0):.1f}</b>",
                f"🏠 Private km: <b>{float(private_km or 0):.1f}</b>",
                f"📍 Усього km: <b>{total_km:.1f}</b>",
                "",
                f"💶 Доходи: <b>{float(incomes or 0):.2f} €</b>",
                f"🧾 Бізнес-витрати: <b>{float(expenses or 0):.2f} €</b>",
                f"📈 Результат: <b>{net:.2f} €</b>",
                "",
                f"📌 Відкриті GPS-сесії: <b>{open_sessions}</b>",
                f"🧾 Чеки без підтвердження: <b>{unverified_receipts}</b>",
                "",
                "Деталі: /open, /audit, /report, /taxreport",
            ]
        ),
        parse_mode="HTML",
    )
