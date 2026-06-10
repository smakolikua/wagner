import io
import zipfile
from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Income, Receipt, Trip, User
from ..services.csv_export import export_income_csv, export_receipts_csv, export_trips_csv
from ..services.pdf_report import generate_fahrtenbuch_pdf
from ..services.tax_report import generate_eur_pdf

router = Router(name="steuer_package")


@router.message(Command("steuerpaket"))
async def cmd_steuerpaket(message: Message, session: AsyncSession, user: User):
    year = date.today().year
    date_from = date(year, 1, 1)
    date_to = date(year, 12, 31)
    label = str(year)

    await message.answer("⏳ Генерую пакет для Steuerberater...")

    receipts_result = await session.execute(
        select(Receipt)
        .where(Receipt.user_id == user.id, Receipt.date >= date_from, Receipt.date <= date_to)
        .options(selectinload(Receipt.category), selectinload(Receipt.trip))
        .order_by(Receipt.date)
    )
    receipts = list(receipts_result.scalars().all())

    trips_result = await session.execute(
        select(Trip)
        .where(Trip.user_id == user.id, Trip.date >= date_from, Trip.date <= date_to)
        .options(selectinload(Trip.vehicle), selectinload(Trip.start_address), selectinload(Trip.end_address))
        .order_by(Trip.date)
    )
    trips = list(trips_result.scalars().all())

    incomes_result = await session.execute(
        select(Income)
        .where(Income.user_id == user.id, Income.date >= date_from, Income.date <= date_to)
        .order_by(Income.date)
    )
    incomes = list(incomes_result.scalars().all())

    if not receipts and not trips and not incomes:
        await message.answer("📋 За поточний рік ще немає даних для пакета.")
        return

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"README_Steuerberater_{label}.txt", (
            f"Fahrtenbuch Bot Steuerberater Paket {label}\n"
            f"User: {user.name}\n"
            f"Zeitraum: {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}\n\n"
            f"Belege: {len(receipts)}\n"
            f"Fahrten: {len(trips)}\n"
            f"Einnahmen: {len(incomes)}\n\n"
            "CSV files use semicolon separators and UTF-8 BOM for Excel compatibility.\n"
        ))
        if receipts:
            zf.writestr(f"Belege_{label}.csv", export_receipts_csv(receipts))
        if trips:
            zf.writestr(f"Fahrten_{label}.csv", export_trips_csv(trips))
            zf.writestr(
                f"Fahrtenbuch_{label}.pdf",
                generate_fahrtenbuch_pdf(
                    user=user,
                    vehicle=trips[0].vehicle,
                    trips=trips,
                    period_label=label,
                    date_from=date_from,
                    date_to=date_to,
                ),
            )
        if incomes:
            zf.writestr(f"Einnahmen_{label}.csv", export_income_csv(incomes))

        business_receipts = [r for r in receipts if r.is_business]
        zf.writestr(
            f"EUR_{label}.pdf",
            generate_eur_pdf(
                user=user,
                receipts=business_receipts,
                trips=trips,
                date_from=date_from,
                date_to=date_to,
                period_label=label,
                total_income=sum(i.amount for i in incomes),
            ),
        )

    await message.answer_document(
        BufferedInputFile(buf.getvalue(), filename=f"Steuerberater_Paket_{label}.zip"),
        caption=(
            f"📦 <b>Steuerberater Paket {label}</b>\n"
            f"🧾 Чеків: {len(receipts)}  🚗 Поїздок: {len(trips)}  💶 Доходів: {len(incomes)}"
        ),
        parse_mode="HTML",
    )
