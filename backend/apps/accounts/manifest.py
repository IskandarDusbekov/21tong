"""
Taklif kartasi (storis formati, 1080x1920): ism, viloyat, rota vaqti, maqsad va
"Yolg'iz bo'lma — rota bo'lib harakat qil" chaqirig'i QR-kod bilan. Do'stni taklif qilish uchun.
"""
import qrcode
from django.conf import settings
from PIL import Image, ImageDraw

from apps.camp import graphics as g

W, H = 1080, 1920
WHITE = (255, 255, 255)
SUN = (242, 107, 33)
SUN_2 = (255, 173, 59)
NIGHT = (14, 18, 44)


def _qr(data, size):
    qr = qrcode.QRCode(border=1, box_size=10, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color=NIGHT, back_color="white").convert("RGB").resize((size, size), Image.NEAREST)


def _slot_info(user):
    m = user.memberships.select_related("tribe", "cohort").order_by("-joined_at").first()
    if m:
        return m.tribe.start_wake_time, m.target_wake_time, m.cohort.start_date
    if user.preferred_slot_id:
        s = user.preferred_slot
        return s.start_wake_time, s.target_wake_time, s.cohort.start_date
    return user.current_wake_time, user.target_wake_time, None


def _times(d, start, target, y):
    """«07:00 → 05:30» — strelka qo'lda chiziladi (hamma shriftda ham → belgisi yo'q)."""
    f = g.font("display", 110)
    a, b = f"{start:%H:%M}", f"{target:%H:%M}" if target else ""
    gap = 150 if b else 0
    wa, wb = g.text_width(d, a, f), g.text_width(d, b, f) if b else 0
    x = (W - (wa + gap + wb)) / 2
    d.text((x, y), a, font=f, fill=WHITE)
    if b:
        ax0, ax1, ay = x + wa + 34, x + wa + gap - 34, y + 56
        d.line([(ax0, ay), (ax1 - 10, ay)], fill=SUN_2, width=10)
        d.polygon([(ax1, ay), (ax1 - 30, ay - 22), (ax1 - 30, ay + 22)], fill=SUN_2)
        d.text((x + wa + gap, y), b, font=f, fill=SUN_2)


def render_manifest(user) -> bytes:
    img = g.vertical_gradient((W, H), [
        (0.0, (12, 15, 38)), (0.45, (30, 28, 78)), (0.72, (96, 46, 92)), (0.88, (214, 92, 52)), (1.0, (255, 150, 60)),
    ]).convert("RGBA")
    img.alpha_composite(g.glow((W, H), (W // 2, H + 120), 620, (255, 170, 70), 220, 120))

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    g.scatter_stars(d, (30, 30, W - 30, 1300), 110, seed=user.pk or 1,
                    avoid=[(120, 100, W - 120, 760), (130, 770, W - 130, 1090), (100, 1120, W - 100, 1320)])
    # Quyosh va tog'lar silueti
    d.ellipse([W / 2 - 300, H - 380, W / 2 + 300, H + 220], fill=(255, 196, 92, 255))
    d.polygon([(0, H - 250), (220, H - 420), (420, H - 300), (640, H - 470), (860, H - 320), (W, H - 430), (W, H), (0, H)], fill=(24, 16, 40, 255))
    d.polygon([(0, H - 150), (300, H - 290), (560, H - 190), (800, H - 300), (W, H - 200), (W, H), (0, H)], fill=(14, 10, 26, 255))
    img.alpha_composite(layer)

    d = ImageDraw.Draw(img)
    # Yuqori yorliq
    tag = "21 TONG  ·  INTIZOM LAGERI"
    f_tag = g.font("sans_bold", 30)
    tw = g.text_width(d, tag, f_tag) + 18 * (len(tag) - 1) * 0 + 70
    d.rounded_rectangle([(W - tw) / 2 - 10, 120, (W + tw) / 2 + 10, 182], radius=31, outline=(255, 255, 255, 140), width=2)
    g.centered(d, 133, tag, f_tag, WHITE, W)

    g.centered(d, 250, "MEN", g.font("display", 120), WHITE, W, spacing=10)
    g.centered(d, 380, "QO'SHILDIM", g.font("display", 140), SUN_2, W, spacing=6)

    name = user.display_name
    g.centered(d, 580, name, g.fit_font(d, name, "sans_bold", 78, W - 160), WHITE, W)
    if user.region:
        g.centered(d, 685, user.get_region_display(), g.font("sans", 38), (220, 214, 240), W)

    start, target, start_date = _slot_info(user)
    if start:
        box = [140, 780, W - 140, 1080]
        card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(card).rounded_rectangle(box, radius=40, fill=(255, 255, 255, 34), outline=(255, 255, 255, 70), width=2)
        img.alpha_composite(card)
        g.centered(d, 815, "HAR KUNI TURAMAN", g.font("sans_bold", 32), (230, 225, 250), W, spacing=4)
        _times(d, start, target, 870)
        sub = "21 kun · har tong ovozli raport" + (f" · start {start_date:%d.%m}" if start_date else "")
        g.centered(d, 1010, sub, g.font("sans", 32), (230, 225, 250), W)

    if user.goal:
        f_goal = g.font("serif_italic", 44)
        lines = g.wrap(d, f"«{user.goal}»", f_goal, W - 240)[:3]
        y = 1135
        for line in lines:
            g.centered(d, y, line, f_goal, (255, 240, 225), W)
            y += 60

    # Pastki chaqiriq kartasi + QR
    bot = getattr(settings, "TELEGRAM_BOT_USERNAME", "")
    link = f"https://t.me/{bot}?start={user.referral_code}" if bot else ""
    top = 1400
    d.rounded_rectangle([90, top, W - 90, top + 380], radius=44, fill=(255, 255, 255, 255))
    d.text((140, top + 50), "YOLG'IZ BO'LMA —", font=g.font("display", 50), fill=NIGHT)
    d.text((140, top + 112), "ROTA BO'LIB", font=g.font("display", 50), fill=SUN)
    d.text((140, top + 174), "HARAKAT QIL", font=g.font("display", 50), fill=SUN)
    d.text((140, top + 262), "Do'stingni chaqir — kamerani", font=g.font("sans", 30), fill=(90, 92, 110))
    d.text((140, top + 300), "QR kodga tut va qo'shil", font=g.font("sans", 30), fill=(90, 92, 110))
    if link:
        img.paste(_qr(link, 270), (W - 90 - 55 - 270, top + 55))
        g.centered(d, top + 400, f"t.me/{bot}", g.font("sans_bold", 34), WHITE, W)
    return g.png_bytes(img)
