#!/usr/bin/env python3
"""A ball bouncing around the panel — the simplest 'sprite moves' example. Panel-safe.

    python3 bouncing_ball.py 32 out.gif
    IDM_ADDR=<mac> python3 ../idm_push.py --now out.gif

Read this to see the shape of a motion generator: pick a size, loop over frames, draw a flat
background + a flat-coloured sprite at a moving position, save. Swap the disc for any shape.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from assetlib import Canvas, save_gif       # noqa: E402


def bounce(size, out, n=48):
    r = max(2, size // 8)
    x = y = r + 1
    vx, vy = max(1, size // 24) or 1, max(1, size // 32) or 1
    frames = []
    for _ in range(n):
        x += vx
        y += vy
        if x <= r or x >= size - r:
            vx = -vx
        if y <= r or y >= size - r:
            vy = -vy
        c = Canvas(size, bg=(6, 6, 16))
        c.disc(size / 2, size - r, r * 1.3, (2, 2, 8))     # faint shadow line
        c.disc(x, y, r, (255, 90, 0))                       # the ball
        c.disc(x - r * 0.3, y - r * 0.3, max(1, r * 0.35), (255, 200, 120))  # flat highlight
        frames.append(c.img)
    save_gif(frames, out, ms=55)


if __name__ == "__main__":
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 32
    out = sys.argv[2] if len(sys.argv) > 2 else "ball.gif"
    bounce(size, out)
