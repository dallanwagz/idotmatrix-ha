# iDotMatrix Panel — Orchestrator Handoff

Everything an orchestrator needs to drive the two 32×32 panels to full capacity: the devices, the
captioned 2,762-asset library, the push scripts, the carousel/12-slot mechanics, and every limit and
gotcha we found by reverse-engineering the hardware. Authoritative protocol detail lives in
[`PROTOCOL.md`](PROTOCOL.md); this doc is the operational summary + recipes.

---

## 1. The hardware — two panels

| name | role | BLE MAC | model | size | firmware |
|---|---|---|---|---|---|
| **IDM-858931** | working unit (in use) | `6F:5D:FE:85:89:31` | iDotMatrix HXS-002 | 32×32 RGB | `TR2306R007` (current) |
| **IDM-D28F7F** | spare | `1F:D6:5C:D2:8F:7F` | iDotMatrix HXS-002 | 32×32 RGB | current (ships pre-updated) |

- **Transport:** BLE GATT. On Linux/HA/ESPHome address by the **MAC** above. (macOS hides MACs and
  uses a per-host CoreBluetooth UUID — not portable; ignore the `0A93…560B` UUID in the scripts.)
- **GATT:** service `0x00FA` → `fa02` write (write + write-without-response), `fa03` notify
  (status/ACK). Service `0xAE00` → JieLi RCSP (device-info/OTA) — **not needed for display.**
- **SoC:** JieLi BLE. **Single central** — keep the vendor app *off* the link while orchestrating.
- Both panels are **32×32**. Use the **32×32** asset library (below). 16×16 / 64×64 assets are
  catalogued for other hardware; resize to 32×32 before pushing to these.

---

## 2. Quick start — push one asset

```bash
# run with a python that has bleak (~/.esphome-venv) + the timebox/pinball driver on path
cd /Users/dallan/repo/idm/tools/etoys_catalog
IDM_ADDR=6F:5D:FE:85:89:31 ~/.esphome-venv/bin/python send_to_panel.py 16736
#                ^ panel MAC                                        ^ file_id OR a path
```
`send_to_panel.py` resolves a bare **file_id** against the catalogs (or takes a GIF/PNG path; PNGs
are auto-wrapped to a 1-frame GIF), stores it to a `count=1` carousel slot, and starts playback —
i.e. a **set-and-forget single animation** that loops untethered. Env: `IDM_ADDR` (MAC),
`IDM_SLOT` (default 0), `IDM_DWELL` (dwell seconds, default 300), `IDM_DRIVER_DIR`.

---

## 3. The asset library — 2,762 captioned assets

Every asset has a vision-generated **name** + **2–3 sentence description**, merged into the index
CSVs. Located under `tools/etoys_catalog/`.

**Use these for the panels (32×32):**

| | daily | holiday | emoji | creative | business | total |
|---|---|---|---|---|---|---|
| animations `library/<cat>/<id>.gif` | 212 | 130 | 163 | 206 | 40 | **751** |
| images `library_images/<cat>/<id>.png` | 105 | 70 | 72 | 74 | 31 | **352** |

Other sizes (catalogued, resize before use on a 32×32 panel): **16×16** = 1,099
(`library_16/`, `library_images_16/`), **64×64** = 560 (`library_64/`, `library_images_64/all/`).

**Index files** (one row per asset): `index.csv` / `index_images.csv` (32×32), `index_16.*`,
`index_64.*`. Columns: `category, file_id, format, width, height, category_name, label, file_path`
(CDN URL), `local` (relative path), **`name`**, **`description`**.

**How to choose an asset by meaning** — grep the index by name/description, take the `file_id`:
```bash
grep -i heart tools/etoys_catalog/index.csv         # -> file_ids of every heart animation
grep -iE "santa|christmas|snow" tools/etoys_catalog/index.csv
# then: send_to_panel.py <file_id>
```
Browse visually: `tools/etoys_catalog/contact_sheets/` (one labeled PNG grid per size·type·category).

---

## 4. Display modes & how to drive them

