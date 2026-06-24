#!/usr/bin/env python3
"""Sync the e-toys asset library for a given PANEL SIZE — RE-RUNNABLE and idempotent.

Re-queries the FULL cloud catalog (animations 动画 + images 图片 across all 5 categories) for the
chosen panel size, then downloads + deobfuscates ONLY assets not already present locally — assets
already on disk are skipped. Rebuilds the per-size index.csv/index_images.csv. Captions are
preserved; any NEWLY fetched (un-captioned) assets are listed in new_assets_<sfx>.json.

    python sync.py                 # size 32 (default)
    python sync.py --size 16       # 16x16 panel
    python sync.py --size 64       # 64x64 panel
    python sync.py --size 16 --list   # dry-run: report catalog-vs-local counts, no downloads

Per-size layout (suffix is "" for 32, "_16"/"_64" otherwise):
    library{sfx}/<category>/<file_id>.gif        animations
    library_images{sfx}/<category>/<file_id>.png images
    index{sfx}.csv/json, index_images{sfx}.csv/json
    captions{sfx}.json  (read to enrich the indexes; preserved)
    new_assets{sfx}.json (assets without a caption yet)

Scope: the 5 categories the app exposes (日常/节日/表情/创意/商业), types anim + image. category_name
follows the app's per-size rule (see etoys_api.category_name_for): 16/32 -> "<group>_IDM" both types;
64 -> "<group>_IDM" for anim, single pool "iDotMatrix" for images.
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


def parse_size(argv):
    if "--size" in argv:
        return int(argv[argv.index("--size") + 1])
    return 32


def groups_for(size, anim):
    """The (display_category, category_name) pairs to query for this size+type. For 64x64 images the
    app uses one shared pool ("iDotMatrix") rather than per-group categories."""
    cn = api.category_name_for("日常", size, size, anim)
    if cn == "iDotMatrix":               # 64x64 images: a single un-grouped pool
        return [("all", "iDotMatrix")]
    return [(cat, f"{zh}_IDM") for cat, zh in CATS.items()]


def _req(category_name, page, anim, size):
    for _ in range(6):
        try:
            r = api.request(api.material_params("", page, anim, size, size, category_name=category_name))
            if r and r.get("data"):
                return r["data"]
        except Exception:
            pass
    return None


def list_group(category_name, anim, size, pool):
    d1 = _req(category_name, 1, anim, size)
    if not d1:
        return [], 0
    tp = d1["totalPage"]
    bypage = {1: d1["records"]}
    futs = {pool.submit(_req, category_name, p, anim, size): p for p in range(2, tp + 1)}
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


def sync_type(typ, anim, libdir, idxbase, size, pool, capkeys, list_only):
    rows, to_dl = [], []
    total_count = have = 0
    for cat, cn in groups_for(size, anim):
        recs, tc = list_group(cn, anim, size, pool)
        total_count += tc
        os.makedirs(os.path.join(HERE, libdir, cat), exist_ok=True)
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
    size = parse_size(sys.argv)
    if size not in (16, 32, 64):
        sys.exit("--size must be 16, 32 or 64")
    list_only = "--list" in sys.argv
    sfx = "" if size == 32 else f"_{size}"
    types = [("anim", True, f"library{sfx}", f"index{sfx}"),
             ("image", False, f"library_images{sfx}", f"index_images{sfx}")]
    capf = os.path.join(HERE, f"captions{sfx}.json")
    caps = json.load(open(capf)) if os.path.exists(capf) else {}
    capkeys = {(c["type"], c["file_id"]): c for c in caps.values()}
    print(f"e-toys sync — {size}x{size} ({'LIST ONLY' if list_only else 'download new'}) — captions known: {len(caps)}")
    tot = newfound = newdl = 0
    uncaptioned = []
    with ThreadPoolExecutor(max_workers=16) as pool:
        for typ, anim, libdir, idxbase in types:
            t, nf, nd, unc = sync_type(typ, anim, libdir, idxbase, size, pool, capkeys, list_only)
            tot += t; newfound += nf; newdl += nd; uncaptioned += unc
    if not list_only:
        json.dump(uncaptioned, open(os.path.join(HERE, f"new_assets{sfx}.json"), "w"), ensure_ascii=False, indent=1)
    print(f"\n{size}x{size} TOTAL available via API: {tot}")
    print(f"NEW this run: {newfound} found, {newdl} downloaded ({'list-only, none downloaded' if list_only else 'deobfuscated'})")
    print(f"un-captioned assets: {len(uncaptioned)}"
          + (f" -> new_assets{sfx}.json (caption these, then re-merge)" if uncaptioned else " (fully captioned)"))


if __name__ == "__main__":
    main()
