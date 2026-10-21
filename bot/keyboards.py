from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

import config


def gender():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👨 Yigit", callback_data="gender:M"),
        InlineKeyboardButton(text="👩 Qiz", callback_data="gender:F"),
    ]])


def cohorts(items):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{c['name']} — {c['start_date']}", callback_data=f"cohort:{c['id']}")]
        for c in items
    ])


def review(review_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Tasdiqlayman ✅", callback_data=f"vote:{review_id}:1"),
        InlineKeyboardButton(text="Rad etaman ❌", callback_data=f"vote:{review_id}:0"),
    ]])


def mini_app():
    if not config.MINI_APP_URL:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="☀️ Uyg'ondim", web_app=WebAppInfo(url=config.MINI_APP_URL)),
    ]])
