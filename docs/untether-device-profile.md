# Device profile: iDotMatrix HXS-002 / NL-XSD-32 (32×32 BLE LED panel)

> Ready to contribute to `github.com/dallanwagz/untether` → `examples/devices/idotmatrix-hxs002.md`.

| | |
|---|---|
| **Vendor / app** | iDotMatrix · `com.tech.idotmatrix` (Play Store v2.1.1) · vendor 佰微/Chengdu |
| **Transport** | **BLE GATT** — confirmed (service 0x00FA, write fa02, notify fa03) |
| **Host** | Native HA via BLE proxy/adapter |
| **Model gating** | One app drives a whole family; this unit = **deviceType 3 / 32×32** |
| **Firmware** | `TR2306R007` (read via JieLi RCSP channel, not a plain GATT char) |

## How transport was confirmed
Decompiled app uses `BluetoothGatt`/`writeCharacteristic` (not RFCOMM); `BleManager`
defines `UUID_WRITE_CHA = 0000fa02-…`. Live `bleak` GATT enumeration on hardware showed
service `0x00FA` (fa02 write / fa03 notify) and a second `0x0AE00` JieLi RCSP service.

## GATT
- Service `000000fa-0000-1000-8000-00805f9b34fb`
  - write `0000fa02-…` (`write` + `write-without-response`)
  - notify `0000fa03-…` (ACK/status)
- Service `0000ae00-…` (`ae01`/`ae02`) = JieLi RCSP (device-info/material sync + OTA).
- Device name `IDM-xxxxxx`; adv mfr id `0x5254`, byte showing deviceType `03`.

## Frame format
`[len_lo, len_hi, CMD, SUB, *payload]`, `len` = total length LE16, **no checksum** on
control frames; bulk media adds CRC32. Device ACKs on fa03: `[len,0,CMD,SUB,status]`,
status 1/3 = ok.

## Command catalog + golden frames (all ✅ on hardware)
```
set_time(2026-06-22 21:22:51)   0b0001801a061601151633
get_device_info()               04000180   (reply 09000180040e010300 -> 03 = 32x32)
brightness(50)                  0500048032
fullscreen_color(255,0,0)       07000202ff0000
clock(0,date,24h,white)         08000601c0ffffff     # flags = style|0x80(date)|0x40(24h)
countdown(start,0,30)           0700088001001e
chronograph(start)              0500098001
scoreboard(258,7)               08000a8002010700      # u16 LITTLE-endian (OSS docs say BE — wrong here)
flip(on/off)                    0500068001 / 0500068000
screen(off/on)                  0500070100 / 0500070101
enter_diy(1)                    0500040101
draw_pixel(255,0,0,8,8)         0a00050100ff00000808  # [len,0,5,1,option,R,G,B,col,row] RGB order
```

## Status / notify
fa03 carries ACKs only — `[len,0,cmd,sub,status]`. **No sensor telemetry, no battery**
(mains-powered). Upload state machine: status 1=next, 2=no-space, 3=done.

## Build snippets (pure protocol)
```python
def frame(cmd, sub, *payload):
    body = bytes(b & 0xFF for b in payload)
    total = 4 + len(body)
    return bytes((total & 0xFF, total >> 8 & 0xFF, cmd & 0xFF, sub & 0xFF)) + body

set_brightness = lambda pct: frame(4, 0x80, max(0, min(100, pct)))
set_fullscreen_color = lambda r, g, b: frame(2, 2, r, g, b)
set_screen = lambda on: frame(7, 1, 1 if on else 0)
draw_pixel = lambda r, g, b, x, y: frame(5, 1, 0, r, g, b, x, y)   # DIY mode first: frame(4,1,1)
```

## Honest gaps / traps
- **Bulk bitmap upload (dataType {2,0}, BGR, CRC32) is decoded but did not render from a
  bare bleak client** (no ACK) — appears **gated on the JieLi-RCSP session** the app
  establishes on connect. Use the DIY pixel path for images until that handshake is RE'd.
- **Two pixel-colour orders:** DIY draw path is **RGB**; bulk image path is **BGR**.
- **Scoreboard is little-endian** on the wire (contradicts OSS docs) — verified on screen.
- Panel **reverts to idle animation on disconnect** → HA must hold a persistent link and
  re-assert state.
- `mic/rhythm/FM` (cmd 0/11) and `joint` (cmd 12) opcodes exist in the app but are for
  **other models** (speakers / multi-panel), not this 32×32.
- Firmware/version + stored-material live behind the **JieLi RCSP** sub-protocol, not the
  display service.

## Operator-in-the-loop notes
Every command above was visually confirmed on the panel (colour fills, clock digits,
countdown ticking, scoreboard digits, flip, blank/on). The scoreboard endianness and the
two pixel-colour orders were resolved specifically by reading the panel back.
