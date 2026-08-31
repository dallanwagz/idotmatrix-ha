"""Asset catalog — loads the 32x32 iDotMatrix library (tools/etoys_catalog/) into memory.

Source of truth: index.csv (GIFs) + index_images.csv (PNGs), both columns
[category, file_id, format, width, height, category_name, label, file_path, local, name,
description]. Same submodule, same resolver logic as tools/etoys_catalog/send_to_panel.py.
"""
from __future__ import annotations

import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG_DIR = os.path.normpath(os.path.join(HERE, "..", "tools", "etoys_catalog"))
_INDEXES = ["index.csv", "index_images.csv"]  # 32x32 only — the two panels' native size


def _load() -> list[dict]:
    assets = []
    for fname in _INDEXES:
        path = os.path.join(CATALOG_DIR, fname)
        if not os.path.exists(path):
            continue
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                row["file_id"] = int(row["file_id"])
                assets.append(row)
    assets.sort(key=lambda r: r["file_id"])
    return assets


ASSETS: list[dict] = _load()
_BY_ID = {a["file_id"]: a for a in ASSETS}


def by_file_id(file_id: int) -> dict | None:
    return _BY_ID.get(int(file_id))


def categories() -> list[str]:
    return sorted({a["category"] for a in ASSETS})


def search(q: str = "", category: str = "", kind: str = "") -> list[dict]:
    q = (q or "").strip().lower()
    results = ASSETS
    if category:
        results = [a for a in results if a["category"] == category]
    if kind:
        results = [a for a in results if a["format"] == kind]
    if q:
        results = [
            a for a in results
            if q in a["name"].lower() or q in a["description"].lower()
        ]
    return results


def asset_path(asset: dict) -> str:
    """Absolute path to the asset's file on disk."""
    return os.path.join(CATALOG_DIR, asset["local"])


if __name__ == "__main__":
    # ponytail: minimal self-check, not a test suite
    assert len(ASSETS) > 1000, f"expected 1000+ assets, got {len(ASSETS)}"
    cookie = by_file_id(32718)
    assert cookie and cookie["name"] == "chocolate-chip-cookie", cookie
    assert os.path.exists(asset_path(cookie)), asset_path(cookie)
    hits = search(q="heart")
    assert hits, "expected at least one 'heart' hit"
    assert set(categories()) >= {"daily", "holiday", "emoji", "creative", "business"}
    print(f"OK: {len(ASSETS)} assets, {len(categories())} categories, "
          f"'heart' -> {len(hits)} hits")
