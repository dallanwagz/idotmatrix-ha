#!/usr/bin/env python3
"""Push GIFs to an iDotMatrix panel over BLE — self-contained (needs only `bleak`).

Works on a Raspberry Pi (BlueZ addresses panels by MAC, which is what this uses). The upload
protocol is size-agnostic: the panel decodes whatever GIF you send, so the SAME script drives a
32x32 and a 64x64 panel — just send a GIF of the matching size. Reverse-engineered protocol; the
full write-up is in ../docs/PROTOCOL.md.

Three ways to call it:

  # 1) LIVE PREVIEW (instant, not stored) — best while iterating on an asset
  IDM_ADDR=<mac> python3 idm_push.py --now art.gif

  # 2) SET-AND-FORGET one animation (stored in a slot; loops on-device after you disconnect)
  IDM_ADDR=<mac> python3 idm_push.py art.gif:30

  # 3) CAROUSEL of up to 12 GIFs, each with its own dwell in seconds
  IDM_ADDR=<mac> python3 idm_push.py flag.gif:10 ball.gif:8 word.gif:8

You can also name panels in `panels.local.json` (see panels.local.json.example) and use
`--panel big` instead of `IDM_ADDR=...`.
"""
import asyncio
import json
import os
import struct
import sys
import time
import zlib

from bleak import BleakClient
from bleak.exc import BleakError

FA_WRITE = "0000fa02-0000-1000-8000-00805f9b34fb"   # control/upload write
FA_NOTIFY = "0000fa03-0000-1000-8000-00805f9b34fb"  # status/ACK notify
OUTER = 4096          # outer packet payload chunk
SAFE = 244            # inner GATT write cap (panel silently drops larger)
GIF = 1               # DataType.GIF
SHOW_NOW = 12         # image_index 12 = live/transient display (not stored)
# Newer-firmware panels (mfr sig 04050b, e.g. the 64) silently drop some write-without-response
# chunks, failing the whole-GIF CRC and never ACKing. Set IDM_WRITE_RESPONSE=1 to write WITH
# response (each chunk confirmed at the BLE layer) — slower but reliable on those panels.
WRITE_RESPONSE = os.environ.get("IDM_WRITE_RESPONSE") == "1"
WRITE_DELAY = float(os.environ.get("IDM_WRITE_DELAY", "0.02"))
HERE = os.path.dirname(os.path.abspath(__file__))


def frame(cmd, sub, *payload):
    body = bytes(b & 0xFF for b in payload)
    total = 4 + len(body)
    return bytes((total & 0xFF, (total >> 8) & 0xFF, cmd & 0xFF, sub & 0xFF)) + body


def outer_packets(data, image_index, time_sign, dtype=GIF):
    crc = struct.pack("<I", zlib.crc32(data) & 0xFFFFFFFF)
    total = len(data)
    ts = 0 if image_index == SHOW_NOW else time_sign
    chunks = [data[i:i + OUTER] for i in range(0, len(data), OUTER)] or [b""]
    out = []
    for i, ch in enumerate(chunks):
        option = 0 if i == 0 else 2
        length = len(ch) + 16
        hdr = (bytes((length & 0xFF, (length >> 8) & 0xFF, dtype & 0xFF, 0, option))
               + struct.pack("<I", total) + crc
               + bytes((ts & 0xFF, (ts >> 8) & 0xFF, image_index & 0xFF)))
        out.append(hdr + ch)
    return out


class Link:
    def __init__(self):
        self.ev = asyncio.Event()
        self.status = None

    def on_notify(self, _, data):
        if len(data) >= 5:
            self.status = data[4]      # 1=next, 3=done, 2=no-space
            self.ev.set()


async def _upload(client, link, gif, slot, dwell):
    for pkt in outer_packets(gif, slot, dwell):
        for j in range(0, len(pkt), SAFE):
            await client.write_gatt_char(FA_WRITE, pkt[j:j + SAFE], response=WRITE_RESPONSE)
            if not WRITE_RESPONSE:
                await asyncio.sleep(WRITE_DELAY)
        link.ev.clear()
        try:
            await asyncio.wait_for(link.ev.wait(), 8)
        except asyncio.TimeoutError:
            return False, "ack timeout"
        if link.status == 2:
            return False, "NO_SPACE"
    return True, f"ok(status {link.status})"


