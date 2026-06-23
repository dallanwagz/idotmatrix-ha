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
| Clock | 6 | 1 | `style\|0x80(date)\|0x40(24h), r, g, b` | `08000601c0ffffff` | ✅ |
| Countdown | 8 | 0x80 | `mode(0-3), min, sec` | `0700088001001e` (start 0:30) | ✅ |
| Stopwatch | 9 | 0x80 | `mode(0-3)` | `0500098001` (start) | ✅ |
| Scoreboard | 10 | 0x80 | `c1(u16 LE), c2(u16 LE)` | `08000a8002010700` (258:7) | ✅ **LE confirmed** |
| Flip 180° | 6 | 0x80 | `0/1` | `0500068001` | ✅ |
| Screen on/off | 7 | 1 | `0/1` | `0500070100` (off) | ✅ |
| Time-indicator | 7 | 0x80 | `0/1` | `0500078001` | 📖 |
| Eco/sleep sched | 2 | 0x80 | `onH,onM,offH,offM,e5,e6` | — | 📖 |
| Screen-on timer | 15 | 0x80 | `value` (`0xFF`=query) | `0500078f…` | 📖 |
| Text speed | 3 | 1 | `speed` | `0500030105` | 📖 |
| Reset | 3 | 0x80 | *(none)* | `04000380` | 📖 |
| Enter/exit DIY | 4 | 1 | `mode(0-3)` | `0500040101` (enter+clear) | ✅ |
| Password set/verify | 4/5 | 2 | `…` | — | 📖 |
| Joint (multi-panel) | 12 | 0x80 | `mode` | — | n/a (not 32×32) |
| Mic/rhythm/FM | 0/11 | 2/0x80 | `…` | — | n/a (speaker models) |
| OTA | type | 0x80 | `pkgCount, CRC32(4), binSize(4)` | — | 📖 (don't blind-fire) |

`mode` enums: Countdown/Stopwatch `0=disable/reset,1=start,2=pause,3=restart/continue`.
DIY fun `0=quit-nosave,1=enter+clear,2=quit-still,3=enter-noclear`.

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
Valid for 32×32: all of the above except **joint** (multi-panel) and **mic/rhythm/FM**
(speaker models, gated by adv `isNewDeviceRhythm`). Text rendering uses the 16-tall font
path (the 12-px path is only `ledType==2`/8×32).

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
