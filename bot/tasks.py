"""
Fon vazifalari:
  * notifications — backend outbox'idagi voqealarni foydalanuvchilarga yetkazadi;
  * alarms        — har daqiqada budilnik vaqti kelganlarni uyg'otadi;
  * windows       — qabila chatlarini "Oyna" jadvali bo'yicha ochadi/qulflaydi.
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


async def deliver(bot: Bot, n):
    tg, kind, p = n["telegram_id"], n["kind"], n["payload"]
    if kind == "approved":
        await bot.send_message(tg, texts.APPROVED)
    elif kind == "rejected":
        await bot.send_message(tg, texts.REJECTED)
    elif kind == "review_request":
        await bot.send_video_note(tg, p["file_id"])
        await bot.send_message(tg, texts.REVIEW_REQUEST, reply_markup=keyboards.review(p["review_id"]))
    elif kind == "video_approved":
        await bot.send_message(tg, texts.VIDEO_APPROVED.format(day=p["day_number"]))
    elif kind == "video_rejected":
        await bot.send_message(tg, texts.VIDEO_REJECTED)
    elif kind == "strike":
        reason = texts.STRIKE_REASONS.get(p["reason"], p["reason"])
        await bot.send_message(tg, texts.STRIKE.format(count=p["count"], max=p["max"], reason=reason))
    elif kind == "joker_used":
        await bot.send_message(tg, texts.JOKER_USED.format(reason=texts.STRIKE_REASONS.get(p["reason"], "")))
    elif kind == "joker_granted":
        await bot.send_message(tg, texts.JOKER_GRANTED.get(p.get("source"), "🃏 Sizga Joker berildi!"))
    elif kind == "expelled":
        await bot.send_message(tg, texts.EXPELLED)
        if p.get("tribe_chat_id"):
            await bot.ban_chat_member(p["tribe_chat_id"], tg)
            await bot.unban_chat_member(p["tribe_chat_id"], tg, only_if_banned=True)
    elif kind == "stage_up":
        await bot.send_message(tg, texts.STAGE_UP.format(name=p["name"], day=p["day"]))


async def notifications_loop(bot: Bot, interval=5):
    while True:
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
    """Har daqiqa boshida: budilniklar va chat oynalari."""
    window_state: dict[int, str] = {}
    while True:
        now = dt.datetime.now(config.TZ)
        await asyncio.sleep(60 - now.second)
        now = dt.datetime.now(config.TZ)
        hhmm = now.strftime("%H:%M")
        try:
            await send_alarms(bot, hhmm)
            await sync_windows(bot, hhmm, window_state)
        except Exception:
            log.exception("minute_loop")


async def send_alarms(bot: Bot, hhmm):
    for a in await backend.alarms(hhmm):
        hint = texts.FACELESS_HINT if a.get("gender") == "F" else ""
        text = (
            f"{texts.alarm(a['day_number'])}\n\n{texts.STEPS}\n\n"
            f"🗣 <b>«{texts.cognitive_phrase()}»</b>{hint}"
        )
        try:
            await bot.send_message(a["telegram_id"], text, reply_markup=keyboards.mini_app())
        except TelegramAPIError as e:
            log.warning("Budilnik %s ga yetmadi: %s", a["telegram_id"], e)


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
                    await bot.send_message(chat, texts.CHAT_CLOSED)
            else:
                await bot.set_chat_permissions(chat, OPEN)
                await bot.send_message(chat, texts.CHAT_OPEN[current])
            state[chat] = current
        except TelegramAPIError as e:
            log.warning("Chat %s oynasini o'zgartirib bo'lmadi (bot admin emasmi?): %s", chat, e)
