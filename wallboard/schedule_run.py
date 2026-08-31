#!/usr/bin/env python3
"""schedule_run.py — cron entrypoint, run every 15 min. Per panel: a pinned time-of-day
entry wins if we're in its 15-minute bucket right now; otherwise, if `interval_minutes` has
elapsed since the last rotation, advance to the next asset in the configured category.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import catalog  # noqa: E402
import push     # noqa: E402

SCHEDULE_PATH = os.path.join(HERE, "schedule.json")


def _load_schedule() -> dict:
    with open(SCHEDULE_PATH) as f:
        return json.load(f)


def _due_pinned(entry: dict, now: datetime) -> int | None:
    for p in entry.get("pinned", []):
        hh, mm = (int(x) for x in p["time"].split(":"))
        if now.hour == hh and now.minute // 15 == mm // 15:
            return int(p["file_id"])
    return None


def _due_rotate(panel_name: str, entry: dict, state: dict, now: datetime):
    """Returns (file_id, next_index) if a rotation is due, else None."""
    if entry.get("mode") != "rotate":
        return None
    interval = int(entry.get("interval_minutes", 360))
    panel_state = state.get(panel_name, {})
    last = panel_state.get("last_rotated_at")
    if last and (now - datetime.fromisoformat(last)).total_seconds() < interval * 60:
        return None
    pool = sorted(catalog.search(category=entry.get("category")), key=lambda a: a["file_id"])
    if not pool:
        return None
    idx = (panel_state.get("rotate_index", -1) + 1) % len(pool)
    return pool[idx]["file_id"], idx


def main() -> None:
    schedule = _load_schedule()
    state = push.load_state()
    now = datetime.now(timezone.utc)

    for panel_name, entry in schedule.items():
        fid = _due_pinned(entry, now)
        if fid is not None:
            ok, msg = push.push_asset(panel_name, fid, tries=5,
                                       extra_state={"last_rotated_at": now.isoformat()})
            print(f"{now.isoformat()} {panel_name} pinned -> {msg}", flush=True)
            continue

        due = _due_rotate(panel_name, entry, state, now)
        if due is None:
            continue
        fid, idx = due
        extra = {"last_rotated_at": now.isoformat(), "rotate_index": idx}
        ok, msg = push.push_asset(panel_name, fid, tries=5, extra_state=extra)
        print(f"{now.isoformat()} {panel_name} rotate -> {msg}", flush=True)


if __name__ == "__main__":
    main()
