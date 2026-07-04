#!/usr/bin/env python3
"""REST API for the iDotMatrix panel: accept a GIF, validate it against the spec, and — if it
passes — drive it onto the panel over Bluetooth. Runs on the Pi (needs BlueZ/DBus in range).

Endpoints
  GET  /health                       -> {status, panel, busy}
  GET  /spec                         -> the GIF content spec (markdown)
  POST /validate   (form field gif)  -> {compliant, checks[]}          (no push)
  POST /push       (form field gif)  -> validate then push to the panel
       ?fix=1        auto-normalize a non-compliant GIF before pushing
       ?mode=now|store   now = live/transient (default), store = persist on-device
       ?dwell=<sec>  dwell for store mode (default 30)
       ?panel=<name> panel from panels.local.json (default env IDM_PANEL / "big")

The panel accepts one Bluetooth connection at a time, so pushes are serialized by a lock.
"""
import asyncio
import os
import sys
import tempfile
import threading

from flask import Flask, jsonify, request, send_file

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "pi-quickstart"))
import idm_push                                                     # noqa: E402
import validate_gif                                                 # noqa: E402
from idm_push import push, resolve_addr, run_with_retry            # noqa: E402

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024                  # 4 MB upload cap
PANEL = os.environ.get("IDM_PANEL", "big")
SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "idm64-gif-spec.md")
PUSH_LOCK = threading.Lock()                                        # single BLE central -> serialize


def _save_upload():
    f = request.files.get("gif")
    if not f:
        return None, (jsonify(error="upload a GIF in multipart form field 'gif'"), 400)
    fd, path = tempfile.mkstemp(suffix=".gif")
    os.close(fd)
    f.save(path)
    return path, None


def _checks_json(checks):
    return [{"check": label, "pass": bool(ok)} for label, ok in checks]


@app.get("/")
def root():
    return jsonify(
        service="idm-panel-api",
        panel=PANEL,
        endpoints=["GET /health", "GET /spec", "POST /validate (gif)", "POST /push (gif) [?fix=1&mode=now|store&dwell=&panel=]"],
    )


@app.get("/health")
def health():
    return jsonify(status="ok", panel=PANEL, busy=PUSH_LOCK.locked())


@app.get("/spec")
def spec():
    return send_file(SPEC, mimetype="text/markdown")


@app.post("/validate")
def validate():
    path, err = _save_upload()
    if err:
        return err
    try:
        ok, checks = validate_gif.check(path)
        return jsonify(compliant=ok, checks=_checks_json(checks))
    finally:
        os.unlink(path)


@app.post("/push")
def push_ep():
    path, err = _save_upload()
    if err:
        return err
    do_fix = request.args.get("fix", "0").lower() in ("1", "true", "yes")
    mode = request.args.get("mode", "now").lower()
    dwell = int(request.args.get("dwell", "30"))
    panel = request.args.get("panel", PANEL)
    try:
        ok, checks = validate_gif.check(path)
        if not ok and do_fix:
            fixed = path + ".fixed"
            validate_gif.fix(path, fixed)
            os.replace(fixed, path)
            ok, checks = validate_gif.check(path)
        if not ok:
            return jsonify(error="not spec-compliant", compliant=False,
                           checks=_checks_json(checks),
                           hint="retry with ?fix=1 to auto-normalize"), 422

        if not PUSH_LOCK.acquire(blocking=True, timeout=8):
            return jsonify(error="panel busy with another push, try again"), 429
        try:
            addr = resolve_addr(panel)                             # also sets idm_push.WRITE_RESPONSE
            data = open(path, "rb").read()
            if mode == "store":
                pushed = run_with_retry(lambda: push(addr, [(data, dwell, "upload.gif")]))
            else:
                pushed = run_with_retry(lambda: push(addr, [(data, 0, "upload.gif")], live=True))
        finally:
            PUSH_LOCK.release()

        if pushed:
            return jsonify(pushed=True, compliant=True, mode=mode, panel=panel,
                           bytes=len(data), checks=_checks_json(checks))
        return jsonify(pushed=False, error="bluetooth push failed after retries"), 502
    finally:
        os.unlink(path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
