#!/usr/bin/env python3
"""The Awakening Lion of Foshan — a 36-scene 32x32 pixel-art legend for the iDotMatrix
on-device carousel (one animated GIF per slot; slot order == story order).

A Foshan (佛山) tale: a kung fu student's path from dawn training to the lion-dance
climax of 采青 (cai qing, "plucking the greens").

  0-5   Dawn training  — Wing Chun forms in a courtyard at sunrise.
  6-11  The wooden dummy (木人桩) — striking the mook jong, building skill.
  12-17 The lion awakens (醒狮) — the festival; the lion head blinks open & stirs.
  18-23 The lion dance — weaving through a lantern-lit street to the drums.
  24-29 The plum-blossom poles (梅花桩) — leaping pole to pole toward the green up high.
  30-35 Cai qing & celebration — pluck the greens, fireworks, red packets fall.

Run: `python generate.py` -> writes ./gifs/slot_NN_*.gif. Upload with the carousel
store (DataType.GIF, image_index=slot, time_sign=dwell) — see docs/PROTOCOL.md.
"""
import io
import math
import os
import random

from PIL import Image, ImageDraw

W = H = 32
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gifs")
os.makedirs(OUT, exist_ok=True)

# palette
RED = (210, 30, 30)
GOLD = (255, 205, 70)
BLACK = (25, 20, 25)
WHITE = (250, 245, 235)
JADE = (30, 200, 130)
WOOD = (150, 95, 45)
SKIN = (240, 195, 150)
GI = (40, 55, 90)


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def vgrad(top, bot):
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        c = lerp(top, bot, y / (H - 1))
        for x in range(W):
            px[x, y] = c
    return img


def lantern(d, x, y):
    d.line([(x, y - 4), (x, y - 2)], fill=GOLD)
    d.ellipse([x - 3, y - 2, x + 3, y + 4], fill=RED)
    d.line([(x - 3, y + 1), (x + 3, y + 1)], fill=GOLD)
    d.line([(x, y + 4), (x, y + 6)], fill=GOLD)


def fighter(d, cx, cy, pose, fr):
    """Tiny kung-fu figure. pose: 'horse','punch','block','kick','guard','salute'."""
    sw = math.sin(fr * 0.9)
    d.ellipse([cx - 2, cy - 8, cx + 2, cy - 4], fill=SKIN)            # head
    d.rectangle([cx - 2, cy - 4, cx + 2, cy + 2], fill=GI)            # torso
    if pose == "horse":
        d.line([(cx - 1, cy + 2), (cx - 4, cy + 7)], fill=GI)
        d.line([(cx + 1, cy + 2), (cx + 4, cy + 7)], fill=GI)
        d.line([(cx - 2, cy - 2), (cx - 5, cy)], fill=SKIN)
        d.line([(cx + 2, cy - 2), (cx + 5, cy)], fill=SKIN)
    elif pose == "punch":
        ext = 4 + int(2 + 2 * sw)
        d.line([(cx + 2, cy - 2), (cx + ext, cy - 2)], fill=SKIN)     # punch
        d.line([(cx - 2, cy - 2), (cx - 4, cy - 1)], fill=SKIN)
        d.line([(cx - 1, cy + 2), (cx - 3, cy + 7)], fill=GI)
        d.line([(cx + 1, cy + 2), (cx + 3, cy + 7)], fill=GI)
    elif pose == "block":
        d.line([(cx - 2, cy - 3), (cx - 5, cy - 5)], fill=SKIN)
        d.line([(cx + 2, cy - 2), (cx + 4, cy - 4)], fill=SKIN)
        d.line([(cx - 1, cy + 2), (cx - 3, cy + 7)], fill=GI)
        d.line([(cx + 1, cy + 2), (cx + 3, cy + 7)], fill=GI)
    elif pose == "kick":
        ky = cy + int(sw * 3)
        d.line([(cx + 1, cy + 1), (cx + 6, ky - 2)], fill=GI)         # high kick
        d.line([(cx - 1, cy + 2), (cx - 3, cy + 7)], fill=GI)
        d.line([(cx - 2, cy - 2), (cx - 5, cy - 1)], fill=SKIN)
        d.line([(cx + 2, cy - 2), (cx + 4, cy - 3)], fill=SKIN)
    elif pose == "guard":                                            # Wing Chun centerline
        d.line([(cx + 2, cy - 3), (cx + 5, cy - 2)], fill=SKIN)
        d.line([(cx - 2, cy - 2), (cx + 1, cy - 1)], fill=SKIN)
        d.line([(cx - 1, cy + 2), (cx - 3, cy + 7)], fill=GI)
        d.line([(cx + 1, cy + 2), (cx + 3, cy + 7)], fill=GI)
    else:  # salute
        d.line([(cx - 2, cy - 2), (cx - 4, cy - 4)], fill=SKIN)
        d.line([(cx + 2, cy - 2), (cx + 4, cy - 4)], fill=SKIN)
        d.line([(cx - 1, cy + 2), (cx - 2, cy + 7)], fill=GI)
        d.line([(cx + 1, cy + 2), (cx + 2, cy + 7)], fill=GI)


