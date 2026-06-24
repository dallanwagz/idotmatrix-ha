#!/usr/bin/env python3
"""List the full e-toys cloud animation library — ALL categories+pages concurrently."""
import json, os
from concurrent.futures import ThreadPoolExecutor
import etoys_api as api

HERE = os.path.dirname(os.path.abspath(__file__))
CATS = {"daily": "日常", "holiday": "节日", "emoji": "表情", "creative": "创意", "business": "商业"}

def fetch(cn, page):
    for _ in range(6):
        try:
            r = api.request(api.material_params(cn, page, True))
            if r and r.get("data"):
                return r["data"]
        except Exception:
            pass
    return None

with ThreadPoolExecutor(max_workers=16) as pool:
    # page 1 of each category (learn total_page) concurrently
    p1 = {en: pool.submit(fetch, cn, 1) for en, cn in CATS.items()}
    tp = {en: (p1[en].result() or {"totalPage": 1, "records": []}) for en in CATS}
    # all remaining pages across all categories, one pool
    tasks = {}
    bypage = {en: {1: tp[en]["records"]} for en in CATS}
    for en, cn in CATS.items():
        for p in range(2, tp[en]["totalPage"] + 1):
            tasks[pool.submit(fetch, cn, p)] = (en, p)
    for f, (en, p) in tasks.items():
        d = f.result(); bypage[en][p] = d["records"] if d else []

man = {en: [r for p in sorted(bypage[en]) for r in bypage[en][p]] for en in CATS}
json.dump(man, open(os.path.join(HERE, "manifest.json"), "w"), ensure_ascii=False, indent=1)
for en in CATS:
    print(f"  {en:9s}: {len(man[en])} animations ({tp[en]['totalPage']} pages)", flush=True)
print(f"\nTOTAL: {sum(len(v) for v in man.values())} animations  [saved]", flush=True)
