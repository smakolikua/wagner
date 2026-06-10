from __future__ import annotations

from datetime import date, datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, Vehicle, Address, Trip, TripPurpose
from ..keyboards import (
    trips_list_kb, trip_actions_kb, purpose_kb, month_filter_kb,
    vehicle_select_kb, address_select_kb, cancel_kb, confirm_kb,
)
from ..keyboards.main_menu import main_menu_kb, CANCEL_TEXTS
from ..i18n import t
from ..services.validators import validate_mileage, validate_date
from ..services.audit import log_audit, snapshot

router = Router(name="trips")
PER_PAGE = 8


class AddTripFSM(StatesGroup):
    waiting_vehicle       = State()
    waiting_date          = State()
    waiting_start         = State()
    waiting_start_manual  = State()
    waiting_end           = State()
    waiting_end_manual    = State()
    waiting_start_mileage = State()
    waiting_end_mileage   = State()
    waiting_purpose       = State()
    waiting_notes         = State()


class EditTripFSM(StatesGroup):
    choosing_field    = State()
    editing_date      = State()
    editing_purpose   = State()
    editing_notes     = State()
    editing_start_km  = State()
    editing_end_km    = State()


async def _get_trips(session, user_id, page=0, month=None, year=None):
    q = select(Trip).where(Trip.user_id == user_id)
    if month and year:
        end_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        q = q.where(and_(Trip.date >= date(year, month, 1), Trip.date < end_date))
    q = q.options(
        selectinload(Trip.vehicle),
        selectinload(Trip.start_address),
        selectinload(Trip.end_address),
    ).order_by(Trip.date.desc())
    result = await session.execute(q)
    all_trips = list(result.scalars().all())
    total = len(all_trips)
    return all_trips[page * PER_PAGE:(page + 1) * PER_PAGE], total


def _edit_kb(trip_id: int, lang: str) -> InlineKeyboardMarkup:
    fields = {
        "de": [("📅 Datum",    "date"), ("💼 Zweck",     "purpose"),
               ("📝 Notizen", "notes"), ("km Start",    "start_km"),
               ("km Ende",   "end_km")],
        "ua": [("📅 Дата",    "date"), ("💼 Мета",      "purpose"),
               ("📝 Нотатки","notes"), ("km початок", "start_km"),
               ("km кінець","end_km")],
        "ru": [("📅 Дата",    "date"), ("💼 Цель",      "purpose"),
               ("📝 Заметки","notes"), ("km начало",  "start_km"),
               ("km конец", "end_km")],
        "en": [("📅 Date",    "date"), ("💼 Purpose",   "purpose"),
               ("📝 Notes",  "notes"), ("km Start",    "start_km"),
               ("km End",   "end_km")],
    }
    b = InlineKeyboardBuilder()
    for label, field in fields.get(lang, fields["de"]):
        b.button(text=label, callback_data=f"trip:edit_field:{trip_id}:{field}")
    b.button(text=t("back", lang), callback_data=f"trip:view:{trip_id}")
    b.adjust(2)
    return b.as_markup()


# ─── Список поїздок ──────────────────────────────────────────────────────────

@router.message(Command("trips"))
async def cmd_trips(message: Message, session: AsyncSession, user: User):
    lang = user.lang
    trips, total = await _get_trips(session, user.id)
    if not trips:
        await message.answer(t("trips_empty", lang), reply_markup=trips_list_kb([], total=0))
    else:
        await message.answer(
            t("trips_title", lang, count=total),
            reply_markup=trips_list_kb(trips, page=0, total=total),
            parse_mode="HTML",
        )




@router.callback_query(F.data == "trip:list")
async def cb_trip_list(callback: CallbackQuery, session: AsyncSession, user: User):
    trips, total = await _get_trips(session, user.id)
    await callback.message.edit_text(
        t("trips_title", user.lang, count=total),
        reply_markup=trips_list_kb(trips, page=0, total=total),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("trip:page:"))
async def cb_trip_page(callback: CallbackQuery, session: AsyncSession, user: User):
    page = int(callback.data.split(":")[2])
    trips, total = await _get_trips(session, user.id, page=page)
    await callback.message.edit_reply_markup(reply_markup=trips_list_kb(trips, page=page, total=total))
    await callback.answer()


@router.callback_query(F.data == "trip:filter")
async def cb_trip_filter(callback: CallbackQuery, user: User):
    await callback.message.edit_text("🔍", reply_markup=month_filter_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("trip:filter_month:"))
