from aiogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup, WebAppInfo

import config


def _kb(*rows):
    return InlineKeyboardMarkup(inline_keyboard=[list(r) for r in rows])


def gender():
    return _kb([B(text="👨 Yigit", callback_data="gender:M"), B(text="👩 Qiz", callback_data="gender:F")])


def confirm_application():
    return _kb(
        [B(text="✅ Arizani yuborish", callback_data="apply:send")],
        [B(text="✏️ Qaytadan to'ldirish", callback_data="apply:restart")],
    )


def admin_decision(telegram_id):
    return _kb([
        B(text="✅ Qabul", callback_data=f"adm:ok:{telegram_id}"),
        B(text="❌ Rad", callback_data=f"adm:no:{telegram_id}"),
    ])


def cohorts(items):
    return _kb(*[[B(text=f"{c['name']} — {c['start_date']}", callback_data=f"cohort:{c['id']}")] for c in items])


def squads(items):
    return _kb(*[[B(text=f"{s['name']} · {s['tribe']}", callback_data=f"link:{s['id']}")] for s in items])


def alarm():
    rows = [[B(text="☀️ Uyg'ondim", callback_data="wake")]]
    if config.MINI_APP_URL:
        rows.append([B(text="📱 Mini App", web_app=WebAppInfo(url=config.MINI_APP_URL))])
    return _kb(*rows)


def review(review_id):
    return _kb([
        B(text="Tasdiqlayman ✅", callback_data=f"vote:{review_id}:1"),
        B(text="Rad etaman ❌", callback_data=f"vote:{review_id}:0"),
    ])
