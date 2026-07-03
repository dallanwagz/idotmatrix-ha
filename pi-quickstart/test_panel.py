#!/usr/bin/env python3
"""Prove control of a panel AND identify its size — self-contained (needs `bleak` + `Pillow`).

Builds an unmistakable test animation (big size number + a cycling RED/GREEN/BLUE border) and
shows it LIVE on the panel at the given MAC. Watch which physical panel lights up and what number
it shows — that tells you which MAC is your 32x32 and which is your 64x64.

    python3 test_panel.py <MAC> 32      # render a 32x32 test and show it
    python3 test_panel.py <MAC> 64      # render a 64x64 test and show it

If a panel lights up, control works. Record the MAC->size mapping in panels.local.json.
"""
import asyncio
import os
import sys

from assetlib import Canvas, save_gif
from idm_push import push

COLORS = [((220, 30, 30), "RED"), ((30, 200, 60), "GREEN"), ((40, 90, 230), "BLUE")]


def build_test(size):
    frames = []
    for i in range(len(COLORS) * 4):
        col, _ = COLORS[(i // 4) % len(COLORS)]
        c = Canvas(size, bg=(0, 0, 0))
        b = max(2, size // 16)
        c.rect(0, 0, size - 1, b, col)                 # border
        c.rect(0, size - 1 - b, size - 1, size - 1, col)
        c.rect(0, 0, b, size - 1, col)
        c.rect(size - 1 - b, 0, size - 1, size - 1, col)
        blink = (i % 4) != 3                            # size number blinks so it reads as "alive"
        c.text(str(size), (255, 255, 255) if blink else col)
        frames.append(c.img)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"_test_{size}.gif")
    save_gif(frames, path, ms=120)
    return path


async def main():
    if len(sys.argv) < 3 or sys.argv[2] not in ("16", "32", "64"):
        sys.exit("usage: python3 test_panel.py <MAC> <16|32|64>")
    mac, size = sys.argv[1], int(sys.argv[2])
    print(f"building {size}x{size} test pattern ...", flush=True)
    path = build_test(size)
    print(f"showing it live on {mac} — watch your panels", flush=True)
    ok = await push(mac, [(open(path, "rb").read(), 0, f"test{size}")], live=True)
    print("\n>>> Did a panel light up showing '%d' with a colour border? If yes, that MAC is your "
          "%dx%d panel." % (size, size, size) if ok else "\nFAILED — no ACK. Check the MAC, range, "
          "and that the phone app isn't connected.", flush=True)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    asyncio.run(main())
