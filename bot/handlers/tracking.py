"""
tracking.py — GPS Live Location handler (Фаза 2).

Покращення відносно Фази 1:
- TrackAccumulator: smooth distance по всіх точках треку
- Dwell detection: зупинка фіксується після 60 сек в радіусі 30 м
- Автоматичний запит мети при кожній невідомій зупинці
- Inline-кнопка "зберегти адресу?" після невідомої зупинки  
- Підсумок сесії при /stoptrack: кількість поїздок, загальний км
- Збереження нових адрес одразу при прибутті
- Захист від дублювання: одна сесія на користувача
"""

from __future__ import annotations

from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from ..models import User, Vehicle, Address, Trip, TripPurpose, LiveSession
from ..keyboards import vehicle_select_kb, cancel_kb, main_menu_kb
from ..services.geo import find_nearest_address, haversine_km, reverse_geocode, DwellEvent
from ..services.track_store import get_or_create, get, remove, has_active
from ..config import settings

router = Router(name="tracking")


class TrackingFSM(StatesGroup):
    selecting_vehicle = State()
    active            = State()   # live location йде сюди
    asking_purpose    = State()   # після невідомої зупинки
    asking_save_addr  = State()   # запит чи зберегти нову адресу
    asking_addr_label = State()   # ввід назви нової адреси


def _purpose_kb():
    b = InlineKeyboardBuilder()
    b.button(text="💼 geschäftlich", callback_data="trk_purpose:geschaeftlich")
    b.button(text="🏠 privat",        callback_data="trk_purpose:privat")
    b.adjust(2)
    return b.as_markup()


def _save_addr_kb():
    b = InlineKeyboardBuilder()
    b.button(text="✅ Так, зберегти", callback_data="trk_saveaddr:yes")
    b.button(text="❌ Ні",             callback_data="trk_saveaddr:no")
    b.adjust(2)
    return b.as_markup()


# ─── /track ──────────────────────────────────────────────────────────────────

@router.message(Command("track"))
async def cmd_track(message: Message, state: FSMContext, session: AsyncSession, user: User):
    # Перевірка активної сесії в БД
    res = await session.execute(
        select(LiveSession).where(
            LiveSession.user_id == user.id,
            LiveSession.ended_at.is_(None),
        )
    )
    active_db = res.scalar_one_or_none()
    if active_db:
        await message.answer(
            "📡 Трекінг вже активний!\n\n"
            "Надсилайте live-геолокацію — бот фіксує поїздки автоматично.\n"
            "Зупинити: /stoptrack"
        )
        return

    res = await session.execute(select(Vehicle).where(Vehicle.user_id == user.id))
    vehicles = list(res.scalars().all())
    if not vehicles:
        await message.answer("⚠️ Спочатку додайте авто в /cars")
        return

    await message.answer("🚗 Оберіть авто для трекінгу:", reply_markup=vehicle_select_kb(vehicles))
    await state.set_state(TrackingFSM.selecting_vehicle)


