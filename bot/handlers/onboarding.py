"""
Ariza: ism -> familiya -> viloyat -> jins -> maqsad -> tayyor rotani tanlash -> tasdiqlash -> taklif rasmi.
Hamma savol tugmalar orqali yoki qisqa matn bilan — yangi odam adashib qolmasin.
"""
from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message

import keyboards
import texts
from api import ApiError, backend

router = Router()
router.message.filter(F.chat.type == "private")


class Apply(StatesGroup):
    first_name = State()
    last_name = State()
    region = State()
    gender = State()
    goal = State()
    slot = State()
    confirm = State()


def valid_name(text):
    name = " ".join((text or "").split())
    return name if 2 <= len(name) <= 30 and not any(ch.isdigit() for ch in name) else None


async def show_welcome(message: Message, state: FSMContext, referral_code=None):
    await texts.refresh()
    if not texts.setting("registration_open", True):
        return await message.answer(texts.t("registration_closed"))
    await state.clear()
    await state.update_data(referral_code=referral_code)
    await message.answer(texts.t("welcome"), reply_markup=keyboards.start_application())


@router.message(CommandStart())
async def start(message: Message, command: CommandObject, state: FSMContext):
    user = await backend.get_user(message.from_user.id)
    status = user and user["status"]
    if status == "pending":
        return await message.answer(texts.t("already_pending"))
    if status == "approved":
        return await message.answer(texts.welcome_back(user), reply_markup=keyboards.main_menu())
    if status == "rejected":
        return await message.answer(texts.t("rejected"))
    await show_welcome(message, state, command.args)


