# Carousel demo — "A Grand Tour of China" (36 scenes)

36 animated 32×32 pixel-art scenes touring China, looping on the iDotMatrix **autonomously**.

The catch: **the device carousels only 12 slots** (a firmware hard cap — see
[`../../docs/PROTOCOL.md`](../../docs/PROTOCOL.md) → *Device carousel*). The clean way to get **36
sequential** scenes is therefore **not** the carousel at all — it's **one long GIF of all 36 scenes
stored in a single slot** (`count=1`), which the device loops in true frame order → 1…36, no
carousel timing to fight.

| scenes | theme |
|---|---|
| 1–4 | ☯ Yin/Yang (rotating taiji) |
| 5–7 | 🌆 Guangzhou (Pearl River skyline) |
| 8–11 | 🗼 Canton Tower (the twisty 小蛮腰) |
| 12–14 | 🌃 Shenzhen (neon skyline, Ping An) |
| 15–18 | 🟣 Shanghai (Oriental Pearl + the Bund) |
| 19–22 | 🏯 Suzhou (moon gate, white walls, willows, canal) |
| 23–26 | ⛩ West Lake (Leifeng Pagoda, willows, boat) |
| 27–29 | 🦁 Foshan (lion dance) |
| 30–33 | 🐉 Dragon Boat (paddlers + drum) |
| 34–36 | 🌿 TCM (mortar & pestle, herbs, bagua) |

![36 scenes](contact.png)

## Generate

```bash
python generate.py        # writes ./combined.gif (360 frames, all 36 in order, ~221 KB)
                          #  + ./gifs/slot_00..11.gif (the alt 12-slot packed form)
```

## Store it (the working way) — one GIF, one slot

Slot-setup with **`count=1`** (`cmd 2/1` = `06 00 02 01 01 00`), upload `combined.gif` to
`image_index=0` (`DataType.GIF`), then `enter_asset_view` (`cmd 10/1`). The device loops the single
GIF → scenes **1→36** in order, ~32 s, untethered. (Driver helper: `combined_upload.py`.)

> **Why not the 12-slot carousel?** Packing 3 scenes per slot (the `gifs/slot_*.gif` form) works,
> but each slot **loops its 3-scene GIF for the whole dwell**, so you see `1,2,3,1,2,3,…` then
> `4,5,6,4,5,6,…` — it reads out of order. The single-GIF/`count=1` form avoids that entirely.

## Gotcha — keep frame palettes modest

The device's **GIF decoder silently skips color-heavy frames.** The first cut of the Canton Tower
used a per-row colour gradient; the panel **froze on scene 7 and skipped 8–11**. Flattening it to a
single cycling tower colour (far fewer palette entries per frame) fixed it — all 36 now play. Rule
of thumb: a handful of solid colours per 32×32 frame, not smooth gradients.