def mook_jong(d, cx, cy):
    """Wooden dummy: trunk + 3 arms + leg."""
    d.rectangle([cx - 2, cy - 9, cx + 2, cy + 9], fill=WOOD)
    d.line([(cx - 2, cy - 6), (cx - 7, cy - 8)], fill=lerp(WOOD, BLACK, 0.2))
    d.line([(cx + 2, cy - 6), (cx + 7, cy - 8)], fill=lerp(WOOD, BLACK, 0.2))
    d.line([(cx + 2, cy - 2), (cx + 7, cy - 2)], fill=lerp(WOOD, BLACK, 0.2))
    d.line([(cx, cy + 9), (cx - 5, cy + 13)], fill=WOOD)


def lion(d, cx, cy, fr, blink=False, mouth=0.4, mane=True, body_col=RED):
    """Southern lion (醒狮) head — colourful, expressive."""
    if mane:
        for k in range(14):
            a = k / 14 * math.tau + fr * 0.15
            r = 9.5 + math.sin(fr * 0.5 + k) * 0.8
            tc = [(255, 120, 20), GOLD, RED, WHITE, JADE][k % 5]
            mx, my = cx + math.cos(a) * r, cy + math.sin(a) * r
            d.ellipse([mx - 1.6, my - 1.6, mx + 1.6, my + 1.6], fill=tc)
    d.ellipse([cx - 8, cy - 7, cx + 8, cy + 7], fill=body_col)        # head
    d.arc([cx - 8, cy - 9, cx + 8, cy + 3], 180, 360, fill=GOLD)      # brow ridge
    d.polygon([(cx, cy - 9), (cx - 2, cy - 12), (cx + 2, cy - 12)], fill=GOLD)  # horn
    d.ellipse([cx - 2, cy - 6, cx + 2, cy - 2], fill=(120, 220, 255))  # forehead mirror
    for ex in (-4, 4):                                               # eyes
        if blink:
            d.line([(cx + ex - 2, cy - 1), (cx + ex + 2, cy - 1)], fill=BLACK)
        else:
            d.ellipse([cx + ex - 2, cy - 3, cx + ex + 2, cy + 1], fill=WHITE)
            d.ellipse([cx + ex - 1, cy - 2, cx + ex + 1, cy], fill=BLACK)
    mh = int(1 + mouth * 5)                                          # mouth opens
    d.rectangle([cx - 6, cy + 3, cx + 6, cy + 3 + mh], fill=(50, 20, 25))
    d.rectangle([cx - 6, cy + 3, cx + 6, cy + 4], fill=JADE)         # green lip
    for tx in range(-4, 5, 2):
        d.point((cx + tx, cy + 4), fill=WHITE)


def drum(d, x, y):
    d.ellipse([x - 4, y - 3, x + 4, y + 3], fill=RED)
    d.line([(x - 4, y), (x + 4, y)], fill=GOLD)
    for k in range(5):
        d.point((x - 3 + k * 1.5, y - 2), fill=GOLD)


def firework(d, cx, cy, fr, col):
    r = 2 + (fr % 8) * 1.7
    for k in range(10):
        a = k / 10 * math.tau
        d.point((cx + math.cos(a) * r, cy + math.sin(a) * r), fill=col)
        d.point((cx + math.cos(a) * r * 0.6, cy + math.sin(a) * r * 0.6), fill=lerp(col, WHITE, 0.5))


