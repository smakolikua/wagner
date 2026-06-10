from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, Document
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from ..models import User, Address, AddressType
from ..keyboards import addresses_list_kb, address_actions_kb, address_type_kb, address_select_kb
from ..keyboards.main_menu import main_menu_kb, cancel_kb, confirm_kb, CANCEL_TEXTS
from ..services import geocode_address, parse_addresses_csv, geocode_batch
from ..services.audit import log_audit, snapshot
from ..i18n import t

router = Router(name="addresses")


class AddAddressFSM(StatesGroup):
    waiting_label       = State()
    waiting_address_str = State()
    waiting_type        = State()


class EditAddressFSM(StatesGroup):
    waiting_label       = State()
    waiting_address_str = State()
    waiting_type        = State()


def _edit_address_kb(address_id: int) -> object:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="🏷 Назва", callback_data=f"addr:edit_field:{address_id}:label")
    b.button(text="🗺 Адреса", callback_data=f"addr:edit_field:{address_id}:address")
    b.button(text="📍 Тип", callback_data=f"addr:edit_field:{address_id}:type")
    b.button(text="◀️ Назад", callback_data=f"addr:view:{address_id}")
    b.adjust(1)
    return b.as_markup()


async def _get_addresses(session: AsyncSession, user: User) -> list[Address]:
    result = await session.execute(
        select(Address).where(Address.user_id == user.id).order_by(Address.type, Address.label)
    )
    return list(result.scalars().all())


@router.message(Command("addresses"))
async def cmd_addresses(message: Message, session: AsyncSession, user: User):
    lang = user.lang
    addresses = await _get_addresses(session, user)
    if not addresses:
        await message.answer(t("addresses_empty", lang), reply_markup=addresses_list_kb([]))
    else:
        await message.answer(
            t("addresses_title", lang, count=len(addresses)),
            reply_markup=addresses_list_kb(addresses),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "addr:list")
async def cb_addr_list(callback: CallbackQuery, session: AsyncSession, user: User):
    addresses = await _get_addresses(session, user)
    await callback.message.edit_text(
        t("addresses_title", user.lang, count=len(addresses)),
        reply_markup=addresses_list_kb(addresses),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("addr:view:"))
async def cb_addr_view(callback: CallbackQuery, session: AsyncSession, user: User):
    addr_id = int(callback.data.split(":")[2])
    addr = await session.get(Address, addr_id)
    if not addr or addr.user_id != user.id:
        await callback.answer(t("not_found", user.lang), show_alert=True)
        return
    is_home = user.home_address_id == addr_id
    coords = f"📌 {addr.lat:.5f}, {addr.lon:.5f}" if addr.has_coords else "📌 —"
    await callback.message.edit_text(
        f"📍 <b>{addr.label}</b>\n\n🏷 {addr.type.value}\n🗺 {addr.address_str}\n{coords}"
        + ("\n🏠 <i>Home</i>" if is_home else ""),
        reply_markup=address_actions_kb(addr_id, is_home=is_home),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "addr:add")
async def cb_addr_add(callback: CallbackQuery, state: FSMContext, user: User):
    await callback.message.answer(
        "📍 " + t("add_address", user.lang) + "\n\n"
        + ("Bezeichnung eingeben:" if user.lang == "de" else
           "Введіть назву:" if user.lang == "ua" else
           "Введите название:" if user.lang == "ru" else "Enter label:"),
        reply_markup=cancel_kb(user.lang),
    )
    await state.set_state(AddAddressFSM.waiting_label)
    await callback.answer()


