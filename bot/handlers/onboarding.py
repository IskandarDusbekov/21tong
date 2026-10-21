"""1-bo'lim: ro'yxatdan o'tish (jins -> maqsad -> manifest), oqimga qo'shilish."""
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

TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


class Signup(StatesGroup):
    gender = State()
    goal = State()


class Join(StatesGroup):
    start_time = State()
    target_time = State()


@router.message(CommandStart())
async def start(message: Message, command: CommandObject, state: FSMContext):
    user = await backend.get_user(message.from_user.id)
    if user and user["status"] == "pending":
        return await message.answer(texts.ALREADY_PENDING)
    if user and user["status"] == "approved":
        return await message.answer(texts.APPROVED)
    if user and user["status"] == "rejected":
        return await message.answer(texts.REJECTED)

    await state.clear()
    await state.update_data(referral_code=command.args)
    await state.set_state(Signup.gender)
    await message.answer(texts.WELCOME, reply_markup=keyboards.gender())


@router.callback_query(Signup.gender, F.data.startswith("gender:"))
async def chose_gender(call: CallbackQuery, state: FSMContext):
    await state.update_data(gender=call.data.split(":")[1])
    await state.set_state(Signup.goal)
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(texts.ASK_GOAL)
    await call.answer()


@router.message(Signup.goal, F.text)
async def got_goal(message: Message, state: FSMContext):
    goal = message.text.strip()
    if len(goal) < 10:
        return await message.answer(texts.GOAL_TOO_SHORT)
    data = await state.get_data()
    u = message.from_user
    try:
        user = await backend.register(
            telegram_id=u.id, gender=data["gender"], goal=goal[:500],
            username=u.username or "", first_name=u.first_name or "",
            referral_code=data.get("referral_code"),
        )
    except ApiError as e:
        return await message.answer(str(e.detail))
    await state.clear()

    await message.answer(texts.PENDING)
    me = await message.bot.me()
    link = f"https://t.me/{me.username}?start={user['referral_code']}"
    png = await backend.manifest(u.id)
    await message.answer_photo(
        BufferedInputFile(png, filename="manifest.png"),
        caption=texts.MANIFEST_CAPTION.format(link=link),
    )


@router.message(Command("join"))
async def join(message: Message, state: FSMContext):
    user = await backend.get_user(message.from_user.id)
    if not user:
        return await message.answer(texts.NOT_REGISTERED)
    if user["status"] != "approved":
        return await message.answer(texts.ALREADY_PENDING)
    cohorts = await backend.recruiting_cohorts()
    if not cohorts:
        return await message.answer(texts.NO_COHORTS)
    await message.answer("Qaysi oqimga qo'shilasiz?", reply_markup=keyboards.cohorts(cohorts))


@router.callback_query(F.data.startswith("cohort:"))
async def chose_cohort(call: CallbackQuery, state: FSMContext):
    await state.update_data(cohort_id=int(call.data.split(":")[1]))
    await state.set_state(Join.start_time)
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(texts.ASK_START_TIME)
    await call.answer()


@router.message(Join.start_time, F.text.regexp(TIME_RE))
async def got_start(message: Message, state: FSMContext):
    await state.update_data(start=message.text.zfill(5))
    await state.set_state(Join.target_time)
    await message.answer(texts.ASK_TARGET_TIME)


@router.message(Join.target_time, F.text.regexp(TIME_RE))
async def got_target(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        m = await backend.join(
            telegram_id=message.from_user.id, cohort_id=data["cohort_id"],
            start_wake_time=data["start"], target_wake_time=message.text.zfill(5),
        )
    except ApiError as e:
        return await message.answer(str(e.detail))
    await state.clear()
    await message.answer(texts.JOINED.format(tribe=m["tribe"], link=m["tribe_invite_link"] or "admin yuboradi"))


@router.message(Join.start_time)
@router.message(Join.target_time)
async def bad_time(message: Message):
    await message.answer(texts.BAD_TIME)