async def push(addr, items, live=False):
    """items = [(gif_bytes, dwell_seconds, label), ...]. live=True -> transient show-now."""
    link = Link()
    async with BleakClient(addr, timeout=25) as c:
        await c.start_notify(FA_NOTIFY, link.on_notify)
        if live:
            gif, _, name = items[0]
            ok, info = await _upload(c, link, gif, SHOW_NOW, 0)
            print(f"  live: {name} {len(gif)}B -> {ok} ({info})", flush=True)
            return ok
        n = min(len(items), 12)
        await c.write_gatt_char(FA_WRITE, frame(2, 1, 12, *range(12)), response=False)  # wipe 12
        await asyncio.sleep(1.0)
        await c.write_gatt_char(FA_WRITE, frame(2, 1, n, *range(n)), response=False)     # setup n
        await asyncio.sleep(1.0)
        ok_all = True
        for i, (gif, dwell, name) in enumerate(items[:12]):
            ok, info = await _upload(c, link, gif, i, dwell)
            print(f"  slot {i}: {name:16s} {len(gif):6d}B dwell={dwell:>3}s -> {ok} ({info})", flush=True)
            ok_all &= ok
            if not ok:
                break
            await asyncio.sleep(0.25)
        await c.write_gatt_char(FA_WRITE, frame(10, 1), response=False)   # enter asset view -> cycle
        await asyncio.sleep(1.0)
        return ok_all


def run_with_retry(coro_factory, tries=None, delay=None):
    """Run an async push, retrying on transient BLE faults (e.g. the panel's 'Unlikely Error')
    with a fresh connection each attempt. Uses linear backoff (delay*attempt) so the link gets
    progressively more time to settle — one quick burst of retries often isn't enough. Tunable via
    IDM_RETRIES / IDM_RETRY_DELAY."""
    tries = int(os.environ.get("IDM_RETRIES", "5")) if tries is None else tries
    delay = float(os.environ.get("IDM_RETRY_DELAY", "4.0")) if delay is None else delay
    for attempt in range(1, tries + 1):
        try:
            if asyncio.run(coro_factory()):
                return True
            reason = "upload returned FAILED"
        except BleakError as e:
            reason = f"BLE error: {e}"
        if attempt < tries:
            wait = delay * attempt                        # 4, 8, 12, 16 ... s
            print(f"  attempt {attempt}/{tries} {reason} — retrying in {wait:.0f}s ...", flush=True)
            time.sleep(wait)
        else:
            print(f"  attempt {attempt}/{tries} {reason} — giving up", flush=True)
    return False


def resolve_addr(name_or_none):
    """--panel NAME -> MAC from panels.local.json; else IDM_ADDR env.

    A panel entry may set "write_response": true to force reliable write-with-response
    (needed by newer-firmware panels like the 64). IDM_WRITE_RESPONSE=1 still overrides globally.
    """
    global WRITE_RESPONSE
    if name_or_none:
        cfg = os.path.join(HERE, "panels.local.json")
        if not os.path.exists(cfg):
            sys.exit("no panels.local.json — copy panels.local.json.example and fill in MACs")
        panels = json.load(open(cfg)).get("panels", {})
        if name_or_none not in panels:
            sys.exit(f"panel '{name_or_none}' not in panels.local.json (have: {', '.join(panels)})")
        if panels[name_or_none].get("write_response"):
            WRITE_RESPONSE = True
        return panels[name_or_none]["mac"]
    addr = os.environ.get("IDM_ADDR")
    if not addr:
        sys.exit("set IDM_ADDR=<mac> or use --panel <name> (needs panels.local.json)")
    return addr


def main():
    args = sys.argv[1:]
    live = "--now" in args
    args = [a for a in args if a != "--now"]
    panel = None
    if "--panel" in args:
        i = args.index("--panel")
        panel = args[i + 1]
        del args[i:i + 2]
    if not args:
        sys.exit(__doc__)
    addr = resolve_addr(panel)
    items = []
    for a in args:
        spec, _, dw = a.rpartition(":")
        path, dwell = (spec, int(dw)) if spec and dw.isdigit() else (a, 8)
        if not os.path.exists(path):
            sys.exit(f"file not found: {path}")
        items.append((open(path, "rb").read(), dwell, os.path.basename(path)))
    mode = "live preview" if live else (f"{len(items)}-slot carousel" if len(items) > 1 else "single")
    print(f"connecting {addr} — {mode}", flush=True)
    ok = run_with_retry(lambda: push(addr, items, live=live))
    print("done" if ok else "FAILED", flush=True)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
