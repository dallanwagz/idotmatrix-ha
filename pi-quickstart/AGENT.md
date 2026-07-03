# Agent handoff — set Tyler up to control his two iDotMatrix panels from his Pi

**Paste this to Tyler's Claude agent** (it's also the body of the GitHub setup issue). It gives the
agent everything it needs; it should then drive the whole process, asking Tyler only to look at the
panels and confirm.

---

You're helping **Tyler**, who is new to Claude. Goal: get his **Raspberry Pi** driving his **two
iDotMatrix LED panels** — a **32×32** and a **64×64** — over Bluetooth, no phone app, and leave him
able to say "show me X on the panels" and have you build + push it. Everything you need is in the
**`pi-quickstart/`** folder of this repo. **Read `pi-quickstart/README.md` and `pi-quickstart/SPEC.md`
first**, then work the steps below. Tyler is a beginner — run the commands yourself over his Pi
session, explain briefly, and ask him only to watch the panels and answer simple questions.

## What you're working with
- Two panels, BLE (Bluetooth Low Energy). On the Pi/Linux they're addressed by **MAC address**.
- The kit is **self-contained**: only `bleak` + `Pillow` (installed by `pi-quickstart/setup.sh` into
  `~/.idm-venv`). Use `~/.idm-venv/bin/python` for every script.
- The upload protocol is **size-agnostic** — the same `idm_push.py` drives both the 32 and the 64;
  you just send a GIF of the matching size.

## Do these in order
1. **Install** — on the Pi, `bash pi-quickstart/setup.sh` (BlueZ + venv + libs; idempotent).
2. **Confirm Bluetooth is alive** — `bluetoothctl --timeout 5 scan on` should list *some* devices.
   If the adapter is missing/blocked: `rfkill unblock bluetooth`, check `hciconfig`/`bluetoothctl
   list`, make sure `sudo systemctl status bluetooth` is active. (Ask Tyler which Pi model / whether
   it has built-in BT or a USB dongle if nothing shows.)
3. **Scan** — `~/.idm-venv/bin/python pi-quickstart/scan.py`. Expect two `IDM-XXXXXX` entries.
   Record both MACs. If none: panels powered on? phone app disconnected (one BLE link per panel)? in
   range? Retry with `scan.py 15`.
4. **Identify + prove control** — for each MAC run `test_panel.py <MAC> 32` (then `64` if needed) and
   ask Tyler **which physical panel lit up and what number it showed**. That maps each MAC to a size
   AND proves control. This operator-in-the-loop check is the reliable identifier — don't skip it.
5. **Save the mapping** — `cp panels.local.json.example panels.local.json` and fill in the real MACs
   under `small` (32) and `big` (64). (Gitignored; stays on the Pi.)
6. **First real asset** — build something small and push it **live** to confirm the full pipeline:
   `~/.idm-venv/bin/python pi-quickstart/examples/scroll_text.py "HI TYLER" 32 /tmp/hi.gif` then
   `~/.idm-venv/bin/python pi-quickstart/idm_push.py --panel small --now /tmp/hi.gif`.
   Confirm with Tyler it appeared.

## Then: make whatever Tyler asks for
He'll describe things ("a red guitar sliding between the two panels", "a heart beating", "GO
BRASIL scrolling"). Your job: turn the description into a **panel-safe GIF** and push it.
- Build with `pi-quickstart/assetlib.py` and adapt an `examples/` script. `assetlib.save_gif()`
  keeps frames panel-safe automatically.
- **The one hard rule:** the decoder silently drops colour-heavy/gradient frames — keep a handful of
  **flat** colours per frame. Build via the helpers and this is handled.
- Iterate fast with `idm_push.py --now` (instant, not stored). Make it permanent by dropping `--now`
  and adding a dwell (`art.gif:30`). Up to 12 GIFs can share a rotating carousel.
- **Cross-panel** (the guitar): `examples/cross_panel_sweep.py <lsize> <rsize> left.gif right.gif`
  then `dual_push.py <LEFT_MAC> left.gif <RIGHT_MAC> right.gif`. Treats both panels as one wide scene.
- To preview a GIF for Tyler before pushing, `assetlib.preview_png()` writes a zoomed PNG.

## Safety (don't brick the panels)
- **Never** enable the device password. **Never** leave brightness stickily low. Keep the **phone app
  off** while the Pi drives a panel (one BLE connection at a time). These are the only real footguns.

## Deeper reference (only if needed)
- `pi-quickstart/SPEC.md` — asset rules in one page. `docs/PROTOCOL.md` — full reverse-engineered
  BLE protocol. `demo/worldcup/` — a finished team-switcher (Brazil/USA at 32 and 64) to crib from.
  `tools/etoys_catalog/` — a 2,700+ ready-made asset library (needs the catalog submodule).

When step 6 works and Tyler has seen at least one thing he asked for on the panels, you're done —
he's set up.
