from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ..i18n import t

# Всі тексти кнопки "Скасувати" у всіх мовах
CANCEL_TEXTS = {"❌ Abbrechen", "❌ Скасувати", "❌ Отмена", "❌ Cancel"}


def main_menu_kb(lang: str = "de") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("menu_cars", lang)),      KeyboardButton(text=t("menu_addresses", lang))],
            [KeyboardButton(text=t("menu_trips", lang)),     KeyboardButton(text=t("menu_newtrip", lang))],
            [KeyboardButton(text=t("menu_track", lang)),     KeyboardButton(text=t("menu_report", lang))],
            [KeyboardButton(text=t("menu_receipts", lang)),  KeyboardButton(text=t("menu_tax", lang))],
            [KeyboardButton(text=t("menu_settings", lang))],
        ],
        resize_keyboard=True,
        input_field_placeholder=t("menu_hint", lang),
    )


def lang_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🇩🇪 Deutsch",    callback_data="lang:de")
    builder.button(text="🇺🇦 Українська", callback_data="lang:ua")
    builder.button(text="🇷🇺 Русский",    callback_data="lang:ru")
    builder.button(text="🇬🇧 English",    callback_data="lang:en")
    builder.adjust(2)
    return builder.as_markup()


def confirm_kb(yes_data: str, no_data: str, lang: str = "de") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("yes", lang), callback_data=yes_data)
    builder.button(text=t("no",  lang), callback_data=no_data)
    builder.adjust(2)
    return builder.as_markup()


def cancel_kb(lang: str = "de") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("cancel_text", lang))]],
        resize_keyboard=True,
    )
