#!/usr/bin/env python3
"""Cross-panel animation: one object sweeps across BOTH panels (Tyler's 'guitar between them').

Treats the two side-by-side panels as ONE wide canvas (width = left_size + right_size), animates a
sprite sweeping across the whole thing, then slices each frame into a LEFT gif and a RIGHT gif that
loop in lockstep. Push them together with dual_push.py so the sprite appears to glide off one panel
and onto the other.

    python3 cross_panel_sweep.py 32 32 left.gif right.gif      # two 32x32 panels
    python3 ../dual_push.py <LEFT_MAC> left.gif <RIGHT_MAC> right.gif

The default sprite is a little flat-colour electric guitar. Swap draw_guitar() for any shape — the
sweep math stays the same. (For panels of DIFFERENT sizes, the shorter panel is centred vertically
within the taller one's height; the horizontal glide still lines up.)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image, ImageDraw            # noqa: E402
from assetlib import save_gif               # noqa: E402


def draw_guitar(d, cx, cy, s, tilt):
    body = (200, 40, 30); neck = (60, 35, 20); head = (230, 220, 200)
    r = s * 0.5
    d.ellipse([cx - r, cy - r * 0.8 + tilt, cx + r, cy + r * 0.8 + tilt], fill=body)   # body
    d.ellipse([cx - r * 0.35, cy - r * 0.3 + tilt, cx + r * 0.35, cy + r * 0.3 + tilt], fill=(20, 20, 20))  # hole
    d.line([cx, cy + tilt, cx + s * 1.1, cy - s * 0.9 + tilt], fill=neck, width=max(2, int(s * 0.18)))       # neck
    d.ellipse([cx + s * 1.0, cy - s * 1.05 + tilt, cx + s * 1.25, cy - s * 0.8 + tilt], fill=head)           # headstock


def sweep(lsize, rsize, lout, rout, n=64):
    H = max(lsize, rsize)
    W = lsize + rsize
    s = H * 0.42
    lframes, rframes = [], []
    for f in range(n):
        p = f / n
        x = -s + (W + 2 * s) * p                      # glide fully across, off both edges
        tilt = (1 if (f // 8) % 2 else -1) * H * 0.05  # gentle bob
        wide = Image.new("RGB", (W, H), (8, 10, 24))
        d = ImageDraw.Draw(wide)
        for i in range(0, W, max(6, H // 4)):          # flat "stage light" dots, not a gradient
            d.rectangle([i, H - 2, i + 2, H - 1], fill=(30, 30, 60))
        draw_guitar(d, x, H * 0.5, s, tilt)
        # slice into the two panels (centre each vertically in its own height)
        left = wide.crop((0, (H - lsize) // 2, lsize, (H - lsize) // 2 + lsize))
        right = wide.crop((lsize, (H - rsize) // 2, lsize + rsize, (H - rsize) // 2 + rsize))
        lframes.append(left)
        rframes.append(right)
    save_gif(lframes, lout, ms=60)
    save_gif(rframes, rout, ms=60)


if __name__ == "__main__":
    a = sys.argv[1:]
    lsize = int(a[0]) if len(a) > 0 else 32
    rsize = int(a[1]) if len(a) > 1 else 32
    lout = a[2] if len(a) > 2 else "left.gif"
    rout = a[3] if len(a) > 3 else "right.gif"
    sweep(lsize, rsize, lout, rout)
