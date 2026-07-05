"""HTTP interface: POST /prompt -> generate+validate+push, return a short (spoken) status.
The voice-bridge (ESP32: Opus->ASR->text) and any web UI POST transcribed text here. Thin — all
the work is in pipeline.core. See CONTRACT.md for the frozen request/response shape.

    POST /prompt   json {"prompt": "<text>", "source": "voice",
                         "mode": "now|store"?, "dwell": 30?, "panel": "big"?}
        200 -> {"ok": bool, "message": "<short spoken status>", "pushed": bool, "attempts": n}
        400 -> {"ok": false, "message": "..."}   (no prompt)

    The caller speaks `message` back to the user.
"""
import json
import os
import sys
import threading
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask, jsonify, request           # noqa: E402
from pipeline import Job, library, prompt_to_panel  # noqa: E402

app = Flask(__name__)
PORT = int(os.environ.get("P2P_PROMPT_PORT", "8090"))

# Fast-ack async jobs. In-memory + ephemeral (lost on restart) — fine for
# fire-and-speak voice commands. ponytail: dict+lock, not a queue/DB; add
# persistence only if a job must survive a restart (it needn't).
_jobs: dict = {}
_jobs_lock = threading.Lock()


def _run_job(job_id: str, job, callback: str) -> None:
    """Run the (slow) generation in the background, store the result, and — if a
    callback URL was given — POST the result to it so the caller can speak it."""
    try:
        r = prompt_to_panel(job)
        result = {"ok": r.ok, "message": r.message, "pushed": r.pushed, "attempts": r.attempts}
    except Exception as e:  # never let a worker thread die silently
        app.logger.exception("job %s failed", job_id)
        result = {"ok": False, "message": f"Couldn't build that one: {e}", "pushed": False, "attempts": 0}
    with _jobs_lock:
        _jobs[job_id] = {"status": "done", "result": result}
    if callback:
        try:
            body = json.dumps({"job": job_id, **result}).encode()
            req = urllib.request.Request(callback, data=body,
                                         headers={"content-type": "application/json"})
            urllib.request.urlopen(req, timeout=15).read()
        except Exception:
            app.logger.exception("callback POST to %s failed for job %s", callback, job_id)


@app.post("/prompt")
def prompt():
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("prompt") or data.get("text") or "").strip()   # 'prompt' primary; 'text' alias
    if not text:
        return jsonify(ok=False, message="Give me something to make."), 400
    job = Job(prompt=text, source=data.get("source", "voice"),
              panel=data.get("panel", "big"), mode=data.get("mode", "now"),
              dwell=int(data.get("dwell", 30)))

    # Fast-ack (opt-in, backward compatible): if the caller sets async=true or
    # passes a callback URL, return an interim "on it" immediately and run the
    # 15-60s generation in the background. Sync callers are unchanged.
    callback = (data.get("callback") or "").strip()
    if data.get("async") or callback:
        job_id = uuid.uuid4().hex[:8]
        with _jobs_lock:
            _jobs[job_id] = {"status": "running", "result": None}
        threading.Thread(target=_run_job, args=(job_id, job, callback), daemon=True).start()
        return jsonify({"ok": True, "async": True, "job": job_id,
                        "message": "On it — making that now."}), 202

    r = prompt_to_panel(job)
    return jsonify(ok=r.ok, message=r.message, pushed=r.pushed, attempts=r.attempts)


@app.get("/status/<job_id>")
def status(job_id):
    """Poll an async job — alternative to the callback for bridges that can't receive one."""
    with _jobs_lock:
        j = _jobs.get(job_id)
    if not j:
        return jsonify(ok=False, message="No such job."), 404
    if j["status"] == "running":
        return jsonify(ok=True, status="running", message="Still working on it…")
    return jsonify({"ok": True, "status": "done", **j["result"]})


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
    app.run(host="0.0.0.0", port=PORT, threaded=True)
