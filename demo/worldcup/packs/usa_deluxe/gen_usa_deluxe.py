#!/usr/bin/env python3
"""Generate the USA (United States) World Cup **DELUXE** animation pack for a 64x64 iDotMatrix panel.

Unlike the old flat-16-colour pack, these lean into everything the 64x64 panel's decoder proved it can
render: up to ~256 colours/frame, gradients, soft glows, cloth shading, spotlights and smooth motion.

Technique: most scenes are drawn at a 4x supersample (256x256) with PIL, glows/gradients are composited
in float via numpy (screen/additive blend), then downsampled to 64x64 with LANCZOS for anti-aliased,
shaded edges. `save_gif(..., colors=N, dither=True)` keeps the colour depth.

Run:  python3 gen_usa_deluxe.py
  -> (re)creates every usd_*.gif + a *_preview.png beside it + _montage.png contact sheet.
Builds ONLY files; never touches Bluetooth / the panel.
"""
import math, os, sys
sys.path.insert(0, "/Users/dallan/repo/tyler/idotmatrix-ha/pi-quickstart")
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from assetlib import save_gif, preview_png

HERE = os.path.dirname(os.path.abspath(__file__))
S = 64
SS = 4                 # supersample factor
HI = S * SS            # 256

# ---- USA palette (LED-bright) ----
RED   = (200, 28, 46)
RED_L = (232, 74, 92)
RED_D = (120, 14, 30)
WHITE = (245, 245, 250)
NAVY  = (10, 30, 96)
NAVY_L= (44, 78, 168)
NAVY_D= (4, 14, 52)
GOLD  = (255, 205, 40)
GOLD_L= (255, 244, 176)
GOLD_D= (150, 96, 8)
SKY_T = (26, 40, 92)   # deep sky top
SKY_B = (120, 150, 210)# soft sky bottom

MANIFEST = []          # (filename, frames, bytes, ms, dwell, desc)


# ----------------------------------------------------------------- font helper
def afont(px):
    for f in ("/System/Library/Fonts/Supplemental/Arial Black.ttf",
              "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, px)
            except Exception:
                pass
    return ImageFont.load_default()


# ----------------------------------------------------------------- numpy utils
def vgrad(h, w, top, bot):
    """Vertical gradient as float HxWx3."""
    t = np.linspace(0, 1, h)[:, None, None]
    top = np.array(top, float); bot = np.array(bot, float)
    return top[None, None, :] * (1 - t) + bot[None, None, :] * t + np.zeros((h, w, 1))


def radial(h, w, cx, cy, r, color, power=2.0):
    """Additive radial glow, float HxWx3, falls to 0 at radius r."""
    ys, xs = np.mgrid[0:h, 0:w]
    d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2) / max(r, 1e-3)
    fall = np.clip(1 - d, 0, 1) ** power
    return fall[:, :, None] * np.array(color, float)[None, None, :]


def screen(base, add):
    """Screen blend two 0..255 float buffers (glow that never dulls)."""
    b = base / 255.0; a = np.clip(add, 0, 255) / 255.0
    return (1 - (1 - b) * (1 - a)) * 255.0