@router.callback_query(F.data == "apply:begin")
async def begin(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup(reply_markup=None)
    await state.set_state(Apply.first_name)
    await call.message.answer(texts.t("ask_first_name"))
    await call.answer()


@router.message(Command("holat"))
@router.message(F.text == keyboards.BTN_STATUS)
async def holat(message: Message):
    user = await backend.get_user(message.from_user.id)
    if not user:
        return await message.answer(texts.t("not_registered"))
    if user["status"] != "approved":
        return await message.answer(texts.t("already_pending") if user["status"] == "pending" else texts.t("rejected"))
    await message.answer(texts.welcome_back(user), reply_markup=keyboards.main_menu())


@router.message(Command("nizom"))
@router.message(F.text == keyboards.BTN_RULES)
async def nizom(message: Message):
    await message.answer(texts.t("rules"))


@router.message(Command("yoriqnoma"))
@router.message(F.text == keyboards.BTN_GUIDE)
async def guide(message: Message):
    await message.answer(texts.t("guide"))


@router.message(F.text == keyboards.BTN_REFERRAL)
async def referral(message: Message):
    user = await backend.get_user(message.from_user.id)
    if not user or user["status"] != "approved":
        return await message.answer(texts.t("not_registered"))
    me = await message.bot.me()
    link = f"https://t.me/{me.username}?start={user['referral_code']}"
    await message.answer(texts.t("referral_share", link=link))


# --- Anketa savollari ------------------------------------------------------------

@router.message(Apply.first_name, F.text)
async def got_first_name(message: Message, state: FSMContext):
    name = valid_name(message.text)
    if not name:
        return await message.answer(texts.t("bad_name"))
    await state.update_data(first_name=name)
    await state.set_state(Apply.last_name)
    await message.answer(texts.t("ask_last_name"))


@router.message(Apply.last_name, F.text)
async def got_last_name(message: Message, state: FSMContext):
    name = valid_name(message.text)
    if not name:
        return await message.answer(texts.t("bad_name"))
    await state.update_data(last_name=name)
    await state.set_state(Apply.region)
    await texts.refresh()
    await message.answer(texts.t("ask_region"), reply_markup=keyboards.regions(texts.regions()))


@router.callback_query(Apply.region, F.data.startswith("region:"))
async def got_region(call: CallbackQuery, state: FSMContext):
    value = call.data.split(":", 1)[1]
    label = next((r["label"] for r in texts.regions() if r["value"] == value), value)
    await state.update_data(region=value, region_label=label)
    await state.set_state(Apply.gender)
    await call.message.edit_text(f"{texts.t('ask_region')}\n✅ <b>{texts.escape(label)}</b>")
    await call.message.answer(texts.t("ask_gender"), reply_markup=keyboards.gender())
    await call.answer()


@router.callback_query(Apply.gender, F.data.startswith("gender:"))
async def got_gender(call: CallbackQuery, state: FSMContext):
    gender = call.data.split(":")[1]
    await state.update_data(gender=gender)
    await state.set_state(Apply.goal)
    await call.message.edit_text(f"{texts.t('ask_gender')}\n✅ <b>{texts.GENDER[gender]}</b>")
    await call.message.answer(texts.t("ask_goal"))
    await call.answer()


@router.message(Apply.goal, F.text)
async def got_goal(message: Message, state: FSMContext):
    goal = message.text.strip()
    if len(goal) < 10:
        return await message.answer(texts.t("goal_too_short"))
    await state.update_data(goal=goal[:500])
    slots = await backend.slots()
    if not slots:
        await state.clear()
        return await message.answer(texts.t("no_slots"))
    await state.update_data(slots={str(s["id"]): s for s in slots})
    await state.set_state(Apply.slot)
    await message.answer(texts.ask_slot(slots), reply_markup=keyboards.slots(slots))


@router.callback_query(Apply.slot, F.data.startswith("slot:"))
async def got_slot(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    slot = data["slots"].get(call.data.split(":")[1])
    if not slot:
        return await call.answer("Bu rota topilmadi, qaytadan tanlang.", show_alert=True)
    await state.update_data(slot=slot)
    await state.set_state(Apply.confirm)
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(texts.application_summary({**data, "slot": slot}), reply_markup=keyboards.confirm_application())
    await call.answer()


@router.message(Apply.first_name)
@router.message(Apply.last_name)
@router.message(Apply.goal)
async def need_text(message: Message):
    await message.answer("Iltimos, matn bilan javob bering.")


@router.message(Apply.region)
@router.message(Apply.gender)
@router.message(Apply.slot)
async def need_button(message: Message):
    await message.answer("Iltimos, yuqoridagi tugmalardan birini bosing 👆")


@router.callback_query(Apply.confirm, F.data == "apply:restart")
async def restart(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await call.message.edit_reply_markup(reply_markup=None)
    await call.answer()
    await show_welcome(call.message, state, data.get("referral_code"))


@router.callback_query(Apply.confirm, F.data == "apply:send")
async def send(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    u = call.from_user
    try:
        user = await backend.register(
            telegram_id=u.id, gender=data["gender"], goal=data["goal"],
            first_name=data["first_name"], last_name=data["last_name"], region=data["region"],
            slot_id=data["slot"]["id"], username=u.username or "",
            referral_code=data.get("referral_code"),
            tg_first_name=u.first_name or "", tg_last_name=u.last_name or "",
            tg_language=u.language_code or "", tg_is_premium=bool(u.is_premium),
        )
    except ApiError as e:
        return await call.answer(str(e.detail), show_alert=True)
    await state.clear()
    await call.message.edit_reply_markup(reply_markup=None)
    await call.answer()

    await call.message.answer(texts.t("submitted"))
    me = await call.bot.me()
    link = f"https://t.me/{me.username}?start={user['referral_code']}"
    png = await backend.manifest(u.id)
    await call.message.answer_photo(
        BufferedInputFile(png, filename="21tong.png"),
        caption=texts.t("manifest_caption", link=link),
    )


# --- Qabul qilingan, lekin oqimga tushmagan foydalanuvchi uchun -------------------

@router.message(Command("join"))
async def join(message: Message):
    user = await backend.get_user(message.from_user.id)
    if not user:
        return await message.answer(texts.t("not_registered"))
    if user["status"] != "approved":
        return await message.answer(texts.t("already_pending"))
    slots = await backend.slots()
    if not slots:
        return await message.answer(texts.t("no_slots"))
    await message.answer(texts.ask_slot(slots), reply_markup=keyboards.slots(slots, prefix="join"))


@router.callback_query(F.data.startswith("join:"))
async def join_slot(call: CallbackQuery):
    try:
        p = await backend.join(telegram_id=call.from_user.id, slot_id=int(call.data.split(":")[1]))
    except ApiError as e:
        return await call.answer(str(e.detail), show_alert=True)
    await call.message.edit_reply_markup(reply_markup=None)
    await call.answer()
    await call.message.answer(texts.approved(p))
    await call.message.answer(texts.t("guide"))
