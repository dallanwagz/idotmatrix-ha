# idm-panel-api — REST service to push GIFs to the iDotMatrix panel

A containerized HTTP API that **accepts a GIF, validates it against the
[64×64 spec](../docs/idm64-gif-spec.md), and — if it passes — drives it onto the panel over
Bluetooth.** Any tool/LLM/agent can now display content with one HTTP call.

## Where it runs
On the **Pi** (or any Linux host with BlueZ, in Bluetooth range of the panel). A container on a
machine without a Bluetooth radio near the panel can't reach it — `bleak` in the container talks to
the **host's BlueZ over the mounted DBus socket**.

## Run it
```bash
# on the Pi, from a checkout that has pi-quickstart/panels.local.json filled in:
sudo docker compose -f server/docker-compose.yml up -d --build
curl http://localhost:8080/health          # {"status":"ok","panel":"big","busy":false}
```
The panel MACs come from `pi-quickstart/panels.local.json` (mounted read-only, not baked into the image).

## Endpoints
| Method | Path | Body | What |
|---|---|---|---|
| GET | `/health` | — | liveness + whether a push is in progress |
| GET | `/spec` | — | the GIF content spec (markdown) |
| POST | `/validate` | multipart `gif` | check against the spec, no push → `{compliant, checks[]}` |
| POST | `/push` | multipart `gif` | validate then push to the panel |

`/push` query params:
- `fix=1` — auto-normalize a non-compliant GIF (resize/loop/shrink) before pushing
- `mode=now` (default, live/transient) or `mode=store` (persist on-device)
- `dwell=<sec>` — dwell for `mode=store` (default 30)
- `panel=<name>` — a panel from `panels.local.json` (default `big`)

## Examples
```bash
# validate only
curl -F gif=@art.gif http://PI:8080/validate

# push live (rejects if not compliant)
curl -F gif=@art.gif http://PI:8080/push

# push, auto-fixing anything non-compliant, and store it so it persists
curl -F gif=@random.gif "http://PI:8080/push?fix=1&mode=store&dwell=60"
```

## Notes
- The panel accepts **one Bluetooth connection at a time**, so pushes are **serialized** (a second
  concurrent push gets `429`). Keep the vendor phone app disconnected while the API drives the panel.
- Big uploads occasionally hit a transient BLE fault; the push path **auto-retries** with a fresh
  connection (see `idm_push.run_with_retry`).
- One gunicorn worker on purpose (single BLE central); threads handle `/health` + `/validate`
  concurrently with an in-flight push.
