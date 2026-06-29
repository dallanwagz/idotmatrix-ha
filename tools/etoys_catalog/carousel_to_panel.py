#!/usr/bin/env python3
"""Load a rotating carousel onto an iDotMatrix panel — GIFs in slots 0..N-1, each with its own
dwell (seconds). The device then cycles them autonomously (no host needed, survives disconnect).

    IDM_ADDR=<MAC> ~/.esphome-venv/bin/python carousel_to_panel.py gif:dwell gif:dwell ...
    e.g.  IDM_ADDR=6F:5D:FE:85:89:31 ... carousel_to_panel.py flag.gif:10 ball.gif:8 brasil.gif:8

Accepts up to 12 items (firmware hard cap). Each item is <path|file_id>[:dwell_seconds] (default 8).
A bare file_id resolves against the catalogs. Overwrites the panel's carousel.
"""
import glob
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DRIVER_DIR = os.environ.get("IDM_DRIVER_DIR", "/Users/dallan/repo/timebox/pinball")
ADDR = os.environ.get("IDM_ADDR", "0A935535-7939-DD31-2CC3-72B639D9560B")


def resolve(arg):
    if os.path.exists(arg):
        return os.path.abspath(arg)
    p = os.path.join(HERE, arg)
    if os.path.exists(p):
        return p
    if arg.isdigit():
        for idx in sorted(glob.glob(os.path.join(HERE, "index*.json"))):
            for r in json.load(open(idx)):
                if r["file_id"] == int(arg):
                    return os.path.join(HERE, r["local"])
    sys.exit(f"could not resolve '{arg}'")


def to_gif(path):
    data = open(path, "rb").read()
    if path.lower().endswith(".gif"):
        return data
    from PIL import Image
    buf = io.BytesIO()
    Image.open(path).convert("RGB").save(buf, format="GIF")
    return buf.getvalue()


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: carousel_to_panel.py <gif|file_id>[:dwell] ...  (up to 12)")
    items = []
    for a in sys.argv[1:]:
        spec, _, dw = a.rpartition(":")
        if spec and dw.isdigit():
            items.append((resolve(spec), int(dw)))
        else:
            items.append((resolve(a), 8))
    if len(items) > 12:
        print(f"note: {len(items)} items > 12-slot cap; keeping first 12", flush=True)
        items = items[:12]
    n = len(items)

    sys.path.insert(0, DRIVER_DIR)
    import panel_api
    import panel_idotmatrix  # noqa: F401
    import idm_protocol as IDM

    d = panel_api.build_panel("idotmatrix32", ADDR, 0, 0)
    if not d.connect():
        sys.exit(f"connect FAIL: {d.last_error}")
    print(f"connected {ADDR} — loading {n}-slot carousel", flush=True)
    L = d._link
    L.last_notify = b""
    L.write(IDM.frame(2, 1, 12, *range(12)))         # full clear: wipe all 12 slots (kills leftovers)
    time.sleep(1.0)
    print("wipe ack:", L.last_notify.hex() or "(none)", flush=True)
    L.last_notify = b""
    L.write(IDM.frame(2, 1, n, *range(n)))          # slot-setup, count=n
    time.sleep(1.0)
    print("setup ack:", L.last_notify.hex() or "(none)", flush=True)
    for i, (path, dw) in enumerate(items):
        gif = to_gif(path)
        up = IDM.ImageUpload(gif, IDM.DataType.GIF, image_index=i, time_sign=dw)
        ok, info = L.upload_acked(up.outer_packets())
        print(f"  slot {i}: {os.path.basename(path):14s} {len(gif):5d}B dwell={dw:>2}s -> {ok} ({info})", flush=True)
        if not ok:
            print(f"  *** stopped at slot {i}: {info}", flush=True)
            break
        time.sleep(0.25)
    L.write(IDM.enter_asset_view())
    time.sleep(1.0)
    d.disconnect()
    print("carousel started — cycling autonomously", flush=True)


if __name__ == "__main__":
    main()
