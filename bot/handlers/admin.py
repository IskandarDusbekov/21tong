"""Qo'mondonlik: arizalarni tasdiqlash, rota guruhlarini ulash, guruhga kirishni nazorat qilish."""
from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ChatJoinRequest, Message

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


@router.message(Command("ulash"))
async def link_start(message: Message):
    """Rota guruhida: admin /ulash yozadi va guruh qaysi rotaga tegishli ekanini tanlaydi."""
    if not config.is_admin(message.from_user.id):
        return await message.answer(texts.NOT_ADMIN)
    if message.chat.type not in ("group", "supergroup"):
        return await message.answer(texts.LINK_HELP)
    squads = await backend.squads(unlinked=True)
    if not squads:
        return await message.answer(texts.NO_SQUADS)
    await message.answer("Bu guruh qaysi rotaniki?", reply_markup=keyboards.squads(squads))


@router.callback_query(F.data.startswith("link:"))
async def link_pick(call: CallbackQuery):
    if not config.is_admin(call.from_user.id):
        return await call.answer(texts.NOT_ADMIN, show_alert=True)
    squad_id = int(call.data.split(":")[1])
    chat = call.message.chat
    invite = ""
    try:
        # Kirish so'rov orqali — bot faqat shu rota a'zolarini kiritadi
        link = await call.bot.create_chat_invite_link(chat.id, name="21tong", creates_join_request=True)
        invite = link.invite_link
    except TelegramAPIError:
        pass  # bot admin emas — havolasiz ulaymiz, admin keyin qo'lda qo'shadi
    try:
        r = await backend.link_squad(squad_id, chat.id, invite)
    except ApiError as e:
        return await call.answer(str(e.detail), show_alert=True)
    await call.message.edit_text(texts.squad_linked(r))
    await call.answer()
    if invite:
        for tg in r["members"]:
            try:
                await call.bot.send_message(tg, texts.t("squad_invite", squad=r["name"], link=invite))
            except TelegramAPIError:
                pass


@router.chat_join_request()
async def join_request(req: ChatJoinRequest):
    """Guruhga faqat o'sha rotaning faol a'zosi kira oladi (gender-izolyatsiya ham shu yerda)."""
    user = await backend.get_user(req.from_user.id)
    m = user and user.get("membership")
    if m and m["status"] == "active" and m["squad_chat_id"] == req.chat.id:
        await req.approve()
    else:
        await req.decline()
        try:
            await req.bot.send_message(req.from_user.id, texts.t("join_denied"))
        except TelegramAPIError:
            pass
