#!/usr/bin/env python3
"""A Grand Tour of China — 36 scenes of 32x32 pixel art for the iDotMatrix carousel.

The device carousels only 12 slots, so we pack **3 scenes per slot GIF** -> 12 GIFs, 36
scenes. Each scene is stamped with its number (1-36, top-left). Themes:
  Yin/Yang · Guangzhou · Canton Tower · Shenzhen · Shanghai · Suzhou · West Lake ·
  Foshan (lion dance) · Dragon Boat · TCM.

Run: `python generate.py` -> ./gifs/slot_00.gif … slot_11.gif. Store with image_index 0-11,
dwell ~10s (so each slot's 3 scenes show before the carousel advances).
"""
import io
import math
import os
import random

from PIL import Image, ImageDraw

W = H = 32
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gifs")
os.makedirs(OUT, exist_ok=True)
N = 16          # frames per scene

GOLD = (255, 205, 70); RED = (210, 30, 30); JADE = (30, 200, 130)
WHITE = (250, 245, 235); BLACK = (20, 18, 24); NEON = (60, 220, 255)


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def vgrad(top, bot):
    img = Image.new("RGB", (W, H)); px = img.load()
    for y in range(H):
        c = lerp(top, bot, y / (H - 1))
        for x in range(W):
            px[x, y] = c
    return img


def water(d, fr, y0, base, hi):
    for y in range(y0, H, 2):
        off = int(round(1.5 * math.sin((y * 0.7 + fr) * 0.5)))
        d.line([(0, y + off), (W, y + off)], fill=hi if (y // 2) % 2 else base)


def stars(d, fr, n=8):
    pts = [(3, 3), (9, 2), (15, 4), (21, 2), (27, 5), (6, 7), (24, 8), (18, 6)]
    for i, (x, y) in enumerate(pts[:n]):
        if (fr + i) % 5 < 3:
            d.point((x, y), fill=WHITE)


_DIGITS = {
    "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"], "9": ["111", "101", "111", "001", "111"],
}


def stamp(img, n):
    d = ImageDraw.Draw(img); s = str(n)
    d.rectangle([0, 0, len(s) * 4, 6], fill=(235, 235, 235))
    for i, ch in enumerate(s):
        for ry, row in enumerate(_DIGITS[ch]):
            for cx, bit in enumerate(row):
                if bit == "1":
                    d.point((1 + i * 4 + cx, 1 + ry), fill=BLACK)
    return img


def enrich(img, fr, seed):
    d = ImageDraw.Draw(img); rng = random.Random(seed * 991 + fr)
    for _ in range(24):
        x = rng.randrange(W); y = (rng.randrange(H) + fr) % H
        cur = img.getpixel((x, y))
        d.point((x, y), fill=tuple(min(255, cur[i] + rng.randrange(18, 60)) for i in range(3)))
    return img


# ---- themes (each returns N frames for a variant) -----------------------------

def yinyang(v, fr):
    img = vgrad(lerp((40, 40, 70), (20, 20, 40), v / 3), (10, 10, 25)); d = ImageDraw.Draw(img)
    cx, cy, r = 16, 18, 9
    ang = fr * 0.4
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE)
    d.pieslice([cx - r, cy - r, cx + r, cy + r], int(math.degrees(ang)), int(math.degrees(ang)) + 180, fill=BLACK)
    # the two dots/teardrops, rotating
    dx, dy = math.cos(ang) * (r / 2), math.sin(ang) * (r / 2)
    d.ellipse([cx + dx - 3, cy + dy - 3, cx + dx + 3, cy + dy + 3], fill=BLACK)
    d.ellipse([cx - dx - 3, cy - dy - 3, cx - dx + 3, cy - dy + 3], fill=WHITE)
    d.point((cx + dx, cy + dy), fill=WHITE); d.point((cx - dx, cy - dy), fill=BLACK)
    return img


def guangzhou(v, fr):
    img = vgrad((255, 150, 90), (120, 60, 110)); d = ImageDraw.Draw(img)
    d.ellipse([23, 4, 28, 9], fill=(255, 235, 150))                  # sun
    for bx, bh in [(2, 10), (6, 14), (10, 8), (20, 12), (26, 16)]:   # skyline
        d.rectangle([bx, 22 - bh, bx + 3, 22], fill=(70, 50, 90))
    d.line([(15, 22), (15, 6)], fill=(180, 120, 160))               # Canton tower hint
    d.ellipse([13, 9, 17, 13], fill=GOLD)
    water(d, fr, 22, (60, 60, 130), (90, 90, 170))
    d.polygon([(4 + fr % 24, 27), (8 + fr % 24, 27), (6 + fr % 24, 25)], fill=RED)  # river boat
    return img


