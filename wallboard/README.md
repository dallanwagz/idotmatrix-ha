# wallboard

Daily-use control for the two 32×32 iDotMatrix wall panels (`IDM-858931`, `IDM-D28F7F`):
a searchable gallery over the [asset catalog](../tools/etoys_catalog/) with per-panel push
buttons, plus a cron-driven scheduler for hands-off content rotation. Replaces the retired
"World Cup" light show that used to run on this same host.

## Layout
- `driver/` — the BLE/protocol stack (`idm_protocol.py`, `panel_api.py`,
  `panel_idotmatrix.py`), salvaged from the original `/home/claude/timebox/` build on
  `10.10.2.203`. General-purpose, no World Cup content.
- `catalog.py` — loads `../tools/etoys_catalog/index*.csv` into memory; search/filter/by-id.
- `push.py` — the one push primitive (per-panel `flock`, connect+retry, `store_and_loop`,
  records `state.json`). Used by both `app.py` and `schedule_run.py`.
- `app.py` — the Flask gallery/control UI.
- `schedule_run.py` + `schedule.json` — cron entrypoint for scheduled rotation/pinned pushes.
- `deploy/wallboard.service` — systemd unit for the always-on web app.

## Run it (on the Pi, `10.10.2.203`)
```bash
cd wallboard
python3 -m venv .venv
.venv/bin/pip install bleak flask Pillow
WALLBOARD_PORT=8090 .venv/bin/python app.py   # scratch port for testing before cutover
```

Self-checks (no BLE, no network — safe anywhere):
```bash
python3 catalog.py
python3 push.py
```

## Scheduling
Edit `schedule.json` — per panel, either `"mode": "rotate"` (round-robins through a
`category` every `interval_minutes`) and/or a `pinned` list of `{"time": "HH:MM", "file_id": N}`
overrides. Cron runs `schedule_run.py` every 15 minutes; see the repo's top-level plan doc
for the exact crontab line and the full cutover sequence from the old light show.
