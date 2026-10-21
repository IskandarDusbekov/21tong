"""3-bo'lim: anti-uyqu zanjirining 2- va 3-qadamlari hamda P2P ovoz berish."""
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

import texts
from api import ApiError, backend

router = Router()


@router.message(F.chat.type.in_({"group", "supergroup"}), F.voice)
async def group_voice(message: Message):
    """2-qadam: qabila guruhidagi ovozli xabar."""
    try:
        await backend.voice(message.from_user.id, message.chat.id)
    except ApiError as e:
        if e.status != 404:
            await message.reply(str(e.detail))
        return
    await message.reply(texts.VOICE_OK)


@router.message(F.chat.type == "private", F.video_note | F.video)
async def private_video(message: Message):
    """3-qadam: 10 soniyalik video krujok (yoki oddiy qisqa video)."""
    media = message.video_note or message.video
    try:
        result = await backend.video(message.from_user.id, media.file_id, media.duration or 0)
    except ApiError as e:
        return await message.answer(str(e.detail))
    await message.answer(texts.VIDEO_SENT if result["status"] == "reviewing" else texts.VIDEO_AUTO)


@router.callback_query(F.data.startswith("vote:"))
async def vote(call: CallbackQuery):
    _, review_id, approved = call.data.split(":")
    try:
        await backend.vote(int(review_id), call.from_user.id, approved == "1")
    except ApiError as e:
        return await call.answer(str(e.detail), show_alert=True)
    await call.message.edit_reply_markup(reply_markup=None)
    await call.answer(texts.VOTE_THANKS)
