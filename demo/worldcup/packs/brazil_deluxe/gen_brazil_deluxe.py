#!/usr/bin/env python3
"""gen_brazil_deluxe.py — a DELUXE, full-colour, cinematic Brazil World Cup pack for the
64x64 iDotMatrix RGB panel.

Unlike the old flat-16-colour pack, this one leans into what the 64x64 panel can actually do
(verified ~126 colours/frame, ~90 frames, gradients + dithering): per-pixel shading, gradient
skies, cloth folds, gold speculars, bloom/glow, motion blur and smooth motion. Everything is
built with numpy for the heavy pixel math and Pillow for compositing, then written through the
project's assetlib.save_gif(..., colors=256, dither=True) so the panel decoder keeps the colour.

Run:  python3 gen_brazil_deluxe.py
Produces: all *.gif, a *_preview.png per gif, and _montage.png. Files only — never touches BLE.
"""
import os
import sys
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

sys.path.insert(0, "/Users/dallan/repo/tyler/idotmatrix-ha/pi-quickstart")
from assetlib import save_gif, preview_png, font  # noqa: E402

S = 64
HERE = os.path.dirname(os.path.abspath(__file__))
YY, XX = np.mgrid[0:S, 0:S].astype(np.float32)   # YY = row (y), XX = col (x)

# ---- Brazil palette anchors --------------------------------------------------
GREEN = (0, 156, 59)
YELLOW = (255, 223, 0)
BLUE = (0, 39, 118)
WHITE = (255, 255, 255)

# =============================================================================
# numpy / PIL helpers
# =============================================================================


def arr():
    return np.zeros((S, S, 3), np.float32)


