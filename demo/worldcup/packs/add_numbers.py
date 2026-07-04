#!/usr/bin/env python3
"""Stamp a small carousel-slot number in the top-left corner of each GIF (panel-safe),
so a human watching the panel can refer to each animation by number.

Number is drawn as a crisp 3x5 pixel font on a black box (legible over any background).
Frames are quantized to 14 colours first, then black+white are added for the label
(<=16 total), so the label survives without dithering. Output -> _numbered/NN_<name>.gif
"""
import os
import sys

sys.path.insert(0, "/Users/dallan/repo/tyler/idotmatrix-ha/pi-quickstart")
from assetlib import save_gif                       # noqa: E402
from PIL import Image, ImageSequence                # noqa: E402

DIGITS = {
    "0": ["111", "101", "101", "101", "111"],
    "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"],
    "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"],
    "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"],
    "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"],
    "9": ["111", "101", "111", "001", "111"],
}
FG = (255, 255, 255)
BG = (0, 0, 0)


def stamp(img, n):
    s = str(n)
    w = len(s) * 3 + (len(s) - 1)                    # 3px/digit + 1px gaps
    for x in range(0, w + 2):                        # black backing box (+1px margin)
        for y in range(0, 7):
            img.putpixel((x, y), BG)
    x = 1
    for ch in s:
        for ry, row in enumerate(DIGITS[ch]):
            for rx, bit in enumerate(row):
                if bit == "1":
                    img.putpixel((x + rx, 1 + ry), FG)
        x += 4
    return img


# carousel order == slot numbers the panel plays
CAROUSEL = [
    ("brazil/br_flag_wave.gif", 1), ("usa/us_flag_wave.gif", 2), ("brazil/br_ball_roll.gif", 3),
    ("usa/us_goal.gif", 4), ("brazil/br_goal_freekick.gif", 5), ("brazil/br_gooool.gif", 6),
    ("usa/us_champions.gif", 7), ("brazil/br_trophy_raise.gif", 8), ("usa/us_trophy_raise.gif", 9),
    ("brazil/br_campeoes.gif", 10), ("usa/us_fireworks.gif", 11), ("brazil/br_confetti.gif", 12),
]
BASE = "/Users/dallan/repo/tyler/idotmatrix-ha/demo/worldcup/packs"
OUT = os.path.join(BASE, "_numbered")
os.makedirs(OUT, exist_ok=True)

for rel, n in CAROUSEL:
    im = Image.open(os.path.join(BASE, rel))
    ms = im.info.get("duration", 100)
    frames = []
    for fr in ImageSequence.Iterator(im):
        q = fr.convert("RGB").quantize(colors=14, dither=Image.Dither.NONE).convert("RGB")
        stamp(q, n)
        frames.append(q)
    save_gif(frames, os.path.join(OUT, f"{n:02d}_{os.path.basename(rel)}"), ms=ms)