def to_img(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def arr(img):
    return np.asarray(img.convert("RGB"), float)


def down(img):
    """Downsample a HI-res frame to the 64 panel with anti-aliasing."""
    return img.resize((S, S), Image.LANCZOS)


def star_poly(cx, cy, r, rot=-math.pi / 2, inner=0.40):
    pts = []
    for i in range(10):
        a = rot + i * math.pi / 5
        rr = r if i % 2 == 0 else r * inner
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


CAP = 98_000   # keep a little margin under the ~100 KB BLE-safe ceiling


def emit(frames, name, ms, colors=200, dither=True, dwell=10, desc=""):
    """Write the GIF, then auto-fit under CAP: shave colours first (protects motion),
    then drop frames as a last resort. Keeps the pack reproducible & BLE-safe."""
    path = os.path.join(HERE, name + ".gif")
    cur = list(frames)
    c = colors
    save_gif(cur, path, ms=ms, colors=c, dither=dither)
    sz = os.path.getsize(path)
    # 1) shave colour depth down to a floor (dither keeps gradients smooth even ~110 colours)
    while sz > CAP and c > 110:
        c = max(110, int(c * 0.85))
        save_gif(cur, path, ms=ms, colors=c, dither=dither)
        sz = os.path.getsize(path)
    # 2) trim frames gradually (~12% at a time, evenly spaced) if colour cuts weren't enough
    while sz > CAP and len(cur) > 22:
        keep = max(22, int(len(cur) * 0.88))
        idx = sorted(set(np.linspace(0, len(cur) - 1, keep).round().astype(int)))
        cur = [cur[i] for i in idx]
        save_gif(cur, path, ms=ms, colors=c, dither=dither)
        sz = os.path.getsize(path)
    # 3) final safety: only if still over, drop colours to the hard minimum
    while sz > CAP and c > 64:
        c = max(64, int(c * 0.85))
        save_gif(cur, path, ms=ms, colors=c, dither=dither)
        sz = os.path.getsize(path)
    preview_png(path, scale=8)
    flag = "  <-- OVER 100KB" if sz > 100_000 else ""
    print(f"    {name:22s} {len(cur):3d}f  {c}col  {sz/1024:6.1f}KB{flag}")
    MANIFEST.append((name + ".gif", len(cur), sz, ms, dwell, desc))
    return path


# ============================================================ 1. FLAG WAVE =====
def gen_flag_wave(N=34):
    """Stars & Stripes as a real waving banner: cloth folds shaded by a light source,
    a second-harmonic ripple, soft blue sky gradient behind the flowing top/bottom edges."""
    # --- build the flat flag texture once, at HI res ---
    tex = Image.new("RGB", (HI, HI), NAVY)
    td = ImageDraw.Draw(tex)
    stripe_h = HI / 13.0
    for i in range(13):
        col = RED if i % 2 == 0 else WHITE
        td.rectangle([0, i * stripe_h, HI, (i + 1) * stripe_h], fill=col)
    cw, chh = HI * 0.40, stripe_h * 7
    td.rectangle([0, 0, cw, chh], fill=NAVY)
    # subtle canton shading (top-lit)
    td.rectangle([0, 0, cw, chh], fill=NAVY)
    for r in range(5):
        for cc in range(6):
            sx = cw * (0.10 + cc * 0.16)
            sy = chh * (0.12 + r * 0.19)
            td.polygon(star_poly(sx, sy, HI * 0.022), fill=WHITE)
    tex_np = arr(tex)

    # sky behind
    sky = vgrad(HI, HI, SKY_T, SKY_B)

    frames = []
    band_top, band_bot = int(HI * 0.13), int(HI * 0.87)
    xs = np.arange(HI)
    for f in range(N):
        ph = 2 * math.pi * f / N
        # column vertical displacement (two harmonics) + edge taper
        off = (HI * 0.055 * np.sin(2 * math.pi * xs / HI * 1.4 - ph)
               + HI * 0.028 * np.sin(2 * math.pi * xs / HI * 2.7 - 1.7 * ph))
        # cloth shading from local slope (folds facing light get brighter)
        slope = np.gradient(off)
        shade = np.clip(1.0 + 0.9 * slope / (HI * 0.02), 0.45, 1.7)

        ys = np.arange(HI)
        src_y = np.clip(np.round(ys[:, None] - off[None, :]).astype(int), 0, HI - 1)
        warped = tex_np[src_y, xs[None, :], :] * shade[None, :, None]

        # compose: sky, then flag band where inside taper
        out = sky.copy()
        band = np.zeros((HI, HI), bool)
        band[band_top:band_bot, :] = True
        out[band] = warped[band]
        # soft top/bottom cloth edge highlight
        img = to_img(out)
        frames.append(down(img))
    emit(frames, "usd_flag_wave", ms=55, colors=200, dwell=15,
         desc="Waving Stars & Stripes with cloth folds, light-shaded, soft sky behind")


# ============================================================ 2. STADIUM GOAL ==
def gen_stadium_goal(N=42):
    """Cinematic goal: shaded pitch with mow-stripes, tiered crowd with depth, a goal &
    net, the ball driven in low, the net ripples, then a red/white/blue 'GOAL!' flash."""
    # static backdrop (crowd + stands + pitch) rendered once
    def backdrop():
        base = np.zeros((HI, HI, 3), float)
        # night sky glow over stadium
        base[:] = vgrad(HI, HI, (12, 16, 40), (30, 34, 70))
        img = to_img(base); d = ImageDraw.Draw(img)
        horizon = int(HI * 0.42)
        # far stands (dark) + tiers
        d.rectangle([0, int(HI*0.16), HI, horizon], fill=(28, 30, 52))
        # crowd speckle with depth (denser/darker up top, brighter lower)
        rng = np.random.default_rng(7)
        for band, (y0, y1, br) in enumerate([(int(HI*0.17), int(HI*0.27), 90),
                                             (int(HI*0.27), int(HI*0.36), 140),
                                             (int(HI*0.36), horizon, 190)]):
            n = 1400
            xs = rng.integers(0, HI, n); ys = rng.integers(y0, y1, n)
            for x, y in zip(xs, ys):
                c = rng.choice([0, 1, 2, 3])
                col = [(br, br-30, br-30), (br-30, br-30, br), (br, br, br-20), (br-40,br-40,br-40)][c]
                d.point((x, y), fill=tuple(max(0, v) for v in col))
        # advertising board glow strip
        d.rectangle([0, horizon-4, HI, horizon+2], fill=(20, 60, 120))
        # pitch with mow stripes + perspective shading
        pitch = arr(img)
        ys = np.arange(horizon, HI)
        for i, y in enumerate(ys):
            depth = (y - horizon) / (HI - horizon)
            g = int(38 + 70 * depth)
            stripe = 12 if ((y // int(HI*0.05)) % 2 == 0) else 0
            pitch[y, :, :] = np.array([18 + stripe*0.4, g + stripe, 24 + stripe*0.4])
        img = to_img(pitch); d = ImageDraw.Draw(img)
        return img

    bg = backdrop()
    # goal geometry (centered, receding)
    gx0, gx1 = int(HI*0.22), int(HI*0.78)
    gy0, gy1 = int(HI*0.30), int(HI*0.58)
    frames = []
    for f in range(N):
        img = bg.copy(); d = ImageDraw.Draw(img)
        # net (drawn subtly)
        for x in range(gx0, gx1 + 1, int(HI*0.028)):
            d.line([x, gy0, x, gy1], fill=(150, 155, 175), width=1)
        for y in range(gy0, gy1 + 1, int(HI*0.028)):
            d.line([gx0, y, gx1, y], fill=(150, 155, 175), width=1)
        # goal frame (bright, lit)
        d.line([gx0, gy0, gx1, gy0], fill=(240, 240, 250), width=SS)
        d.line([gx0, gy0, gx0, gy1], fill=(240, 240, 250), width=SS)
        d.line([gx1, gy0, gx1, gy1], fill=(240, 240, 250), width=SS)

        t = f / N
        # ball flies from lower-right foreground to inside goal (first ~55%)
        if t < 0.55:
            p = t / 0.55
            bx = HI * (0.86 - 0.40 * p)
            by = HI * (0.86 - 0.44 * p)
            br = HI * (0.055 - 0.028 * p)
            # motion-blur trail
            for k in range(1, 5):
                tx = bx + (HI*0.05) * k; ty = by + (HI*0.055) * k
                d.ellipse([tx-br, ty-br, tx+br, ty+br], fill=(220, 220, 225))
            d.ellipse([bx-br, by-br, bx+br, by+br], fill=(250, 250, 255))
            d.ellipse([bx-br*0.5, by-br*0.6, bx+br*0.2, by+br*0.1], fill=(255, 255, 255))
        else:
            # ball resting in net, net ripple
            bx, by, br = HI*0.5, gy1 - HI*0.05, HI*0.03
            rip = math.sin((t - 0.55) * 20) * (1 - (t - 0.55) / 0.45)
            for x in range(gx0, gx1 + 1, int(HI*0.028)):
                dxr = int(rip * 6 * math.sin((x - gx0) * 0.05))
                d.line([x, gy0, x, gy1 + dxr], fill=(170, 175, 195), width=1)
            d.ellipse([bx-br, by-br, bx+br, by+br], fill=(250, 250, 255))

        out = arr(img)
        # GOAL flash: after ball is in, pulse a red/white/blue glow + text
        if t >= 0.58:
            pulse = 0.5 + 0.5 * math.sin((t - 0.58) * 30)
            glow = (radial(HI, HI, HI*0.5, HI*0.35, HI*0.6, (60, 20, 30), 1.5)
                    + radial(HI, HI, HI*0.2, HI*0.4, HI*0.4, (10, 20, 60), 1.5)
                    + radial(HI, HI, HI*0.8, HI*0.4, HI*0.4, (60, 20, 30), 1.5))
            out = screen(out, glow * (0.5 + 0.5 * pulse))
            img = to_img(out); d = ImageDraw.Draw(img)
            fnt = afont(int(HI * 0.24))
            txt = "GOAL!"
            bb = d.textbbox((0, 0), txt, font=fnt)
            tw, th = bb[2]-bb[0], bb[3]-bb[1]
            tx, ty = (HI - tw)//2 - bb[0], int(HI*0.66) - bb[1]
            for dx, dy in ((3,3),(-3,3),(3,-3),(-3,-3)):
                d.text((tx+dx, ty+dy), txt, font=fnt, fill=(0, 0, 0))
            col = (255, 60, 60) if int((t-0.58)*30) % 2 == 0 else (255, 255, 255)
            d.text((tx, ty), txt, font=fnt, fill=col)
            out = arr(img)
        frames.append(down(to_img(out)))
    emit(frames, "usd_stadium_goal", ms=55, colors=220, dwell=20,
         desc="Stadium goal: shaded pitch, tiered crowd, driven shot, net ripple, GOAL! flash")


# ============================================================ 3. TROPHY GLINT ==
def gen_trophy_glint(N=36):
    """Shaded gold World Cup-style trophy on a plinth, soft spotlight, a specular glint
    sweeps across the metal; sparkle stars pop where the highlight lands."""
    # build trophy shape mask + base shaded gold once
    def trophy_layer():
        img = Image.new("RGB", (HI, HI), (0, 0, 0))
        d = ImageDraw.Draw(img)
        cx = HI * 0.5
        # two curved figures holding a globe -> approximate FIFA silhouette with cup form
        # stem/base
        d.polygon([(cx-HI*0.11, HI*0.86), (cx+HI*0.11, HI*0.86),
                   (cx+HI*0.05, HI*0.70), (cx-HI*0.05, HI*0.70)], fill=GOLD)
        d.ellipse([cx-HI*0.14, HI*0.84, cx+HI*0.14, HI*0.92], fill=GOLD)
        # body: a spiraling twisted column widening to a globe on top
        pts_l, pts_r = [], []
        for i in range(21):
            u = i / 20.0
            y = HI * (0.70 - 0.40 * u)
            w = HI * (0.05 + 0.11 * u ** 1.5) + HI * 0.02 * math.sin(u * 9)
            pts_l.append((cx - w, y)); pts_r.append((cx + w, y))
        d.polygon(pts_l + pts_r[::-1], fill=GOLD)
        # globe on top
        d.ellipse([cx-HI*0.17, HI*0.16, cx+HI*0.17, HI*0.40], fill=GOLD)
        return img
    tl = trophy_layer()
    mask = (arr(tl).sum(2) > 30)  # trophy pixels
    # base shading: vertical light + left-lit
    ys, xs = np.mgrid[0:HI, 0:HI]
    cx = HI * 0.5
    base = arr(tl)
    lit = np.clip(1.15 - 0.6 * (xs - (cx - HI*0.12)) / (HI*0.34), 0.35, 1.35)
    vshade = np.clip(1.2 - 0.5 * ys / HI, 0.55, 1.25)
    shaded = base.copy()
    g = np.array(GOLD, float)
    shaded[mask] = np.clip(g[None, :] * (lit[mask] * vshade[mask])[:, None]
                           + np.array(GOLD_D, float) * 0.25, 0, 255)

    frames = []
    for f in range(N):
        t = f / N
        # spotlight background
        bgc = vgrad(HI, HI, (14, 12, 26), (40, 34, 20))
        spot = radial(HI, HI, HI*0.5, HI*0.34, HI*0.62, (90, 78, 40), 1.6)
        out = screen(bgc, spot)
        # trophy composited
        out[mask] = shaded[mask]
        # specular glint: a diagonal bright band sweeping left->right
        gpos = (t * 1.6 - 0.3) * HI
        band = np.exp(-((xs - ys*0.5 - gpos) ** 2) / (2 * (HI*0.05) ** 2))
        glint = (band[:, :, None] * np.array(GOLD_L, float)[None, None, :]) * mask[:, :, None]
        out = screen(out, glint * 1.1)
        img = to_img(out); d = ImageDraw.Draw(img)
        # sparkle where glint crosses top globe
        gx = gpos + HI*0.5*0.5
        if HI*0.20 < gx < HI*0.80:
            sy = HI*0.27
            for rr, col in ((HI*0.05, GOLD_L), (HI*0.09, (255, 255, 220))):
                d.line([gx-rr, sy, gx+rr, sy], fill=col, width=2)
                d.line([gx, sy-rr, gx, sy+rr], fill=col, width=2)
        frames.append(down(img))
    emit(frames, "usd_trophy_glint", ms=60, colors=180, dwell=20,
         desc="Shaded gold trophy under a spotlight with a sweeping specular glint & sparkle")


# ============================================================ 4. FIREWORKS =====
def gen_fireworks(N=40):
    """Red/white/blue fireworks bursting over a silhouetted stadium skyline, with rising
    shells, layered glow, gravity-fed sparks and a glowing crowd horizon."""
    rng = np.random.default_rng(21)
    COLORS = [(255, 66, 74), (255, 255, 255), (80, 130, 255)]  # red / white / blue
    # schedule bursts so the sky is never empty: staggered, overlapping, wrap the loop
    bursts = []
    for k in range(11):
        bursts.append((int((k * N / 11 + rng.integers(0, 3)) % N),
                       rng.uniform(0.14, 0.86) * HI,
                       rng.uniform(0.12, 0.40) * HI,
                       COLORS[k % 3],
                       int(rng.integers(30, 46))))
    # spark angles/speeds per burst (two-ring for a fuller burst)
    spk = []
    for (_, _, _, _, ns) in bursts:
        ang = rng.uniform(0, 2 * math.pi, ns)
        spd = (rng.uniform(0.55, 1.0, ns) ** 0.7) * HI * 0.020
        spk.append((ang, spd))

    # skyline silhouette
    sky_base = vgrad(HI, HI, (6, 6, 22), (22, 16, 44))
    skyline = to_img(sky_base); sd = ImageDraw.Draw(skyline)
    horizon = int(HI*0.80)
    sd.rectangle([0, horizon, HI, HI], fill=(8, 10, 24))
    # stadium bowl
    sd.ellipse([HI*0.18, horizon-HI*0.10, HI*0.82, horizon+HI*0.14], fill=(14, 16, 34))
    sd.arc([HI*0.20, horizon-HI*0.09, HI*0.80, horizon+HI*0.05], 180, 360, fill=(60, 80, 150), width=2)
    # crowd glow on horizon
    sky_np = arr(skyline)
    sky_np = screen(sky_np, radial(HI, HI, HI*0.5, horizon, HI*0.5, (30, 40, 80), 2.0))

    LIFE = 30
    frames = []
    for f in range(N):
        out = sky_np.copy()
        for bi, (bf, bx, by, col, ns) in enumerate(bursts):
            # age with loop wrap so bursts that start late also show at loop top
            age = (f - bf) % N
            colf = np.array(col, float)
            if age >= LIFE:
                # brief rising shell just before the next birth
                lead = (bf - f) % N
                if 0 < lead <= 7:
                    p = lead / 7.0
                    ry = HI - (HI - by) * (1 - p)
                    out = screen(out, radial(HI, HI, bx, ry, HI*0.045, colf*0.85, 2.5))
                continue
            ang, spd = spk[bi]
            life = age / LIFE
            r = spd * age * (1.0 - 0.35 * life)          # ease-out expansion
            gy = HI * 0.00035 * age * age                # gentle gravity droop
            px = bx + np.cos(ang) * r
            py = by + np.sin(ang) * r + gy
            fade = (1 - life) ** 0.6
            twk = 0.7 + 0.3 * math.sin(f * 1.7 + bi)     # sparkle twinkle
            # additive sparks (bright, full colour)
            img = to_img(np.zeros((HI, HI, 3), float)); ld = ImageDraw.Draw(img)
            br = 2.2 if life < 0.5 else 1.6
            for x, y in zip(px, py):
                c = tuple(min(255, int(v * (0.55 + 0.6 * fade) * twk)) for v in col)
                ld.ellipse([x-br, y-br, x+br, y+br], fill=c)
            layer = arr(img)
            # bright flash core early, softer coloured glow through the burst
            core = radial(HI, HI, bx, by, HI*0.10, np.array((255,255,255),float),
                          2.4) * max(0.0, 1 - life*3)
            glow = radial(HI, HI, bx, by, HI*0.14*(0.5+life), colf*fade, 2.0)
            out = screen(out, layer)
            out = screen(out, core)
            out = screen(out, glow)
        frames.append(down(to_img(out)))
    emit(frames, "usd_fireworks", ms=55, colors=200, dwell=20,
         desc="Red/white/blue fireworks over a silhouetted stadium with glow & gravity sparks")


# ============================================================ 5. STRIKER ======
def gen_striker(N=30):
    """Stylized USMNT striker in a shaded kit, plants and strikes; ball rockets away with
    a motion trail and a small impact flash. Low sun rim-light for depth."""
    frames = []
    horizon = int(HI*0.72)
    for f in range(N):
        t = f / N
        bg = vgrad(HI, HI, (40, 60, 120), (150, 180, 210))
        # pitch
        out = bg.copy()
        pv = vgrad(HI - horizon, HI, (24, 96, 40), (16, 64, 28))
        out[horizon:, :, :] = pv
        # sun rim glow low-right
        out = screen(out, radial(HI, HI, HI*0.86, horizon-HI*0.05, HI*0.5, (120, 90, 30), 1.8))
        img = to_img(out); d = ImageDraw.Draw(img)

        # swing phase: wind-up (0-0.4) -> contact (~0.45) -> follow (0.45-1)
        swing = math.sin(min(t, 0.5) / 0.5 * math.pi - math.pi/2) * 0.5 + 0.5  # 0->1
        cx, cy = HI*0.40, HI*0.42  # torso center
        white = (235, 235, 245); navy = NAVY; navyL = NAVY_L; skin = (222, 170, 130)
        skinD = (180, 130, 96)
        # torso (navy jersey, shaded)
        d.polygon([(cx-HI*0.06, cy-HI*0.08), (cx+HI*0.07, cy-HI*0.08),
                   (cx+HI*0.05, cy+HI*0.10), (cx-HI*0.05, cy+HI*0.10)], fill=navy)
        d.polygon([(cx-HI*0.06, cy-HI*0.08), (cx-HI*0.02, cy-HI*0.08),
                   (cx-HI*0.02, cy+HI*0.10), (cx-HI*0.05, cy+HI*0.10)], fill=navyL)
        # head
        hx, hy = cx+HI*0.01, cy-HI*0.15
        d.ellipse([hx-HI*0.045, hy-HI*0.05, hx+HI*0.045, hy+HI*0.05], fill=skin)
        d.ellipse([hx-HI*0.045, hy-HI*0.05, hx-HI*0.005, hy+HI*0.05], fill=skinD)
        # standing leg (left) white shorts + sock
        d.line([cx-HI*0.02, cy+HI*0.10, cx-HI*0.05, horizon], fill=skin, width=int(HI*0.035))
        d.line([cx-HI*0.05, horizon, cx-HI*0.05, horizon+HI*0.06], fill=white, width=int(HI*0.03))
        # kicking leg swings from back to front
        kang = math.radians(200 - 150 * swing)
        kx = cx + HI*0.02 + math.cos(kang) * HI*0.16
        ky = cy + HI*0.12 + math.sin(kang) * HI*0.16
        d.line([cx+HI*0.02, cy+HI*0.10, kx, ky], fill=skin, width=int(HI*0.038))
        d.ellipse([kx-HI*0.03, ky-HI*0.02, kx+HI*0.03, ky+HI*0.02], fill=(20,20,24))  # boot
        # shorts block
        d.polygon([(cx-HI*0.06, cy+HI*0.06), (cx+HI*0.07, cy+HI*0.06),
                   (cx+HI*0.05, cy+HI*0.14), (cx-HI*0.05, cy+HI*0.14)], fill=white)

        # ball: sits at foot until contact, then launches right with trail
        if t < 0.45:
            bx, by = cx+HI*0.14, cy+HI*0.20
            br = HI*0.045
            d.ellipse([bx-br, by-br, bx+br, by+br], fill=(250,250,255))
            d.ellipse([bx-br*0.4, by-br*0.5, bx+br*0.2, by+br*0.1], fill=(255,255,255))
        else:
            p = (t - 0.45) / 0.55
            bx = cx+HI*0.14 + p * HI*0.7
            by = cy+HI*0.20 - p * HI*0.28
            br = HI*0.045 * (1 - 0.3*p)
            out = arr(img)
            for k in range(1, 6):
                tx = bx - k*HI*0.06; ty = by + k*HI*0.024
                a = (1 - k/6)
                out = screen(out, radial(HI, HI, tx, ty, br*2.4, (120,120,140)*np.array([1,1,1.0]), 2.0)*a)
            img = to_img(out); d = ImageDraw.Draw(img)
            d.ellipse([bx-br, by-br, bx+br, by+br], fill=(250,250,255))
            # impact flash at contact frame
            if p < 0.18:
                out = arr(img)
                out = screen(out, radial(HI, HI, cx+HI*0.16, cy+HI*0.20, HI*0.18,
                                         (255,240,180), 1.6)*(1-p/0.18))
                img = to_img(out)
        frames.append(down(img))
    emit(frames, "usd_striker", ms=60, colors=180, dwell=12,
         desc="Shaded USMNT striker plants and strikes; ball rockets off with motion trail")


# ============================================================ 6. EAGLE ========
def gen_eagle(N=30):
    """Bald eagle crest: shaded head, hooked gold beak, fierce eye, wings that beat; radiant
    red/white/blue backdrop with a subtle rotating sunburst for USMNT spirit."""
    frames = []
    cx, cy = HI*0.5, HI*0.52
    for f in range(N):
        t = f / N
        # radiating red/white/blue backdrop
        base = vgrad(HI, HI, (12, 24, 70), (30, 12, 30))
        out = base.copy()
        # rotating sunburst rays
        img = to_img(out); d = ImageDraw.Draw(img)
        nray = 24
        for i in range(nray):
            a = 2*math.pi*i/nray + t*0.5
            col = (RED_D if i % 2 == 0 else NAVY_D)
            d.polygon([(cx, cy),
                       (cx+math.cos(a-0.06)*HI, cy+math.sin(a-0.06)*HI),
                       (cx+math.cos(a+0.06)*HI, cy+math.sin(a+0.06)*HI)], fill=col)
        out = arr(img)
        out = screen(out, radial(HI, HI, cx, cy, HI*0.55, (60, 55, 45), 1.8))
        img = to_img(out); d = ImageDraw.Draw(img)

        beat = math.sin(t * 2*math.pi)  # wing flap
        # wings (behind body)
        for sgn in (-1, 1):
            tip_y = cy - HI*0.10 + beat*HI*0.12*(-1)
            wpts = [(cx, cy-HI*0.02),
                    (cx+sgn*HI*0.34, tip_y),
                    (cx+sgn*HI*0.30, cy+HI*0.14),
                    (cx+sgn*HI*0.10, cy+HI*0.08)]
            d.polygon(wpts, fill=(70, 52, 34))
            # feather shading lines
            for k in range(1, 5):
                d.line([(cx+sgn*HI*0.10, cy+HI*0.02),
                        (cx+sgn*(HI*0.14+k*HI*0.05), tip_y+ k*HI*0.03)],
                       fill=(45, 33, 22), width=1)
        # body brown
        d.polygon([(cx-HI*0.11, cy-HI*0.02), (cx+HI*0.11, cy-HI*0.02),
                   (cx+HI*0.07, cy+HI*0.24), (cx-HI*0.07, cy+HI*0.24)], fill=(78, 54, 32))
        # white head
        hx, hy = cx, cy - HI*0.14
        d.ellipse([hx-HI*0.11, hy-HI*0.12, hx+HI*0.11, hy+HI*0.10], fill=(238, 238, 244))
        d.ellipse([hx-HI*0.11, hy-HI*0.12, hx-HI*0.0, hy+HI*0.10], fill=(205, 208, 218))  # shade
        # gold hooked beak
        d.polygon([(hx+HI*0.06, hy-HI*0.01), (hx+HI*0.20, hy+HI*0.03),
                   (hx+HI*0.07, hy+HI*0.07)], fill=GOLD)
        d.polygon([(hx+HI*0.15, hy+HI*0.03), (hx+HI*0.20, hy+HI*0.03),
                   (hx+HI*0.15, hy+HI*0.06)], fill=GOLD_D)
        # fierce eye
        d.ellipse([hx+HI*0.02, hy-HI*0.03, hx+HI*0.055, hy+HI*0.005], fill=(20, 20, 20))
        d.ellipse([hx+HI*0.03, hy-HI*0.028, hx+HI*0.042, hy-HI*0.012], fill=(255, 220, 80))
        frames.append(down(img))
    emit(frames, "usd_eagle", ms=60, colors=170, dwell=15,
         desc="Bald eagle crest with beating wings, gold beak, fierce eye over a rotating sunburst")


# ============================================================ 7. USA TEXT =====
def gen_usa_text(N=36):
    """Big metallic 'USA' with a chrome red/white/blue gradient fill, a specular highlight
    sweep across the letters, and a star that shines/twinkles above."""
    fnt = afont(int(HI * 0.40))
    # letter mask
    tmp = Image.new("L", (HI, HI), 0)
    td = ImageDraw.Draw(tmp)
    txt = "USA"
    bb = td.textbbox((0, 0), txt, font=fnt)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    tx, ty = (HI - tw)//2 - bb[0], int(HI*0.40) - bb[1]
    td.text((tx, ty), txt, font=fnt, fill=255)
    lmask = np.asarray(tmp, float) / 255.0
    letter = lmask > 0.4

    ys, xs = np.mgrid[0:HI, 0:HI]
    # vertical chrome gradient inside letters: white top -> red mid -> navy bottom
    top = np.array((250, 250, 255), float)
    mid = np.array(RED, float)
    bot = np.array(NAVY, float)
    v = np.clip((ys - int(HI*0.40)) / (th if th else HI), 0, 1)
    grad = np.where(v[:, :, None] < 0.5,
                    top[None, None]*(1-v[:, :, None]*2) + mid[None, None]*(v[:, :, None]*2),
                    mid[None, None]*(1-(v[:, :, None]-0.5)*2) + bot[None, None]*((v[:, :, None]-0.5)*2))
    frames = []
    for f in range(N):
        t = f / N
        out = vgrad(HI, HI, (10, 10, 28), (20, 16, 40))
        # drop shadow
        sh = np.zeros((HI, HI, 3), float)
        shim = Image.new("L", (HI, HI), 0)
        ImageDraw.Draw(shim).text((tx+SS*2, ty+SS*2), txt, font=fnt, fill=200)
        shmask = np.asarray(shim.filter(ImageFilter.GaussianBlur(SS)), float)/255.0
        out = out * (1 - shmask[:, :, None]*0.6)
        # letters with gradient
        out = np.where(letter[:, :, None], grad, out)
        # specular sweep
        gpos = (t*1.5 - 0.25) * HI
        band = np.exp(-((xs - gpos)**2) / (2*(HI*0.05)**2))
        out = screen(out, (band[:, :, None]*np.array((255,255,255),float)[None,None]) * letter[:, :, None] * 0.9)
        img = to_img(out); d = ImageDraw.Draw(img)
        # twinkling star above
        stw = 0.6 + 0.4*math.sin(t*2*math.pi*2)
        sx, sy = HI*0.5, HI*0.20
        d.polygon(star_poly(sx, sy, HI*0.07*stw), fill=GOLD_L)
        d.polygon(star_poly(sx, sy, HI*0.045*stw), fill=(255,255,240))
        if stw > 0.85:
            d.line([sx-HI*0.13, sy, sx+HI*0.13, sy], fill=GOLD_L, width=2)
            d.line([sx, sy-HI*0.11, sx, sy+HI*0.11], fill=GOLD_L, width=2)
        frames.append(down(img))
    emit(frames, "usd_usa_text", ms=60, colors=160, dwell=12,
         desc="Chrome red/white/blue 'USA' with a specular sweep and a twinkling star")


# ============================================================ 8. STAR FIELD ===
def gen_starfield(N=36):
    """Patriotic warp: red/white/blue stars stream toward the viewer out of a navy void
    with parallax depth, growing and brightening as they approach. Hypnotic loop."""
    rng = np.random.default_rng(5)
    NSTAR = 70
    zx = rng.uniform(-1, 1, NSTAR)
    zy = rng.uniform(-1, 1, NSTAR)
    zz = rng.uniform(0.1, 1.0, NSTAR)
    cols = [np.array((255,70,80),float), np.array((250,250,255),float), np.array((80,120,255),float)]
    ci = rng.integers(0, 3, NSTAR)
    frames = []
    cx, cy = HI*0.5, HI*0.5
    for f in range(N):
        out = vgrad(HI, HI, NAVY_D, (14, 24, 74))
        out = screen(out, radial(HI, HI, cx, cy, HI*0.7, (20, 26, 60), 2.2))
        img = to_img(out); d = ImageDraw.Draw(img)
        for i in range(NSTAR):
            z = (zz[i] - f / N) % 1.0
            z = 0.02 + z  # avoid 0
            px = cx + zx[i] / z * HI * 0.5
            py = cy + zy[i] / z * HI * 0.5
            if 0 <= px < HI and 0 <= py < HI:
                sz = HI * 0.012 / z
                sz = min(sz, HI*0.06)
                bright = min(1.0, (1 - z) * 1.3 + 0.2)
                col = tuple(int(v * bright) for v in cols[ci[i]])
                if sz > HI*0.02:
                    d.polygon(star_poly(px, py, sz), fill=col)
                else:
                    d.ellipse([px-sz, py-sz, px+sz, py+sz], fill=col)
        frames.append(down(img))
    emit(frames, "usd_starfield", ms=60, colors=160, dwell=12,
         desc="Red/white/blue star warp streaming out of a navy void with parallax depth")


# ============================================================ 9. LIBERTY ======
def gen_liberty(N=32):
    """Statue of Liberty torch motif: a shaded verdigris hand & torch with a live flickering
    gold flame, warm glow, over a dawn sky; small stars drift. Patriotic + iconic."""
    frames = []
    rng = np.random.default_rng(3)
    tx, ty = HI*0.5, HI*0.42   # torch bowl center
    for f in range(N):
        t = f / N
        out = vgrad(HI, HI, (30, 34, 78), (210, 150, 110))  # dawn
        out = screen(out, radial(HI, HI, tx, ty, HI*0.55, (120, 80, 20), 1.7))
        img = to_img(out); d = ImageDraw.Draw(img)
        # drifting bg stars
        for k in range(14):
            sx = (k*53 + f*2) % HI
            sy = (k*37) % int(HI*0.5)
            if (k + f) % 3 == 0:
                d.point((sx, sy), fill=(255, 255, 220))
        verd = (74, 150, 130); verdD = (44, 104, 92); verdL = (120, 190, 168)
        # arm rising from lower right
        d.line([HI*0.78, HI*0.98, tx+HI*0.06, ty+HI*0.12], fill=verd, width=int(HI*0.09))
        d.line([HI*0.78, HI*0.98, tx+HI*0.06, ty+HI*0.12], fill=verdD, width=int(HI*0.04))
        # hand
        d.ellipse([tx-HI*0.02, ty+HI*0.08, tx+HI*0.14, ty+HI*0.20], fill=verd)
        # torch handle + bowl
        d.rectangle([tx-HI*0.03, ty+HI*0.02, tx+HI*0.03, ty+HI*0.12], fill=verdD)
        d.polygon([(tx-HI*0.07, ty), (tx+HI*0.07, ty),
                   (tx+HI*0.05, ty+HI*0.05), (tx-HI*0.05, ty+HI*0.05)], fill=GOLD_D)
        d.ellipse([tx-HI*0.08, ty-HI*0.03, tx+HI*0.08, ty+HI*0.03], fill=verdL)
        # flame: layered flicker
        out = arr(img)
        flick = 1 + 0.15*math.sin(t*2*math.pi*3) + 0.1*rng.uniform(-1, 1)
        fh = HI*0.22 * flick
        for r, col, a in ((HI*0.12, (255, 150, 30), 0.9),
                          (HI*0.075, (255, 210, 70), 1.0),
                          (HI*0.04, (255, 250, 200), 1.0)):
            out = screen(out, radial(HI, HI, tx, ty-fh*0.4, r*1.6, np.array(col,float)*0.7, 2.0)*a)
        img = to_img(out); d = ImageDraw.Draw(img)
        # flame body polygon
        wob = math.sin(t*2*math.pi*3)*HI*0.02
        for col, w, h in (((255,140,20), 0.10, 0.22), ((255,205,60), 0.06, 0.16), ((255,250,210), 0.03, 0.10)):
            d.polygon([(tx-HI*w, ty-HI*0.01),
                       (tx+wob, ty-HI*h*flick),
                       (tx+HI*w, ty-HI*0.01)], fill=col)
        frames.append(down(img))
    emit(frames, "usd_liberty", ms=60, colors=170, dwell=15,
         desc="Liberty torch with a live flickering gold flame & warm glow over a dawn sky")


# ============================================================ MONTAGE =========
def build_montage():
    gifs = [m[0] for m in MANIFEST]
    cols = 3
    rows = (len(gifs) + cols - 1) // cols
    cell = S * 3
    pad = 8
    label_h = 14
    W = cols * cell + (cols + 1) * pad
    H = rows * (cell + label_h) + (rows + 1) * pad
    sheet = Image.new("RGB", (W, H), (18, 18, 24))
    d = ImageDraw.Draw(sheet)
    fnt = afont(11)
    for i, name in enumerate(gifs):
        r, c = divmod(i, cols)
        x = pad + c * (cell + pad)
        y = pad + r * (cell + label_h + pad)
        im = Image.open(os.path.join(HERE, name)).convert("RGB").resize((cell, cell), Image.NEAREST)
        sheet.paste(im, (x, y))
        lbl = name.replace("usd_", "").replace(".gif", "")
        d.text((x + 2, y + cell + 1), lbl, font=fnt, fill=(220, 220, 230))
    out = os.path.join(HERE, "_montage.png")
    sheet.save(out)
    print(f"    montage -> {os.path.basename(out)}  {W}x{H}")


def write_readme():
    order = ["usd_stadium_goal.gif", "usd_flag_wave.gif", "usd_trophy_glint.gif",
             "usd_fireworks.gif", "usd_usa_text.gif", "usd_eagle.gif",
             "usd_striker.gif", "usd_starfield.gif", "usd_liberty.gif"]
    lines = ["# USA World Cup — DELUXE pack (64x64, full-colour)", "",
             "Rich, shaded, cinematic USA soccer animations for the iDotMatrix 64x64 panel.",
             "Built with gradients, soft glows, cloth shading and 4x-supersampled anti-aliasing",
             "(`colors<=256, dither=True`). Regenerate with `python3 gen_usa_deluxe.py`.", "",
             "| # | file | frames | size | ms | dwell | description |",
             "|---|------|-------:|-----:|---:|------:|-------------|"]
    byname = {m[0]: m for m in MANIFEST}
    for i, nm in enumerate([o for o in order if o in byname] +
                           [m[0] for m in MANIFEST if m[0] not in order], 1):
        f, fr, sz, ms, dw, desc = byname[nm]
        lines.append(f"| {i} | `{f}` | {fr} | {sz/1024:.1f} KB | {ms} | {dw}s | {desc} |")
    lines += ["",
              "## Recommended best-of ordering (carousel)",
              "1. **usd_stadium_goal** — the showpiece: crowd, driven shot, net ripple, GOAL! flash.",
              "2. **usd_flag_wave** — waving Stars & Stripes with real cloth folds.",
              "3. **usd_trophy_glint** — gold trophy, spotlight, sweeping glint.",
              "4. **usd_fireworks** — red/white/blue bursts over the stadium.",
              "5. **usd_usa_text** — chrome 'USA' with specular sweep + star.",
              "6. **usd_eagle** — beating-wing bald eagle crest.",
              "7. **usd_striker** — striker plants and rockets the ball.",
              "8. **usd_starfield** — patriotic star warp (great as an idle/loop filler).",
              "9. **usd_liberty** — Liberty torch with a live flickering flame.", "",
              "All files are under the ~100 KB BLE-safe ceiling. Suggested per-slot dwell is in the",
              "table above; the goal, trophy and fireworks reward a longer (20s) dwell.", ""]
    with open(os.path.join(HERE, "README.md"), "w") as fh:
        fh.write("\n".join(lines))
    print("    wrote README.md")


def main():
    print("Building USA DELUXE pack ->", HERE)
    gen_flag_wave()
    gen_stadium_goal()
    gen_trophy_glint()
    gen_fireworks()
    gen_striker()
    gen_eagle()
    gen_usa_text()
    gen_starfield()
    gen_liberty()
    build_montage()
    write_readme()
    over = [m for m in MANIFEST if m[2] > 100_000]
    print(f"\nDone: {len(MANIFEST)} GIFs. " +
          (f"OVER LIMIT: {[m[0] for m in over]}" if over else "all under 100 KB."))


if __name__ == "__main__":
    main()
