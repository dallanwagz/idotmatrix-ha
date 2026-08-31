"""push.py — the one push primitive. Used by both app.py (web UI) and schedule_run.py (cron).

Loads a catalog asset, connects to the target panel, and stores it to carousel slot 0 via
store_and_loop() so it plays back looping, on-device, with no live BLE connection required
afterward. One flock per panel MAC serializes pushes across both the Flask process and any
separately-invoked cron run (a plain threading.Lock wouldn't reach across processes).
"""
from __future__ import annotations

import fcntl
import json
import os
import sys
import time
from datetime import datetime, timezone

import catalog

HERE = os.path.dirname(os.path.abspath(__file__))
DRIVER_DIR = os.path.join(HERE, "driver")
sys.path.insert(0, DRIVER_DIR)
import panel_api          # noqa: E402
import panel_idotmatrix   # noqa: E402,F401  (registers the "idotmatrix32" driver)

STATE_PATH = os.path.join(HERE, "state.json")
PANELS_JSON = os.path.join(catalog.CATALOG_DIR, "panels.json")


def _load_panels() -> dict[str, str]:
    """name -> mac, from the panel manifest already committed in the catalog submodule."""
    data = json.load(open(PANELS_JSON))
    return {p["name"]: p["mac"] for p in data["panels"]}


PANELS = _load_panels()  # {"IDM-858931": "6F:5D:FE:85:89:31", "IDM-D28F7F": "1F:D6:5C:D2:8F:7F"}


def _lock(name: str):
    path = f"/tmp/wallboard-{name.replace(':', '').replace(' ', '_')}.lock"
    lf = open(path, "w")
    try:
        fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lf.close()
        return None
    return lf


def _unlock(lf) -> None:
    fcntl.flock(lf, fcntl.LOCK_UN)
    lf.close()


def load_state() -> dict:
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH) as f:
        return json.load(f)


def _record_state(panel_name: str, asset: dict, extra: dict | None = None) -> None:
    slock = _lock("state")
    try:
        state = load_state()
        entry = state.setdefault(panel_name, {})
        entry.update({
            "file_id": asset["file_id"],
            "name": asset["name"],
            "local": asset["local"],
            "pushed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        if extra:
            entry.update(extra)
        with open(STATE_PATH + ".tmp", "w") as f:
            json.dump(state, f, indent=2)
        os.replace(STATE_PATH + ".tmp", STATE_PATH)
    finally:
        _unlock(slock)


def _load_frames_and_fps(path: str):
    from PIL import Image, ImageSequence

    im = Image.open(path)
    frames, durations = [], []
    for frame in ImageSequence.Iterator(im):
        frames.append(frame.convert("RGB").copy())
        durations.append(frame.info.get("duration", 100))
    if len(frames) <= 1:
        return frames, 10.0
    avg_ms = sum(durations) / len(durations)
    fps = 1000.0 / max(avg_ms, 20)  # 20ms floor matches store_and_loop's own encode floor
    return frames, fps


def _connect_with_retry(mac: str, tries: int):
    last_err = ""
    for i in range(tries):
        d = panel_api.build_panel("idotmatrix32", mac, 0, 0)
        if d.connect():
            return d
        last_err = d.last_error
        if i < tries - 1:
            time.sleep(1 + i)  # linear backoff, same shape as pi-quickstart/idm_push.py
    raise RuntimeError(f"connect failed after {tries} tries: {last_err}")


def push_asset(panel_name: str, file_id: int, slot: int = 0, dwell: int = 3600,
               tries: int = 2, extra_state: dict | None = None) -> tuple[bool, str]:
    """Push a catalog asset to a named panel. Returns (ok, message).

    extra_state: optional extra fields merged into state.json's entry for this panel on
    success (e.g. schedule_run.py's last_rotated_at/rotate_index) — avoids callers reaching
    into _record_state directly.
    """
    mac = PANELS.get(panel_name)
    if not mac:
        return False, f"unknown panel {panel_name!r} (have: {', '.join(PANELS)})"

    asset = catalog.by_file_id(file_id)
    if not asset:
        return False, f"file_id {file_id} not in catalog"

    lf = _lock(mac)
    if lf is None:
        return False, "panel busy with another push, try again"
    try:
        frames, fps = _load_frames_and_fps(catalog.asset_path(asset))
        d = _connect_with_retry(mac, tries)
        try:
            d.store_and_loop(frames, fps=fps, slot=slot, dwell=dwell)
        finally:
            d.disconnect()
        _record_state(panel_name, asset, extra=extra_state)
        return True, f"pushed {asset['name']!r} to {panel_name}"
    except Exception as e:  # noqa: BLE001 — surfaced to the caller, not swallowed
        return False, f"{type(e).__name__}: {e}"
    finally:
        _unlock(lf)


if __name__ == "__main__":
    # ponytail: minimal self-check — dry-run the resolve/lock path without touching BLE
    assert set(PANELS) == {"IDM-858931", "IDM-D28F7F"}, PANELS
    lf = _lock("selftest")
    assert lf is not None
    lf2 = _lock("selftest")
    assert lf2 is None, "expected the second lock attempt to fail while held"
    _unlock(lf)
    lf3 = _lock("selftest")
    assert lf3 is not None, "expected the lock to be free again after unlock"
    _unlock(lf3)
    print(f"OK: panels={PANELS}")
