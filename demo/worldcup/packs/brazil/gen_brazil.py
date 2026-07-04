#!/usr/bin/env python3
"""gen_brazil.py — a rich, panel-safe Brazil World Cup animation pack for a 64x64 iDotMatrix panel.

Builds 12 looping GIFs (+ a preview PNG each and a contact-sheet montage) under this directory,
grouped into 3 themed packs:

  Pack A - Flags & Fan decor : br_flag_wave, br_brasil_scroll, br_stars5, br_confetti, br_samba_wave
  Pack B - Goals & Ball action: br_ball_roll, br_goal_freekick, br_gooool, br_striker_kick
  Pack C - Trophies & Glory  : br_trophy, br_trophy_raise, br_campeoes

Every asset is built with the project's panel-safe helper (<=16 flat colours/frame, 50 ms floor,
no gradients/dithering) so the panel's GIF decoder plays every frame.

Run:  python3 gen_brazil.py     # (re)creates every GIF + preview + montage, prints size/frame report
Does NOT connect to Bluetooth or push to hardware — it only writes files.
"""
import math
import os
import sys

sys.path.insert(0, "/Users/dallan/repo/tyler/idotmatrix-ha/pi-quickstart")
from assetlib import Canvas, save_gif, preview_png, panel_safe, font  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
S = 64

# ---- Brazil palette ----
GREEN = (0, 156, 59)
DGREEN = (0, 110, 40)
YELLOW = (255, 223, 0)
GOLD = (255, 200, 40)
DGOLD = (170, 120, 0)
BLUE = (0, 39, 118)
LBLUE = (0, 80, 190)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

REPORT = []  # (name, frames, bytes)


def emit(frames, name, ms):
    """Save a GIF + its preview PNG, and record size/frame for the final report."""
    path = os.path.join(HERE, name + ".gif")
    save_gif(frames, path, ms=ms)
    preview_png(path, scale=8)
    n = len(frames)
    b = os.path.getsize(path)
    REPORT.append((name, n, b))
    flag = "  <-- OVER 200KB" if b > 200_000 else ""
    print(f"    {name:20s} {n:3d}f  {b:6d}B  {ms}ms{flag}")


# ============================================================================
# PACK A - Flags & Fan decor
# ============================================================================

def _brazil_flag_base():
    """Build the static Brazilian flag as a flat-colour PIL image (green field, yellow diamond,
    blue globe with a slanted white band + scattered white stars). Returns the RGB image."""
    img = Image.new("RGB", (S, S), GREEN)
    d = ImageDraw.Draw(img)
    cx = cy = S / 2
    mx, my = 7, 9
    # yellow diamond
    d.polygon([(cx, my), (S - mx, cy), (cx, S - my), (mx, cy)], fill=YELLOW)
    # blue globe
    r = 15
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLUE)
    px = img.load()
    # slanted white band ("ORDEM E PROGRESSO") + star dots, per-pixel inside the globe
    stars = [(-8, -6), (5, -9), (-3, 4), (9, 2), (-10, 1), (1, -11),
             (6, 7), (-6, 8), (3, 1), (-2, -3), (8, -4), (11, 0), (-9, -8)]
    starset = {(int(cx + a), int(cy + b)) for a, b in stars}
    for y in range(S):
        for x in range(S):
            dx, dy = x - cx, y - cy
            if dx * dx + dy * dy <= r * r:
                band = dy + 0.32 * dx + 4.0          # slanted band offset
                if -2.4 < band < 2.4:
                    px[x, y] = WHITE
                elif (x, y) in starset:
                    px[x, y] = WHITE
    return img


def br_flag_wave():
    """Waving Brazilian flag — vertical per-column sine displacement makes the cloth ripple."""
    base = _brazil_flag_base()
    N, amp, wl = 12, 3.0, 26.0
    frames = []
    for f in range(N):
        ph = 2 * math.pi * f / N
        out = Image.new("RGB", (S, S), GREEN)
        for x in range(S):
            dy = int(round(amp * math.sin(2 * math.pi * x / wl - ph)))
            col = base.crop((x, 0, x + 1, S))
            out.paste(col, (x, dy))
        frames.append(out)
    emit(frames, "br_flag_wave", 90)


