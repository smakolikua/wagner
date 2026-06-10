from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, Address
from ..keyboards.main_menu import cancel_kb, lang_kb, main_menu_kb, CANCEL_TEXTS
from ..i18n import t

router = Router(name="settings")

LANG_LABELS = {"de": "🇩🇪 Deutsch", "ua": "🇺🇦 Українська", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}


class SettingsFSM(StatesGroup):
    waiting_name = State()


def _settings_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("settings_name",   lang), callback_data="settings:name")
    b.button(text=t("settings_lang",   lang), callback_data="settings:lang")
    b.button(text=t("settings_home",   lang), callback_data="settings:home")
    b.button(text=t("settings_radius", lang), callback_data="settings:radius")
    b.adjust(1)
    return b.as_markup()


def _radius_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for m in [50, 100, 150, 200]:
        b.button(text=f"{m} м", callback_data=f"settings:radius:{m}")
    b.adjust(4)
    return b.as_markup()


@router.message(Command("settings"))
async def cmd_settings(message: Message, user: User):
    lang = user.lang
    await message.answer(
        t("settings_title", lang,
          name=user.name,
          lang_label=LANG_LABELS.get(lang, lang),
          radius=user.geofence_radius,
          tg_id=user.telegram_id),
        reply_markup=_settings_kb(lang),
        parse_mode="HTML",
    )


# Shortcut з reply-кнопок (всі мови)


@router.callback_query(F.data == "settings:name")
async def settings_name(callback: CallbackQuery, state: FSMContext, user: User):
    await callback.message.answer(t("settings_ask_name", user.lang), reply_markup=cancel_kb(user.lang))
    await state.set_state(SettingsFSM.waiting_name)
    await callback.answer()


@router.message(SettingsFSM.waiting_name, F.text)
async def settings_name_save(message: Message, state: FSMContext, session: AsyncSession, user: User):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled", user.lang), reply_markup=main_menu_kb(user.lang))
        return
    name = message.text.strip()
    if len(name) < 2:
        await message.answer(t("name_too_short", user.lang))
        return
    user.name = name
    await session.commit()
    await state.clear()
    await message.answer(
        t("settings_name_changed", user.lang, name=name),
        reply_markup=main_menu_kb(user.lang), parse_mode="HTML",
    )


@router.callback_query(F.data == "settings:lang")
async def settings_lang(callback: CallbackQuery, user: User):
    await callback.message.edit_text(
        t("choose_lang", user.lang, name=user.name),
        reply_markup=lang_kb(), parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lang:"))
async def settings_lang_save(callback: CallbackQuery, session: AsyncSession, user: User):
    lang = callback.data.split(":")[1]
    user.lang = lang
    await session.commit()
    await callback.message.edit_text(
        t("settings_lang_changed", lang, lang=LANG_LABELS.get(lang, lang)),
        parse_mode="HTML",
    )
    await callback.message.answer(t("main_menu", lang), reply_markup=main_menu_kb(lang))
    await callback.answer()


@router.callback_query(F.data == "settings:home")
async def settings_home(callback: CallbackQuery, session: AsyncSession, user: User):
    res = await session.execute(select(Address).where(Address.user_id == user.id))
    addresses = list(res.scalars().all())
    if not addresses:
        await callback.answer(t("addresses_empty", user.lang), show_alert=True)
        return
    b = InlineKeyboardBuilder()
    for a in addresses:
        mark = " ✅" if user.home_address_id == a.id else ""
        b.button(text=f"{a.label}{mark}", callback_data=f"settings:sethome:{a.id}")
    b.adjust(1)
    await callback.message.edit_text(
        t("settings_home_ask", user.lang), reply_markup=b.as_markup(), parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:sethome:"))
async def settings_set_home(callback: CallbackQuery, session: AsyncSession, user: User):
    addr_id = int(callback.data.split(":")[2])
    addr = await session.get(Address, addr_id)
    if not addr or addr.user_id != user.id:
        await callback.answer(t("not_found", user.lang), show_alert=True)
        return
    user.home_address_id = addr_id
    await session.commit()
    await callback.message.edit_text(
        t("settings_home_changed", user.lang, label=addr.label), parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "settings:radius")
async def settings_radius(callback: CallbackQuery, user: User):
    await callback.message.edit_text(
        t("settings_radius_ask", user.lang),
        reply_markup=_radius_kb(), parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:radius:"))
async def settings_set_radius(callback: CallbackQuery, session: AsyncSession, user: User):
    radius = int(callback.data.split(":")[2])
    user.geofence_radius = radius
    await session.commit()
    await callback.message.edit_text(
        t("settings_radius_changed", user.lang, radius=radius), parse_mode="HTML",
    )
    await callback.answer()
