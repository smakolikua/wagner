"""
export_handler.py — команда /export для завантаження CSV/ZIP.
"""
from datetime import date
from calendar import monthrange
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, Receipt, Trip, Income
from ..keyboards.main_menu import main_menu_kb
from ..services.csv_export import (
    export_receipts_csv, export_trips_csv,
    export_income_csv, export_full_zip,
)

router = Router(name="export")


class ExportFSM(StatesGroup):
    selecting_period = State()
    selecting_type   = State()


def _period_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    today = date.today()
    q     = (today.month - 1) // 3 + 1
    # Квартали
    b.button(text=f"📊 Q{q} {today.year} (поточний)",  callback_data=f"exp:q:{today.year}:{q}")
    pq = q-1 if q>1 else 4; py = today.year if q>1 else today.year-1
    b.button(text=f"📊 Q{pq} {py} (минулий)",          callback_data=f"exp:q:{py}:{pq}")
    # Роки
    b.button(text=f"📅 {today.year} (весь рік)",        callback_data=f"exp:y:{today.year}")
    b.button(text=f"📅 {today.year-1}",                 callback_data=f"exp:y:{today.year-1}")
    b.adjust(2)
    return b.as_markup()


def _type_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📦 Все (ZIP)",         callback_data="exp:type:all")
    b.button(text="🧾 Тільки чеки",       callback_data="exp:type:receipts")
    b.button(text="🚗 Тільки поїздки",    callback_data="exp:type:trips")
    b.button(text="💶 Тільки доходи",     callback_data="exp:type:incomes")
    b.adjust(1)
    return b.as_markup()


@router.message(Command("export"))
async def cmd_export(message: Message, state: FSMContext, user: User):
    await message.answer(
        "📤 <b>Експорт даних (CSV)</b>\n\n"
        "Формат сумісний з Excel, DATEV, Lexware.\n\n"
        "Оберіть період:",
        reply_markup=_period_kb(), parse_mode="HTML",
    )
    await state.set_state(ExportFSM.selecting_period)


@router.callback_query(ExportFSM.selecting_period, F.data.startswith("exp:q:"))
async def exp_select_quarter(callback: CallbackQuery, state: FSMContext):
    _, _, year, q = callback.data.split(":")
    year, q = int(year), int(q)
    fm = (q-1)*3+1; lm = fm+2
    _, ld = monthrange(year, lm)
    await state.update_data(
        exp_from=date(year, fm, 1).isoformat(),
        exp_to=date(year, lm, ld).isoformat(),
        exp_label=f"Q{q}_{year}",
    )
    await callback.message.edit_text("📦 Що експортувати?", reply_markup=_type_kb())
    await state.set_state(ExportFSM.selecting_type)
    await callback.answer()


@router.callback_query(ExportFSM.selecting_period, F.data.startswith("exp:y:"))
async def exp_select_year(callback: CallbackQuery, state: FSMContext):
    year = int(callback.data.split(":")[2])
    await state.update_data(
        exp_from=date(year, 1, 1).isoformat(),
        exp_to=date(year, 12, 31).isoformat(),
        exp_label=str(year),
    )
    await callback.message.edit_text("📦 Що експортувати?", reply_markup=_type_kb())
    await state.set_state(ExportFSM.selecting_type)
    await callback.answer()


@router.callback_query(ExportFSM.selecting_type, F.data.startswith("exp:type:"))
async def exp_generate(callback: CallbackQuery, state: FSMContext,
                       session: AsyncSession, user: User):
    exp_type = callback.data.split(":")[2]
    data = await state.get_data()
    await state.clear()

    date_from = date.fromisoformat(data["exp_from"])
    date_to   = date.fromisoformat(data["exp_to"])
    label     = data["exp_label"]

    await callback.message.edit_text("⏳ Генерую файл...")

    # Завантажуємо потрібні дані
    receipts = trips = incomes = []

    if exp_type in ("all", "receipts"):
        r = await session.execute(
            select(Receipt)
            .where(Receipt.user_id == user.id)
            .where(Receipt.date >= date_from).where(Receipt.date <= date_to)
            .options(selectinload(Receipt.category), selectinload(Receipt.trip))
        )
        receipts = list(r.scalars().all())

    if exp_type in ("all", "trips"):
        r = await session.execute(
            select(Trip)
            .where(Trip.user_id == user.id)
            .where(Trip.date >= date_from).where(Trip.date <= date_to)
            .options(selectinload(Trip.vehicle))
        )
        trips = list(r.scalars().all())

    if exp_type in ("all", "incomes"):
        r = await session.execute(
            select(Income)
            .where(Income.user_id == user.id)
            .where(Income.date >= date_from).where(Income.date <= date_to)
        )
        incomes = list(r.scalars().all())

    total = len(receipts) + len(trips) + len(incomes)
    if total == 0:
        await callback.message.answer("📋 За вказаний період немає даних.")
        return

    if exp_type == "all":
        data_bytes = export_full_zip(receipts, trips, incomes, label)
        filename   = f"Fahrtenbuch_Export_{label}.zip"
        caption    = (f"📦 <b>Повний експорт — {label}</b>\n"
                      f"🧾 Чеків: {len(receipts)}  🚗 Поїздок: {len(trips)}  💶 Доходів: {len(incomes)}")
    elif exp_type == "receipts":
        data_bytes = export_receipts_csv(receipts)
        filename   = f"Belege_{label}.csv"
        caption    = f"🧾 <b>Чеки — {label}</b> ({len(receipts)} записів)"
    elif exp_type == "trips":
        data_bytes = export_trips_csv(trips)
        filename   = f"Fahrten_{label}.csv"
        caption    = f"🚗 <b>Поїздки — {label}</b> ({len(trips)} записів)"
    else:
        data_bytes = export_income_csv(incomes)
        filename   = f"Einnahmen_{label}.csv"
        caption    = f"💶 <b>Доходи — {label}</b> ({len(incomes)} записів)"

    await callback.message.answer_document(
        document=BufferedInputFile(data_bytes, filename=filename),
        caption=caption, parse_mode="HTML",
    )
    await callback.message.answer("Головне меню:", reply_markup=main_menu_kb(user.lang))
    await callback.answer()
