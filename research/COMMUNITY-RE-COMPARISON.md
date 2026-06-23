# Community iDotMatrix RE — Comparison vs. OUR work (ground truth: decompiled official app v2.1.1)

This document compares community reverse-engineering repos of the iDotMatrix
protocol against **our** canonical RE, resolving every disagreement against the
**decompiled official Android app** (`com.tech.idotmatrix` v2.1.1), which is
ground truth.

Our canonical sources:
- `/Users/dallan/repo/idm/custom_components/idotmatrix/protocol.py`
- `/Users/dallan/repo/idm/docs/PROTOCOL.md`
- `/Users/dallan/repo/timebox/pinball/idm_protocol.py` (vendored copy; adds `DataType.TEXT=3`)
- `/Users/dallan/repo/timebox/pinball/panel_idotmatrix.py` (driver + measured PanelSpec)

Ground truth (decompiled):
- `/Users/dallan/repo/idm/decompiled/playstore/sources/com/tech/idotmatrix/`
  esp. `ble/BleProtocolN.java`, `core/data/{TextAgreement,GifAgreement,ImageAgreement}.java`

Tag legend per claim:
- **[Verified-against-decompile]** — confirmed in the decompiled app source (cited file:line).
- **[Verified-on-our-hardware]** — confirmed by our own HCI snoop / live `bleak` test (per docs/PROTOCOL.md).
- **[Unconfirmed]** — plausible but not yet checked against decompile or hardware.

The structure below is extensible: each repo gets its own `## Repo N` section with
four subsections (a) WE MISSED, (b) we got RIGHT, (c) DISAGREEMENTS/WRONG,
(d) IMPROVEMENTS. A final `## Synthesis` section is appended after all repos.

---

## Repo 1 — 8none1/idotmatrix

**URL:** https://github.com/8none1/idotmatrix
**Cloned to:** `/Users/dallan/repo/idm/research/community/8none1-idotmatrix`
**Nature:** This is the author's *original exploratory* repo (a single
`idotmatrix_controller.py` driver plus hand-written `decoding_bytes.md` /
`readme.md` byte-layout notes and btsnoop captures). It is NOT the later
polished `python-idotmatrix-library`; it's the raw RE notebook. It targets a
32×32 device only and uses `simplepyble`. It implements: on/off, time sync,
graffiti (single-pixel DIY draw), scrolling **text** (full builder), and **GIF**
upload. No clock/countdown/chronograph/scoreboard/brightness/fullscreen-color.

Key files read:
- `idotmatrix_controller.py` — driver + `build_string_packet`, `string_to_bitmaps`, `build_gif_packet`, `generate_gif_payload`, `graffiti_paint`, `sync_time`, `switch_on`, `send_reset_command`.
- `decoding_bytes.md`, `readme.md` — byte-layout annotations for text + GIF headers.

---

### (a) What WE MISSED

**A1. A complete scrolling-TEXT builder. [Verified-against-decompile]**
This is the biggest gap. Our `protocol.py` has only `set_text_speed()` (CMD 3/1)
— it has **no text-rendering path at all**. 8none1 has a full one
(`idotmatrix_controller.py:120-189` `string_to_bitmaps` + `build_string_packet`).
And the decompiled `TextAgreement.java` confirms the exact wire format, so we can
add a correct, ground-truth text builder.

Ground-truth text frame (from `TextAgreement.java`, the 16-tall path our 32×32 uses):

Outer 4 KiB packet header (16 bytes), `sendTextTo1616(...,String,...)` build at
`TextAgreement.java:692-707`:
```
[len_lo, len_hi,            # short2Bytes((chunk+16)) placed [1],[0] => LE total of this packet
 0x03, 0x00,                # bArr5[2]=3, bArr5[3]=0   (dataType = TEXT)
 option,                    # bArr5[4] = 0 first packet, 2 for continuation
 plen0,plen1,plen2,plen3,   # bArr5[5..8] = int2byte(i7) = length of (text-meta + glyphs), LE
 crc0,crc1,crc2,crc3,       # bArr5[9..12] = CRC32 of (text-meta + glyphs), LE
 ts_lo, ts_hi,              # bArr5[13..14] timeSign (0,0 when imageIndex==12)
 image_index]               # bArr5[15] = 12 (0x0c) for "show now"
```
Then the **text-metadata header (14 bytes)** prepended to the glyph stream
(`sendTextTo1616(...,String,...)` build at `TextAgreement.java:660-677`):
```
[numchars_lo, numchars_hi,  # bArr3[0]=short2Bytes(nChars)[1], bArr3[1]=[0]  => LE
 0x01, 0x01,                # bArr3[2]=1, bArr3[3]=1  (this is the 16x16 path)
 text_mode,                 # bArr3[4]
 speed,                     # bArr3[5]
 text_color_mode,           # bArr3[6]
 r, g, b,                   # bArr3[7..9]   (NB: blue forced to 1 if color==(0,0,0))
 bg_mode,                   # bArr3[10]
 bg_r, bg_g, bg_b]          # bArr3[11..13]
```
Then per glyph: `[fontsize_marker, 0xFF, 0xFF, 0xFF, <bitmap bytes>]` where the
marker is **2** if the glyph bitmap is 16 bytes (8px wide) or **3** if 32 bytes
(16px wide) — `TextAgreement.java:636-647`. 8none1 hardcodes `05ffffff` as the
marker, which is the **32-tall / 64px** path (see A1-note).

> **A1-note (font height):** 8none1's `string_to_bitmaps` renders **16×32**
> glyphs and emits marker `05` (their readme says "05 = size 32"). The decompiled
> app has **three** text paths — `sendTextTo1616` (markers 2/3, 16-tall),
> `sendTextTo1664` (`bArr3[2]=0, bArr3[3]=1`), and `sendTextTo3232` — selected by
> `ledType`. For our 32×32 device the app actually calls the **16-tall** path
> (`sendTextTo1616`, metadata `[..,1,1,..]`, glyph markers 2/3), not 8none1's
> 32-tall marker `05`. So if we implement text we should follow the decompile's
> 16-tall layout, not 8none1's. **[Verified-against-decompile]** (`TextAgreement.java:309-725`)

**A2. A GIF-upload builder. [Verified-against-decompile]**
We have a still-image uploader (`ImageUpload`) but **no GIF path**. 8none1 has
`build_gif_packet` / `generate_gif_payload` (`idotmatrix_controller.py:197-247`).
The decompiled `GifAgreement.java:309-340` confirms the GIF outer header is
identical in shape to our image header but with **dataType byte[2]=1, byte[3]=0**
and **image_index byte[15] commonly = 0x0d (13)** for a GIF "show now". The whole
raw `.gif` file bytes (must be 32×32) are the payload, CRC32 over the whole file,
split into 4096-byte outer chunks each with a 16-byte header. We already have
`DataType.GIF = 1`; we just never wired an upload helper for it.

GIF outer header (`GifAgreement.java:311-339`):
```
[len_lo, len_hi, 0x01, 0x00, option(0/2),
 totalLen(4 LE), crc32(4 LE), timeSign(2 LE), image_index]
```
Identical to our `ImageUpload.outer_packets()` except `dtype0=1`. **Our existing
`image_rgb`/`ImageUpload(data, DataType.GIF)` already produces this** — we just
need a convenience `gif(raw_gif_bytes)` wrapper and to document that the payload
is the literal `.gif` file (not raster RGB).

**A3. The DIY-animation header is only 9 bytes, not 16. [Verified-against-decompile]**
`ImageAgreement.sendDIYImageData` (`ImageAgreement.java:301-344`) uses a **9-byte**
header: `[len_lo,len_hi, 0x00,0x00, option, totalLen(4 LE)]` — **no CRC, no
timeSign, no image_index**. Our `DataType.ANIM = 0` is documented but our
`ImageUpload.outer_packets()` always emits the **16-byte** header. For DIY-anim
uploads the app uses the shorter 9-byte header and the ACK keys on
`byte[2]==0` (`parseDiyDataNextPackage`: `bArr[2]==0 && bArr[4]==2`,
`ImageAgreement.java:281-283`). We have neither the 9-byte header nor the diy-ACK
parsing. (8none1 doesn't implement this either, but it's a real app feature.)

**A4. Text-mode / color-mode catalog. [Unconfirmed]**
8none1's `readme.md:128-162` enumerates **text modes 0-8** (0 fixed, 1 L→R, 2 R→L,
3 up, 4 down, 5 strobe, 6 fade, 7 falling blocks, 8 laser), **color modes 0-5**
(1 fixed, 2 blue→red gradient, 3 pastel, 4 pink→orange), and **bg modes** (0 off,
1 solid). These map directly to `text_mode`/`text_color_mode`/`bg_mode` bytes in
the metadata header. Our docs have none of this. Worth capturing as capability
notes (8none1 observed these on hardware, not from decompile).

**A5. `sendImageRhythm` / mic CMD detail. [Verified-against-decompile]**
Minor: the rhythm/mic "image rhythm" command is `{6,0,0,2,(byte)mode,1}`
(`BleProtocolN.java:81-83`) and stop is `{6,0,0,2,0,0}` (`:103-105`). We only note
"Mic/rhythm/FM — n/a (speaker models)". Not needed for our panel; noting for
completeness.

---

### (b) What we got RIGHT (independently confirmed by 8none1)

- **GATT UUIDs & service.** 8none1 uses the exact same `000000fa` service,
  `0000fa02` write, `0000fa03` notify (`idotmatrix_controller.py:17-19`). Matches
  our `protocol.py:43-45`. **[Verified-on-our-hardware]**
- **Name prefix `IDM-`.** `idotmatrix_controller.py:297,312`. Matches
  `protocol.py:48`. **[Verified-on-our-hardware]**
- **Frame format `[len_lo, len_hi, CMD, SUB, *payload]`, LE total length, no
  checksum on control frames.** Every 8none1 control packet follows this
  (e.g. `05 00 07 01 01`). Matches `protocol.py:113-120`. **[Verified-against-decompile]**