def br_brasil_scroll():
    """Bold BRASIL wordmark scrolling right-to-left over a blue field with sweeping green stripes."""
    # render "BRASIL" once to a tall yellow mask
    fnt = font(46)
    tmp = Image.new("L", (S * 6, S), 0)
    ImageDraw.Draw(tmp).text((0, 0), "BRASIL", fill=255, font=fnt)
    b = tmp.getbbox()
    mask = tmp.crop(b)
    tw, th = mask.size
    # scale to a comfortable panel height
    nh = 30
    mask = mask.resize((int(tw * nh / th), nh))
    tw, th = mask.size
    ml = mask.load()
    oy = (S - th) // 2
    span = tw + S           # scroll one full word-width + screen
    N = 40
    frames = []
    for f in range(N):
        img = Image.new("RGB", (S, S), BLUE)
        d = ImageDraw.Draw(img)
        # diagonal green sweep stripes moving opposite the text
        off = (f * 3) % 16
        for k in range(-2, S // 8 + 2):
            xx = k * 16 + off
            d.polygon([(xx, 0), (xx + 6, 0), (xx + 6 - 12, S), (xx - 12, S)], fill=GREEN)
        ox = S - int(span * f / N)
        px = img.load()
        for y in range(th):
            for x in range(tw):
                if ml[x, y] > 110:
                    X, Y = ox + x, oy + y
                    if 0 <= X < S and 0 <= Y < S:
                        px[X, Y] = YELLOW
        # thin white top/bottom trim
        d.rectangle([0, 0, S, 1], fill=WHITE)
        d.rectangle([0, S - 2, S, S], fill=WHITE)
        frames.append(img)
    emit(frames, "br_brasil_scroll", 90)


def _star(d, cx, cy, R, color):
    """Draw a filled 5-point star."""
    pts = []
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        rr = R if k % 2 == 0 else R * 0.42
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=color)


def br_stars5():
    """The 5 championship stars (Brazil = 5-time champs) appearing one-by-one then twinkling,
    over a deep-green field with a gold baseline."""
    positions = [(12, 22), (26, 16), (40, 16), (54, 22), (33, 40)]
    N = 30
    frames = []
    for f in range(N):
        img = Image.new("RGB", (S, S), DGREEN)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 50, S, 51], fill=GOLD)
        d.rectangle([0, 0, S, 1], fill=GOLD)
        # reveal phase: first 15 frames light stars 1..5; then twinkle
        for i, (sx, sy) in enumerate(positions):
            appear = f >= i * 3
            if not appear:
                continue
            twk = (f + i) % 6
            if twk == 0:            # bright flash
                _star(d, sx, sy, 8, WHITE)
                _star(d, sx, sy, 4, YELLOW)
            elif twk in (1, 5):
                _star(d, sx, sy, 7, YELLOW)
                _star(d, sx, sy, 3, WHITE)
            else:
                _star(d, sx, sy, 7, GOLD)
        # sparkle dots
        for j in range(4):
            sx = (j * 17 + f * 5) % S
            sy = 6 + (j * 13 + f * 3) % 44
            if (f + j) % 3 == 0:
                d.point((sx, sy), fill=WHITE)
        frames.append(img)
    emit(frames, "br_stars5", 110)


def br_confetti():
    """Samba-colour confetti raining down a black (LED-off) sky — bright falling flecks that loop."""
    import random
    random.seed(7)
    cols = [GREEN, YELLOW, BLUE, WHITE, GOLD]
    N = 30
    pieces = []
    for _ in range(46):
        pieces.append(dict(x=random.uniform(0, S), y=random.uniform(0, S),
                           v=random.uniform(1.4, 2.8), sway=random.uniform(0, 6.28),
                           c=random.choice(cols), w=random.choice([1, 2, 2])))
    frames = []
    for f in range(N):
        img = Image.new("RGB", (S, S), BLACK)
        d = ImageDraw.Draw(img)
        for p in pieces:
            y = (p["y"] + p["v"] * f) % (S + 4)
            x = (p["x"] + 2.4 * math.sin(p["sway"] + f * 0.4)) % S
            w = p["w"]
            d.rectangle([x, y, x + w, y + w], fill=p["c"])
        frames.append(img)
    emit(frames, "br_confetti", 80)


