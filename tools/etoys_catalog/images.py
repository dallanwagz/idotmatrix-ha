#!/usr/bin/env python3
"""Pull the e-toys IMAGE library (type=图片) — catalog + deobfuscating download, concurrent."""
import csv, json, os, urllib.request
from concurrent.futures import ThreadPoolExecutor
import etoys_api as api

HERE = os.path.dirname(os.path.abspath(__file__))
CATS = {"daily": "日常", "holiday": "节日", "emoji": "表情", "creative": "创意", "business": "商业"}

def fetch(cn, page):
    for _ in range(6):
        try:
            r = api.request(api.material_params(cn, page, type_anim=False))
            if r and r.get("data"):
                return r["data"]
        except Exception:
            pass
    return None

with ThreadPoolExecutor(max_workers=16) as pool:
    p1 = {en: pool.submit(fetch, cn, 1) for en, cn in CATS.items()}
    tp = {en: (p1[en].result() or {"totalPage": 1, "records": []}) for en in CATS}
    bypage = {en: {1: tp[en]["records"]} for en in CATS}
    tasks = {pool.submit(fetch, cn, p): (en, p)
             for en, cn in CATS.items() for p in range(2, tp[en]["totalPage"] + 1)}
    for f, (en, p) in tasks.items():
        d = f.result(); bypage[en][p] = d["records"] if d else []
man = {en: [r for p in sorted(bypage[en]) for r in bypage[en][p]] for en in CATS}
json.dump(man, open(os.path.join(HERE, "manifest_images.json"), "w"), ensure_ascii=False, indent=1)
for en in CATS:
    print(f"  {en:9s}: {len(man[en])} images ({tp[en]['totalPage']} pages)", flush=True)
print(f"TOTAL listed: {sum(len(v) for v in man.values())}", flush=True)

rows = []
for cat, recs in man.items():
    os.makedirs(os.path.join(HERE, "library_images", cat), exist_ok=True)
    for r in recs:
        fmt = r.get("format", "png")
        rows.append({"category": cat, "file_id": r["file_id"], "format": fmt,
                     "width": r.get("width"), "height": r.get("height"),
                     "category_name": r.get("category_name"), "label": r.get("label"),
                     "file_path": r["file_path"],
                     "local": f"library_images/{cat}/{r['file_id']}.{fmt}"})

def get(row):
    p = os.path.join(HERE, row["local"])
    if os.path.exists(p) and os.path.getsize(p) > 0:
        return "skip"
    try:
        req = urllib.request.Request(row["file_path"], headers={"User-Agent": "okhttp/4.12.0"})
        open(p, "wb").write(api.deobfuscate(urllib.request.urlopen(req, timeout=25).read().decode()))
        return "ok"
    except Exception as e:
        return f"fail:{e}"

with ThreadPoolExecutor(max_workers=16) as pool:
    res = list(pool.map(get, rows))
json.dump(rows, open(os.path.join(HERE, "index_images.json"), "w"), ensure_ascii=False, indent=1)
with open(os.path.join(HERE, "index_images.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"downloaded {res.count('ok')}, had {res.count('skip')}, "
      f"failed {sum(1 for x in res if str(x).startswith('fail'))}; {len(rows)} catalogued", flush=True)
