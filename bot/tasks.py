"""
Fon vazifalari:
  * notifications — backend outbox'idagi voqealarni yetkazadi (shaxsan, adminlarga, rota guruhiga);
  * alarms        — har daqiqada budilnik vaqti kelganlarni "TURISH!" bilan uyg'otadi;
  * windows       — rota chatlarini "Oyna" jadvali bo'yicha ochadi/qulflaydi;
  * roll call     — tonggi oyna yopilganda rota guruhiga RAPORT chiqaradi.
"""
import asyncio
import datetime as dt
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatPermissions

import config
import keyboards
import texts
from api import backend

log = logging.getLogger(__name__)

OPEN = ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_voice_notes=True,
                       can_send_video_notes=True, can_send_videos=True, can_send_photos=True)
LOCKED = ChatPermissions(can_send_messages=False)


async def safe_send(bot: Bot, chat_id, text, **kwargs):
    try:
        await bot.send_message(chat_id, text, **kwargs)
    except TelegramAPIError as e:
        log.warning("%s ga yuborilmadi: %s", chat_id, e)


async def deliver(bot: Bot, n):
    tg, kind, p = n["telegram_id"], n["kind"], n["payload"]
    squad_chat = p.get("squad_chat_id")
    if kind == "new_application":
        for admin in config.ADMIN_IDS:
            await safe_send(bot, admin, texts.new_application(p, tg), reply_markup=keyboards.admin_decision(tg))
    elif kind == "approved":
        await bot.send_message(tg, texts.approved(p))
    elif kind == "rejected":
        await bot.send_message(tg, texts.t("rejected"))
    elif kind == "review_request":
        await bot.send_video_note(tg, p["file_id"])
        await bot.send_message(tg, texts.review_request(p), reply_markup=keyboards.review(p["review_id"]))
    elif kind == "video_approved":
        await bot.send_message(tg, texts.t("video_approved", day=p["day_number"]))
    elif kind == "video_rejected":
        await bot.send_message(tg, texts.t("video_rejected"))
    elif kind == "strike":
        await bot.send_message(tg, texts.strike(p))
        if squad_chat:
            await safe_send(bot, squad_chat, texts.strike_public(p))
    elif kind == "immunity_used":
        await bot.send_message(tg, texts.t("immunity_used", reason=texts.reason(p["reason"])))
    elif kind == "immunity_granted":
        await bot.send_message(tg, texts.immunity_granted(p.get("source")))
    elif kind == "expelled":
        await bot.send_message(tg, texts.t("expelled"))
        if squad_chat:
            await safe_send(bot, squad_chat, texts.t("expelled_public", name=texts.escape(p["name"])))
            await bot.ban_chat_member(squad_chat, tg)
            await bot.unban_chat_member(squad_chat, tg, only_if_banned=True)
    elif kind == "stage_up":
        await bot.send_message(tg, texts.stage_up(p))
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
    """Har daqiqa boshida: budilniklar, chat oynalari va tonggi raport."""
    window_state: dict[int, str] = {}
    while True:
        now = dt.datetime.now(config.TZ)
        await asyncio.sleep(60 - now.second)
        hhmm = dt.datetime.now(config.TZ).strftime("%H:%M")
        for job in (send_alarms(bot, hhmm), sync_windows(bot, hhmm, window_state), send_roll_calls(bot, hhmm)):
            try:
                await job
            except Exception:
                log.exception("minute_loop")


async def send_alarms(bot: Bot, hhmm):
    for a in await backend.alarms(hhmm):
        await safe_send(bot, a["telegram_id"], texts.alarm(a["day_number"], hhmm), reply_markup=keyboards.alarm())


async def send_roll_calls(bot: Bot, hhmm):
    reports = await backend.roll_call()
    for r in reports:
        if r["morning_end"] == hhmm:
            await safe_send(bot, r["chat_id"], texts.roll_call(r))


def _current_window(w, hhmm):
    for name in ("morning", "evening"):
        start, end = w[name]
        if start <= hhmm < end:
            return name
    return None


async def sync_windows(bot: Bot, hhmm, state):
    for w in await backend.windows():
        chat = w["chat_id"]
        current = _current_window(w, hhmm) or "closed"
        if state.get(chat) == current:
            continue
        try:
            if current == "closed":
                await bot.set_chat_permissions(chat, LOCKED)
                if chat in state:
                    await bot.send_message(chat, texts.t("chat_closed"))
            else:
                await bot.set_chat_permissions(chat, OPEN)
                await bot.send_message(chat, texts.t(f"chat_open_{current}"))
            state[chat] = current
        except TelegramAPIError as e:
            log.warning("Chat %s oynasini o'zgartirib bo'lmadi (bot admin emasmi?): %s", chat, e)