def br_samba_wave():
    """A lively samba-colour chevron wave scrolling diagonally with white sparkle accents — pure
    colour-and-refresh decor that flexes the panel."""
    pal = [GREEN, YELLOW, BLUE]
    N = 18
    frames = []
    for f in range(N):
        img = Image.new("RGB", (S, S), BLACK)
        px = img.load()
        ph = f * 1.6
        for y in range(S):
            for x in range(S):
                v = x + y * 0.6 + 4.0 * math.sin(y * 0.20 + ph)
                idx = int(v / 6 + ph * 0.3) % 3
                px[x, y] = pal[idx]
        d = ImageDraw.Draw(img)
        for j in range(6):
            sx = (j * 11 + f * 7) % S
            sy = (j * 23 + f * 5) % S
            d.point((sx, sy), fill=WHITE)
        frames.append(img)
    emit(frames, "br_samba_wave", 90)


# ============================================================================
# PACK B - Goals & Ball action
# ============================================================================

def _draw_ball(d, cx, cy, r, theta):
    """A flat pixel-art soccer ball: white disc + black pentagon spots rotated by `theta`."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(40, 40, 40))
    # central pentagon
    cpts = [(cx + r * 0.42 * math.cos(theta + k * 2 * math.pi / 5),
             cy + r * 0.42 * math.sin(theta + k * 2 * math.pi / 5)) for k in range(5)]
    d.polygon(cpts, fill=BLACK)
    # outer spots
    for k in range(5):
        a = theta + math.pi / 5 + k * 2 * math.pi / 5
        ox, oy = cx + r * 0.78 * math.cos(a), cy + r * 0.78 * math.sin(a)
        d.ellipse([ox - r * 0.22, oy - r * 0.22, ox + r * 0.22, oy + r * 0.22], fill=BLACK)


def br_ball_roll():
    """Soccer ball rolling across a green pitch with a moving shadow — spins as it travels."""
    N = 28
    r = 8
    frames = []
    for f in range(N):
        img = Image.new("RGB", (S, S), BLACK)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 44, S, S], fill=GREEN)          # pitch
        d.rectangle([0, 44, S, 45], fill=WHITE)         # touch line
        cx = -8 + (S + 16) * f / N
        cy = 36
        theta = -cx / r                                  # rolling (no slip)
        d.ellipse([cx - r, 45, cx + r, 49], fill=DGREEN)  # shadow
        _draw_ball(d, cx, cy, r, theta)
        frames.append(img)
    emit(frames, "br_ball_roll", 70)


def br_goal_freekick():
    """Roberto-Carlos-style banana free-kick: the ball curves in a bending arc past a wall and
    into the top corner, and the net ripples on impact."""
    N = 34
    # goal frame near the top-right
    gx0, gy0, gx1, gy1 = 30, 6, 60, 34
    # ball path: quadratic bezier from bottom-left, control pulls it wide then it bends back in
    p0 = (6, 56)
    p1 = (58, 46)        # control (bend)
    p2 = (52, 14)        # top-right corner (inside goal)
    frames = []
    for f in range(N):
        t = min(1.0, f / (N - 6))
        img = Image.new("RGB", (S, S), BLACK)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 52, S, S], fill=GREEN)          # grass
        # defensive wall (three yellow shirts) lower-left
        for i in range(3):
            wx = 12 + i * 7
            d.rectangle([wx, 40, wx + 5, 52], fill=YELLOW)
            d.rectangle([wx, 36, wx + 5, 40], fill=(230, 190, 150))  # heads
        # goal posts + crossbar
        d.rectangle([gx0, gy0, gx0 + 2, gy1], fill=WHITE)
        d.rectangle([gx1 - 2, gy0, gx1, gy1], fill=WHITE)
        d.rectangle([gx0, gy0, gx1, gy0 + 2], fill=WHITE)
        # net grid (ripple after impact)
        impacted = f >= N - 6
        rip = math.sin(f * 1.4) * 1.5 if impacted else 0.0
        for gx in range(gx0 + 4, gx1 - 2, 5):
            off = int(rip) if impacted else 0
            d.line([(gx + off, gy0 + 2), (gx, gy1)], fill=(150, 150, 160))
        for gy in range(gy0 + 5, gy1, 5):
            off = int(rip) if impacted else 0
            d.line([(gx0 + 2, gy + off), (gx1 - 2, gy)], fill=(150, 150, 160))
        # ball position along bezier
        bx = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        by = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        # motion trail
        for k in range(1, 4):
            tt = max(0.0, t - k * 0.05)
            tx = (1 - tt) ** 2 * p0[0] + 2 * (1 - tt) * tt * p1[0] + tt * tt * p2[0]
            ty = (1 - tt) ** 2 * p0[1] + 2 * (1 - tt) * tt * p1[1] + tt * tt * p2[1]
            d.ellipse([tx - 1, ty - 1, tx + 1, ty + 1], fill=(90, 90, 90))
        _draw_ball(d, bx, by, 3, -f * 0.6)
        if impacted:                                     # goal flash trim
            d.rectangle([0, 0, S, 1], fill=YELLOW)
            d.rectangle([0, S - 2, S, S], fill=YELLOW)
        frames.append(img)
    emit(frames, "br_goal_freekick", 80)


def br_gooool():
    """GOOOL! celebration — text punches in over pulsing green/yellow rays and a confetti burst."""
    N = 22
    frames = []
    for f in range(N):
        bg = [BLUE, GREEN, BLUE, DGREEN][f % 4]
        img = Image.new("RGB", (S, S), bg)
        d = ImageDraw.Draw(img)
        # radiating wedges from centre
        cx = cy = 32
        step = 30
        rot = f * 8
        for a in range(0, 360, step):
            a0 = math.radians(a + rot)
            a1 = math.radians(a + rot + step / 2)
            col = YELLOW if (a // step) % 2 == 0 else GOLD
            d.polygon([(cx, cy),
                       (cx + 60 * math.cos(a0), cy + 60 * math.sin(a0)),
                       (cx + 60 * math.cos(a1), cy + 60 * math.sin(a1))], fill=col)
        # word: "GOOOL!" grows with a slight bob
        scale = 40 + (6 if f % 2 == 0 else 0)
        fnt = font(scale)
        tmp = Image.new("L", (S * 6, S * 2), 0)
        ImageDraw.Draw(tmp).text((0, 0), "GOOOL!", fill=255, font=fnt)
        bb = tmp.getbbox()
        m = tmp.crop(bb)
        maxw = S - 4
        if m.width > maxw:
            m.thumbnail((maxw, S), Image.NEAREST)
        ox, oy = (S - m.width) // 2, (S - m.height) // 2
        outline = Image.new("RGB", m.size, GREEN)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            img.paste(outline, (ox + dx, oy + dy), m.point(lambda v: 255 if v > 110 else 0))
        solid = Image.new("RGB", m.size, WHITE)
        img.paste(solid, (ox, oy), m.point(lambda v: 255 if v > 110 else 0))
        frames.append(img)
    emit(frames, "br_gooool", 90)


def br_striker_kick():
    """A striker silhouette winding up and striking — the ball rockets off the boot with a trail."""
    N = 20
    frames = []
    # kick swings over frames; contact around f=10
    for f in range(N):
        img = Image.new("RGB", (S, S), YELLOW)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 50, S, S], fill=GREEN)            # ground
        d.rectangle([0, 50, S, 51], fill=WHITE)
        hipx, hipy = 30, 34
        # torso + head (black silhouette)
        d.ellipse([hipx - 4, 12, hipx + 4, 20], fill=BLACK)   # head
        d.line([(hipx, 20), (hipx, hipy)], fill=BLACK, width=5)  # torso
        # planted leg
        d.line([(hipx, hipy), (hipx - 6, 50)], fill=BLACK, width=4)
        # kicking leg swings from back (-) to front (+)
        phase = f / (N - 1)
        swing = math.radians(-40 + 150 * phase)
        kx = hipx + 20 * math.sin(swing)
        ky = hipy + 18 * math.cos(swing)
        d.line([(hipx, hipy), (kx, ky)], fill=BLACK, width=4)
        d.ellipse([kx - 2, ky - 2, kx + 3, ky + 3], fill=BLACK)   # boot
        # arms for balance
        d.line([(hipx, 24), (hipx + 10, 20)], fill=BLACK, width=3)
        d.line([(hipx, 24), (hipx - 9, 30)], fill=BLACK, width=3)
        # ball: rests at foot until contact, then launches up-right with a trail
        contact = 10
        if f < contact:
            bx, by = 46, 46
            _draw_ball(d, bx, by, 4, f * 0.3)
        else:
            k = f - contact
            bx = 46 + k * 3.2
            by = 46 - k * 3.4
            for tsteps in range(1, 4):
                tx = bx - tsteps * 3.2
                ty = by + tsteps * 3.4
                d.ellipse([tx - 1, ty - 1, tx + 1, ty + 1], fill=WHITE)
            _draw_ball(d, bx, by, 4, k * 0.8)
        frames.append(img)
    emit(frames, "br_striker_kick", 85)


# ============================================================================
# PACK C - Trophies & Glory
# ============================================================================

def _trophy_mask():
    """Return (image, maskset) for the gold World Cup trophy centred on a transparent field.
    maskset is the set of (x,y) gold pixels used to clip the glint sweep."""
    img = Image.new("RGB", (S, S), BLACK)
    d = ImageDraw.Draw(img)
    cx = 32
    # base (two stacked discs / plinth)
    d.ellipse([cx - 12, 52, cx + 12, 60], fill=DGOLD)
    d.rectangle([cx - 11, 50, cx + 11, 56], fill=GOLD)
    d.ellipse([cx - 12, 46, cx + 12, 52], fill=GOLD)
    # twisted stem: two curved bands sweeping up and out to the globe (the classic FIFA figures)
    for side in (-1, 1):
        pts = []
        for tt in range(0, 21):
            t = tt / 20.0
            x = cx + side * (2 + 9 * t * t)
            y = 48 - 30 * t
            pts.append((x, y))
        d.line(pts, fill=GOLD, width=4)
    # globe on top
    d.ellipse([cx - 12, 6, cx + 12, 26], fill=GOLD)
    d.ellipse([cx - 12, 6, cx + 12, 26], outline=DGOLD)
    # globe banding (continents hint)
    d.arc([cx - 12, 6, cx + 12, 26], 20, 160, fill=DGOLD)
    d.line([(cx - 10, 16), (cx + 10, 16)], fill=DGOLD)
    maskset = set()
    px = img.load()
    for y in range(S):
        for x in range(S):
            if px[x, y] != BLACK:
                maskset.add((x, y))
    return img, maskset


def br_trophy():
    """The gold World Cup trophy with a white glint sweeping diagonally across its surface."""
    base, maskset = _trophy_mask()
    N = 24
    frames = []
    for f in range(N):
        img = base.copy()
        px = img.load()
        gpos = -20 + (S + 40) * f / N       # glint diagonal position
        for (x, y) in maskset:
            band = (x + y) - gpos
            if -2 < band < 2:
                px[x, y] = WHITE
            elif -4 < band < 4:
                px[x, y] = YELLOW
        # sparkle at globe top on some frames
        if f % 4 == 0:
            d = ImageDraw.Draw(img)
            _star(d, 32, 5, 3, WHITE)
        frames.append(img)
    emit(frames, "br_trophy", 90)


def br_trophy_raise():
    """Rays-of-glory burst: golden rays spin behind while the trophy rises from the base."""
    base, maskset = _trophy_mask()
    N = 26
    frames = []
    for f in range(N):
        img = Image.new("RGB", (S, S), BLUE)
        d = ImageDraw.Draw(img)
        cx = cy = 30
        rot = f * 6
        for a in range(0, 360, 24):
            a0 = math.radians(a + rot)
            a1 = math.radians(a + rot + 12)
            col = YELLOW if (a // 24) % 2 == 0 else GOLD
            d.polygon([(cx, cy),
                       (cx + 70 * math.cos(a0), cy + 70 * math.sin(a0)),
                       (cx + 70 * math.cos(a1), cy + 70 * math.sin(a1))], fill=col)
        # trophy rises: paste base shifted up over frames
        rise = int(max(0, 22 - f * 2))
        tr = base.copy()
        px = tr.load()
        out = img.load()
        for (x, y) in maskset:
            Y = y + rise
            if 0 <= Y < S:
                out[x, Y] = px[x, y]
        # glint on the risen trophy
        gpos = (f * 5) % (S + 20) - 10
        for (x, y) in maskset:
            Y = y + rise
            if 0 <= Y < S and -2 < (x + Y) - gpos < 2:
                out[x, Y] = WHITE
        frames.append(img)
    emit(frames, "br_trophy_raise", 90)


def br_campeoes():
    """CAMPEOES flourish: the wordmark with the 5 championship stars twinkling above a gold rule."""
    fnt = font(30)
    tmp = Image.new("L", (S * 6, S), 0)
    ImageDraw.Draw(tmp).text((0, 0), "CAMPEOES", fill=255, font=fnt)
    b = tmp.getbbox()
    m = tmp.crop(b)
    maxw = S - 2
    if m.width > maxw:
        m = m.resize((maxw, max(1, int(m.height * maxw / m.width))))
    ml = m.load()
    tw, th = m.size
    ox, oy = (S - tw) // 2, 40
    starx = [10, 23, 32, 41, 54]
    N = 24
    frames = []
    for f in range(N):
        img = Image.new("RGB", (S, S), BLUE)
        d = ImageDraw.Draw(img)
        # top green band + gold rule
        d.rectangle([0, 0, S, 3], fill=GREEN)
        d.rectangle([0, 34, S, 36], fill=GOLD)
        # 5 stars twinkle
        for i, sx in enumerate(starx):
            twk = (f + i) % 5
            if twk == 0:
                _star(d, sx, 18, 8, WHITE); _star(d, sx, 18, 4, GOLD)
            elif twk in (1, 4):
                _star(d, sx, 18, 7, YELLOW)
            else:
                _star(d, sx, 18, 7, GOLD)
        # wordmark with sweeping colour fill (yellow with a green wipe)
        wipe = (f * 5) % (tw + 20)
        px = img.load()
        for y in range(th):
            for x in range(tw):
                if ml[x, y] > 110:
                    X, Y = ox + x, oy + y
                    if 0 <= X < S and 0 <= Y < S:
                        px[X, Y] = GREEN if abs(x - wipe) < 6 else YELLOW
        frames.append(img)
    emit(frames, "br_campeoes", 100)


# ============================================================================
# montage + main
# ============================================================================

def build_montage():
    """Contact-sheet PNG of every GIF's frame-0 (4 columns), for quick human eyeballing."""
    names = [r[0] for r in REPORT]
    cols, cell, pad, sc = 4, S, 6, 3
    rows = (len(names) + cols - 1) // cols
    W = cols * (cell * sc + pad) + pad
    H = rows * (cell * sc + pad + 12) + pad
    sheet = Image.new("RGB", (W, H), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    fnt = font(11)
    for i, nm in enumerate(names):
        r, cc = divmod(i, cols)
        im = Image.open(os.path.join(HERE, nm + ".gif")).convert("RGB")
        im = im.resize((cell * sc, cell * sc), Image.NEAREST)
        x = pad + cc * (cell * sc + pad)
        y = pad + r * (cell * sc + pad + 12)
        sheet.paste(im, (x, y))
        d.text((x, y + cell * sc + 1), nm, fill=(230, 230, 230), font=fnt)
    out = os.path.join(HERE, "_montage.png")
    sheet.save(out)
    print(f"  montage -> {os.path.basename(out)} ({W}x{H})")


def main():
    print("Brazil World Cup pack @ 64x64:")
    print("  Pack A - Flags & Fan decor")
    br_flag_wave()
    br_brasil_scroll()
    br_stars5()
    br_confetti()
    br_samba_wave()
    print("  Pack B - Goals & Ball action")
    br_ball_roll()
    br_goal_freekick()
    br_gooool()
    br_striker_kick()
    print("  Pack C - Trophies & Glory")
    br_trophy()
    br_trophy_raise()
    br_campeoes()
    build_montage()
    total = sum(r[2] for r in REPORT)
    print(f"  {len(REPORT)} GIFs, {total} bytes total; "
          f"{sum(1 for r in REPORT if r[2] > 200_000)} over 200KB")


if __name__ == "__main__":
    main()