async def cb_filter_month(callback: CallbackQuery, session: AsyncSession, user: User):
    _, _, year, month = callback.data.split(":")
    trips, total = await _get_trips(session, user.id, month=int(month), year=int(year))
    label = date(int(year), int(month), 1).strftime("%B %Y")
    await callback.message.edit_text(
        t("trips_title", user.lang, count=total) + f"\n<i>{label}</i>",
        reply_markup=trips_list_kb(trips, total=total),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "trip:filter_all")
async def cb_filter_all(callback: CallbackQuery, session: AsyncSession, user: User):
    trips, total = await _get_trips(session, user.id)
    await callback.message.edit_text(
        t("trips_title", user.lang, count=total),
        reply_markup=trips_list_kb(trips, total=total),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("trip:view:"))
async def cb_trip_view(callback: CallbackQuery, session: AsyncSession, user: User):
    trip_id = int(callback.data.split(":")[2])
    trip = await session.get(Trip, trip_id, options=[
        selectinload(Trip.vehicle), selectinload(Trip.start_address), selectinload(Trip.end_address),
    ])
    if not trip or trip.user_id != user.id:
        await callback.answer(t("not_found", user.lang), show_alert=True)
        return
    icon = "💼" if trip.purpose == TripPurpose.BUSINESS else "🏠"
    auto_tag = "\n🤖 <i>GPS auto</i>" if trip.is_auto else ""
    text = (
        f"🚗 <b>Trip #{trip.id}</b>\n\n"
        f"📅 {trip.date.strftime('%d.%m.%Y')}\n"
        f"🚘 {trip.vehicle.display_name}\n"
        f"▶️ {trip.start_label}\n"
        f"🏁 {trip.end_label}\n"
        f"📊 {int(trip.start_mileage):,} → {int(trip.end_mileage):,} km\n"
        f"📏 <b>{trip.distance} km</b>\n"
        f"{icon} {trip.purpose.value}\n"
        + (f"📝 {trip.notes}\n" if trip.notes else "")
        + auto_tag
    )
    await callback.message.edit_text(text, reply_markup=trip_actions_kb(trip_id), parse_mode="HTML")
    await callback.answer()


# ─── Видалення ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("trip:delete:"))
async def cb_delete_trip(callback: CallbackQuery, session: AsyncSession, user: User):
    trip_id = int(callback.data.split(":")[2])
    trip = await session.get(Trip, trip_id)
    if not trip or trip.user_id != user.id:
        await callback.answer(t("not_found", user.lang), show_alert=True)
        return
    await callback.message.edit_text(
        f"🗑 {trip.date.strftime('%d.%m.%Y')} | {trip.start_label} → {trip.end_label} | {trip.distance} km",
        reply_markup=confirm_kb(f"trip:delete_confirm:{trip_id}", "trip:list", user.lang),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("trip:delete_confirm:"))
async def cb_delete_confirm(callback: CallbackQuery, session: AsyncSession, user: User):
    trip_id = int(callback.data.split(":")[2])
    trip = await session.get(Trip, trip_id)
    if not trip or trip.user_id != user.id:
        await callback.answer(t("not_found", user.lang), show_alert=True)
        return
    before = snapshot(trip, ["date", "start_mileage", "end_mileage", "purpose", "notes"])
    await session.delete(trip)
    await log_audit(
        session, user, "delete", "trip", f"Поїздку видалено: {trip.date} / {trip.distance} km",
        entity_id=trip_id, telegram_id=callback.from_user.id, before=before,
    )
    await session.commit()
    await callback.message.edit_text(t("trip_deleted", user.lang))
    await callback.answer()


# ─── Редагування поїздки ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("trip:edit:"))
async def cb_trip_edit(callback: CallbackQuery, state: FSMContext, user: User):
    trip_id = int(callback.data.split(":")[2])
    await state.update_data(editing_trip_id=trip_id)
    await callback.message.edit_text(
        t("trip_edit_what", user.lang),
        reply_markup=_edit_kb(trip_id, user.lang),
        parse_mode="HTML",
    )
    await state.set_state(EditTripFSM.choosing_field)
    await callback.answer()


