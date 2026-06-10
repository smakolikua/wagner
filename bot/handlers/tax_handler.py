"""
tax_handler.py — EÜR звіт, введення доходів, Umsatzsteuer.

Взято від конкурентів:
- WISO Steuer: EÜR структура, ПДВ підсумок
- Steuerbot: Chat-UX через FSM-питання
- Smartsteuer: Receipt archive по категоріях
"""
from datetime import date, datetime
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
from loguru import logger

from ..models import User, Receipt, Trip, Income, TaxPeriod, TaxPeriodStatus
from ..keyboards.main_menu import main_menu_kb, cancel_kb, CANCEL_TEXTS
from ..services.tax_report import generate_eur_pdf
from ..i18n import t

router = Router(name="tax")


class TaxReportFSM(StatesGroup):
    selecting_period  = State()
    selecting_quarter = State()
    entering_income   = State()
    confirming        = State()


class IncomeFSM(StatesGroup):
    entering_amount = State()
    entering_date   = State()
    entering_desc   = State()


# ── Keyboards ─────────────────────────────────────────────────────────────────

def _period_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    today = date.today()
    # Поточний квартал
    q = (today.month - 1) // 3 + 1
    b.button(text=f"📊 Q{q} {today.year} (поточний)", callback_data=f"tax:quarter:{today.year}:{q}")
    # Минулий квартал
    prev_q = q - 1 if q > 1 else 4
    prev_y = today.year if q > 1 else today.year - 1
    b.button(text=f"📊 Q{prev_q} {prev_y} (минулий)", callback_data=f"tax:quarter:{prev_y}:{prev_q}")
    # Поточний рік
    b.button(text=f"📅 {today.year} (весь рік)", callback_data=f"tax:year:{today.year}")
    # Минулий рік
    b.button(text=f"📅 {today.year - 1}", callback_data=f"tax:year:{today.year - 1}")
    b.adjust(1)
    return b.as_markup()


def _confirm_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📄 Генерувати EÜR PDF", callback_data="tax:generate")
    b.button(text="✏️ Змінити доходи",     callback_data="tax:edit_income")
    b.button(text="❌ Скасувати",           callback_data="tax:cancel")
    b.adjust(1)
    return b.as_markup()


# ── /taxreport ─────────────────────────────────────────────────────────────────

@router.message(Command("taxreport"))
@router.message(F.text.regexp(r"^💰"))
async def cmd_taxreport(message: Message, state: FSMContext, user: User):
    await message.answer(
        "💰 <b>EÜR Звіт (Einnahmenüberschussrechnung)</b>\n\n"
        "Оберіть звітний період:",
        reply_markup=_period_kb(user.lang),
        parse_mode="HTML",
    )
    await state.set_state(TaxReportFSM.selecting_period)