- **Screen on/off = CMD 7 / SUB 1, `0/1`.** 8none1 `switch_on`
  (`:112-118`) `05 00 07 01 01`. Matches our `set_screen` and
  `BleProtocolN.sendSwitchplate` `{5,0,7,1,...}` (`:107-109`). **[Verified-on-our-hardware]**
- **Time sync = CMD 1 / SUB 0x80, payload `yy-2000?, mo, dd, dow(1=Mon..7=Sun),
  hh, mm, ss`.** 8none1 `sync_time` (`:82-102`) and `synchronizedTime`
  (`BleProtocolN.java:170-175`) match our `set_time` (`protocol.py:128-136`),
  including weekday 1-7. **[Verified-on-our-hardware]** (golden `0b0001801a061601151633`)
- **Reset = CMD 3 / SUB 0x80, then brightness `04 00 03 80` / `05 00 04 80 50`.**
  8none1 `send_reset_command` (`:105-110`) matches our `reset_device` note "App
  follows with brightness 0x50" (`protocol.py:232-234`). **[Verified-against-decompile]**
  (`BleProtocolN.restDevice :63-66`)
- **Graffiti single-pixel DIY draw = `0a 00 05 01 00 R G B X Y`, colour RGB,
  no CRC, no ACK.** 8none1 `graffiti_paint` (`:55-80`) is byte-identical to our
  `draw_pixel` (`protocol.py:242-250`) and our golden frame
  `0a00050100ff00000808`. **Independently confirms RGB (not BGR) order** and the
  X=col, Y=row mapping. **[Verified-on-our-hardware]**
- **Bulk transport: 4096-byte outer chunks, 16-byte header, CRC32 (zlib) over the
  whole payload (LE on wire), `option`=0 first / 2 continuation, ACK between
  chunks.** 8none1 `build_gif_packet` (`:212-247`) and `build_string_packet`
  (`:150-189`) match our `ImageUpload.outer_packets()` (`protocol.py:313-330`) and
  `ImageAgreement/GifAgreement` ground truth. **[Verified-against-decompile + on-our-hardware]**
- **Upload ACK semantics: `…01`=send next, `…02`=no space, `…03`=finished.**
  8none1's readme (`:170-171`) notes `0500010001` (next) / `0500010003` (done) for
  GIF. Matches our `Ack` enum (`protocol.py:347-352`) and `parseData*`
  (`GifAgreement.java:257-274`). **[Verified-against-decompile]**
