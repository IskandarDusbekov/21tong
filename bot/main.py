import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    MenuButtonCommands,
    MenuButtonWebApp,
    WebAppInfo,
)

import config
import tasks
import texts
from api import backend
from handlers import routers

log = logging.getLogger("21tong")

USER_COMMANDS = [
    BotCommand(command="start", description="Ariza / bosh sahifa"),
    BotCommand(command="holat", description="Mening holatim"),
    BotCommand(command="yoriqnoma", description="Raport qanday yuboriladi"),
    BotCommand(command="nizom", description="Lager nizomi"),
]
ADMIN_COMMANDS = USER_COMMANDS + [
    BotCommand(command="arizalar", description="Kutilayotgan arizalar"),
]


async def setup_commands(bot: Bot):
    await bot.set_my_commands(USER_COMMANDS, scope=BotCommandScopeAllPrivateChats())
    for admin in config.ADMIN_IDS:
        try:
            await bot.set_my_commands(ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=admin))
        except Exception as e:  # admin hali botga /start bosmagan
            log.warning("Admin %s uchun buyruqlar o'rnatilmadi: %s", admin, e)
    # MINI_APP_URL (HTTPS) berilsa — doimiy «Menu» tugmasi Mini App'ni ochadi (BotFather'da
    # qo'lda sozlash shart emas). Bo'lmasa — oddiy buyruqlar menyusi.
    if config.MINI_APP_URL:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Mini App", web_app=WebAppInfo(url=config.MINI_APP_URL))
        )
    else:
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not config.BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN .env faylida ko'rsatilmagan")
    if not config.ADMIN_IDS:
        log.warning("ADMIN_IDS bo'sh — arizalar hech kimga bormaydi. .env ga Telegram ID'ingizni yozing.")
    try:
        await backend.config()
    except Exception as e:
        raise SystemExit(f"Backend'ga ulanib bo'lmadi ({config.BACKEND_URL}): {e}. Avval runserver'ni ishga tushiring.")
    await texts.refresh(force=True)
    # Bot o'chiq turgan paytda o'tkazib yuborilgan kunlik hisob bo'lsa — hozir bajariladi (idempotent)
    await backend.run_daily()

    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_routers(*routers)
    await setup_commands(bot)
    me = await bot.me()
    log.info("Bot ishga tushdi: @%s", me.username)

    background = [
        asyncio.create_task(tasks.notifications_loop(bot)),
        asyncio.create_task(tasks.minute_loop(bot)),
    ]
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        for t in background:
            t.cancel()


if __name__ == "__main__":
    asyncio.run(main())