def canton_tower(v, fr):
    img = vgrad((20, 15, 50), (60, 20, 70)); d = ImageDraw.Draw(img); stars(d, fr)
    cx = 16
    for y in range(2, 30):                                          # twisty hyperboloid
        wgt = abs(y - 16) / 14
        w = 1 + wgt * 4
        hue = lerp((NEON), (255, 80, 200), (math.sin(y * 0.4 + fr * 0.5) + 1) / 2)
        d.line([(cx - w, y), (cx + w, y)], fill=hue)
    d.point((cx, 1), fill=GOLD)
    if v >= 2:
        for k in range(6):
            a = k / 6 * math.tau + fr
            d.point((cx + math.cos(a) * (5 + fr % 5), 6 + math.sin(a) * (5 + fr % 5)), fill=GOLD)
    return img


def shenzhen(v, fr):
    img = vgrad((10, 20, 45), (5, 10, 30)); d = ImageDraw.Draw(img); stars(d, fr)
    for bx, bh, col in [(2, 12, (40, 120, 200)), (7, 20, (60, 220, 255)), (13, 26, (120, 240, 255)),
                        (19, 16, (40, 160, 220)), (24, 22, (80, 200, 255)), (29, 14, (40, 120, 200))]:
        d.rectangle([bx, 30 - bh, bx + 2, 30], fill=lerp(col, WHITE, 0.1))
        for wy in range(30 - bh + 1, 30, 2):                        # lit windows
            if (wy + bx + fr) % 3 == 0:
                d.point((bx + 1, wy), fill=GOLD)
    d.line([(13, 4), (15, 4)], fill=NEON)                           # Ping An spire
    return img


def shanghai(v, fr):
    img = vgrad((30, 25, 70), (90, 40, 90)); d = ImageDraw.Draw(img); stars(d, fr)
    # Oriental Pearl: column + two spheres
    d.line([(8, 4), (8, 28)], fill=(180, 120, 160))
    d.ellipse([5, 8, 11, 14], fill=lerp((255, 80, 160), GOLD, (math.sin(fr * 0.4) + 1) / 2))
    d.ellipse([6, 18, 10, 22], fill=(255, 120, 180))
    for bx, bh in [(15, 16), (19, 24), (23, 18), (27, 26)]:         # Pudong towers
        d.rectangle([bx, 28 - bh, bx + 2, 28], fill=(90, 70, 120))
        d.point((bx + 1, 28 - bh), fill=GOLD)
    water(d, fr, 28, (40, 30, 80), (70, 50, 110))
    return img


def suzhou(v, fr):
    img = vgrad((180, 210, 230), (200, 220, 235)); d = ImageDraw.Draw(img)
    d.rectangle([0, 12, 31, 24], fill=WHITE)                        # white wall
    d.rectangle([0, 10, 31, 12], fill=(60, 60, 70))                # black-tile roof
    d.ellipse([6, 13, 16, 23], fill=(150, 200, 225))              # moon gate
    d.ellipse([8, 15, 14, 21], fill=WHITE)
    for k in range(6):                                            # willow fronds
        d.line([(26, 8), (24 + math.sin(fr * 0.3 + k) * 2, 12 + k)], fill=(60, 160, 90))
    water(d, fr, 24, (120, 170, 200), (150, 200, 220))
    d.polygon([(10 + fr % 20, 28), (14 + fr % 20, 28), (12 + fr % 20, 26)], fill=(120, 80, 60))
    return img


def westlake(v, fr):
    img = vgrad((150, 200, 220), (90, 150, 180)); d = ImageDraw.Draw(img)
    # Leifeng Pagoda (tiered)
    px = 23
    for t in range(5):
        ww = 5 - t
        d.rectangle([px - ww, 6 + t * 3, px + ww, 9 + t * 3], fill=(170, 90, 60))
        d.line([(px - ww - 1, 6 + t * 3), (px + ww + 1, 6 + t * 3)], fill=(80, 50, 40))
    d.polygon([(px, 3), (px - 3, 6), (px + 3, 6)], fill=GOLD)
    for k in range(5):                                            # willows
        d.line([(4, 7), (3 + math.sin(fr * 0.3 + k) * 2, 11 + k)], fill=(50, 150, 80))
    water(d, fr, 22, (90, 150, 190), (120, 180, 210))
    d.line([(0, 24), (12, 23)], fill=(120, 100, 90))               # broken bridge
    d.polygon([(6 + fr % 18, 28), (11 + fr % 18, 28), (8 + fr % 18, 26)], fill=WHITE)  # boat
    return img


