#!/usr/bin/env python3
"""Brazil futebol animations for the iDotMatrix 32x32 panels — solid colours only (the panel's
GIF decoder silently skips gradient/colour-heavy frames). Outputs:
  flag.gif            single 32x32 bandeira (twinkling stars)
  flag_L.gif/_R.gif   one 64x32 bandeira split across BOTH panels (left/right halves)
  ball.gif            bouncing soccer ball on the green pitch
  brasil.gif          'BRASIL' scrolling, yellow on blue
  gol.gif             'GOL!' flash for celebrations
"""
import io
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
GREEN = (0, 156, 59)
YELLOW = (255, 223, 0)
BLUE = (0, 39, 118)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def save_gif(frames, name, ms):
    p = os.path.join(HERE, name)
    frames[0].save(p, format="GIF", save_all=True, append_images=frames[1:],
                   duration=ms, loop=0, disposal=2)
    return p, len(frames), os.path.getsize(p)


def _font(sz):
    for f in ("/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/Library/Fonts/Arial.ttf"):
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_flag(d, W, H, stars_on):
    """Draw a stylised bandeira filling WxH onto draw d. stars_on = set of star indices lit."""
    d.rectangle([0, 0, W, H], fill=GREEN)
    cx, cy = W / 2, H / 2
    mx, my = W * 0.08, H * 0.10
    # yellow losango (diamond)
    d.polygon([(cx, my), (W - mx, cy), (cx, H - my), (mx, cy)], fill=YELLOW)
    # blue globe
    r = min(W, H) * 0.30
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLUE)
    # white band (ordem e progresso) — a slanted stripe clipped to the globe
    band = Image.new("L", (W, H), 0)
    bd = ImageDraw.Draw(band)
    bd.polygon([(cx - r, cy + r * 0.20), (cx + r, cy - r * 0.45),
                (cx + r, cy - r * 0.10), (cx - r, cy + r * 0.55)], fill=255)
    globe = Image.new("L", (W, H), 0)
    ImageDraw.Draw(globe).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    # stars: fixed positions inside the globe; lit ones white
    star_pos = [(cx - r * .4, cy - r * .3), (cx + r * .3, cy - r * .4), (cx - r * .1, cy + r * .3),
                (cx + r * .45, cy + r * .15), (cx - r * .5, cy + r * .1), (cx + r * .05, cy - r * .55),
                (cx + r * .25, cy + r * .45)]
    return r, cx, cy, band, globe, star_pos


def render_flag(W, H, frame, nframes):
    img = Image.new("RGB", (W, H), GREEN)
    d = ImageDraw.Draw(img)
    r, cx, cy, band, globe, star_pos = draw_flag(d, W, H, None)
    # paste white band only where inside globe
    px = img.load()
    bl, gl = band.load(), globe.load()
    for y in range(H):
        for x in range(W):
            if gl[x, y] and bl[x, y]:
                px[x, y] = WHITE
    # twinkle stars
    lit = (frame * 2) % len(star_pos)
    for i, (sx, sy) in enumerate(star_pos):
        on = ((i + frame) % 3) != 0
        if on:
            ix, iy = int(round(sx)), int(round(sy))
            if 0 <= ix < W and 0 <= iy < H:
                px[ix, iy] = WHITE
    return img


def gen_flag():
    n = 8
    save_gif([render_flag(32, 32, f, n) for f in range(n)], "flag.gif", 200)
    wide = [render_flag(64, 32, f, n) for f in range(n)]
    save_gif([w.crop((0, 0, 32, 32)) for w in wide], "flag_L.gif", 200)
    save_gif([w.crop((32, 0, 64, 32)) for w in wide], "flag_R.gif", 200)


