"""
rate_limit.py — простий rate limiter.
Не більше MAX_CALLS запитів за WINDOW_SEC секунд на користувача.
"""
import time
from collections import defaultdict
from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message


MAX_CALLS   = 10   # запитів
WINDOW_SEC  = 5    # за 5 секунд

_buckets: dict[int, list[float]] = defaultdict(list)


class RateLimitMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user:
            uid = tg_user.id
            now = time.time()
            # Очищаємо застарілі записи
            _buckets[uid] = [t for t in _buckets[uid] if now - t < WINDOW_SEC]
            if len(_buckets[uid]) >= MAX_CALLS:
                if isinstance(event, Message):
                    await event.answer("⏳ Надто багато запитів. Зачекайте секунду.")
                return
            _buckets[uid].append(now)

        return await handler(event, data)