@router.callback_query(EditTripFSM.choosing_field, F.data.startswith("trip:edit_field:"))
async def cb_edit_field(callback: CallbackQuery, state: FSMContext, user: User):
    parts   = callback.data.split(":")
    trip_id = int(parts[2])
    field   = parts[3]
    lang    = user.lang

    await state.update_data(editing_trip_id=trip_id, editing_field=field)

    if field == "date":
        await callback.message.answer(t("trip_ask_date", lang), reply_markup=cancel_kb(lang))
        await state.set_state(EditTripFSM.editing_date)
    elif field == "purpose":
        await callback.message.answer(t("trip_ask_purpose", lang), reply_markup=purpose_kb())
        await state.set_state(EditTripFSM.editing_purpose)
    elif field == "notes":
        await callback.message.answer(t("trip_ask_notes", lang), reply_markup=cancel_kb(lang))
        await state.set_state(EditTripFSM.editing_notes)
    elif field == "start_km":
        await callback.message.answer(t("trip_ask_start_km", lang), reply_markup=cancel_kb(lang))
        await state.set_state(EditTripFSM.editing_start_km)
    elif field == "end_km":
        await callback.message.answer(t("trip_ask_end_km", lang), reply_markup=cancel_kb(lang))
        await state.set_state(EditTripFSM.editing_end_km)
    await callback.answer()


async def _apply_edit(state, session, user, **updates):
    data = await state.get_data()
    trip = await session.get(Trip, data["editing_trip_id"])
    if not trip or trip.user_id != user.id:
        return None
    before = snapshot(trip, list(updates.keys()))
    for k, v in updates.items():
        setattr(trip, k, v)
    await log_audit(
        session, user, "update", "trip", f"Поїздку оновлено: #{trip.id}",
        entity_id=trip.id, before=before, after=snapshot(trip, list(updates.keys())),
    )
    await session.commit()
    return trip


@router.message(EditTripFSM.editing_date, F.text)
async def edit_date(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear(); await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang)); return
    text = message.text.strip().lower()
    today_words = {"heute", "today", "сьогодні", "сегодня"}
    try:
        d = date.today() if text in today_words else datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer(t("date_format_error", user.lang)); return
    await _apply_edit(state, session, user, date=d)
    await state.clear()
    await message.answer(t("trip_updated", user.lang), reply_markup=main_menu_kb(user.lang))


@router.callback_query(EditTripFSM.editing_purpose, F.data.startswith("purpose:"))
async def edit_purpose(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    p = TripPurpose.BUSINESS if "sch" in callback.data else TripPurpose.PRIVATE
    await _apply_edit(state, session, user, purpose=p)
    await state.clear()
    await callback.message.answer(t("trip_updated", user.lang), reply_markup=main_menu_kb(user.lang))
    await callback.answer()


@router.message(EditTripFSM.editing_notes, F.text)
async def edit_notes(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear(); await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang)); return
    notes = None if message.text.strip() == "-" else message.text.strip()
    await _apply_edit(state, session, user, notes=notes)
    await state.clear()
    await message.answer(t("trip_updated", user.lang), reply_markup=main_menu_kb(user.lang))


async def _parse_km(text: str) -> float | None:
    cleaned = text.strip().replace(" ", "").replace(",", ".").replace(".", "", text.count(".") - 1)
    try:
        return float(cleaned)
    except ValueError:
        return None


def _norm_addr_text(text: str) -> str:
    return " ".join(text.strip().casefold().split())


async def _find_smart_address(session: AsyncSession, user_id: int, text: str) -> Address | None:
    needle = _norm_addr_text(text)
    if not needle:
        return None
    result = await session.execute(select(Address).where(Address.user_id == user_id))
    for address in result.scalars().all():
        label = _norm_addr_text(address.label)
        full = _norm_addr_text(address.address_str)
        if needle == label or needle == full:
            return address
        if len(needle) >= 4 and (needle in label or needle in full):
            return address
    return None


@router.message(EditTripFSM.editing_start_km, F.text)
async def edit_start_km(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear(); await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang)); return
    km = await _parse_km(message.text)
    if km is None:
        await message.answer(t("error_number", user.lang)); return
    await _apply_edit(state, session, user, start_mileage=km)
    await state.clear()
    await message.answer(t("trip_updated", user.lang), reply_markup=main_menu_kb(user.lang))


@router.message(EditTripFSM.editing_end_km, F.text)
async def edit_end_km(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear(); await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang)); return
    km = await _parse_km(message.text)
    if km is None:
        await message.answer(t("error_number", user.lang)); return
    data = await state.get_data()
    trip = await session.get(Trip, data["editing_trip_id"])
    if trip and km < trip.start_mileage:
        await message.answer(t("trip_mileage_error", user.lang)); return
    await _apply_edit(state, session, user, end_mileage=km)
    await state.clear()
    await message.answer(t("trip_updated", user.lang), reply_markup=main_menu_kb(user.lang))