Frame format on `fa02`: `[len_lo, len_hi, CMD, SUB, *payload]`, `len` = total length LE16, no
checksum. Device ACKs on `fa03` as `[len,0,CMD,SUB,status]` (status 1 or 3 = OK). Builders are in
`timebox/pinball/idm_protocol.py` (`IDM`); panel object via `panel_api.build_panel("idotmatrix32",
MAC, 0, 0)`.

| mode | how | notes |
|---|---|---|
| **Single animation (set-and-forget)** | `send_to_panel.py <id>` → 1-slot carousel, loops on-device | survives disconnect |
| **Show-now (transient)** | `ImageUpload(gif, DataType.GIF, image_index=12, time_sign=0)` | live display, not stored |
| **12-slot carousel** | slot-setup 12 → upload GIFs to slots 0–11 → enter asset view | autonomous loop; see §5 |
| **Long sequential story (>12 scenes)** | ONE long GIF in a `count=1` slot | device loops it in true frame order; see §5 |
| **Clock face** | `cmd 6/1`, `byte[4]=style|0x80(date)|0x40(24h)`, RGB | 8 styles 0–7; see CLOCK-STYLES.md |
| **DIY live pixels** | `enter_diy(1)`=`0500040101`, then `[0x0a,0,5,1,opt,R,G,B,col,row]` | RGB order, per-pixel, no ACK |
| **Rhythm / spectrum** | `cmd 11/0x80` pattern-select + 21-byte spectrum stream ~12 fps | host-streamed, not autonomous |
| **Brightness** | `cmd 4/0x80` | separate from clock/eco |

---

## 5. The carousel — 12 slots (and the "3 pages of 12 = 36" myth)

**The device plays exactly 12 slots (`image_index` 0–11). It is a firmware hard cap.** The app's
"3 pages of 12 = 36" is an *app-side* illusion — pushing any page uploads to indices 0–11 and
**replaces** the 12 on the device. `count` in the slot-setup does **not** extend it (tested
`count=16` → still wraps at slot 11; indices 12–35 ACK but never play).

`image_index` semantics:
- `0`–`11` = persistent carousel **storage slots** (require `DataType.GIF` to stick)
- `12` = **live / show-now** (transient; `timeSign` forced to 0)
- `13` = preview buffer (transient); `14`–`35` = ACK-but-dropped

Control commands:
- **Slot-setup / clear** (⚠️ wipes stored assets): `cmd 2/1`
  - 12 slots: `[17,0,2,1, 12, 0,1,2,3,4,5,6,7,8,9,10,11]`
  - 1 slot: `06 00 02 01 01 00`
- **Start carousel / enter asset view:** `cmd 10/1` = `04000a01`
- **Per-slot dwell:** `timeSign` (bytes[13–14] LE of the GIF upload header) = **seconds**
  (app presets 5 / 10 / 30 / 60 / 300).

**Two ways to fill it** (reference scripts in `timebox/pinball/`):
- **12 distinct loops** → `story_upload.py` pattern: slot-setup(12) → upload 12 GIFs to slots 0–11
  (each with its own `timeSign`) → `enter_asset_view()`. Each slot loops its own GIF for its dwell.
- **One long ordered story** → `combined_upload.py` pattern: slot-setup `count=1` → upload ONE big
  GIF to slot 0 → `enter_asset_view()`. The device plays its frames **1→N in true order** (verified
  with a 360-frame / 36-scene GIF). Use this whenever you want >12 scenes *in sequence* — it
  sidesteps the per-slot dwell/loop that makes a multi-scene GIF read out of order.

**Capacity:** ≥1.3 MB measured into a single slot without `NO_SPACE`; dense frames (~2 KB) → ~650–800
frames ≈ 60–80 s @ 10 fps. So one slot can hold 1–2 min of full-motion 32×32, and the 12-slot set
loops untethered.

---

## 6. Hard limits & gotchas (learned on real hardware)

- **12-slot carousel cap** — see §5. Don't try to address slots ≥12.
- **Frame rate:** uploaded GIFs are capped at **~20 fps** (50 ms/frame floor); full-frame stills
  push at only **~3 fps**; rhythm spectrum ~12 fps.
