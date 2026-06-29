#!/usr/bin/env python3
"""Standalone iDotMatrix carousel pusher — bleak only, no external driver.

Loads a rotating carousel of GIFs onto a 32x32 iDotMatrix panel (slots 0..N-1, each with its own
dwell in seconds); the panel then cycles them autonomously. Wipes all 12 slots first so nothing
stale lingers. Reverse-engineered protocol (see repo docs/PROTOCOL.md); this file vendors just the
upload logic so it runs anywhere with bleak (e.g. a Raspberry Pi on BlueZ, where the MAC is native).

    IDM_ADDR=<MAC> python3 idm_push.py flag.gif:10 ball.gif:8 brasil.gif:8
    IDM_ADDR=<MAC> python3 idm_push.py gol.gif:5            # single item works too

Up to 12 items (firmware hard cap). Address by BLE MAC on Linux/Pi (BlueZ);
on macOS use the per-host CoreBluetooth UUID instead.
"""
import asyncio
import os
import struct
import sys
import zlib

from bleak import BleakClient

FA_WRITE = "0000fa02-0000-1000-8000-00805f9b34fb"   # control/upload write
FA_NOTIFY = "0000fa03-0000-1000-8000-00805f9b34fb"  # status/ACK notify
OUTER = 4096          # outer packet payload chunk
SAFE = 244            # inner GATT write cap (panel drops larger)
GIF = 1               # DataType.GIF (header byte[2]=1, byte[3]=0)


def frame(cmd, sub, *payload):
    body = bytes(b & 0xFF for b in payload)
    total = 4 + len(body)
    return bytes((total & 0xFF, (total >> 8) & 0xFF, cmd & 0xFF, sub & 0xFF)) + body


def outer_packets(data, image_index, time_sign, dtype=GIF):
    crc = struct.pack("<I", zlib.crc32(data) & 0xFFFFFFFF)
    total = len(data)
    ts = 0 if image_index == 12 else time_sign
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
            self.status = data[4]      # byte[4] = status: 1=next, 3=done, 2=no-space
            self.ev.set()


async def w(client, b):
    await client.write_gatt_char(FA_WRITE, b, response=False)


async def upload(client, link, gif, slot, dwell):
    for pkt in outer_packets(gif, slot, dwell):
        for j in range(0, len(pkt), SAFE):
            await client.write_gatt_char(FA_WRITE, pkt[j:j + SAFE], response=False)
            await asyncio.sleep(0.02)
        link.ev.clear()
        try:
            await asyncio.wait_for(link.ev.wait(), 8)
        except asyncio.TimeoutError:
            return False, "ack timeout"
        if link.status == 2:
            return False, "NO_SPACE"
    return True, f"status {link.status}"


async def main():
    addr = os.environ.get("IDM_ADDR")
    if not addr or len(sys.argv) < 2:
        sys.exit("usage: IDM_ADDR=<mac|uuid> python3 idm_push.py <gif>[:dwell] ...  (up to 12)")
    items = []
    for a in sys.argv[1:]:
        spec, _, dw = a.rpartition(":")
        path, dwell = (spec, int(dw)) if spec and dw.isdigit() else (a, 8)
        if not os.path.exists(path):
            sys.exit(f"file not found: {path}")
        items.append((open(path, "rb").read(), dwell, os.path.basename(path)))
    items = items[:12]
    n = len(items)
    link = Link()
    print(f"connecting {addr} — loading {n}-slot carousel", flush=True)
    async with BleakClient(addr, timeout=25) as c:
        await c.start_notify(FA_NOTIFY, link.on_notify)
        await w(c, frame(2, 1, 12, *range(12)))     # wipe all 12 slots
        await asyncio.sleep(1.0)
        await w(c, frame(2, 1, n, *range(n)))        # slot-setup count=n
        await asyncio.sleep(1.0)
        ok_all = True
        for i, (gif, dwell, name) in enumerate(items):
            ok, info = await upload(c, link, gif, i, dwell)
            print(f"  slot {i}: {name:14s} {len(gif):5d}B dwell={dwell:>2}s -> {ok} ({info})", flush=True)
            ok_all &= ok
            if not ok:
                break
            await asyncio.sleep(0.25)
        await w(c, frame(10, 1))                      # enter asset view -> start cycling
        await asyncio.sleep(1.0)
    print("carousel started — cycling autonomously" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 2)


if __name__ == "__main__":
    asyncio.run(main())
