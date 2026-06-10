from datetime import date, timedelta
from collections import defaultdict
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, Trip, TripPurpose
from ..services.stats_chart import generate_weekly_chart, generate_purpose_pie
from ..i18n import t

router = Router(name="stats")


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession, user: User):
    lang = user.lang
    res = await session.execute(
        select(Trip).where(Trip.user_id == user.id).order_by(Trip.date.desc())
    )
    all_trips = list(res.scalars().all())

    if not all_trips:
        await message.answer(t("stats_empty", lang))
        return

    today      = date.today()
    month_start = today.replace(day=1)
    week_start  = today - timedelta(days=today.weekday())

    month_trips = [tr for tr in all_trips if tr.date >= month_start]
    week_trips  = [tr for tr in all_trips if tr.date >= week_start]

    def km_sum(trips):
        total = sum(tr.distance for tr in trips)
        biz   = sum(tr.distance for tr in trips if tr.purpose == TripPurpose.BUSINESS)
        priv  = sum(tr.distance for tr in trips if tr.purpose == TripPurpose.PRIVATE)
        return total, biz, priv

    w_tot, w_biz, w_priv = km_sum(week_trips)
    m_tot, m_biz, m_priv = km_sum(month_trips)
    a_tot, a_biz, a_priv = km_sum(all_trips)

    dest: dict = defaultdict(int)
    for tr in all_trips:
        label = tr.end_address_text or "—"
        dest[label] += 1
    top5 = sorted(dest.items(), key=lambda x: -x[1])[:5]

    week_lbl  = week_start.strftime("%d.%m")
    month_lbl = month_start.strftime("%B %Y")

    sections = {
        "de": (f"<b>Diese Woche</b> ({week_lbl} – heute):",
               f"<b>Dieser Monat</b> ({month_lbl}):",
               f"<b>Gesamt</b>:",
               "  🚗 Fahrten: {cnt}  |  📏 {tot:.1f} km",
               "  💼 {biz:.1f} km geschäftl. / 🏠 {priv:.1f} km privat",
               "<b>Top-5 Ziele:</b>"),
        "ua": (f"<b>За цей тиждень</b> ({week_lbl} – сьогодні):",
               f"<b>За цей місяць</b> ({month_lbl}):",
               f"<b>За весь час</b>:",
               "  🚗 Поїздок: {cnt}  |  📏 {tot:.1f} км",
               "  💼 {biz:.1f} км ділових / 🏠 {priv:.1f} км приватних",
               "<b>Топ-5 напрямків:</b>"),
        "ru": (f"<b>За эту неделю</b> ({week_lbl} – сегодня):",
               f"<b>За этот месяц</b> ({month_lbl}):",
               f"<b>За всё время</b>:",
               "  🚗 Поездок: {cnt}  |  📏 {tot:.1f} км",
               "  💼 {biz:.1f} км деловых / 🏠 {priv:.1f} км частных",
               "<b>Топ-5 направлений:</b>"),
        "en": (f"<b>This week</b> ({week_lbl} – today):",
               f"<b>This month</b> ({month_lbl}):",
               f"<b>All time</b>:",
               "  🚗 Trips: {cnt}  |  📏 {tot:.1f} km",
               "  💼 {biz:.1f} km business / 🏠 {priv:.1f} km private",
               "<b>Top-5 destinations:</b>"),
    }
    s = sections.get(lang, sections["de"])

    lines = [f"📊 {t('stats_title', lang)}\n"]
    for header, cnt, tot, biz, priv in [
        (s[0], len(week_trips),  w_tot, w_biz, w_priv),
        (s[1], len(month_trips), m_tot, m_biz, m_priv),
        (s[2], len(all_trips),   a_tot, a_biz, a_priv),
    ]:
        lines.append(header)
        lines.append(s[3].format(cnt=cnt, tot=tot))
        lines.append(s[4].format(biz=biz, priv=priv))
        lines.append("")

    if top5:
        lines.append(s[5])
        for i, (label, cnt) in enumerate(top5, 1):
            lines.append(f"  {i}. {label[:35]} — {cnt}×")

    # Inline-кнопки для діаграм
    b = InlineKeyboardBuilder()
    b.button(text="📊 " + t("stats_chart_title", lang), callback_data="stats:chart:weekly")
    b.button(text="🥧 Pie chart", callback_data="stats:chart:pie")
    b.adjust(1)

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=b.as_markup())


@router.callback_query(F.data == "stats:chart:weekly")
async def chart_weekly(callback, session: AsyncSession, user: User):
    await callback.answer()
    res = await session.execute(select(Trip).where(Trip.user_id == user.id))
    trips = list(res.scalars().all())
    png = generate_weekly_chart(trips, lang=user.lang)
    await callback.message.answer_photo(
        BufferedInputFile(png, filename="weekly_chart.png"),
        caption=t("stats_chart_title", user.lang),
    )


@router.callback_query(F.data == "stats:chart:pie")
async def chart_pie(callback, session: AsyncSession, user: User):
    await callback.answer()
    res = await session.execute(select(Trip).where(Trip.user_id == user.id))
    trips = list(res.scalars().all())
    png = generate_purpose_pie(trips, lang=user.lang)
    if not png:
        await callback.message.answer(t("stats_empty", user.lang))
        return
    await callback.message.answer_photo(
        BufferedInputFile(png, filename="pie_chart.png"),
        caption="🥧 Fahrtverteilung",
    )