# ─── Додавання поїздки вручну ────────────────────────────────────────────────

@router.message(Command("newtrip"))
@router.callback_query(F.data == "trip:add")
async def start_add_trip(event, state: FSMContext, session: AsyncSession, user: User):
    msg = event if isinstance(event, Message) else event.message
    lang = user.lang
    res = await session.execute(select(Vehicle).where(Vehicle.user_id == user.id))
    vehicles = list(res.scalars().all())
    if not vehicles:
        await msg.answer(t("no_vehicles", lang)); return
    if isinstance(event, CallbackQuery):
        await event.answer()
    await msg.answer(t("trip_ask_vehicle", lang), reply_markup=vehicle_select_kb(vehicles))
    await state.set_state(AddTripFSM.waiting_vehicle)




@router.callback_query(AddTripFSM.waiting_vehicle, F.data.startswith("select_vehicle:"))
async def fsm_vehicle(callback: CallbackQuery, state: FSMContext, user: User):
    await state.update_data(vehicle_id=int(callback.data.split(":")[1]))
    await callback.message.answer(t("trip_ask_date", user.lang), reply_markup=cancel_kb(user.lang))
    await state.set_state(AddTripFSM.waiting_date)
    await callback.answer()


@router.message(AddTripFSM.waiting_date, F.text)
async def fsm_date(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear(); await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang)); return
    text = message.text.strip().lower()
    today_words = {"heute", "today", "сьогодні", "сегодня"}
    try:
        d = date.today() if text in today_words else datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer(t("date_format_error", user.lang)); return
    v_result = validate_date(d)
    if not v_result.ok:
        await message.answer(f"⚠️ {v_result.error}"); return
    await state.update_data(trip_date=d.isoformat())
    res = await session.execute(select(Address).where(Address.user_id == user.id))
    addresses = list(res.scalars().all())
    await message.answer(t("trip_ask_from", user.lang), parse_mode="HTML",
                         reply_markup=address_select_kb(addresses, "trip_start", user.lang))
    await state.set_state(AddTripFSM.waiting_start)


@router.callback_query(AddTripFSM.waiting_start, F.data.startswith("trip_start:"))
async def fsm_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    val = callback.data.split(":")[1]
    if val == "manual":
        await callback.message.answer(t("trip_ask_from", user.lang), parse_mode="HTML")
        await state.set_state(AddTripFSM.waiting_start_manual)
    else:
        await state.update_data(start_address_id=int(val), start_address_text=None)
        res = await session.execute(select(Address).where(Address.user_id == user.id))
        addresses = list(res.scalars().all())
        await callback.message.answer(t("trip_ask_to", user.lang), parse_mode="HTML",
                                      reply_markup=address_select_kb(addresses, "trip_end", user.lang))
        await state.set_state(AddTripFSM.waiting_end)
    await callback.answer()


@router.message(AddTripFSM.waiting_start_manual, F.text)
async def fsm_start_manual(message: Message, state: FSMContext, session: AsyncSession, user: User):
    typed = message.text.strip()
    smart = await _find_smart_address(session, user.id, typed)
    if smart:
        await state.update_data(start_address_id=smart.id, start_address_text=None)
        await message.answer(f"✨ Адресу розпізнано: <b>{smart.label}</b>", parse_mode="HTML")
    else:
        await state.update_data(start_address_id=None, start_address_text=typed)
    res = await session.execute(select(Address).where(Address.user_id == user.id))
    addresses = list(res.scalars().all())
    await message.answer(t("trip_ask_to", user.lang), parse_mode="HTML",
                         reply_markup=address_select_kb(addresses, "trip_end", user.lang))
    await state.set_state(AddTripFSM.waiting_end)


@router.callback_query(AddTripFSM.waiting_end, F.data.startswith("trip_end:"))
async def fsm_end(callback: CallbackQuery, state: FSMContext, user: User):
    val = callback.data.split(":")[1]
    if val == "manual":
        await callback.message.answer(t("trip_ask_to", user.lang), parse_mode="HTML")
        await state.set_state(AddTripFSM.waiting_end_manual)
    else:
        await state.update_data(end_address_id=int(val), end_address_text=None)
        await callback.message.answer(t("trip_ask_start_km", user.lang), parse_mode="HTML")
        await state.set_state(AddTripFSM.waiting_start_mileage)
    await callback.answer()


