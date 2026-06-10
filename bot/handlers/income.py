"""
income.py — управління доходами (Einnahmen).

Команди: /incomes, /addincome
Функції: список, додавання (FSM), видалення, статистика по місяцях
"""
from datetime import date, datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, Income
from ..keyboards.main_menu import main_menu_kb, cancel_kb, CANCEL_TEXTS
from ..services.validators import validate_date
from ..services.audit import log_audit, snapshot
from ..i18n import t

router = Router(name="income")
PER_PAGE = 10


class AddIncomeFSM(StatesGroup):
    waiting_date           = State()
    waiting_amount         = State()
    waiting_vat            = State()
    waiting_client         = State()
    waiting_invoice        = State()
    waiting_description    = State()


def _list_kb(incomes: list, page: int, total: int, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for inc in incomes:
        client = f" · {inc.client_name[:12]}" if inc.client_name else ""
        inv    = f" #{inc.invoice_number}" if inc.invoice_number else ""
        b.button(
            text=f"💶 {inc.date.strftime('%d.%m')} · {inc.amount:.2f}€{client}{inv}",
            callback_data=f"inc:view:{inc.id}",
        )
    nav = []
    if page > 0:           nav.append(("◀️", f"inc:page:{page-1}"))
    if (page+1)*PER_PAGE < total: nav.append(("▶️", f"inc:page:{page+1}"))
    for lbl, cb in nav:
        b.button(text=lbl, callback_data=cb)
    b.button(text="➕ Додати дохід", callback_data="inc:add")
    b.button(text="📊 По місяцях",   callback_data="inc:monthly")
    b.adjust(1)
    return b.as_markup()


def _actions_kb(inc_id: int, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🗑 Видалити",  callback_data=f"inc:delete:{inc_id}")
    b.button(text="◀️ Назад",    callback_data="inc:list")
    b.adjust(2)
    return b.as_markup()


def _vat_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="0% Kleinunternehmer", callback_data="inc_vat:0")
    b.button(text="7% (ermäßigt)",       callback_data="inc_vat:7")
    b.button(text="19% (Regelsteuersatz)", callback_data="inc_vat:19")
    b.adjust(1)
    return b.as_markup()


async def _get_incomes(session, user_id, page=0):
    q = (select(Income).where(Income.user_id == user_id)
         .order_by(Income.date.desc()))
    result = await session.execute(q)
    all_inc = list(result.scalars().all())
    total   = len(all_inc)
    return all_inc[page*PER_PAGE:(page+1)*PER_PAGE], total


# ── Список доходів ────────────────────────────────────────────────────────────

@router.message(Command("incomes"))
async def cmd_incomes(message: Message, session: AsyncSession, user: User):
    incomes, total = await _get_incomes(session, user.id)
    all_result = await session.execute(select(Income).where(Income.user_id == user.id))
    all_inc    = list(all_result.scalars().all())
    total_eur  = sum(i.amount for i in all_inc)
    total_vat  = sum(i.vat_amount for i in all_inc)

    if not all_inc:
        await message.answer(
            "💶 <b>Доходи (Einnahmen)</b>\n\nЩе немає жодного запису.\nДодайте перший дохід:",
            reply_markup=_list_kb([], 0, 0, user.lang), parse_mode="HTML",
        )
        return

    await message.answer(
        f"💶 <b>Доходи (Einnahmen)</b> — {len(all_inc)} записів\n"
        f"Нетто: <b>{total_eur:.2f} €</b>  |  ПДВ отриманий: <b>{total_vat:.2f} €</b>\n"
        f"Брутто: <b>{total_eur + total_vat:.2f} €</b>",
        reply_markup=_list_kb(incomes, 0, total, user.lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "inc:list")
async def cb_inc_list(callback: CallbackQuery, session: AsyncSession, user: User):
    incomes, total = await _get_incomes(session, user.id)
    await callback.message.edit_text(
        f"💶 <b>Доходи</b> ({total})",
        reply_markup=_list_kb(incomes, 0, total, user.lang), parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("inc:page:"))
async def cb_inc_page(callback: CallbackQuery, session: AsyncSession, user: User):
    page = int(callback.data.split(":")[2])
    incomes, total = await _get_incomes(session, user.id, page)
    await callback.message.edit_reply_markup(
        reply_markup=_list_kb(incomes, page, total, user.lang)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("inc:view:"))
async def cb_inc_view(callback: CallbackQuery, session: AsyncSession, user: User):
    inc_id = int(callback.data.split(":")[2])
    inc    = await session.get(Income, inc_id)
    if not inc or inc.user_id != user.id:
        await callback.answer("Не знайдено.", show_alert=True); return
    lines = [
        f"💶 <b>Дохід #{inc.id}</b>\n",
        f"📅 {inc.date.strftime('%d.%m.%Y')}",
        f"💰 Нетто: <b>{inc.amount:.2f} €</b>",
    ]
    if inc.vat_rate:
        lines.append(f"🧾 ПДВ {inc.vat_rate}%: {inc.vat_amount:.2f} €")
        lines.append(f"💵 Брутто: {inc.gross_amount:.2f} €")
    if inc.client_name:    lines.append(f"👤 Клієнт: {inc.client_name}")
    if inc.invoice_number: lines.append(f"📄 Рахунок: #{inc.invoice_number}")
    if inc.description:    lines.append(f"📝 {inc.description}")
    if inc.is_kleinunternehmer: lines.append("ℹ️ <i>Kleinunternehmer (§ 19 UStG)</i>")
    await callback.message.edit_text(
        "\n".join(lines), reply_markup=_actions_kb(inc_id, user.lang), parse_mode="HTML",
    )
    await callback.answer()


# ── Місячна статистика ────────────────────────────────────────────────────────

@router.callback_query(F.data == "inc:monthly")
async def cb_inc_monthly(callback: CallbackQuery, session: AsyncSession, user: User):
    result = await session.execute(
        select(Income).where(Income.user_id == user.id).order_by(Income.date)
    )
    all_inc = list(result.scalars().all())
    if not all_inc:
        await callback.answer("Немає даних.", show_alert=True); return

    from collections import defaultdict
    monthly: dict[str, float] = defaultdict(float)
    monthly_vat: dict[str, float] = defaultdict(float)
    for inc in all_inc:
        key = inc.date.strftime("%m.%Y")
        monthly[key]     += inc.amount
        monthly_vat[key] += inc.vat_amount

    lines = ["📅 <b>Доходи по місяцях</b>\n"]
    for month in sorted(monthly.keys(), key=lambda x: (x[3:], x[:2]), reverse=True)[:12]:
        vat = monthly_vat[month]
        lines.append(
            f"<b>{month}</b>: {monthly[month]:.2f} €"
            + (f" (+ ПДВ {vat:.2f} €)" if vat else "")
        )
    total = sum(monthly.values())
    lines.append(f"\n💶 <b>Всього нетто: {total:.2f} €</b>")

    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад до списку", callback_data="inc:list")
    await callback.message.edit_text("\n".join(lines), reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()


# ── Додавання доходу (FSM) ────────────────────────────────────────────────────

@router.message(Command("addincome"))
@router.callback_query(F.data == "inc:add")
async def start_add_income(event, state: FSMContext, user: User):
    msg  = event if isinstance(event, Message) else event.message
    lang = user.lang
    if isinstance(event, CallbackQuery): await event.answer()
    await msg.answer(
        "💶 <b>Додавання доходу</b>\n\n📅 Введіть дату (ДД.ММ.РРРР або 'сьогодні'):",
        reply_markup=cancel_kb(lang), parse_mode="HTML",
    )
    await state.set_state(AddIncomeFSM.waiting_date)


@router.message(AddIncomeFSM.waiting_date, F.text)
async def income_date(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang)); return
    text = message.text.strip().lower()
    today_words = {"сьогодні", "сегодня", "heute", "today"}
    try:
        d = date.today() if text in today_words else datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer("⚠️ Формат: ДД.ММ.РРРР"); return
    v = validate_date(d)
    if not v.ok:
        await message.answer(f"⚠️ {v.error}"); return
    await state.update_data(inc_date=d.isoformat())
    await message.answer("💰 Введіть суму <b>нетто</b> (без ПДВ, €):", parse_mode="HTML")
    await state.set_state(AddIncomeFSM.waiting_amount)


@router.message(AddIncomeFSM.waiting_amount, F.text)
async def income_amount(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang)); return
    text = message.text.strip().replace(",", ".").replace("€", "").replace(" ", "")
    try:
        amount = round(float(text), 2)
        assert amount > 0
    except (ValueError, AssertionError):
        await message.answer("⚠️ Введіть суму, наприклад: 1500.00"); return
    await state.update_data(inc_amount=amount)
    await message.answer("🧾 Ставка ПДВ:", reply_markup=_vat_kb())
    await state.set_state(AddIncomeFSM.waiting_vat)


@router.callback_query(AddIncomeFSM.waiting_vat, F.data.startswith("inc_vat:"))
async def income_vat(callback: CallbackQuery, state: FSMContext, user: User):
    vat_rate = int(callback.data.split(":")[1])
    data     = await state.get_data()
    amount   = data["inc_amount"]
    vat_amt  = round(amount * vat_rate / 100, 2)
    is_klein = (vat_rate == 0)
    await state.update_data(inc_vat_rate=vat_rate, inc_vat_amount=vat_amt, inc_is_klein=is_klein)
    await callback.message.answer("👤 Ім'я клієнта (або '-' пропустити):")
    await state.set_state(AddIncomeFSM.waiting_client)
    await callback.answer()


@router.message(AddIncomeFSM.waiting_client, F.text)
async def income_client(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang)); return
    client = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(inc_client=client)
    await message.answer("📄 Номер рахунку-фактури (або '-' пропустити):")
    await state.set_state(AddIncomeFSM.waiting_invoice)


