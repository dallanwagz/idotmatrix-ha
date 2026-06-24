# iDotMatrix BLE protocol — HXS-002 / NL-XSD-32 (32×32)

Reverse-engineered from the official Android app `com.tech.idotmatrix` **v2.1.1**
(decompiled, unpacked Play Store build) and **validated byte-for-byte on real
hardware** (panel `IDM-858931`, firmware `TR2306R007`) via HCI snoop + live `bleak`
control with operator visual confirmation. Cross-checked against the open-source
`derkalle4/python-idotmatrix-library` and `8none1/idotmatrix`.

Legend: ✅ = confirmed on this hardware · 📖 = from source/OSS, not yet hardware-tested.

## Transport & GATT

- **BLE GATT**, no bonding (just-works, no pairing). Device name starts `IDM-`.
- Advertised manufacturer data: company id `0x5254` ("TR"), bytes `00 70 03 …` where
  the **`03` = deviceType 3 = 32×32**.
- **Service `0x00FA`** (`000000fa-0000-1000-8000-00805f9b34fb`):
  - **Write** `0000fa02-…` — `write` + `write-without-response` (handle 5 here). ✅
  - **Notify** `0000fa03-…` — status/ACK stream (handle 8). ✅
- **Service `0xAE00`**: `ae01` write / `ae02` notify — a **second, JieLi (杰理) RCSP**
  sub-protocol (frames `fe dc ba … ef`) used on connect for device-info/material sync
  and OTA. Firmware version (`TR2306R007`) is read here, not via a plain GATT char. Not
  needed for display control. ✅ (observed)

## Control-frame format

```
[len_lo, len_hi, CMD, SUB, *payload]
```
- `len` = **total** frame length (incl. the 2 length bytes), little-endian uint16.
- **No checksum** on control frames. (CRC32 only on bulk media — see below.)
- The device **ACKs** most commands on fa03 with `[len, 0, CMD, SUB, status]`,
  `status` 1 or 3 = success. ✅

## Command catalog

All validated on the 32×32 unless marked. CMD/SUB are bytes [2]/[3]; `0x80`=128.

