#!/usr/bin/env python3
"""Send any catalog asset to the iDotMatrix panel over BLE.

Accepts a bare file_id (resolved against the index*.json catalogs) OR a path to a GIF/PNG:

    python send_to_panel.py 16736                       # by file_id (any size)
    python send_to_panel.py library_64/holiday/24039.gif  # by path

It stores the asset to a count=1 carousel slot and shows it (loops in frame order). Static PNGs
are converted to a 1-frame GIF first. Overwrites carousel slot 0.

Requires bleak + the timebox/pinball iDotMatrix driver. Run it with a python that has bleak, e.g.:
    ~/.esphome-venv/bin/python send_to_panel.py 16736

Env overrides: IDM_ADDR (panel BLE address), IDM_DRIVER_DIR (path to timebox/pinball),
IDM_SLOT (default 0), IDM_DWELL (time_sign seconds, default 300).
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
SLOT = int(os.environ.get("IDM_SLOT", "0"))
DWELL = int(os.environ.get("IDM_DWELL", "300"))


def resolve(arg):
    """Return (abs_path, label) for a file_id or path argument."""
    if os.path.exists(arg):
        return os.path.abspath(arg), os.path.basename(arg)
    p = os.path.join(HERE, arg)
    if os.path.exists(p):
        return p, arg
    if arg.isdigit():
        fid = int(arg)
        for idx in sorted(glob.glob(os.path.join(HERE, "index*.json"))):
            for r in json.load(open(idx)):
                if r["file_id"] == fid:
                    local = os.path.join(HERE, r["local"])
                    sz = f'{r["width"]}x{r["height"]}'
                    return local, f'{r.get("name", fid)} ({sz} {r["category"]})'
        sys.exit(f"file_id {fid} not found in any index*.json")
    sys.exit(f"could not resolve '{arg}' (not a path or known file_id)")


def to_gif(path):
    """Load the asset as GIF bytes — pass GIFs through, render PNGs to a single 32/16/64 frame."""
    data = open(path, "rb").read()
    if path.lower().endswith(".gif"):
        return data
    from PIL import Image
    im = Image.open(path).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, format="GIF")
    return buf.getvalue()


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: send_to_panel.py <file_id | path-to-gif-or-png>")
    path, label = resolve(sys.argv[1])
    gif = to_gif(path)
    print(f"sending {label}: {os.path.relpath(path, HERE)} ({len(gif)} bytes) -> slot {SLOT}", flush=True)

    sys.path.insert(0, DRIVER_DIR)
    import panel_api
    import panel_idotmatrix  # noqa: F401  (registers the idotmatrix32 driver)
    import idm_protocol as IDM

    d = panel_api.build_panel("idotmatrix32", ADDR, 0, 0)
    if not d.connect():
        sys.exit(f"connect FAIL: {d.last_error}")
    print("connected", flush=True)
    L = d._link
    L.last_notify = b""
    L.write(IDM.frame(2, 1, 1, SLOT))          # slot-setup: count=1
    time.sleep(1.0)
    print("setup ack:", L.last_notify.hex() or "(none)", flush=True)
    up = IDM.ImageUpload(gif, IDM.DataType.GIF, image_index=SLOT, time_sign=DWELL)
    ok, info = L.upload_acked(up.outer_packets())
    print("upload:", ok, info, flush=True)
    L.write(IDM.enter_asset_view())
    time.sleep(1.0)
    d.disconnect()
    print("DONE — showing on panel" if ok else "UPLOAD FAILED", flush=True)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
