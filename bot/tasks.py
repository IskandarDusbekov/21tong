"""
Fon vazifalari:
  * notifications — backend outbox'idagi voqealarni yetkazadi (shaxsan va adminlarga);
  * alarms        — har daqiqada budilnik vaqti kelganlarni "TURISH!" bilan uyg'otadi.
Rota muloqoti (chat, oynalar, tonggi raport) endi Mini App ichida — bot guruh bilan ishlamaydi.
"""
import asyncio
import datetime as dt
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BufferedInputFile

import config
import keyboards
import texts
from api import backend

log = logging.getLogger(__name__)


async def safe_send(bot: Bot, chat_id, text, **kwargs):
    try:
        await bot.send_message(chat_id, text, **kwargs)
    except TelegramAPIError as e:
        log.warning("%s ga yuborilmadi: %s", chat_id, e)


async def deliver(bot: Bot, n):
    tg, kind, p = n["telegram_id"], n["kind"], n["payload"]
    if kind == "new_application":
        for admin in config.ADMIN_IDS:
            await safe_send(bot, admin, texts.new_application(p, tg), reply_markup=keyboards.admin_decision(tg))
    elif kind == "approved":
        await bot.send_message(tg, texts.approved(p), reply_markup=keyboards.main_menu())
        if p.get("squad"):
            # Birinchi kundan tushunmovchilik bo'lmasin: raport qanday yuborilishi + mashq taklifi
            await bot.send_message(tg, texts.t("guide"))
    elif kind == "rejected":
        await bot.send_message(tg, texts.t("rejected"))
    elif kind == "review_request":
        if p.get("local"):  # Mini App'da yozilgan video — bot yuklab, oddiy video sifatida yuboradi
            try:
                data = await backend.review_video_bytes(p["review_id"])
                await bot.send_video(tg, BufferedInputFile(data, filename="raport.mp4"))
            except Exception as e:  # noqa: BLE001 — yuklanmasa ham baholash tugmalari boradi
                log.warning("Tekshiruv videosi yuborilmadi (review %s): %s", p.get("review_id"), e)
        elif p.get("file_id"):
            await bot.send_video_note(tg, p["file_id"])
        await bot.send_message(tg, texts.review_request(p), reply_markup=keyboards.review(p["review_id"]))
    elif kind == "video_approved":
        await bot.send_message(tg, texts.t("video_approved", day=p["day_number"]))
    elif kind == "video_rejected":
        await bot.send_message(tg, texts.t("video_rejected"))
    elif kind == "strike":
        await bot.send_message(tg, texts.strike(p))
    elif kind == "immunity_used":
        await bot.send_message(tg, texts.t("immunity_used", reason=texts.reason(p["reason"])))
    elif kind == "immunity_granted":
        await bot.send_message(tg, texts.immunity_granted(p.get("source")))
    elif kind == "expelled":
        await bot.send_message(tg, texts.t("expelled"))
    elif kind == "stage_up":
        png = await backend.award_image(p["award_id"])
        await bot.send_photo(tg, BufferedInputFile(png, filename=f"21tong-{p['number']}.png"), caption=texts.award_caption(p))
    elif kind == "broadcast":
        await bot.send_message(tg, p["text"])


async def notifications_loop(bot: Bot, interval=5):
    while True:
        await texts.refresh()  # admin panelda o'zgargan matnlar 30 soniyada yetib keladi
        try:
            items = await backend.notifications()
            done = []
            for n in items:
                try:
                    await deliver(bot, n)
                except TelegramAPIError as e:
                    log.warning("Notification %s yetkazilmadi: %s", n["id"], e)
                done.append(n["id"])  # bloklagan foydalanuvchi navbatni to'xtatmasin
            if done:
                await backend.ack(done)
        except Exception:
            log.exception("notifications_loop")
        await asyncio.sleep(interval)


async def minute_loop(bot: Bot):
    """Har daqiqa boshida: budilniklar, kunlik hisob va startgacha eslatma."""
    while True:
        now = dt.datetime.now(config.TZ)
        await asyncio.sleep(60 - now.second)
        hhmm = dt.datetime.now(config.TZ).strftime("%H:%M")
        jobs = [send_alarms(bot, hhmm)]
        if hhmm == DAILY_AT:
            jobs.append(backend.run_daily())
        if hhmm == COUNTDOWN_AT:
            jobs.append(send_countdowns(bot))
        for job in jobs:
            try:
                await job
            except Exception:
                log.exception("minute_loop")


# Kunlik hisob (kechagi kunni baholash, oqimni boshlash) — cron kerak emas, bot o'zi chaqiradi
DAILY_AT = "00:05"
# Startni kutayotganlarga "Startga N kun qoldi" eslatmasi
COUNTDOWN_AT = "20:00"


async def send_countdowns(bot: Bot):
    for r in await backend.countdown():
        await safe_send(bot, r["telegram_id"], texts.countdown(r))


async def send_alarms(bot: Bot, hhmm):
    for a in await backend.alarms(hhmm):
        await safe_send(bot, a["telegram_id"], texts.alarm(a["day_number"], hhmm), reply_markup=keyboards.alarm())
