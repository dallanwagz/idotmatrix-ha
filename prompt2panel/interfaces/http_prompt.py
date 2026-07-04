"""HTTP interface: POST /prompt -> generate+validate+push, return a short (spoken) status.
The voice-bridge (ESP32: Opus->ASR->text) and any web UI POST transcribed text here. Thin — all
the work is in pipeline.core. See CONTRACT.md for the frozen request/response shape.

    POST /prompt   json {"prompt": "<text>", "source": "voice",
                         "mode": "now|store"?, "dwell": 30?, "panel": "big"?}
        200 -> {"ok": bool, "message": "<short spoken status>", "pushed": bool, "attempts": n}
        400 -> {"ok": false, "message": "..."}   (no prompt)

    The caller speaks `message` back to the user.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask, jsonify, request           # noqa: E402
from pipeline import Job, library, prompt_to_panel  # noqa: E402

app = Flask(__name__)
PORT = int(os.environ.get("P2P_PROMPT_PORT", "8090"))


@app.post("/prompt")
def prompt():
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("prompt") or data.get("text") or "").strip()   # 'prompt' primary; 'text' alias
    if not text:
        return jsonify(ok=False, message="Give me something to make."), 400
    job = Job(prompt=text, source=data.get("source", "voice"),
              panel=data.get("panel", "big"), mode=data.get("mode", "now"),
              dwell=int(data.get("dwell", 30)))
    r = prompt_to_panel(job)
    return jsonify(ok=r.ok, message=r.message, pushed=r.pushed, attempts=r.attempts)


@app.post("/save")
def save():
    """Promote the last generated GIF into the library:  {"name": "brazil_2"}."""
    name = ((request.get_json(force=True, silent=True) or {}).get("name") or "").strip()
    if not name:
        return jsonify(ok=False, message="Give it a name: /save <name>"), 400
    saved = library.save_last(name)
    if not saved:
        return jsonify(ok=False, message="Nothing generated yet to save."), 409
    return jsonify(ok=True, name=saved, message=f"Saved as '{saved}'. Show it any time with /show {saved}.")


@app.post("/show")
def show():
    """Show a saved asset by name (or list the library if no name):  {"name": "surprise_1"}."""
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(ok=True, names=library.names(),
                       message="Library: " + (", ".join(library.names()) or "(empty)"))
    ok, msg = library.show(name, panel=data.get("panel", "big"),
                           mode=data.get("mode", "now"), dwell=int(data.get("dwell", 30)))
    return jsonify(ok=ok, message=msg)


@app.get("/library")
def lib():
    return jsonify(names=library.names())


@app.get("/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
