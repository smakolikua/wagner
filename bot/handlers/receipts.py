"""
receipts.py — обробка фото чеків, CRUD, ручне введення.

Flow автоматичного розпізнавання:
  фото → OCR/AI → preview + підтвердження категорії → збереження

Flow ручного введення:
  /newreceipt → дата → сума → категорія → збереження
"""
import io
from datetime import date, datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, PhotoSize,
    InlineKeyboardMarkup, BufferedInputFile,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from ..models import User, Receipt, Category, TaxCode
from ..keyboards.main_menu import main_menu_kb, cancel_kb, CANCEL_TEXTS
from ..services.ocr_service import extract_receipt_data, format_ocr_preview, OCRResult
from ..services.validators import validate_date
from ..services.audit import log_audit, snapshot
from ..i18n import t

router = Router(name="receipts")

PER_PAGE = 8


# ── FSM ──────────────────────────────────────────────────────────────────────

class PhotoReceiptFSM(StatesGroup):
    """Автоматичне розпізнавання з фото."""
    confirming          = State()   # показуємо preview, чекаємо підтвердження
    selecting_category  = State()   # юзер змінює категорію
    entering_vendor     = State()   # якщо vendor не розпізнано
    entering_amount     = State()   # якщо сума не розпізнана
    entering_date       = State()   # якщо дата не розпізнана


class ManualReceiptFSM(StatesGroup):
    """Ручне введення без фото."""
    waiting_date        = State()
    waiting_amount      = State()
    waiting_vendor      = State()
    waiting_description = State()
    waiting_category    = State()
    waiting_vat         = State()


class EditReceiptFSM(StatesGroup):
    editing_date        = State()
    editing_amount      = State()
    editing_vendor      = State()
    editing_description = State()


# ── Клавіатури ───────────────────────────────────────────────────────────────

async def _category_kb(session: AsyncSession, prefix: str = "rcat") -> InlineKeyboardMarkup:
    """Inline-клавіатура вибору категорії."""
    result = await session.execute(
        select(Category)
        .where(Category.is_default == True)
        .order_by(Category.sort_order)
    )
    categories = list(result.scalars().all())
    b = InlineKeyboardBuilder()
    for cat in categories:
        b.button(text=cat.name, callback_data=f"{prefix}:{cat.id}")
    b.adjust(2)
    return b.as_markup()


def _confirm_ocr_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Підтвердити", callback_data="ocr:confirm")
    b.button(text="✏️ Змінити категорію", callback_data="ocr:change_cat")
    b.button(text="💶 Змінити суму", callback_data="ocr:change_amount")
    b.button(text="📅 Змінити дату", callback_data="ocr:change_date")
    b.button(text="🏠/💼 Тип витрати", callback_data="ocr:toggle_type")
    b.button(text="🗑 Скасувати", callback_data="ocr:cancel")
    b.adjust(1)
    return b.as_markup()


