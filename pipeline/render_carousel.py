#!/usr/bin/env python3
"""Render a carousel post.json into 1080x1350 JPEG slides (slides/01.jpg ...)."""
import argparse
from pathlib import Path

from common import BRAND, CONFIG, draw_rich, fit_rich, font, hex_rgb, load_post, new_canvas

W, H = 1080, 1350
M = 96                      # outer margin
FG = hex_rgb(BRAND["fg"])
ACC = hex_rgb(BRAND["accent"])
MUTED = hex_rgb(BRAND["muted"])
PANEL = hex_rgb(BRAND["panel"])
CODE_BG = hex_rgb(BRAND["code_bg"])


def chrome(d, idx, total, handle):
    """Handle top-left, counter top-right, progress dots bottom."""
    d.text((M, 64), handle, font=font("semibold", 30), fill=MUTED)
    counter = f"{idx}/{total}"
    f = font("semibold", 30)
    d.text((W - M - d.textlength(counter, font=f), 64), counter, font=f, fill=MUTED)
    dot_w, gap = 34, 12
    full = total * dot_w + (total - 1) * gap
    x = (W - full) / 2
    for i in range(total):
        col = ACC if i + 1 == idx else (60, 66, 80)
        d.rounded_rectangle([x, H - 70, x + dot_w, H - 62], radius=4, fill=col)
        x += dot_w + gap
    if idx < total:
        arrow = "Glisse  →"
        f2 = font("semibold", 28)
        d.text((W - M - d.textlength(arrow, font=f2), H - 120), arrow, font=f2, fill=ACC)


def slide_cover(d, s):
    fnt, lines, h = fit_rich(d, s["title"], "bold", W - 2 * M, 640, 128, 64, 1.05)
    y = 330
    draw_rich(d, lines, fnt, M, y, FG, ACC, line_gap=1.05)
    y += h + 40
    if s.get("subtitle"):
        f2, l2, _ = fit_rich(d, s["subtitle"], "regular", W - 2 * M, 200, 44, 32)
        d.rounded_rectangle([M, y, M + 90, y + 8], radius=4, fill=ACC)
        draw_rich(d, l2, f2, M, y + 40, MUTED, ACC)


def slide_text(d, s):
    y = 240
    if s.get("title"):
        fnt, lines, h = fit_rich(d, s["title"], "bold", W - 2 * M, 330, 84, 48, 1.08)
        draw_rich(d, lines, fnt, M, y, FG, ACC, line_gap=1.08)
        y += h + 50
    if s.get("body"):
        fnt, lines, _ = fit_rich(d, s["body"], "regular", W - 2 * M, H - y - 200, 50, 32, 1.3)
        draw_rich(d, lines, fnt, M, y, (205, 210, 220), ACC, line_gap=1.3)


def slide_list(d, s):
    y = 220
    fnt, lines, h = fit_rich(d, s.get("title", ""), "bold", W - 2 * M, 260, 76, 46, 1.08)
    draw_rich(d, lines, fnt, M, y, FG, ACC, line_gap=1.08)
    y += h + 50
    items = s.get("items", [])
    avail = H - y - 200
    per = avail / max(1, len(items))
    for i, item in enumerate(items, 1):
        d.rounded_rectangle([M, y, W - M, y + per - 22], radius=22, fill=PANEL)
        num = f"{i:02d}"
        d.text((M + 32, y + 26), num, font=font("bold", 40), fill=ACC)
        f2, l2, _ = fit_rich(d, item, "semibold", W - 2 * M - 150, per - 70, 44, 26, 1.2)
        draw_rich(d, l2, f2, M + 130, y + 28, FG, ACC, line_gap=1.2)
        y += per