- **image_index `12` => timeSign forced to (0,0).** 8none1's note "if thing is 12
  then 00,00" (`decoding_bytes.md:16`, `readme.md:87`) matches our
  `image_index=12` default (`protocol.py:310,316`) and the app's `if (i==12){
  bArr3[13]=0; bArr3[14]=0; }` (`ImageAgreement.java:381-388`,
  `GifAgreement.java:330-337`). **[Verified-against-decompile]**
- **509-byte vs 18-byte inner write (MTU-gated).** 8none1 doesn't split inner
  writes (relies on `simplepyble` / the GIF being small), but the decompiled
  `getSendData` `int i = isMtuStatus() ? 509 : 18` (`ImageAgreement.java:203`,
  `GifAgreement.java:208`, `TextAgreement.java:187`) confirms our
  `INNER_MTU_HIGH=509 / INNER_MTU_LOW=18` constants (`protocol.py:258-259`). **[Verified-against-decompile]**

---

### (c) Disagreements / WRONG (with ground-truth verdict)

**C1. GIF "total length" field — 8none1 computes it wrong. [Verified-against-decompile]**
8none1 `build_gif_packet` (`:221-226`) sets the total-length field to
`len(gif_payload) + (len(header) * 2)` (i.e. payload + 32). Ground truth
(`GifAgreement.java:304`, `bArrInt2byte2 = int2byte(bArr.length)`) is **just the
raw payload length** — the header bytes are NOT counted. 8none1's own
`decoding_bytes.md:218-227` actually annotates this field correctly as "total
payload **inc headers** over all chunks", but they were guessing — and even the
field name disagrees with their code. **Verdict: the app uses the bare
`bArr.length` (payload only, no header).** Our `ImageUpload` uses
`struct.pack("<I", total)` with `total = len(self.data)` (`protocol.py:316,324`),
i.e. payload only — **OUR code matches ground truth; 8none1 is wrong by +32.**
(8none1's GIF may still render because the device appears to read until CRC/EOF,
but the field is incorrect.)

**C2. Text packet-length field — 8none1 has a comment-vs-code mismatch. [Verified-against-decompile]**
8none1 `build_string_packet` (`:178-182`) sets the length field to
`len(packet)` = (text-meta header + glyphs), which **matches** ground truth
(`int2byte(i7)` where `i7 = size+14`, `TextAgreement.java:680,697-700`). So
8none1's *text* length is right (unlike its *GIF* length, C1). No disagreement
with us — we have no text path to disagree. Listed only to flag the inconsistency
between 8none1's two builders.

**C3. Text-metadata `[2],[3]` bytes — 8none1's `01 00` vs app's `01 01`/`00 01`. [Verified-against-decompile]**
8none1's text metadata header (`build_string_packet :155`,
`decoding_bytes.md:22`) is `FF FF 00 01 …` i.e. byte[2]=**0**, byte[3]=**1**.
The decompiled app uses byte[2]=**1**, byte[3]=**1** in `sendTextTo1616`
(`:662-663`) and byte[2]=**0**, byte[3]=**1** only in `sendTextTo1664`
(`:787-788`, `:918-919`). 8none1 captured the **1664** variant; for a 32×32 panel
the app drives the **1616** variant (`1,1`). **Verdict: byte[2]=1 for our device.**
Neither we nor 8none1 had this nailed; the decompile settles it. (We had no text
builder, so this is a "get it right when we add one" note, not an error in our code.)

**C4. 8none1 fonts are app-incompatible. [Verified-against-decompile]**
8none1 renders glyphs with **DejaVuSans-Bold** via PIL (`string_to_bitmaps :120-148`)
in **little-endian bit order, row-major, 16×32**. The app uses its own embedded
bitmap fonts (`Text1664.getCharBitmap`, multiple `fontIndex` values, CJK-aware
width selection) — `TextAgreement.java:331-336`. So 8none1's glyph *bytes* will
not match the app's and the per-glyph **width marker** logic differs (8none1
always `05`; app picks 2/3 or 0/1 by measured glyph width). **Verdict: the wire
*container* (markers + 0xFFFFFF + bitmap) is right, but the glyph *content* is a
free re-implementation.** Not "wrong", but anyone porting should know the rendered
pixels won't be byte-identical to the app.

**No hard byte/opcode conflicts** exist between 8none1 and our `protocol.py` on
anything we both implement (on/off, time, graffiti, transport). The only real
*bug* found is **C1 (GIF length +32)**, which is in 8none1, not us.

---

### (d) Concrete IMPROVEMENTS to our code/docs

1. **Add a ground-truth TEXT builder to `protocol.py`.** (Biggest win.) Implement
   `text(...)` returning an `ImageUpload`-style chunked upload using the **16-tall
   (`sendTextTo1616`) layout**: text-metadata header
   `[nchars(2 LE), 0x01, 0x01, mode, speed, color_mode, r,g,b, bg_mode, bg_r,bg_g,bg_b]`
   + per-glyph `[marker(2|3), 0xFF,0xFF,0xFF, <bitmap>]`, wrapped in the 16-byte
   outer header with **dataType byte[2]=3, byte[3]=0**, CRC32 over
   (meta+glyphs), `image_index=12`. Reuse a glyph renderer (PIL, like 8none1) for
   the bitmaps but follow the app's marker rule (2 for 8px-wide, 3 for 16px-wide
   glyphs). Add `DataType.TEXT = 3` to the canonical `protocol.py` (the vendored
   `timebox` copy already has it — sync it back). Cite: `TextAgreement.java:636-707`.

2. **Add a `gif()` convenience + document the GIF payload.** Add
   `def gif(raw_gif_bytes) -> ImageUpload: return ImageUpload(raw_gif_bytes,
   DataType.GIF, image_index=13)`. The payload is the **literal 32×32 `.gif` file
   bytes**, not raster RGB. Our existing `ImageUpload` machinery already produces
   the correct header (only `dtype0` differs). Document that `image_index=13`
   (`0x0d`) is the GIF "show now" value the app emits
   (`GifAgreement.java:338` writes `(byte)i`, with `i=13` from the GIF call site).
   Cite: `GifAgreement.java:309-340`.

3. **Add the DIY-animation 9-byte header path.** Our `DataType.ANIM=0` is dead
   without it. Add a branch in `ImageUpload.outer_packets()` (or a separate
   builder) that, for `DataType.ANIM`, emits the **9-byte** header
   `[len(2 LE), 0x00, 0x00, option, totalLen(4 LE)]` (no CRC/timeSign/index), and
   extend `parse_status` / the upload state machine to also accept the diy-ACK
   `byte[2]==0` (`…00…02`=next, `…00…01`/`…00…00`=finish). Cite:
   `ImageAgreement.java:301-344, 269-283`.

4. **Document text-mode / color-mode / bg-mode enums** in `docs/PROTOCOL.md`
   (from 8none1's hardware observations, A4): modes 0-8, color modes 0-5, bg 0-1.
   Tag **[Unconfirmed]** pending our own hardware check.

5. **Add a regression note that 8none1's GIF length field is +32 (C1)** so we
   don't "fix" our (correct) `total = len(self.data)` to match theirs.

6. **Capability note:** the app's image-upload `parseDataFinish` accepts a bare
   `bArr[4]==3` regardless of dataType (`ImageAgreement.java:256-261`), which is
   why our generic `[..,3]` DONE detection works across image/gif/text/diy.
   Worth stating explicitly in `docs/PROTOCOL.md`.

---

### Repo-1 summary (biggest findings)

1. **We're missing two whole upload features the app has: scrolling TEXT and GIF.**
   8none1 implements both; the decompiled `TextAgreement`/`GifAgreement` give us
   the exact ground-truth byte layouts to add them correctly (text outer header
   dataType byte[2]=**3**; GIF byte[2]=**1**; text-meta `[nchars,1,1,mode,speed,
   colormode,rgb,bgmode,bgrgb]`).
2. **Real bug found — in 8none1, not us:** its GIF builder writes the total-length
   field as `payload + 32`; the app writes bare `payload.length`. Our `ImageUpload`
   already does it right — do not "match" theirs.
3. **8none1 independently confirms our load-bearing facts:** RGB (not BGR) pixel
   order, the `0a00050100…` graffiti frame, the 4 KiB/16-byte-header/CRC32
   transport, the `01/02/03` ACK codes, `image_index=12 ⇒ timeSign 0`, and the
   509/18 MTU split.
4. **Two "get-it-right-later" gotchas the decompile settles:** our 32×32 uses the
   **16-tall** text path (meta byte[2]=**1**, glyph markers 2/3), not 8none1's
   32-tall `05`; and there's a separate **9-byte** DIY-animation header
   (`DataType.ANIM`) we have declared but never emit.
5. **No opcode/byte conflicts** between 8none1 and our `protocol.py` on the
   commands we both implement — our control-frame catalog holds up.

---

## Repo 2 — derkalle4/python3-idotmatrix-library

**URL:** https://github.com/derkalle4/python3-idotmatrix-library
**Cloned to:** `/Users/dallan/repo/idm/research/community/derkalle4-idotmatrix`
**Pinned commit:** `507a17a` (2025-06-05)
**Nature:** This is the **largest and most-complete** community library — the
polished, modular, `pip install idotmatrix` package (the successor in spirit to
8none1's notebook). It targets 16×16 and 32×32 displays, uses `bleak`, and is
organised as one command class per feature under `idotmatrix/modules/`:
`clock, common, countdown, chronograph, scoreboard, fullscreenColor, eco,
effect, graffiti, musicSync, system, image, gif, text`. Every class is
explicitly "Based on the BleProtocolN.java file of the iDotMatrix Android App",
so most opcodes are lifted straight from the same ground truth we use — making
this the best independent cross-check of our control-frame catalog, and the
source of several **whole features we never catalogued**.

Key files read (all under `idotmatrix/`):
- `connectionManager.py` — `bleak` singleton; `send()` chunks by
  `max_write_without_response_size`; UUIDs in `const.py`.
- `modules/common.py` — `setTime, setBrightness, screenOn/Off, flipScreen,
  freezeScreen, setSpeed, setJoint, setPassword, reset`.
- `modules/clock.py, countdown.py, chronograph.py, scoreboard.py,
  fullscreenColor.py, eco.py, effect.py, graffiti.py, musicSync.py, system.py`.
- `modules/image.py, gif.py, text.py` — the three chunked-upload builders.

Decompile cross-refs used (all under
`decompiled/playstore/sources/com/tech/idotmatrix/`):
`ble/BleProtocolN.java`, `core/data/{ImageAgreement,GifAgreement,TextAgreement,
Text1664,MutilColorAgreement}.java`.

---

### (a) What WE MISSED

**A1. `effect` / lighting-effect presets (CMD 3 / SUB 2). [Verified-against-decompile]**
This is the biggest *new opcode* we lack entirely. `modules/effect.py` sends a
multi-colour "lighting effect" frame:
`[len, 0, 3, 2, style, 90, count, r0,g0,b0, r1,g1,b1, …]` — `style` 0-6 selects
an animated pattern (rainbow sweeps, random pixels, etc., enumerated in
`effect.py:1-15`), `90` is a fixed speed, then a palette of 2-7 RGB triples.
Ground truth: this is **`MutilColorAgreement.sendMutilColor`**
(`MutilColorAgreement.java:135-167`), which builds
`bArr[2]=3, bArr[3]=2, bArr[4]=modelIndex, bArr[5]=speed, bArr[6]=size`
then `size` RGB triples; the `90` magic comes from
`LightingEffectsFragment.java:200 curLightColor.setSpeed(90)`. The device ACKs
`[..,3,2, 1]`=ok / `[..,3,2, 0]`=error (`MutilColorAgreement.java:106-111`). Our
`protocol.py` has **no effect/preset path at all**. Confirmed real for 32×32 (the
"Lighting Effects" tab drives every model). **(But their length byte is wrong —
see C1.)**

**A2. Password set + verify (CMD 4/2 and CMD 5/2). [Verified-against-decompile]**
`modules/common.py:setPassword` sends `[8,0,4,2, 1, high,mid,low]` (6-digit PIN
split into three 2-digit bytes). Ground truth `BleProtocolN.setPwd`
(`:132-141`) = `{8,0,4,2,(byte)i, pwd1,pwd2,pwd3}` — byte[4] is a flag (1=set),
then the three PIN bytes parsed from the 6-char string. There is **also a
separate verify opcode** the lib lacks but we should note: `BleProtocolN.verifyPwd`
(`:177-189`) = `{7,0,5,2, pwd1,pwd2,pwd3}` (CMD 5/SUB 2). We have neither set nor
verify. Real on all models.

**A3. Eco/sleep schedule has a leading FLAG byte we dropped (CMD 2/0x80). [Verified-against-decompile]**
`modules/eco.py:setMode(flag, start_h, start_m, end_h, end_m, light)` →
`[10,0,2,0x80, flag, sh,sm,eh,em, light]` (6 payload bytes). Ground truth
`BleProtocolN.setEco` (`:118-119`) = `{10,0,2,0x80,(byte)i,…,(byte)i6}` and the
caller `EcoActivity.java:62` passes
`(flag, hour1, min1, hour2, min2, light)`. **Our `protocol.py:set_eco`
(`:212-214`) is mis-shaped:** its signature is
`(on_h, on_m, off_h, off_m, e5, e6)` — it **omits the leading `flag`** and
mislabels the trailing **`light`/brightness** byte as `e6`. The byte count
(6) is right but the field mapping is wrong; derkalle4 has it correct. (See C3.)

**A4. `setJoint` is CMD 12 / SUB 0x80 — confirms our opcode but we never tested. [Verified-against-decompile]**
`common.setJoint` = `[5,0,12,0x80, mode]`. Matches `BleProtocolN.sendJoint`
(`:85-86`) `{5,0,12,0x80,(byte)i}` and our `protocol.py:set_joint` (`:227-229`).
Listed under "missed" only because the multi-panel "joint" feature exists and we
treat it as N/A — it's a real frame for tiled setups.

**A5. `deleteDeviceData` — wipe all stored device materials (CMD 2 / SUB 1). [Verified-against-decompile]**
`modules/system.py:deleteDeviceData` sends the fixed 17-byte frame
`[17,0,2,1, 12, 0,1,2,3,4,5,6,7,8,9,10,11]`. Ground truth: the literal array
`{17,0,2,1,12,0,1,…,11}` in `DeviceMaterialChildFragment.java:202` (and
`NewDeviceMaterialChildFragment.java:243`), dispatched via
`Agreement.deleteDeviceMaterial()`. It deletes the 12 stored material slots
(indices 0-11) on the device. We have no equivalent. Real on all models.

**A6. MusicSync / mic family (CMD 11/0x80, CMD 0/2). [Verified-against-decompile]**
`modules/musicSync.py` exposes `setMicType` `[5,0,11,0x80,type]`
(= `BleProtocolN.setMicType :127-128`), `sendImageRhythm` `[6,0,0,2, v, 1]`
(= `sendImageRhythm :81-82` `{6,0,0,2,(byte)i2,1}`), and `stopRhythm`
`[6,0,0,2,0,0]` (= `sendStopMicRhythm :103-104`). 8none1 had the rhythm bytes
too (Repo-1 A5); derkalle4 adds the mic-type opcode. We note "mic/rhythm n/a";
these are real frames (the 32×32 has no mic, but the opcodes are accepted).

**A7. `setTimeIndicator` confirms CMD 7 / SUB 0x80. [Verified-against-decompile]**
`clock.setTimeIndicator` = `[5,0,7,0x80, en]`. Matches
`BleProtocolN.setTimeIndicatorEnable` (`:166-168`) and our
`protocol.py:set_time_indicator` (`:207-209`). derkalle4's own comment notes the
app builds it but never calls it — matching the empty `setTimeIndicator(){}`
stub at `BleProtocolN.java:163`.

**A8. `freezeScreen` (CMD 3 / SUB 0). [Unconfirmed]**
`common.freezeScreen` = `[4,0,3,0]`. **NOT present in v2.1.1** — a grep of the
whole decompile finds no `{4,0,3,0}` frame and no freeze/定格 sender. Either a
community guess or carried from an older app build. We lack it; flag
**Unconfirmed** (do not add without a hardware test).

**A9. Alarm/buzzer + schedule + phrase — three whole feature families we (and
derkalle4) lack.** derkalle4's README explicitly lists "Alarm & Buzzer" and the
cloud/phrase APIs as **unimplemented** roadmap items, so the lib itself has no
alarm path — but the decompile has all three, with distinct opcodes, and we lack
them too. Detailed in A10-A12 (all **[Verified-against-decompile]**).

**A10. Timer / alarm with buzzer — `TimerAgreement` (byte[2]=0x00, byte[3]=0x80).**
A 12-byte non-chunked command (`TimerAgreement.sendCloseData`, `:262-282`):
`[len(2 LE), 0x00, 0x80, num, week, hour, min, dur_lo, dur_hi, index, buzzer]`
— `week` is a weekday bitmask, `dur` is the on-duration seconds (30/60/300/900/10
via `getTimeDuration()`, LE), `buzzer` is a 1/0 enable. There is also a chunked
variant (`sendData(Timer,…)`, `:464-527`) that uploads an image/text payload to
display when the timer fires (chunk header byte[2]=0x00, byte[3]=0x80). This is
the on-device **alarm with buzzer** the README wishes for. We have nothing here.

**A11. Scheduled on/off windows — `ScheduleAgreement` (byte[2]=0x05/0x07, byte[3]=0x80).**
Per-weekday on/off windows with content. Two chunked image builders
(`imageSolve`/`imageSolve2`, `:340-431`) use a **23-byte** header:
`[len(2 LE), 0x05, 0x80, index, week_mask, startH, startM, endH, endM,
type(1=gif|2=img), opt(0/2), totalLen(4 LE), CRC32(4 LE), 0,0, (index+30)]`.
The **master on/off + buzzer** toggle is a tiny fixed frame
`{5, 0, 7, 0x80, packed(on,buzzer)}` (`masterSwitch`, `:440`) — note this REUSES
the CMD 7 / SUB 0x80 opcode that we and derkalle4 call the "time indicator"
(A7). **So CMD 7/0x80's payload byte packs both an on/off and a buzzer bit for
the schedule master switch** — a nuance neither we nor derkalle4 captured. We
lack the whole schedule path.

**A12. Preset-phrase activation — `PhraseAgreement` (byte[2]=0x06, byte[3]=0x02).**
Selects/activates a set of stored "phrase" slots. Small non-chunked, no-CRC
command (`PhraseAgreement.sendData`, `:95-117`):
`[size+5, 0x00, 0x06, 0x02, size, (pos0+14), (pos1+14), …]` — one byte per
material, each `position+14`. ACK: `[..,6,2, 1]`=ok / `[..,6,2, 2]`=error
(`:72,77`). Related: phrases/material are also pushed via `GifAgreement` with
`image_index = position + 14` (`PresetPhraseActivity.java:412`,
`MaterialDetailsListActivity.java:671`) — explaining why GIF/image indices ≥14
exist. Brand-new opcode (CMD 6/SUB 2) we don't have.

---

### (b) What we got RIGHT (independently confirmed by derkalle4 + decompile)

- **GATT UUIDs / name prefix.** `const.py` `0000fa02` write, `0000fa03` read,
  name `IDM-`. Matches `protocol.py:43-48`. **[Verified-on-our-hardware]**
- **Frame format `[len_lo, len_hi, CMD, SUB, *payload]`, LE total length, no
  checksum.** Every `modules/*` frame is built exactly this way. Matches
  `protocol.py:113-120`. **[Verified-against-decompile]**
- **Time sync CMD 1/0x80, `yy%100, mo, dd, weekday(Mon=1..Sun=7), hh, mm, ss`.**
  `common.setTime` uses `datetime(...).weekday()+1` — identical to our `set_time`
  (`protocol.py:128-136`) and `synchronizedTime` (`BleProtocolN.java:170-175`).
  **[Verified-on-our-hardware]**
- **Brightness CMD 4/0x80.** `common.setBrightness` `[5,0,4,0x80, pct]` matches
  `protocol.py:set_brightness` (`:144-146`) and `BleProtocolN.setLight`
  (`:122-124`). (derkalle4 clamps 5-100; we clamp 0-100.) **[Verified-on-our-hardware]**
- **Screen on/off CMD 7/1; flip CMD 6/0x80; reset CMD 3/0x80 + brightness 0x50.**
  `common.screenOn/Off/flipScreen/reset` all match `protocol.py` and the app
  (`sendSwitchplate :107-108`, `setRotate180 :143-144`, `restDevice :63-66`).
  derkalle4's `reset()` even sends the same two-frame
  `04 00 03 80` / `05 00 04 80 50` we documented. **[Verified-against-decompile]**
- **Clock CMD 6/1, flags `style | 0x80(date) | 0x40(24h)`, then RGB.**
  `clock.setMode` packs the byte identically to our `set_clock`
  (`protocol.py:154-169`) and `sendClockMode` (`BleProtocolN.java:67-69`, where
  `i2==1`→`0x40`). **[Verified-against-decompile]**
- **Countdown CMD 8/0x80 `[mode, min, sec]`; chronograph CMD 9/0x80 `[mode]`.**
  `countdown.setMode` / `chronograph.setMode` match `protocol.py:set_countdown/
  set_chronograph` and `setCountDown :114-115` / `setSecondChronograph :157-159`.
  **[Verified-against-decompile]**
- **Fullscreen colour CMD 2/2 `[r,g,b]`, RGB order.** `fullscreenColor.setMode`
  matches `set_fullscreen_color` (`protocol.py:149-151`) and `sendColor`
  (`BleProtocolN.java:73-74`). **[Verified-against-decompile]**
- **Graffiti single-pixel CMD 5/1 `[0, r,g,b, x,y]`, RGB, no CRC/ACK.**
  `graffiti.setPixel` is byte-identical to our `draw_pixel` (`protocol.py:242-250`)
  and our golden `0a00050100ff00000808`. **Third independent confirmation of RGB
  order** (after 8none1 + decompile). **[Verified-on-our-hardware]**
- **Scoreboard CMD 10/0x80 — little-endian on the wire.** `scoreboard.setMode`
  does `struct.pack("!H", n)` (big-endian) then places bytes `[1],[0]` ⇒ **LE on
  the wire**. The app does the same: `short2Bytes((short)i)` (BE) placed
  `bArr[1], bArr[0]` (`BleProtocolN.setScoreboard :147-150`). Our
  `protocol.py:set_scoreboard` (`:182-189`) already emits LE. **All three agree:
  scoreboard is little-endian.** (See C2 — settles a long-standing doubt.)
  **[Verified-against-decompile]**
- **Bulk media: 4096-byte outer chunks, 16-byte header, CRC32 (zlib) over the
  whole payload (LE on wire), option 0 first / 2 continuation, ACK-paced.**
  derkalle4's `gif.py:_createPayloads` matches our `ImageUpload.outer_packets()`
  (`protocol.py:313-330`) and `GifAgreement.sendImageData`
  (`GifAgreement.java:303-340`) **exactly**. **[Verified-against-decompile + on-our-hardware]**
- **GIF dataType byte[2]=1, image_index byte[15]=13.** `gif.py` header
  `[..,1,0,…, 13]`. Matches `GifAgreement.java:314 bArr2[2]=1` and call site
  `sendImageData(...,13,...)` (`DiyAnimAddActivity.java:680`). Confirms our
  Repo-1 A2 finding and our timebox driver's `DataType.GIF`. **[Verified-against-decompile]**
- **509-vs-18 inner MTU split.** `ImageAgreement/GifAgreement.getSendData`
  `int i = isMtuStatus() ? 509 : 18` — confirms our `INNER_MTU_HIGH=509 /
  INNER_MTU_LOW=18` (`protocol.py:258-259`). **[Verified-against-decompile]**
- **ACK codes 1=next / 2=no-space|error / 3=done.** `parseDataNextPackage`/
  `parseDataError`/`parseDataFinish` (`ImageAgreement.java:264-274`) key on
  `bArr[4]` ∈ {1,2,3}; `parseDataFinish` accepts a bare `bArr[4]==3` regardless
  of dataType — matching our `Ack` enum and generic DONE detection
  (`protocol.py:347-377`). **[Verified-against-decompile]**

---

### (c) Disagreements / WRONG (with ground-truth verdict)

**C1. `effect` length byte — derkalle4 computes it wrong. [Verified-against-decompile]**
`effect.py:832-841` sets byte[0] = `6 + len(processed_rgb_values)` where
`len(processed_rgb_values)` is the **count of tuples** (2-7), giving e.g. 8 for a
2-colour effect. Ground truth `MutilColorAgreement.sendMutilColor` sets
`int i = (size*3) + 7; bArr[0] = (byte) i` (`MutilColorAgreement.java:137-139`) —
the length is the **total frame byte count**, i.e. `7 + 3*count` (= 13 for a
2-colour effect, not 8). **Verdict: app uses `7 + 3*count`; derkalle4's `6+count`
is wrong** (the device may still parse because it reads `count` from byte[6] and
ignores the wrong total-length). When WE add `effect()`, use `7 + 3*count`.
Frame (2 colours red+blue): `0d 00 03 02 <style> 5a 02 ff0000 0000ff`.

**C2. Scoreboard "big-endian" labels are misleading — the wire is LE.
[Verified-against-decompile]**
Both derkalle4 (`struct.pack("!H")` "big-endian" comment) and our own
`protocol.py:set_scoreboard` docstring ("OSS libraries document big-endian … the
decompiled app emits little-endian … Flagged to verify") describe it ambiguously,
but **all three implementations actually put the LOW byte first** =
little-endian on the wire. Ground truth `setScoreboard` (`BleProtocolN.java:148-150`)
places `short2Bytes[1]` (low) then `[0]` (high). **Verdict: scoreboard is
little-endian; nobody is wrong in bytes, only in their comments.** We can drop the
"Flagged to verify" caveat from our docstring — it's settled.

**C3. Our `set_eco` field mapping is wrong (theirs is right). [Verified-against-decompile]**
As in A3: our `protocol.py:set_eco(on_h, on_m, off_h, off_m, e5, e6)` omits the
app's leading **flag** byte and mislabels the **light/brightness** byte. Ground
truth payload = `(flag, start_h, start_m, end_h, end_m, light)`
(`EcoActivity.java:62` → `setEco :118-119`). **Verdict: derkalle4 is correct; our
signature should become `set_eco(flag, start_h, start_m, end_h, end_m, light)`.**

**C4. `image.py` upload format is BROKEN — not the ImageAgreement format.
[Verified-against-decompile]**
`image.py:_createPayloads` (`:62-77`) builds a **7-byte** header
`short(idk)[2] + [0,0,opt] + int(png_len)[4]` where `idk = len(png) + chunk_count`
— there is **NO CRC32**, **no timeSign**, **no image_index**, and the dataType
bytes are `[0,0]` not `[2,0]`. It also uploads a raw **PNG** blob, not RGB.
Ground truth `ImageAgreement.sendImageData` (`ImageAgreement.java:346-395`) uses
the **16-byte** header `[len(2), 2, 0, opt, totalLen(4 LE), CRC32(4 LE),
timeSign(2), index=12]` over the raw payload. **Verdict: derkalle4's still-image
uploader does not match v2.1.1 at all** (it looks like a stale/early DIY-anim
shape — closest to the 9-byte `sendDIYImageData` header `[len,0,0,opt,totalLen]`
at `ImageAgreement.java:301-344`, minus a byte). **OUR `image_rgb`/`ImageUpload`
is correct** (16-byte header, CRC32, byte[2]=2, index=12) — confirmed on hardware
(`0500020003` done-ACK). Do NOT mirror derkalle4's `image.py`. *(Their `gif.py`,
by contrast, IS correct — see (b).)*

**C5. Text glyph format — THREE-way conflict; the decompile settles the wire
container. [Verified-against-decompile; our hw capture differs]**
- **derkalle4 `text.py`** uses 8none1's shape: separator `05 ff ff ff`, **16×32**
  glyphs (32-byte bitmaps), metadata header byte[2]=**0**, byte[3]=**1**
  (`text.py:_buildStringPacket` "0,1 Static values"), and a Rain `.otf` font.
- **OUR timebox driver** (`panel_idotmatrix.py:60-89`, decoded from a real "Hi"
  capture) uses per-char `[02][fg(3)][bg(3)][11-byte bitmap][00 00]` with a
  global header `[count][00 01 01 00 00 01][fg(3)][bg(3)][pad]`, **11-row 8-wide**
  glyphs, LSB=leftmost.
- **Ground truth v2.1.1 `sendTextTo1616(...,String,...)`**
  (`TextAgreement.java:588-723`): metadata header is
  `[nchars(2 LE), 1, 1, mode, speed, colorMode, r,g,b, bgMode, bgr,bgg,bgb]`
  (byte[2]=**1**, byte[3]=**1**; `:662-663`), then **per glyph
  `[marker, 0xFF, 0xFF, 0xFF, <bitmap>]`** where `marker = 2` if the bitmap is 16
  bytes (8-wide×16-tall) else **3** (16-wide×16-tall = 32 bytes) — `:636-647`.
  The three bytes after the marker are **always `FF FF FF`, NOT per-glyph fg/bg**.
  Glyphs are **16 rows tall** (`Text1664.getCharBitmap(...,16,16,...)`), packed
  row-major 8 px/byte with **LSB = leftmost column**
  (`Text1664.getTextData :411-417`: `b = (bArr[i] << i5)`). The outer header is
  `[len(2), 3, 0, opt, totalLen(4 LE), CRC32(4 LE), 0, 0, index=12]`
  (byte[2]=**3**, byte[15]=**12**; `:692-708`).

  **Verdicts:**
  - byte[2] of the **text metadata** is **1** (1616 path), not derkalle4's/8none1's
    **0** (that `0,1` is the *1664* path, `:787-788`). Our 32×32 uses 1616 → **1**.
  - the per-glyph wrapper is **`[2|3][FF FF FF][16/32-byte bitmap]`**, 16-tall —
    NOT derkalle4's fixed `05 ff ff ff` (marker `5` is wrong for both paths) and
    NOT our driver's `[02][fg][bg][11-byte bitmap][00 00]` (no per-glyph colour;
    11-tall is wrong for v2.1.1). **Both community shape AND our captured shape
    disagree with v2.1.1 in the marker and the per-glyph colour bytes.**
  - the **bitmap bit order** our driver decoded (LSB=leftmost, row-major) is
    **correct** and matches `getTextData`.

  **Why our capture differs:** our `[02][fg][bg][bitmap][00 00]` + 11-tall glyphs
  was decoded live and renders on *our* unit, so it is a real, working format —
  but it does not match the v2.1.1 `sendTextTo1616` we decompiled. Likely a
  **different firmware/app build or a different ledType text path** produced it.
  **Action: tag our driver's text builder Unconfirmed-against-v2.1.1 and re-verify
  on hardware** which of the two the unit actually accepts (the v2.1.1
  `[2/3][FFFFFF][16-tall]` form, or our captured `[02][fg/bg][11-tall]` form).
  Outer header byte[2]=**3** and index=**12** are agreed by everyone.

**C6. derkalle4 `gif.py` leaves a stale timeSign. [Verified-against-decompile]**
Because GIF uses `image_index=13` (≠12), the app writes the real timeSign into
bytes[13-14] (`GifAgreement.java:329-337`). derkalle4's `gif.py` hardcodes the
header template `… 5, 0, 13` so bytes[13]=**5**, [14]=**0** are leftover garbage
(never zeroed, never set to a real timeSign). Harmless (timeSign only matters for
scheduled material) but technically wrong. Our `ImageUpload` zeroes timeSign only
when `image_index==12`; for a GIF (index 13) we'd emit `self.time_sign` (0 by
default) — also not the app's real value, but a clean 0 rather than 5. Minor.

**No hard control-frame conflicts** exist between derkalle4 and our `protocol.py`
on the simple commands (time, brightness, screen, clock, countdown, chronograph,
fullscreen, graffiti, scoreboard, joint, flip, reset) — they all match
byte-for-byte. The real bugs are **C1 (effect length)** and **C4 (image upload)**
in *their* code, and **C3 (eco fields)** in *ours*.

---

### (d) Concrete IMPROVEMENTS to our code/docs

1. **Add `effect()` (CMD 3/2) to `protocol.py`** — a brand-new opcode we lack:
   ```
   def effect(style: int, colors: list[tuple[int,int,int]], speed: int = 90) -> bytes:
       n = len(colors)                       # 2..7
       payload = [style & 0xFF, speed & 0xFF, n] + [c for rgb in colors for c in rgb]
       return frame(3, 2, *payload)          # frame() recomputes len = 7 + 3*n  ✓
   ```
   Use `7 + 3*count` for the length (our `frame()` already does the right thing —
   do NOT copy derkalle4's `6+count`, C1). Document `style` 0-6 and the 2-7 RGB
   palette. Cite `MutilColorAgreement.java:135-167`.

2. **Fix `set_eco` field mapping (C3).** Change the signature to
   `set_eco(flag, start_h, start_m, end_h, end_m, light)` → `frame(2, 0x80, flag,
   start_h, start_m, end_h, end_m, light)`. Cite `EcoActivity.java:62`,
   `BleProtocolN.setEco :118-119`.

3. **Add password set/verify.** `set_password(pin6: str, flag=1)` →
   `frame(4, 2, flag, int(pin6[0:2]), int(pin6[2:4]), int(pin6[4:6]))`;
   `verify_password(pin6)` → `frame(5, 2, int(pin6[0:2]), int(pin6[2:4]),
   int(pin6[4:6]))`. Cite `BleProtocolN.setPwd :132-141`, `verifyPwd :177-189`.

4. **Add `delete_device_materials()`** = `frame(2, 1, 12, 0,1,2,3,4,5,6,7,8,9,10,
   11)` (the fixed 17-byte wipe). Cite `DeviceMaterialChildFragment.java:202`.

5. **Add mic-family opcodes for completeness** (no-ops on 32×32 but real):
   `set_mic_type(t)`=`frame(11, 0x80, t)`, `image_rhythm(v)`=`frame(0, 2, v, 1)`,
   `stop_rhythm()`=`frame(0, 2, 0, 0)`. Cite `BleProtocolN :81,103,127`.

6. **Drop the "Flagged to verify" caveat on `set_scoreboard`** — the decompile
   plus two OSS libs confirm little-endian (C2). Keep the LE bytes as-is.

7. **Do NOT adopt derkalle4's `image.py`** — it has no CRC and the wrong dataType
   (C4). Our `ImageUpload` is the correct ImageAgreement format. Add a regression
   note so nobody "ports" their image uploader.

8. **Resolve the text format (C5) before shipping a canonical TEXT builder.** The
   v2.1.1 ground truth for our 32×32 is the **1616** path: metadata
   `[nchars(2LE), 1, 1, mode, speed, colorMode, r,g,b, bgMode, bgr,bgg,bgb]`,
   per-glyph `[2|3, FF, FF, FF, <16-tall bitmap>]`, outer header byte[2]=**3**,
   index=**12**, CRC32 over (meta+glyphs). Our timebox driver's captured form
   (`[02][fg][bg][11-tall][00 00]`) renders on our unit but does NOT match
   v2.1.1 — **tag it Unconfirmed-against-v2.1.1 and bench-test which form the unit
   accepts** before promoting either into canonical `protocol.py`. The bitmap bit
   order (LSB=leftmost, row-major) is confirmed either way. Cite
   `TextAgreement.java:588-723`, `Text1664.getTextData :394-417`.

9. **Mark `freezeScreen` (CMD 3/0) Unconfirmed in docs** (A8) — absent from
   v2.1.1; don't add without a hardware test.

10. **Add the timer/alarm + schedule + phrase opcodes** (A10-A12) — new feature
    families nobody in the OSS world has. Minimum viable additions:
    - `timer_alarm(num, week_mask, hour, minute, dur_s, index=0, buzzer=True)` →
      `frame(0, 0x80, num, week_mask, hour, minute, dur_s & 0xFF, (dur_s>>8)&0xFF,
      index, 1 if buzzer else 0)`. Cite `TimerAgreement.java:262-282`.
    - `schedule_master(on, buzzer=False)` → `frame(7, 0x80, packed)` where the
      payload byte packs `on` + `buzzer`. **Important: this shares CMD 7/0x80 with
      our `set_time_indicator`** — document that CMD 7/0x80 is overloaded (time
      indicator vs schedule master switch + buzzer). Cite `ScheduleAgreement.masterSwitch :440`.
    - `phrase(positions: list[int])` → `frame(6, 2, len(positions),
      *[(p+14) & 0xFF for p in positions])`. Cite `PhraseAgreement.java:95-117`.
    - (Full per-weekday schedule with content is a 23-byte-header chunked upload,
      `ScheduleAgreement.java:340-431` — lower priority; document the header shape.)

11. **Document that GIF/image `image_index` ≥ 14 is the phrase/material slot
    convention** (`image_index = position + 14`), explaining indices beyond
    12 (still) / 13 (gif). Cite `PresetPhraseActivity.java:412`.

### Repo-2 summary (biggest findings)

1. **New opcodes we never catalogued, all confirmed in v2.1.1:** the `effect`
   lighting-preset command (**CMD 3/2**, `[style, 90, count, …RGB]` via
   `MutilColorAgreement`), password **set (CMD 4/2)** + **verify (CMD 5/2)**, a
   device-material **wipe (CMD 2/1)** 17-byte frame, and three whole feature
   families the OSS world lacks — **timer/alarm-with-buzzer (CMD 0/0x80)**,
   **per-weekday schedule + master on/off-with-buzzer (CMD 5/0x80 & CMD 7/0x80)**,
   and **preset-phrase activation (CMD 6/2)**.
2. **A real bug in OUR code:** `set_eco` is mis-shaped — it drops the app's
   leading **flag** byte and mislabels the trailing **light/brightness** byte. The
   correct payload is `(flag, start_h, start_m, end_h, end_m, light)`
   (`EcoActivity.java:62`). derkalle4 has it right; we should fix it.
3. **Two real bugs in THEIR code:** `effect.py`'s length byte is `6+count` but the
   app uses `7 + 3*count` (`MutilColorAgreement.java:137`); and `image.py`'s
   still-image uploader is **broken** — no CRC32, wrong dataType `[0,0]`, bogus
   `idk` length field, and it ships a PNG blob. **Our `ImageUpload` is the correct
   ImageAgreement format** (16-byte header, CRC32, byte[2]=2, index=12) — do not
   port theirs. (Their `gif.py`, however, is correct and matches us byte-for-byte.)
4. **Scoreboard endianness is settled: little-endian on the wire** — all three
   (us, derkalle4, app) emit low-byte-first despite "big-endian" comments
   (`BleProtocolN.setScoreboard :148-150`). Drop our "flag to verify" caveat.
5. **Text format is a genuine three-way conflict the decompile partly settles:**
   v2.1.1's 32×32 path (`sendTextTo1616`) uses metadata byte[2]=**1** (not 0),
   per-glyph **`[2|3][FF FF FF][16-tall bitmap]` with NO per-glyph colour**, and
   outer byte[2]=**3**/index=**12**. **Both** derkalle4's `05 ff ff ff`/16×32 shape
   **and** our own hardware-captured `[02][fg][bg][11-tall][00 00]` shape disagree
   with v2.1.1 — so our captured text builder is from a different firmware/path and
   must be re-verified on hardware before we promote a canonical TEXT builder. The
   bitmap bit order (LSB=leftmost, row-major) is confirmed correct either way.

