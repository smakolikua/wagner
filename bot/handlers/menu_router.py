"""
menu_router.py — єдиний роутер для всіх кнопок головного меню (4 мови).
Реєструється ПЕРШИМ щоб кнопки не перехоплювались FSM-станами.
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from ..i18n import t, SUPPORTED_LANGS
from ..models import User

router = Router(name="menu_router")


def _all(key: str) -> set[str]:
    return {t(key, lang) for lang in SUPPORTED_LANGS}


CARS_TEXTS      = _all("menu_cars")
ADDRESSES_TEXTS = _all("menu_addresses")
TRIPS_TEXTS     = _all("menu_trips")
NEWTRIP_TEXTS   = _all("menu_newtrip")
TRACK_TEXTS     = _all("menu_track")
REPORT_TEXTS    = _all("menu_report")
RECEIPTS_TEXTS  = _all("menu_receipts")
TAX_TEXTS       = _all("menu_tax")
SETTINGS_TEXTS  = _all("menu_settings")


@router.message(F.text.in_(CARS_TEXTS))
async def menu_cars(message: Message, session: AsyncSession, user: User):
    from .vehicles import cmd_cars
    await cmd_cars(message, session, user)


@router.message(F.text.in_(ADDRESSES_TEXTS))
async def menu_addresses(message: Message, session: AsyncSession, user: User):
    from .addresses import cmd_addresses
    await cmd_addresses(message, session, user)


@router.message(F.text.in_(TRIPS_TEXTS))
async def menu_trips(message: Message, session: AsyncSession, user: User):
    from .trips import cmd_trips
    await cmd_trips(message, session, user)


@router.message(F.text.in_(NEWTRIP_TEXTS))
async def menu_newtrip(message: Message, state: FSMContext, session: AsyncSession, user: User):
    from .trips import start_add_trip
    await start_add_trip(message, state, session, user)


@router.message(F.text.in_(TRACK_TEXTS))
async def menu_track(message: Message, state: FSMContext, session: AsyncSession, user: User):
    from .tracking import cmd_track
    await cmd_track(message, state, session, user)


@router.message(F.text.in_(REPORT_TEXTS))
async def menu_report(message: Message, state: FSMContext, session: AsyncSession, user: User):
    from .reports import cmd_report
    await cmd_report(message, state, session, user)


@router.message(F.text.in_(RECEIPTS_TEXTS))
async def menu_receipts(message: Message, session: AsyncSession, user: User):
    from .receipts import cmd_receipts
    await cmd_receipts(message, session, user)


@router.message(F.text.in_(TAX_TEXTS))
async def menu_tax(message: Message, state: FSMContext, user: User):
    from .tax_handler import cmd_taxreport
    await cmd_taxreport(message, state, user)


@router.message(F.text.in_(SETTINGS_TEXTS))
async def menu_settings(message: Message, user: User):
    from .settings import cmd_settings
    await cmd_settings(message, user)
