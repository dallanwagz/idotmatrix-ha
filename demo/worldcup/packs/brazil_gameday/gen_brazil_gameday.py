#!/usr/bin/env python3
"""gen_brazil_gameday.py — an EXTENSIVE, full-colour, cinematic Brazil World Cup GAME-DAY pack
for the 64x64 iDotMatrix RGB panel.

This is a NEW, richer set than brazil_deluxe/ — built to loop all game long on a fan's panel
during a live match. Twelve animations: waving flag, GOOOL! net-buster, stadium bicycle kick,
banana free-kick, samba + confetti, gold trophy, PENTA five stars, VAI BRASIL scroller, crowd
tifo mosaic, stadium fireworks, player wheel-away celebration, and a spinning Brazil football.

Everything leans on numpy for pixel math (gradients, shading, glow, motion blur) and Pillow for
compositing, then is written through assetlib.save_gif(..., colors=256, dither=True) so the 64x64
decoder keeps the colour. FILL THE FRAME is a hard rule here — every scene covers all 64x64.

Run:  python3 gen_brazil_gameday.py
Produces: all brg_*.gif, a *_preview.png per gif, and _montage.png. Files only — never touches BLE.
"""
import os
import sys
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

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
    """Vertical gradient array top->bottom (fills the whole frame)."""
    t = (YY / (S - 1))[..., None]
    return np.array(top, np.float32) * (1 - t) + np.array(bot, np.float32) * t


def hgrad(left, right):
    t = (XX / (S - 1))[..., None]
    return np.array(left, np.float32) * (1 - t) + np.array(right, np.float32) * t


def radial(cx, cy, color, radius, gamma=2.0):
    """Additive radial glow array (0 at edge -> color at centre)."""
    d = np.sqrt((XX - cx) ** 2 + (YY - cy) ** 2) / max(0.001, radius)
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


def ball_layer(cx, cy, r, spin=0.0):
    """A little football with pentagon speckles + ground shadow. spin rotates the panels."""
    r = max(1.0, r)

    def paint(d):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(245, 248, 252, 255))
        if r >= 2.2:
            # rotating black pentagon patches
            for k in range(5):
                ang = spin + k * 2 * math.pi / 5
                px = cx + r * 0.55 * math.cos(ang)
                py = cy + r * 0.55 * math.sin(ang)
                pr = r * 0.28
                d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(24, 26, 34, 255))
            cr = r * 0.26
            d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(24, 26, 34, 255))
        # top-left specular
        d.ellipse([cx - r * 0.6, cy - r * 0.7, cx - r * 0.1, cy - r * 0.2],
                  fill=(255, 255, 255, 200))
        # ground shadow
        d.ellipse([cx - r, cy + r - 1, cx + r, cy + r + 1], fill=(0, 0, 0, 90))
    return draw_layer(paint)