---

## Repo 3 — markusressel/idotmatrix-api-client

**URL:** https://github.com/markusressel/idotmatrix-api-client
**Cloned to:** `/Users/dallan/repo/idm/research/community/markusressel-idotmatrix`
**Pinned commit:** `0f27f02` (merge of PR #7)
**Nature:** A **modern refactor/fork of derkalle4's library** (Repo 2). Same
module taxonomy (`clock, common, countdown, chronograph, scoreboard,
fullscreen_color, eco, effect, graffiti, music_sync, system, image, gif, text`),
same "Based on the BleProtocolN.java file" headers — but rewritten with snake_case
APIs, an `IDotMatrixClient` facade (`client.py`), `ScreenSize` enum, enums for
every mode (`ClockStyle`, `EffectStyle`, `TextMode`, `TextColorMode`, `ImageMode`),
PIL-based `image_utils`/`color_utils` helpers, and — most importantly — a far more
robust **transport** (`connection_manager.py`) with auto-reconnect, connection
listeners, and an inner-MTU re-chunker. It also ships two **brand-new
application-level features** absent from every other OSS repo: a
**`DigitalPictureFrame`** slideshow with filesystem-watch, and a **`LOCATE`**
device-locate command. Because it shares derkalle4's opcode catalogue, this
section focuses ONLY on where markusressel **diverges** — bug fixes it made to
derkalle4, new bugs it introduced, the cleaner transport, and the new features.

Key files read (all under `idotmatrix/`):
- `connection_manager.py` — `bleak` client with auto-reconnect loop, connection
  listeners, signal handlers, dual chunking (`send_bytes`/`send_packets`).
- `client.py` — `IDotMatrixClient` facade exposing each module as a property.
- `const.py`, `screensize.py` — UUIDs + size enum.
- `modules/{common,clock,graffiti,scoreboard,eco,effect,music_sync,system,
  image,gif,text}.py`.
- `digital_picture_frame.py` — slideshow + auto-reconnect + folder-watch.

Decompile cross-refs (under
`decompiled/playstore/sources/com/tech/idotmatrix/`):
`core/data/{Agreement,ImageAgreement}.java`, `ble/BleProtocolN.java`,
`ui/settings/EcoActivity.java`.

---

### (a) What WE MISSED (esp. beyond Repos 1-2)

**A1. A genuinely robust BLE transport with auto-reconnect + connection
listeners. [Verified-against-source; transport pattern]**
This is the single biggest *new* thing in this repo and it is NOT in Repos 1-2
(8none1 uses `simplepyble` with no reconnect; derkalle4's `connectionManager`
is a bare singleton). `connection_manager.py` adds:
- **`set_auto_reconnect(bool)` + `_reconnect_loop()`** (`:359-372`) — on an
  unexpected `_on_disconnected` callback (`:337-357`) it spins up an asyncio task
  that retries `connect()` every 5 s until reconnected, gated by an
  `_is_auto_reconnect_active` flag that is cleared on *intentional* `disconnect()`
  (`:188`) so a user-initiated close doesn't trigger reconnection.
- **`ConnectionListener(on_connected, on_disconnected)`** (`:13-27`,
  `add_connection_listener :321`) — async callbacks fired on connect/disconnect,
  used by the picture-frame to pause/resume a slideshow across drops.
- **A reusable `BleakClient`** whose address is swapped in place
  (`_create_ble_client :109-112`: `self.client._backend.address = address`)
  rather than recreated.
- **SIGINT/SIGTERM handlers** (`_setup_signal_handlers :383-401`) that disconnect
  cleanly on Ctrl-C.
- **A `connection_manager_lock`** (`:29`) serialising connect/disconnect so the
  reconnect loop and a manual call can't race.
Our HA integration relies on HA's `bleak-retry-connector`, but **our standalone
timebox driver (`panel_idotmatrix.py`) has no reconnect/keepalive at all** — this
is a clean reference pattern worth porting for any non-HA use. **(d)#1.**

**A2. Dual-layer chunking with a runtime-probed inner MTU. [Verified-against-decompile]**
`send_packets` (`:231-296`) keeps the protocol's **outer** 4 KiB chunking (the
`List[List[bytes]]` the builders return) separate from the **inner** BLE-MTU
chunking, and probes the real MTU at runtime: `get_max_bytes_per_chunk`
(`:298-312`) reads `char.max_write_without_response_size`, and — for a quirk where
"my 64x64 device reports 20 most of the time" — falls back to **514**. It only
waits for / reads a notify response on the **last** inner packet of each outer
packet (`wait_for_response = response if j == len(packet)-1`, `:279`), and
swallows BlueZ `NotPermitted` errors on the read (`:289-291`). This is more
faithful to the app's `isMtuStatus() ? 509 : 18` split than a fixed constant, and
our drivers hardcode the inner size. **[Verified-against-decompile]**
(`ImageAgreement.getSendData` 509/18.)