@router.message(AddIncomeFSM.waiting_invoice, F.text)
async def income_invoice(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang)); return
    inv = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(inc_invoice=inv)
    await message.answer("📝 Опис (або '-' пропустити):")
    await state.set_state(AddIncomeFSM.waiting_description)


@router.message(AddIncomeFSM.waiting_description, F.text)
async def income_desc(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang)); return
    desc = None if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()

    inc = Income(
        user_id        = user.id,
        date           = date.fromisoformat(data["inc_date"]),
        amount         = data["inc_amount"],
        vat_rate       = data["inc_vat_rate"],
        vat_amount     = data["inc_vat_amount"],
        client_name    = data.get("inc_client"),
        invoice_number = data.get("inc_invoice"),
        description    = desc,
        is_kleinunternehmer = data.get("inc_is_klein", False),
    )
    session.add(inc)
    await session.flush()
    await log_audit(
        session, user, "create", "income", f"Дохід створено: {inc.amount:.2f} €",
        entity_id=inc.id, telegram_id=message.from_user.id,
        after=snapshot(inc, ["date", "amount", "vat_rate", "vat_amount", "client_name", "invoice_number"]),
    )
    await session.commit()
    await state.clear()

    await message.answer(
        f"✅ <b>Дохід записано!</b>\n\n"
        f"📅 {inc.date.strftime('%d.%m.%Y')}\n"
        f"💰 Нетто: <b>{inc.amount:.2f} €</b>"
        + (f"\n🧾 ПДВ {inc.vat_rate}%: {inc.vat_amount:.2f} €\n💵 Брутто: {inc.gross_amount:.2f} €"
           if inc.vat_rate else "")
        + (f"\n👤 {inc.client_name}" if inc.client_name else "")
        + (f"\n📄 #{inc.invoice_number}" if inc.invoice_number else ""),
        reply_markup=main_menu_kb(user.lang), parse_mode="HTML",
    )