| Command | CMD | SUB | Payload | Example frame | ✓ |
|---|---|---|---|---|---|
| Sync time | 1 | 0x80 | `yy-2000, mo, dd, dow(1=Mon), hh, mm, ss` | `0b0001801a061601151633` | ✅ |
| Device-info query | 1 | 0x80 | *(none)* | `0400 0180` | ✅ (reply `09000180040e010300`, `03`=32×32) |
| Brightness 0-100 | 4 | 0x80 | `pct` | `0500048032` (50%) | ✅ |
| Fullscreen RGB | 2 | 2 | `r, g, b` | `07000202ff0000` (red) | ✅ |
| Lighting effect (MutilColor) | 3 | 2 | `model, speed, count, rgb…` | `1c000302005a07…` | ✅ (see MODE tab) |
| Clock | 6 | 1 | `style\|0x80(date)\|0x40(24h), r, g, b` | `08000601c0ffffff` | ✅ |
| Countdown | 8 | 0x80 | `mode(0-3), min, sec` | `0700088001001e` (start 0:30) | ✅ |
| Stopwatch | 9 | 0x80 | `mode(0-3)` | `0500098001` (start) | ✅ |
| Scoreboard | 10 | 0x80 | `c1(u16 LE), c2(u16 LE)` | `08000a8002010700` (258:7) | ✅ **LE confirmed** |
| Flip 180° | 6 | 0x80 | `0/1` | `0500068001` | ✅ |
| Screen on/off | 7 | 1 | `0/1` | `0500070100` (off) | ✅ |
| Time-indicator | 7 | 0x80 | `0/1` | `0500078001` | 📖 |
| Eco/sleep sched | 2 | 0x80 | `flag, startH,startM, endH,endM, light` | `0a000280010000173b08` | ✅ (dims; sticky — see gotcha) |
| Screen-on timer | 15 | 0x80 | `value` (`0xFF`=query) | `0500078f…` | 📖 (read is SILENT) |
| Text speed | 3 | 1 | `speed` | `0500030105` | 📖 |
| Reset | 3 | 0x80 | *(none)* | `04000380` | 📖 |
| Enter/exit DIY | 4 | 1 | `mode(0-3)` | `0500040101` (enter+clear) | ✅ |
| Password set | 4 | 2 | `enable, dd1,dd2,dd3` (6 digits→3 pairs) | `0800040201` `0c2238` | ✅ (verify→01 ok/00 wrong) |
| Password verify | 5 | 2 | `dd1,dd2,dd3` | `070005020c2238` | ✅ |
| Rhythm pattern-select | 11 | 0x80 | `mode+1, sensitivity` | `06000b800164` | ✅ (see Rhythm section) |
| Rhythm stop | 0 | 2 | `0,0` | `060000020000` | ✅ |
| Material-wipe (carousel page) | 2 | 1 | `12, 0..11` | `110002010c000102030405060708090a0b` | ✅ ⚠️ destroys stored assets |
| Enter asset/carousel view | 10 | 1 | *(none)* | `04000a01` | ✅ (see Carousel section) |
| Joint (multi-panel) | 12 | 0x80 | `mode` | — | n/a (not 32×32) |
| OTA | type | 0x80 | `pkgCount, CRC32(4), binSize(4)` | — | 📖 (don't blind-fire) |

`mode` enums: Countdown/Stopwatch `0=disable/reset,1=start,2=pause,3=restart/continue`.
DIY fun `0=quit-nosave,1=enter+clear,2=quit-still,3=enter-noclear`.

### Clock faces (`cmd 6/1`) — full sweep confirmed ✅

`sendClockMode(style, showDate, hour24, r, g, b)` →
`[8,0, 6,1, style | (0x80 if date) | (0x40 if 24h), r, g, b]`.

- **8 styles** `0–7` in the low bits of byte[4] (the 32×32 set). Captured swiping the preview:
  `42→43→44→45→46→47→40→41` = styles 2,3,4,5,6,7,0,1.
- **`0x80` = show date**, **`0x40` = 24-hour** — each verified by toggling: `0x41`↔`0x01` (24h),
  `0x01`↔`0x81` (date).
- **bytes[5–7] = RGB**, set by the colour picker (captured `…81ffd981`, `…81b6ffff`, `…81ff5a7f`).
- Each style ships a **default colour** (`default16x16TimeColor`): 0=`(97,24,214)` 1=`(229,12,23)`
  2=`(255,152,43)` 3=`(19,67,248)` 4=`(106,39,248)` 5=`(255,146,42)` 6=`(255,15,77)` 7=`(67,250,85)`.
- **"Intensity" is the separate `set_brightness` (`cmd 4/0x80`)** — NOT part of the clock frame.
- **What each style looks like** (photographed on-device, `style N` == app preview `#(N+1)`):
  0=rainbow border, 1=Christmas tree, 2=checkered bands, 3=filled/inverted, 4=hourglass,
  5=alarm-clock frame, 6=blue gradient border, 7=corner-gradient border. Full photo gallery:
  [CLOCK-STYLES.md](CLOCK-STYLES.md). ⚠️ A `set_clock` as the *first* frame after a fresh connect
  can be dropped — send it twice or after another command.

## DIY pixel draw (live graffiti) ✅

Enter DIY mode first (`enter_diy(1)` = `0500040101`), then per pixel:

```
[0x0a,0, 5,1, option, R, G, B, col, row]     # RGB order, no CRC, no ACK
```
Captured golden frame: `0a00050100ff00000808` = red pixel at (col 8, row 8). ✅
`option` = move/effect (0=none). Same-colour multi-pixel variant appends more
`col,row` pairs after one `R,G,B`. **Colour order is RGB** (same as the bulk image path).

## Bulk image upload ✅ — fully working (no session handshake needed)

Two-level chunked transport with CRC32 (class `ImageUpload` in `protocol.py`):

1. Split the raster into **4096-byte** outer packets; prepend a **16-byte header**:
   `[len(2 LE)=chunk+16, 2, 0, option(0 first/2 rest), totalLen(4 LE), CRC32(4 LE),
   timeSign(2 LE; 0 when image_index==12), image_index(1)]`. Use **`image_index=12`**
   for a "show now, no schedule" image (forces `timeSign=0`).
2. Split each outer packet into inner GATT writes and write them to fa02
   (write-without-response), ~20 ms apart. After the last inner write of an outer
   packet, **wait for the fa03 ACK**: status `1`=send next packet, `3`=done, `2`=no-space.
- **Pixel data is RGB**, row-major top-to-bottom, 3 bytes/pixel → **3072 bytes for
  32×32**. (The app's `bitmap2BGR` is misleadingly named: Android `copyPixelsToBuffer`
  yields little-endian BGRA and that function reverses it back to **RGB**.) CRC32 is
  standard `zlib.crc32` over the whole buffer.
- **Inner-write size matters (hardware finding):** the panel's fa02 receiver **silently
  drops GATT writes larger than ~256 bytes**, even though a 512 MTU is negotiated. The
  Android app gets away with 509-byte writes because Android fragments them transparently;
  other stacks (e.g. macOS CoreBluetooth) send the whole value and the device ignores it.
  **Cap inner writes at ≤256 bytes** (`protocol.SAFE_WRITE_LEN = 244`). This — not any
  RCSP session — was why a naive 509-byte-chunk upload got no ACK. A 32×32 RGB frame
  (3072 B → one 4 KiB packet → ~13×244 writes) uploads and ACKs `[05,00,02,00,03]`,
  **confirmed rendering on hardware** (4-colour quadrants + a red-X test). GIF/text use
  the same transport with a different header byte[2] (gif=1) / glyph payload.

## Inbound notify / ACK (fa03) ✅

`[len, 0, CMD, SUB, status, …]`. For uploads the state machine keys on `value[2]`
(dataType) and `value[4]` (status): `1`=next, `2`=no-space, `3`=finished. Simple
commands echo their CMD/SUB with status 1. No battery/sensor telemetry is reported.

## Model gating (this device = deviceType 3, 32×32)

LED-size map: `1=16×16, 2=8×32, 3=32×32, 4=64×64, 6=24×48, 7=16×32, 11=16×64`.
Valid for 32×32: all of the above except **joint** (multi-panel). The 32×32 **DOES** support
the mic/**rhythm** visualizers (`RhythmLedView32x32`) — see the Rhythm section. Text rendering
uses the 16-tall font path (the 12-px path is only `ledType==2`/8×32).

## Gotchas (state-changing commands that stick) ⚠️
- **`set_eco` dims persistently.** Eco's `light` byte sets a dimmed brightness for the
  window; it's a saved device setting that **survives a power-cycle** and overrides
  `set_brightness`. A software "off" (`flag=0`) may not fully restore it — clearing it
  reliably needed a power-cycle. Avoid eco in any automated/test path, or always restore.
- **`set_password` with `enable=1` locks the device** (the app then prompts for it). Sent
  over plain BLE; disable with `set_password(pwd, enable=0)`. Don't fire it casually.

## Golden frames (regression anchors)

```
set_time(2026-06-22 21:22:51)      0b0001801a061601151633   ✅ captured
get_device_info()                  04000180                 ✅ (reply 09000180040e010300)
set_brightness(50)                 0500048032               ✅
set_fullscreen_color(255,0,0)      07000202ff0000           ✅
set_clock(0,date,24h,white)        08000601c0ffffff         ✅
set_countdown(START,0,30)          0700088001001e           ✅
set_chronograph(START)             0500098001               ✅
set_scoreboard(258,7)              08000a8002010700         ✅ (LE)
set_flip(True/False)               0500068001 / 0500068000  ✅
set_screen(False/True)             0500070100 / 0500070101  ✅
enter_diy(1)                       0500040101               ✅
draw_pixel(255,0,0,8,8)            0a00050100ff00000808     ✅ captured
```

## Rhythm / sound-reactive spectrum ✅ (plaintext path)

The mic/rhythm visualizers. The phone does the FFT and **streams** to the panel; the
panel renders a built-in pattern. RE'd from live captures + driven from our client.

**Two parts:**
1. **Pattern select** — `sendMicCommand1`, CMD 11 / SUB 0x80:
   `[06,00,0b,80, mode+1, sensitivity]` (`sensitivity` 0-100). `mode` picks the device-side
   render pattern (bars / lightbulb / tree / …) — captured `06000b800164` (mode 0) and
   `06000b800564` (mode 4). **Stop:** `sendStopMicRhythm` CMD 0/2 = `060000020000`.
2. **Spectrum stream** — a RAW 21-byte frame (no envelope/CRC), ~**12 fps**:
   `21 00 01 02 02 | <16 band heights>` — the 16 are **8 bands mirrored left-right**
   (`right = reverse(left)`), so the bars are symmetric. ✅ golden frame from 8 bands
   `[0a,05,04,02,02,04,02,02]` → `2100010202 0a05040202040202 02020402020405 0a`.

**Modes/limits:**
- The **bars/lightbulb/etc. patterns are PLAINTEXT** and fully replicable — only the mode
  byte in `sendMicCommand1` differs between them; the 21-byte data frame format is identical.
  We drive them from a host (`rhythm_select` + `rhythm_frame`) — verified on-device (synthetic
  bars + a file-FFT visualizer both track the audio).
- The **fancier image-based visualizer modes** render frames on the phone and send them as
  GIF/image uploads + an **AES-encrypted** `sendRhythmData` path (`csh.tiro.cc.aes`, the same
  native cipher that walls off `LOCATE`/material-wipe) — NOT replicable.
- It is **not autonomous**: even the "device-mic" pattern still streams from the phone at ~12 fps.

This makes the panel viable as a **live audio visualizer** from a Python/HA host (FFT → 8 bands →
`rhythm_frame` at 12 fps) — and unlike full-frame stills, it's not gated by the ~3 fps image ceiling.

## Device carousel / on-device asset storage ✅

The panel **persistently carousels 12 slots** (`image_index` 0–11) and **cycles them
autonomously** — no host needed, survives disconnect. This is the "Device Assets" feature.
RE'd + driven from our own client (verified: 12-scene story loops on its own).

⚠️ **The device holds 12, not 36.** The app shows "3 pages of 12 = 36," but those are
**app-side** sets: a "push page" always uploads to `image_index` 0–11 (`curIndex` increments
0,1,2,… *per push*, `DeviceMaterialChildFragment.sendData`), so pushing any page **replaces** the
12 on the device. Uploading to index 14–35 ACKs but never enters the carousel.

**Store an asset to a slot** — reuse the bulk **GIF** upload (`DataType.GIF`, dtype byte[2]=1)
with two header fields:
- **`image_index` (byte[15]) = the slot number 0–11.**
- **`timeSign` (bytes[13–14], LE) = the per-asset carousel dwell time in *seconds*.**

`image_index` semantics (corrects the bulk-image note above):
| value | meaning |
|---|---|
| `0`–`11` | carousel **storage slot** — requires `DataType.GIF` to actually persist |
| `12` | **live / show-now** (transient display; `timeSign` forced to 0) — what a plain push uses |
| `13` | **preview / "currently showing"** buffer (transient) |
| `14`–`35` | not a playable carousel slot (ACKs but is dropped) |

A **static image (`DataType.IMAGE`) at idx 12/13 only displays** — it does not enter the
carousel. Storage needs an animated GIF at a slot index. Each upload ACKs the GIF state
machine (`0500010001`=next / `0500010003`=done).

**Control:**
- **Slot-setup / clear** (slots 0–11): `cmd 2/1` = `[17,0,2,1, 12, 0,1,2,3,4,5,6,7,8,9,10,11]`
  (`Agreement.getDeleteMaterial`). Sent once before a push — ⚠️ destroys stored assets.
- **Start the carousel / enter asset view:** `cmd 10/1` = `04000a01`.
- Slots fill in arrival order after the slot-setup; per-slot dwell is each asset's `timeSign`.

**Why this matters:** it's the true **set-and-forget** mode — preload 12 animations and
the panel loops them itself, unlike rhythm (streamed) or stills (host-driven). Builders:
`material_wipe()`, `enter_asset_view()`, and `ImageUpload(gif, DataType.GIF, image_index=slot,
time_sign=dwell)`.

## MODE tab — Lighting / Lighting-Effects / Assets (full UI map)

Static-decoded from the app + on-device confirmation. Every tunable knob on the four MODE
sub-tabs maps to these frames.

### Lighting sub-tab
Just two opcodes — there is no distinct "lamp" command:
- **Brightness** → `set_brightness` `cmd 4/0x80 [pct]` (UI range 5–100).
- **Any colour, the 7 presets, and the 3 whites** → `set_fullscreen_color` `cmd 2/2 [r,g,b]`.
  - 7 presets: red `FF0000` · orange `FFA200` · yellow `FFFF00` · green `00FF00` · blue `0000FF`
    · pink `FF00FF` · white `FFFFFF`.
  - 3 whites: warm `F88D1E` · cool `FFD5FF` · night-light `FF996B`.

### Lighting-Effects sub-tab ✅ (`set_effect`, cmd 3/2)
```
[len, 0, 3, 2, model, speed, count, r0,g0,b0, r1,g1,b1, …]      len = count*3 + 7
```
- **`model`** = the scene/style **0–6** (the 7 swipe modes).
- **`speed`** = byte[5], **0–100** (the lightning-bolt slider).
- **`count`** + that many **RGB** triplets (the editable swatch list, 4–8 colours).
- Each channel is **value-`1`→`0`** remapped (1 is reserved) then scaled by **`saturation/100`**.
- Brightness here is the same `cmd 4/0x80`. Confirmed on-device (animated multi-colour effect;
  ack `0500030201`). Golden: `set_effect(0,90,<7 rainbow>)` = `1c000302005a07ff0000ffa200ffff0000ff000000ffff00ffffffff`.
  (The community RE's "len 6+count" layout is wrong — this is byte-for-byte from the app builder.)

### Device-Assets sub-tab (carousel)
Store = GIF upload (`DataType.GIF`) with `image_index`=slot **0–11**, `timeSign`=dwell. The `+`
boxes are empty slots; the down-arrow pushes the page. **The device carousels 12 slots** — the
app's "3 pages" are swappable app-side sets, each push replaces the on-device 12 (see Device-carousel
section). **Carousel interval → `timeSign` seconds:**
| UI | 5s | 10s | 30s | 1min | 5min |
|---|---|---|---|---|---|
| seconds | 5 | 10 | 30 | 60 | 300 |

(byte order of `timeSign` is settled little-endian for our builder; only the 5-min=300 case has a
non-zero high byte — re-confirm on-wire if it ever misbehaves. The app sends a `cmd 2/1` slot-setup
frame — `material_wipe()` — before a multi-slot/page download; our multi-packet uploads need it too.)

### My-Assets sub-tab
A **local SQLite** library of saved items (`type` 0=PNG/img, 1=GIF, 2=text, 3=effect, 4=colour).
Selecting one just **re-sends its original opcode** (GIF→`cmd 1/0`, effect→`cmd 3/2`,
colour→`cmd 2/2`, …) — **no new commands**.

### Max animation size (per-slot storage) — MEASURED
There is **no app-side size/frame/length limit** — the app streams the whole GIF and lets the
**device firmware** reject overflow (the "insufficient space" NAK = `NO_SPACE`, byte[4]==2).
Empirically, a single slot **accepted ≥1.3 MB and never returned `NO_SPACE`** (the uploads ended on
BLE drops over multi-minute transfers, not a device limit). Practical guidance at 32×32:
- dense/noisy frames (~2 KB/frame): **~650–800 frames** (≈60–80 s @ 10 fps);
- typical 256-colour content (~300–600 B/frame): **thousands of frames** (many minutes).
- Storage is **not** the bottleneck — BLE upload time/reliability and the device's playback decode
  are. The carousel is **12 slots** (≥1.3 MB measured into one), so a single animation can run
  **1–2 min of full-motion 32×32 GIF**, and the full 12-slot set loops untethered.
