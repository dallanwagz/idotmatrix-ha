#!/usr/bin/env python3
"""Show two GIFs on two panels at once, started together — for cross-panel animations.

Use this when one motion spans BOTH panels sitting side by side (e.g. a guitar, a ball, a comet
that slides off the right edge of the left panel and onto the left edge of the right panel). You
generate two GIFs — the "left half" and "right half" of the same wide scene, looping in lockstep —
and this pushes them live to both panels concurrently so they start as close to together as BLE
allows.

    python3 dual_push.py <LEFT_MAC> left.gif <RIGHT_MAC> right.gif

Panels can be different sizes; just make each GIF match its panel. See examples/cross_panel_sweep.py
for a generator that produces a matched left/right pair. Because it's a loop, any small start skew
washes out after the first cycle.
"""
import asyncio
import sys

from idm_push import push


async def main():
    if len(sys.argv) != 5:
        sys.exit("usage: python3 dual_push.py <LEFT_MAC> left.gif <RIGHT_MAC> right.gif")
    lmac, lgif, rmac, rgif = sys.argv[1:5]
    print(f"showing {lgif} on {lmac}  +  {rgif} on {rmac}  (concurrent live)", flush=True)
    results = await asyncio.gather(
        push(lmac, [(open(lgif, "rb").read(), 0, "left")], live=True),
        push(rmac, [(open(rgif, "rb").read(), 0, "right")], live=True),
        return_exceptions=True,
    )
    ok = all(r is True for r in results)
    print("both shown" if ok else f"problem: {results}", flush=True)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    asyncio.run(main())