def _text_img(s, fnt, color, outline=None, ow=2):
    tmp = Image.new("RGBA", (S * 6, S * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.text((6, 6), s, font=fnt, fill=color + (255,),
           stroke_width=ow if outline else 0,
           stroke_fill=(outline + (255,)) if outline else None)
    return tmp.crop(tmp.getbbox())


def paste_fit(out_arr, txt_img, cx, cy, maxw=60, scale=1.0):
    """Paste an RGBA text image centred at (cx,cy), auto-fit to maxw*scale. Returns array."""
    w = txt_img.width
    fit = min(1.0, float(maxw) / w) * scale
    tw = max(1, int(txt_img.width * fit))
    th = max(1, int(txt_img.height * fit))
    t2 = txt_img.resize((tw, th), Image.BILINEAR)
    oimg = to_img(out_arr)
    oimg.paste(t2, (int(cx - tw / 2), int(cy - th / 2)), t2)
    return from_img(oimg)


# =============================================================================
# 1. Waving Brazil flag with cloth folds + soft sky
# =============================================================================


def build_flag_wave(nframes=44):
    px, py0, py1 = 7, 6, 57            # flag body; pole at x=px
    def paint(d):
        d.rectangle([px, py0, S - 1, py1], fill=GREEN + (255,))
        cx, cy = (px + S) / 2 + 1, (py0 + py1) / 2
        w, h = (S - px) / 2 - 2, (py1 - py0) / 2 - 2
        d.polygon([(cx, cy - h), (cx + w, cy), (cx, cy + h), (cx - w, cy)],
                  fill=YELLOW + (255,))
        r = 12
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLUE + (255,))
        d.arc([cx - r, cy - r + 3, cx + r, cy + r + 3], 20, 160, fill=WHITE + (255,), width=3)
        for sx, sy, sr in [(-6, -4, 1.5), (3, -7, 1.2), (7, 2, 1.4), (-3, 5, 1.3),
                           (1, 1, 1.7), (-8, 1, 1.1), (6, 7, 1.1), (-2, -8, 1.0),
                           (9, -3, 1.0), (0, 9, 1.1)]:
            d.ellipse([cx + sx - sr, cy + sy - sr, cx + sx + sr, cy + sy + sr],
                      fill=WHITE + (255,))
    base_rgb, base_a = draw_layer(paint)

    sky = vgrad((70, 128, 200), (182, 218, 242))
    sky = sky + radial(12, 10, (70, 62, 34), 42, gamma=2.2)   # sun glow upper-left

    pole_x = px - 2
    frames = []
    for f in range(nframes):
        t = 2 * math.pi * f / nframes
        span = np.clip((XX - pole_x) / (S - pole_x), 0, 1)
        k = 0.42
        phase = XX * k - t * 1.15
        dy = (3.6 * span * np.sin(phase) + 1.5 * span * np.sin(phase * 0.5 + 1.7))
        srcy = YY - dy
        col = sample(base_rgb, srcy, XX)
        al = sample(base_a[..., None], srcy, XX)[..., 0]
        shade = 1.0 + 0.34 * span * np.cos(phase) + 0.10 * np.cos(phase * 0.5 + 1.7)
        shade = shade + 0.05 * (1 - YY / S)
        col = col * shade[..., None]
        out = over(sky.copy(), col, al)
        pg = np.clip(1 - np.abs(XX - pole_x) / 2.2, 0, 1)
        out += (pg[..., None] * np.array([120, 120, 135], np.float32))
        out += radial(pole_x, 5, (150, 150, 160), 4)
        frames.append(to_img(out))
    return frames


# =============================================================================
# 2. GOOOL! — ball rockets into the net, explosion of green/yellow, flashing text
# =============================================================================


def build_gooool(nframes=48):
    # a full-frame net backdrop with a goal frame; ball flies from bottom into top-centre
    def netpaint(d):
        d.rectangle([0, 0, S, S], fill=(18, 24, 40, 255))
        for x in range(2, S, 4):
            d.line([(x, 6), (x, S - 2)], fill=(150, 170, 200, 90))
        for y in range(6, S, 4):
            d.line([(2, y), (S - 2, y)], fill=(150, 170, 200, 90))
        # goal frame
        d.line([(2, 6), (S - 3, 6)], fill=(255, 255, 255, 255), width=3)
        d.line([(2, 6), (2, S - 1)], fill=(255, 255, 255, 255), width=3)
        d.line([(S - 3, 6), (S - 3, S - 1)], fill=(240, 240, 245, 255), width=3)
    net_rgb, net_a = draw_layer(netpaint)
    stage = over(vgrad((22, 30, 52), (10, 14, 28)), net_rgb, net_a)

    fnt = font(30)
    txt = _text_img("GOOOL!", fnt, YELLOW, outline=(180, 30, 0), ow=2)

    frames = []
    for f in range(nframes):
        t = f / nframes
        out = stage.copy()
        # ball flight: from bottom-centre up to net target (32,20), grows slightly then sticks
        if f <= 20:
            u = easeinout(f / 20)
            bx = 32 + (10 * (1 - u)) * math.sin(f * 0.6)
            by = 66 - 46 * u
            br = 4.0 + 1.5 * u
            for g in range(1, 7):
                uu = max(0.0, (f - g) / 20)
                if uu <= 0:
                    continue
                ty = 66 - 46 * uu
                a = 0.16 * (7 - g)
                out += radial(32, ty, (255 * a, 240 * a, 120 * a), br + 2)
            out = over(out, *ball_layer(bx, by, br, spin=f * 0.5))
        else:
            out = over(out, *ball_layer(32, 21, 5.0, spin=f * 0.2))
            # net bulge ripple around impact
            rp = math.sin(min(1.0, (f - 20) / 16) * math.pi)
            out += radial(32, 22, (120 * rp, 140 * rp, 170 * rp), 22, 1.4)

        # explosion of green/yellow particles from impact point
        if f >= 18:
            age = (f - 18) / (nframes - 18)
            rng = np.random.default_rng(99)
            for k in range(26):
                ang = 2 * math.pi * k / 26 + 0.3
                rr = 40 * easeinout(min(1.0, age * 1.4)) * (0.6 + 0.4 * rng.random())
                pxp = 32 + rr * math.cos(ang)
                pyp = 22 + rr * math.sin(ang)
                col = (255, 223, 0) if k % 2 else (0, 200, 80)
                fade = max(0.0, 1 - age)
                out += radial(pxp, pyp, tuple(c * fade for c in col), 3)

        # flashing GOOOL! text (blink on/off), punch-in scale
        if f >= 22 and (f // 3) % 2 == 0:
            pop = 0.7 + 0.3 * easeinout(min(1.0, (f - 22) / 8))
            out = paste_fit(out, txt, 32, 46, maxw=60, scale=pop)
        out = bloom(out, 2.2, 195, 0.8)
        frames.append(to_img(out))
    return frames


# =============================================================================
# 3. Stadium bicycle kick — full pitch, depth crowd, striker overhead kick, net
# =============================================================================


def build_bicycle_kick(nframes=48):
    horizon = 20
    stage = vgrad((16, 22, 56), (34, 40, 76))
    stage += radial(32, 40, (32, 28, 12), 56, 1.6)
    # depth crowd speckle
    rng = np.random.default_rng(11)
    crowd_rgb = arr()
    crowd_a = np.zeros((S, S), np.float32)
    for y in range(4, horizon):
        depth = (y - 4) / (horizon - 4)
        dens = 0.35 + 0.5 * depth
        base_b = 40 + 90 * depth
        for x in range(0, S):
            if rng.random() < dens:
                c = rng.choice([0, 1, 2, 3], p=[0.32, 0.30, 0.20, 0.18])
                col = [(255, 223, 0), (0, 170, 70), (60, 90, 210), (230, 230, 235)][c]
                jit = rng.choice([0.6, 0.8, 1.0])
                crowd_rgb[y, x] = np.array(col) * jit * (base_b / 120 + 0.4)
                crowd_a[y, x] = 1.0
    tmp = to_img(stage.copy())
    ImageDraw.Draw(tmp).rectangle([0, horizon - 2, S, horizon - 1], fill=(20, 22, 30))
    stage = from_img(tmp)
    stage = over(stage, crowd_rgb, crowd_a)
    # pitch stripes
    for y in range(horizon, S):
        d = (y - horizon) / (S - horizon)
        g1 = np.array([26 + 40 * d, 120 + 70 * d, 40 + 30 * d])
        g = g1 * (1.10 if (math.sin((y - horizon) * 0.9) > 0) else 0.90)
        stage[y, :] = g
    stage += radial(40, 34, (34, 30, 8), 30, 2.0)
    # small goal upper-left for depth
    def goalpaint(d):
        gx0, gx1, gt, gb = 6, 26, horizon - 1, horizon + 10
        for x in range(gx0, gx1 + 1, 3):
            d.line([(x, gt), (x, gb)], fill=(220, 230, 240, 70))
        for y in range(gt, gb + 1, 3):
            d.line([(gx0, y), (gx1, y)], fill=(220, 230, 240, 70))
        d.line([(gx0, gt), (gx0, gb)], fill=(255, 255, 255, 255), width=2)
        d.line([(gx1, gt), (gx1, gb)], fill=(240, 240, 245, 255), width=2)
        d.line([(gx0, gt), (gx1, gt)], fill=(255, 255, 255, 255), width=2)
    stage = over(stage, *draw_layer(goalpaint))

    frames = []
    for f in range(nframes):
        t = f / nframes
        out = stage.copy()
        # player rotates upside-down for the overhead kick around pivot (40,40)
        pang = -0.5 + 3.4 * easeinout(min(1.0, t / 0.8))   # body rotation
        px0, py0 = 40, 40                                   # hip pivot
        def player(d):
            # torso vector
            tx = px0 + 12 * math.cos(pang)
            ty = py0 + 12 * math.sin(pang)
            d.line([(px0, py0), (tx, ty)], fill=(255, 223, 0, 255), width=5)   # yellow shirt
            # head at torso top
            d.ellipse([tx - 4, ty - 4, tx + 4, ty + 4], fill=(120, 82, 56, 255))
            # striking leg (kicks up/over)
            legang = pang - 1.3
            kx = px0 + 11 * math.cos(legang)
            ky = py0 + 11 * math.sin(legang)
            fx = kx + 10 * math.cos(legang - 0.5)
            fy = ky + 10 * math.sin(legang - 0.5)
            d.line([(px0, py0), (kx, ky)], fill=(30, 40, 90, 255), width=4)     # thigh
            d.line([(kx, ky), (fx, fy)], fill=(240, 240, 245, 255), width=3)    # boot
            # trailing leg
            lx = px0 + 10 * math.cos(pang + 1.1)
            ly = py0 + 10 * math.sin(pang + 1.1)
            d.line([(px0, py0), (lx, ly)], fill=(30, 40, 90, 255), width=4)
            # arms out for balance
            ax = tx + 8 * math.cos(pang + 1.6)
            ay = ty + 8 * math.sin(pang + 1.6)
            d.line([(tx, ty), (ax, ay)], fill=(255, 223, 0, 255), width=3)
        pr, pa = draw_layer(player)
        rim = np.clip(np.roll(pa, -1, axis=1) - pa, 0, 1)
        pr = pr + rim[..., None] * np.array([0, 130, 55], np.float32)
        out = over(out, pr, pa)

        # ball: near the striking foot early, then rockets toward the goal
        legang = pang - 1.3
        kx = px0 + 11 * math.cos(legang) + 10 * math.cos(legang - 0.5)
        ky = py0 + 11 * math.sin(legang) + 10 * math.sin(legang - 0.5)
        if t < 0.62:
            out = over(out, *ball_layer(kx, ky, 3.4, spin=f * 0.4))
        else:
            u = (t - 0.62) / 0.38
            bx = kx + (12 - kx) * u
            by = ky + ((horizon + 4) - ky) * u
            br = 3.4 - 1.6 * u
            for g in range(1, 7):
                uu = max(0.0, u - g * 0.08)
                if uu <= 0:
                    continue
                tx = kx + (12 - kx) * uu
                ty = ky + ((horizon + 4) - ky) * uu
                a = 0.2 * (7 - g) / 6
                out += radial(tx, ty, (255 * a, 240 * a, 200 * a), br + 1)
            out = over(out, *ball_layer(bx, by, max(1.4, br), spin=f * 0.6))
        out = bloom(out, 1.8, 200, 0.6)
        frames.append(to_img(out))
    return frames


# =============================================================================
# 4. Banana free-kick curving past a wall into the top corner
# =============================================================================


def build_freekick(nframes=46):
    stage = vgrad((32, 48, 100), (64, 84, 146))        # dusk sky
    for y in range(30, S):
        d = (y - 30) / (S - 30)
        stripe = 1.08 if (math.sin((y - 30) * 0.8) > 0) else 0.9
        stage[y, :] = np.array([30 + 30 * d, 120 + 60 * d, 44 + 24 * d]) * stripe

    def furniture(d):
        gx, gy0, gy1 = 50, 16, 42
        for yy in range(gy0, gy1 + 1, 3):
            d.line([(gx, yy), (S - 2, yy - 2)], fill=(230, 235, 245, 60))
        for xx in range(gx, S - 1, 3):
            d.line([(xx, gy0), (xx, gy1)], fill=(230, 235, 245, 60))
        d.line([(gx, gy0), (gx, gy1)], fill=(255, 255, 255, 255), width=2)
        d.line([(S - 2, gy0 - 2), (S - 2, gy1 - 2)], fill=(240, 240, 245, 255), width=2)
        d.line([(gx, gy0), (S - 2, gy0 - 2)], fill=(255, 255, 255, 255), width=2)
        for wx in [20, 25, 30, 35]:
            d.rectangle([wx, 30, wx + 3, 44], fill=(18, 20, 30, 255))
            d.ellipse([wx - 1, 26, wx + 4, 31], fill=(22, 24, 34, 255))
    stage = over(stage, *draw_layer(furniture))

    P0 = np.array([6, 52]); P1 = np.array([16, 6]); P2 = np.array([58, 20])
    frames = []
    for f in range(nframes):
        out = stage.copy()
        u = easeinout(min(1.0, f / (nframes - 8)))
        pos = (1 - u) ** 2 * P0 + 2 * (1 - u) * u * P1 + u ** 2 * P2
        bx, by = pos
        for g in range(1, 10):
            uu = u - g * 0.05
            if uu < 0:
                continue
            gp = (1 - uu) ** 2 * P0 + 2 * (1 - uu) * uu * P1 + uu ** 2 * P2
            a = 0.22 * (10 - g) / 9
            out += radial(gp[0], gp[1], (245 * a, 240 * a, 210 * a), 3.0)
        out = over(out, *ball_layer(bx, by, 3.0 if u < 1 else 2.6, spin=f * 0.7))
        if f >= nframes - 10:
            rp = math.sin((f - (nframes - 10)) / 10 * math.pi)
            def rip(d):
                for xx in range(50, S - 1, 3):
                    off = int(rp * 3 * math.exp(-((xx - 56) ** 2) / 30))
                    d.line([(xx, 16), (xx, 42 + off)], fill=(235, 245, 255, int(120 * rp)))
            out = over(out, *draw_layer(rip))
        out = bloom(out, 1.6, 205, 0.6)
        frames.append(to_img(out))
    return frames


# =============================================================================
# 5. Samba celebration — dancers + drummers silhouettes, glowing confetti
# =============================================================================


def build_samba(nframes=48):
    rng = np.random.default_rng(21)
    cols = [(255, 223, 0), (0, 190, 80), (60, 110, 230), (240, 240, 245), (255, 150, 0)]
    N = 48
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
        bg = vgrad((26, 8, 40), (58, 16, 60))          # magenta stage
        bg += radial(32, 62, (80, 24, 90), 54, 1.4)    # footlight glow
        bg += radial(10, 4, (70, 30, 20), 40, 2.0)

        def dancers(d):
            xs = [10, 24, 40, 54]
            for i, dx in enumerate(xs):
                sw = math.sin(f * 0.30 + i * 1.7) * 3
                cx = dx + sw
                d.line([(cx, 64), (cx, 48)], fill=(10, 5, 16, 255), width=3)     # body
                d.ellipse([cx - 3, 42, cx + 3, 48], fill=(12, 6, 18, 255))       # head
                d.line([(cx, 52), (cx - 6, 46 - int(sw))], fill=(10, 5, 16, 255), width=2)
                d.line([(cx, 52), (cx + 6, 46 + int(sw))], fill=(10, 5, 16, 255), width=2)
                if i == 1:   # drummer: surdo drum
                    d.ellipse([cx - 7, 52, cx - 1, 60], fill=(200, 180, 40, 255))
        bg = over(bg, *draw_layer(dancers))

        glow = arr()
        for p in part:
            yy = (p["y"] + f * p["vy"]) % (S + 20) - 10
            xx = (p["x"] + math.sin(f * 0.12 + p["ph"]) * p["sway"] * 3) % S
            r = p["size"] * (0.6 + 0.6 * p["depth"])
            c = np.array(p["col"], np.float32) * (0.5 + 0.5 * p["depth"])
            glow += radial(xx, yy, c * 0.9, r + 1.6)

            def _dot(d, xx=xx, yy=yy, r=r, c=c):
                d.ellipse([xx - r, yy - r, xx + r, yy + r],
                          fill=tuple(int(v) for v in c) + (255,))
            bg = over(bg, *draw_layer(_dot))
        bg = bg + glow * 0.5
        bg = bloom(bg, 1.8, 170, 0.7)
        frames.append(to_img(bg))
    return frames


# =============================================================================
# 6. Gold World Cup trophy w/ sweeping glint + rays
# =============================================================================


def _trophy_mask():
    def paint(d):
        cx = 32
        d.ellipse([cx - 13, 55, cx + 13, 62], fill=(255,) * 4)
        d.ellipse([cx - 11, 50, cx + 11, 57], fill=(255,) * 4)
        d.polygon([(cx - 4, 52), (cx + 4, 52), (cx + 8, 24), (cx - 8, 24)], fill=(255,) * 4)
        d.polygon([(cx - 8, 26), (cx + 8, 26), (cx + 6, 16), (cx - 6, 16)], fill=(255,) * 4)
        d.ellipse([cx - 10, 4, cx + 10, 24], fill=(255,) * 4)
    _, a = draw_layer(paint)
    return a


def build_trophy(nframes=44):
    mask = _trophy_mask()
    cx = 32.0
    cyl = np.clip(1 - np.abs(XX - cx) / 12.0, 0, 1)
    vg = np.clip(1 - (YY - 4) / 58, 0.25, 1.0)
    base_gold = (np.array([120, 78, 8], np.float32)[None, None]
                 + cyl[..., None] * np.array([150, 120, 30], np.float32)
                 + vg[..., None] * np.array([70, 55, 12], np.float32))
    frames = []
    for f in range(nframes):
        t = f / nframes
        # dark stage but FILLED with rotating light rays + spotlight glow (no dead corners)
        out = vgrad((14, 10, 20), (30, 22, 34))
        for k in range(12):
            ang = k * math.pi / 6 + t * 0.6
            ex = 32 + 90 * math.cos(ang)
            ey = 30 + 90 * math.sin(ang)
            b = 0.10 + 0.06 * math.sin(t * 6.28 + k)
            out += radial((32 + ex) / 2, (30 + ey) / 2, (60 * b * 10, 50 * b * 10, 24 * b * 10), 60, 2.4)
        out += radial(32, 26, (70, 60, 30), 48, 1.7)
        out += radial(32, 58, (34, 28, 16), 30, 2.0)

        gold = base_gold.copy()
        phase = (t * 1.0) * (S * 1.8) - 20
        band = (XX * 0.7 + YY * 0.7)
        gl = np.exp(-((band - phase) ** 2) / 18.0)
        gold = gold + gl[..., None] * np.array([185, 168, 122], np.float32)
        gold = gold * (0.8 + 0.4 * cyl)[..., None]
        out = over(out, gold, mask)
        if 0.28 < t < 0.60:
            s = math.sin((t - 0.28) / 0.32 * math.pi)
            for (sx, sy) in [(24, 8), (40, 10), (32, 4)]:
                out += radial(sx, sy, (255 * s, 250 * s, 210 * s), 4)
        out = bloom(out, 2.0, 185, 0.9)
        frames.append(to_img(out))
    return frames


# =============================================================================
# 7. PENTA — five golden champion stars with shine + "PENTA" pulse
# =============================================================================


def build_penta(nframes=44):
    field = vgrad((0, 120, 48), (0, 66, 28))
    field += radial(32, 28, (0, 70, 28), 50, 1.5)
    centres = []
    for i in range(5):
        cx = 32 + 21 * math.sin(math.radians((i - 2) * 30))
        cy = 22 - 5 * math.cos(math.radians((i - 2) * 30))
        centres.append((cx, cy))
    fnt = font(20)
    txt = _text_img("PENTA", fnt, YELLOW, outline=(0, 60, 24), ow=2)
    frames = []
    for f in range(nframes):
        t = f / nframes
        out = field.copy()
        for i, (cx, cy) in enumerate(centres):
            def spaint(d):
                d.polygon(star_poly(cx, cy, 8.5), fill=(255, 210, 30, 255))
            srgb, sa = draw_layer(spaint)
            shade = (0.7 + 0.5 * np.clip(1 - (YY - (cy - 8)) / 16, 0, 1)
                     + 0.25 * np.clip(1 - np.abs(XX - cx) / 9, 0, 1))
            srgb = srgb * shade[..., None]
            if (i / 5.0) < ((t * 1.3) % 1.0) < (i / 5.0 + 0.22):
                srgb = srgb + sa[..., None] * np.array([70, 60, 30], np.float32)
            out = over(out, srgb, sa)
            sp = 0.5 + 0.5 * math.sin(f * 0.4 + i)
            out += radial(cx, cy - 8.5, (200 * sp, 190 * sp, 120 * sp), 3)
        # PENTA wordmark pulsing along the bottom
        pulse = 0.9 + 0.12 * math.sin(f * 0.5)
        out = paste_fit(out, txt, 32, 50, maxw=52, scale=pulse)
        out = bloom(out, 1.8, 190, 0.8)
        frames.append(to_img(out))
    return frames


# =============================================================================
# 8. VAI BRASIL — bold scroller over a green/yellow diagonal-stripe scene
# =============================================================================


def build_vai_brasil(nframes=48):
    fnt = font(30)
    txt = _text_img("VAI BRASIL", fnt, YELLOW, outline=(0, 40, 100), ow=2)
    # scale text to a readable height (~26px) but let it be WIDE and scroll
    th = 30
    tw = int(txt.width * th / txt.height)
    txt = txt.resize((tw, th), Image.LANCZOS)
    span = tw + S
    frames = []
    for f in range(nframes):
        t = f / nframes
        # animated diagonal green/yellow chevron background, FULL frame
        d = (XX * 0.5 + YY * 0.5) * 0.5 - f * 1.3
        band = (np.sin(d * 0.5) > 0)
        bg = np.where(band[..., None],
                      np.array(GREEN, np.float32), np.array([0, 120, 46], np.float32))
        bg = bg + 0.0
        # yellow diagonal accent stripes
        stripe = (np.sin((XX + YY) * 0.4 - f * 0.6) > 0.7)
        bg = np.where(stripe[..., None], np.array([255, 223, 0], np.float32), bg)
        bg += radial(32, 32, (0, 40, 18), 55, 1.3)
        # scroll the wordmark right->left, vertically centred
        ox = int(S - (f / nframes) * span)
        oy = (S - th) // 2
        oimg = to_img(bg)
        # shadow then text
        sh = Image.new("RGBA", txt.size, (0, 0, 0, 0))
        sh.paste(txt, (0, 0), txt)
        oimg.paste(txt, (ox, oy), txt)
        out = from_img(oimg)
        out = bloom(out, 1.6, 205, 0.6)
        frames.append(to_img(out))
    return frames


# =============================================================================
# 9. Crowd tifo mosaic — cards flip to reveal the flag
# =============================================================================


def build_tifo(nframes=42):
    G = 16
    cell = S / G
    def paint(d):
        d.rectangle([0, 0, S, S], fill=GREEN + (255,))
        d.polygon([(32, 5), (59, 32), (32, 59), (5, 32)], fill=YELLOW + (255,))
        d.ellipse([20, 20, 44, 44], fill=BLUE + (255,))
        d.arc([20, 23, 44, 47], 20, 160, fill=WHITE + (255,), width=3)
    flag_rgb, _ = draw_layer(paint)
    small = to_img(flag_rgb).resize((G, G), Image.BILINEAR)
    tgt = np.asarray(small, np.float32)
    rng = np.random.default_rng(3)
    reveal_t = rng.uniform(0, 0.55, (G, G))
    frames = []
    for f in range(nframes):
        t = f / nframes
        grid = np.zeros((G, G, 3), np.float32)
        for gy in range(G):
            for gx in range(G):
                p = np.clip((t - reveal_t[gy, gx]) / 0.2, 0, 1)
                back = np.array([34, 34, 46], np.float32)
                shimmer = 1.0 + 0.12 * math.sin(f * 0.5 + gx + gy)
                grid[gy, gx] = (back * (1 - p) + tgt[gy, gx] * p) * shimmer
        img = to_img(grid).resize((S, S), Image.NEAREST)
        out = from_img(img)
        out[np.rint(YY / cell) * cell == YY] *= 0.7
        out[np.rint(XX / cell) * cell == XX] *= 0.7
        out = bloom(out, 1.4, 200, 0.5)
        frames.append(to_img(out))
    return frames


# =============================================================================
# 10. Fireworks over a floodlit stadium bowl
# =============================================================================


def build_fireworks(nframes=52):
    base = vgrad((8, 10, 30), (20, 22, 48))
    def stad(d):
        d.ellipse([-8, 46, S + 8, 76], fill=(10, 12, 26, 255))
        d.ellipse([6, 50, S - 6, 66], fill=(24, 46, 34, 255))
        for lx in [8, 30, 54]:
            d.line([(lx, 48), (lx, 40)], fill=(40, 42, 60, 255), width=1)
            d.ellipse([lx - 2, 37, lx + 2, 41], fill=(255, 250, 210, 255))
    base = over(base, *draw_layer(stad))
    rng = np.random.default_rng(5)
    bursts = []
    for _ in range(7):
        bursts.append(dict(
            cx=rng.uniform(12, 52), cy=rng.uniform(8, 30),
            t0=rng.uniform(0, 0.78), col=int(rng.integers(0, 4)),
            n=int(rng.integers(14, 22)), spd=rng.uniform(6, 10)))
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
                py = b["cy"] + rr * sa + 8 * age * age
                out += radial(px, py, col * fade, 2.4)
                ri = rr * 0.55
                out += radial(b["cx"] + ri * ca, b["cy"] + ri * sa + 4 * age * age,
                              col * fade * 0.8, 1.8)
                out += radial(b["cx"] + rr * 0.8 * ca, b["cy"] + rr * 0.8 * sa,
                              np.array([255, 250, 220]) * fade * 0.5, 1.3)
            if age < 0.14:
                out += radial(b["cx"], b["cy"], col * (1 - age / 0.14), 7)
        out = bloom(out, 2.2, 155, 0.9)
        frames.append(to_img(out))
    return frames


# =============================================================================
# 11. Player celebration — striker wheels away arms-out with a flag
# =============================================================================


def build_celebration(nframes=44):
    stage = vgrad((28, 42, 96), (56, 78, 138))
    for y in range(40, S):
        d = (y - 40) / (S - 40)
        stripe = 1.08 if (math.sin((y - 40) * 0.9) > 0) else 0.9
        stage[y, :] = np.array([30 + 26 * d, 120 + 60 * d, 44 + 22 * d]) * stripe
    # depth crowd band up top
    rng = np.random.default_rng(31)
    for y in range(0, 16):
        for x in range(0, S):
            if rng.random() < 0.4:
                col = [(255, 223, 0), (0, 170, 70), (60, 90, 210), (230, 230, 235)][int(rng.integers(0, 4))]
                stage[y, x] = np.array(col) * rng.choice([0.6, 0.8, 1.0])
    stage += radial(32, 40, (30, 26, 10), 40, 1.8)

    frames = []
    for f in range(nframes):
        t = f / nframes
        out = stage.copy()
        # player runs slightly across, arms out, flag streaming behind
        run = math.sin(f * 0.5)
        hipx = 30 + 3 * math.sin(t * 6.28)
        hipy = 40
        def player(d):
            # flag streaming from the hand, wavy, behind the runner
            fx0 = hipx - 8
            pts = [(fx0, 26)]
            for s in range(1, 9):
                pts.append((fx0 - s * 3, 22 + 4 * math.sin(f * 0.4 + s * 0.7)))
            # flag as green/yellow ribbon
            for s in range(len(pts) - 1):
                col = (255, 223, 0) if s % 2 else (0, 180, 70)
                d.line([pts[s], pts[s + 1]], fill=col + (255,), width=4)
            # torso (yellow)
            d.line([(hipx, hipy), (hipx + 1, 24)], fill=(255, 223, 0, 255), width=6)
            d.ellipse([hipx - 3, 16, hipx + 5, 24], fill=(120, 82, 56, 255))    # head
            # arms out wide (celebration)
            d.line([(hipx + 1, 27), (hipx + 12, 22 - int(3 * run))], fill=(255, 223, 0, 255), width=3)
            d.line([(hipx + 1, 27), (hipx - 8, 26)], fill=(255, 223, 0, 255), width=3)
            # legs running
            d.line([(hipx, hipy), (hipx + 6 * run, 56)], fill=(30, 40, 90, 255), width=4)
            d.line([(hipx, hipy), (hipx - 6 * run, 56)], fill=(30, 40, 90, 255), width=4)
        pr, pa = draw_layer(player)
        rim = np.clip(np.roll(pa, -1, axis=1) - pa, 0, 1)
        pr = pr + rim[..., None] * np.array([0, 120, 50], np.float32)
        out = over(out, pr, pa)
        # sparkle confetti drifting
        for k in range(10):
            xx = (k * 6 + f * 1.2) % S
            yy = (k * 9 + f * 1.6) % S
            col = (255, 223, 0) if k % 2 else (0, 200, 80)
            out += radial(xx, yy, tuple(c * 0.5 for c in col), 2)
        out = bloom(out, 1.6, 200, 0.6)
        frames.append(to_img(out))
    return frames


# =============================================================================
# 12. Spinning Brazil football with trailing glow
# =============================================================================


def build_spin_ball(nframes=40):
    # radial gradient stage (green->dark) filling frame + faint rotating rays
    frames = []
    for f in range(nframes):
        t = f / nframes
        out = vgrad((0, 130, 52), (0, 50, 22))
        out += radial(32, 32, (0, 70, 30), 55, 1.4)
        for k in range(8):
            ang = k * math.pi / 4 + t * 6.28
            ex = 32 + 60 * math.cos(ang)
            ey = 32 + 60 * math.sin(ang)
            out += radial((32 + ex) / 2, (32 + ey) / 2, (0, 40, 18), 40, 2.2)
        # the football, large + spinning; a big Brazil ball with yellow/green panels
        cx, cy, r = 32, 32, 18
        spin = t * 6.28

        def ballpaint(d):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(250, 250, 252, 255))
            # spinning coloured panels (alternating green/yellow/blue)
            pcols = [(0, 156, 59), (255, 223, 0), (0, 39, 118), (0, 156, 59), (255, 223, 0)]
            for k in range(5):
                ang = spin + k * 2 * math.pi / 5
                px = cx + r * 0.52 * math.cos(ang)
                py = cy + r * 0.52 * math.sin(ang)
                pr = r * 0.34
                d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=pcols[k] + (255,))
            cr = r * 0.32
            d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(255, 223, 0, 255))
            # outline + specular
            d.arc([cx - r, cy - r, cx + r, cy + r], 0, 360, fill=(20, 24, 30, 255), width=1)
            d.ellipse([cx - r * 0.6, cy - r * 0.7, cx - r * 0.1, cy - r * 0.2],
                      fill=(255, 255, 255, 150))
        out = over(out, *draw_layer(ballpaint))
        out = bloom(out, 1.8, 205, 0.6)
        frames.append(to_img(out))
    return frames


