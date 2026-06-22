#!/usr/bin/env python3
"""Persistent iDotMatrix BLE connection holder for interactive validation.

Connects once and stays connected, polling a command file so commands can be
sent across many turns without the panel reverting to its idle animation.

Protocol:
  - command file (argv[2]): lines of "<seq> <hexframe>"; when <seq> increases,
    the hex frame is written to fa02. Special frame "quit" disconnects.
  - status/log goes to stdout.

Usage: idm_daemon.py <ADDR> <cmdfile>
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "idotmatrix"))
import protocol as P  # noqa: E402
from bleak import BleakClient  # noqa: E402

ADDR = sys.argv[1]
CMDFILE = sys.argv[2]


async def main():
    last_seq = -1
    async with BleakClient(ADDR, timeout=25.0) as c:
        print(f"DAEMON connected={c.is_connected} addr={ADDR}", flush=True)

        def on_notify(_h, d):
            print(f"NOTIFY {bytes(d).hex()}", flush=True)

        await c.start_notify(P.NOTIFY_UUID, on_notify)
        print("DAEMON ready", flush=True)
        while True:
            try:
                with open(CMDFILE) as f:
                    line = f.read().strip()
            except FileNotFoundError:
                line = ""
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    seq = int(parts[0])
                    frame = parts[1]
                    if seq > last_seq:
                        last_seq = seq
                        if frame == "quit":
                            print("DAEMON quit", flush=True)
                            break
                        try:
                            await c.write_gatt_char(P.WRITE_UUID, bytes.fromhex(frame), response=False)
                            print(f"WROTE seq={seq} {frame}", flush=True)
                        except Exception as e:
                            print(f"ERR seq={seq} {e}", flush=True)
            if not c.is_connected:
                print("DAEMON lost connection", flush=True)
                break
            await asyncio.sleep(0.2)


asyncio.run(main())
