"""Named-asset library: keep GIFs you like and push a saved one to the panel by name.

Lives on disk under P2P_WORK_DIR/library/<name>.gif. The last GIF the pipeline generated is
tracked at P2P_WORK_DIR/last.gif so `save(name)` can promote it into the library. This is the
"chooser" half of the workflow; `core.prompt_to_panel` is the "generate" half.
"""
import glob
import os
import shutil

from . import config, deliver

LIB = os.path.join(config.WORK_DIR, "library")
LAST = os.path.join(config.WORK_DIR, "last.gif")


def _safe(name):
    n = "".join(c for c in (name or "").strip().replace(" ", "_") if c.isalnum() or c in "-_")
    return n or "unnamed"


def set_last(gif_path):
    """Record the most recently generated GIF (so it can be saved by name)."""
    os.makedirs(config.WORK_DIR, exist_ok=True)
    shutil.copyfile(gif_path, LAST)


def names():
    os.makedirs(LIB, exist_ok=True)
    return sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(LIB, "*.gif")))


def path(name):
    p = os.path.join(LIB, _safe(name) + ".gif")
    return p if os.path.exists(p) else None


def add(name, src_gif):
    """Add/replace a library asset from any GIF file. Returns the sanitized name."""
    os.makedirs(LIB, exist_ok=True)
    n = _safe(name)
    shutil.copyfile(src_gif, os.path.join(LIB, n + ".gif"))
    return n


def save_last(name):
    """Promote the last generated GIF into the library under `name`. None if nothing generated."""
    if not os.path.exists(LAST):
        return None
    return add(name, LAST)


def show(name, panel="big", mode="now", dwell=30):
    """Push a saved asset to the panel. Returns (ok, message)."""
    p = path(name)
    if not p:
        return False, f"No saved asset '{_safe(name)}'. Library: " + (", ".join(names()) or "(empty)")
    ok, detail = deliver.push(p, panel=panel, mode=mode, dwell=dwell)
    return ok, (f"Showing '{_safe(name)}' on the panel." if ok
                else f"Push failed: {detail.get('error', detail)}")
