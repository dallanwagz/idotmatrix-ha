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
from pipeline import Job, prompt_to_panel            # noqa: E402

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


@app.get("/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
