#!/usr/bin/env python3
"""Upload a 32x32 image to the iDotMatrix panel using the chunked CRC path.

Builds a BGR, row-major, 3072-byte buffer, wraps it with protocol.ImageUpload
(16-byte header + CRC32), splits into MTU-sized writes, and drives the fa03 ACK.

Usage: idm_image.py <ADDR> [quadrants|red|green|blue|smiley]
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "idotmatrix"))
import protocol as P  # noqa: E402
from bleak import BleakClient  # noqa: E402

ADDR = sys.argv[1]
PATTERN = sys.argv[2] if len(sys.argv) > 2 else "quadrants"
W = H = 32


def rgb_buf():
    px = [(0, 0, 0)] * (W * H)
    for y in range(H):
        for x in range(W):
            if PATTERN == "quadrants":
                if x < 16 and y < 16:
                    c = (255, 0, 0)      # TL red
                elif x >= 16 and y < 16:
                    c = (0, 255, 0)      # TR green
                elif x < 16 and y >= 16:
                    c = (0, 0, 255)      # BL blue
                else:
                    c = (255, 255, 0)    # BR yellow
            elif PATTERN == "red":
                c = (255, 0, 0)
            elif PATTERN == "green":
                c = (0, 255, 0)
            elif PATTERN == "blue":
                c = (0, 0, 255)
            else:
                c = (255, 255, 255)
            px[y * W + x] = c
    return px


def bgr_bytes():
    out = bytearray()
    for (r, g, b) in rgb_buf():
        out += bytes((r, g, b))   # RGB order (the app's "bitmap2BGR" actually emits RGB)
    return bytes(out)


async def main():
    data = bgr_bytes()
    assert len(data) == W * H * 3 == 3072, len(data)
    up = P.ImageUpload(data, P.DataType.IMAGE)
    packets = up.outer_packets()
    done = asyncio.Event()
    last = {"status": None}

    async with BleakClient(ADDR, timeout=25.0) as c:
        mtu = c.mtu_size
        step = int(os.environ.get("IDM_CHUNK", "0")) or max(20, min(mtu - 3, P.INNER_MTU_HIGH))
        pace = float(os.environ.get("IDM_PACE", "0.02"))
        print(f"connected mtu={mtu} inner_step={step} outer_packets={len(packets)} crc_data={len(data)}B")

        def on_notify(_h, d):
            st = P.parse_status(bytes(d))
            print(f"  NOTIFY {bytes(d).hex()} ack={st.ack.name}")
            last["status"] = st.ack
            if st.ack in (P.Ack.DONE,):
                done.set()

        await c.start_notify(P.NOTIFY_UUID, on_notify)
        for pi, pkt in enumerate(packets):
            writes = P.inner_writes(pkt, mtu_ok=(step >= 100))
            # re-split to actual negotiated step:
            writes = [pkt[i:i + step] for i in range(0, len(pkt), step)]
            resp = os.environ.get("IDM_WRITE_RESP", "0") == "1"
            print(f"outer {pi}: {len(pkt)}B -> {len(writes)} inner writes (chunk={step} pace={pace} response={resp})")
            for w in writes:
                await c.write_gatt_char(P.WRITE_UUID, w, response=resp)
                if pace:
                    await asyncio.sleep(pace)
        try:
            await asyncio.wait_for(done.wait(), timeout=5.0)
            print("UPLOAD DONE (device ACK 3)")
        except asyncio.TimeoutError:
            print(f"no DONE ack within 5s (last={last['status']}) — image may still have rendered")
        await asyncio.sleep(float(os.environ.get("IDM_HOLD", "2.0")))


asyncio.run(main())
