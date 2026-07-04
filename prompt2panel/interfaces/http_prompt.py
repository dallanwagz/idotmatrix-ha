"""HTTP interface: POST /prompt {text} -> generate+validate+push, return a short (spoken) status.
This is what the voice / ESP32 buddy (and any future web UI) posts transcribed text to. Thin —
all the work is in pipeline.core.

    POST /prompt   json {"text": "...", "mode": "now|store", "dwell": 30, "panel": "big"}
        -> {"ok": bool, "message": "...", "pushed": bool, "attempts": n}
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask, jsonify, request           # noqa: E402
from pipeline import Job, prompt_to_panel            # noqa: E402

app = Flask(__name__)


@app.post("/prompt")
def prompt():
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify(ok=False, message="Give me something to make."), 400
    job = Job(prompt=text, source=data.get("source", "voice"),
              panel=data.get("panel", "big"), mode=data.get("mode", "now"),
              dwell=int(data.get("dwell", 30)))
    r = prompt_to_panel(job)
    return jsonify(ok=r.ok, message=r.message, pushed=r.pushed, attempts=r.attempts)


@app.get("/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)
