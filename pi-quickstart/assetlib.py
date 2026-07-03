#!/usr/bin/env python3
"""assetlib — helpers for building *panel-safe* GIFs for iDotMatrix panels (needs `Pillow`).

Why this exists: the panel's GIF decoder SILENTLY SKIPS frames that are too colour-heavy (smooth
gradients, hundreds of colours). A frame that looks fine on your screen can just not appear on the
panel. The fix is always the same — keep a handful of FLAT colours per frame. `panel_safe()` and
`save_gif()` below enforce that for you, so if you build frames with these helpers, they'll render.

Import this from an asset generator (see examples/). Typical shape:

    from assetlib import Canvas, save_gif, SIZES
    S = 32
    frames = []
    for f in range(24):
        c = Canvas(S)                       # blank frame, RGB
        c.fill((10, 10, 40))                # flat background
        c.disc(S/2, S/2, 6, (255, 80, 0))   # a flat-coloured sprite
        frames.append(c.img)
    save_gif(frames, "art.gif", ms=80)      # quantizes to <=16 colours + writes the GIF

Then push it live:  IDM_ADDR=<mac> python3 idm_push.py --now art.gif
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

# ---- the spec, in constants (see SPEC.md / docs/PROTOCOL.md) ----
SIZES = (16, 32, 64)          # panel canvases this family supports; use YOUR panel's size
MAX_COLORS = 16               # keep frames at/below this — decoder is happy, dodges the skip bug
MIN_MS = 50                   # 50 ms/frame floor => ~20 fps ceiling for uploaded GIFs
DWELL_PRESETS = (5, 10, 30, 60, 300)   # per-slot carousel dwell seconds the app uses
SLOT_CAP = 12                 # carousel hard cap (image_index 0..11); a 13th slot never plays
# rough capacity: one slot holds >=1.3 MB; ~2 KB/frame dense => ~650-800 frames (~60-80 s @ 10 fps)


def font(px):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/Menlo.ttc"):
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, px)
            except Exception:
                pass
    return ImageFont.load_default()


class Canvas:
    """A single RGB frame with a few flat-colour drawing helpers (coords in pixels)."""
    def __init__(self, size, bg=(0, 0, 0)):
        self.S = size
        self.img = Image.new("RGB", (size, size), bg)
        self.d = ImageDraw.Draw(self.img)

    def fill(self, color):
        self.d.rectangle([0, 0, self.S, self.S], fill=color)

    def rect(self, x0, y0, x1, y1, color):
        self.d.rectangle([x0, y0, x1, y1], fill=color)

    def disc(self, cx, cy, r, color):
        self.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

    def line(self, x0, y0, x1, y1, color, width=1):
        self.d.line([x0, y0, x1, y1], fill=color, width=width)

    def text(self, s, color, center=True, y=None, fnt=None):
        fnt = fnt or font(int(self.S * 0.5))
        tmp = Image.new("L", (self.S * 8, self.S * 2), 0)
        ImageDraw.Draw(tmp).text((0, 0), s, fill=255, font=fnt)
        b = tmp.getbbox()
        if not b:
            return
        mask = tmp.crop(b)
        maxw = self.S - 2
        if mask.width > maxw:                       # scale to fit the panel width
            mask = mask.resize((maxw, max(1, int(mask.height * maxw / mask.width))))
        ox = (self.S - mask.width) // 2 if center else 1
        oy = (self.S - mask.height) // 2 if y is None else y
        solid = Image.new("RGB", mask.size, color)
        self.img.paste(solid, (ox, oy), mask.point(lambda v: 255 if v > 110 else 0))


def panel_safe(img, colors=MAX_COLORS):
    """Quantize to <=`colors` flat colours with NO dithering — the decoder-safe form."""
    return img.convert("RGB").quantize(colors=colors, dither=Image.Dither.NONE).convert("RGB")


def save_gif(frames, path, ms=80, colors=MAX_COLORS, loop=0):
    """Write a looping, panel-safe GIF. Clamps frame time to the 50 ms floor."""
    ms = max(MIN_MS, int(ms))
    safe = [panel_safe(f, colors) for f in frames]
    safe[0].save(path, format="GIF", save_all=True, append_images=safe[1:],
                 duration=ms, loop=loop, disposal=2)
    im = Image.open(path)
    print(f"  wrote {os.path.basename(path)}  {im.size[0]}x{im.size[1]}  "
          f"{getattr(im, 'n_frames', 1)}f  {os.path.getsize(path)}B")
    return path


def preview_png(path, scale=6, out=None):
    """Save a zoomed PNG of frame 0 so a human can eyeball the asset before pushing."""
    im = Image.open(path).convert("RGB")
    out = out or (os.path.splitext(path)[0] + "_preview.png")
    im.resize((im.width * scale, im.height * scale), Image.NEAREST).save(out)
    return out