def _receipts_list_kb(receipts: list, page: int, total: int, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for r in receipts:
        cat_name = r.category.name if r.category else "—"
        icon = "💼" if r.is_business else "🏠"
        b.button(
            text=f"{icon} {r.date.strftime('%d.%m')} · {r.amount_gross:.2f}€ · {cat_name[:15]}",
            callback_data=f"receipt:view:{r.id}",
        )
    nav = []
    if page > 0:
        nav.append(("◀️", f"receipt:page:{page-1}"))
    if (page + 1) * PER_PAGE < total:
        nav.append(("▶️", f"receipt:page:{page+1}"))
    for label, data in nav:
        b.button(text=label, callback_data=data)
    b.button(text="➕ Додати вручну", callback_data="receipt:manual")
    b.button(text="🔍 Фільтр", callback_data="receipt:filter")
    b.button(text="📊 Статистика", callback_data="receipt:stats")
    b.adjust(1)
    return b.as_markup()


def _receipt_actions_kb(receipt_id: int, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Редагувати", callback_data=f"receipt:edit:{receipt_id}")
    b.button(text="🏷 Змінити категорію", callback_data=f"receipt:cat:{receipt_id}")
    b.button(text="🗑 Видалити", callback_data=f"receipt:delete:{receipt_id}")
    b.button(text="◀️ Назад", callback_data="receipt:list")
    b.adjust(1)
    return b.as_markup()


def _receipt_edit_kb(receipt_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📅 Дата", callback_data=f"receipt:edit_field:{receipt_id}:date")
    b.button(text="💶 Сума", callback_data=f"receipt:edit_field:{receipt_id}:amount")
    b.button(text="🏪 Постачальник", callback_data=f"receipt:edit_field:{receipt_id}:vendor")
    b.button(text="📝 Опис", callback_data=f"receipt:edit_field:{receipt_id}:description")
    b.button(text="🏠/💼 Тип витрати", callback_data=f"receipt:toggle_biz:{receipt_id}")
    b.button(text="◀️ Назад", callback_data=f"receipt:view:{receipt_id}")
    b.adjust(1)
    return b.as_markup()


# ── Список чеків ─────────────────────────────────────────────────────────────

@router.message(Command("receipts"))
@router.message(F.text.regexp(r"^🧾"))
async def cmd_receipts(message: Message, session: AsyncSession, user: User):
    lang = user.lang
    q = (select(Receipt)
         .where(Receipt.user_id == user.id)
         .options(selectinload(Receipt.category))
         .order_by(Receipt.date.desc()))
    result = await session.execute(q)
    all_receipts = list(result.scalars().all())
    total = len(all_receipts)
    page_receipts = all_receipts[:PER_PAGE]

    if not all_receipts:
        await message.answer(
            "🧾 <b>Чеки та витрати</b>\n\n"
            "Ще немає жодного чека.\n"
            "Надішліть фото чека або додайте вручну:",
            reply_markup=_receipts_list_kb([], 0, 0, lang),
            parse_mode="HTML",
        )
        return

    total_eur = sum(r.amount_gross for r in all_receipts)
    biz_eur   = sum(r.amount_gross for r in all_receipts if r.is_business)

    await message.answer(
        f"🧾 <b>Чеки та витрати</b> ({total} шт.)\n"
        f"💶 Загалом: <b>{total_eur:.2f} €</b>  |  Ділові: <b>{biz_eur:.2f} €</b>",
        reply_markup=_receipts_list_kb(page_receipts, 0, total, lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "receipt:list")
async def cb_receipt_list(callback: CallbackQuery, session: AsyncSession, user: User):
    result = await session.execute(
        select(Receipt).where(Receipt.user_id == user.id)
        .options(selectinload(Receipt.category))
        .order_by(Receipt.date.desc())
    )
    receipts = list(result.scalars().all())
    total = len(receipts)
    await callback.message.edit_text(
        f"🧾 <b>Чеки та витрати</b> ({total} шт.)",
        reply_markup=_receipts_list_kb(receipts[:PER_PAGE], 0, total, user.lang),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("receipt:page:"))
async def cb_receipt_page(callback: CallbackQuery, session: AsyncSession, user: User):
    page = int(callback.data.split(":")[2])
    result = await session.execute(
        select(Receipt).where(Receipt.user_id == user.id)
        .options(selectinload(Receipt.category))
        .order_by(Receipt.date.desc())
    )
    all_r = list(result.scalars().all())
    page_r = all_r[page * PER_PAGE:(page + 1) * PER_PAGE]
    await callback.message.edit_reply_markup(
        reply_markup=_receipts_list_kb(page_r, page, len(all_r), user.lang)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("receipt:view:"))
async def cb_receipt_view(callback: CallbackQuery, session: AsyncSession, user: User):
    rid = int(callback.data.split(":")[2])
    r = await session.get(Receipt, rid, options=[selectinload(Receipt.category)])
    if not r or r.user_id != user.id:
        await callback.answer("Не знайдено.", show_alert=True)
        return
    cat = r.category.name if r.category else "—"
    icon = "💼" if r.is_business else "🏠"
    text = (
        f"🧾 <b>Чек #{r.id}</b>\n\n"
        f"📅 {r.date.strftime('%d.%m.%Y')}\n"
        f"💶 <b>{r.amount_gross:.2f} €</b>"
        + (f" (нетто: {r.amount_net:.2f} €, ПДВ {r.vat_rate}%: {r.vat_amount:.2f} €)"
           if r.vat_rate else "") + "\n"
        f"🏪 {r.vendor or '—'}\n"
        f"🏷 {cat}  {icon}\n"
        + (f"📝 {r.description}\n" if r.description else "")
        + (f"🎯 AI впевненість: {r.ai_confidence:.0%}\n" if r.ai_confidence else "")
    )
    await callback.message.edit_text(
        text, reply_markup=_receipt_actions_kb(rid, user.lang), parse_mode="HTML"
    )
    await callback.answer()


# ── Фото → OCR ───────────────────────────────────────────────────────────────

@router.message(F.photo)
async def handle_photo(message: Message, state: FSMContext, session: AsyncSession, user: User):
    """Перехоплює будь-яке фото і запускає OCR."""
    # Беремо найякісніше фото (останнє в масиві)
    photo: PhotoSize = message.photo[-1]
    await message.answer("🔍 Розпізнаю чек...")

    try:
        file = await message.bot.get_file(photo.file_id)
        buf = await message.bot.download_file(file.file_path)
        image_bytes = buf.read()
    except Exception as e:
        logger.error(f"Photo download failed: {e}")
        await message.answer("❌ Не вдалося завантажити фото. Спробуйте ще раз.")
        return

    result: OCRResult = await extract_receipt_data(image_bytes, user.lang)

    if not result.success:
        await message.answer(
            f"⚠️ {result.error}\n\nДодати чек вручну?",
            reply_markup=_manual_or_skip_kb(),
        )
        return

    # Зберігаємо дані в FSM
    await state.update_data(
        ocr_photo_file_id=photo.file_id,
        ocr_amount_gross=result.amount_gross,
        ocr_amount_net=result.amount_net,
        ocr_vat_amount=result.vat_amount,
        ocr_vat_rate=result.vat_rate,
        ocr_date=result.date.isoformat() if result.date else None,
        ocr_vendor=result.vendor,
        ocr_description=result.description,
        ocr_suggested_cat=result.suggested_category,
        ocr_is_business=result.is_business,
        ocr_confidence=result.confidence,
        ocr_raw_text=result.raw_text,
    )

    preview = format_ocr_preview(result, user.lang)

    # Якщо впевненість низька — попереджаємо
    if result.confidence < 0.6:
        preview = "⚠️ Низька якість розпізнавання. Перевірте дані!\n\n" + preview

    await message.answer(
        preview + "\n\nПідтвердити?",
        reply_markup=_confirm_ocr_kb(user.lang),
        parse_mode="HTML",
    )
    await state.set_state(PhotoReceiptFSM.confirming)


def _manual_or_skip_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✍️ Ввести вручну", callback_data="receipt:manual")
    b.button(text="❌ Скасувати",     callback_data="receipt:skip")
    b.adjust(2)
    return b.as_markup()


@router.callback_query(F.data == "receipt:skip")
async def receipt_skip(callback: CallbackQuery, state: FSMContext, user: User):
    await state.clear()
    await callback.message.edit_text("❌ Скасовано.")
    await callback.message.answer(t("main_menu", user.lang), reply_markup=main_menu_kb(user.lang))
    await callback.answer()


# ── Підтвердження OCR ────────────────────────────────────────────────────────

@router.callback_query(PhotoReceiptFSM.confirming, F.data == "ocr:confirm")
async def ocr_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    data = await state.get_data()
    await _save_ocr_receipt(data, session, user)
    await state.clear()
    await callback.message.edit_text("✅ <b>Чек збережено!</b>", parse_mode="HTML")
    await callback.message.answer(t("main_menu", user.lang), reply_markup=main_menu_kb(user.lang))
    await callback.answer()


@router.callback_query(PhotoReceiptFSM.confirming, F.data == "ocr:toggle_type")
async def ocr_toggle_type(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_type = not data.get("ocr_is_business", True)
    await state.update_data(ocr_is_business=new_type)
    icon = "💼 Ділова" if new_type else "🏠 Приватна"
    await callback.answer(f"Тип змінено: {icon}", show_alert=False)


@router.callback_query(PhotoReceiptFSM.confirming, F.data == "ocr:change_cat")
async def ocr_change_cat(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    kb = await _category_kb(session, prefix="ocr_cat")
    await callback.message.answer("🏷 Оберіть категорію:", reply_markup=kb)
    await state.set_state(PhotoReceiptFSM.selecting_category)
    await callback.answer()


@router.callback_query(PhotoReceiptFSM.selecting_category, F.data.startswith("ocr_cat:"))
async def ocr_set_cat(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    cat_id = int(callback.data.split(":")[1])
    cat = await session.get(Category, cat_id)
    await state.update_data(ocr_category_id=cat_id, ocr_suggested_cat=cat.name if cat else None)
    await state.set_state(PhotoReceiptFSM.confirming)
    await callback.message.edit_text(f"✅ Категорія: <b>{cat.name}</b>", parse_mode="HTML")
    await callback.answer()


@router.callback_query(PhotoReceiptFSM.confirming, F.data == "ocr:change_amount")
async def ocr_change_amount(callback: CallbackQuery, state: FSMContext, user: User):
    await callback.message.answer("💶 Введіть суму (€):", reply_markup=cancel_kb(user.lang))
    await state.set_state(PhotoReceiptFSM.entering_amount)
    await callback.answer()


@router.message(PhotoReceiptFSM.entering_amount, F.text)
async def ocr_enter_amount(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.set_state(PhotoReceiptFSM.confirming)
        await message.answer("Скасовано.")
        return
    text = message.text.strip().replace(",", ".").replace(" ", "").replace("€", "")
    try:
        amount = round(float(text), 2)
    except ValueError:
        await message.answer("⚠️ Введіть число, наприклад: 12.50")
        return
    await state.update_data(ocr_amount_gross=amount, ocr_amount_net=amount, ocr_vat_amount=0.0, ocr_vat_rate=0)
    await state.set_state(PhotoReceiptFSM.confirming)
    await message.answer(f"✅ Сума: <b>{amount:.2f} €</b>", parse_mode="HTML")


@router.callback_query(PhotoReceiptFSM.confirming, F.data == "ocr:change_date")
async def ocr_change_date(callback: CallbackQuery, state: FSMContext, user: User):
    await callback.message.answer("📅 Введіть дату (ДД.ММ.РРРР):", reply_markup=cancel_kb(user.lang))
    await state.set_state(PhotoReceiptFSM.entering_date)
    await callback.answer()


@router.message(PhotoReceiptFSM.entering_date, F.text)
async def ocr_enter_date(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.set_state(PhotoReceiptFSM.confirming)
        await message.answer("Скасовано.")
        return
    try:
        d = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("⚠️ Формат: ДД.ММ.РРРР")
        return
    v = validate_date(d)
    if not v.ok:
        await message.answer(f"⚠️ {v.error}")
        return
    await state.update_data(ocr_date=d.isoformat())
    await state.set_state(PhotoReceiptFSM.confirming)
    await message.answer(f"✅ Дата: <b>{d.strftime('%d.%m.%Y')}</b>", parse_mode="HTML")


@router.callback_query(PhotoReceiptFSM.confirming, F.data == "ocr:cancel")
async def ocr_cancel(callback: CallbackQuery, state: FSMContext, user: User):
    await state.clear()
    await callback.message.edit_text("❌ Скасовано.")
    await callback.message.answer(t("main_menu", user.lang), reply_markup=main_menu_kb(user.lang))
    await callback.answer()


async def _save_ocr_receipt(data: dict, session: AsyncSession, user: User):
    """Зберігає чек з OCR-даних."""
    # Знаходимо категорію
    cat_id = data.get("ocr_category_id")
    if not cat_id and data.get("ocr_suggested_cat"):
        result = await session.execute(
            select(Category).where(Category.name == data["ocr_suggested_cat"]).limit(1)
        )
        cat = result.scalar_one_or_none()
        if cat:
            cat_id = cat.id

    receipt = Receipt(
        user_id=user.id,
        category_id=cat_id,
        date=date.fromisoformat(data["ocr_date"]) if data.get("ocr_date") else date.today(),
        amount_gross=data.get("ocr_amount_gross") or 0.0,
        amount_net=data.get("ocr_amount_net"),
        vat_amount=data.get("ocr_vat_amount"),
        vat_rate=data.get("ocr_vat_rate") or 0,
        vendor=data.get("ocr_vendor"),
        description=data.get("ocr_description"),
        photo_file_id=data.get("ocr_photo_file_id"),
        raw_ocr_text=data.get("ocr_raw_text"),
        ai_confidence=data.get("ocr_confidence"),
        is_business=data.get("ocr_is_business", True),
        is_verified=True,
    )
    session.add(receipt)
    await session.flush()
    await log_audit(
        session, user, "create", "receipt", f"Чек створено: {receipt.amount_gross:.2f} €",
        entity_id=receipt.id,
        after=snapshot(receipt, ["date", "amount_gross", "vat_rate", "vendor", "description", "is_business"]),
    )
    await session.commit()
    return receipt


# ── Ручне введення ────────────────────────────────────────────────────────────

@router.message(Command("newreceipt"))
@router.callback_query(F.data == "receipt:manual")
async def start_manual_receipt(event, state: FSMContext, user: User):
    msg = event if isinstance(event, Message) else event.message
    lang = user.lang
    if isinstance(event, CallbackQuery):
        await event.answer()
    await msg.answer(
        "✍️ <b>Додавання чека вручну</b>\n\n📅 Введіть дату (ДД.ММ.РРРР або 'сьогодні'):",
        reply_markup=cancel_kb(lang), parse_mode="HTML",
    )
    await state.set_state(ManualReceiptFSM.waiting_date)


@router.message(ManualReceiptFSM.waiting_date, F.text)
async def manual_date(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    text = message.text.strip().lower()
    today_words = {"сьогодні", "сегодня", "heute", "today"}
    try:
        d = date.today() if text in today_words else datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer("⚠️ Формат: ДД.ММ.РРРР або 'сьогодні'")
        return
    v = validate_date(d)
    if not v.ok:
        await message.answer(f"⚠️ {v.error}")
        return
    await state.update_data(m_date=d.isoformat())
    await message.answer("💶 Введіть суму з ПДВ (наприклад: 12.50):")
    await state.set_state(ManualReceiptFSM.waiting_amount)


@router.message(ManualReceiptFSM.waiting_amount, F.text)
async def manual_amount(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    text = message.text.strip().replace(",", ".").replace("€", "").replace(" ", "")
    try:
        amount = round(float(text), 2)
        assert amount > 0
    except (ValueError, AssertionError):
        await message.answer("⚠️ Введіть суму, наприклад: 12.50")
        return
    await state.update_data(m_amount=amount)
    await message.answer("🏪 Назва постачальника/магазину (або '-' пропустити):")
    await state.set_state(ManualReceiptFSM.waiting_vendor)


@router.message(ManualReceiptFSM.waiting_vendor, F.text)
async def manual_vendor(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    vendor = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(m_vendor=vendor)
    await message.answer("📝 Опис витрати (або '-' пропустити):")
    await state.set_state(ManualReceiptFSM.waiting_description)


@router.message(ManualReceiptFSM.waiting_description, F.text)
async def manual_description(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    desc = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(m_description=desc)
    kb = await _category_kb(session, prefix="mcat")
    await message.answer("🏷 Оберіть категорію витрати:", reply_markup=kb)
    await state.set_state(ManualReceiptFSM.waiting_category)


@router.callback_query(ManualReceiptFSM.waiting_category, F.data.startswith("mcat:"))
async def manual_category(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    cat_id = int(callback.data.split(":")[1])
    cat = await session.get(Category, cat_id)
    await state.update_data(m_category_id=cat_id)

    # ПДВ тільки для ділових витрат
    if cat and cat.tax_code.value != "Privat":
        b = InlineKeyboardBuilder()
        b.button(text="0% (без ПДВ)",  callback_data="mvat:0")
        b.button(text="7% (знижена)",  callback_data="mvat:7")
        b.button(text="19% (стандарт)",callback_data="mvat:19")
        b.adjust(3)
        await callback.message.answer("🧾 Ставка ПДВ:", reply_markup=b.as_markup())
        await state.set_state(ManualReceiptFSM.waiting_vat)
    else:
        await _finalize_manual(callback.message, state, session, user, vat_rate=0)

    await callback.answer()


@router.callback_query(ManualReceiptFSM.waiting_vat, F.data.startswith("mvat:"))
async def manual_vat(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    vat_rate = int(callback.data.split(":")[1])
    await callback.answer()
    await _finalize_manual(callback.message, state, session, user, vat_rate)


async def _finalize_manual(msg: Message, state: FSMContext,
                            session: AsyncSession, user: User, vat_rate: int):
    data = await state.get_data()
    amount_gross = data["m_amount"]
    amount_net   = round(amount_gross / (1 + vat_rate / 100), 2) if vat_rate else amount_gross
    vat_amount   = round(amount_gross - amount_net, 2) if vat_rate else 0.0
    cat = await session.get(Category, data.get("m_category_id"))
    is_biz = cat.tax_code != TaxCode.PRIVAT if cat else True

    receipt = Receipt(
        user_id=user.id,
        category_id=data.get("m_category_id"),
        date=date.fromisoformat(data["m_date"]),
        amount_gross=amount_gross,
        amount_net=amount_net,
        vat_amount=vat_amount,
        vat_rate=vat_rate,
        vendor=data.get("m_vendor"),
        description=data.get("m_description"),
        is_business=is_biz,
        is_verified=True,
    )
    session.add(receipt)
    await session.commit()
    await state.clear()

    cat_name = cat.name if cat else "—"
    await msg.answer(
        f"✅ <b>Чек збережено!</b>\n\n"
        f"📅 {receipt.date.strftime('%d.%m.%Y')}\n"
        f"💶 <b>{receipt.amount_gross:.2f} €</b>"
        + (f" (ПДВ {vat_rate}%: {vat_amount:.2f} €)" if vat_rate else "") + "\n"
        f"🏷 {cat_name}",
        reply_markup=main_menu_kb(user.lang),
        parse_mode="HTML",
    )


# ── Редагування чеків ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("receipt:edit:"))
async def cb_edit_receipt(callback: CallbackQuery, session: AsyncSession, user: User):
    rid = int(callback.data.split(":")[2])
    r = await session.get(Receipt, rid)
    if not r or r.user_id != user.id:
        await callback.answer("Не знайдено.", show_alert=True)
        return
    await callback.message.edit_text(
        f"✏️ <b>Редагувати чек #{rid}</b>",
        reply_markup=_receipt_edit_kb(rid),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("receipt:edit_field:"))
async def cb_edit_receipt_field(callback: CallbackQuery, state: FSMContext, user: User):
    _, _, _, rid, field = callback.data.split(":")
    await state.update_data(edit_receipt_id=int(rid), edit_receipt_field=field)
    prompts = {
        "date": ("📅 Введіть дату (ДД.ММ.РРРР):", EditReceiptFSM.editing_date),
        "amount": ("💶 Введіть суму (€):", EditReceiptFSM.editing_amount),
        "vendor": ("🏪 Введіть постачальника або '-' щоб очистити:", EditReceiptFSM.editing_vendor),
        "description": ("📝 Введіть опис або '-' щоб очистити:", EditReceiptFSM.editing_description),
    }
    prompt, next_state = prompts[field]
    await callback.message.answer(prompt, reply_markup=cancel_kb(user.lang))
    await state.set_state(next_state)
    await callback.answer()


@router.message(EditReceiptFSM.editing_date, F.text)
async def edit_receipt_date(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    try:
        d = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("⚠️ Формат: ДД.ММ.РРРР")
        return
    v = validate_date(d)
    if not v.ok:
        await message.answer(f"⚠️ {v.error}")
        return
    data = await state.get_data()
    r = await session.get(Receipt, data["edit_receipt_id"])
    if not r or r.user_id != user.id:
        await message.answer("Не знайдено.")
        await state.clear()
        return
    before = snapshot(r, ["date"])
    r.date = d
    await log_audit(
        session, user, "update", "receipt", f"Дату чека оновлено: #{r.id}",
        entity_id=r.id, telegram_id=message.from_user.id,
        before=before, after=snapshot(r, ["date"]),
    )
    await session.commit()
    await state.clear()
    await message.answer("✅ Дату оновлено.", reply_markup=main_menu_kb(user.lang))


@router.message(EditReceiptFSM.editing_amount, F.text)
async def edit_receipt_amount(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    text = message.text.strip().replace(",", ".").replace("€", "").replace(" ", "")
    try:
        amount = round(float(text), 2)
        assert amount > 0
    except (ValueError, AssertionError):
        await message.answer("⚠️ Введіть суму, наприклад: 12.50")
        return
    data = await state.get_data()
    r = await session.get(Receipt, data["edit_receipt_id"])
    if not r or r.user_id != user.id:
        await message.answer("Не знайдено.")
        await state.clear()
        return
    before = snapshot(r, ["amount_gross", "amount_net", "vat_amount"])
    r.amount_gross = amount
    r.amount_net = round(amount / (1 + r.vat_rate / 100), 2) if r.vat_rate else amount
    r.vat_amount = round(amount - r.amount_net, 2) if r.vat_rate else 0.0
    await log_audit(
        session, user, "update", "receipt", f"Суму чека оновлено: #{r.id}",
        entity_id=r.id, telegram_id=message.from_user.id,
        before=before, after=snapshot(r, ["amount_gross", "amount_net", "vat_amount"]),
    )
    await session.commit()
    await state.clear()
    await message.answer("✅ Суму оновлено.", reply_markup=main_menu_kb(user.lang))


@router.message(EditReceiptFSM.editing_vendor, F.text)
async def edit_receipt_vendor(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    data = await state.get_data()
    r = await session.get(Receipt, data["edit_receipt_id"])
    if not r or r.user_id != user.id:
        await message.answer("Не знайдено.")
        await state.clear()
        return
    before = snapshot(r, ["vendor"])
    r.vendor = None if message.text.strip() == "-" else message.text.strip()
    await log_audit(
        session, user, "update", "receipt", f"Постачальника чека оновлено: #{r.id}",
        entity_id=r.id, telegram_id=message.from_user.id,
        before=before, after=snapshot(r, ["vendor"]),
    )
    await session.commit()
    await state.clear()
    await message.answer("✅ Постачальника оновлено.", reply_markup=main_menu_kb(user.lang))


@router.message(EditReceiptFSM.editing_description, F.text)
async def edit_receipt_description(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    data = await state.get_data()
    r = await session.get(Receipt, data["edit_receipt_id"])
    if not r or r.user_id != user.id:
        await message.answer("Не знайдено.")
        await state.clear()
        return
    before = snapshot(r, ["description"])
    r.description = None if message.text.strip() == "-" else message.text.strip()
    await log_audit(
        session, user, "update", "receipt", f"Опис чека оновлено: #{r.id}",
        entity_id=r.id, telegram_id=message.from_user.id,
        before=before, after=snapshot(r, ["description"]),
    )
    await session.commit()
    await state.clear()
    await message.answer("✅ Опис оновлено.", reply_markup=main_menu_kb(user.lang))


@router.callback_query(F.data.startswith("receipt:toggle_biz:"))
async def cb_toggle_receipt_biz(callback: CallbackQuery, session: AsyncSession, user: User):
    rid = int(callback.data.split(":")[2])
    r = await session.get(Receipt, rid)
    if not r or r.user_id != user.id:
        await callback.answer("Не знайдено.", show_alert=True)
        return
    before = snapshot(r, ["is_business"])
    r.is_business = not r.is_business
    await log_audit(
        session, user, "update", "receipt", f"Тип витрати оновлено: #{r.id}",
        entity_id=r.id, telegram_id=callback.from_user.id,
        before=before, after=snapshot(r, ["is_business"]),
    )
    await session.commit()
    await callback.answer("Тип витрати оновлено.", show_alert=True)
    await cb_receipt_view(callback, session, user)


@router.callback_query(F.data.startswith("receipt:cat:"))
async def cb_receipt_cat(callback: CallbackQuery, session: AsyncSession, user: User):
    rid = int(callback.data.split(":")[2])
    r = await session.get(Receipt, rid)
    if not r or r.user_id != user.id:
        await callback.answer("Не знайдено.", show_alert=True)
        return
    result = await session.execute(
        select(Category).where(Category.is_default == True).order_by(Category.sort_order)
    )
    cats = list(result.scalars().all())
    b = InlineKeyboardBuilder()
    for cat in cats:
        b.button(text=cat.name, callback_data=f"receipt:setcat:{rid}:{cat.id}")
    b.button(text="◀️ Назад", callback_data=f"receipt:view:{rid}")
    b.adjust(2)
    await callback.message.edit_text("🏷 Оберіть нову категорію:", reply_markup=b.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("receipt:setcat:"))
async def cb_receipt_setcat(callback: CallbackQuery, session: AsyncSession, user: User):
    _, _, rid, cat_id = callback.data.split(":")
    r = await session.get(Receipt, int(rid))
    cat = await session.get(Category, int(cat_id))
    if not r or r.user_id != user.id or not cat:
        await callback.answer("Не знайдено.", show_alert=True)
        return
    before = snapshot(r, ["category_id", "is_business"])
    r.category_id = cat.id
    r.is_business = cat.tax_code != TaxCode.PRIVAT
    await log_audit(
        session, user, "update", "receipt", f"Категорію чека оновлено: #{r.id}",
        entity_id=r.id, telegram_id=callback.from_user.id,
        before=before, after=snapshot(r, ["category_id", "is_business"]),
    )
    await session.commit()
    await callback.answer("Категорію оновлено.", show_alert=True)
    await cb_receipt_view(callback, session, user)


# ── Видалення ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("receipt:delete:"))
async def cb_delete_receipt(callback: CallbackQuery, session: AsyncSession, user: User):
    rid = int(callback.data.split(":")[2])
    r = await session.get(Receipt, rid)
    if not r or r.user_id != user.id:
        await callback.answer("Не знайдено.", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    b.button(text="✅ Так, видалити", callback_data=f"receipt:del_confirm:{rid}")
    b.button(text="❌ Ні",            callback_data=f"receipt:view:{rid}")
    b.adjust(2)
    await callback.message.edit_text(
        f"🗑 Видалити чек від {r.date.strftime('%d.%m.%Y')} на {r.amount_gross:.2f} €?",
        reply_markup=b.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("receipt:del_confirm:"))
async def cb_del_confirm(callback: CallbackQuery, session: AsyncSession, user: User):
    rid = int(callback.data.split(":")[2])
    r = await session.get(Receipt, rid)
    if not r or r.user_id != user.id:
        await callback.answer("Не знайдено.", show_alert=True)
        return
    before = snapshot(r, ["date", "amount_gross", "vat_rate", "vendor", "description", "is_business"])
    await session.delete(r)
    await log_audit(
        session, user, "delete", "receipt", f"Чек видалено: {r.amount_gross:.2f} €",
        entity_id=rid, telegram_id=callback.from_user.id, before=before,
    )
    await session.commit()
    await callback.message.edit_text("✅ Чек видалено.")
    await callback.answer()


# ── Статистика чеків ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "receipt:stats")
async def cb_receipt_stats(callback: CallbackQuery, session: AsyncSession, user: User):
    result = await session.execute(
        select(Receipt)
        .where(Receipt.user_id == user.id)
        .options(selectinload(Receipt.category))
    )
    receipts = list(result.scalars().all())
    if not receipts:
        await callback.answer("Статистика порожня.", show_alert=True)
        return

    total = sum(r.amount_gross for r in receipts)
    biz   = sum(r.amount_gross for r in receipts if r.is_business)
    vat   = sum((r.vat_amount or 0) for r in receipts if r.is_business)

    # По категоріях
    by_cat: dict[str, float] = {}
    for r in receipts:
        cat_name = r.category.name if r.category else "—"
        by_cat[cat_name] = by_cat.get(cat_name, 0) + r.amount_gross
    top = sorted(by_cat.items(), key=lambda x: -x[1])[:5]

    lines = [
        "📊 <b>Статистика витрат</b>\n",
        f"🧾 Чеків: <b>{len(receipts)}</b>",
        f"💶 Загальна сума: <b>{total:.2f} €</b>",
        f"💼 Ділові витрати: <b>{biz:.2f} €</b>",
        f"🧾 Всього ПДВ (VSt): <b>{vat:.2f} €</b>\n",
        "<b>По категоріях:</b>",
    ]
    for cat_name, amount in top:
        lines.append(f"  • {cat_name}: {amount:.2f} €")

    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()


# ── Фільтр по місяцю / категорії ─────────────────────────────────────────────

@router.callback_query(F.data == "receipt:filter")
async def cb_receipt_filter(callback: CallbackQuery, session: AsyncSession, user: User):
    from datetime import date as d
    today = d.today()
    b = InlineKeyboardBuilder()
    # Останні 6 місяців
    for i in range(6):
        m = (today.month - i - 1) % 12 + 1
        y = today.year if today.month - i > 0 else today.year - 1
        lbl = d(y, m, 1).strftime("%B %Y")
        b.button(text=f"📅 {lbl}", callback_data=f"receipt:fmonth:{y}:{m}")
    b.button(text="🏷 По категорії", callback_data="receipt:fcat")
    b.button(text="💼 Тільки ділові", callback_data="receipt:fbiz:1")
    b.button(text="🏠 Тільки приватні", callback_data="receipt:fbiz:0")
    b.button(text="◀️ Назад", callback_data="receipt:list")
    b.adjust(2)
    await callback.message.edit_text("🔍 Фільтр чеків:", reply_markup=b.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("receipt:fmonth:"))
async def cb_filter_month(callback: CallbackQuery, session: AsyncSession, user: User):
    from datetime import date as d
    from calendar import monthrange
    _, _, year, month = callback.data.split(":")
    year, month = int(year), int(month)
    _, last_day = monthrange(year, month)
    date_from, date_to = d(year, month, 1), d(year, month, last_day)

    result = await session.execute(
        select(Receipt)
        .where(Receipt.user_id == user.id)
        .where(Receipt.date >= date_from)
        .where(Receipt.date <= date_to)
        .options(selectinload(Receipt.category))
        .order_by(Receipt.date.desc())
    )
    receipts = list(result.scalars().all())
    total     = len(receipts)
    total_eur = sum(r.amount_gross for r in receipts)
    label     = d(year, month, 1).strftime("%B %Y")

    await callback.message.edit_text(
        f"🧾 <b>Чеки за {label}</b> ({total} шт.)\n💶 Сума: <b>{total_eur:.2f} €</b>",
        reply_markup=_receipts_list_kb(receipts[:PER_PAGE], 0, total, user.lang),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "receipt:fcat")
async def cb_filter_cat(callback: CallbackQuery, session: AsyncSession, user: User):
    result = await session.execute(
        select(Category).where(Category.is_default == True).order_by(Category.sort_order)
    )
    cats = list(result.scalars().all())
    b = InlineKeyboardBuilder()
    for cat in cats:
        b.button(text=cat.name, callback_data=f"receipt:fcat_id:{cat.id}")
    b.button(text="◀️ Назад", callback_data="receipt:filter")
    b.adjust(2)
    await callback.message.edit_text("🏷 Оберіть категорію:", reply_markup=b.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("receipt:fcat_id:"))
async def cb_filter_cat_id(callback: CallbackQuery, session: AsyncSession, user: User):
    cat_id = int(callback.data.split(":")[2])
    cat    = await session.get(Category, cat_id)
    result = await session.execute(
        select(Receipt)
        .where(Receipt.user_id == user.id)
        .where(Receipt.category_id == cat_id)
        .options(selectinload(Receipt.category))
        .order_by(Receipt.date.desc())
    )
    receipts  = list(result.scalars().all())
    total     = len(receipts)
    total_eur = sum(r.amount_gross for r in receipts)
    await callback.message.edit_text(
        f"🏷 <b>{cat.name if cat else '—'}</b> — {total} чеків\n💶 <b>{total_eur:.2f} €</b>",
        reply_markup=_receipts_list_kb(receipts[:PER_PAGE], 0, total, user.lang),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("receipt:fbiz:"))
async def cb_filter_biz(callback: CallbackQuery, session: AsyncSession, user: User):
    is_biz = callback.data.split(":")[2] == "1"
    result = await session.execute(
        select(Receipt)
        .where(Receipt.user_id == user.id)
        .where(Receipt.is_business == is_biz)
        .options(selectinload(Receipt.category))
        .order_by(Receipt.date.desc())
    )
    receipts  = list(result.scalars().all())
    total     = len(receipts)
    total_eur = sum(r.amount_gross for r in receipts)
    label     = "💼 Ділові" if is_biz else "🏠 Приватні"
    await callback.message.edit_text(
        f"{label} чеки — {total} шт.\n💶 <b>{total_eur:.2f} €</b>",
        reply_markup=_receipts_list_kb(receipts[:PER_PAGE], 0, total, user.lang),
        parse_mode="HTML",
    )
    await callback.answer()
