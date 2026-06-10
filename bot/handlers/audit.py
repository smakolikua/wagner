from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditLog, User

router = Router(name="audit")


@router.message(Command("audit"))
async def cmd_audit(message: Message, session: AsyncSession, user: User):
    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.user_id == user.id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(10)
    )
    rows = result.scalars().all()
    if not rows:
        await message.answer("🧾 Änderungsprotokoll поки порожній.")
        return

    lines = ["🧾 <b>Останні зміни</b>"]
    for row in rows:
        when = row.created_at.strftime("%d.%m.%Y %H:%M") if row.created_at else "—"
        lines.append(
            f"\n{when}\n"
            f"• {row.action.upper()} {row.entity_type} #{row.entity_id or '—'}\n"
            f"• {row.summary}"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")