def to_img(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def from_img(im):
    return np.asarray(im.convert("RGB"), np.float32).copy()


def vgrad(top, bot):
    """Vertical gradient array top->bottom."""
    t = (YY / (S - 1))[..., None]
    return np.array(top, np.float32) * (1 - t) + np.array(bot, np.float32) * t


def radial(cx, cy, color, radius, gamma=2.0):
    """Additive radial glow array (0 at edge -> color at centre)."""
    d = np.sqrt((XX - cx) ** 2 + (YY - cy) ** 2) / radius
    f = np.clip(1 - d, 0, 1) ** gamma
    return f[..., None] * np.array(color, np.float32)


def bloom(a, radius=2.0, thresh=180, strength=0.9):
    """Add a soft glow around the brightest parts of the frame."""
    im = to_img(a)
    lum = np.asarray(im.convert("L"), np.float32)
    mask = np.clip((lum - thresh) / (255 - thresh), 0, 1)[..., None]
    bright = (from_img(im) * mask)
    blurred = np.asarray(
        to_img(bright).filter(ImageFilter.GaussianBlur(radius)), np.float32)
    return a + blurred * strength


def sample(base, sy, sx):
    """Nearest-neighbour gather from base[H,W,C] at float coords (clamped)."""
    yi = np.clip(np.rint(sy), 0, S - 1).astype(np.intp)
    xi = np.clip(np.rint(sx), 0, S - 1).astype(np.intp)
    return base[yi, xi]


def draw_layer(draw_fn, mode="RGBA"):
    """Make a transparent RGBA image, run draw_fn(ImageDraw), return (rgb, alpha) arrays."""
    im = Image.new(mode, (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    draw_fn(d)
    a = np.asarray(im, np.float32)
    return a[..., :3], a[..., 3] / 255.0


def over(bg, rgb, alpha):
    """Alpha-composite rgb (with alpha 0..1 HxW) over bg array."""
    al = alpha[..., None]
    return bg * (1 - al) + rgb * al


def star_poly(cx, cy, r, rot=-math.pi / 2, ratio=0.42):
    pts = []
    for i in range(10):
        ang = rot + i * math.pi / 5
        rad = r if i % 2 == 0 else r * ratio
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    return pts


def easeinout(t):
    return t * t * (3 - 2 * t)


# =============================================================================
# 1. Waving flag with cloth folds + soft sky
# =============================================================================


def build_flag_wave(nframes=40):
    # --- base flag texture (drawn once, then warped per frame) ---
    px, py0, py1 = 8, 8, 55            # flag body attaches to a pole at x=px
    def paint(d):
        d.rectangle([px, py0, S - 1, py1], fill=GREEN + (255,))
        cx, cy = (px + S) / 2 + 1, (py0 + py1) / 2
        w, h = (S - px) / 2 - 3, (py1 - py0) / 2 - 3
        d.polygon([(cx, cy - h), (cx + w, cy), (cx, cy + h), (cx - w, cy)],
                  fill=YELLOW + (255,))
        r = 11
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLUE + (255,))
        # white 'Ordem e Progresso' band (just a shaded arc)
        d.arc([cx - r, cy - r + 3, cx + r, cy + r + 3], 20, 160, fill=WHITE + (255,), width=3)
        # a scatter of white stars on the blue globe
        for sx, sy, sr in [(-5, -4, 1.4), (3, -6, 1.1), (6, 2, 1.3), (-3, 4, 1.2),
                           (1, 1, 1.6), (-7, 1, 1.0), (5, 6, 1.0)]:
            d.ellipse([cx + sx - sr, cy + sy - sr, cx + sx + sr, cy + sy + sr],
                      fill=WHITE + (255,))
    base_rgb, base_a = draw_layer(paint)

    sky = vgrad((66, 122, 196), (176, 214, 240))
    # a soft sun glow upper-left
    sky = sky + radial(14, 12, (60, 55, 30), 40, gamma=2.2)

    pole_x = px - 2
    frames = []
    for f in range(nframes):
        t = 2 * math.pi * f / nframes
        # displacement grows toward the free (right) end of the flag
        span = np.clip((XX - pole_x) / (S - pole_x), 0, 1)
        k = 0.42
        phase = XX * k - t * 1.15
        dy = (3.4 * span * np.sin(phase) + 1.4 * span * np.sin(phase * 0.5 + 1.7))
        srcy = YY - dy
        col = sample(base_rgb, srcy, XX)
        al = sample(base_a[..., None], srcy, XX)[..., 0]
        # cloth shading: folds from the wave slope + a gentle light from upper-left
        shade = 1.0 + 0.34 * span * np.cos(phase) + 0.10 * np.cos(phase * 0.5 + 1.7)
        shade = shade + 0.05 * (1 - YY / S)
        col = col * shade[..., None]
        out = over(sky.copy(), col, al)
        # flag pole with a little metal shading
        pg = np.clip(1 - np.abs(XX - pole_x) / 2.2, 0, 1)
        out += (pg[..., None] * np.array([120, 120, 135], np.float32))
        out += radial(pole_x, 6, (150, 150, 160), 4)   # finial
        frames.append(to_img(out))
    return frames


# =============================================================================
# 2. Stadium goal scene (the showpiece)
# =============================================================================


def build_stadium_goal(nframes=52):
    # --- static stage: sky, stands (crowd w/ depth), pitch, goal ---
    stage = vgrad((14, 20, 54), (36, 40, 78))       # night sky
    stage += radial(32, 40, (30, 26, 10), 55, 1.6)  # floodlit glow toward pitch

    horizon = 22
    # crowd stands: two banked tiers of coloured speckle, darker/denser high up
    rng = np.random.default_rng(7)
    crowd_rgb = arr()
    crowd_a = np.zeros((S, S), np.float32)
    for y in range(6, horizon):
        depth = (y - 6) / (horizon - 6)                 # 0 far/high -> 1 near/low
        dens = 0.35 + 0.5 * depth
        base_b = 40 + 90 * depth
        for x in range(0, S):
            if rng.random() < dens:
                c = rng.choice([0, 1, 2, 3], p=[0.32, 0.30, 0.20, 0.18])
                col = [(255, 223, 0), (0, 170, 70), (60, 90, 210), (230, 230, 235)][c]
                jit = rng.choice([0.6, 0.8, 1.0])       # discrete -> fewer unique colours
                crowd_rgb[y, x] = np.array(col) * jit * (base_b / 120 + 0.4)
                crowd_a[y, x] = 1.0
    # stand structure lines
    stands = to_img(stage.copy())
    dd = ImageDraw.Draw(stands)
    dd.rectangle([0, horizon - 2, S, horizon - 1], fill=(20, 22, 30))
    stage = from_img(stands)
    stage = over(stage, crowd_rgb, crowd_a)

    # pitch with perspective mowing stripes
    for y in range(horizon, S):
        d = (y - horizon) / (S - horizon)
        g1 = np.array([28 + 40 * d, 120 + 70 * d, 40 + 30 * d])
        stripe = (math.sin((y - horizon) * 0.9) > 0)
        g = g1 * (1.10 if stripe else 0.92)
        stage[y, :] = g
    stage += radial(32, 30, (35, 30, 8), 34, 2.0)   # spotlight pool near goal mouth

    # goal at the far end (upper-centre), drawn small for depth
    gx0, gx1, gtop, gbot = 18, 46, horizon - 1, horizon + 12
    def goalpaint(d):
        # net
        for x in range(gx0, gx1 + 1, 3):
            d.line([(x, gtop), (x, gbot)], fill=(220, 230, 240, 70))
        for y in range(gtop, gbot + 1, 3):
            d.line([(gx0, y), (gx1, y)], fill=(220, 230, 240, 70))
        # posts + crossbar
        d.line([(gx0, gtop), (gx0, gbot)], fill=(255, 255, 255, 255), width=2)
        d.line([(gx1, gtop), (gx1, gbot)], fill=(240, 240, 245, 255), width=2)
        d.line([(gx0, gtop), (gx1, gtop)], fill=(255, 255, 255, 255), width=2)
    goal_rgb, goal_a = draw_layer(goalpaint)
    stage_goal = over(stage.copy(), goal_rgb, goal_a)

    fnt_big = font(26)

    frames = []
    # phases: 0..30 ball flies to goal (shrinking), 30..38 net ripple, 38..end GOOOL
    for f in range(nframes):
        out = stage_goal.copy()
        # ball trajectory: from lower-right foreground toward goal mouth (perspective shrink)
        if f <= 32:
            u = easeinout(min(1.0, f / 32))
            bx = 46 - 14 * u
            by = 60 - (60 - (gbot - 1)) * u
            br = 5.5 - 4.0 * u                 # shrinks with distance
            # motion-blur trail
            for g in range(1, 6):
                uu = easeinout(max(0.0, (f - g * 0.9) / 32))
                if uu <= 0:
                    continue
                tx = 46 - 14 * uu
                ty = 60 - (60 - (gbot - 1)) * uu
                tr = (5.5 - 4.0 * uu)
                a = 0.16 * (6 - g)
                out += radial(tx, ty, (255 * a, 255 * a, 255 * a), tr + 1.5)
            out = over(out, *ball_layer(bx, by, br))
        else:
            # ball has hit the net (rest at goal mouth)
            out = over(out, *ball_layer(32, gbot - 1, 1.6))

        # net ripple on impact
        if 30 <= f <= 42:
            rp = math.sin((f - 30) / 12 * math.pi)      # 0->1->0
            def ripple(d):
                cx, cyr = 32, (gtop + gbot) // 2
                for x in range(gx0, gx1 + 1, 3):
                    off = rp * 3 * math.exp(-((x - cx) ** 2) / 60)
                    d.line([(x, gtop), (x, gbot + int(off))],
                           fill=(230, 240, 255, int(120 * rp)))
            out = over(out, *draw_layer(ripple))

        # GOOOL! + camera-flash sparkle in the crowd
        if f >= 34:
            fl = min(1.0, (f - 34) / 6)
            # random flashes in stands
            fr = np.random.default_rng(f).random((S, S)) > 0.985
            fl_mask = fr & (YY < horizon)
            out[fl_mask] = np.array([255, 255, 240])
            # text punch-in with scale/pop (scaled to FIT the 64px width)
            txt = _text_img("GOOOL!", fnt_big, (255, 223, 0), outline=(180, 40, 0))
            fit = min(1.0, 60.0 / txt.width)
            pop = (0.55 + 0.45 * easeinout(fl)) * fit
            tw = max(1, int(txt.width * pop))
            th = max(1, int(txt.height * pop))
            txt2 = txt.resize((tw, th), Image.BILINEAR)
            oimg = to_img(out)
            oimg.paste(txt2, ((S - tw) // 2, 42 - th // 2), txt2)
            out = from_img(oimg)
            out = bloom(out, 2.2, 200, 0.7)
        frames.append(to_img(out))
    return frames


def ball_layer(cx, cy, r):
    r = max(1.0, r)
    def paint(d):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(245, 248, 252, 255))
        # simple pentagon speckles + shading
        if r >= 2.2:
            d.ellipse([cx - r * 0.5, cy - r * 0.6, cx + r * 0.1, cy], fill=(255, 255, 255, 255))
            d.ellipse([cx - r * 0.2, cy - r * 0.1, cx + r * 0.4, cy + r * 0.5],
                      fill=(30, 30, 40, 255))
        # ground shadow
        d.ellipse([cx - r, cy + r - 1, cx + r, cy + r + 1], fill=(0, 0, 0, 90))
    return draw_layer(paint)


def _text_img(s, fnt, color, outline=None):
    tmp = Image.new("RGBA", (S * 6, S * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.text((4, 4), s, font=fnt, fill=color + (255,),
           stroke_width=2 if outline else 0,
           stroke_fill=(outline + (255,)) if outline else None)
    return tmp.crop(tmp.getbbox())


# =============================================================================
# 3. Gold World Cup trophy w/ glint sweep + spotlight
# =============================================================================


def _trophy_mask():
    """Alpha mask (0..1) of a stylised FIFA-ish trophy silhouette."""
    def paint(d):
        cx = 32
        # base (malachite plinth) two stacked ellipses
        d.ellipse([cx - 13, 55, cx + 13, 62], fill=(255,) * 4)
        d.ellipse([cx - 11, 50, cx + 11, 57], fill=(255,) * 4)
        # stem: two spiralling bodies rising and flaring to the globe
        d.polygon([(cx - 4, 52), (cx + 4, 52), (cx + 8, 24), (cx - 8, 24)], fill=(255,) * 4)
        # twisting figures -> approximate with a curved column
        d.polygon([(cx - 8, 26), (cx + 8, 26), (cx + 6, 16), (cx - 6, 16)], fill=(255,) * 4)
        # globe on top
        d.ellipse([cx - 10, 4, cx + 10, 24], fill=(255,) * 4)
    _, a = draw_layer(paint)
    return a


def build_trophy_glint(nframes=44):
    mask = _trophy_mask()
    # gold shading: vertical gradient + cylindrical highlight down the centre
    cx = 32.0
    cyl = np.clip(1 - np.abs(XX - cx) / 12.0, 0, 1)          # bright centre column
    vg = np.clip(1 - (YY - 4) / 58, 0.25, 1.0)              # brighter up top
    base_gold = (np.array([120, 78, 8], np.float32)[None, None]
                 + cyl[..., None] * np.array([150, 120, 30], np.float32)
                 + vg[..., None] * np.array([70, 55, 12], np.float32))

    frames = []
    for f in range(nframes):
        t = f / nframes
        # dark stage + spotlight bloom behind trophy
        out = vgrad((10, 9, 16), (26, 22, 30))
        out += radial(32, 26, (60, 52, 26), 46, 1.7)
        out += radial(32, 58, (30, 26, 16), 30, 2.0)       # base pool

        gold = base_gold.copy()
        # sweeping specular glint (diagonal band)
        phase = (t * 1.0) * (S * 1.8) - 20
        band = (XX * 0.7 + YY * 0.7)
        gl = np.exp(-((band - phase) ** 2) / 18.0)
        gold = gold + gl[..., None] * np.array([180, 165, 120], np.float32)
        # rim on left edge shadow / right edge light
        gold = gold * (0.8 + 0.4 * cyl)[..., None]

        out = over(out, gold, mask)
        # sparkle stars at the top of the glint sweep
        if 0.30 < t < 0.62:
            s = math.sin((t - 0.30) / 0.32 * math.pi)
            for (sx, sy) in [(24, 8), (40, 10), (32, 4)]:
                out += radial(sx, sy, (255 * s, 250 * s, 210 * s), 4)
        out = bloom(out, 2.0, 190, 0.85)
        frames.append(to_img(out))
    return frames


# =============================================================================
# 4. Banana free-kick with motion-blur trail
# =============================================================================


def build_freekick(nframes=46):
    # stage: pitch + goal (right) + defensive wall
    stage = vgrad((30, 46, 96), (60, 80, 140))         # dusk sky
    for y in range(30, S):
        d = (y - 30) / (S - 30)
        stripe = 1.08 if (math.sin((y - 30) * 0.8) > 0) else 0.9
        stage[y, :] = np.array([30 + 30 * d, 120 + 60 * d, 44 + 24 * d]) * stripe

    def furniture(d):
        # goal on the right, angled
        gx, gy0, gy1 = 52, 20, 44
        for yy in range(gy0, gy1 + 1, 3):
            d.line([(gx, yy), (S - 2, yy - 2)], fill=(230, 235, 245, 60))
        for xx in range(gx, S - 1, 3):
            d.line([(xx, gy0), (xx, gy1)], fill=(230, 235, 245, 60))
        d.line([(gx, gy0), (gx, gy1)], fill=(255, 255, 255, 255), width=2)
        d.line([(S - 2, gy0 - 2), (S - 2, gy1 - 2)], fill=(240, 240, 245, 255), width=2)
        d.line([(gx, gy0), (S - 2, gy0 - 2)], fill=(255, 255, 255, 255), width=2)
        # defensive wall of silhouettes mid-pitch
        for i, wx in enumerate([20, 25, 30, 35]):
            d.rectangle([wx, 30, wx + 3, 44], fill=(18, 20, 30, 255))
            d.ellipse([wx - 1, 26, wx + 4, 31], fill=(22, 24, 34, 255))
    fr, fa = draw_layer(furniture)
    stage = over(stage, fr, fa)

    # banana path: start lower-left, curve up-around the wall into top-right corner
    P0 = np.array([6, 52]); P1 = np.array([18, 8]); P2 = np.array([57, 24])

    frames = []
    for f in range(nframes):
        out = stage.copy()
        u = easeinout(min(1.0, f / (nframes - 8)))
        pos = (1 - u) ** 2 * P0 + 2 * (1 - u) * u * P1 + u ** 2 * P2
        bx, by = pos
        # motion-blur trail (fading ghosts along the curve)
        for g in range(1, 9):
            uu = u - g * 0.055
            if uu < 0:
                continue
            gp = (1 - uu) ** 2 * P0 + 2 * (1 - uu) * uu * P1 + uu ** 2 * P2
            a = 0.20 * (9 - g) / 8
            out += radial(gp[0], gp[1], (235 * a, 240 * a, 210 * a), 3.0)
        # spin lines on the ball
        out = over(out, *ball_layer(bx, by, 3.0 if u < 1 else 2.6))
        # net ripple when it arrives
        if f >= nframes - 10:
            rp = math.sin((f - (nframes - 10)) / 10 * math.pi)
            def rip(d):
                for xx in range(52, S - 1, 3):
                    off = int(rp * 3 * math.exp(-((xx - 56) ** 2) / 30))
                    d.line([(xx, 20), (xx, 44 + off)], fill=(235, 245, 255, int(120 * rp)))
            out = over(out, *draw_layer(rip))
        out = bloom(out, 1.6, 205, 0.6)
        frames.append(to_img(out))
    return frames


# =============================================================================
# 5. Samba celebration / glowing confetti with depth
# =============================================================================


def build_samba_confetti(nframes=48):
    rng = np.random.default_rng(21)
    cols = [(255, 223, 0), (0, 190, 80), (60, 110, 230), (240, 240, 245), (255, 150, 0)]
    N = 46
    part = []
    for _ in range(N):
        part.append(dict(
            x=rng.uniform(0, S), y=rng.uniform(-S, S),
            vy=rng.uniform(0.6, 1.9), sway=rng.uniform(0.5, 1.6),
            ph=rng.uniform(0, 6.28), size=rng.uniform(1.0, 2.6),
            col=cols[rng.integers(0, len(cols))],
            depth=rng.uniform(0.3, 1.0)))
    frames = []
    for f in range(nframes):
        bg = vgrad((18, 8, 30), (40, 14, 46))          # purple stage
        bg += radial(32, 60, (60, 20, 70), 50, 1.5)    # footlight glow
        # swaying dancer silhouettes at the bottom for depth
        def dancers(d):
            for i, dx in enumerate([14, 32, 50]):
                sw = math.sin(f * 0.28 + i * 1.7) * 3
                cx = dx + sw
                d.line([(cx, 64), (cx, 50)], fill=(12, 6, 18, 255), width=3)   # body
                d.ellipse([cx - 3, 44, cx + 3, 50], fill=(14, 8, 20, 255))     # head
                d.line([(cx, 54), (cx - 5, 48 - int(sw)), ], fill=(12, 6, 18, 255), width=2)
                d.line([(cx, 54), (cx + 5, 48 + int(sw))], fill=(12, 6, 18, 255), width=2)
        bg = over(bg, *draw_layer(dancers))
        # confetti, back (small/blurry) to front (big/sharp)
        glow = arr()
        for p in part:
            yy = (p["y"] + f * p["vy"]) % (S + 20) - 10
            xx = (p["x"] + math.sin(f * 0.12 + p["ph"]) * p["sway"] * 3) % S
            r = p["size"] * (0.6 + 0.6 * p["depth"])
            c = np.array(p["col"], np.float32) * (0.5 + 0.5 * p["depth"])
            glow += radial(xx, yy, c * 0.9, r + 1.6)
            bg = over(bg, *_dot(xx, yy, r, tuple(int(v) for v in c)))
        bg = bg + glow * 0.5
        bg = bloom(bg, 1.8, 170, 0.7)
        frames.append(to_img(bg))
    return frames


def _dot(cx, cy, r, col):
    def paint(d):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col + (255,))
    return draw_layer(paint)


# =============================================================================
# 6. Five golden stars w/ shine + sparkle
# =============================================================================


def build_five_stars(nframes=44):
    field = vgrad((0, 110, 44), (0, 70, 30))
    field += radial(32, 30, (0, 60, 24), 46, 1.5)
    # arc of 5 stars
    centres = []
    for i in range(5):
        ang = math.radians(-90 + (i - 2) * 26)
        cx = 32 + 20 * math.sin(math.radians((i - 2) * 30))
        cy = 26 - 6 * math.cos(math.radians((i - 2) * 30))
        centres.append((cx, cy))
    frames = []
    for f in range(nframes):
        t = f / nframes
        out = field.copy()
        for i, (cx, cy) in enumerate(centres):
            # gold gradient star via a small vertical-shaded fill
            def spaint(d):
                d.polygon(star_poly(cx, cy, 8.5), fill=(255, 210, 30, 255))
            srgb, sa = draw_layer(spaint)
            # shade the star: brighter top-left
            shade = (0.7 + 0.5 * np.clip(1 - (YY - (cy - 8)) / 16, 0, 1)
                     + 0.25 * np.clip(1 - np.abs(XX - cx) / 9, 0, 1))
            srgb = srgb * shade[..., None]
            # travelling shine sweep across all stars
            sweep = ((i / 5.0) < ((t * 1.3) % 1.0) < (i / 5.0 + 0.22))
            if sweep:
                srgb = srgb + sa[..., None] * np.array([70, 60, 30], np.float32)
            out = over(out, srgb, sa)
            # sparkle glints at points
            sp = 0.5 + 0.5 * math.sin(f * 0.4 + i)
            out += radial(cx, cy - 8.5, (200 * sp, 190 * sp, 120 * sp), 3)
        # "5x" not drawn; keep it pure stars. subtle sparkle motes
        out = bloom(out, 1.8, 195, 0.8)
        frames.append(to_img(out))
    return frames


# =============================================================================
# 7. Stylised striker striking the ball
# =============================================================================


def build_striker(nframes=40):
    stage = vgrad((26, 40, 92), (54, 74, 132))
    for y in range(38, S):
        d = (y - 38) / (S - 38)
        stripe = 1.08 if (math.sin((y - 38) * 0.9) > 0) else 0.9
        stage[y, :] = np.array([30 + 26 * d, 120 + 60 * d, 44 + 22 * d]) * stripe
    stage += radial(40, 44, (30, 26, 8), 30, 2.0)

    frames = []
    for f in range(nframes):
        t = f / nframes
        out = stage.copy()
        # wind-up (0..0.5) then strike (0.5..0.7) then follow-through
        if t < 0.5:
            leg = -0.9 + 1.0 * (t / 0.5)         # back-swing
        elif t < 0.68:
            leg = 0.1 + 2.6 * ((t - 0.5) / 0.18)  # swing through
        else:
            leg = 2.7
        hipx, hipy = 26, 42
        kneex = hipx + 6 * math.cos(leg - 0.4)
        kneey = hipy + 8 * math.sin(leg - 0.4)
        footx = kneex + 8 * math.cos(leg)
        footy = kneey + 8 * math.sin(leg)

        def player(d):
            # torso lean (yellow shirt), shaded
            d.line([(24, 30), (hipx, hipy)], fill=(255, 223, 0, 255), width=5)
            d.line([(24, 30), (26, 20)], fill=(255, 223, 0, 255), width=4)      # neck
            d.ellipse([22, 12, 30, 20], fill=(120, 80, 55, 255))               # head
            # planted leg
            d.line([(hipx, hipy), (hipx - 3, 58)], fill=(40, 45, 80, 255), width=4)
            # kicking leg (blue shorts->socks)
            d.line([(hipx, hipy), (kneex, kneey)], fill=(30, 40, 90, 255), width=4)
            d.line([(kneex, kneey), (footx, footy)], fill=(240, 240, 245, 255), width=3)
            # arms for balance
            d.line([(25, 32), (16, 30 + 6 * math.sin(leg))], fill=(255, 223, 0, 255), width=3)
        pr, pa = draw_layer(player)
        # rim light (green) on the player's right edge
        rim = np.roll(pa, 1, axis=1) - pa
        pr = pr + np.clip(rim, 0, 1)[..., None] * np.array([0, 120, 50], np.float32)
        out = over(out, pr, pa)

        # ball: sits at ~(44,52); launches after contact (t>0.62)
        if t < 0.62:
            bx, by, br = 44, 52, 3.2
            out = over(out, *ball_layer(bx, by, br))
        else:
            u = (t - 0.62) / 0.38
            bx = 44 + 26 * u
            by = 52 - 30 * u * (1 - 0.4 * u)
            for g in range(1, 7):
                uu = u - g * 0.08
                if uu < 0:
                    continue
                tx = 44 + 26 * uu
                ty = 52 - 30 * uu * (1 - 0.4 * uu)
                a = 0.22 * (7 - g) / 6
                out += radial(tx, ty, (235 * a, 240 * a, 210 * a), 3)
            out = over(out, *ball_layer(bx, by, 3.0))
        out = bloom(out, 1.6, 205, 0.6)
        frames.append(to_img(out))
    return frames


# =============================================================================
# 8. Metallic gradient "BRASIL" wordmark w/ specular sweep
# =============================================================================


def build_brasil_metal(nframes=40):
    fnt = font(30)
    txt = _text_img("BRASIL", fnt, (255, 255, 255), outline=(0, 30, 90))
    maxw = S - 4
    if txt.width > maxw:
        txt = txt.resize((maxw, int(txt.height * maxw / txt.width)), Image.LANCZOS)
    tmask = np.asarray(txt.split()[-1], np.float32) / 255.0
    tw, th = txt.width, txt.height
    ox, oy = (S - tw) // 2, (S - th) // 2
    # place mask on full canvas
    M = np.zeros((S, S), np.float32)
    M[oy:oy + th, ox:ox + tw] = tmask[:th, :tw]

    # gold metallic vertical gradient within the glyphs
    yy_n = np.clip((YY - oy) / max(1, th), 0, 1)
    metal = (np.array([120, 84, 8], np.float32)[None, None]
             + (1 - np.abs(yy_n - 0.35))[..., None] * np.array([150, 120, 40], np.float32))
    frames = []
    for f in range(nframes):
        t = f / nframes
        bg = vgrad((0, 30, 90), (0, 90, 44))          # blue->green field
        bg += radial(32, 32, (0, 20, 40), 50, 1.4)
        g = metal.copy()
        # specular sweep left->right across the letters
        phase = t * (S + 20) - 10
        spec = np.exp(-((XX - phase) ** 2) / 20.0)
        g = g + spec[..., None] * np.array([180, 170, 120], np.float32)
        out = over(bg, g, M)
        out = bloom(out, 2.0, 190, 0.8)
        frames.append(to_img(out))
    return frames


# =============================================================================
# 9. Fireworks over a stadium silhouette
# =============================================================================


def build_fireworks(nframes=54):
    # stadium bowl silhouette + floodlights on a night sky
    base = vgrad((6, 8, 26), (18, 20, 44))
    def stad(d):
        d.ellipse([-6, 46, S + 6, 74], fill=(10, 12, 26, 255))     # bowl
        d.ellipse([6, 50, S - 6, 66], fill=(22, 40, 30, 255))       # pitch glow rim
        for lx in [8, 30, 54]:
            d.line([(lx, 48), (lx, 40)], fill=(40, 42, 60, 255), width=1)
            d.ellipse([lx - 2, 37, lx + 2, 41], fill=(255, 250, 210, 255))
    sr, sa = draw_layer(stad)
    base = over(base, sr, sa)

    rng = np.random.default_rng(5)
    # schedule several bursts
    bursts = []
    for _ in range(6):
        bursts.append(dict(
            cx=rng.uniform(12, 52), cy=rng.uniform(10, 30),
            t0=rng.uniform(0, 0.75), col=rng.choice([0, 1, 2, 3]),
            n=rng.integers(14, 22), spd=rng.uniform(6, 10)))
    palette = [(255, 223, 0), (0, 210, 90), (80, 140, 255), (255, 90, 120)]
    frames = []
    for f in range(nframes):
        t = f / nframes
        out = base.copy()
        for b in bursts:
            age = (t - b["t0"]) % 1.0
            if age < 0 or age > 0.42:
                continue
            col = np.array(palette[b["col"]], np.float32)
            fade = max(0.0, 1 - age / 0.42)
            for k in range(b["n"]):
                ang = 2 * math.pi * k / b["n"]
                ca, sa = math.cos(ang), math.sin(ang)
                rr = b["spd"] * age * 2.3
                px = b["cx"] + rr * ca
                py = b["cy"] + rr * sa + 8 * age * age          # gravity droop
                out += radial(px, py, col * fade, 2.4)
                # inner ring of embers -> fuller burst + a short spark trail
                ri = rr * 0.55
                out += radial(b["cx"] + ri * ca, b["cy"] + ri * sa + 4 * age * age,
                              col * fade * 0.8, 1.8)
                out += radial(b["cx"] + rr * 0.8 * ca, b["cy"] + rr * 0.8 * sa,
                              np.array([255, 250, 220]) * fade * 0.5, 1.3)
            # bright core flash early
            if age < 0.14:
                out += radial(b["cx"], b["cy"], col * (1 - age / 0.14), 7)
        out = bloom(out, 2.2, 160, 0.9)
        frames.append(to_img(out))
    return frames


# =============================================================================
# 10. Crowd tifo mosaic — flag forms across the stands (bonus)
# =============================================================================


def build_tifo(nframes=40):
    # a grid of "cards" held up by a crowd that flip to reveal the flag, with a shimmer
    G = 16                      # grid cells across
    cell = S / G
    # target flag image at grid resolution
    def paint(d):
        d.rectangle([0, 0, S, S], fill=GREEN + (255,))
        d.polygon([(32, 6), (58, 32), (32, 58), (6, 32)], fill=YELLOW + (255,))
        d.ellipse([21, 21, 43, 43], fill=BLUE + (255,))
        d.arc([21, 24, 43, 46], 20, 160, fill=WHITE + (255,), width=3)
    flag_rgb, _ = draw_layer(paint)
    # downsample to grid then back to blocky
    small = to_img(flag_rgb).resize((G, G), Image.BILINEAR)
    tgt = np.asarray(small, np.float32)

    rng = np.random.default_rng(3)
    reveal_t = rng.uniform(0, 0.55, (G, G))       # when each card flips
    frames = []
    for f in range(nframes):
        t = f / nframes
        grid = np.zeros((G, G, 3), np.float32)
        for gy in range(G):
            for gx in range(G):
                p = np.clip((t - reveal_t[gy, gx]) / 0.2, 0, 1)
                back = np.array([30, 30, 40], np.float32)
                shimmer = 1.0 + 0.12 * math.sin(f * 0.5 + gx + gy)
                grid[gy, gx] = (back * (1 - p) + tgt[gy, gx] * p) * shimmer
        img = to_img(grid).resize((S, S), Image.NEAREST)
        out = from_img(img)
        # gap lines between cards for the "held card" look
        out[np.rint(YY / cell) * cell == YY] *= 0.7
        out[np.rint(XX / cell) * cell == XX] *= 0.7
        out = bloom(out, 1.4, 200, 0.5)
        frames.append(to_img(out))
    return frames


# =============================================================================
# build all
# =============================================================================

BUILDERS = [
    ("brd_flag_wave",      "Waving Brazil flag with cloth folds over a soft sky", build_flag_wave, 70, 10),
    ("brd_stadium_goal",   "Stadium goal: ball driven in, net ripple, GOOOL! + crowd flash", build_stadium_goal, 55, 14),
    ("brd_trophy_glint",   "Shaded gold World Cup trophy, spotlight + sweeping glint", build_trophy_glint, 60, 10),
    ("brd_freekick_banana","Roberto-Carlos banana free-kick with motion-blur trail", build_freekick, 55, 12),
    ("brd_samba_confetti", "Samba dancers + glowing layered confetti", build_samba_confetti, 60, 10),
    ("brd_five_stars",     "Five golden champion stars with shine + sparkle", build_five_stars, 60, 10),
    ("brd_striker",        "Stylised striker winding up and striking the ball", build_striker, 55, 8),
    ("brd_brasil_metal",   "Metallic gold BRASIL wordmark with specular sweep", build_brasil_metal, 60, 10),
    ("brd_fireworks",      "Fireworks bursting over a floodlit stadium", build_fireworks, 60, 12),
    ("brd_crowd_tifo",     "Crowd tifo mosaic flipping to reveal the flag", build_tifo, 65, 10),
]


TARGET = 95_000          # keep every gif comfortably under the ~100 KB BLE ceiling


def adaptive_save(frames, path, ms):
    """Write a rich full-colour GIF, auto-tuning colours (then frame count) to stay < TARGET.
    The 64x64 panel only shows ~126 colours/frame, so 64-144 colours reads as full colour."""
    floor = 48
    for colors in (144, 128, 112, 96, 80, 72, 64, 56, floor):
        save_gif(frames, path, ms=ms, colors=colors, dither=True)
        if os.path.getsize(path) <= TARGET:
            return colors, len(frames)
    # still too big even at the colour floor: gently thin frames (drop every 8th)
    fr = list(frames)
    while os.path.getsize(path) > TARGET and len(fr) > 30:
        fr = [f for i, f in enumerate(fr) if i % 8 != 0]
        save_gif(fr, path, ms=ms, colors=floor, dither=True)
    return floor, len(fr)


def main():
    manifest = []
    montage_imgs = []
    for name, desc, fn, ms, dwell in BUILDERS:
        print(f"building {name} ...")
        frames = fn()
        path = os.path.join(HERE, name + ".gif")
        colors, nf = adaptive_save(frames, path, ms)
        preview_png(path, scale=6)
        size = os.path.getsize(path)
        flag = "  <-- OVER 100KB" if size > 100_000 else ""
        print(f"    {name}: {nf}f  {colors}c  {size/1024:.1f} KB{flag}")
        manifest.append((name, desc, nf, size, dwell, ms, colors))
        montage_imgs.append((name, frames[len(frames) // 3]))

    # contact sheet
    cols = 5
    rows = (len(montage_imgs) + cols - 1) // cols
    pad, sc, lbl = 6, 3, 10
    cw, ch = S * sc + pad, S * sc + pad + lbl
    sheet = Image.new("RGB", (cols * cw + pad, rows * ch + pad), (16, 16, 20))
    dd = ImageDraw.Draw(sheet)
    sfnt = font(9)
    for i, (name, im) in enumerate(montage_imgs):
        r, c = divmod(i, cols)
        x = pad + c * cw
        y = pad + r * ch
        sheet.paste(im.resize((S * sc, S * sc), Image.NEAREST), (x, y))
        dd.text((x, y + S * sc + 1), name.replace("brd_", ""), font=sfnt, fill=(210, 210, 220))
    sheet.save(os.path.join(HERE, "_montage.png"))
    print(f"\nwrote _montage.png ({cols}x{rows})")

    total = sum(m[3] for m in manifest)
    print(f"\nTOTAL: {len(manifest)} gifs, {total/1024:.1f} KB")
    for name, desc, nf, size, dwell, ms, colors in manifest:
        print(f"  {name:22s} {nf:3d}f  {colors}c  {size/1024:6.1f} KB  dwell {dwell}s")
    return manifest


if __name__ == "__main__":
    main()
