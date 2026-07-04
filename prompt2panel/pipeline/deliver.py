"""Deliver a finished GIF to the panel via the idm-panel-api REST service (the 'hands').
Keeps BLE logic in one place — the container we already built and verified."""
import requests

from . import config


def push(gif_path, panel="big", mode="now", dwell=30, fix=False):
    """POST the GIF to idm-panel-api /push. Returns (pushed: bool, detail: dict)."""
    params = {"mode": mode, "dwell": dwell, "panel": panel}
    if fix:
        params["fix"] = 1
    with open(gif_path, "rb") as f:
        r = requests.post(f"{config.IDM_API_URL}/push", params=params,
                          files={"gif": ("art.gif", f, "image/gif")}, timeout=300)
    try:
        detail = r.json()
    except ValueError:
        detail = {"status_code": r.status_code, "text": r.text[:300]}
    return (r.status_code == 200 and detail.get("pushed") is True), detail
