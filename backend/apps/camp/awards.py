"""
Bosqich mukofotlari rasmda: pogon (harbiy unvon), medal yoki sertifikat.
Har birida ism-familiya, viloyat, bosqich, sana va o'zgarmas raqam bo'ladi.
"""
import math

from PIL import Image, ImageDraw, ImageFilter

from . import graphics as g

NAVY = (18, 22, 46)
NAVY_2 = (30, 36, 78)
GOLD = (214, 168, 64)
GOLD_LIGHT = (246, 214, 126)
GOLD_DARK = (150, 108, 30)
CREAM = (251, 246, 234)
SUN = (242, 107, 33)
WHITE = (255, 255, 255)

AWARD_LABEL = {"pagon": "Pogon", "medal": "Medal", "certificate": "Sertifikat"}


def _context(award):
    m = award.membership
    u = m.user
    return {
        "name": u.display_name,
        "region": u.get_region_display() if u.region else "",
        "stage": award.stage.name,
        "rank": award.stage.rank or award.stage.name,
        "day": award.stage.day,
        "stars": award.stage.stars,
        "description": award.stage.description,
        "date": award.issued_at.strftime("%d.%m.%Y"),
        "number": award.number,
        "cohort": m.cohort.name,
    }


def _dark_background(w, h, seed):
    img = g.vertical_gradient((w, h), [(0.0, (10, 13, 32)), (0.6, NAVY_2), (1.0, (52, 34, 70))]).convert("RGBA")
    img.alpha_composite(g.glow((w, h), (w // 2, int(h * 0.36)), 380, (255, 190, 90), 120, 140))
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    # Yulduzlar faqat chetlarda — markazdagi rasm va matnga tushmaydi
    g.scatter_stars(ImageDraw.Draw(layer), (30, 30, w - 30, h - 30), 90, seed=seed, avoid=[(170, 50, w - 170, h - 60)])
    img.alpha_composite(layer)
    return img


def _footer(d, c, w, y):
    g.centered(d, y, c["name"], g.fit_font(d, c["name"], "sans_bold", 64, w - 140), WHITE, w)
    sub = " · ".join(x for x in [c["region"], c["cohort"]] if x)
    if sub:
        g.centered(d, y + 82, sub, g.font("sans", 32), (200, 200, 225), w)
    g.centered(d, y + 150, f"{c['date']}   ·   № {c['number']}", g.font("sans", 28), (160, 160, 195), w)


def _gold_star(d, cx, cy, r):
    d.polygon(g.star_points(cx, cy, r + 4), fill=GOLD_DARK)
    d.polygon(g.star_points(cx, cy, r), fill=GOLD_LIGHT)
    d.polygon(g.star_points(cx, cy - r * 0.08, r * 0.55), fill=(255, 236, 170))


# --- Pogon ------------------------------------------------------------------------

def render_pagon(c, seed=1):
    w, h = 1080, 1350
    img = _dark_background(w, h, seed)
    d = ImageDraw.Draw(img)
    g.centered(d, 70, "UNVON BERILDI", g.font("sans_bold", 34), GOLD_LIGHT, w, spacing=8)

    # Pogon shakli: pastda to'g'ri, tepasi uchli
    bx0, bx1, by0, by1 = w / 2 - 150, w / 2 + 150, 170, 860
    shape = [(bx0, by1), (bx0, by0 + 90), (w / 2, by0), (bx1, by0 + 90), (bx1, by1)]
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).polygon([(x + 14, y + 18) for x, y in shape], fill=(0, 0, 0, 120))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(img)
    d.polygon(shape, fill=GOLD)
    inner = [(bx0 + 12, by1 - 12), (bx0 + 12, by0 + 96), (w / 2, by0 + 16), (bx1 - 12, by0 + 96), (bx1 - 12, by1 - 12)]
    d.polygon(inner, fill=(28, 46, 88))
    # Mato chiziqlari
    for x in range(int(bx0 + 24), int(bx1 - 12), 9):
        d.line([(x, by0 + 110), (x, by1 - 14)], fill=(34, 54, 100), width=2)
    # Ikki uzunasiga chiziq (lychka)
    d.rectangle([w / 2 - 48, by0 + 130, w / 2 - 34, by1 - 12], fill=GOLD)
    d.rectangle([w / 2 + 34, by0 + 130, w / 2 + 48, by1 - 12], fill=GOLD)
    # Tugma
    d.ellipse([w / 2 - 34, by0 + 48, w / 2 + 34, by0 + 116], fill=GOLD_DARK)
    d.ellipse([w / 2 - 28, by0 + 54, w / 2 + 28, by0 + 110], fill=GOLD_LIGHT)
    _gold_star(d, w / 2, by0 + 82, 16)
    # Yulduzlar
    n = max(0, min(c["stars"], 4))
    for i in range(n):
        _gold_star(d, w / 2, by1 - 110 - i * 120, 44)

    g.centered(d, 900, c["rank"].upper(), g.fit_font(d, c["rank"].upper(), "display", 86, w - 120), GOLD_LIGHT, w, spacing=3)
    g.centered(d, 1000, f"«{c['stage']}» · {c['day']}-kun", g.font("serif_italic", 38), (230, 225, 245), w)
    _footer(d, c, w, 1075)
    return img


# --- Medal ------------------------------------------------------------------------

def render_medal(c, seed=1):
    w, h = 1080, 1350
    img = _dark_background(w, h, seed)
    d = ImageDraw.Draw(img)
    g.centered(d, 70, "21 TONG  ·  MEDAL", g.font("sans_bold", 34), GOLD_LIGHT, w, spacing=6)

    cx, cy, r = w / 2, 560, 230
    # Lenta
    ribbon_top = 140
    for i, color in enumerate([SUN, NAVY, WHITE, NAVY, SUN]):
        x0 = cx - 150 + i * 60
        d.polygon([(x0, ribbon_top), (x0 + 60, ribbon_top), (x0 + 60 + (cx - x0 - 30) * 0.35, cy - r + 30),
                   (x0 + (cx - x0 - 30) * 0.35, cy - r + 30)], fill=color)
    d.rectangle([cx - 150, ribbon_top - 14, cx + 150, ribbon_top + 6], fill=GOLD_DARK)
    # Medal doiralari
    for rr, col in [(r + 16, GOLD_DARK), (r + 6, GOLD), (r - 18, GOLD_LIGHT), (r - 34, GOLD), (r - 46, (232, 190, 92))]:
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col)
    # Doira bo'ylab nuqtalar
    for k in range(36):
        a = math.radians(k * 10)
        x, y = cx + (r - 26) * math.cos(a), cy + (r - 26) * math.sin(a)
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=GOLD_DARK)
    d.polygon(g.star_points(cx, cy - 6, 150, 62), fill=(204, 150, 44))
    d.polygon(g.star_points(cx, cy - 6, 136, 56), fill=GOLD_LIGHT)
    f_day = g.font("display", 104)
    day = str(c["day"])
    d.text((cx - g.text_width(d, day, f_day) / 2, cy - 72), day, font=f_day, fill=(120, 80, 14))
    g.centered(d, cy + 128, "KUN", g.font("sans_bold", 28), (120, 80, 14), w, spacing=6)

    g.centered(d, 850, c["stage"].upper(), g.fit_font(d, c["stage"].upper(), "display", 80, w - 120), GOLD_LIGHT, w, spacing=3)
    g.centered(d, 950, c["rank"], g.font("serif_italic", 40), (230, 225, 245), w)
    _footer(d, c, w, 1040)
    return img


