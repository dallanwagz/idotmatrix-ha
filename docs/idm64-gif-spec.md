# iDotMatrix 64×64 LED Panel — GIF Content Spec (v1)

**Purpose.** Hand this file to any LLM/agent. If it produces a GIF that follows these rules, the GIF
will render correctly on the iDotMatrix **64×64** LED matrix panel. Every limit below was determined
empirically on real hardware — it is not guesswork.

**The output is a single animated `.gif` file.** That is the only format the panel needs.

---

## 1. Hard requirements (MUST — break these and it won't display right)

| Rule | Value |
|---|---|
| **File format** | Animated **GIF** (GIF89a). Nothing else. |
| **Dimensions** | **Exactly 64 × 64 pixels.** Square. Not 63, not 128. |
| **Color** | GIF indexed palette, **up to 256 colors.** |
| **Looping** | **Loop forever** (GIF loop count = 0). |
| **File size** | **≤ 100 KB.** Target **≤ 90 KB.** (This is a Bluetooth-upload reliability limit, not a display limit — bigger files upload slowly and can fail mid-transfer.) |

If a generated file violates any of these, fix it before use (see §5 validator).

## 2. Recommended ranges (SHOULD — for the best look)

| Aspect | Recommended | Notes |
|---|---|---|
| **Frame count** | 8 – 90 frames (sweet spot 20–60) | Up to ~90 verified. More frames = bigger file; watch the 100 KB cap. |
| **Frame duration** | 40 – 120 ms per frame (≈ **8–25 fps**) | 60–80 ms is a great default. 40 ms (25 fps) is the fastest that helps. |
| **Colors** | **Full color is fine** — gradients, shading, and dithering all render. | Verified: 126 colors in a single frame, gradient-shaded scenes, no dropped frames. |
| **Brightness** | Bright, **saturated** colors pop best on LEDs. | Pastels/very dark tones read weakly. |
| **Background** | **Pure black `#000000` = LED off** — great for backgrounds/negative space and saving file size. | |
| **Composition** | Bold shapes readable at 64px; motion in a sprite over a calmer background looks smoothest. | Full-screen every-pixel-changes-every-frame still works but is heavier. |

## 3. What was actually verified on this panel (so you can trust the numbers)

- **Full color:** a reconstructed reference scene — **64×64, 83 frames, up to 126 colors/frame, gradient-shaded, ~40 ms/frame** — rendered full-color and smooth.
- **Long animations:** a **92-frame** GIF played fine.
- **File size:** GIFs up to **~95 KB** uploaded and displayed reliably; a full pack of ~90 KB scenes played back-to-back. Above ~100 KB, Bluetooth uploads get slow/flaky.
- **The old "≤16 flat colors, no gradients" rule does NOT apply to this 64×64 panel.** (It was a limit of the older 32×32 firmware.) Design richly.

## 4. How to generate a compliant GIF (recipe for the LLM)

1. Render your animation frames as **64×64 RGB** images (any tool: Pillow/PIL, a canvas library, etc.).
2. Save as a single looping GIF. With Python + Pillow:
   ```python
   frames[0].save(
       "out.gif", format="GIF", save_all=True, append_images=frames[1:],
       duration=70,      # ms per frame (~14 fps); 40–120 is fine
       loop=0,           # loop forever
       disposal=2,       # clear each frame (clean animation)
   )
   ```
3. **Check the file size.** If `out.gif` is over ~90 KB, reduce in this order until it fits:
   (a) cut the color count (e.g. quantize to 128 or 64 colors), then (b) drop frames, then
   (c) simplify busy backgrounds (large flat/black areas compress far better).
4. Confirm it's exactly 64×64 and loops. Done — that `.gif` is ready to push to the panel.

## 5. Validation checklist (and an auto-fixer)

A compliant GIF passes ALL of:
- [ ] opens as a GIF; **width = 64, height = 64**
- [ ] **≤ 100 KB** on disk (ideally ≤ 90 KB)
- [ ] **animated** (≥ 2 frames) and **loops forever**
- [ ] every frame ≤ 256 colors (automatic for a real GIF)
- [ ] frame durations ≥ ~40 ms

The repo ships **`pi-quickstart/validate_gif.py`** which checks all of the above and can **auto-fix** a
non-compliant GIF (resize to 64×64, cap frames/colors, enforce loop, shrink under the size cap):
```bash
python3 validate_gif.py yourfile.gif            # report pass/fail
python3 validate_gif.py yourfile.gif --fix out.gif   # write a compliant version
```

## 6. TL;DR for a prompt
> Generate a **64×64 pixel animated GIF**, **≤ 90 KB**, **looping forever**, **20–60 frames** at
> **~60–80 ms/frame**. **Full color / gradients / shading are welcome** (up to 256 colors). Use
> **bright saturated colors**; **pure black is "off"** (good for backgrounds). Keep subjects bold and
> readable at 64px. Output a single `.gif`.
