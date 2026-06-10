from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, Vehicle, Trip
from ..keyboards import vehicles_list_kb, vehicle_actions_kb
from ..keyboards.main_menu import main_menu_kb, cancel_kb, confirm_kb, CANCEL_TEXTS
from ..i18n import t
from ..services.audit import log_audit, snapshot

router = Router(name="vehicles")


class AddVehicleFSM(StatesGroup):
    waiting_make    = State()
    waiting_model   = State()
    waiting_plate   = State()
    waiting_mileage = State()


class EditMileageFSM(StatesGroup):
    waiting_mileage = State()


async def _get_vehicles(session: AsyncSession, user: User) -> list[Vehicle]:
    result = await session.execute(
        select(Vehicle).where(Vehicle.user_id == user.id).order_by(Vehicle.created_at)
    )
    return list(result.scalars().all())


def _parse_km(text: str) -> float | None:
    cleaned = text.strip().replace(" ", "").replace(".", "").replace(",", "")
    return float(cleaned) if cleaned.isdigit() else None


@router.message(Command("cars"))
async def cmd_cars(message: Message, session: AsyncSession, user: User):
    lang = user.lang
    vehicles = await _get_vehicles(session, user)
    if not vehicles:
        await message.answer(t("cars_empty", lang), reply_markup=vehicles_list_kb([], show_add=True))
    else:
        await message.answer(
            t("cars_title", lang, count=len(vehicles)),
            reply_markup=vehicles_list_kb(vehicles),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "vehicle:list")
async def cb_vehicle_list(callback: CallbackQuery, session: AsyncSession, user: User):
    vehicles = await _get_vehicles(session, user)
    await callback.message.edit_text(
        t("cars_title", user.lang, count=len(vehicles)),
        reply_markup=vehicles_list_kb(vehicles),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("vehicle:view:"))