**A3. `DigitalPictureFrame` — a slideshow application layer. [New feature, no
protocol impact]**
`digital_picture_frame.py` (541 lines) is an entire app on top of the client:
a slideshow of images+GIFs with configurable interval/shuffle, **inotify/polling
folder-watch** (`watchdog`) so dropping a file into a watched dir adds it live,
DIY-mode bookkeeping (`_switch_device_to_image_mode`/`_gif_mode` toggles
`image.set_mode(EnableDIY/DisableDIY)`), and slideshow pause/resume wired to the
A1 connection listeners so a BLE drop pauses and reconnect resumes. No new wire
bytes, but a strong UX reference if we ever want an HA "media slideshow".

**A4. `LOCATE` device-locate command — `{6,'L','O','C','A','T','E',0×9}` encrypted.
[Verified-against-decompile]**
`system.get_device_location` (`system.py:56-83`) targets a real app command we and
both prior repos lack: the 16-byte frame `{6, 76, 79, 67, 65, 84, 69, 0,0,0,0,0,0,
0,0,0}` (ASCII "LOCATE") sent through an encrypt step. Ground truth:
`Agreement.getLocationDevice()` (`Agreement.java:16-18`) returns exactly that
array, and `BleProtocol.java:30` writes
`Agreement.getEncryptData(Agreement.getLocationDevice())` where
`getEncryptData` = `aes.cipher(bArr, bArr)` from the obfuscated
`csh.tiro.cc.aes` class (`Agreement.java:11-13`). **markusressel's implementation
does NOT work** — see C4 — but it *documents the existence and plaintext* of a
locate opcode, which is new to us. **[Verified-against-decompile]**

