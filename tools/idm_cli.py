#!/usr/bin/env python3
"""iDotMatrix BLE driver/CLI — drives the panel directly from this host via bleak.

Imports the pure protocol module so this doubles as live validation of it.

Usage:
  idm_cli.py scan                       # list IDM-* devices in range
  idm_cli.py info                       # connect, enumerate GATT, read firmware, watch 3s
  idm_cli.py watch [secs]               # connect and print fa03 notifications
  idm_cli.py send <hexframe>            # write raw hex to fa02
  idm_cli.py time                       # sync clock
  idm_cli.py bright <0-100>
  idm_cli.py color <r> <g> <b>          # fullscreen RGB
  idm_cli.py clock <style> [r g b]
  idm_cli.py countdown <mode> <min> <sec>
  idm_cli.py chrono <mode>
  idm_cli.py score <c1> <c2>
  idm_cli.py flip <0|1>
  idm_cli.py screen <0|1>               # panel off/on
  idm_cli.py reset

Env: IDM_ADDR can pin a specific device (CoreBluetooth UUID on macOS).
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "idotmatrix"))
import protocol as P  # noqa: E402

from bleak import BleakClient, BleakScanner  # noqa: E402


def _match(d) -> bool:
    return bool(d.name and (d.name.startswith("IDM-") or "idotmatrix" in d.name.lower()))


async def scan(timeout: float = 8.0):
    print(f"scanning {timeout}s for IDM-* ...")
    devs = await BleakScanner.discover(timeout=timeout, return_adv=True)
    found = []
    for addr, (d, adv) in devs.items():
        name = d.name or adv.local_name or ""
        mfr = {k: v.hex() for k, v in (adv.manufacturer_data or {}).items()}
        if _match(d) or (adv.local_name and adv.local_name.startswith("IDM-")):
            found.append((addr, name, adv.rssi, mfr))
            print(f"  *** {addr}  name={name!r}  rssi={adv.rssi}  mfr={mfr}")
        else:
            print(f"      {addr}  name={name!r}  rssi={adv.rssi}")
    return found


async def _find_addr():
    if os.environ.get("IDM_ADDR"):
        return os.environ["IDM_ADDR"]
    d = await BleakScanner.find_device_by_filter(_match, timeout=10.0)
    if not d:
        raise SystemExit("no IDM-* device found (is the app still holding it? force-stop it)")
    print(f"found {d.address} name={d.name!r}")
    return d.address


def _on_notify(_char, data: bytearray):
    st = P.parse_status(bytes(data))
    print(f"  NOTIFY fa03: {bytes(data).hex()}  -> dtype={st.data_type} ack={st.ack.name}")


async def info():
    addr = await _find_addr()
    async with BleakClient(addr, timeout=20.0) as c:
        print(f"connected={c.is_connected}")
        for s in c.services:
            print(f"service {s.uuid}")
            for ch in s.characteristics:
                print(f"   char {ch.uuid}  props={','.join(ch.properties)}  handle={ch.handle}")
        # firmware version
        try:
            ver = await c.read_gatt_char(P.VERSION_UUID)
            print(f"firmware: {ver!r}  ({ver.hex()})")
        except Exception as e:
            print(f"version read failed: {e}")
        try:
            await c.start_notify(P.NOTIFY_UUID, _on_notify)
            await c.write_gatt_char(P.WRITE_UUID, P.get_device_info(), response=False)
            await asyncio.sleep(3.0)
        except Exception as e:
            print(f"notify/info failed: {e}")


async def watch(secs: float = 15.0):
    addr = await _find_addr()
    async with BleakClient(addr, timeout=20.0) as c:
        await c.start_notify(P.NOTIFY_UUID, _on_notify)
        print(f"watching fa03 for {secs}s ...")
        await asyncio.sleep(secs)


async def send_frames(frames: list[bytes], watch_secs: float = 2.0):
    addr = await _find_addr()
    async with BleakClient(addr, timeout=20.0) as c:
        print(f"connected={c.is_connected}")
        try:
            await c.start_notify(P.NOTIFY_UUID, _on_notify)
        except Exception as e:
            print(f"(notify subscribe failed: {e})")
        for fr in frames:
            print(f"  WRITE fa02: {fr.hex()}")
            await c.write_gatt_char(P.WRITE_UUID, fr, response=False)
            await asyncio.sleep(0.4)
        await asyncio.sleep(watch_secs)


def build(argv: list[str]) -> list[bytes]:
    cmd, *a = argv
    match cmd:
        case "time":
            return [P.set_time()]
        case "bright":
            return [P.set_brightness(int(a[0]))]
        case "color":
            return [P.set_fullscreen_color(int(a[0]), int(a[1]), int(a[2]))]
        case "clock":
            style = int(a[0]); rgb = list(map(int, a[1:4])) if len(a) >= 4 else [255, 255, 255]
            return [P.set_clock(style, r=rgb[0], g=rgb[1], b=rgb[2])]
        case "countdown":
            return [P.set_countdown(int(a[0]), int(a[1]), int(a[2]))]
        case "chrono":
            return [P.set_chronograph(int(a[0]))]
        case "score":
            return [P.set_scoreboard(int(a[0]), int(a[1]))]
        case "flip":
            return [P.set_flip(bool(int(a[0])))]
        case "screen":
            return [P.set_screen(bool(int(a[0])))]
        case "reset":
            return [P.reset_device()]
        case "send":
            return [bytes.fromhex(a[0])]
        case _:
            raise SystemExit(f"unknown command: {cmd}")


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    cmd = sys.argv[1]
    if cmd == "scan":
        asyncio.run(scan())
    elif cmd == "info":
        asyncio.run(info())
    elif cmd == "watch":
        asyncio.run(watch(float(sys.argv[2]) if len(sys.argv) > 2 else 15.0))
    else:
        asyncio.run(send_frames(build(sys.argv[1:])))


if __name__ == "__main__":
    main()