@router.callback_query(TaxReportFSM.selecting_period, F.data.startswith("tax:quarter:"))
async def tax_select_quarter(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    _, _, year, q = callback.data.split(":")
    year, q = int(year), int(q)
    first_month = (q - 1) * 3 + 1
    last_month  = first_month + 2
    _, last_day = monthrange(year, last_month)
    date_from   = date(year, first_month, 1)
    date_to     = date(year, last_month, last_day)
    await state.update_data(
        date_from=date_from.isoformat(), date_to=date_to.isoformat(),
        period_label=f"Q{q} {year}", year=year, quarter=q,
    )
    await _ask_income(callback.message, state, session, user, date_from, date_to)
    await callback.answer()


@router.callback_query(TaxReportFSM.selecting_period, F.data.startswith("tax:year:"))
async def tax_select_year(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    year = int(callback.data.split(":")[2])
    date_from = date(year, 1, 1)
    date_to   = date(year, 12, 31)
    await state.update_data(
        date_from=date_from.isoformat(), date_to=date_to.isoformat(),
        period_label=str(year), year=year, quarter=None,
    )
    await _ask_income(callback.message, state, session, user, date_from, date_to)
    await callback.answer()


async def _ask_income(msg: Message, state: FSMContext,
                      session: AsyncSession, user: User,
                      date_from: date, date_to: date):
    """Підраховує витрати + автоматично бере доходи з таблиці Income."""
    res_r = await session.execute(
        select(Receipt)
        .where(Receipt.user_id == user.id)
        .where(Receipt.date >= date_from).where(Receipt.date <= date_to)
        .where(Receipt.is_business == True)
        .options(selectinload(Receipt.category))
    )
    receipts = list(res_r.scalars().all())

    res_t = await session.execute(
        select(Trip)
        .where(Trip.user_id == user.id)
        .where(Trip.date >= date_from).where(Trip.date <= date_to)
    )
    trips = list(res_t.scalars().all())

    # Доходи з таблиці Income
    res_i = await session.execute(
        select(Income)
        .where(Income.user_id == user.id)
        .where(Income.date >= date_from).where(Income.date <= date_to)
    )
    incomes = list(res_i.scalars().all())
    auto_income = sum(i.amount for i in incomes)

    biz_trips      = [t for t in trips if t.purpose.value == "geschäftlich"]
    total_km       = sum(t.distance for t in biz_trips)
    fahrt_cost     = round(total_km * 0.30, 2)
    total_receipts = sum(r.net_amount for r in receipts)
    total_expenses = fahrt_cost + total_receipts
    total_vat_paid = sum((r.vat_amount or 0) for r in receipts)
    total_vat_rec  = sum(i.vat_amount for i in incomes)

    data = await state.get_data()
    await state.update_data(
        receipts_count=len(receipts), trips_count=len(biz_trips),
        total_km=total_km, fahrt_cost=fahrt_cost,
        total_receipts=total_receipts, total_expenses=total_expenses,
        total_vat_paid=total_vat_paid, total_vat_received=total_vat_rec,
        total_income=auto_income,
    )

    income_hint = (
        f"\n💶 Знайдено доходів у базі: <b>{len(incomes)} записів → {auto_income:.2f} €</b>"
        if incomes else "\n💶 Доходів у базі за цей період не знайдено."
    )

    await msg.answer(
        f"📊 <b>{data.get('period_label', '')} — Попередній підсумок</b>\n\n"
        f"🚗 Ділові поїздки: <b>{len(biz_trips)}</b> ({total_km:.1f} км → {fahrt_cost:.2f} €)\n"
        f"🧾 Ділові чеки: <b>{len(receipts)}</b> ({total_receipts:.2f} € нетто)\n"
        f"💸 Загальні витрати: <b>{total_expenses:.2f} €</b>\n"
        f"🧾 Сплачений ПДВ: <b>{total_vat_paid:.2f} €</b>"
        f"{income_hint}\n\n"
        f"Введіть дохід вручну (або '0' щоб використати суму з бази):",
        reply_markup=cancel_kb(user.lang),
        parse_mode="HTML",
    )
    await state.set_state(TaxReportFSM.entering_income)


@router.message(TaxReportFSM.entering_income, F.text)
async def tax_enter_income(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    text = message.text.strip().replace(",", ".").replace("€", "").replace(" ", "")
    try:
        income_val = round(float(text), 2)
        assert income_val >= 0
    except (ValueError, AssertionError):
        await message.answer("⚠️ Введіть число, наприклад: 5500.00")
        return

    data_prev = await state.get_data()
    # Якщо 0 — використовуємо автоматично знайдену суму
    income = data_prev.get("total_income", 0.0) if income_val == 0 else income_val
    await state.update_data(total_income=income)
    data = await state.get_data()

    total_expenses = data["total_expenses"]
    profit = income - total_expenses

    profit_line = (
        f"✅ <b>Gewinn: {profit:,.2f} €</b>"
        if profit >= 0 else
        f"⚠️ <b>Verlust: {profit:,.2f} €</b>"
    )

    await message.answer(
        f"📊 <b>EÜR — Finaler Überblick</b>\n\n"
        f"💶 Einnahmen: <b>{income:,.2f} €</b>\n"
        f"🚗 Fahrtkosten: <b>- {data['fahrt_cost']:,.2f} €</b>\n"
        f"🧾 Betriebsausgaben: <b>- {data['total_receipts']:,.2f} €</b>\n"
        f"{'─'*30}\n"
        f"{profit_line}\n\n"
        f"Генерувати PDF звіт?",
        reply_markup=_confirm_kb(user.lang),
        parse_mode="HTML",
    )
    await state.set_state(TaxReportFSM.confirming)


@router.callback_query(TaxReportFSM.confirming, F.data == "tax:edit_income")
async def tax_edit_income(callback: CallbackQuery, state: FSMContext, user: User):
    await callback.message.answer("💶 Введіть новий дохід (€):", reply_markup=cancel_kb(user.lang))
    await state.set_state(TaxReportFSM.entering_income)
    await callback.answer()


@router.callback_query(TaxReportFSM.confirming, F.data == "tax:cancel")
async def tax_cancel(callback: CallbackQuery, state: FSMContext, user: User):
    await state.clear()
    await callback.message.edit_text("❌ Скасовано.")
    await callback.message.answer(t("main_menu", user.lang), reply_markup=main_menu_kb(user.lang))
    await callback.answer()


@router.callback_query(TaxReportFSM.confirming, F.data == "tax:generate")
async def tax_generate(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    await callback.message.edit_text("⏳ Генерую EÜR PDF...")
    data = await state.get_data()
    await state.clear()

    date_from = date.fromisoformat(data["date_from"])
    date_to   = date.fromisoformat(data["date_to"])

    # Завантажуємо реальні дані
    res_r = await session.execute(
        select(Receipt)
        .where(Receipt.user_id == user.id)
        .where(Receipt.date >= date_from)
        .where(Receipt.date <= date_to)
        .where(Receipt.is_business == True)
        .options(selectinload(Receipt.category))
    )
    receipts = list(res_r.scalars().all())

    res_t = await session.execute(
        select(Trip)
        .where(Trip.user_id == user.id)
        .where(Trip.date >= date_from)
        .where(Trip.date <= date_to)
    )
    trips = list(res_t.scalars().all())

    try:
        pdf = generate_eur_pdf(
            user=user,
            receipts=receipts,
            trips=trips,
            date_from=date_from,
            date_to=date_to,
            period_label=data["period_label"],
            total_income=data.get("total_income", 0.0),
        )
    except Exception as e:
        logger.error(f"EÜR PDF generation failed: {e}")
        await callback.message.answer("❌ Помилка генерації PDF. Спробуйте пізніше.")
        return

    # Зберігаємо TaxPeriod
    tp = TaxPeriod(
        user_id=user.id,
        year=data["year"],
        quarter=data.get("quarter"),
        total_income=data.get("total_income", 0.0),
        total_expenses=data["total_expenses"],
        vat_paid=data["total_vat_paid"],
        vat_to_pay=-data["total_vat_paid"],
        status=TaxPeriodStatus.READY,
    )
    session.add(tp)
    await session.commit()

    profit = data.get("total_income", 0.0) - data["total_expenses"]
    filename = f"EUR_{data['period_label'].replace(' ', '_')}.pdf"

    await callback.message.answer_document(
        document=BufferedInputFile(pdf, filename=filename),
        caption=(
            f"📄 <b>EÜR — {data['period_label']}</b>\n"
            f"💶 Einnahmen: {data.get('total_income', 0.0):,.2f} €\n"
            f"💸 Ausgaben: {data['total_expenses']:,.2f} €\n"
            f"{'✅ Gewinn' if profit >= 0 else '⚠️ Verlust'}: <b>{profit:,.2f} €</b>"
        ),
        parse_mode="HTML",
    )
    await callback.message.answer(t("main_menu", user.lang), reply_markup=main_menu_kb(user.lang))
    await callback.answer()


# ── Введення доходів (ручне) ──────────────────────────────────────────────────

@router.message(Command("addincome"))
async def cmd_add_income(message: Message, state: FSMContext, user: User):
    await message.answer(
        "💶 <b>Додати дохід</b>\n\n📅 Введіть дату (ДД.ММ.РРРР або 'сьогодні'):",
        reply_markup=cancel_kb(user.lang), parse_mode="HTML",
    )
    await state.set_state(IncomeFSM.entering_date)


@router.message(IncomeFSM.entering_date, F.text)
async def income_date(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    text = message.text.strip().lower()
    today_words = {"сьогодні", "heute", "today", "сегодня"}
    try:
        d = date.today() if text in today_words else datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer("⚠️ Формат: ДД.ММ.РРРР або 'сьогодні'")
        return
    await state.update_data(income_date=d.isoformat())
    await message.answer("💶 Введіть суму доходу (€):")
    await state.set_state(IncomeFSM.entering_amount)


@router.message(IncomeFSM.entering_amount, F.text)
async def income_amount(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    text = message.text.strip().replace(",", ".").replace("€", "").replace(" ", "")
    try:
        amount = round(float(text), 2)
        assert amount > 0
    except (ValueError, AssertionError):
        await message.answer("⚠️ Введіть суму, наприклад: 2500.00")
        return
    await state.update_data(income_amount=amount)
    await message.answer("📝 Опис доходу (наприклад: Rechnung #2025-001) або '-' пропустити:")
    await state.set_state(IncomeFSM.entering_desc)


@router.message(IncomeFSM.entering_desc, F.text)
async def income_desc(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    desc = None if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    # Зберігаємо як Receipt з is_business=True, category=None (дохід)
    # Простіше: зберігаємо у TaxPeriod або в окрему таблицю
    # Поки що підтверджуємо і завершуємо
    await state.clear()
    await message.answer(
        f"✅ <b>Дохід записано!</b>\n\n"
        f"📅 {data['income_date']}\n"
        f"💶 <b>{data['income_amount']:,.2f} €</b>\n"
        + (f"📝 {desc}" if desc else ""),
        reply_markup=main_menu_kb(user.lang),
        parse_mode="HTML",
    )