# --- Sertifikat --------------------------------------------------------------------

def render_certificate(c, seed=1):
    w, h = 1600, 1130
    img = Image.new("RGBA", (w, h), CREAM)
    d = ImageDraw.Draw(img)
    # Ramka
    d.rectangle([28, 28, w - 28, h - 28], outline=GOLD, width=10)
    d.rectangle([52, 52, w - 52, h - 52], outline=GOLD_DARK, width=2)
    for x, y in [(52, 52), (w - 52, 52), (52, h - 52), (w - 52, h - 52)]:
        d.polygon([(x, y - 22), (x + 22, y), (x, y + 22), (x - 22, y)], fill=GOLD)
    # Gerb: chiqayotgan quyosh
    cx, top = w / 2, 100
    d.ellipse([cx - 64, top, cx + 64, top + 128], fill=NAVY)
    d.pieslice([cx - 38, top + 40, cx + 38, top + 116], 180, 360, fill=GOLD_LIGHT)
    for k in range(7):
        a = math.radians(180 + 15 + k * 25)
        d.line([(cx + 46 * math.cos(a), top + 78 + 46 * math.sin(a)), (cx + 58 * math.cos(a), top + 78 + 58 * math.sin(a))], fill=GOLD_LIGHT, width=4)
    d.line([(cx - 44, top + 80), (cx + 44, top + 80)], fill=GOLD_LIGHT, width=4)

    g.centered(d, 250, "SERTIFIKAT", g.font("serif_bold", 92), NAVY, w, spacing=14)
    g.centered(d, 365, "21 TONG  ·  INTIZOM LAGERI", g.font("sans_bold", 28), GOLD_DARK, w, spacing=6)
    g.centered(d, 440, "Ushbu sertifikat", g.font("serif_italic", 34), (90, 86, 80), w)
    name = c["name"]
    g.centered(d, 490, name, g.fit_font(d, name, "serif_bold", 84, w - 300), NAVY, w)
    d.line([(w / 2 - 380, 600), (w / 2 + 380, 600)], fill=GOLD, width=3)
    if c["region"]:
        g.centered(d, 612, c["region"], g.font("sans", 28), (110, 105, 98), w)

    body = (f"{c['day']} kunlik qat'iy rejimni sharaf bilan bosib o'tib, «{c['stage']}» bosqichiga erishgani "
            f"va «{c['rank']}» unvoniga sazovor bo'lgani uchun beriladi.")
    f_body = g.font("serif", 36)
    y = 680
    for line in g.wrap(d, body, f_body, w - 420):
        g.centered(d, y, line, f_body, (60, 58, 70), w)
        y += 52

    # Pastki qator: sana — muhr — qo'mondon
    base = h - 230
    d.line([(190, base + 60), (520, base + 60)], fill=(120, 115, 105), width=2)
    d.text((190, base + 10), c["date"], font=g.font("serif_bold", 34), fill=NAVY)
    d.text((190, base + 72), "Sana", font=g.font("sans", 26), fill=(120, 115, 105))
    d.line([(w - 520, base + 60), (w - 190, base + 60)], fill=(120, 115, 105), width=2)
    d.text((w - 520, base + 2), "21 Tong", font=g.font("serif_italic", 44), fill=NAVY)
    d.text((w - 520, base + 72), "Qo'mondon", font=g.font("sans", 26), fill=(120, 115, 105))
    # Muhr
    mx, my = w / 2, base + 20
    for rr, col, width in [(92, SUN, 6), (80, SUN, 2)]:
        d.ellipse([mx - rr, my - rr, mx + rr, my + rr], outline=col, width=width)
    d.polygon(g.star_points(mx, my - 18, 30, 12), fill=SUN)
    g.centered(d, my + 20, "21 TONG", g.font("sans_bold", 22), SUN, w, spacing=3)
    g.centered(d, h - 94, f"№ {c['number']}", g.font("sans", 24), (130, 124, 112), w)
    return img


RENDERERS = {"pagon": render_pagon, "medal": render_medal, "certificate": render_certificate}


def render_award(award) -> bytes:
    c = _context(award)
    return g.png_bytes(RENDERERS.get(award.stage.award_type, render_medal)(c, seed=award.pk or 1))


def render_preview(stage, name="Ism Familiya", region="Toshkent shahri") -> bytes:
    """Admin panelda bosqich mukofotini oldindan ko'rish uchun namunaviy rasm."""
    import datetime as dt

    c = {
        "name": name, "region": region, "stage": stage.name, "rank": stage.rank or stage.name,
        "day": stage.day, "stars": stage.stars, "description": stage.description,
        "date": dt.date.today().strftime("%d.%m.%Y"), "number": "21T-NAMUNA", "cohort": "Namuna oqim",
    }
    return g.png_bytes(RENDERERS.get(stage.award_type, render_medal)(c, seed=stage.pk or 1))
