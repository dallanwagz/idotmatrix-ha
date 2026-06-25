#!/usr/bin/env python3
"""Generate labeled contact sheets for the e-toys library — one PNG per (size, type, category),
each a grid of every asset in that group with its caption name + file_id. Output -> contact_sheets/."""
import json
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "contact_sheets")
os.makedirs(OUT, exist_ok=True)

# (size, suffix). 32 uses unsuffixed index names.
SIZES = [(16, "_16"), (32, ""), (64, "_64")]
CATS = ["daily", "holiday", "emoji", "creative", "business", "all"]

COLS = 10
THUMB = 96          # upscaled cell image (NEAREST -> crisp pixel art)
LABEL = 24          # label band height (2 lines: name, id)
PAD = 6
TITLE = 30


def load_font(size):
    for p in ("/System/Library/Fonts/SFNSMono.ttf", "/System/Library/Fonts/Menlo.ttc",
              "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


F_LABEL = load_font(11)
F_ID = load_font(9)
F_TITLE = load_font(18)


def rep_frame(im):
    n = getattr(im, "n_frames", 1)
    try:
        im.seek(min(n - 1, max(0, n // 3)))
    except Exception:
        pass
    return im


def sheet(rows, title, outpath):
    n = len(rows)
    ncols = min(COLS, n) if n else 1
    nrows = (n + ncols - 1) // ncols
    cw, ch = THUMB + PAD, THUMB + LABEL + PAD
    W = ncols * cw + PAD
    H = TITLE + nrows * ch + PAD
    sh = Image.new("RGB", (W, H), (18, 18, 22))
    d = ImageDraw.Draw(sh)
    d.text((PAD, 7), title, fill=(255, 230, 120), font=F_TITLE)
    for i, r in enumerate(rows):
        try:
            im = Image.open(os.path.join(HERE, r["local"]))
            im = rep_frame(im).convert("RGB").resize((THUMB, THUMB), Image.NEAREST)
        except Exception:
            im = Image.new("RGB", (THUMB, THUMB), (60, 0, 0))
        cx = PAD + (i % ncols) * cw
        cy = TITLE + (i // ncols) * ch
        sh.paste(im, (cx, cy))
        d.rectangle([cx, cy + THUMB, cx + THUMB, cy + THUMB + LABEL], fill=(0, 0, 0))
        name = (r.get("name") or "?")[:16]
        d.text((cx + 2, cy + THUMB + 1), name, fill=(235, 235, 235), font=F_LABEL)
        d.text((cx + 2, cy + THUMB + 13), str(r["file_id"]), fill=(150, 150, 150), font=F_ID)
    sh.save(outpath)
    return outpath, W, H, n


def main():
    made = []
    for size, sfx in SIZES:
        for typ, base in (("anim", f"index{sfx}"), ("image", f"index_images{sfx}")):
            p = os.path.join(HERE, base + ".json")
            if not os.path.exists(p):
                continue
            rows = json.load(open(p))
            by = {}
            for r in rows:
                by.setdefault(r["category"], []).append(r)
            for cat in CATS:
                grp = sorted(by.get(cat, []), key=lambda r: r["file_id"])
                if not grp:
                    continue
                title = f"e-toys {size}x{size} · {typ} · {cat} ({len(grp)})"
                out = os.path.join(OUT, f"{size}_{typ}_{cat}.png")
                made.append(sheet(grp, title, out))
    print(f"generated {len(made)} contact sheets -> {OUT}")
    for path, w, h, n in made:
        print(f"  {os.path.basename(path):28s} {n:4d} assets  {w}x{h}")


if __name__ == "__main__":
    main()