async def cb_vehicle_view(callback: CallbackQuery, session: AsyncSession, user: User):
    vehicle_id = int(callback.data.split(":")[2])
    vehicle = await session.get(Vehicle, vehicle_id)
    if not vehicle or vehicle.user_id != user.id:
        await callback.answer(t("not_found", user.lang), show_alert=True)
        return
    await callback.message.edit_text(
        f"🚗 <b>{vehicle.display_name}</b>\n\n"
        f"📊 {int(vehicle.current_mileage):,} km\n"
        f"🔢 {vehicle.plate}",
        reply_markup=vehicle_actions_kb(vehicle_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "vehicle:add")
async def cb_vehicle_add(callback: CallbackQuery, state: FSMContext, user: User):
    await callback.message.answer(
        t("car_ask_make", user.lang),
        parse_mode="HTML",
        reply_markup=cancel_kb(user.lang),
    )
    await state.set_state(AddVehicleFSM.waiting_make)
    await callback.answer()


@router.message(AddVehicleFSM.waiting_make, F.text)
async def fsm_make(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    await state.update_data(make=message.text.strip())
    await message.answer(t("car_ask_model", user.lang), parse_mode="HTML")
    await state.set_state(AddVehicleFSM.waiting_model)


@router.message(AddVehicleFSM.waiting_model, F.text)
async def fsm_model(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    await state.update_data(model=message.text.strip())
    await message.answer(t("car_ask_plate", user.lang), parse_mode="HTML")
    await state.set_state(AddVehicleFSM.waiting_plate)


@router.message(AddVehicleFSM.waiting_plate, F.text)
async def fsm_plate(message: Message, state: FSMContext, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    await state.update_data(plate=message.text.strip().upper())
    await message.answer(t("car_ask_mileage", user.lang), parse_mode="HTML")
    await state.set_state(AddVehicleFSM.waiting_mileage)


@router.message(AddVehicleFSM.waiting_mileage, F.text)
async def fsm_mileage(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    km = _parse_km(message.text)
    if km is None:
        await message.answer(t("error_number", user.lang))
        return
    data = await state.get_data()
    vehicle = Vehicle(
        user_id=user.id,
        make=data["make"], model=data["model"],
        plate=data["plate"], current_mileage=km,
    )
    session.add(vehicle)
    await session.flush()
    await log_audit(
        session, user, "create", "vehicle", f"Auto створено: {vehicle.display_name}",
        entity_id=vehicle.id, telegram_id=message.from_user.id,
        after=snapshot(vehicle, ["make", "model", "plate", "current_mileage"]),
    )
    await session.commit()
    await state.clear()
    await message.answer(
        t("car_added", user.lang, name=vehicle.display_name, km=int(km)),
        reply_markup=main_menu_kb(user.lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("vehicle:mileage:"))
async def cb_edit_mileage(callback: CallbackQuery, state: FSMContext, user: User):
    vehicle_id = int(callback.data.split(":")[2])
    await state.update_data(vehicle_id=vehicle_id)
    await callback.message.answer(t("car_ask_mileage", user.lang), parse_mode="HTML",
                                   reply_markup=cancel_kb(user.lang))
    await state.set_state(EditMileageFSM.waiting_mileage)
    await callback.answer()


@router.message(EditMileageFSM.waiting_mileage, F.text)
async def fsm_edit_mileage(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    km = _parse_km(message.text)
    if km is None:
        await message.answer(t("error_number", user.lang))
        return
    data = await state.get_data()
    vehicle = await session.get(Vehicle, data["vehicle_id"])
    if not vehicle or vehicle.user_id != user.id:
        await message.answer(t("not_found", user.lang))
        await state.clear()
        return
    before = snapshot(vehicle, ["current_mileage"])
    vehicle.current_mileage = km
    await log_audit(
        session, user, "update", "vehicle", f"Пробіг авто оновлено: {vehicle.display_name}",
        entity_id=vehicle.id, telegram_id=message.from_user.id,
        before=before, after=snapshot(vehicle, ["current_mileage"]),
    )
    await session.commit()
    await state.clear()
    await message.answer(
        t("car_mileage_updated", user.lang, name=vehicle.display_name, km=int(km)),
        reply_markup=main_menu_kb(user.lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("vehicle:delete:"))
async def cb_delete_vehicle(callback: CallbackQuery, session: AsyncSession, user: User):
    vehicle_id = int(callback.data.split(":")[2])
    vehicle = await session.get(Vehicle, vehicle_id)
    if not vehicle or vehicle.user_id != user.id:
        await callback.answer(t("not_found", user.lang), show_alert=True)
        return
    # Рахуємо кількість поїздок для попередження
    result = await session.execute(
        select(func.count()).where(Trip.vehicle_id == vehicle_id)
    )
    trip_count = result.scalar() or 0
    warn = f"\n⚠️ Буде видалено також <b>{trip_count} поїздок</b>!" if trip_count else ""
    await callback.message.edit_text(
        t("car_delete_confirm", user.lang, name=vehicle.display_name) + warn,
        reply_markup=confirm_kb(f"vehicle:delete_confirm:{vehicle_id}", "vehicle:list", user.lang),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("vehicle:delete_confirm:"))
async def cb_delete_confirm(callback: CallbackQuery, session: AsyncSession, user: User):
    vehicle_id = int(callback.data.split(":")[2])
    vehicle = await session.get(Vehicle, vehicle_id)
    if not vehicle or vehicle.user_id != user.id:
        await callback.answer(t("not_found", user.lang), show_alert=True)
        return
    name = vehicle.display_name
    before = snapshot(vehicle, ["make", "model", "plate", "current_mileage"])
    await session.delete(vehicle)
    await log_audit(
        session, user, "delete", "vehicle", f"Auto видалено: {name}",
        entity_id=vehicle_id, telegram_id=callback.from_user.id, before=before,
    )
    await session.commit()
    await callback.message.edit_text(
        t("car_deleted", user.lang, name=name), parse_mode="HTML"
    )
    await callback.answer()