def enrich(img, fr, seed):
    """Drifting embers/confetti — thematic + inflates entropy so each scene is a fuller GIF."""
    d = ImageDraw.Draw(img)
    rng = random.Random(seed * 1000 + fr)
    for _ in range(26):
        x = rng.randrange(W)
        y = (rng.randrange(H) + fr) % H
        cur = img.getpixel((x, y))
        d.point((x, y), fill=tuple(min(255, cur[i] + rng.randrange(20, 70)) for i in range(3)))
    return img


_DIGITS = {
    "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"], "9": ["111", "101", "111", "001", "111"],
}


def stamp(img, n):
    """Black scene number on a small pale pad, top-left (for debugging where the carousel stops)."""
    d = ImageDraw.Draw(img)
    s = str(n)
    d.rectangle([0, 0, len(s) * 4, 6], fill=(235, 235, 235))
    for i, ch in enumerate(s):
        for ry, row in enumerate(_DIGITS[ch]):
            for cx, bit in enumerate(row):
                if bit == "1":
                    d.point((1 + i * 4 + cx, 1 + ry), fill=(0, 0, 0))
    return img


def save_gif(frames, name, ms=70):
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:],
                   duration=ms, loop=0, disposal=2)
    open(os.path.join(OUT, name), "wb").write(buf.getvalue())
    return len(buf.getvalue())


# ---- the six acts -------------------------------------------------------------
POSES = ["horse", "punch", "block", "kick", "guard", "salute"]


def act_train(s, N):
    sky = lerp((255, 170, 90), (150, 205, 245), s / 5)              # sunrise -> morning
    out = []
    for f in range(N):
        img = vgrad(sky, (180, 150, 120))
        d = ImageDraw.Draw(img)
        d.ellipse([24 - s, 3, 29 - s, 8], fill=(255, 235, 130))     # sun
        d.rectangle([0, 26, 31, 31], fill=(120, 80, 55))            # courtyard floor
        d.rectangle([0, 24, 31, 26], fill=(90, 60, 40))
        lantern(d, 5, 8)
        lantern(d, 27, 8)
        fighter(d, 16, 22, POSES[s], f)
        out.append(img)
    return out


def act_dummy(s, N):
    out = []
    for f in range(N):
        img = vgrad((150, 205, 245), (170, 140, 110))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 26, 31, 31], fill=(120, 80, 55))
        lantern(d, 27, 7)
        mook_jong(d, 21, 18)
        strike = math.sin(f * (1.0 + s * 0.25))
        pose = "punch" if strike > 0 else "block"
        fighter(d, 11 + int(strike * 1.5), 22, pose, f)
        if strike > 0.7:                                            # impact spark
            d.point((17, 16), fill=GOLD)
            d.point((18, 17), fill=WHITE)
        out.append(img)
    return out


def act_awaken(s, N):
    out = []
    for f in range(N):
        img = vgrad((120, 190, 240), (200, 120, 90))
        d = ImageDraw.Draw(img)
        lantern(d, 4, 7)
        lantern(d, 28, 7)
        drum(d, 27, 26)
        rise = (s / 5)
        blink = (s == 1 and f % 6 < 3) or (s == 0)
        mouth = 0.0 if s < 3 else (0.2 + 0.4 * (s - 3) / 2 + 0.2 * math.sin(f * 0.8))
        lion(d, 16, 18 - int(rise * 3), f, blink=blink, mouth=mouth)
        out.append(img)
    return out


def act_dance(s, N):
    out = []
    for f in range(N):
        img = vgrad((90, 150, 220), (210, 80, 70))
        d = ImageDraw.Draw(img)
        for lx in (3, 12, 20, 29):
            lantern(d, lx, 6)
        d.rectangle([0, 27, 31, 31], fill=(110, 70, 50))
        sway = math.sin(f * 0.7 + s) * 6
        cx = 16 + int(sway)
        bob = int(math.sin(f * 1.2) * 2)
        # trailing body cloth
        for k in range(5):
            bx = cx - int(sway * (k + 1) * 0.2) - 6 - k * 3
            d.ellipse([bx - 2, 22 + bob - k, bx + 2, 26 + bob - k],
                      fill=[RED, GOLD, JADE, RED, GOLD][k])
        mouth = 0.4 + 0.4 * abs(math.sin(f * 0.9))
        lion(d, cx, 16 + bob, f, mouth=mouth)
        out.append(img)
    return out


