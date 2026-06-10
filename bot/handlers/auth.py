from __future__ import annotations

import hashlib
import secrets

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, UserAccount
from ..keyboards.main_menu import main_menu_kb, lang_kb, cancel_kb, CANCEL_TEXTS
from ..i18n import t

router = Router(name="auth")

LANG_LABELS = {
    "de": "🇩🇪 Deutsch",
    "ua": "🇺🇦 Українська",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
}


class RegistrationFSM(StatesGroup):
    waiting_entry = State()
    waiting_lang = State()


def _pin_hash(pin: str) -> str:
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


async def _generate_unique_pin(session: AsyncSession) -> str:
    for _ in range(100):
        pin = f"{secrets.randbelow(900000) + 100000}"
        result = await session.execute(
            select(User).where(User.access_pin_hash == _pin_hash(pin))
        )
        if result.scalar_one_or_none() is None:
            return pin
    raise RuntimeError("Could not generate a unique PIN")


def _start_text(lang: str = "de") -> str:
    if lang == "ua":
        return (
            "👋 Ласкаво просимо до <b>Fahrtenbuch Bot</b>!\n\n"
            "Якщо у вас вже є профіль, введіть ваш <b>6-значний PIN</b>.\n"
            "Якщо це перший вхід, введіть ваше ім'я та прізвище:"
        )
    return (
        "👋 Willkommen bei <b>Fahrtenbuch Bot</b>!\n\n"
        "Wenn Sie bereits ein Profil haben, geben Sie Ihre <b>6-stellige PIN</b> ein.\n"
        "Wenn dies der erste Login ist, geben Sie bitte Ihren Vor- und Nachnamen ein:"
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession, user: User | None):
    if user:
        pin_note = ""
        if not user.access_pin_hash:
            pin = await _generate_unique_pin(session)
            user.access_pin_hash = _pin_hash(pin)
            await session.commit()
            pin_note = (
                f"\n\n🔐 Ваш PIN для входу з іншого Telegram: <code>{pin}</code>\n"
                "Збережіть його в безпечному місці."
            )
        await message.answer(
            t("welcome_back", user.lang, name=user.name) + pin_note,
            reply_markup=main_menu_kb(user.lang),
            parse_mode="HTML",
        )
        return

    await message.answer(
        _start_text("ua"),
        reply_markup=cancel_kb("de"),
        parse_mode="HTML",
    )
    await state.set_state(RegistrationFSM.waiting_entry)


@router.message(RegistrationFSM.waiting_entry, F.text)
async def reg_entry(message: Message, state: FSMContext, session: AsyncSession):
    if message.text in CANCEL_TEXTS:
        await state.clear()
        await message.answer(t("cancelled"), reply_markup=main_menu_kb())
        return

    entry = message.text.strip()
    if entry.isdigit() and len(entry) == 6:
        result = await session.execute(
            select(User).where(User.access_pin_hash == _pin_hash(entry))
        )
        linked_user = result.scalar_one_or_none()
        if not linked_user:
            await message.answer(
                "⚠️ PIN не знайдено. Перевірте PIN або введіть ім'я для нової реєстрації."
            )
            return

        existing = await session.execute(
            select(UserAccount).where(UserAccount.telegram_id == message.from_user.id)
        )
        existing_account = existing.scalar_one_or_none()
        if existing_account and existing_account.user_id != linked_user.id:
            await message.answer("⚠️ Цей Telegram вже прив'язаний до іншого профілю.")
            return
        if not existing_account:
            session.add(UserAccount(user_id=linked_user.id, telegram_id=message.from_user.id, role="driver"))

        await session.commit()
        await state.clear()
        await message.answer(
            "✅ Профіль підключено!\n\n" + t("welcome_back", linked_user.lang, name=linked_user.name),
            reply_markup=main_menu_kb(linked_user.lang),
            parse_mode="HTML",
        )
        return

    name = entry
    if len(name) < 2:
        await message.answer(t("name_too_short", "de"))
        return
    if len(name) > 100:
        await message.answer("Name zu lang (max. 100 Zeichen).")
        return
    await state.update_data(name=name)
    await message.answer(
        t("choose_lang", "de", name=name),
        reply_markup=lang_kb(),
        parse_mode="HTML",
    )
    await state.set_state(RegistrationFSM.waiting_lang)


@router.callback_query(RegistrationFSM.waiting_lang, F.data.startswith("lang:"))
async def reg_lang(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    lang = callback.data.split(":")[1]
    data = await state.get_data()
    name = data["name"]
    pin = await _generate_unique_pin(session)

    new_user = User(
        telegram_id=callback.from_user.id,
        name=name,
        lang=lang,
        access_pin_hash=_pin_hash(pin),
    )
    session.add(new_user)
    await session.flush()
    session.add(UserAccount(user_id=new_user.id, telegram_id=callback.from_user.id, role="owner"))
    await session.commit()
    await state.clear()

    await callback.message.edit_text(
        t("reg_done", lang, name=name, lang=LANG_LABELS.get(lang, lang))
        + (
            f"\n\n🔐 <b>Ваш PIN для входу:</b> <code>{pin}</code>\n"
            "Збережіть його. За цим PIN можна підключити ваші дані з іншого Telegram."
        ),
        parse_mode="HTML",
    )
    await callback.message.answer(t("main_menu", lang), reply_markup=main_menu_kb(lang))
    await callback.answer()


@router.message(Command("my_pin"))
async def cmd_my_pin(message: Message, session: AsyncSession, user: User):
    pin = await _generate_unique_pin(session)
    user.access_pin_hash = _pin_hash(pin)
    await session.commit()
    await message.answer(
        "🔐 <b>Ваш новий PIN для входу:</b>\n"
        f"<code>{pin}</code>\n\n"
        "Попередній PIN більше не працює. Збережіть цей PIN у безпечному місці.",
        parse_mode="HTML",
    )


@router.message(F.text.in_({"⚙️ Налаштування", "⚙️ Настройки", "⚙️ Settings", "⚙️ Einstellungen"}))
async def settings_shortcut(message: Message):
    # Редирект до /settings хендлера
    from .settings import cmd_settings
    # просто викликаємо через команду
    await message.answer("/settings")