- **GIF decoder silently skips colour-heavy frames.** A 32×32 frame with a smooth gradient / full
  palette gets dropped (panel freezes/skips that scene). **Keep a handful of solid colours per
  frame, not gradients.** (Relevant if generating content, not for the pre-made library — those are
  already panel-safe.)
- **First frame after a fresh connect can be dropped** — send it twice, or after another command.
- **Inner GATT writes must be ≤256 bytes** even though a 512 MTU negotiates (the receiver silently
  drops larger). The driver already chunks correctly.
- **Pixel data is RGB**, row-major top-to-bottom, 3072 bytes for 32×32; bulk upload uses CRC32.
- **`DataType.IMAGE` (static) only displays at idx 12/13** — it does *not* persist to a slot;
  storage needs an animated **GIF**.

### ⚠️ Don't-do list (bricks / sticky bad states)
- **Never enable the device password** (`cmd 5/2` enable=1) — it **locks the device**.
- **Never leave eco/brightness stickily dimmed** — a low `set_eco`/brightness survives power-cycle
  and looks like a dead panel. Reset brightness explicitly after.
- **Slot-setup / material-wipe destroys stored assets** — only send it when you intend to repaint
  the whole carousel.
- Keep the **vendor app off** these panels (single central; it also force-OTAs older units).

---

## 7. Scripts & driver

All under `/Users/dallan/repo/idm/tools/etoys_catalog/` unless noted. Run with a python that has
**bleak** (`~/.esphome-venv/bin/python`) — the driver lives in `/Users/dallan/repo/timebox/pinball/`.

| script | purpose |
|---|---|
| `send_to_panel.py <id\|path>` | push one asset to a panel (set-and-forget). Env `IDM_ADDR`/`IDM_SLOT`/`IDM_DWELL` |
| `sync.py [--size 16\|32\|64] [--list]` | refresh/expand the library from the cloud; idempotent, downloads only new |
| `contact_sheets.py` | regenerate the labeled browse grids |
| `build_montage.py N [--size S]` | render N un-captioned thumbnails (caption tooling) |
| `etoys_api.py` | reusable Heaton cloud client (sign + AES + deobfuscate) |
| `timebox/pinball/idm_protocol.py` | `IDM` frame/command builders, `ImageUpload`, `DataType`, `enter_asset_view`, `material_wipe` |
| `timebox/pinball/panel_api.py` | `build_panel("idotmatrix32", MAC, 0, 0)` → connect/link object |
| `timebox/pinball/story_upload.py` | reference: fill a 12-slot carousel |
| `timebox/pinball/combined_upload.py` | reference: one long GIF in a `count=1` slot |

**Multi-device:** set `IDM_ADDR` per panel (`6F:5D:FE:85:89:31` or `1F:D6:5C:D2:8F:7F`). One BLE
central per panel at a time.

---

## 8. Recipes (copy-paste)

```bash
cd /Users/dallan/repo/idm/tools/etoys_catalog
PY="~/.esphome-venv/bin/python"; P1=6F:5D:FE:85:89:31; P2=1F:D6:5C:D2:8F:7F

# pick a themed asset by meaning, push to panel 1
fid=$(grep -i pumpkin index.csv | head -1 | cut -d, -f2)
IDM_ADDR=$P1 $PY send_to_panel.py $fid

# different content on each panel
IDM_ADDR=$P1 $PY send_to_panel.py 16736          # purple monster
IDM_ADDR=$P2 $PY send_to_panel.py $(grep -i heart index.csv | head -1 | cut -d, -f2)

# refresh the library (only new assets download)
$PY sync.py --size 32
```
For a **12-slot carousel** or a **36-scene single-GIF story**, follow the `story_upload.py` /
`combined_upload.py` patterns in §5 (slot-setup → upload(s) → `enter_asset_view`).

---

## 9. Machine-readable manifest

`tools/etoys_catalog/panels.json` — panel list (MAC/size/role) + library summary + key constraints,
for programmatic ingestion. See §1 / §3 for the human version.
