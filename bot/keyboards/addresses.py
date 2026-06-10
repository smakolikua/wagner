from typing import List
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ..models import Address, AddressType


def addresses_list_kb(addresses: List[Address]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    icons = {
        AddressType.HOME: "🏠",
        AddressType.CLIENT: "👤",
        AddressType.OFFICE: "🏢",
        AddressType.OTHER: "📍",
    }
    for a in addresses:
        icon = icons.get(a.type, "📍")
        builder.button(
            text=f"{icon} {a.label} — {a.type.value}",
            callback_data=f"addr:view:{a.id}"
        )
    builder.button(text="➕ Додати адресу", callback_data="addr:add")
    builder.button(text="📂 Імпорт CSV", callback_data="addr:csv")
    builder.adjust(1)
    return builder.as_markup()


def address_actions_kb(address_id: int, is_home: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not is_home:
        builder.button(text="🏠 Зробити домашньою", callback_data=f"addr:sethome:{address_id}")
    builder.button(text="✏️ Редагувати", callback_data=f"addr:edit:{address_id}")
    builder.button(text="🗑 Видалити", callback_data=f"addr:delete:{address_id}")
    builder.button(text="◀️ Назад", callback_data="addr:list")
    builder.adjust(1)
    return builder.as_markup()


def address_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Heimatadresse", callback_data="atype:Heimatadresse")
    builder.button(text="👤 Kunde", callback_data="atype:Kunde")
    builder.button(text="🏢 Büro", callback_data="atype:Büro")
    builder.button(text="📍 Sonstiges", callback_data="atype:Sonstiges")
    builder.adjust(2)
    return builder.as_markup()


def address_select_kb(addresses: List[Address], prefix: str, lang: str = "de") -> InlineKeyboardMarkup:
    """Вибір адреси при додаванні поїздки вручну."""
    builder = InlineKeyboardBuilder()
    icons = {
        AddressType.HOME: "🏠",
        AddressType.CLIENT: "👤",
        AddressType.OFFICE: "🏢",
        AddressType.OTHER: "📍",
    }
    for a in addresses:
        icon = icons.get(a.type, "📍")
        builder.button(
            text=f"{icon} {a.label}",
            callback_data=f"{prefix}:{a.id}"
        )
    from ..i18n import t as _t
    builder.button(text=_t("manual_input", lang), callback_data=f"{prefix}:manual")
    builder.adjust(1)
    return builder.as_markup()
