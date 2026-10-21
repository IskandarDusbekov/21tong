"""Ariza: jins -> maqsad -> hozirgi vaqt -> maqsad vaqti -> tasdiqlash -> manifest."""
import re

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

TIME_RE = re.compile(r"^([01]?\d|2[0-3])[:.]([0-5]\d)$")


def norm_time(text):
    h, m = TIME_RE.match(text.strip()).groups()
    return f"{int(h):02d}:{m}"


class Apply(StatesGroup):
    gender = State()
    goal = State()
    current = State()
    target = State()
    confirm = State()


class Join(StatesGroup):
    start_time = State()
    target_time = State()


async def begin(message: Message, state: FSMContext, referral_code=None):
    await state.clear()
    await state.update_data(referral_code=referral_code)
    await state.set_state(Apply.gender)
    await message.answer(texts.WELCOME, reply_markup=keyboards.gender())


@router.message(CommandStart())
async def start(message: Message, command: CommandObject, state: FSMContext):
    user = await backend.get_user(message.from_user.id)
    status = user and user["status"]
    if status == "pending":
        return await message.answer(texts.ALREADY_PENDING)
    if status == "approved":
        return await message.answer(texts.welcome_back(user))
    if status == "rejected":
        return await message.answer(texts.REJECTED)
    await begin(message, state, command.args)


@router.message(Command("holat"))
async def holat(message: Message):
    user = await backend.get_user(message.from_user.id)
    if not user:
        return await message.answer(texts.NOT_REGISTERED)
    if user["status"] != "approved":
        return await message.answer(texts.ALREADY_PENDING if user["status"] == "pending" else texts.REJECTED)
    await message.answer(texts.welcome_back(user))


@router.message(Command("nizom"))
async def nizom(message: Message):
    await message.answer(texts.RULES)


@router.callback_query(Apply.gender, F.data.startswith("gender:"))
async def chose_gender(call: CallbackQuery, state: FSMContext):
    await state.update_data(gender=call.data.split(":")[1])
    await state.set_state(Apply.goal)
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(texts.ASK_GOAL)
    await call.answer()


@router.message(Apply.goal, F.text)
async def got_goal(message: Message, state: FSMContext):
    goal = message.text.strip()
    if len(goal) < 10:
        return await message.answer(texts.GOAL_TOO_SHORT)
    await state.update_data(goal=goal[:500])
    await state.set_state(Apply.current)
    await message.answer(texts.ASK_CURRENT_TIME)


@router.message(Apply.current, F.text.regexp(TIME_RE))
async def got_current(message: Message, state: FSMContext):
    await state.update_data(current=norm_time(message.text))
    await state.set_state(Apply.target)
    await message.answer(texts.ASK_TARGET_TIME)


@router.message(Apply.target, F.text.regexp(TIME_RE))
async def got_target(message: Message, state: FSMContext):
    target = norm_time(message.text)
    data = await state.get_data()
    if target > data["current"]:
        return await message.answer(texts.TARGET_LATER)
    await state.update_data(target=target)
    await state.set_state(Apply.confirm)
    await message.answer(texts.application_summary({**data, "target": target}), reply_markup=keyboards.confirm_application())


@router.message(Apply.current)
@router.message(Apply.target)
async def bad_time(message: Message):
    await message.answer(texts.BAD_TIME)


@router.callback_query(Apply.confirm, F.data == "apply:restart")
async def restart(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await call.message.edit_reply_markup(reply_markup=None)
    await call.answer()
    await begin(call.message, state, data.get("referral_code"))


@router.callback_query(Apply.confirm, F.data == "apply:send")
async def send(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    u = call.from_user
    try:
        user = await backend.register(
            telegram_id=u.id, gender=data["gender"], goal=data["goal"],
            current_wake_time=data["current"], target_wake_time=data["target"],
            username=u.username or "", first_name=u.first_name or "",
            referral_code=data.get("referral_code"),
        )
    except ApiError as e:
        return await call.answer(str(e.detail), show_alert=True)
    await state.clear()
    await call.message.edit_reply_markup(reply_markup=None)
    await call.answer()

    await call.message.answer(texts.SUBMITTED)
    me = await call.bot.me()
    link = f"https://t.me/{me.username}?start={user['referral_code']}"
    png = await backend.manifest(u.id)
    await call.message.answer_photo(
        BufferedInputFile(png, filename="manifest.png"),
        caption=texts.MANIFEST_CAPTION.format(link=link),
    )


# --- Zaxira: tasdiqlangan, lekin oqimga tushmagan foydalanuvchi uchun ---------------

@router.message(Command("join"))
async def join(message: Message, state: FSMContext):
    user = await backend.get_user(message.from_user.id)
    if not user:
        return await message.answer(texts.NOT_REGISTERED)
    if user["status"] != "approved":
        return await message.answer(texts.ALREADY_PENDING)
    cohorts = await backend.recruiting_cohorts()
    if not cohorts:
        return await message.answer("Hozircha qabul ochiq oqim yo'q. E'lon qilinishi bilan xabar beramiz.")
    await message.answer("Qaysi oqimga qo'shilasiz?", reply_markup=keyboards.cohorts(cohorts))


@router.callback_query(F.data.startswith("cohort:"))
async def chose_cohort(call: CallbackQuery, state: FSMContext):
    await state.update_data(cohort_id=int(call.data.split(":")[1]))
    await state.set_state(Join.start_time)
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(texts.ASK_CURRENT_TIME)
    await call.answer()


@router.message(Join.start_time, F.text.regexp(TIME_RE))
async def join_start(message: Message, state: FSMContext):
    await state.update_data(start=norm_time(message.text))
    await state.set_state(Join.target_time)
    await message.answer(texts.ASK_TARGET_TIME)


@router.message(Join.target_time, F.text.regexp(TIME_RE))
async def join_target(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        m = await backend.join(
            telegram_id=message.from_user.id, cohort_id=data["cohort_id"],
            start_wake_time=data["start"], target_wake_time=norm_time(message.text),
        )
    except ApiError as e:
        return await message.answer(str(e.detail))
    await state.clear()
    link = m["squad_invite_link"]
    await message.answer(
        f"Siz <b>{m['squad']}</b> · {m['tribe']} safidasiz.\n"
        + (f"Guruhga kiring: {link}" if link else "Guruh havolasi tez orada keladi.")
    )


@router.message(Join.start_time)
@router.message(Join.target_time)
async def join_bad_time(message: Message):
    await message.answer(texts.BAD_TIME)
