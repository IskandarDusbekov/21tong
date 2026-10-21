"""
Virallik: foydalanuvchi maqsadi tushirilgan kvadrat "Manifest" rasmi (1080x1080, storis uchun).
"""
import io
import textwrap

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

SIZE = 1080
TOP = (20, 24, 48)       # tun
BOTTOM = (242, 140, 56)  # tong
FG = (255, 255, 255)


def _font(size):
    path = getattr(settings, "MANIFEST_FONT_PATH", "")
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def _gradient():
    img = Image.new("RGB", (SIZE, SIZE))
    draw = ImageDraw.Draw(img)
    for y in range(SIZE):
        t = y / (SIZE - 1)
        color = tuple(int(a + (b - a) * t) for a, b in zip(TOP, BOTTOM))
        draw.line([(0, y), (SIZE, y)], fill=color)
    return img


def _centered(draw, y, text, font):
    w = draw.textlength(text, font=font)
    draw.text(((SIZE - w) / 2, y), text, font=font, fill=FG)


def render_manifest(user) -> bytes:
    img = _gradient()
    draw = ImageDraw.Draw(img)

    _centered(draw, 110, "21 TONG", _font(110))
    _centered(draw, 250, "MANIFEST", _font(44))

    body = _font(54)
    lines = textwrap.wrap(f"“{user.goal}”", width=26)[:7]
    y = 380
    for line in lines:
        _centered(draw, y, line, body)
        y += 70

    name = user.first_name or (f"@{user.telegram_username}" if user.telegram_username else "")
    _centered(draw, 860, f"— {name}, 21 kunlik va'da", _font(40))

    bot = getattr(settings, "TELEGRAM_BOT_USERNAME", "")
    if bot:
        _centered(draw, 960, f"t.me/{bot}?start={user.referral_code}", _font(34))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