@router.callback_query(TrackingFSM.selecting_vehicle, F.data.startswith("select_vehicle:"))
async def tracking_vehicle_selected(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User
):
    vehicle_id = int(callback.data.split(":")[1])
    vehicle = await session.get(Vehicle, vehicle_id)
    if not vehicle or vehicle.user_id != user.id:
        await callback.answer("Авто не знайдено.", show_alert=True)
        return

    # Зберігаємо сесію в БД
    live = LiveSession(
        user_id=user.id,
        vehicle_id=vehicle_id,
        start_mileage=vehicle.current_mileage,
    )
    session.add(live)
    await session.commit()

    # Стартуємо акумулятор треку в пам'яті
    get_or_create(user.id)

    await state.update_data(live_session_id=live.id, vehicle_id=vehicle_id)
    await state.set_state(TrackingFSM.active)

    await callback.message.answer(
        f"✅ Трекінг активовано — <b>{vehicle.display_name}</b>\n"
        f"📊 Пробіг зараз: <b>{int(vehicle.current_mileage):,} км</b>\n\n"
        f"📡 Тепер надішліть <b>Live Location</b>:\n"
        f"<i>📎 Скріпка → Геолокація → Поділитися live-геолокацією</i>\n\n"
        f"Бот автоматично фіксує кожну зупинку ≥ 1 хв.\n"
        f"Зупинити трекінг: /stoptrack",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


# ─── Live Location updates ────────────────────────────────────────────────────

@router.message(TrackingFSM.active, F.location)
async def handle_live_location(
    message: Message, state: FSMContext, session: AsyncSession, user: User
):
    lat = message.location.latitude
    lon = message.location.longitude

    data = await state.get_data()
    live = await session.get(LiveSession, data.get("live_session_id"))
    if not live or not live.is_active:
        await message.answer("⚠️ Сесія трекінгу не знайдена. Запустіть /track знову.")
        await state.clear()
        return

    # Оновлюємо координати в БД-сесії
    live.last_lat = lat
    live.last_lon = lon
    live.last_update = datetime.now()

    # Додаємо точку в акумулятор
    acc = get_or_create(user.id)
    dwell = acc.add_point(lat, lon)

    if dwell is not None:
        # Зафіксована нова зупинка — шукаємо адресу
        res = await session.execute(select(Address).where(Address.user_id == user.id))
        addresses = list(res.scalars().all())
        nearest = find_nearest_address(lat, lon, addresses, radius_meters=settings.GEOFENCE_RADIUS_METERS)

        km_since_last = acc.flush_km()
        vehicle = await session.get(Vehicle, live.vehicle_id)
        start_mileage = vehicle.current_mileage
        end_mileage = round(start_mileage + km_since_last, 1)

        if nearest:
            # Відома адреса — пишемо поїздку автоматично
            if nearest.id != live.last_address_id:
                trip = Trip(
                    user_id=user.id,
                    vehicle_id=live.vehicle_id,
                    date=datetime.now().date(),
                    start_address_id=live.last_address_id,
                    end_address_id=nearest.id,
                    start_mileage=start_mileage,
                    end_mileage=end_mileage,
                    purpose=TripPurpose.BUSINESS,
                    is_auto=True,
                )
                session.add(trip)
                vehicle.current_mileage = end_mileage
                live.last_address_id = nearest.id

                await message.answer(
                    f"📍 <b>Прибуття зафіксовано</b>\n"
                    f"📌 {nearest.label} ({nearest.type.value})\n"
                    f"📏 +{km_since_last:.1f} км  |  Одометр: {int(end_mileage):,} км\n"
                    f"<i>Мета: geschäftlich — змінити /trips</i>",
                    parse_mode="HTML",
                )
        else:
            # Невідома зупинка — питаємо мету
            addr_str = await reverse_geocode(lat, lon) or f"{lat:.5f}, {lon:.5f}"
            await state.update_data(
                dwell_lat=lat,
                dwell_lon=lon,
                dwell_addr_str=addr_str,
                dwell_start_mileage=start_mileage,
                dwell_end_mileage=end_mileage,
            )
            await message.answer(
                f"❓ <b>Нова зупинка!</b>\n"
                f"<code>{addr_str[:100]}</code>\n\n"
                f"📏 +{km_since_last:.1f} км\n\n"
                f"Мета поїздки сюди?",
                reply_markup=_purpose_kb(),
                parse_mode="HTML",
            )
            await state.set_state(TrackingFSM.asking_purpose)
            await session.commit()
            return

    await session.commit()


# ─── Невідома зупинка: мета ──────────────────────────────────────────────────

@router.callback_query(TrackingFSM.asking_purpose, F.data.startswith("trk_purpose:"))
async def trk_set_purpose(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User
):
    purpose_raw = callback.data.split(":")[1]
    purpose = TripPurpose.BUSINESS if purpose_raw == "geschaeftlich" else TripPurpose.PRIVATE
    await state.update_data(dwell_purpose=purpose)

    await callback.message.edit_reply_markup()
    await callback.message.answer(
        f"{'💼' if purpose == TripPurpose.BUSINESS else '🏠'} <b>{purpose.value}</b>\n\n"
        f"Зберегти цю адресу для майбутніх поїздок?",
        reply_markup=_save_addr_kb(),
        parse_mode="HTML",
    )
    await state.set_state(TrackingFSM.asking_save_addr)
    await callback.answer()


@router.callback_query(TrackingFSM.asking_save_addr, F.data.startswith("trk_saveaddr:"))
async def trk_save_addr_choice(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User
):
    choice = callback.data.split(":")[1]
    await callback.message.edit_reply_markup()

    if choice == "yes":
        await callback.message.answer("Введіть назву для цього місця:")
        await state.set_state(TrackingFSM.asking_addr_label)
    else:
        # Зберігаємо поїздку без нової адреси
        await _save_dwell_trip(state, session, user, label=None)
        await callback.message.answer(
            "✅ Поїздку записано.",
            reply_markup=cancel_kb(),
        )
        await state.set_state(TrackingFSM.active)

    await callback.answer()


@router.message(TrackingFSM.asking_addr_label, F.text)
async def trk_addr_label(
    message: Message, state: FSMContext, session: AsyncSession, user: User
):
    label = message.text.strip()
    new_addr = await _save_dwell_trip(state, session, user, label=label)

    if new_addr:
        await message.answer(
            f"✅ Адресу <b>{label}</b> збережено та поїздку записано!",
            reply_markup=cancel_kb(),
            parse_mode="HTML",
        )
    else:
        await message.answer("✅ Поїздку записано.", reply_markup=cancel_kb())

    await state.set_state(TrackingFSM.active)


async def _save_dwell_trip(
    state: FSMContext,
    session: AsyncSession,
    user: User,
    label: str | None,
) -> Address | None:
    """Зберігає Trip та (опціонально) нову Address після зупинки."""
    data = await state.get_data()
    live = await session.get(LiveSession, data.get("live_session_id"))
    vehicle = await session.get(Vehicle, data.get("vehicle_id"))

    purpose = data.get("dwell_purpose", TripPurpose.BUSINESS)
    start_mileage = data["dwell_start_mileage"]
    end_mileage   = data["dwell_end_mileage"]
    addr_str      = data.get("dwell_addr_str", "")
    lat           = data["dwell_lat"]
    lon           = data["dwell_lon"]

    new_addr: Address | None = None
    end_address_id = None

    if label:
        new_addr = Address(
            user_id=user.id,
            label=label,
            address_str=addr_str,
            lat=lat,
            lon=lon,
        )
        session.add(new_addr)
        await session.flush()
        end_address_id = new_addr.id
        if live:
            live.last_address_id = new_addr.id

    trip = Trip(
        user_id=user.id,
        vehicle_id=data["vehicle_id"],
        date=datetime.now().date(),
        start_address_id=live.last_address_id if live and not label else (live.last_address_id if live else None),
        end_address_id=end_address_id,
        end_address_text=addr_str if not label else None,
        start_mileage=start_mileage,
        end_mileage=end_mileage,
        purpose=purpose,
        is_auto=True,
    )
    session.add(trip)

    if vehicle:
        vehicle.current_mileage = end_mileage

    await session.commit()
    return new_addr


# ─── /stoptrack ──────────────────────────────────────────────────────────────

@router.message(Command("stoptrack"))
async def cmd_stoptrack(
    message: Message, state: FSMContext, session: AsyncSession, user: User
):
    res = await session.execute(
        select(LiveSession).where(
            LiveSession.user_id == user.id,
            LiveSession.ended_at.is_(None),
        )
    )
    live = res.scalar_one_or_none()
    if not live:
        await message.answer("ℹ️ Активного трекінгу немає.")
        return

    live.ended_at = datetime.now()

    # Підсумок сесії
    acc = get(user.id)
    leftover_km = acc.flush_km() if acc else 0.0
    remove(user.id)

    # Поїздки за цю сесію
    res = await session.execute(
        select(Trip).where(
            Trip.user_id == user.id,
            Trip.is_auto == True,
            Trip.created_at >= live.started_at,
        )
    )
    session_trips = list(res.scalars().all())
    total_km  = sum(t.distance for t in session_trips)
    biz_km    = sum(t.distance for t in session_trips if t.purpose == TripPurpose.BUSINESS)
    priv_km   = sum(t.distance for t in session_trips if t.purpose == TripPurpose.PRIVATE)
    duration  = datetime.now() - live.started_at
    hours, rem = divmod(int(duration.total_seconds()), 3600)
    mins = rem // 60

    await session.commit()
    await state.clear()

    await message.answer(
        f"🏁 <b>Трекінг завершено</b>\n\n"
        f"⏱ Тривалість: {hours}г {mins}хв\n"
        f"📋 Поїздок: <b>{len(session_trips)}</b>\n"
        f"📏 Загальний пробіг: <b>{total_km:.1f} км</b>\n"
        f"  💼 Ділових: {biz_km:.1f} км\n"
        f"  🏠 Приватних: {priv_km:.1f} км\n\n"
        f"Повний журнал: /trips\nPDF-звіт: /report",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


# ─── Статус трекінгу ──────────────────────────────────────────────────────────

@router.message(Command("trackstatus"))
async def cmd_trackstatus(message: Message, session: AsyncSession, user: User):
    res = await session.execute(
        select(LiveSession).where(
            LiveSession.user_id == user.id,
            LiveSession.ended_at.is_(None),
        )
    )
    live = res.scalar_one_or_none()
    if not live:
        await message.answer("ℹ️ Трекінг не активний. Запустити: /track")
        return

    acc = get(user.id)
    km = acc.total_km if acc else 0.0
    pts = acc.point_count if acc else 0
    duration = datetime.now() - live.started_at
    hours, rem = divmod(int(duration.total_seconds()), 3600)
    mins = rem // 60

    await message.answer(
        f"📡 <b>Трекінг активний</b>\n\n"
        f"⏱ Тривалість: {hours}г {mins}хв\n"
        f"📍 GPS-точок: {pts}\n"
        f"📏 Накопичено: {km:.1f} км\n\n"
        f"Зупинити: /stoptrack",
        parse_mode="HTML",
    )
