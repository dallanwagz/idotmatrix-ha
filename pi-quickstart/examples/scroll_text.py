#!/usr/bin/env python3
"""Scrolling message across a panel. Panel-safe (flat colours).

    python3 scroll_text.py "GO BRASIL" 32 out.gif [textR,textG,textB] [bgR,bgG,bgB]

Then:  IDM_ADDR=<mac> python3 ../idm_push.py --now out.gif
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image, ImageDraw            # noqa: E402
from assetlib import font, save_gif         # noqa: E402


def scroll(text, size, out, fg=(255, 220, 0), bg=(0, 30, 90), speed=1):
    fnt = font(int(size * 0.8))
    tmp = Image.new("L", (size * 12, size * 2), 0)
    ImageDraw.Draw(tmp).text((0, 0), text, fill=255, font=fnt)
    b = tmp.getbbox()
    mask = tmp.crop(b) if b else tmp
    if mask.height > size:                                  # fit to panel height
        mask = mask.resize((int(mask.width * size / mask.height), size))
    tw, th = mask.size
    oy = (size - th) // 2
    frames = []
    for x in range(size, -(tw + 1), -speed):               # slide right -> left
        img = Image.new("RGB", (size, size), bg)
        solid = Image.new("RGB", mask.size, fg)
        img.paste(solid, (x, oy), mask.point(lambda v: 255 if v > 110 else 0))
        frames.append(img)
    save_gif(frames, out, ms=60)


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else "HELLO"
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 32
    out = sys.argv[3] if len(sys.argv) > 3 else "scroll.gif"
    fg = tuple(int(v) for v in sys.argv[4].split(",")) if len(sys.argv) > 4 else (255, 220, 0)
    bg = tuple(int(v) for v in sys.argv[5].split(",")) if len(sys.argv) > 5 else (0, 30, 90)
    scroll(text, size, out, fg, bg)
