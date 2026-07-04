#!/usr/bin/env python3
"""Send iDotMatrix *control* commands (the non-image catalog) to a panel over fa02.

These are the fixed-function features (brightness, colour, clock, scoreboard, timers, DIY
pixels) — distinct from GIF/image display, which lives in idm_push.py. Command bytes were
reverse-engineered from the iDotMatrix Android app v2.1.2 and VERIFIED on Tyler's 64x64 by
live BLE capture (scoreboard, DIY pixels, colour, brightness are byte-confirmed).

Channel note: all control goes to characteristic fa02. The panel's ae01/ae02 channel is the
OTA firmware updater — NEVER write to it. The 64 needs write-with-response (set automatically
from panels.local.json "write_response": true).

Usage (panel name from panels.local.json, e.g. big):
  panel_cmd.py --panel big color R G B          # fullscreen solid colour        (07 00 02 02)
  panel_cmd.py --panel big brightness 0-100     # backlight                       (04 80)
  panel_cmd.py --panel big scoreboard A B        # two int16 scores               (0A 80)
  panel_cmd.py --panel big countdown MIN SEC     # start a countdown              (08 80, mode 1)
  panel_cmd.py --panel big countdown stop
  panel_cmd.py --panel big stopwatch start|pause|reset
  panel_cmd.py --panel big clock STYLE [--24h] [--date] [R G B]   # face 0-7      (06 01)
  panel_cmd.py --panel big flip on|off           # rotate 180                     (06 80)
  panel_cmd.py --panel big screen on|off         # panel on/off                   (07 01)
  panel_cmd.py --panel big pixel COL ROW R G B   # draw one DIY pixel (enters DIY)(05 01)
  panel_cmd.py --panel big time                  # sync device clock to now       (01 80)

For scrolling words / pictures / animations use idm_push.py (image transport) — text is just a
rendered GIF; there is no separate "text" command on the wire.
"""
import asyncio
import datetime
import json
import os
import sys

from bleak import BleakClient

FA = "0000fa02-0000-1000-8000-00805f9b34fb"
HERE = os.path.dirname(os.path.abspath(__file__))


def frame(cmd, sub, *payload):
    body = bytes(b & 0xFF for b in payload)
    total = 4 + len(body)
    return bytes((total & 0xFF, (total >> 8) & 0xFF, cmd & 0xFF, sub & 0xFF)) + body


def le16(v):
    return (v & 0xFF, (v >> 8) & 0xFF)


def build(args):
    c = args[0]
    if c == "color":
        r, g, b = (int(x) for x in args[1:4]); return [frame(2, 2, r, g, b)]
    if c == "brightness":
        return [frame(4, 0x80, int(args[1]))]
    if c == "scoreboard":
        a, b = int(args[1]), int(args[2]); return [frame(10, 0x80, *le16(a), *le16(b))]
    if c == "countdown":
        if args[1] == "stop":
            return [frame(8, 0x80, 0, 0, 0)]
        return [frame(8, 0x80, 1, int(args[1]), int(args[2]))]     # mode 1 = start
    if c == "stopwatch":
        mode = {"reset": 0, "start": 1, "pause": 2, "continue": 3}[args[1]]
        return [frame(9, 0x80, mode)]
    if c == "clock":
        style = int(args[1]); flags = style
        rest = args[2:]
        if "--24h" in rest: flags |= 0x40; rest = [a for a in rest if a != "--24h"]
        if "--date" in rest: flags |= 0x80; rest = [a for a in rest if a != "--date"]
        r, g, b = (int(x) for x in (rest + ["255", "255", "255"])[:3])
        return [frame(6, 1, flags, r, g, b)]
    if c == "flip":
        return [frame(6, 0x80, 1 if args[1] == "on" else 0)]
    if c == "screen":
        return [frame(7, 1, 1 if args[1] == "on" else 0)]
    if c == "pixel":
        col, row, r, g, b = (int(x) for x in args[1:6])
        return [frame(4, 1, 1),                          # enter DIY (+clear)
                bytes((0x0A, 0x00, 0x05, 0x01, 0x00, r & 0xFF, g & 0xFF, b & 0xFF, col & 0xFF, row & 0xFF))]
    if c == "time":
        n = datetime.datetime.now()
        return [frame(1, 0x80, n.year - 2000, n.month, n.day, n.isoweekday(), n.hour, n.minute, n.second)]
    sys.exit(f"unknown command: {c}\n{__doc__}")


def resolve(panel):
    cfg = json.load(open(os.path.join(HERE, "panels.local.json")))["panels"]
    if panel not in cfg:
        sys.exit(f"panel '{panel}' not in panels.local.json (have: {', '.join(cfg)})")
    p = cfg[panel]
    return p["mac"], bool(p.get("write_response"))


async def main():
    args = sys.argv[1:]
    panel = "big"
    if "--panel" in args:
        i = args.index("--panel"); panel = args[i + 1]; del args[i:i + 2]
    if not args:
        sys.exit(__doc__)
    mac, resp = resolve(panel)
    pkts = build(args)
    print(f"connecting {mac} ({'write-with-response' if resp else 'write-no-response'})", flush=True)
    async with BleakClient(mac, timeout=25) as c:
        for p in pkts:
            await c.write_gatt_char(FA, p, response=resp)
            print(f"  sent {p.hex()}", flush=True)
            await asyncio.sleep(0.2)
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
