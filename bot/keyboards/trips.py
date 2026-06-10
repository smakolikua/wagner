from typing import List
from datetime import date
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ..models import Trip, TripPurpose


def trips_list_kb(trips: List[Trip], page: int = 0, total: int = 0, per_page: int = 8) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in trips:
        purpose_icon = "💼" if t.purpose == TripPurpose.BUSINESS else "🏠"
        builder.button(
            text=f"{purpose_icon} {t.date.strftime('%d.%m')} | {t.start_label[:12]} → {t.end_label[:12]} | {t.distance} km",
            callback_data=f"trip:view:{t.id}"
        )

    # Пагінація
    nav_row = []
    if page > 0:
        nav_row.append(("◀️", f"trip:page:{page-1}"))
    if (page + 1) * per_page < total:
        nav_row.append(("▶️", f"trip:page:{page+1}"))

    for label, data in nav_row:
        builder.button(text=label, callback_data=data)

    builder.button(text="➕ Нова поїздка", callback_data="trip:add")
    builder.button(text="🔍 Фільтр", callback_data="trip:filter")
    builder.adjust(1)
    return builder.as_markup()


def trip_actions_kb(trip_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редагувати", callback_data=f"trip:edit:{trip_id}")
    builder.button(text="🗑 Видалити", callback_data=f"trip:delete:{trip_id}")
    builder.button(text="◀️ Назад", callback_data="trip:list")
    builder.adjust(1)
    return builder.as_markup()


def purpose_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💼 geschäftlich", callback_data="purpose:geschäftlich")
    builder.button(text="🏠 privat", callback_data="purpose:privat")
    builder.adjust(2)
    return builder.as_markup()


def month_filter_kb() -> InlineKeyboardMarkup:
    """Швидкий вибір місяця для фільтру."""
    builder = InlineKeyboardBuilder()
    today = date.today()
    for i in range(6):
        m = (today.month - i - 1) % 12 + 1
        y = today.year if today.month - i > 0 else today.year - 1
        label = date(y, m, 1).strftime("%B %Y")
        builder.button(text=label, callback_data=f"trip:filter_month:{y}:{m}")
    builder.button(text="📋 Всі поїздки", callback_data="trip:filter_all")
    builder.adjust(2)
    return builder.as_markup()
