#!/usr/bin/env python3
"""Sync the e-toys 32x32 asset library — RE-RUNNABLE and idempotent.

Re-queries the FULL cloud catalog (animations 动画 + images 图片 across all 5 categories),
then downloads + deobfuscates ONLY assets not already present locally — assets already on
disk are skipped. Rebuilds manifests + index.csv/index_images.csv. Captions in captions.json
are preserved; any NEWLY fetched (un-captioned) assets are listed in new_assets.json so you
can caption them later.

    python sync.py            # fetch only what's new, report counts
    python sync.py --list     # just report catalog vs local (no downloads)

Scope: width=height=32 (the HXS-002 panel) and the 5 categories the app exposes
(日常/节日/表情/创意/商业), types anim(动画) + image(图片). The API requires a category_name and
a size, so this is exactly "everything the app can browse for a 32x32 panel". To pull other
panel sizes, change W/H below; to discover other category names you'd need new ones from the app.
"""
import csv
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import etoys_api as api

HERE = os.path.dirname(os.path.abspath(__file__))
CATS = {"daily": "日常", "holiday": "节日", "emoji": "表情", "creative": "创意", "business": "商业"}
W = H = 32
TYPES = [("anim", True, "library", "index"), ("image", False, "library_images", "index_images")]


def _req(cn, page, anim):
    for _ in range(6):
        try:
            r = api.request(api.material_params(cn, page, anim, W, H))
            if r and r.get("data"):
                return r["data"]
        except Exception:
            pass
    return None


def list_group(cn, anim, pool):
    d1 = _req(cn, 1, anim)
    if not d1:
        return [], 0
    tp = d1["totalPage"]
    bypage = {1: d1["records"]}
    futs = {pool.submit(_req, cn, p, anim): p for p in range(2, tp + 1)}
    for f in futs:
        d = f.result()
        bypage[futs[f]] = d["records"] if d else []
    recs = [r for p in sorted(bypage) for r in bypage[p]]
    return recs, d1.get("totalCount", len(recs))


def get(url, path):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "okhttp/4.12.0"})
        content = urllib.request.urlopen(req, timeout=25).read().decode()
        open(path, "wb").write(api.deobfuscate(content))
        return True
    except Exception as e:
        print(f"   FAIL {os.path.basename(path)}: {e}", flush=True)
        return False


def sync_type(typ, anim, libdir, idxbase, pool, capkeys, list_only):
    rows, to_dl = [], []
    total_count = have = 0
    for cat, cn in CATS.items():
        recs, tc = list_group(cn, anim, pool)
        total_count += tc
        d = os.path.join(HERE, libdir, cat)
        os.makedirs(d, exist_ok=True)
        for r in recs:
            fmt = r.get("format", "gif" if anim else "png")
            local = f"{libdir}/{cat}/{r['file_id']}.{fmt}"
            rows.append({"category": cat, "file_id": r["file_id"], "format": fmt,
                         "width": r.get("width"), "height": r.get("height"),
                         "category_name": r.get("category_name"), "label": r.get("label"),
                         "file_path": r["file_path"], "local": local})
            p = os.path.join(HERE, local)
            if os.path.exists(p) and os.path.getsize(p) > 0:
                have += 1
            else:
                to_dl.append((r["file_path"], p))
    print(f"  {typ:6s}: catalog {len(rows)} (server totalCount {total_count}), on disk {have}, new {len(to_dl)}", flush=True)
    new_ok = 0
    if not list_only and to_dl:
        new_ok = sum(pool.map(lambda t: get(*t), to_dl))
    # merge captions, write indexes
    new_uncaptioned = []
    for row in rows:
        c = capkeys.get((typ, row["file_id"]), {})
        row["name"] = c.get("name", "")
        row["description"] = c.get("description", "")
        if not row["name"]:
            new_uncaptioned.append({"type": typ, "category": row["category"], "file_id": row["file_id"],
                                    "local": row["local"]})
    if rows and not list_only:
        json.dump(rows, open(os.path.join(HERE, idxbase + ".json"), "w"), ensure_ascii=False, indent=1)
        with open(os.path.join(HERE, idxbase + ".csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    return len(rows), len(to_dl), new_ok, new_uncaptioned


def main():
    list_only = "--list" in sys.argv
    capf = os.path.join(HERE, "captions.json")
    caps = json.load(open(capf)) if os.path.exists(capf) else {}
    capkeys = {(c["type"], c["file_id"]): c for c in caps.values()}
    print(f"e-toys sync ({'LIST ONLY' if list_only else 'download new'}) — captions known: {len(caps)}")
    tot = newfound = newdl = 0
    uncaptioned = []
    with ThreadPoolExecutor(max_workers=16) as pool:
        for typ, anim, libdir, idxbase in TYPES:
            t, nf, nd, unc = sync_type(typ, anim, libdir, idxbase, pool, capkeys, list_only)
            tot += t; newfound += nf; newdl += nd; uncaptioned += unc
    json.dump(uncaptioned, open(os.path.join(HERE, "new_assets.json"), "w"), ensure_ascii=False, indent=1)
    print(f"\nTOTAL available via API: {tot}")
    print(f"NEW this run: {newfound} found, {newdl} downloaded ({'list-only, none downloaded' if list_only else 'deobfuscated'})")
    print(f"un-captioned assets: {len(uncaptioned)} -> new_assets.json"
          + (" (caption these, then re-merge)" if uncaptioned else " (catalog fully captioned)"))


if __name__ == "__main__":
    main()
