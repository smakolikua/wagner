from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, UserAccount

router = Router(name="team")


@router.message(Command("team"))
async def cmd_team(message: Message, session: AsyncSession, user: User, account_role: str | None = None):
    if account_role != "owner":
        await message.answer("🔒 Team-налаштування доступні тільки owner профілю.")
        return
    result = await session.execute(
        select(UserAccount)
        .where(UserAccount.user_id == user.id)
        .order_by(UserAccount.created_at, UserAccount.id)
    )
    accounts = result.scalars().all()
    lines = ["👥 <b>Team / доступи профілю</b>"]
    for account in accounts:
        marker = "⭐" if account.role == "owner" else "🚗"
        lines.append(f"• {marker} Telegram ID <code>{account.telegram_id}</code> — {account.role}")
    lines.append("\nНовий driver додається через PIN після `/start`.")
    await message.answer("\n".join(lines), parse_mode="HTML")
