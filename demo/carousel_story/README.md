# Carousel demo — "The Awakening Lion of Foshan"

A 36-scene animated legend rendered as 32×32 pixel art, one GIF per **on-device carousel
slot**, so the iDotMatrix loops the whole story **autonomously** (no host connected). A Foshan
(佛山) tale — the martial-arts home of Wing Chun and the Southern Lion — following a kung fu
student from dawn training to the lion-dance climax of 采青 (*cai qing*, "plucking the greens").

| slots | act | scene |
|---|---|---|
| 0–5 | Dawn training | Wing Chun forms in a courtyard at sunrise |
| 6–11 | The wooden dummy (木人桩) | striking the mook jong, building skill |
| 12–17 | The lion awakens (醒狮) | the festival; the lion head blinks open & stirs |
| 18–23 | The lion dance | weaving a lantern-lit street to the drums |
| 24–29 | Plum-blossom poles (梅花桩) | leaping pole to pole toward the green up high |
| 30–35 | Cai qing & celebration | pluck the greens, fireworks, red packets fall |

![all 36 scenes](contact.png)

## Generate

```bash
python generate.py        # writes ./gifs/slot_00_*.gif … slot_35_*.gif  (~1.2 MB total)
```

Pure-procedural pixel art (PIL only) — no assets. Each scene is 46 frames at 70 ms with drifting
embers/confetti, ~35 KB encoded.

## Put it on the panel (carousel store)

Each scene is stored with the normal **GIF** chunked upload but two header fields set
(see [`../../docs/PROTOCOL.md`](../../docs/PROTOCOL.md) → *Device carousel*):

- `image_index` = the **slot** (0–35) — so scene order == story order,
- `timeSign` = the per-scene **dwell seconds** (≈4 s here).

Send the `cmd 2/1` page-setup before each page of 12 slots, then `enter_asset_view` (`cmd 10/1`)
to start the loop. **Upload one 12-slot page per BLE session** — macOS CoreBluetooth tends to drop
uploads past ~100 s, so a single ~1.2 MB / 36-scene push will disconnect mid-way; per-page bursts
(resume on drop) complete reliably.

## Notes on limits (measured on hardware)

There is **no app-side size cap** — the device firmware rejects overflow with a `NO_SPACE` NAK.
A single slot accepted **≥1.3 MB**, and all **36 slots (~1.2 MB total) fit with no `NO_SPACE`** —
so flash storage is *not* the bottleneck; BLE upload time/reliability is. Practically, a slot holds
1–2 min of full-motion 32×32 GIF, and the whole 36-scene set (~2.5 min of distinct animation)
loops forever, untethered.
