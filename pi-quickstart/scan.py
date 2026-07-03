#!/usr/bin/env python3
"""Find iDotMatrix panels in range — self-contained (needs only `bleak`).

Lists every nearby device whose name starts with "IDM" (iDotMatrix panels advertise as
IDM-XXXXXX). Prints the MAC address you feed to idm_push.py, the signal strength (closer = higher,
i.e. less negative), and the raw advertisement bytes.

    python3 scan.py            # scan ~8 s and list panels

This does NOT tell you which one is 32x32 and which is 64x64 — advertisement bytes are not a
reliable size tell across firmware. To identify them, run test_panel.py against each MAC and read
which physical panel lights up (it shows its size). Then save the mapping in panels.local.json.
"""
import asyncio
import sys

from bleak import BleakScanner


async def main():
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 8.0
    print(f"scanning {secs:.0f}s for IDM-* panels ...", flush=True)
    found = {}
    def cb(dev, adv):
        name = (adv.local_name or dev.name or "")
        if name.upper().startswith("IDM"):
            found[dev.address] = (name, adv.rssi, adv.manufacturer_data, adv.service_data)
    scanner = BleakScanner(detection_callback=cb)
    await scanner.start()
    await asyncio.sleep(secs)
    await scanner.stop()

    if not found:
        print("no IDM panels found. Make sure they're powered on, in range, and NOT connected in "
              "the phone app (one BLE connection at a time). Try again, or `python3 scan.py 15`.")
        return
    print(f"\nfound {len(found)} panel(s) — strongest signal first:\n")
    for addr, (name, rssi, mfd, svd) in sorted(found.items(), key=lambda kv: -kv[1][1]):
        print(f"  {name:14s}  MAC={addr}  rssi={rssi}dBm")
        for cid, val in (mfd or {}).items():
            print(f"                  mfr[{cid:#06x}]={val.hex()}")
        for uid, val in (svd or {}).items():
            print(f"                  svc[{uid}]={val.hex()}")
    print("\nnext: identify each with  python3 test_panel.py <MAC> 32   (or 64), watch the panel,")
    print("then record the mapping in panels.local.json (copy panels.local.json.example).")


if __name__ == "__main__":
    asyncio.run(main())