@router.message(AddAddressFSM.waiting_label, F.text)
async def fsm_addr_label(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    await state.update_data(label=message.text.strip())
    prompt = ("Vollständige Adresse eingeben (Straße, Stadt):\n<i>z.B. Hauptstraße 1, 80331 München</i>"
              if user.lang == "de" else
              "Введіть <b>повну адресу</b> (вулиця, місто):\n<i>Напр.: Hauptstraße 1, 80331 München</i>"
              if user.lang == "ua" else
              "Введите <b>полный адрес</b> (улица, город):\n<i>Напр.: Hauptstraße 1, 80331 München</i>"
              if user.lang == "ru" else
              "Enter <b>full address</b> (street, city):\n<i>e.g. Hauptstraße 1, 80331 München</i>")
    await message.answer(prompt, parse_mode="HTML")
    await state.set_state(AddAddressFSM.waiting_address_str)


@router.message(AddAddressFSM.waiting_address_str, F.text)
async def fsm_addr_str(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    await state.update_data(address_str=message.text.strip())
    await message.answer(
        ("Adresstyp wählen:" if user.lang == "de" else
         "Оберіть тип адреси:" if user.lang == "ua" else
         "Выберите тип адреса:" if user.lang == "ru" else
         "Choose address type:"),
        reply_markup=address_type_kb(),
    )
    await state.set_state(AddAddressFSM.waiting_type)


@router.callback_query(AddAddressFSM.waiting_type, F.data.startswith("atype:"))
async def fsm_addr_type(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    type_map = {
        "Heimatadresse": AddressType.HOME, "Kunde": AddressType.CLIENT,
        "Büro": AddressType.OFFICE,        "Sonstiges": AddressType.OTHER,
    }
    addr_type = type_map.get(callback.data.split(":")[1], AddressType.OTHER)
    data = await state.get_data()
    await callback.message.edit_text(t("addr_geocoding", user.lang))

    coords = await geocode_address(data["address_str"])
    lat, lon = (coords[0], coords[1]) if coords else (None, None)

    addr = Address(
        user_id=user.id, label=data["label"],
        address_str=data["address_str"], type=addr_type,
        lat=lat, lon=lon,
    )
    session.add(addr)

    if addr_type == AddressType.HOME and not user.home_address_id:
        await session.flush()
        user.home_address_id = addr.id

    await session.flush()
    await log_audit(
        session, user, "create", "address", f"Адресу створено: {addr.label}",
        entity_id=addr.id, telegram_id=callback.from_user.id,
        after=snapshot(addr, ["label", "address_str", "type", "lat", "lon"]),
    )
    await session.commit()
    await state.clear()

    coords_text = f"📌 {lat:.5f}, {lon:.5f}" if coords else "⚠️ coords not found"
    await callback.message.edit_text(
        t("addr_added", user.lang, label=addr.label, type=addr.type.value,
          addr=addr.address_str) + f"\n{coords_text}",
        parse_mode="HTML",
    )
    await callback.message.answer(t("main_menu", user.lang), reply_markup=main_menu_kb(user.lang))
    await callback.answer()


@router.callback_query(F.data.startswith("addr:sethome:"))
async def cb_set_home(callback: CallbackQuery, session: AsyncSession, user: User):
    addr_id = int(callback.data.split(":")[2])
    addr = await session.get(Address, addr_id)
    if not addr or addr.user_id != user.id:
        await callback.answer(t("not_found", user.lang), show_alert=True)
        return
    user.home_address_id = addr_id
    await session.commit()
    await callback.answer(t("addr_home_set", user.lang), show_alert=True)


@router.callback_query(F.data.startswith("addr:edit:"))
async def cb_edit_addr(callback: CallbackQuery, session: AsyncSession, user: User):
    addr_id = int(callback.data.split(":")[2])
    addr = await session.get(Address, addr_id)
    if not addr or addr.user_id != user.id:
        await callback.answer(t("not_found", user.lang), show_alert=True)
        return
    await callback.message.edit_text(
        f"✏️ <b>{addr.label}</b>\n\nЩо змінити?",
        reply_markup=_edit_address_kb(addr_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("addr:edit_field:"))
async def cb_edit_addr_field(callback: CallbackQuery, state: FSMContext, user: User):
    _, _, _, addr_id, field = callback.data.split(":")
    await state.update_data(edit_addr_id=int(addr_id))
    if field == "label":
        await callback.message.answer("🏷 Введіть нову назву:", reply_markup=cancel_kb(user.lang))
        await state.set_state(EditAddressFSM.waiting_label)
    elif field == "address":
        await callback.message.answer("🗺 Введіть нову повну адресу:", reply_markup=cancel_kb(user.lang))
        await state.set_state(EditAddressFSM.waiting_address_str)
    elif field == "type":
        await callback.message.answer("📍 Оберіть новий тип:", reply_markup=address_type_kb())
        await state.set_state(EditAddressFSM.waiting_type)
    await callback.answer()


@router.message(EditAddressFSM.waiting_label, F.text)
async def edit_addr_label(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    label = message.text.strip()
    if not label:
        await message.answer("⚠️ Назва не може бути порожньою.")
        return
    data = await state.get_data()
    addr = await session.get(Address, data["edit_addr_id"])
    if not addr or addr.user_id != user.id:
        await message.answer(t("not_found", user.lang))
        await state.clear()
        return
    before = snapshot(addr, ["label"])
    addr.label = label
    await log_audit(
        session, user, "update", "address", f"Назву адреси оновлено: {label}",
        entity_id=addr.id, telegram_id=message.from_user.id,
        before=before, after=snapshot(addr, ["label"]),
    )
    await session.commit()
    await state.clear()
    await message.answer(t("saved", user.lang), reply_markup=main_menu_kb(user.lang))


@router.message(EditAddressFSM.waiting_address_str, F.text)
async def edit_addr_str(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    address_str = message.text.strip()
    if not address_str:
        await message.answer("⚠️ Адреса не може бути порожньою.")
        return
    data = await state.get_data()
    addr = await session.get(Address, data["edit_addr_id"])
    if not addr or addr.user_id != user.id:
        await message.answer(t("not_found", user.lang))
        await state.clear()
        return
    await message.answer(t("addr_geocoding", user.lang))
    coords = await geocode_address(address_str)
    before = snapshot(addr, ["address_str", "lat", "lon"])
    addr.address_str = address_str
    addr.lat, addr.lon = (coords[0], coords[1]) if coords else (None, None)
    await log_audit(
        session, user, "update", "address", f"Адресу оновлено: {addr.label}",
        entity_id=addr.id, telegram_id=message.from_user.id,
        before=before, after=snapshot(addr, ["address_str", "lat", "lon"]),
    )
    await session.commit()
    await state.clear()
    await message.answer(t("saved", user.lang), reply_markup=main_menu_kb(user.lang))


@router.callback_query(EditAddressFSM.waiting_type, F.data.startswith("atype:"))
async def edit_addr_type(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    type_map = {
        "Heimatadresse": AddressType.HOME, "Kunde": AddressType.CLIENT,
        "Büro": AddressType.OFFICE,        "Sonstiges": AddressType.OTHER,
    }
    addr_type = type_map.get(callback.data.split(":")[1], AddressType.OTHER)
    data = await state.get_data()
    addr = await session.get(Address, data["edit_addr_id"])
    if not addr or addr.user_id != user.id:
        await callback.answer(t("not_found", user.lang), show_alert=True)
        await state.clear()
        return
    before = snapshot(addr, ["type"])
    addr.type = addr_type
    if addr_type == AddressType.HOME:
        user.home_address_id = addr.id
    await log_audit(
        session, user, "update", "address", f"Тип адреси оновлено: {addr.label}",
        entity_id=addr.id, telegram_id=callback.from_user.id,
        before=before, after=snapshot(addr, ["type"]),
    )
    await session.commit()
    await state.clear()
    await callback.message.edit_text(t("saved", user.lang))
    await callback.message.answer(t("main_menu", user.lang), reply_markup=main_menu_kb(user.lang))
    await callback.answer()


@router.callback_query(F.data.startswith("addr:delete:"))
async def cb_delete_addr(callback: CallbackQuery, session: AsyncSession, user: User):
    addr_id = int(callback.data.split(":")[2])
    addr = await session.get(Address, addr_id)
    if not addr or addr.user_id != user.id:
        await callback.answer(t("not_found", user.lang), show_alert=True)
        return
    await callback.message.edit_text(
        f"🗑 <b>{addr.label}</b>?",
        reply_markup=confirm_kb(f"addr:delete_confirm:{addr_id}", "addr:list", user.lang),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("addr:delete_confirm:"))
async def cb_delete_addr_confirm(callback: CallbackQuery, session: AsyncSession, user: User):
    addr_id = int(callback.data.split(":")[2])
    addr = await session.get(Address, addr_id)
    if not addr or addr.user_id != user.id:
        await callback.answer(t("not_found", user.lang), show_alert=True)
        return
    label = addr.label
    before = snapshot(addr, ["label", "address_str", "type", "lat", "lon"])
    if user.home_address_id == addr_id:
        user.home_address_id = None
    await session.delete(addr)
    await log_audit(
        session, user, "delete", "address", f"Адресу видалено: {label}",
        entity_id=addr_id, telegram_id=callback.from_user.id, before=before,
    )
    await session.commit()
    await callback.message.edit_text(
        t("addr_deleted", user.lang, label=label), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "addr:csv")
async def cb_csv_import(callback: CallbackQuery, state: FSMContext, user: User):
    lang = user.lang
    example = (
        "📂 CSV-Import\n\n"
        "<code>name,address,type</code>\n\n"
        "Typen: <code>Heimatadresse</code>, <code>Kunde</code>, <code>Büro</code>, <code>Sonstiges</code>"
        if lang == "de" else
        "📂 Імпорт CSV\n\n"
        "Надішліть файл <code>.csv</code>:\n<code>name,address,type</code>\n\n"
        "Типи: <code>Heimatadresse</code>, <code>Kunde</code>, <code>Büro</code>, <code>Sonstiges</code>"
        if lang == "ua" else
        "📂 Импорт CSV\n\n"
        "Отправьте файл <code>.csv</code>:\n<code>name,address,type</code>\n\n"
        "Типы: <code>Heimatadresse</code>, <code>Kunde</code>, <code>Büro</code>, <code>Sonstiges</code>"
        if lang == "ru" else
        "📂 CSV Import\n\n"
        "Send a <code>.csv</code> file:\n<code>name,address,type</code>\n\n"
        "Types: <code>Heimatadresse</code>, <code>Kunde</code>, <code>Büro</code>, <code>Sonstiges</code>"
    )
    await callback.message.answer(example, parse_mode="HTML", reply_markup=cancel_kb(lang))
    await state.set_state("csv_waiting")
    await callback.answer()


@router.message(F.state == "csv_waiting", F.document)
async def handle_csv_upload(message: Message, state: FSMContext, session: AsyncSession, user: User):
    doc: Document = message.document
    if not doc.file_name.lower().endswith(".csv"):
        await message.answer("⚠️ .csv only")
        return
    await message.answer("⏳...")
    file = await message.bot.get_file(doc.file_id)
    content = await message.bot.download_file(file.file_path)
    raw = content.read()
    addresses, parse_errors = await parse_addresses_csv(raw)
    if parse_errors and not addresses:
        await message.answer("❌ " + "\n".join(parse_errors), reply_markup=main_menu_kb(user.lang))
        await state.clear()
        return
    await message.answer(f"⏳ geocoding {len(addresses)}...")
    geocoded, geo_errors = await geocode_batch(addresses)
    saved = 0
    for item in geocoded:
        session.add(Address(
            user_id=user.id, label=item["label"], address_str=item["address_str"],
            type=item["type"], lat=item.get("lat"), lon=item.get("lon"),
        ))
        saved += 1
    await session.commit()
    await state.clear()
    all_errors = parse_errors + geo_errors
    report = t("saved", user.lang) + f" {saved}"
    if all_errors:
        report += "\n⚠️ " + "\n".join(all_errors[:5])
    await message.answer(report, reply_markup=main_menu_kb(user.lang))
