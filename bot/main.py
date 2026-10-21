import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
import tasks
from handlers import routers


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not config.BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN .env faylida ko'rsatilmagan")

    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_routers(*routers)

    background = [
        asyncio.create_task(tasks.notifications_loop(bot)),
        asyncio.create_task(tasks.minute_loop(bot)),
    ]
    try:
        await dp.start_polling(bot)
    finally:
        for t in background:
            t.cancel()


if __name__ == "__main__":
    asyncio.run(main())
