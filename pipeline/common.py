"""Shared helpers: config, fonts, rich text drawing with **accent** markup."""
import json
import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
BRAND = CONFIG["brand"]

FONT_CANDIDATES = {
    "bold": ["/usr/share/fonts/opentype/inter/Inter-Bold.otf",
             "/usr/share/fonts/truetype/inter/Inter-Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/System/Library/Fonts/Supplemental/Arial Bold.ttf"],
    "semibold": ["/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
                 "/usr/share/fonts/truetype/inter/Inter-SemiBold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/System/Library/Fonts/Supplemental/Arial Bold.ttf"],
    "regular": ["/usr/share/fonts/opentype/inter/Inter-Regular.otf",
                "/usr/share/fonts/truetype/inter/Inter-Regular.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf"],
    "mono": ["/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
             "/System/Library/Fonts/Menlo.ttc"],
}
_font_cache = {}


def font(weight, size):
    key = (weight, size)
    if key not in _font_cache:
        for path in FONT_CANDIDATES[weight]:
            if os.path.exists(path):
                _font_cache[key] = ImageFont.truetype(path, size)
                break
        else:
            raise SystemExit(f"no font found for {weight}; install fonts-inter or fonts-dejavu")
    return _font_cache[key]


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def parse_rich(text):
    """'a **b** c' -> [('a ', False), ('b', True), (' c', False)] as word tokens."""
    tokens = []
    accent = False
    for part in re.split(r"(\*\*)", text):
        if part == "**":
            accent = not accent
            continue
        for w in re.findall(r"\S+|\n", part):
            # French punctuation preceded by a space (« ? », « : », « % ») must
            # never start a line: glue it to the previous word with a no-break space.
            if tokens and w in ("?", "!", ":", ";", "»", "%", "€", "$") and tokens[-1][0] != "\n":
                prev, acc = tokens.pop()
                tokens.append((prev + " " + w, acc))
                continue
            if tokens and tokens[-1][0] == "«":
                tokens.pop()
                w = "« " + w
            tokens.append((w, accent))
    return tokens


def wrap_rich(tokens, fnt, max_width, draw):
    lines, line, width = [], [], 0
    space = draw.textlength(" ", font=fnt)
    for word, acc in tokens:
        if word == "\n":
            lines.append(line)
            line, width = [], 0
            continue
        w = draw.textlength(word, font=fnt)
        add = w if not line else w + space
        if line and width + add > max_width:
            lines.append(line)
            line, width = [(word, acc)], w
        else:
            line.append((word, acc))
            width += add
    if line:
        lines.append(line)
    return lines


def fit_rich(draw, text, weight, max_width, max_height, start, minimum, line_gap=1.12):
    """Largest font size where the wrapped text fits the box."""
    tokens = parse_rich(text)
    size = start
    while size >= minimum:
        fnt = font(weight, size)
        lines = wrap_rich(tokens, fnt, max_width, draw)
        too_wide = any(draw.textlength(w, font=fnt) > max_width for w, _ in tokens if w != "\n")
        height = len(lines) * size * line_gap
        if height <= max_height and not too_wide:
            return fnt, lines, height
        size -= 4
    fnt = font(weight, minimum)
    lines = wrap_rich(tokens, fnt, max_width, draw)
    return fnt, lines, len(lines) * minimum * line_gap


def draw_rich(draw, lines, fnt, x, y, fg, accent, align="left", box_width=None, line_gap=1.12):
    size = fnt.size
    space = draw.textlength(" ", font=fnt)
    for line in lines:
        line_w = sum(draw.textlength(w, font=fnt) for w, _ in line) + space * max(0, len(line) - 1)
        cx = x
        if align == "center" and box_width:
            cx = x + (box_width - line_w) / 2
        for word, acc in line:
            draw.text((cx, y), word, font=fnt, fill=accent if acc else fg)
            cx += draw.textlength(word, font=fnt) + space
        y += size * line_gap
    return y


def new_canvas(w, h):
    key = (w, h)
    if key not in _bg_cache:
        bg = hex_rgb(BRAND["bg"])
        acc = hex_rgb(BRAND["accent"])
        # Soft accent glow in the top-right corner so frames are not flat black.
        small = Image.new("RGB", (w // 8, h // 8), bg)
        sd = ImageDraw.Draw(small)
        r = int(w / 8 * 0.75)
        glow = tuple(int(bg[k] + (acc[k] - bg[k]) * 0.16) for k in range(3))
        sd.ellipse([w // 8 - r, -r, w // 8 + r, r], fill=glow)
        small = small.filter(ImageFilter.GaussianBlur(r * 0.55))
        _bg_cache[key] = small.resize((w, h), Image.BICUBIC)
    img = _bg_cache[key].copy()
    return img, ImageDraw.Draw(img)


_bg_cache = {}


def load_post(post_dir):
    return json.loads((Path(post_dir) / "post.json").read_text(encoding="utf-8"))


def queue_dirs(base=None):
    base = Path(base or ROOT / "content" / "queue")
    return sorted(p for p in base.iterdir() if (p / "post.json").exists())