def act_poles(s, N):
    out = []
    for f in range(N):
        img = vgrad((70, 120, 200), (40, 70, 140))
        d = ImageDraw.Draw(img)
        # plum-blossom poles at increasing heights
        for i, px in enumerate((6, 14, 22, 28)):
            ph = 31 - (i * 4 + 6)
            d.rectangle([px - 1, ph, px + 1, 31], fill=WOOD)
            d.ellipse([px - 2, ph - 2, px + 2, ph + 2], fill=lerp(WOOD, GOLD, 0.3))
        # the green (lettuce + red packet) hangs top-right
        d.ellipse([25, 2, 30, 6], fill=JADE)
        d.rectangle([26, 5, 29, 8], fill=RED)
        # lion climbs higher each scene
        climb_y = 24 - s * 3
        climb_x = 8 + s * 3 + int(math.sin(f * 0.8) * 1.5)
        lion(d, climb_x, climb_y, f, mouth=0.5, mane=True)
        out.append(img)
    return out


def act_finale(s, N):
    out = []
    for f in range(N):
        night = lerp((40, 60, 130), (10, 8, 35), min(1, s / 3))
        img = vgrad(night, (60, 20, 50))
        d = ImageDraw.Draw(img)
        if s >= 1:
            firework(d, 7, 7, f + s, GOLD)
            firework(d, 25, 5, f + s * 2, JADE)
            if s >= 3:
                firework(d, 16, 9, f, RED)
        # the green, then plucked & "spat"
        if s == 0:
            d.ellipse([24, 3, 29, 7], fill=JADE)
            d.rectangle([25, 6, 28, 9], fill=RED)
        if s >= 2:                                                  # spit greens (cai qing)
            for k in range(6):
                gx = 16 + math.cos(f * 0.5 + k) * (4 + k)
                d.point((gx, 12 + (f + k) % 6), fill=JADE)
        if s >= 2:                                                  # falling red packets 利是
            for k in range(4):
                d.rectangle([4 + k * 7, (f * 2 + k * 5) % 30, 6 + k * 7, (f * 2 + k * 5) % 30 + 3],
                            fill=RED)
        lion(d, 16, 15 + int(math.sin(f) * 1.5), f, mouth=0.7 if s >= 2 else 0.3, body_col=RED)
        out.append(img)
    return out


# The device carousels exactly 12 slots (image_index 0-11); the app's "3 pages" are
# swappable 12-scene sets you push one at a time. So the story is told in 12 beats,
# two per act, chosen for visual contrast across each act's arc.
STORY = [
    (act_train, 0, "train-horse"),    # 0  wide horse stance at sunrise
    (act_train, 3, "train-kick"),     # 1  high kick
    (act_dummy, 1, "dummy-strike"),   # 2  striking the mook jong
    (act_dummy, 4, "dummy-flurry"),   # 3  a fast flurry
    (act_awaken, 0, "lion-asleep"),   # 4  the lion head, eyes closed
    (act_awaken, 5, "lion-awake"),    # 5  awake, mouth open, mane shaking
    (act_dance, 1, "dance-weave"),    # 6  weaving the street
    (act_dance, 4, "dance-leap"),     # 7  a big sway/leap
    (act_poles, 1, "poles-climb"),    # 8  onto the plum-blossom poles
    (act_poles, 5, "poles-reach"),    # 9  reaching for the green up high
    (act_finale, 0, "the-green"),     # 10 the green hangs, lion below
    (act_finale, 4, "cai-qing"),      # 11 pluck + fireworks finale
]


def main():
    total = 0
    for slot, (act, s, name) in enumerate(STORY):
        frames = act(s, 48)
        frames = [enrich(im, fi, slot) for fi, im in enumerate(frames)]   # stamp(…, slot) to debug
        n = save_gif(frames, f"slot_{slot:02d}_{name}.gif")
        total += n
        print(f"  slot {slot:02d}  {name:14s} {len(frames)}f  {n:6d} B")
    print(f"\n{len(STORY)} scenes, total {total} bytes ({total/1024:.0f} KB), avg {total//len(STORY)} B/scene")


if __name__ == "__main__":
    main()