def slide_code(d, s):
    y = 220
    if s.get("title"):
        fnt, lines, h = fit_rich(d, s["title"], "bold", W - 2 * M, 240, 72, 44, 1.08)
        draw_rich(d, lines, fnt, M, y, FG, ACC, line_gap=1.08)
        y += h + 40
    code = s.get("code", "").rstrip("\n").split("\n")
    longest = max((len(l) for l in code), default=1)
    size = 40
    while size > 20:
        f = font("mono", size)
        if (max(d.textlength(l, font=f) for l in code) <= W - 2 * M - 80
                and len(code) * size * 1.45 <= H - y - 330):
            break
        size -= 2
    f = font("mono", size)
    box_h = len(code) * size * 1.45 + 120
    d.rounded_rectangle([M, y, W - M, y + box_h], radius=26, fill=CODE_BG, outline=(40, 46, 60), width=2)
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([M + 32 + i * 34, y + 30, M + 52 + i * 34, y + 50], fill=col)
    if s.get("lang"):
        lf = font("semibold", 24)
        d.text((W - M - 32 - d.textlength(s["lang"], font=lf), y + 26), s["lang"], font=lf, fill=MUTED)
    cy = y + 80
    for line in code:
        prompt = line.startswith("$ ")
        d.text((M + 40, cy), line, font=f, fill=ACC if prompt else (220, 226, 236))
        cy += size * 1.45
    if s.get("note"):
        f2, l2, _ = fit_rich(d, s["note"], "regular", W - 2 * M, 160, 38, 28)
        draw_rich(d, l2, f2, M, y + box_h + 36, MUTED, ACC)


def slide_stat(d, s):
    vf, vl, vh = fit_rich(d, s["value"], "bold", W - 2 * M, 380, 260, 100, 1.0)
    y = 360
    draw_rich(d, vl, vf, M, y, ACC, ACC, line_gap=1.0)
    y += vh + 40
    lf, ll, lh = fit_rich(d, s.get("label", ""), "semibold", W - 2 * M, 300, 60, 36, 1.15)
    draw_rich(d, ll, lf, M, y, FG, ACC, line_gap=1.15)
    if s.get("note"):
        nf, nl, _ = fit_rich(d, s["note"], "regular", W - 2 * M, 120, 30, 24)
        draw_rich(d, nl, nf, M, H - 230, MUTED, ACC)


def slide_cta(d, s, handle):
    fnt, lines, h = fit_rich(d, s.get("title", ""), "bold", W - 2 * M, 420, 110, 56, 1.05)
    y = 380
    draw_rich(d, lines, fnt, M, y, FG, ACC, line_gap=1.05)
    y += h + 40
    if s.get("body"):
        f2, l2, h2 = fit_rich(d, s["body"], "regular", W - 2 * M, 260, 46, 32, 1.3)
        draw_rich(d, l2, f2, M, y, (205, 210, 220), ACC, line_gap=1.3)
        y += h2 + 40
    pf = font("bold", 40)
    pw = d.textlength(handle, font=pf) + 80
    d.rounded_rectangle([M, y + 20, M + pw, y + 110], radius=45, fill=ACC)
    d.text((M + 40, y + 42), handle, font=pf, fill=hex_rgb(BRAND["bg"]))


RENDER = {"cover": slide_cover, "text": slide_text, "list": slide_list,
          "code": slide_code, "stat": slide_stat}


def render(post_dir):
    post_dir = Path(post_dir)
    post = load_post(post_dir)
    slides = post["carousel"]["slides"]
    handle = CONFIG["account"]["handle"]
    out = post_dir / "slides"
    out.mkdir(exist_ok=True)
    for old in out.glob("*.jpg"):
        old.unlink()
    for i, s in enumerate(slides, 1):
        img, d = new_canvas(W, H)
        if s["kind"] == "cta":
            slide_cta(d, s, handle)
        else:
            RENDER[s["kind"]](d, s)
        chrome(d, i, len(slides), handle)
        img.save(out / f"{i:02d}.jpg", "JPEG", quality=92, optimize=True, progressive=False)
    return [out / f"{i:02d}.jpg" for i in range(1, len(slides) + 1)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("post_dir")
    for p in render(ap.parse_args().post_dir):
        print(p)