@router.message(AddTripFSM.waiting_end_manual, F.text)
async def fsm_end_manual(message: Message, state: FSMContext, session: AsyncSession, user: User):
    typed = message.text.strip()
    smart = await _find_smart_address(session, user.id, typed)
    if smart:
        await state.update_data(end_address_id=smart.id, end_address_text=None)
        await message.answer(f"✨ Адресу розпізнано: <b>{smart.label}</b>", parse_mode="HTML")
    else:
        await state.update_data(end_address_id=None, end_address_text=typed)
    await message.answer(t("trip_ask_start_km", user.lang), parse_mode="HTML")
    await state.set_state(AddTripFSM.waiting_start_mileage)


@router.message(AddTripFSM.waiting_start_mileage, F.text)
async def fsm_start_km(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear(); await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang)); return
    km = await _parse_km(message.text)
    if km is None:
        await message.answer(t("error_number", user.lang)); return
    await state.update_data(start_mileage=km)
    # Підказка: очікуваний кінцевий пробіг = поточний пробіг авто
    data = await state.get_data()
    vehicle = await session.get(Vehicle, data["vehicle_id"])
    hint = ""
    if vehicle and vehicle.current_mileage > km:
        hint = f"\n💡 Поточний одометр авто: <b>{int(vehicle.current_mileage):,} км</b>"
    await message.answer(t("trip_ask_end_km", user.lang) + hint, parse_mode="HTML")
    await state.set_state(AddTripFSM.waiting_end_mileage)


@router.message(AddTripFSM.waiting_end_mileage, F.text)
async def fsm_end_km(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear(); await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang)); return
    km = await _parse_km(message.text)
    if km is None:
        await message.answer(t("error_number", user.lang)); return
    data = await state.get_data()
    v_result = validate_mileage(data["start_mileage"], km)
    if not v_result.ok:
        await message.answer(f"⚠️ {v_result.error}"); return
    await state.update_data(end_mileage=km)
    await message.answer(t("trip_ask_purpose", user.lang), parse_mode="HTML", reply_markup=purpose_kb())
    await state.set_state(AddTripFSM.waiting_purpose)


@router.callback_query(AddTripFSM.waiting_purpose, F.data.startswith("purpose:"))
async def fsm_purpose(callback: CallbackQuery, state: FSMContext, user: User):
    p = TripPurpose.BUSINESS if "sch" in callback.data else TripPurpose.PRIVATE
    await state.update_data(purpose=p)
    await callback.message.answer(t("trip_ask_notes", user.lang), reply_markup=cancel_kb(user.lang))
    await state.set_state(AddTripFSM.waiting_notes)
    await callback.answer()


@router.message(AddTripFSM.waiting_notes, F.text)
async def fsm_notes(message: Message, state: FSMContext, session: AsyncSession, user: User):
    notes = None if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    vehicle = await session.get(Vehicle, data["vehicle_id"])
    trip = Trip(
        user_id=user.id, vehicle_id=data["vehicle_id"],
        date=date.fromisoformat(data["trip_date"]),
        start_address_id=data.get("start_address_id"),
        end_address_id=data.get("end_address_id"),
        start_address_text=data.get("start_address_text"),
        end_address_text=data.get("end_address_text"),
        start_mileage=data["start_mileage"], end_mileage=data["end_mileage"],
        purpose=data["purpose"], notes=notes, is_auto=False,
    )
    session.add(trip)
    if vehicle and data["end_mileage"] > vehicle.current_mileage:
        vehicle.current_mileage = data["end_mileage"]
    await session.flush()
    await log_audit(
        session, user, "create", "trip", f"Поїздку створено: {trip.date} / {trip.distance} km",
        entity_id=trip.id, telegram_id=message.from_user.id,
        after=snapshot(trip, ["date", "start_mileage", "end_mileage", "purpose", "notes"]),
    )
    await session.commit()
    await state.clear()
    icon = "💼" if trip.purpose == TripPurpose.BUSINESS else "🏠"
    await message.answer(
        t("trip_added", user.lang, date=trip.date.strftime("%d.%m.%Y"),
          km=trip.distance, icon=icon, purpose=trip.purpose.value),
        reply_markup=main_menu_kb(user.lang), parse_mode="HTML",
    )