# =============================================================================
# build all
# =============================================================================

BUILDERS = [
    ("brg_flag_wave",      "Waving Brazil flag with cloth folds over a soft sky", build_flag_wave, 70),
    ("brg_gooool",         "GOOOL! ball buries into the net, green/yellow explosion, flashing text", build_gooool, 60),
    ("brg_bicycle_kick",   "Stadium bicycle kick: overhead volley, depth crowd, net", build_bicycle_kick, 60),
    ("brg_freekick_banana","Banana free-kick curving past the wall into the top corner", build_freekick, 55),
    ("brg_samba",          "Samba dancers + drummer with glowing layered confetti", build_samba, 60),
    ("brg_trophy",         "Gold World Cup trophy with sweeping glint + light rays", build_trophy, 60),
    ("brg_penta",          "PENTA: five golden champion stars shining", build_penta, 60),
    ("brg_vai_brasil",     "VAI BRASIL scrolling over animated green/yellow chevrons", build_vai_brasil, 60),
    ("brg_tifo",           "Crowd tifo mosaic flipping to reveal the flag", build_tifo, 65),
    ("brg_fireworks",      "Fireworks bursting over a floodlit stadium bowl", build_fireworks, 60),
    ("brg_celebration",    "Striker wheeling away arms-out with a streaming flag", build_celebration, 60),
    ("brg_spin_ball",      "Spinning Brazil-colours football with glow", build_spin_ball, 60),
]

