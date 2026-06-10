from typing import List
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ..models import Vehicle


def vehicles_list_kb(vehicles: List[Vehicle], show_add: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for v in vehicles:
        builder.button(text=f"🚗 {v.display_name}", callback_data=f"vehicle:view:{v.id}")
    if show_add:
        builder.button(text="➕ Додати авто", callback_data="vehicle:add")
    builder.adjust(1)
    return builder.as_markup()


def vehicle_actions_kb(vehicle_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редагувати пробіг", callback_data=f"vehicle:mileage:{vehicle_id}")
    builder.button(text="🗑 Видалити", callback_data=f"vehicle:delete:{vehicle_id}")
    builder.button(text="◀️ Назад", callback_data="vehicle:list")
    builder.adjust(1)
    return builder.as_markup()


def vehicle_select_kb(vehicles: List[Vehicle]) -> InlineKeyboardMarkup:
    """Вибір авто перед поїздкою."""
    builder = InlineKeyboardBuilder()
    for v in vehicles:
        builder.button(
            text=f"🚗 {v.display_name} ({int(v.current_mileage):,} км)",
            callback_data=f"select_vehicle:{v.id}"
        )
    builder.adjust(1)
    return builder.as_markup()
