# Asset spec — what makes a GIF the panel will actually play

Everything you need to turn "I want a picture of X" into a GIF the panel renders correctly. Full
protocol detail is in [`../docs/PROTOCOL.md`](../docs/PROTOCOL.md); this is the short version an
asset-builder needs. The helpers in [`assetlib.py`](assetlib.py) already enforce the important
rules — build with those and you're safe by default.

## Canvas
- **Square, matching the panel:** `32×32` or `64×64` (this family also has 16×16). Send a GIF of the
  panel's exact size. The upload is size-agnostic — same script, same protocol, just different pixels.
- **RGB**, top-to-bottom, left-to-right.

## The one rule that bites: keep frames FLAT-coloured
- The panel's GIF decoder **silently skips frames that are too colour-heavy** — smooth gradients or
  hundreds of colours make a frame simply not appear (the panel looks like it froze or stutters).
- **Fix:** ≤ ~16 flat colours per frame, **no dithering**. Blocks/bands of solid colour, not
  gradients. `assetlib.save_gif()` quantizes to 16 colours with dithering off for you.
- Bright, saturated colours read best on the LEDs. Pure black = LED off (good for backgrounds).

## Motion & timing
- **Frame rate ceiling ≈ 20 fps** — minimum **50 ms/frame**. `save_gif` clamps to this.
- Full-frame stills refresh slowly (~3 fps); motion in a small sprite over a flat background is
  smoothest.
- Loop forever (`loop=0`, the default).

## Length / size
- One stored slot holds **≥ 1.3 MB** — roughly **650–800 dense frames (~60–80 s @ 10 fps)**. Plenty
  for any loop; you'll basically never hit it.

## Getting it onto the panel (see [`idm_push.py`](idm_push.py))
- **Live preview (instant, not saved):** `--now` → best while iterating. `idm_push.py --now art.gif`
- **Set-and-forget (stored, loops after you disconnect):** `idm_push.py art.gif:30` (`:30` = dwell s)
- **Carousel:** up to **12** GIFs, each with its own dwell — `idm_push.py a.gif:10 b.gif:8 c.gif:8`.
  12 is a firmware hard cap; a 13th slot never plays.
- **Both panels at once (cross-panel motion):** [`dual_push.py`](dual_push.py).

## Don't
- Don't enable the device password (it can lock the panel).
- Don't leave brightness stickily dimmed (survives power-cycle, looks dead).
- Don't run the phone app on a panel while the Pi is driving it — **one Bluetooth connection at a
  time**.
