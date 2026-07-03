# iDotMatrix Pi Quickstart — get two panels lit from a Raspberry Pi

**For Tyler (and his Claude agent).** This folder is a complete, self-contained kit to make a
Raspberry Pi drive two iDotMatrix LED panels — a **32×32** and a **64×64** — with no phone app and
no special knowledge. By the end you'll be able to say *"put a spinning guitar across both panels"*
and have it happen.

Two dependencies only: **`bleak`** (Bluetooth) and **`Pillow`** (image building). `setup.sh`
installs them. Everything here talks to the panels over Bluetooth by their **MAC address**, which is
how Linux/BlueZ (the Pi) addresses BLE devices.

> **New to this? You don't run these commands by hand.** Point your Claude agent at this folder and
> tell it *"walk me through the quickstart in pi-quickstart/README.md."* The steps below are written
> so the agent drives and you just watch the panels and answer "yes, the left one lit up."

---

## The 5 steps

### 1. Get onto the Pi & install
On the Raspberry Pi (or `ssh` into it), from this folder:
```bash
bash setup.sh
```
It installs BlueZ + a Python venv at `~/.idm-venv` with `bleak` and `pillow`. **Use
`~/.idm-venv/bin/python` for every script below.** Re-running is safe.

### 2. Find the panels
Power on both panels, keep them close, and make sure the **phone app is NOT connected** (one
Bluetooth connection per panel at a time).
```bash
~/.idm-venv/bin/python scan.py
```
You'll get a list of `IDM-XXXXXX` devices with their **MAC** and signal strength. You should see
two. Copy both MACs.

### 3. Identify which MAC is which panel (and prove control works)
Scan can't reliably tell 32 from 64, so we just *look*. Show a labelled test pattern on one MAC:
```bash
~/.idm-venv/bin/python test_panel.py <MAC-A> 32
```
Watch your panels — one lights up with a coloured border and a big number. If the panel that lit up
is your 32×32, great. If it's actually the 64×64, run it again with `64`. Repeat for `<MAC-B>`.
Now you know: *this MAC = 32, that MAC = 64.* (A panel lighting up at all = **control confirmed.**)

### 4. Save the mapping
```bash
cp panels.local.json.example panels.local.json
# edit panels.local.json: put each real MAC + size under "small" (32) and "big" (64)
```
This file stays on your Pi (it's gitignored). Now scripts accept `--panel small` / `--panel big`
instead of raw MACs.

### 5. Make something and show it
Instant live preview (nothing stored) — the fast way to iterate:
```bash
~/.idm-venv/bin/python examples/scroll_text.py "HI TYLER" 32 hi.gif
IDM_ADDR=<32-MAC> ~/.idm-venv/bin/python idm_push.py --now hi.gif
```
Or via the saved names:
```bash
~/.idm-venv/bin/python idm_push.py --panel small --now hi.gif
```
Make it stick (loops on-device after you disconnect): drop `--now` and add a dwell, e.g.
`idm_push.py --panel small hi.gif:30`.

---

## Turning "I want X" into a panel asset

The panels show **GIFs**. Your agent builds them with [`assetlib.py`](assetlib.py) (drawing helpers
that keep every frame **panel-safe** — see the one big rule below) and the [`examples/`](examples/):

| want | start from |
|---|---|
| scrolling words | `examples/scroll_text.py` |
| a moving sprite / bouncing thing | `examples/bouncing_ball.py` |
| **one animation spanning BOTH panels** (Tyler's guitar) | `examples/cross_panel_sweep.py` + `dual_push.py` |

Describe what you want to your agent ("a red guitar that slides from the left panel to the right and
back"). The agent adapts an example, previews it, and pushes it live. If a frame looks wrong, iterate
— it's just Python + Pillow.

**The one rule that matters:** the panel decoder **silently drops frames that are too
colour-heavy** (smooth gradients, hundreds of colours). Keep frames to a handful of **flat**
colours. `assetlib.save_gif()` enforces this automatically, so build with the helpers and you're
fine. Full details: [`SPEC.md`](SPEC.md).

## Cross-panel animation (the guitar)
Two panels side by side = one wide canvas. Generate a matched left/right pair and start them
together:
```bash
~/.idm-venv/bin/python examples/cross_panel_sweep.py 32 64 left.gif right.gif
~/.idm-venv/bin/python dual_push.py <32-MAC> left.gif <64-MAC> right.gif
```
The sprite glides off the right edge of the left panel and onto the left edge of the right panel. It
loops, so any tiny start skew washes out. Swap the guitar shape in the example for anything.

## Ready-made assets (optional)
The main repo has a **2,700+ asset library** (hearts, holidays, emoji, animals…) and a **World Cup
team set** in `demo/worldcup/`. Those need the full repo/catalog; this quickstart is deliberately
standalone so you can get going immediately. Ask your agent about them once the basics work.

## Files in this kit
| file | what it does |
|---|---|
| `setup.sh` | one-time Pi install (BlueZ + venv + bleak + pillow) |
| `scan.py` | find panels → MAC + signal |
| `test_panel.py` | show a labelled test pattern → identify size + prove control |
| `idm_push.py` | push GIF(s): `--now` live, `name.gif:dwell` stored, or a 12-slot carousel |
| `dual_push.py` | show two GIFs on two panels at once (cross-panel) |
| `assetlib.py` | panel-safe drawing/GIF helpers (import this to build assets) |
| `examples/` | scroll text · bouncing ball · cross-panel guitar sweep |
| `SPEC.md` | the asset rules (sizes, colours, fps, limits) |
| `panels.local.json.example` | template for saving your two MACs |

## If something's off
- **scan finds nothing:** panels on? in range? phone app disconnected? Try `python3 scan.py 15`.
- **test_panel says FAILED / no ACK:** wrong MAC, out of range, or the app is still holding the
  panel. Disconnect the app and retry.
- **panel plays but a frame is missing/frozen:** that frame was too colour-heavy — rebuild via
  `assetlib.save_gif()` (or lower the colour count).
- **only one of two panels updates:** push them one at a time, or use `dual_push.py`; the panels are
  independent BLE connections.
