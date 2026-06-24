#!/usr/bin/env python3
"""Build a labeled montage of the next N un-captioned assets. Prints the batch mapping.
Usage: build_montage.py [N] [--size 16|32|64]   (default N=20, size=32)"""
import json, os, sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
N = int(args[0]) if args else 20
size = int(sys.argv[sys.argv.index("--size") + 1]) if "--size" in sys.argv else 32
sfx = "" if size == 32 else f"_{size}"
CAP = os.path.join(HERE, f"captions{sfx}.json")
done = set(json.load(open(CAP)).keys()) if os.path.exists(CAP) else set()

assets = []
for idx, typ in [(f"index{sfx}.json", "anim"), (f"index_images{sfx}.json", "image")]:
    p = os.path.join(HERE, idx)
    if os.path.exists(p):
        for r in json.load(open(p)):
            assets.append({"file_id": r["file_id"], "category": r["category"], "type": typ, "local": r["local"]})

def key(a): return f'{a["type"]}/{a["category"]}/{a["file_id"]}'
todo = [a for a in assets if key(a) not in done]
batch = todo[:N]
print(f"REMAINING: {len(todo)} / {len(assets)}  (done {len(done)})")
if not batch:
    print("ALL DONE"); sys.exit(0)

cols = 5; th = 104; lab = 16; pad = 4
rows = (len(batch) + cols - 1) // cols
sheet = Image.new("RGB", (cols * (th + pad) + pad, rows * (th + lab + pad) + pad), (12, 12, 16))
d = ImageDraw.Draw(sheet)
mapping = []
for i, a in enumerate(batch):
    try:
        im = Image.open(os.path.join(HERE, a["local"]))
        fr = min(getattr(im, "n_frames", 1) - 1, max(0, getattr(im, "n_frames", 1) // 3))
        im.seek(fr)
        im = im.convert("RGB").resize((th, th), Image.NEAREST)
    except Exception:
        im = Image.new("RGB", (th, th), (40, 0, 0))
    c = i % cols; r = i // cols
    x = pad + c * (th + pad); y = pad + r * (th + lab + pad)
    sheet.paste(im, (x, y))
    d.rectangle([x, y + th, x + th, y + th + lab], fill=(0, 0, 0))
    d.text((x + 2, y + th + 3), f"{a['type'][0]}/{a['category'][:3]}/{a['file_id']}", fill=(255, 255, 0))
    mapping.append({"file_id": a["file_id"], "category": a["category"], "type": a["type"], "key": key(a)})
out = "/tmp/cap_montage.png"; sheet.save(out)
print("MONTAGE:", out)
print("BATCH:", json.dumps(mapping, ensure_ascii=False))
