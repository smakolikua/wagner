from datetime import date
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List
from ..models import Vehicle


def report_period_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    today = date.today()

    # Поточний місяць
    builder.button(
        text=f"📅 {today.strftime('%B %Y')} (поточний)",
        callback_data=f"report:month:{today.year}:{today.month}"
    )

    # Минулий місяць
    m = today.month - 1 or 12
    y = today.year if today.month > 1 else today.year - 1
    builder.button(
        text=f"📅 {date(y, m, 1).strftime('%B %Y')} (минулий)",
        callback_data=f"report:month:{y}:{m}"
    )

    # Поточний квартал
    q = (today.month - 1) // 3 + 1
    builder.button(text=f"📊 Q{q} {today.year}", callback_data=f"report:quarter:{today.year}:{q}")

    # Довільний діапазон
    builder.button(text="✍️ Довільний діапазон", callback_data="report:custom")

    builder.adjust(1)
    return builder.as_markup()


def report_vehicle_kb(vehicles: List[Vehicle]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for v in vehicles:
        builder.button(
            text=f"🚗 {v.display_name}",
            callback_data=f"report:vehicle:{v.id}"
        )
    builder.button(text="🚘 Всі авто", callback_data="report:vehicle:all")
    builder.adjust(1)
    return builder.as_markup()
