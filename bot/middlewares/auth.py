from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import User, UserAccount


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session: AsyncSession = data.get("session")
        user_obj = None
        account_obj = None

        tg_user = data.get("event_from_user")
        if tg_user and session:
            account_obj = await session.scalar(
                select(UserAccount).where(UserAccount.telegram_id == tg_user.id)
            )
            if account_obj is not None:
                user_obj = await session.get(User, account_obj.user_id)
            if user_obj is None:
                result = await session.execute(
                    select(User).where(User.telegram_id == tg_user.id)
                )
                user_obj = result.scalar_one_or_none()
                if user_obj is not None:
                    account_obj = UserAccount(user_id=user_obj.id, telegram_id=tg_user.id, role="owner")
                    session.add(account_obj)
                    await session.commit()

        data["user"] = user_obj
        data["account"] = account_obj
        data["account_role"] = account_obj.role if account_obj else None

        # Якщо не зареєстрований і це не /start — редирект
        if user_obj is None and isinstance(event, Message):
            text = event.text or ""
            if not text.startswith("/start") and data.get("raw_state") is None:
                await event.answer(
                    "👋 Спочатку зареєструйтесь — надішліть /start"
                )
                return

        return await handler(event, data)