**A5. `graffiti.set_pixels` — batched multi-pixel DIY draw + a `mirroring` byte.
[Unconfirmed]**
Beyond the single-pixel `set_pixel` we and Repos 1-2 have, markusressel adds
`set_pixels(color, xys)` (`graffiti.py:34-79`) that packs **N** coordinate pairs
into one frame: `[size_lo, size_hi, 5, 1, 0, r,g,b, x0,y0, x1,y1, …]` with
`size = 8 + 2*N` (LE length). It also exposes **byte[3] as a "mirroring mode 1-4"**
field (currently hardcoded `1`) — neither we nor Repos 1-2 noted that byte[3] of
the graffiti frame might select mirroring. The multi-pixel batching is plausible
(same opcode, longer payload) but **Unconfirmed against decompile** — I did not
locate the graffiti builder in the v2.1.1 sources (the single-pixel
`0a00050100...` form is our hardware golden; the batched form is markusressel's
extrapolation). Tag **Unconfirmed**; worth a hardware test (it could let us paint
a whole frame in one write instead of 1024 single-pixel frames). **(d)#5.**

**A6. Per-frame timing / frame-budget logic for GIF upload. [Heuristic, no new bytes]**
`gif.py:_ensure_reasonable_frame_count` (`:337-408`) caps animations at **64
frames** and a **2000 ms** total budget, evenly decimating frames and clamping
per-frame duration to ≥16 ms, and re-encodes via PIL with `disposal=2`,
`optimize=True` (a comment notes `optimize=False` *fails* the transfer). This is
device-empirical know-how (not in the app) that our GIF path lacks — useful when
we wire a `gif()` helper. The payload is still the literal re-encoded `.gif` bytes.

