import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from database import db
from middleware import UserTrackingMiddleware
from routers import user_router, admin_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    logger.info("Connecting to database...")
    await db.connect()
    await db.init_tables()
    logger.info("Database initialized")

    me = await bot.get_me()
    logger.info(f"Bot started: @{me.username}")


async def on_shutdown(bot: Bot):
    logger.info("Shutting down...")
    await db.disconnect()
    logger.info("Database disconnected")


async def main():
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    dp.message.middleware(UserTrackingMiddleware())

    dp.include_router(admin_router)
    dp.include_router(user_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