TARGET = 95_000


def adaptive_save(frames, path, ms):
    floor = 48
    for colors in (144, 128, 112, 96, 80, 72, 64, 56, floor):
        save_gif(frames, path, ms=ms, colors=colors, dither=True)
        if os.path.getsize(path) <= TARGET:
            return colors, len(frames)
    fr = list(frames)
    while os.path.getsize(path) > TARGET and len(fr) > 24:
        fr = [f for i, f in enumerate(fr) if i % 8 != 0]
        save_gif(fr, path, ms=ms, colors=floor, dither=True)
    return floor, len(fr)


def main():
    manifest = []
    montage_imgs = []
    for name, desc, fn, ms in BUILDERS:
        print(f"building {name} ...")
        frames = fn()
        path = os.path.join(HERE, name + ".gif")
        colors, nf = adaptive_save(frames, path, ms)
        preview_png(path, scale=6)
        size = os.path.getsize(path)
        flag = "  <-- OVER 95KB" if size > TARGET else ""
        print(f"    {name}: {nf}f  {colors}c  {size/1024:.1f} KB{flag}")
        manifest.append((name, desc, nf, size, ms, colors))
        montage_imgs.append((name, frames[len(frames) // 3]))

    cols = 4
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
        dd.text((x, y + S * sc + 1), name.replace("brg_", ""), font=sfnt, fill=(210, 210, 220))
    sheet.save(os.path.join(HERE, "_montage.png"))
    print(f"\nwrote _montage.png ({cols}x{rows})")

    total = sum(m[3] for m in manifest)
    print(f"\nTOTAL: {len(manifest)} gifs, {total/1024:.1f} KB")
    for name, desc, nf, size, ms, colors in manifest:
        flag = "  <-- OVER 95KB" if size > TARGET else ""
        print(f"  {name:22s} {nf:3d}f  {colors}c  {size/1024:6.1f} KB{flag}")
    return manifest


if __name__ == "__main__":
    main()
