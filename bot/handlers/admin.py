"""Qo'mondonlik: arizalarni tasdiqlash va rad etish."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import config
import keyboards
import texts
from api import ApiError, backend

router = Router()


@router.callback_query(F.data.startswith("adm:"))
async def decide(call: CallbackQuery):
    if not config.is_admin(call.from_user.id):
        return await call.answer(texts.NOT_ADMIN, show_alert=True)
    _, action, telegram_id = call.data.split(":")
    try:
        user = await (backend.approve if action == "ok" else backend.reject)(int(telegram_id))
    except ApiError as e:
        await call.message.edit_reply_markup(reply_markup=None)
        return await call.answer(str(e.detail), show_alert=True)

    m = user.get("membership")
    verdict = (
        f"✅ <b>Qabul qilindi</b> — {call.from_user.first_name}"
        + (f"\nJoylashdi: {m['squad']} · {m['tribe']}" if m else "\nQabul ochiq oqim yo'q — oqim e'lon qilinganda /join.")
        if action == "ok"
        else f"❌ <b>Rad etildi</b> — {call.from_user.first_name}"
    )
    await call.message.edit_text(f"{call.message.html_text}\n\n{verdict}", reply_markup=None)
    await call.answer("Bajarildi")


@router.message(Command("arizalar"), F.chat.type == "private")
async def pending(message: Message):
    if not config.is_admin(message.from_user.id):
        return await message.answer(texts.NOT_ADMIN)
    items = await backend.pending()
    if not items:
        return await message.answer(texts.NO_PENDING)
    for p in items:
        await message.answer(texts.new_application(p, p["telegram_id"]), reply_markup=keyboards.admin_decision(p["telegram_id"]))
