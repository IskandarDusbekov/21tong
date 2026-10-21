from aiogram.types import (
    InlineKeyboardButton as B, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo,
)

import config

# Pastki menyu tugmalari (ReplyKeyboard) — har biri aniq amal bajaradi
BTN_STATUS = "☀️ Holatim"
BTN_GUIDE = "📘 Yo'riqnoma"
BTN_RULES = "📜 Nizom"
BTN_REFERRAL = "👥 Do'st taklif"


def _kb(*rows):
    return InlineKeyboardMarkup(inline_keyboard=[list(r) for r in rows])


def main_menu():
    """Doimiy pastki menyu — faqat qabul qilinganlarga ko'rsatiladi."""
    rows = []
    if config.MINI_APP_URL:
        rows.append([KeyboardButton(text="📱 Mini App", web_app=WebAppInfo(url=config.MINI_APP_URL))])
    rows.append([KeyboardButton(text=BTN_STATUS), KeyboardButton(text=BTN_GUIDE)])
    rows.append([KeyboardButton(text=BTN_RULES), KeyboardButton(text=BTN_REFERRAL)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True,
                               input_field_placeholder="Raportni ovozli xabar qilib yuboring")


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


def start_application():
    return _kb([B(text="📝 Arizani boshlash", callback_data="apply:begin")])


def regions(items):
    """Viloyatlar — ikki ustunda."""
    buttons = [B(text=r["label"], callback_data=f"region:{r['value']}") for r in items]
    return _kb(*[buttons[i:i + 2] for i in range(0, len(buttons), 2)])


def slots(items, prefix="slot"):
    """Tayyor rotalar: «06:00 → 05:00 · Erta qushlar»."""
    rows = []
    for s in items:
        label = f"⏰ {s['start_wake_time']} → {s['target_wake_time']}"
        if s.get("title"):
            label += f" · {s['title']}"
        rows.append([B(text=label, callback_data=f"{prefix}:{s['id']}")])
    return _kb(*rows)


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