---

### (b) What we got RIGHT (independently confirmed, 3rd source)

markusressel inherits derkalle4's catalogue, so it re-confirms the same
load-bearing facts a **third** independent time. Highlights (all match our
`protocol.py` and the decompile):
- **GATT UUIDs / `IDM-` prefix.** `const.py:20-21,30` — `0000fa02` write,
  `0000fa03` notify, name `IDM-`. **[Verified-on-our-hardware]**
- **Frame `[len_lo, len_hi, CMD, SUB, *payload]`, LE length, no checksum.** Every
  module builds this way. **[Verified-against-decompile]**
- **Time sync CMD 1/0x80, `yy%100, mo, dd, weekday(Mon=1..Sun=7), hh, mm, ss`.**
  `common.set_time` (`:171-186`) — identical to our `set_time`. **[Verified-on-our-hardware]**
- **Brightness CMD 4/0x80, screen CMD 7/1, flip CMD 6/0x80, reset CMD 3/0x80.**
  `common.py:106-124,33-104,230-244`. **[Verified-against-decompile]**
- **Clock CMD 6/1, flags `style | 0x80(date) | 0x40(24h)` then RGB.**
  `clock._create_payload` (`:105-117`) is byte-identical to our `set_clock`.
  **[Verified-against-decompile]**
- **Scoreboard CMD 10/0x80 is LITTLE-ENDIAN on the wire.** `scoreboard.show`
  (`:21-40`) packs `!H` (BE) then emits bytes `[1],[0]` ⇒ LE — a **third**
  confirmation matching `setScoreboard` (`BleProtocolN.java:147-150`,
  `bArrShort2Bytes[1]` low byte first) and our `set_scoreboard`. The "big-endian"
  comment is again just mislabelled; the wire is LE. **[Verified-against-decompile]**
- **Graffiti single-pixel CMD 5/1 `[0, r,g,b, x,y]`, RGB order.** `set_pixel`
  → `_create_payload` with one xy = `0a 00 05 01 00 RGB XY`. Matches our golden
  `0a00050100ff00000808`. **Fourth** confirmation of RGB order. **[Verified-on-our-hardware]**
- **`delete_device_data` = the fixed 17-byte wipe.** `system.py:13-38`
  `[17,0,2,1,12,0,1,…,11]` is byte-identical to ground truth
  `Agreement.deleteDeviceMaterial()` (`Agreement.java:7-9`) and to derkalle4's
  Repo-2 A5. **[Verified-against-decompile]**
- **GIF bulk transport: 4 KiB outer chunks, 16-byte header, dataType byte[2]=1,
  CRC32 (LE), option 0/2, `image_index` byte[15], 509/18 inner MTU.**
  `gif.create_gif_data_packets` (`:211-294`) matches our `ImageUpload` and
  `GifAgreement.sendImageData` (modulo C2). **[Verified-against-decompile + on-our-hardware]**
- **`image_index==12 ⇒ timeSign (0,0)`.** `gif.py:271-273` special-cases 12.
  Matches the app. **[Verified-against-decompile]**

---

### (c) Disagreements / WRONG (ground-truth verdict; who fixed/broke what)

**C1. markusressel FIXED derkalle4's broken still-image uploader. [Verified-against-decompile]**
This is the headline divergence. Repo-2 C4 flagged derkalle4's `image.py` as
**broken** (7-byte header, no CRC, wrong dataType `[0,0]`, bogus `idk` length,
PNG blob). markusressel **rewrote it correctly** as the **DIY-animation 9-byte
header** path: `_create_diy_image_data_packets` (`image.py:207-266`) emits
`[len_lo,len_hi, 0x00,0x00, option(0/2), totalLen(4 LE)]` + raw **RGB** pixel
bytes, chunked at 4096. This matches ground truth `sendDIYImageData`
(`ImageAgreement.java:301-344`) **exactly**: `bArr3[2]=0, bArr3[3]=0`,
`bArr3[5..8] = int2byte(bArr.length)` (full payload length, LE), header length
= `chunk.length + 9`, `option=2` for continuation. **Verdict: markusressel is
correct and fixed derkalle4's bug.** Note this is the **9-byte DIY-anim header**
we flagged as missing in Repo-1 A3 / Repo-2 — markusressel is the **first OSS repo
to emit it correctly**, and it ships RGB pixels (not PNG). It is, however, the
*DIY-animation* path, NOT the 16-byte `sendImageData` ImageAgreement path our
`ImageUpload` uses; both are real app paths (DIY draw vs. still-image-with-index).
**Our `ImageUpload` (16-byte, CRC32, byte[2]=2, index=12) remains correct for the
still-image case** — markusressel simply implements the *other* (DIY) image path.
**(d)#2.**

**C2. markusressel's GIF length-field comment is mislabelled "Big Endian" but the
bytes are LE (correct). [Verified-against-decompile]**
`gif.py:250,254` names the packet-length var `..._bytes_be` and comments
"(Big Endian short)", but it is built with `_int_to_bytes_le` and placed
`header[0]=[0], header[1]=[1]` ⇒ **little-endian, which is correct**
(`GifAgreement`/`ImageAgreement` use `short2Bytes` placed `[1],[0]` = LE). Pure
comment rot; bytes are right. Also: unlike derkalle4 (Repo-2 C6, which left a
stale `5,0` in bytes[13-14] for GIFs), markusressel correctly **zeroes
bytes[13-14] when `gif_type==12`** and otherwise writes a converted timeSign
(`gif.py:271-281`) — **a fix vs derkalle4's stale-timeSign bug.**

**C3. markusressel still carries derkalle4's `effect` length bug. [Verified-against-decompile]**
`effect._compute_payload` (`effect.py:67-77`) sets byte[0] = `6 + len(colors)` —
the **same wrong formula** Repo-2 C1 caught in derkalle4. Ground truth
`MutilColorAgreement.sendMutilColor` uses `(size*3)+7` =
**`7 + 3*count`** (`MutilColorAgreement.java:137-139`). **Verdict: NOT fixed;
still wrong** (e.g. 8 instead of 13 for a 2-colour effect). The device likely
tolerates it because it reads `count` from byte[6]. When WE add `effect()`, use
`7 + 3*count`. (markusressel did add a clean `EffectStyle` enum 0-6, which is a
nice doc artefact.)

