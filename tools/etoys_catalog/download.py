#!/usr/bin/env python3
"""Download all catalogued e-toys GIFs into ./library/<category>/<file_id>.<fmt> (concurrent,
resumable) + write index.csv/json. Reads manifest.json {category:[records]}."""
import csv, json, os, urllib.request
from concurrent.futures import ThreadPoolExecutor
import etoys_api

HERE = os.path.dirname(os.path.abspath(__file__))
man = json.load(open(os.path.join(HERE, "manifest.json")))
rows = []
for cat, recs in man.items():
    os.makedirs(os.path.join(HERE, "library", cat), exist_ok=True)
    for r in recs:
        fmt = r.get("format", "gif")
        path = os.path.join(HERE, "library", cat, f"{r['file_id']}.{fmt}")
        rows.append({"category": cat, "file_id": r["file_id"], "format": fmt,
                     "width": r.get("width"), "height": r.get("height"),
                     "category_name": r.get("category_name"), "label": r.get("label"),
                     "file_path": r["file_path"], "local": os.path.relpath(path, HERE)})

def get(row):
    p = os.path.join(HERE, row["local"])
    if os.path.exists(p) and os.path.getsize(p) > 0:
        return "skip"
    try:
        req = urllib.request.Request(row["file_path"], headers={"User-Agent": "okhttp/4.12.0"})
        content = urllib.request.urlopen(req, timeout=25).read().decode()
        open(p, "wb").write(etoys_api.deobfuscate(content))      # obfuscated -> real GIF
        return "ok"
    except Exception as e:
        return f"fail:{e}"

with ThreadPoolExecutor(max_workers=16) as pool:
    res = list(pool.map(get, rows))
ok = res.count("ok"); skip = res.count("skip"); fail = sum(1 for x in res if str(x).startswith("fail"))
json.dump(rows, open(os.path.join(HERE, "index.json"), "w"), ensure_ascii=False, indent=1)
with open(os.path.join(HERE, "index.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"downloaded {ok}, had {skip}, failed {fail}; {len(rows)} catalogued -> index.csv/json", flush=True)
