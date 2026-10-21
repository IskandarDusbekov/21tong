"""
Rasm yasash uchun umumiy vositalar: shriftlar, gradientlar, yulduz shakli, matnni o'rash.
Shriftlar tizimdan qidiriladi (Windows: Segoe UI / Georgia, Linux: DejaVu / Liberation);
sozlamada MANIFEST_FONT_DIR berilsa, birinchi u yerdan.
"""
import functools
import math
import os
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_CANDIDATES = {
    "sans": ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"],
    "sans_bold": ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"],
    "display": ["bahnschrift.ttf", "segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"],
    "serif_bold": ["georgiab.ttf", "timesbd.ttf", "DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"],
    "serif_italic": ["georgiai.ttf", "timesi.ttf", "DejaVuSerif-Italic.ttf", "LiberationSerif-Italic.ttf"],
    "serif": ["georgia.ttf", "times.ttf", "DejaVuSerif.ttf", "LiberationSerif-Regular.ttf"],
}


def _font_dirs():
    dirs = [getattr(settings, "MANIFEST_FONT_DIR", "")]
    windir = os.environ.get("WINDIR")
    if windir:
        dirs.append(os.path.join(windir, "Fonts"))
    dirs += ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation",
             "/usr/share/fonts/dejavu", "/usr/share/fonts", "/Library/Fonts", "/System/Library/Fonts"]
    return [d for d in dirs if d and os.path.isdir(d)]


@functools.lru_cache(maxsize=None)
def _find(filename):
    for d in _font_dirs():
        direct = Path(d) / filename
        if direct.exists():
            return str(direct)
        for found in Path(d).rglob(filename):
            return str(found)
    return None


@functools.lru_cache(maxsize=None)
def font(kind, size):
    for name in FONT_CANDIDATES[kind]:
        path = _find(name)
        if path:
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def vertical_gradient(size, stops):
    """stops: [(0.0, (r,g,b)), (0.6, ...), (1.0, ...)] — yuqoridan pastga."""
    w, h = size
    strip = Image.new("RGB", (1, h))
    px = strip.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                k = (t - t0) / max(t1 - t0, 1e-6)
                px[0, y] = tuple(int(a + (b - a) * k) for a, b in zip(c0, c1))
                break
    return strip.resize((w, h))


def glow(size, center, radius, color, alpha=255, blur=80):
    """Yumshoq nur (quyosh, yorug'lik) qatlami."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = center
    d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(*color, alpha))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def star_points(cx, cy, r_outer, r_inner=None, points=5, rotation=-90):
    r_inner = r_inner or r_outer * 0.42
    pts = []
    for i in range(points * 2):
        r = r_outer if i % 2 == 0 else r_inner
        a = math.radians(rotation + i * 180 / points)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def scatter_stars(draw, box, count, seed, color=(255, 255, 255), avoid=()):
    """Tasodifiy yulduzlar; `avoid` dagi to'rtburchaklarga (matn joylari) tushmaydi."""
    import random

    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    for _ in range(count):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        if any(ax0 <= x <= ax1 and ay0 <= y <= ay1 for ax0, ay0, ax1, ay1 in avoid):
            continue
        r = rnd.choice([1, 1, 1.5, 2, 2.5])
        a = rnd.randint(90, 230)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(*color, a))


def text_width(draw, text, f):
    return draw.textlength(text, font=f)


def wrap(draw, text, f, max_width):
    words, lines, line = text.split(), [], ""
    for w in words:
        test = f"{line} {w}".strip()
        if text_width(draw, test, f) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def centered(draw, y, text, f, fill, width, spacing=0):
    """Markazga yozadi; spacing>0 bo'lsa harflar orasini kengaytiradi (sarlavhalar uchun)."""
    if spacing:
        total = sum(text_width(draw, ch, f) for ch in text) + spacing * (len(text) - 1)
        x = (width - total) / 2
        for ch in text:
            draw.text((x, y), ch, font=f, fill=fill)
            x += text_width(draw, ch, f) + spacing
        return
    draw.text(((width - text_width(draw, text, f)) / 2, y), text, font=f, fill=fill)


def fit_font(draw, text, kind, start, max_width, min_size=24):
    size = start
    while size > min_size and text_width(draw, text, font(kind, size)) > max_width:
        size -= 2
    return font(kind, size)


def png_bytes(img):
    import io

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()