def gen_ball():
    """Spinning adidas Trionda (FIFA WC 2026) as a clean 2-D pinwheel — the design that actually
    reads at 32px (modelled on the real ball, viewed via Sketchfab): a white sphere with three
    curved colour waves (CA red / MX green / US blue) spiralling out + gold star accents."""
    cx = cy = 16
    R = 15
    BG, SHADOW, RIM = (0, 64, 32), (0, 44, 22), (228, 228, 228)
    RED, GREEN, BLUE, GOLD = (222, 40, 45), (0, 158, 70), (0, 92, 205), (255, 205, 0)
    COLS = [RED, GREEN, BLUE]
    n = 24
    frames = []
    for f in range(n):
        img = Image.new("RGB", (32, 32), BG)
        d = ImageDraw.Draw(img)
        d.ellipse([cx - 12, cy + 12, cx + 12, cy + 15], fill=SHADOW)   # ground shadow
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=WHITE)        # white ball
        rot = 2 * math.pi * f / n
        for k in range(3):                                            # three curved colour waves
            col = COLS[k]
            rr = 2.0
            while rr < R - 0.6:
                ang = rot + k * 2 * math.pi / 3 + 0.17 * rr            # spiral = the "onda" curve
                x, y = cx + rr * math.cos(ang), cy + rr * math.sin(ang)
                w = max(0.9, 2.7 - 0.11 * rr)                          # taper to a comma tip
                d.ellipse([x - w, y - w, x + w, y + w], fill=col)
                rr += 0.5
        for k in range(3):                                            # a gold star near each tip
            ang = rot + k * 2 * math.pi / 3 + 0.17 * 12.5 + 0.25
            x, y = cx + 12.5 * math.cos(ang), cy + 12.5 * math.sin(ang)
            d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=GOLD)
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=RIM)       # crisp rim
        frames.append(img)
    save_gif(frames, "ball.gif", 55)


def _text_mask(s, fnt):
    tmp = Image.new("L", (400, 40), 0)
    ImageDraw.Draw(tmp).text((0, 0), s, fill=255, font=fnt)
    bbox = tmp.getbbox()
    return tmp.crop(bbox) if bbox else tmp


def gen_brasil():
    fnt = _font(22)
    mask = _text_mask("BRASIL  ", fnt)
    tw, th = mask.size
    strip = Image.new("RGB", (tw, 32), BLUE)
    sp = strip.load()
    ml = mask.resize((tw, min(28, th * 28 // th)) if th else (tw, 28)).load() if False else mask.load()
    y0 = (32 - th) // 2
    for y in range(th):
        for x in range(tw):
            if ml[x, y] > 110:
                sp[x, y0 + y] = YELLOW
    frames = []
    step, n = 2, (tw // 2)
    for f in range(n):
        off = (f * step) % tw
        canvas = Image.new("RGB", (32, 32), BLUE)
        for k in (0, tw):
            canvas.paste(strip, (k - off, 0))
        d = ImageDraw.Draw(canvas)
        d.rectangle([0, 0, 31, 1], fill=GREEN)
        d.rectangle([0, 30, 31, 31], fill=GREEN)
        frames.append(canvas)
    save_gif(frames, "brasil.gif", 80)


def gen_gol():
    fnt = _font(20)
    mask = _text_mask("GOL!", fnt)
    tw, th = mask.size
    frames = []
    for f in range(10):
        on = f % 2 == 0
        bg = GREEN if on else YELLOW
        fg = YELLOW if on else GREEN
        img = Image.new("RGB", (32, 32), bg)
        ml = mask.load()
        ox, oy = (32 - tw) // 2, (32 - th) // 2
        px = img.load()
        for y in range(th):
            for x in range(tw):
                if ml[x, y] > 110 and 0 <= ox + x < 32 and 0 <= oy + y < 32:
                    px[ox + x, oy + y] = fg
        frames.append(img)
    save_gif(frames, "gol.gif", 110)


def main():
    random.seed(7)
    gen_flag(); gen_ball(); gen_brasil(); gen_gol()
    print("generated:")
    for n in ("flag.gif", "flag_L.gif", "flag_R.gif", "ball.gif", "brasil.gif", "gol.gif"):
        p = os.path.join(HERE, n)
        im = Image.open(p)
        print(f"  {n:12s} {im.size[0]}x{im.size[1]}  {getattr(im,'n_frames',1)} frames  {os.path.getsize(p)} B")


if __name__ == "__main__":
    main()
