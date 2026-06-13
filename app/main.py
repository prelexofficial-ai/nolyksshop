from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import load_config
from app.database import Database
from app.handlers.admin import router as admin_router
from app.handlers.user import router as user_router
from app.services.crypto_pay import CryptoPayClient


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_config()

    db = Database(config.database_path)
    await db.connect()
    await db.migrate()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    crypto = CryptoPayClient(config.crypto_pay_token, config.crypto_pay_api_url)
    dp = Dispatcher(storage=MemoryStorage(), db=db, config=config, crypto=crypto)
    dp.include_router(admin_router)
    dp.include_router(user_router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
