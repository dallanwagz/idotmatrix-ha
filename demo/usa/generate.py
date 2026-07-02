#!/usr/bin/env python3
"""USA futebol animations for the iDotMatrix 32x32 panels — solid colours (decoder-safe). Outputs:
  flag_usa.gif   Stars & Stripes with twinkling stars
  usa.gif        'USA' bold with a waving stripe field
The soccer ball is shared with the Brazil set (../brasil/ball.gif) — same WC match ball.
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
RED = (191, 10, 48)
WHITE = (255, 255, 255)
BLUE = (0, 40, 104)


def save_gif(frames, name, ms):
    p = os.path.join(HERE, name)
    frames[0].save(p, format="GIF", save_all=True, append_images=frames[1:], duration=ms, loop=0, disposal=2)
    return p


def _font(sz):
    for f in ("/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"):
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def _text_mask(s, fnt):
    tmp = Image.new("L", (400, 40), 0)
    ImageDraw.Draw(tmp).text((0, 0), s, fill=255, font=fnt)
    b = tmp.getbbox()
    return tmp.crop(b) if b else tmp


def gen_flag_usa():
    W = H = 32
    n = 8
    canton_w, canton_h = 14, 17          # ~7 stripes tall, ~0.4 wide
    frames = []
    for f in range(n):
        img = Image.new("RGB", (W, H), RED)
        d = ImageDraw.Draw(img)
        for y in range(H):                # 13 stripes
            if int(y * 13 / H) % 2 == 1:
                d.line([(0, y), (W, y)], fill=WHITE)
        d.rectangle([0, 0, canton_w, canton_h], fill=BLUE)
        # star grid, twinkling
        px = img.load()
        idx = 0
        for ry in range(3, canton_h - 2, 4):
            for rx in range(2, canton_w - 1, 3):
                if (idx + f) % 4 != 0:    # most on, a few blink
                    px[rx, ry] = WHITE
                idx += 1
        frames.append(img)
    save_gif(frames, "flag_usa.gif", 220)


def gen_usa():
    fnt = _font(22)
    mask = _text_mask("USA", fnt)
    tw, th = mask.size
    n = 24
    frames = []
    for f in range(n):
        img = Image.new("RGB", (32, 32), BLUE)
        d = ImageDraw.Draw(img)
        # waving red/white stripe band behind the text
        off = f % 6
        for y in range(0, 32, 6):
            d.rectangle([0, y + off - 3, 31, y + off], fill=(160, 12, 44))
        # 'USA' in white, thresholded solid
        ml = mask.load()
        ox, oy = (32 - tw) // 2, (32 - th) // 2
        px = img.load()
        for y in range(th):
            for x in range(tw):
                if ml[x, y] > 110 and 0 <= ox + x < 32 and 0 <= oy + y < 32:
                    px[ox + x, oy + y] = WHITE
        # star row on top
        for sx in range(3, 30, 5):
            if (sx // 5 + f) % 4 != 0:
                px[sx, 2] = WHITE
        frames.append(img)
    save_gif(frames, "usa.gif", 90)


def main():
    gen_flag_usa()
    gen_usa()
    # share the WC ball from the Brazil set
    ball = os.path.join(HERE, "..", "brasil", "ball.gif")
    if os.path.exists(ball):
        import shutil
        shutil.copy(ball, os.path.join(HERE, "ball.gif"))
    print("generated:")
    for n in ("flag_usa.gif", "usa.gif", "ball.gif"):
        p = os.path.join(HERE, n)
        if os.path.exists(p):
            im = Image.open(p)
            print(f"  {n:14s} {im.size[0]}x{im.size[1]} {getattr(im,'n_frames',1)}f {os.path.getsize(p)}B")


if __name__ == "__main__":
    main()
