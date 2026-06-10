import io
from datetime import date
from calendar import monthrange
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, Vehicle, Trip
from ..keyboards import report_period_kb, report_vehicle_kb, cancel_kb, main_menu_kb
from ..services import generate_fahrtenbuch_pdf
from ..services.validators import validate_trips_for_pdf

router = Router(name="reports")


class ReportFSM(StatesGroup):
    selecting_vehicle = State()
    selecting_period = State()
    waiting_date_from = State()
    waiting_date_to = State()


@router.message(Command("report"))
async def cmd_report(message: Message, state: FSMContext, session: AsyncSession, user: User):
    result = await session.execute(select(Vehicle).where(Vehicle.user_id == user.id))
    vehicles = list(result.scalars().all())
    if not vehicles:
        await message.answer("⚠️ Спочатку додайте авто в /cars")
        return

    await message.answer(
        "📄 <b>Генерація Fahrtenbuch PDF</b>\n\nОберіть автомобіль:",
        reply_markup=report_vehicle_kb(vehicles),
        parse_mode="HTML",
    )
    await state.set_state(ReportFSM.selecting_vehicle)


@router.callback_query(ReportFSM.selecting_vehicle, F.data.startswith("report:vehicle:"))
async def report_vehicle(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":")[2]
    await state.update_data(vehicle_id=val)  # може бути "all"
    await callback.message.edit_text(
        "📅 Оберіть період:",
        reply_markup=report_period_kb(),
    )
    await state.set_state(ReportFSM.selecting_period)
    await callback.answer()


@router.callback_query(ReportFSM.selecting_period, F.data.startswith("report:month:"))
async def report_month(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    _, _, year, month = callback.data.split(":")
    year, month = int(year), int(month)
    _, last_day = monthrange(year, month)
    date_from = date(year, month, 1)
    date_to = date(year, month, last_day)
    period_label = date_from.strftime("%B %Y")

    await callback.message.edit_text(f"⏳ Генерую звіт за <b>{period_label}</b>...", parse_mode="HTML")
    await _generate_and_send(callback.message, state, session, user, date_from, date_to, period_label)
    await callback.answer()


@router.callback_query(ReportFSM.selecting_period, F.data.startswith("report:quarter:"))
async def report_quarter(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    _, _, year, q = callback.data.split(":")
    year, q = int(year), int(q)
    first_month = (q - 1) * 3 + 1
    last_month = first_month + 2
    _, last_day = monthrange(year, last_month)
    date_from = date(year, first_month, 1)
    date_to = date(year, last_month, last_day)
    period_label = f"Q{q} {year}"

    await callback.message.edit_text(f"⏳ Генерую звіт за <b>{period_label}</b>...", parse_mode="HTML")
    await _generate_and_send(callback.message, state, session, user, date_from, date_to, period_label)
    await callback.answer()


@router.callback_query(ReportFSM.selecting_period, F.data == "report:custom")
async def report_custom(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Введіть дату <b>початку</b> (DD.MM.YYYY):",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await state.set_state(ReportFSM.waiting_date_from)
    await callback.answer()


@router.message(ReportFSM.waiting_date_from, F.text)
async def report_date_from(message: Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=main_menu_kb())
        return
    try:
        from datetime import datetime
        d = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("⚠️ Невірний формат. Введіть DD.MM.YYYY:")
        return
    await state.update_data(date_from=d.isoformat())
    await message.answer("Введіть дату <b>кінця</b> (DD.MM.YYYY):", parse_mode="HTML")
    await state.set_state(ReportFSM.waiting_date_to)


@router.message(ReportFSM.waiting_date_to, F.text)
async def report_date_to(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=main_menu_kb())
        return
    try:
        from datetime import datetime
        d = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("⚠️ Невірний формат. Введіть DD.MM.YYYY:")
        return
    data = await state.get_data()
    date_from = date.fromisoformat(data["date_from"])
    if d < date_from:
        await message.answer("⚠️ Дата кінця не може бути раніше початку. Спробуйте ще раз:")
        return
    period_label = f"{date_from.strftime('%d.%m.%Y')} – {d.strftime('%d.%m.%Y')}"
    await message.answer(f"⏳ Генерую звіт за <b>{period_label}</b>...", parse_mode="HTML")
    await _generate_and_send(message, state, session, user, date_from, d, period_label)


async def _generate_and_send(
    msg: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    date_from: date,
    date_to: date,
    period_label: str,
):
    data = await state.get_data()
    vehicle_id_val = data.get("vehicle_id", "all")

    # Запит поїздок
    q = (
        select(Trip)
        .where(Trip.user_id == user.id)
        .where(Trip.date >= date_from)
        .where(Trip.date <= date_to)
        .options(
            selectinload(Trip.vehicle),
            selectinload(Trip.start_address),
            selectinload(Trip.end_address),
        )
        .order_by(Trip.date)
    )
    if vehicle_id_val != "all":
        q = q.where(Trip.vehicle_id == int(vehicle_id_val))

    result = await session.execute(q)
    trips = list(result.scalars().all())

    if not trips:
        await msg.answer(
            f"📋 За вказаний період поїздок не знайдено.",
            reply_markup=main_menu_kb(),
        )
        await state.clear()
        return

    # Визначаємо авто для заголовку
    if vehicle_id_val == "all":
        # Використовуємо перше авто зі списку
        vehicle = trips[0].vehicle
    else:
        vehicle = await session.get(Vehicle, int(vehicle_id_val))

    pdf_bytes = generate_fahrtenbuch_pdf(
        user=user,
        vehicle=vehicle,
        trips=trips,
        period_label=period_label,
        date_from=date_from,
        date_to=date_to,
    )

    filename = f"Fahrtenbuch_{period_label.replace(' ', '_').replace('.', '-').replace('–', '-')}.pdf"
    total_km = sum(t.distance for t in trips)

    await msg.answer_document(
        document=BufferedInputFile(pdf_bytes, filename=filename),
        caption=(
            f"📄 <b>Fahrtenbuch</b> — {period_label}\n"
            f"🚗 {vehicle.display_name}\n"
            f"📊 Поїздок: {len(trips)} | Загальний пробіг: <b>{total_km:.1f} км</b>"
        ),
        parse_mode="HTML",
    )
    await msg.answer("Головне меню:", reply_markup=main_menu_kb())
    await state.clear()
