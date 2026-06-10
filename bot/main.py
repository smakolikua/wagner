"""main.py — точка входу Fahrtenbuch Bot v4."""
import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from loguru import logger

from .config import settings
from .database import create_tables
from .handlers import setup_routers
from .middlewares import DbSessionMiddleware, AuthMiddleware, RateLimitMiddleware
from .schedulers import setup_scheduler
from .logging_setup import setup_logging, setup_sentry

BOT_COMMANDS = [
    BotCommand(command="start",       description="🏠 Головне меню"),
    BotCommand(command="cars",        description="🚗 Автомобілі"),
    BotCommand(command="addresses",   description="📍 Адреси"),
    BotCommand(command="trips",       description="📋 Журнал поїздок"),
    BotCommand(command="newtrip",     description="➕ Нова поїздка"),
    BotCommand(command="track",       description="📡 GPS-трекінг"),
    BotCommand(command="stoptrack",   description="🛑 Зупинити трекінг"),
    BotCommand(command="trackstatus", description="📊 Статус трекінгу"),
    BotCommand(command="report",      description="📄 PDF-звіт"),
    BotCommand(command="stats",       description="📈 Статистика"),
    BotCommand(command="settings",    description="⚙️ Налаштування"),
    BotCommand(command="receipts",    description="🧾 Чеки та витрати"),
    BotCommand(command="newreceipt",  description="📸 Додати чек"),
    BotCommand(command="taxreport",   description="💰 EÜR звіт"),
    BotCommand(command="addincome",   description="💶 Додати дохід"),
    BotCommand(command="my_pin",      description="🔐 Новий PIN для входу"),
    BotCommand(command="audit",       description="🧾 Журнал змін"),
    BotCommand(command="open",        description="📌 Відкриті задачі"),
    BotCommand(command="dashboard",   description="📊 Dashboard"),
    BotCommand(command="steuerpaket", description="📦 Paket für Steuerberater"),
    BotCommand(command="team",        description="👥 Team доступи"),
    BotCommand(command="help",        description="❓ Довідка"),
]


def _build_dp() -> tuple[Bot, Dispatcher]:
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(RateLimitMiddleware())
    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(AuthMiddleware())
    dp.include_router(setup_routers())
    return bot, dp


async def run_polling():
    logger.info("Mode: POLLING")
    await create_tables()
    bot, dp = _build_dp()
    await bot.set_my_commands(BOT_COMMANDS)
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Bot running. Ctrl+C to stop.")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("Bot stopped.")


async def run_webhook():
    logger.info("Mode: WEBHOOK")
    await create_tables()
    bot, dp = _build_dp()
    await bot.set_my_commands(BOT_COMMANDS)

    webhook_path = f"/webhook/{settings.BOT_TOKEN}"
    webhook_url  = f"{settings.BOT_WEBHOOK_URL}{webhook_path}"
    await bot.set_webhook(url=webhook_url, drop_pending_updates=True,
                          allowed_updates=dp.resolve_used_update_types())
    logger.info(f"Webhook: {webhook_url}")

    scheduler = setup_scheduler(bot)
    scheduler.start()

    app = web.Application()

    async def on_startup(_):
        logger.info("Webhook server started.")

    async def on_cleanup(_):
        scheduler.shutdown(wait=False)
        await bot.delete_webhook()
        await bot.session.close()
        logger.info("Webhook server stopped.")

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=webhook_path)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=settings.WEBHOOK_PORT)
    await site.start()
    logger.info(f"Listening 0.0.0.0:{settings.WEBHOOK_PORT}")
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


async def main():
    setup_logging(settings.LOG_LEVEL, settings.LOG_FILE)
    setup_sentry(settings.SENTRY_DSN, environment=os.getenv("ENVIRONMENT", "production"))
    logger.info("Starting Fahrtenbuch Bot v4...")

    if settings.BOT_WEBHOOK_URL:
        await run_webhook()
    else:
        await run_polling()


if __name__ == "__main__":
    asyncio.run(main())
