#!/usr/bin/env python3
"""Generate the USA (United States) World Cup animation pack for a 64x64 iDotMatrix panel.

Three themed packs of looping GIFs, all panel-safe (<=16 flat colors/frame, no gradients):
  Pack A - Flags & Fan decor : us_flag_wave, us_usa_chant, us_stars_twinkle, us_fireworks
  Pack B - Goals & Ball action: us_ball_roll, us_goal, us_striker_kick, us_eagle
  Pack C - Trophies & Glory   : us_trophy, us_trophy_raise, us_champions, us_stripes_scroll

Run:  python3 gen_usa.py    ->  (re)creates every .gif + a *_preview.png beside it.
Builds ONLY files; never touches Bluetooth / the panel.
"""
import math, os, sys
sys.path.insert(0, "/Users/dallan/repo/tyler/idotmatrix-ha/pi-quickstart")
from assetlib import Canvas, save_gif, preview_png, font
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
S = 64

# ---- USA palette (LED-bright) ----
RED   = (200, 30, 45)
WHITE = (255, 255, 255)
NAVY  = (0, 40, 104)
GOLD  = (255, 215, 0)
BLACK = (0, 0, 0)
# a few derived accents (kept small, still <=16/frame in any single design)
RED_D  = (120, 16, 28)     # shadow red
NAVY_D = (0, 22, 60)       # shadow navy
NAVY_L = (30, 80, 170)     # lit navy
GOLD_D = (170, 120, 0)     # trophy shadow gold
GOLD_L = (255, 240, 150)   # trophy highlight gold
GREY_D = (40, 40, 55)      # dim / off-ish

MANIFEST = []   # (filename, frames, bytes)


def emit(frames, name, ms):
    path = os.path.join(HERE, name + ".gif")
    save_gif(frames, path, ms=ms)
    preview_png(path, scale=8)
    MANIFEST.append((name + ".gif", len(frames), os.path.getsize(path)))


def star_poly(cx, cy, r, rot=-math.pi / 2, inner=0.42):
    """10-point polygon for a 5-point star."""
    pts = []
    for i in range(10):
        a = rot + i * math.pi / 5
        rr = r if i % 2 == 0 else r * inner
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


# ============================================================ PACK A ==========

def gen_flag_wave(N=24):
    """Waving Stars & Stripes: 13 stripes + navy canton with a star grid, column wave."""
    stripe_cols = [RED if i % 2 == 0 else WHITE for i in range(13)]
    dark = {RED: RED_D, WHITE: (180, 180, 195), NAVY: NAVY_D}
    cw, ch = int(S * 0.42), int(S * 7 / 13)  # canton
    # precompute star dot positions in canton (5 rows x 6 cols)
    stars = []
    for r in range(5):
        for cc in range(6):
            sx = 3 + cc * (cw - 5) / 5.0
            sy = 3 + r * (ch - 5) / 4.0
            stars.append((sx, sy))

    def base_color(x, y):
        if x < cw and y < ch:
            return NAVY
        stripe = int(y * 13 / S)
        stripe = max(0, min(12, stripe))
        return stripe_cols[stripe]

    frames = []
    for f in range(N):
        img = Image.new("RGB", (S, S), NAVY)
        px = img.load()
        phase = 2 * math.pi * f / N
        for x in range(S):
            # vertical displacement + a moving shadow band along the wave
            wav = 2.6 * math.sin(2 * math.pi * x / 26.0 - phase)
            slope = math.cos(2 * math.pi * x / 26.0 - phase)  # <0 => back of wave (shade)
            for y in range(S):
                sy = int(round(y - wav))
                sy = max(0, min(S - 1, sy))
                col = base_color(x, sy)
                if slope < -0.35:
                    col = dark.get(col, col)
                px[x, y] = col
        # stars ride the wave with the canton
        d = ImageDraw.Draw(img)
        wav0 = 2.6 * math.sin(-phase)
        for i, (sx, sy) in enumerate(stars):
            wav = 2.6 * math.sin(2 * math.pi * sx / 26.0 - phase)
            yy = int(sy + wav)
            if 0 <= yy < S:
                d.point((int(sx), yy), fill=WHITE)
        frames.append(img)
    emit(frames, "us_flag_wave", 90)


