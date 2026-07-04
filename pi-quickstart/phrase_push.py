#!/usr/bin/env python3
"""Send a "Preset Phrase" set (up to 6 GIFs) to a panel — a display set SEPARATE from the
12-slot carousel (idm_push.py). Reverse-engineered from a live BLE capture of the iDotMatrix
app driving the 64: it uploads each GIF to image indices 14..19, then activates the set with
cmd 6/2 (frame: `06 02 <count> <idx...>`). Title + theme color in the app are app-side only
(theme color just colours Text-type slots' rasterized image) — no wire command, so not here.

Unlike the carousel, phrases can be RICH: the app's cloud phrases are full-colour (100+
colours/frame), 60-90 frame, up to ~80 KB animated GIFs — this panel renders them fine.

Usage:  phrase_push.py --panel big scene1.gif scene2.gif ...   (1-6 GIFs)
"""
import asyncio
import os
import sys

from bleak import BleakClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idm_push                                            # noqa: E402
from idm_push import FA_NOTIFY, FA_WRITE, Link, _upload, frame, resolve_addr, run_with_retry  # noqa: E402

PHRASE_BASE = 14          # phrase image indices 14..19 (0x0e..0x13)
PHRASE_MAX = 6


async def push_phrase(addr, gifs):
    link = Link()
    async with BleakClient(addr, timeout=25) as c:
        await c.start_notify(FA_NOTIFY, link.on_notify)
        idxs = []
        for i, (data, name) in enumerate(gifs):
            slot = PHRASE_BASE + i
            ok, info = await _upload(c, link, data, slot, 0)
            print(f"  img -> idx {slot}: {name:22s} {len(data):6d}B -> {ok} ({info})", flush=True)
            if not ok:
                return False
            idxs.append(slot)
            await asyncio.sleep(0.25)
        act = frame(6, 2, len(idxs), *idxs)                # cmd 6/2: count + indices
        await c.write_gatt_char(FA_WRITE, act, response=idm_push.WRITE_RESPONSE)
        print(f"  activate phrase: {act.hex()}", flush=True)
        await asyncio.sleep(1.0)
        return True


def main():
    args = sys.argv[1:]
    panel = None
    if "--panel" in args:
        i = args.index("--panel"); panel = args[i + 1]; del args[i:i + 2]
    if not args:
        sys.exit(__doc__)
    if len(args) > PHRASE_MAX:
        sys.exit(f"phrases hold at most {PHRASE_MAX} GIFs (got {len(args)})")
    addr = resolve_addr(panel)                             # also sets idm_push.WRITE_RESPONSE
    gifs = []
    for a in args:
        if not os.path.exists(a):
            sys.exit(f"file not found: {a}")
        gifs.append((open(a, "rb").read(), os.path.basename(a)))
    print(f"connecting {addr} — phrase set of {len(gifs)} "
          f"({'write-with-response' if idm_push.WRITE_RESPONSE else 'no-response'})", flush=True)
    ok = run_with_retry(lambda: push_phrase(addr, gifs))
    print("done" if ok else "FAILED", flush=True)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