**C4. markusressel's `LOCATE` encryption is WRONG and cannot work. [Verified-against-decompile]**
`system.get_device_location` (`system.py:56-83`) encrypts the LOCATE plaintext
with **`cryptography.fernet.Fernet` using a freshly `Fernet.generate_key()`**.
The app uses neither Fernet nor a random key: `getEncryptData` calls
`aes.cipher(bArr, bArr)` — an **in-place fixed-key block cipher** from the
obfuscated/native `csh.tiro.cc.aes` class (`Agreement.java:11-13`), which is not
present in the decompiled Java sources (stripped/native). Fernet is
AES-128-CBC+HMAC with a versioned token envelope — structurally incompatible with
a raw 16-byte in-place AES block, and a random key can never match the device's.
**Verdict: broken (markusressel even comments "Missing some AES encryption stuff
of iDotMatrix to work").** Value is documentary only: it reveals the LOCATE
plaintext and that locate is gated behind the same custom AES used elsewhere
(this AES gate is why we can't trivially reimplement certain commands).

**C5. markusressel BROKE the mic-type length byte. [Verified-against-decompile]**
`music_sync.set_mic_type` (`music_sync.py:9-25`) builds
`[6, 0, 11, 128, type]` — but that frame is **5 bytes**, so byte[0] should be
**5**, not 6. Ground truth `setMicType` (`BleProtocolN.java:127-128`) =
`{5, 0, 11, 0x80, (byte)i}` (length 5). derkalle4 had it right (Repo-2 A6:
`[5,0,11,0x80,t]`). **Verdict: markusressel introduced a +1 length bug.** Minor
(device reads param count implicitly), but a regression vs derkalle4. Note also
markusressel renamed `send_image_rythm`/`stop_rythm` (sic) — the byte frames
`[6,0,0,2,v,1]` / `[6,0,0,2,0,0]` are unchanged and correct.

**C6. `eco.set_mode` is CORRECT here (and exposes OUR bug again). [Verified-against-decompile]**
`eco.set_mode` (`eco.py:15-72`) emits
`[10,0,2,0x80, enabled, start_h, start_m, end_h, end_m, eco_brightness]` — the
leading **enabled/flag** byte + trailing **brightness** byte, matching ground
truth `setEco(flag, hour1, min1, hour2, min2, light)`
(`EcoActivity.java:62` → `BleProtocolN.setEco :118`). This re-confirms (a 3rd
source) that **OUR `protocol.py:set_eco` is the one that's mis-shaped** (drops the
flag, mislabels brightness) — already logged as Repo-2 C3; markusressel
independently corroborates the correct field order. **(d)#3.**

**C7. `freeze_screen` (CMD 3/0) carried forward — still Unconfirmed/absent from
v2.1.1. [Unconfirmed]**
`common.freeze_screen` (`common.py:16-31`) = `[4,0,3,0]`, inherited verbatim from
derkalle4 (Repo-2 A8). Same verdict: **no `{4,0,3,0}` sender exists in v2.1.1** —
a community guess. Don't adopt without a hardware test.

**No new hard opcode conflicts** with our `protocol.py` beyond what Repos 1-2
already surfaced. Net bug tally for this repo: **fixed** derkalle4's image
uploader (C1) and stale-GIF-timeSign (C2); **carried** the effect-length bug (C3)
and freeze guess (C7); **introduced** the mic-type length bug (C5) and a
non-functional Fernet LOCATE (C4).

---

### (d) Concrete IMPROVEMENTS to our code/docs

1. **Port the auto-reconnect transport pattern to our standalone driver (A1).**
   `panel_idotmatrix.py` has no reconnect/keepalive. Adopt markusressel's
   `connection_manager.py` design: a `disconnected_callback` that, when the drop
   was *unexpected* (flag cleared on intentional `disconnect()`), launches a
   bounded retry loop; optional `ConnectionListener` callbacks; a lock serialising
   connect/disconnect. (Our HA path already gets this from
   `bleak-retry-connector`, so this is for the non-HA driver.) Cite
   `connection_manager.py:337-401`.

2. **Add a DIY-animation image path using the 9-byte header (C1) — markusressel
   gives us the first correct OSS reference.** Add an `ImageUpload`-style builder
   (or branch on `DataType.ANIM`) that emits `[len(2 LE), 0,0, option, totalLen(4
   LE)]` + raw **RGB** pixels (no CRC/timeSign/index), exactly per
   `ImageAgreement.sendDIYImageData` (`:301-344`) and markusressel's
   `image._create_diy_image_data_packets`. Keep our existing 16-byte
   `ImageUpload` for the still-image (`sendImageData`, index 12) case — they are
   two different real paths. This finally retires the dead `DataType.ANIM=0`.

3. **Fix `set_eco` (3rd corroboration, C6).** Signature →
   `set_eco(flag, start_h, start_m, end_h, end_m, light)`. Already actioned in
   Repo-2 (d)#2; markusressel confirms.

4. **When we add `effect()`, use `7 + 3*count` for the length (C3)** — do NOT copy
   markusressel/derkalle4's `6+count`. Cite `MutilColorAgreement.java:137`.

5. **Hardware-test markusressel's batched graffiti `set_pixels` (A5).** If the
   device accepts `[size(2 LE), 5, 1, mirror, 0, r,g,b, x0,y0,…]` with N pairs, we
   can paint a full frame in ONE write instead of 1024 single-pixel
   `0a000501...` frames — a big throughput win for our pinball driver. Also probe
   whether byte[3] really selects a 1-4 mirroring mode. Tag results
   **Verified-on-our-hardware** once tested. Cite `graffiti.py:55-79`.

6. **Document the `LOCATE` opcode + the custom-AES gate (A4/C4).** Add to
   `docs/PROTOCOL.md`: locate plaintext = `{6,'L','O','C','A','T','E',0×9}`, but it
   (and presumably any cloud/material command) is wrapped by the obfuscated
   `csh.tiro.cc.aes` cipher — markusressel's Fernet attempt does NOT work, and
   reproducing it requires recovering the native AES key/mode. Marks a hard
   boundary on what we can reimplement without the key. Cite `Agreement.java:11-18`.

7. **Adopt markusressel's GIF frame-budget heuristics for a future `gif()` helper
   (A6):** cap 64 frames / 2000 ms, clamp per-frame ≥16 ms, re-encode with
   `disposal=2` + `optimize=True` (their note: `optimize=False` fails transfer).
   Empirical, not in the app, but battle-tested. Cite `gif.py:337-408`.

8. **Note the mic-type length-byte regression (C5)** so we keep our (correct)
   length=5 for `frame(11, 0x80, t)` and don't mirror markusressel's `6`.

9. **Borrow the `DigitalPictureFrame` UX as a model** if we ever expose a HA
   "slideshow/media" entity (folder-watch + interval + pause-on-disconnect).
   No protocol impact. Cite `digital_picture_frame.py`.

### Repo-3 summary (biggest NET-NEW findings beyond Repos 1-2)

1. **markusressel FIXED derkalle4's broken still-image uploader** by implementing
   the **9-byte DIY-animation header** (`[len,0,0,opt,totalLen(LE)]` + raw RGB)
   correctly per `sendDIYImageData` (`ImageAgreement.java:301-344`) — the first
   correct OSS rendering of the DIY path we'd only seen as a gap, and it retires
   our dead `DataType.ANIM=0`.
2. **A real reconnect/keepalive transport** (auto-reconnect loop + connection
   listeners + dual-layer MTU chunking with a runtime-probed inner size) that our
   standalone driver lacks — a clean reference to port.
3. **Two brand-new opcodes/features:** the **`LOCATE`** command (plaintext
   `{6,"LOCATE",0×9}`, but gated behind the obfuscated `csh.tiro.cc.aes` cipher —
   markusressel's Fernet stab does NOT work, marking a hard AES boundary), and a
   **batched multi-pixel graffiti** write (`5,1` with N xy pairs + a possible
   `mirror` byte[3]) that could replace 1024 single-pixel frames — Unconfirmed,
   worth a bench test.
4. **Bug ledger:** fixed derkalle4's image uploader (C1) and stale-GIF-timeSign
   (C2); **introduced** a mic-type length +1 bug (C5) and a non-functional Fernet
   LOCATE (C4); **carried** the `effect` length bug (`6+count` vs correct
   `7+3*count`, C3) and the `freeze_screen {4,0,3,0}` guess (absent from v2.1.1).
5. **Third independent corroboration** of our load-bearing facts (LE scoreboard,
   RGB graffiti, the eco `(flag,…,light)` field order that OUR `set_eco` still
   gets wrong, the 17-byte material-wipe, GIF transport/dataType=1/index=12).

---

# Synthesis & Prioritized Improvements

Cross-checked our RE against **8none1/idotmatrix**, **derkalle4/python3-idotmatrix-library**,
and **markusressel/idotmatrix-api-client**, every disagreement settled against the decompiled
official app v2.1.1. Net: **our control-frame catalog and chunked-upload transport are correct**;
the community repos surfaced one real bug in our code, a set of commands we hadn't catalogued,
and several bugs in *their* code we must NOT copy.

## What we got RIGHT (3-way + ground-truth confirmed)
- Control-frame envelope `[len_lo,len_hi,cmd,sub,…]`, total length LE16, **no checksum**.
- Every shared opcode: time-sync, brightness, screen on/off, fullscreen colour, clock + the
  `0x80`/`0x40` date/24h flag bits, countdown, chronograph, flip, reset, graffiti `0a000501…`.
- **RGB** pixel order (not BGR), the 4 KiB-outer / 16-byte-header / **CRC32** chunked image
  transport, ACK codes `01`=next/`02`=no-space/`03`=done, and `image_index=12 ⇒ timeSign=0`.
- **Scoreboard little-endian** — SETTLED (us + all 3 repos + app).
- Our **≤256-byte inner-write cap** is a genuine value-add the others lack (they hardcode 509;
  Android fragments transparently, other stacks don't — our cap is why uploads work off-Android).
- GIF dataType=1; text glyph bit-order (LSB=leftmost, row-major) — our hardware-verified formats hold.

## What was WRONG
- **OURS (now FIXED):** `set_eco` mislabeled all fields — correct is
  `(flag, start_h, start_m, end_h, end_m, light)` per `EcoActivity.java:62`. Fixed + tested.
- **THEIRS — do NOT port:** 8none1 GIF total-length `payload+32` (app uses bare `payload.length`);
  derkalle4 `effect` length `6+count` (app: `7+3*count`) and a **broken still-image uploader**
  (no CRC32, wrong dataType `{0,0}`, ships a PNG blob — our `ImageUpload` is the correct
  `ImageAgreement` format); markusressel mic-type length `+1` (`BleProtocolN.java:127` = `5`) and a
  non-functional Fernet `LOCATE`; derkalle4/markusressel `freeze_screen {4,0,3,0}` — **absent in v2.1.1**.

## What we MISSED
| Feature | Opcode | Status |
|---|---|---|
| eco field order | 2/0x80 | ✅ FIXED this pass |
| password set / verify | 4/2, 5/2 | ✅ ADDED this pass (`set_password`/`verify_password`) |
| effect / lighting presets (MutilColor) | 3/2 | backlog — ground-truth the exact `[style,90,count,…RGB]` layout (community versions buggy) |
| timer / alarm + buzzer | 0/0x80 | backlog (advanced) |
| schedule + master on/off + buzzer | 5/0x80, 7/0x80 | backlog (note the 7/0x80 overload vs time-indicator) |
| preset-phrase activation | 6/2 | backlog |
| device-material wipe | 2/1 | backlog (17-byte AES-wrapped) |
| DIY-animation 9-byte header (`DataType.ANIM=0`) | dtype 0 | backlog — markusressel got it right; we declare the enum but never emit it |
| `LOCATE` | — | BLOCKED — gated behind the native `csh.tiro.cc.aes` cipher; not reimplementable |
| batched multi-pixel graffiti (N xy pairs, `5/1`) | 5/1 | backlog — needs a hardware test |

## Prioritized improvements
**DONE this pass** (canonical `protocol.py`, 21 tests pass): fixed `set_eco`; added
`set_password`/`verify_password`; dropped the settled scoreboard caveat; added golden tests.

**HIGH backlog**
1. **Backport TEXT + GIF + DIY-anim builders into the canonical `protocol.py`** — they exist
   (hardware-verified) only in the timebox driver; backporting gives the HA integration native
   animations + scrolling text. (markusressel's correct 9-byte DIY-anim header retires our dead
   `DataType.ANIM`.)
2. Port markusressel's **reconnect/keepalive + runtime inner-MTU probe** into the standalone
   `panel_idotmatrix.py` (HA already gets reconnect from `bleak-retry-connector`).

**MEDIUM backlog**
3. Implement `effect` (3/2) + the alarm/schedule/phrase families, ground-truthing each `*Agreement`
   layout in the decompile (the community implementations are buggy — derive from the app, not them).
4. Fix the on-the-wire docs in `docs/PROTOCOL.md` to add the above opcodes.

**LOW / blocked**
5. `LOCATE` is behind a native AES cipher — documented as a hard boundary, not reimplementable.
6. Batched multi-pixel graffiti — verify on hardware before adding.
