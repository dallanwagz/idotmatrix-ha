"""Signal interface: listen for messages, treat each as an animation description, run the shared
pipeline, and reply with the status + a preview image. Thin adapter over pipeline.core.

Uses signal-cli in JSON-RPC daemon mode (the maintained way to script Signal):
    signal-cli -a +YOURNUMBER daemon --http    # or --json-rpc on a socket
Set SIGNAL_CLI_RPC (default http://127.0.0.1:8081/api/v1/rpc) and SIGNAL_ACCOUNT (+E164).

Run:  python3 interfaces/signal_bot.py
"""
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline import Job, prompt_to_panel            # noqa: E402

RPC = os.environ.get("SIGNAL_CLI_RPC", "http://127.0.0.1:8081/api/v1/rpc")
ACCOUNT = os.environ.get("SIGNAL_ACCOUNT", "")


def _rpc(method, params):
    r = requests.post(RPC, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=310)
    return r.json()


def reply(recipient, text, attachment=None):
    params = {"account": ACCOUNT, "recipient": [recipient], "message": text}
    if attachment:
        params["attachment"] = [attachment]
    _rpc("send", params)


def handle(recipient, text):
    reply(recipient, "🎨 on it — designing your GIF…")
    r = prompt_to_panel(Job(prompt=text, source="signal"))
    reply(recipient, r.message, attachment=r.preview_path if r.ok else None)


def main():
    if not ACCOUNT:
        sys.exit("set SIGNAL_ACCOUNT=+E164 (and run signal-cli daemon; see module docstring)")
    print(f"signal_bot listening on {ACCOUNT} via {RPC}")
    while True:
        try:
            res = _rpc("receive", {"account": ACCOUNT}).get("result", [])
            for env in res:
                msg = (env.get("envelope", {}).get("dataMessage") or {})
                text = (msg.get("message") or "").strip()
                src = env.get("envelope", {}).get("source")
                if text and src:
                    print(f"[{src}] {text!r}")
                    handle(src, text)
        except Exception as e:                       # keep the bot alive across transient errors
            print("loop error:", e)
        time.sleep(2)


if __name__ == "__main__":
    main()