# ── Видалення ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("inc:delete:"))
async def cb_delete_income(callback: CallbackQuery, session: AsyncSession, user: User):
    inc_id = int(callback.data.split(":")[2])
    inc    = await session.get(Income, inc_id)
    if not inc or inc.user_id != user.id:
        await callback.answer("Не знайдено.", show_alert=True); return
    b = InlineKeyboardBuilder()
    b.button(text="✅ Так", callback_data=f"inc:del_ok:{inc_id}")
    b.button(text="❌ Ні",  callback_data=f"inc:view:{inc_id}")
    b.adjust(2)
    await callback.message.edit_text(
        f"🗑 Видалити дохід від {inc.date.strftime('%d.%m.%Y')} на {inc.amount:.2f} €?",
        reply_markup=b.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("inc:del_ok:"))
async def cb_del_ok(callback: CallbackQuery, session: AsyncSession, user: User):
    inc_id = int(callback.data.split(":")[2])
    inc    = await session.get(Income, inc_id)
    if not inc or inc.user_id != user.id:
        await callback.answer("Не знайдено.", show_alert=True); return
    before = snapshot(inc, ["date", "amount", "vat_rate", "vat_amount", "client_name", "invoice_number"])
    await session.delete(inc)
    await log_audit(
        session, user, "delete", "income", f"Дохід видалено: {inc.amount:.2f} €",
        entity_id=inc_id, telegram_id=callback.from_user.id, before=before,
    )
    await session.commit()
    await callback.message.edit_text("✅ Дохід видалено.")
    await callback.answer()
