#!/usr/bin/env python3
"""wallboard — asset gallery + per-panel control for the two iDotMatrix wall panels.

One page: a status strip (what's currently showing on each panel) above a searchable
gallery of the catalog. Click a panel button on any asset card to push it there.
"""
from __future__ import annotations

import os

from flask import Flask, abort, redirect, render_template, request, send_from_directory, url_for

import catalog
import push

app = Flask(__name__)


@app.get("/")
def gallery():
    q = request.args.get("q", "")
    category = request.args.get("category", "")
    kind = request.args.get("kind", "")
    msg = request.args.get("msg", "")
    assets = catalog.search(q=q, category=category, kind=kind)
    return render_template(
        "gallery.html",
        assets=assets,
        categories=catalog.categories(),
        panels=list(push.PANELS),
        state=push.load_state(),
        q=q, category=category, kind=kind, msg=msg,
    )


@app.get("/asset/<path:relpath>")
def asset_file(relpath):
    full = os.path.normpath(os.path.join(catalog.CATALOG_DIR, relpath))
    if not full.startswith(catalog.CATALOG_DIR + os.sep):
        abort(404)
    directory, filename = os.path.split(full)
    return send_from_directory(directory, filename)


@app.post("/push")
def do_push():
    panel = request.form.get("panel", "")
    q = request.form.get("q", "")
    category = request.form.get("category", "")
    kind = request.form.get("kind", "")
    try:
        file_id = int(request.form.get("file_id", ""))
        _ok, message = push.push_asset(panel, file_id)
    except ValueError:
        message = "bad file_id"
    return redirect(url_for("gallery", q=q, category=category, kind=kind, msg=message))


if __name__ == "__main__":
    port = int(os.environ.get("WALLBOARD_PORT", "8080"))
    app.run(host="0.0.0.0", port=port, threaded=True)
