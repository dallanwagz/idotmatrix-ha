"""The DRY heart: prompt_to_panel(job) -> Result. generate → validate → repair → deliver.
Every interface (Signal, voice, HTTP, TFT) builds a Job and renders the Result in its own medium."""
import os
import shutil
import sys
import time
from dataclasses import dataclass, field

from . import config, deliver, generate, library

sys.path.insert(0, config.PI_QUICKSTART)
import validate_gif  # noqa: E402


@dataclass
class Job:
    prompt: str
    source: str = "api"                 # signal | voice | http | tft
    panel: str = "big"
    mode: str = "now"                   # now | store
    dwell: int = 30
    max_repair: int = None              # falls back to config


@dataclass
class Result:
    ok: bool
    message: str                        # human/spoken summary
    gif_path: str = None
    preview_path: str = None
    pushed: bool = False
    attempts: int = 0
    validation: list = field(default_factory=list)
    code: str = None
    error: str = None


def _stamp():
    # Date.now()-free stamp: a monotonic counter dir is enough for local caching/browsing
    return str(int(time.monotonic() * 1000))


def prompt_to_panel(job: Job) -> Result:
    os.makedirs(config.WORK_DIR, exist_ok=True)
    try:
        gif, code, attempts = generate.generate(job.prompt, max_repair=job.max_repair)
    except generate.GenerationError as e:
        return Result(ok=False, message=f"Couldn't build that one: {e}", error=str(e))

    # persist artifacts for caching / the TFT browser
    slot = os.path.join(config.WORK_DIR, _stamp())
    os.makedirs(slot, exist_ok=True)
    gif_path = os.path.join(slot, "art.gif")
    shutil.move(gif, gif_path)
    library.set_last(gif_path)                          # so `/save <name>` can promote it
    open(os.path.join(slot, "prompt.txt"), "w").write(job.prompt)
    open(os.path.join(slot, "gen.py"), "w").write(code)
    preview = os.path.join(slot, "preview.png")
    try:
        validate_gif.Image.open(gif_path).convert("RGB").resize((320, 320),
            validate_gif.Image.NEAREST).save(preview)
    except Exception:
        preview = None
    _, checks = validate_gif.check(gif_path)

    pushed, detail = deliver.push(gif_path, panel=job.panel, mode=job.mode, dwell=job.dwell)
    if pushed:
        msg = f"Done — it's on the panel ({attempts} attempt{'s' if attempts != 1 else ''})."
    else:
        msg = f"Made a compliant GIF but the panel push failed: {detail.get('error', detail)}"
    return Result(ok=pushed, message=msg, gif_path=gif_path, preview_path=preview,
                  pushed=pushed, attempts=attempts,
                  validation=[{"check": l, "pass": p} for l, p in checks], code=code)