def gen_usa_chant(N=20):
    """Bold 'USA' pulsing between team colors with an expanding ring + stripe backdrop."""
    fnt = font(40)
    # pre-render USA text mask
    tmp = Image.new("L", (S * 4, S * 2), 0)
    ImageDraw.Draw(tmp).text((0, 0), "USA", fill=255, font=fnt)
    b = tmp.getbbox(); mask = tmp.crop(b)
    maxw = S - 6
    if mask.width > maxw:
        mask = mask.resize((maxw, int(mask.height * maxw / mask.width)))
    ml = mask.load(); tw, th = mask.size
    ox, oy = (S - tw) // 2, (S - th) // 2
    cycle = [RED, WHITE, NAVY_L, GOLD]
    frames = []
    for f in range(N):
        c = Canvas(S, bg=NAVY)
        # faint moving stripes backdrop
        off = f % 8
        for y in range(-8 + off, S, 8):
            c.rect(0, y, S, y + 1, NAVY_D)
        # pulsing ring
        pr = 8 + (f % (N // 2)) * 3
        ring = GOLD if (f // (N // 2)) % 2 == 0 else RED
        c.d.ellipse([S / 2 - pr, S / 2 - pr, S / 2 + pr, S / 2 + pr], outline=ring, width=2)
        fg = cycle[f % len(cycle)]
        px = c.img.load()
        for y in range(th):
            for x in range(tw):
                if ml[x, y] > 110:
                    xx, yy = ox + x, oy + y
                    if 0 <= xx < S and 0 <= yy < S:
                        px[xx, yy] = fg
        # sparkle corners
        for i, (sx, sy) in enumerate([(4, 4), (S - 5, 4), (4, S - 5), (S - 5, S - 5)]):
            if (i + f) % 2 == 0:
                c.d.point((sx, sy), fill=GOLD)
        frames.append(c.img)
    emit(frames, "us_usa_chant", 110)


def gen_stars_twinkle(N=16):
    """Field of red/white/gold 5-point stars twinkling over navy (static bg = fast refresh)."""
    import random
    random.seed(1776)
    stars = []
    for _ in range(22):
        stars.append((random.uniform(4, S - 4), random.uniform(4, S - 4),
                      random.uniform(2, 4.2), random.randint(0, 5),
                      random.choice([WHITE, WHITE, GOLD, RED])))
    frames = []
    for f in range(N):
        img = Image.new("RGB", (S, S), NAVY)
        d = ImageDraw.Draw(img)
        # a couple of static big background stars (dim)
        for sx, sy, r, ph, col in stars:
            phase = (f + ph) % 6
            if phase == 5:
                continue  # blink off
            rr = r * (0.55 if phase in (0, 4) else 1.0)
            bright = col if phase in (1, 2, 3) else NAVY_L
            d.polygon(star_poly(sx, sy, rr, rot=-math.pi / 2), fill=bright)
        frames.append(img)
    emit(frames, "us_stars_twinkle", 120)


def gen_fireworks(N=28):
    """Red/white/blue fireworks bursting over black (LEDs off between sparks)."""
    # each burst: (start_frame, cx, cy, color)
    bursts = [(0, 20, 22, RED), (6, 44, 18, WHITE), (12, 32, 30, NAVY_L),
              (18, 16, 40, GOLD), (22, 48, 42, RED), (4, 32, 12, NAVY_L)]
    frames = []
    for f in range(N):
        img = Image.new("RGB", (S, S), BLACK)
        d = ImageDraw.Draw(img)
        for sf, cx, cy, col in bursts:
            age = (f - sf) % N
            if age < 0 or age > 9:
                continue
            R = 2 + age * 2.4
            fade = col if age < 6 else GREY_D
            for k in range(12):
                a = k * math.pi / 6 + age * 0.15
                x = cx + R * math.cos(a)
                y = cy + R * math.sin(a)
                if 0 <= x < S and 0 <= y < S:
                    d.point((int(x), int(y)), fill=fade)
                    if age < 4:  # bright inner trail
                        d.point((int(cx + (R - 2) * math.cos(a)),
                                 int(cy + (R - 2) * math.sin(a))), fill=WHITE)
            if age <= 1:
                d.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=WHITE)
        frames.append(img)
    emit(frames, "us_fireworks", 80)


# ============================================================ PACK B ==========

# ---- rolling soccer ball (white ball, navy pentagons, USA accents), shaded sphere ----
_PENT = []  # pentagon centers as unit directions
def _pent_dirs():
    dirs = [(0, 0, 1)]
    for i in range(5):
        a = i * 2 * math.pi / 5
        dirs.append((0.9 * math.cos(a), 0.9 * math.sin(a), 0.42))
    for i in range(5):
        a = i * 2 * math.pi / 5 + math.pi / 5
        dirs.append((0.9 * math.cos(a), 0.9 * math.sin(a), -0.42))
    return [(x / (x * x + y * y + z * z) ** .5, y / (x * x + y * y + z * z) ** .5,
             z / (x * x + y * y + z * z) ** .5) for x, y, z in dirs]
_PENT = _pent_dirs()
_L = (-0.5, -0.6, 0.62); _ln = sum(v * v for v in _L) ** .5; _L = tuple(v / _ln for v in _L)

def _ball_tex(bx, by, bz):
    for gx, gy, gz in _PENT:
        if bx * gx + by * gy + bz * gz > 0.93:
            return NAVY
    return WHITE

def _ball_shade(col, nx, ny, nz):
    diff = nx * _L[0] + ny * _L[1] + nz * _L[2]
    if diff > 0.9 and col == WHITE:
        return WHITE
    t = 0.5 if diff < 0.15 else (0.78 if diff < 0.55 else 1.0)
    if col == WHITE:
        base = (235, 235, 245)
        return tuple(min(255, int(c * t)) for c in base)
    return tuple(min(255, int(c * t)) for c in NAVY_L if False) or tuple(min(255, int(c * t)) for c in col)

def gen_ball_roll(N=24):
    """A soccer ball rolls left->right across a navy pitch with a red/white ground stripe."""
    R = 9.5
    cy = 34
    frames = []
    for f in range(N):
        img = Image.new("RGB", (S, S), NAVY_D)
        d = ImageDraw.Draw(img)
        # pitch ground + a bright accent stripe
        d.rectangle([0, 46, S, S], fill=(0, 90, 40))
        d.rectangle([0, 44, S, 46], fill=WHITE)
        cx = -R + (S + 2 * R) * f / N
        roll = -2 * math.pi * (cx) / (2 * math.pi * R)  # rolling angle tied to travel
        ca, sa = math.cos(roll), math.sin(roll)
        # shadow
        d.ellipse([cx - R * 0.9, 45, cx + R * 0.9, 49], fill=(0, 60, 26))
        px = img.load()
        x0, x1 = int(cx - R - 1), int(cx + R + 2)
        for y in range(int(cy - R - 1), int(cy + R + 2)):
            if y < 0 or y >= S:
                continue
            for x in range(max(0, x0), min(S, x1)):
                nx, ny = (x + 0.5 - cx) / R, (y + 0.5 - cy) / R
                r2 = nx * nx + ny * ny
                if r2 <= 1.0:
                    nz = math.sqrt(1 - r2)
                    # rotate about vertical axis (rolling forward = rotate around screen-y)
                    bx = ca * nx - sa * nz
                    bz = sa * nx + ca * nz
                    by = ny
                    px[x, y] = _ball_shade(_ball_tex(bx, by, bz), nx, ny, nz)
        frames.append(img)
    emit(frames, "us_ball_roll", 70)


def gen_goal(N=30):
    """Ball driven into the net: approach -> impact -> net ripple -> GOAL! flash (team colors)."""
    frames = []
    net_x0 = 30
    for f in range(N):
        img = Image.new("RGB", (S, S), (0, 80, 36))  # pitch green
        d = ImageDraw.Draw(img)
        d.rectangle([0, 50, S, S], fill=(0, 60, 26))
        # goal frame posts
        d.rectangle([net_x0, 6, net_x0 + 2, 52], fill=WHITE)
        d.rectangle([S - 3, 6, S - 1, 52], fill=WHITE)
        d.rectangle([net_x0, 6, S - 1, 8], fill=WHITE)
        # impact frames = last 12
        impact = f >= 16
        bulge = 0
        if impact:
            k = f - 16
            bulge = max(0, int(4 * math.sin(math.pi * k / 6)))  # ripple in and settle
        # net grid inside goal
        for gx in range(net_x0 + 4, S - 2, 4):
            push = bulge if impact else 0
            d.line([(gx + push, 8), (gx + push, 50)], fill=(200, 240, 210))
        for gy in range(10, 50, 4):
            push = bulge if impact else 0
            d.line([(net_x0 + 2, gy), (S - 2 + push, gy)], fill=(200, 240, 210))
        # ball: flies in from left, lodges in net
        if f < 18:
            bx = 2 + (net_x0 + 12) * f / 18.0
            by = 44 - 18 * math.sin(math.pi * f / 18.0)
        else:
            bx = net_x0 + 12 + bulge
            by = 26
        d.ellipse([bx - 4, by - 4, bx + 4, by + 4], fill=WHITE)
        d.ellipse([bx - 4, by - 4, bx + 4, by + 4], outline=NAVY)
        d.point((bx, by), fill=NAVY)
        # GOAL! flash on the last stretch
        if f >= 22:
            flash = [RED, WHITE, NAVY][(f) % 3]
            c = Canvas(S)  # reuse text helper on a temp then paste band
            img2 = Image.new("RGB", (S, S), flash if f % 2 == 0 else NAVY)
            d2 = ImageDraw.Draw(img2)
            fnt = font(30)
            tmp = Image.new("L", (S * 4, S), 0)
            ImageDraw.Draw(tmp).text((0, 0), "GOAL!", fill=255, font=fnt)
            bb = tmp.getbbox(); m = tmp.crop(bb)
            mw = S - 4
            if m.width > mw:
                m = m.resize((mw, int(m.height * mw / m.width)))
            solid = Image.new("RGB", m.size, WHITE if f % 2 == 0 else GOLD)
            img2.paste(solid, ((S - m.width) // 2, (S - m.height) // 2),
                       m.point(lambda v: 255 if v > 110 else 0))
            img = img2
        frames.append(img)
    emit(frames, "us_goal", 85)


def gen_striker_kick(N=16):
    """Navy silhouette striker swings his leg and launches the ball off-screen; RWB backdrop."""
    frames = []
    for f in range(N):
        img = Image.new("RGB", (S, S), NAVY)
        d = ImageDraw.Draw(img)
        # backdrop: red/white ground + sky band
        d.rectangle([0, 0, S, 12], fill=NAVY_L)
        d.rectangle([0, 50, S, S], fill=(0, 90, 40))
        d.rectangle([0, 48, S, 50], fill=WHITE)
        # sun/ball-glow star
        d.polygon(star_poly(52, 8, 4), fill=GOLD)
        # silhouette figure at left-center, black
        BODY = BLACK
        hx, hy = 24, 20
        d.ellipse([hx - 4, hy - 4, hx + 4, hy + 4], fill=BODY)      # head
        d.line([(hx, hy + 4), (hx, 40)], fill=BODY, width=4)        # torso
        d.line([(hx, 26), (hx - 8, 32)], fill=BODY, width=3)        # back arm
        d.line([(hx, 26), (hx + 8, 20)], fill=BODY, width=3)        # front arm
        # planted leg
        d.line([(hx, 40), (hx - 5, 50)], fill=BODY, width=4)
        # kicking leg swings forward through the kick
        prog = f / (N - 1)
        knee_a = math.radians(-30 + 120 * prog)
        kx = hx + 12 * math.cos(knee_a)
        ky = 40 + 10 * math.sin(knee_a)
        d.line([(hx, 40), (kx, ky)], fill=BODY, width=4)
        fx = kx + 8 * math.cos(knee_a)
        fy = ky + 6 * math.sin(knee_a)
        d.line([(kx, ky), (fx, fy)], fill=BODY, width=4)
        # ball: sits, then launches on the arc after contact
        if prog < 0.55:
            bx, by = 44, 47
        else:
            t = (prog - 0.55) / 0.45
            bx = 44 + 22 * t
            by = 47 - 34 * t
        d.ellipse([bx - 4, by - 4, bx + 4, by + 4], fill=WHITE)
        d.ellipse([bx - 4, by - 4, bx + 4, by + 4], outline=RED)
        if prog >= 0.55:  # motion streak
            d.line([(bx - 6, by + 6), (bx - 2, by + 2)], fill=WHITE)
        frames.append(img)
    emit(frames, "us_striker_kick", 80)


def gen_eagle(N=16):
    """USMNT bald-eagle crest with flapping wings over a red/white/blue field."""
    frames = []
    for f in range(N):
        img = Image.new("RGB", (S, S), NAVY)
        d = ImageDraw.Draw(img)
        # radiating navy/blue field + top red band
        d.rectangle([0, 0, S, 10], fill=RED)
        d.rectangle([0, 54, S, S], fill=RED)
        cx, cy = 32, 30
        flap = math.sin(2 * math.pi * f / N)  # -1..1 wing position
        wy = int(6 * flap)
        # wings (gold/white feathered blocks) - drawn as chevrons
        for side in (-1, 1):
            tip = cx + side * 26
            d.polygon([(cx, cy - 4), (tip, cy - 10 + wy), (tip, cy - 2 + wy),
                       (cx, cy + 4)], fill=WHITE)
            d.polygon([(cx, cy), (tip, cy - 2 + wy), (tip, cy + 6 + wy),
                       (cx, cy + 6)], fill=(210, 210, 220))
        # body (navy) + head (white) + gold beak
        d.polygon([(cx - 6, cy - 2), (cx + 6, cy - 2), (cx + 3, cy + 16),
                   (cx - 3, cy + 16)], fill=NAVY_L)
        d.ellipse([cx - 5, cy - 12, cx + 5, cy - 2], fill=WHITE)   # head
        d.polygon([(cx + 3, cy - 8), (cx + 9, cy - 6), (cx + 3, cy - 4)], fill=GOLD)  # beak
        d.point((cx + 2, cy - 8), fill=BLACK)                      # eye
        # talons clutch a gold star
        d.polygon(star_poly(cx, cy + 20, 4), fill=GOLD)
        frames.append(img)
    emit(frames, "us_eagle", 90)


# ============================================================ PACK C ==========

def _draw_trophy(d, cx, base_y, scale=1.0):
    """Simplified FIFA-style gold trophy: twin curved body rising to a globe on a plinth."""
    g, gd, gl = GOLD, GOLD_D, GOLD_L
    s = scale
    # plinth base
    d.rectangle([cx - 9 * s, base_y, cx + 9 * s, base_y + 4 * s], fill=gd)
    d.rectangle([cx - 9 * s, base_y - 2 * s, cx + 9 * s, base_y, ], fill=g)
    # spiral body (two sweeping columns)
    d.polygon([(cx - 8 * s, base_y - 2 * s), (cx - 2 * s, base_y - 24 * s),
               (cx + 2 * s, base_y - 24 * s), (cx - 3 * s, base_y - 2 * s)], fill=g)
    d.polygon([(cx + 8 * s, base_y - 2 * s), (cx + 2 * s, base_y - 24 * s),
               (cx - 2 * s, base_y - 24 * s), (cx + 3 * s, base_y - 2 * s)], fill=gd)
    # globe on top
    d.ellipse([cx - 8 * s, base_y - 34 * s, cx + 8 * s, base_y - 18 * s], fill=g)
    d.ellipse([cx - 8 * s, base_y - 34 * s, cx + 8 * s, base_y - 18 * s], outline=gd)
    # globe meridian/equator hints
    d.line([(cx, base_y - 34 * s), (cx, base_y - 18 * s)], fill=gd)
    d.line([(cx - 8 * s, base_y - 26 * s), (cx + 8 * s, base_y - 26 * s)], fill=gd)


def gen_trophy(N=20):
    """World Cup trophy in gold with a bright glint sweeping diagonally across it."""
    frames = []
    for f in range(N):
        img = Image.new("RGB", (S, S), NAVY)
        d = ImageDraw.Draw(img)
        # subtle navy rays behind
        for k in range(8):
            a = k * math.pi / 4 + f * 0.05
            d.line([(32, 30), (32 + 40 * math.cos(a), 30 + 40 * math.sin(a))],
                   fill=NAVY_D, width=2)
        _draw_trophy(d, 32, 52, scale=1.0)
        # glint: bright diagonal band sweeping left->right, only over gold pixels
        gpos = -20 + (S + 40) * (f % N) / N
        px = img.load()
        for y in range(S):
            for x in range(S):
                if px[x, y] in (GOLD, GOLD_D):
                    if abs((x + y * 0.4) - gpos) < 3:
                        px[x, y] = GOLD_L
        # base plate label stars
        d.polygon(star_poly(20, 58, 2.5), fill=WHITE)
        d.polygon(star_poly(44, 58, 2.5), fill=WHITE)
        frames.append(img)
    emit(frames, "us_trophy", 90)


def gen_trophy_raise(N=22):
    """Trophy lifted skyward with rotating gold rays-of-glory + a burst of stars."""
    frames = []
    for f in range(N):
        img = Image.new("RGB", (S, S), NAVY_D)
        d = ImageDraw.Draw(img)
        prog = min(1.0, f / (N * 0.6))
        # rotating rays of glory
        for k in range(12):
            a = k * math.pi / 6 + f * 0.12
            col = GOLD if k % 2 == 0 else RED
            d.line([(32, 24), (32 + 46 * math.cos(a), 24 + 46 * math.sin(a))],
                   fill=col, width=2)
        d.ellipse([32 - 10, 24 - 10, 32 + 10, 24 + 10], fill=NAVY_D)  # clear center
        # trophy rises from bottom into center
        base_y = int(64 - (64 - 46) * prog)
        _draw_trophy(d, 32, base_y, scale=0.85)
        # sparkle stars pop outward after it lands
        if prog >= 1.0:
            for i in range(6):
                a = i * math.pi / 3 + f * 0.3
                r = 18 + 6 * math.sin(f * 0.5 + i)
                sx, sy = 32 + r * math.cos(a), 24 + r * math.sin(a)
                d.polygon(star_poly(sx, sy, 2.5), fill=WHITE)
        frames.append(img)
    emit(frames, "us_trophy_raise", 90)


def gen_champions(N=20):
    """'USA!' champions flourish: waving stripes, gold sparkle stars, pulsing wordmark."""
    fnt = font(34)
    tmp = Image.new("L", (S * 4, S), 0)
    ImageDraw.Draw(tmp).text((0, 0), "USA!", fill=255, font=fnt)
    b = tmp.getbbox(); mask = tmp.crop(b)
    mw = S - 4
    if mask.width > mw:
        mask = mask.resize((mw, int(mask.height * mw / mask.width)))
    ml = mask.load(); tw, th = mask.size
    ox, oy = (S - tw) // 2, (S - th) // 2 - 2
    frames = []
    for f in range(N):
        img = Image.new("RGB", (S, S), NAVY)
        d = ImageDraw.Draw(img)
        # waving red/white stripes across the bottom third
        for y in range(44, S):
            wav = int(2 * math.sin(2 * math.pi * (y) / 6.0 - f * 0.5))
            col = RED if ((y + wav) // 3) % 2 == 0 else WHITE
            d.line([(0, y), (S, y)], fill=col)
        # top gold star arc, twinkling
        for i in range(7):
            a = math.pi * (0.15 + 0.7 * i / 6)
            sx = 32 - 26 * math.cos(a)
            sy = 14 - 8 * math.sin(a)
            col = GOLD if (i + f) % 2 == 0 else WHITE
            d.polygon(star_poly(sx, sy, 2.6), fill=col)
        # pulsing wordmark (red <-> white)
        fg = WHITE if (f // 2) % 2 == 0 else RED
        px = img.load()
        for y in range(th):
            for x in range(tw):
                if ml[x, y] > 110:
                    xx, yy = ox + x, oy + y
                    if 0 <= xx < S and 0 <= yy < S:
                        px[xx, yy] = fg
        frames.append(img)
    emit(frames, "us_champions", 100)


def gen_stripes_scroll(N=16):
    """Decorative barber-pole: bold diagonal red/white/navy stripes scrolling forever."""
    frames = []
    band = 8
    cols = [RED, WHITE, NAVY]
    for f in range(N):
        img = Image.new("RGB", (S, S), BLACK)
        d = ImageDraw.Draw(img)
        off = int(f * (band * 3) / N)
        for x in range(-S, S * 2, band):
            idx = ((x + off) // band) % 3
            # diagonal parallelogram stripe
            d.polygon([(x, 0), (x + band, 0), (x + band - S, S), (x - S, S)],
                      fill=cols[idx])
        # a row of gold stars marching along the middle
        for i in range(8):
            sx = ((i * 9 + f * 2) % (S + 8)) - 4
            d.polygon(star_poly(sx, 32, 2.4), fill=GOLD)
        frames.append(img)
    emit(frames, "us_stripes_scroll", 90)


def build_contact_sheet():
    """One montage PNG of every GIF's frame-0 for quick human eyeballing."""
    names = [m[0] for m in MANIFEST]
    cols = 4
    rows = (len(names) + cols - 1) // cols
    pad, sc = 6, 3
    cw = ch = S * sc
    sheet = Image.new("RGB", (cols * (cw + pad) + pad, rows * (ch + pad) + pad), (20, 20, 24))
    for i, nm in enumerate(names):
        im = Image.open(os.path.join(HERE, nm)).convert("RGB")
        im = im.resize((cw, ch), Image.NEAREST)
        r, c = divmod(i, cols)
        sheet.paste(im, (pad + c * (cw + pad), pad + r * (ch + pad)))
    out = os.path.join(HERE, "_contact_sheet.png")
    sheet.save(out)
    print(f"  contact sheet -> {os.path.basename(out)}  {sheet.size}")


if __name__ == "__main__":
    print(f"USA World Cup pack @ {S}x{S}:")
    print(" Pack A - Flags & Fan decor")
    gen_flag_wave()
    gen_usa_chant()
    gen_stars_twinkle()
    gen_fireworks()
    print(" Pack B - Goals & Ball action")
    gen_ball_roll()
    gen_goal()
    gen_striker_kick()
    gen_eagle()
    print(" Pack C - Trophies & Glory")
    gen_trophy()
    gen_trophy_raise()
    gen_champions()
    gen_stripes_scroll()
    build_contact_sheet()
    print("\n  MANIFEST (name, frames, bytes):")
    over = 0
    for nm, nf, sz in MANIFEST:
        flag = "  <-- OVER 200KB" if sz > 200_000 else ""
        if sz > 200_000:
            over += 1
        print(f"    {nm:24s} {nf:3d}f {sz:7d}B{flag}")
    print(f"  total files: {len(MANIFEST)}  over-200KB: {over}")