def foshan(v, fr):
    img = vgrad((90, 150, 220), (210, 80, 70)); d = ImageDraw.Draw(img)
    for lx in (4, 28):                                            # lanterns
        d.ellipse([lx - 3, 4, lx + 3, 10], fill=RED); d.line([(lx - 3, 7), (lx + 3, 7)], fill=GOLD)
    cx, cy = 16, 17
    for k in range(14):                                          # lion mane
        a = k / 14 * math.tau + fr * 0.15; r = 9.5
        tc = [(255, 120, 20), GOLD, RED, WHITE, JADE][k % 5]
        d.ellipse([cx + math.cos(a) * r - 1.5, cy + math.sin(a) * r - 1.5,
                   cx + math.cos(a) * r + 1.5, cy + math.sin(a) * r + 1.5], fill=tc)
    d.ellipse([cx - 8, cy - 7, cx + 8, cy + 7], fill=RED)
    d.polygon([(cx, cy - 9), (cx - 2, cy - 12), (cx + 2, cy - 12)], fill=GOLD)
    for ex in (-4, 4):
        d.ellipse([cx + ex - 2, cy - 3, cx + ex + 2, cy + 1], fill=WHITE)
        d.ellipse([cx + ex - 1, cy - 2, cx + ex + 1, cy], fill=BLACK)
    mo = int(2 + (math.sin(fr * 0.8) + 1) * 2)
    d.rectangle([cx - 6, cy + 3, cx + 6, cy + 3 + mo], fill=(50, 20, 25))
    d.rectangle([cx - 6, cy + 3, cx + 6, cy + 4], fill=JADE)
    return img


def dragonboat(v, fr):
    img = vgrad((120, 190, 230), (40, 110, 170)); d = ImageDraw.Draw(img)
    water(d, fr, 18, (40, 110, 180), (70, 140, 210))
    bx = 4
    d.line([(bx, 22), (bx + 22, 22)], fill=(120, 70, 50))         # hull
    d.polygon([(bx + 22, 22), (bx + 27, 19), (bx + 25, 23)], fill=GOLD)  # dragon head prow
    d.point((bx + 25, 20), fill=RED)
    for k in range(5):                                           # paddlers
        py = int(math.sin(fr * 0.9 + k) * 1.5)
        d.rectangle([bx + 3 + k * 4, 18 + py, bx + 4 + k * 4, 21 + py], fill=RED)
        d.line([(bx + 3 + k * 4, 20 + py), (bx + 1 + k * 4, 23)], fill=(230, 200, 150))  # oar
    d.ellipse([bx + 1, 16, bx + 3, 18], fill=GOLD)               # drum
    return img


def tcm(v, fr):
    img = vgrad((230, 215, 180), (180, 150, 110)); d = ImageDraw.Draw(img)
    # mortar & pestle
    d.polygon([(10, 26), (20, 26), (18, 20), (12, 20)], fill=(120, 80, 55))
    d.line([(15, 20), (15 + int(math.sin(fr * 0.8) * 2), 10)], fill=(150, 110, 80))  # pestle
    # herbs / ginseng
    d.line([(24, 24), (24, 16)], fill=(110, 160, 70))
    for k in range(4):
        d.line([(24, 18 + k), (26 + k, 16 + k)], fill=(90, 150, 60))
    d.ellipse([22, 24, 26, 28], fill=(220, 200, 150))           # root
    # small bagua / yin-yang token top-left-ish
    d.ellipse([4, 4, 10, 10], fill=WHITE); d.pieslice([4, 4, 10, 10], 90, 270, fill=BLACK)
    d.ellipse([6, 4, 8, 6], fill=BLACK); d.ellipse([6, 8, 8, 10], fill=WHITE)
    return img


# scene order (36) -> theme + variant; numbered 1..36
SCENES = (
    [(yinyang, v) for v in range(4)] +        # 1-4
    [(guangzhou, v) for v in range(3)] +      # 5-7
    [(canton_tower, v) for v in range(4)] +   # 8-11
    [(shenzhen, v) for v in range(3)] +       # 12-14
    [(shanghai, v) for v in range(4)] +       # 15-18
    [(suzhou, v) for v in range(4)] +         # 19-22
    [(westlake, v) for v in range(4)] +       # 23-26
    [(foshan, v) for v in range(3)] +         # 27-29
    [(dragonboat, v) for v in range(4)] +     # 30-33
    [(tcm, v) for v in range(3)]              # 34-36
)
assert len(SCENES) == 36, len(SCENES)


def save_gif(frames, name, ms=80):
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=ms, loop=0, disposal=2)
    open(os.path.join(OUT, name), "wb").write(buf.getvalue())
    return len(buf.getvalue())


def main():
    scene_frames = []
    for i, (func, v) in enumerate(SCENES):
        frames = [stamp(enrich(func(v, f), f, i), i + 1) for f in range(N)]    # number 1..36
        scene_frames.append(frames)
    total = 0
    for slot in range(12):                                  # pack 3 scenes per slot
        combined = scene_frames[slot * 3] + scene_frames[slot * 3 + 1] + scene_frames[slot * 3 + 2]
        n = save_gif(combined, f"slot_{slot:02d}.gif")
        total += n
        print(f"  slot {slot:02d}  scenes {slot*3+1}-{slot*3+3}  {len(combined)}f  {n:6d} B")
    print(f"\n36 scenes in 12 slots, total {total} bytes ({total/1024:.0f} KB)")


if __name__ == "__main__":
    main()
