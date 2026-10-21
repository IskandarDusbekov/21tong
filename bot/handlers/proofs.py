"""
Tonggi zanjir: "Uyg'ondim" -> BUYRUQ (o'qiladigan gap) -> raport botga (ovoz yoki video krujok).
Raport backend'ga yoziladi va Mini App ichidagi rota chatida paydo bo'ladi — rotadoshlar eshitadi/ko'radi.
"""
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

import texts
from api import ApiError, backend

router = Router()


@router.callback_query(F.data == "wake")
async def wake(call: CallbackQuery):
    try:
        p = await backend.wake(call.from_user.id)
    except ApiError as e:
        return await call.answer(str(e.detail), show_alert=True)
    user = await backend.get_user(call.from_user.id)
    await call.message.edit_reply_markup(reply_markup=None)
    await call.answer("Xayrli tong! Buyruqni o'qing.")
    await call.message.answer(texts.order(p, user and user.get("gender")))


@router.message(F.chat.type == "private", F.voice)
async def voice(message: Message):
    try:
        p = await backend.voice(message.from_user.id, message.voice.file_id)
    except ApiError as e:
        if e.status == 404:
            return await message.answer(texts.t("not_registered"))
        return await message.answer(f"⛔ {e.detail}")
    if p.get("practice"):
        return await message.answer(texts.practice(p))
    await message.answer(texts.t("voice_ok", day=p["day_number"]))


@router.message(F.chat.type == "private", F.video_note | F.video)
async def video(message: Message):
    media = message.video_note or message.video
    try:
        p = await backend.video(message.from_user.id, media.file_id, media.duration or 0)
    except ApiError as e:
        return await message.answer(f"⛔ {e.detail}")
    await message.answer(texts.t("video_sent") if p["proof_status"] == "reviewing" else texts.t("voice_ok", day=p["day_number"]))


@router.message(F.chat.type == "private", F.audio | F.photo | F.document)
async def wrong_media(message: Message):
    await message.answer(texts.t("unknown_media"))


@router.callback_query(F.data.startswith("vote:"))
async def vote(call: CallbackQuery):
    _, review_id, approved = call.data.split(":")
    try:
        await backend.vote(int(review_id), call.from_user.id, approved == "1")
    except ApiError as e:
        return await call.answer(str(e.detail), show_alert=True)
    verdict = "✅ Siz tasdiqladingiz" if approved == "1" else "❌ Siz rad etdingiz"
    await call.message.edit_text(f"{call.message.html_text}\n\n<b>{verdict}</b>", reply_markup=None)
    await call.answer(texts.t("vote_thanks"))
