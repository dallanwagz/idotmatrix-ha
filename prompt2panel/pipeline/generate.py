"""Generate a spec-compliant GIF from a text description by having Sonnet write a Pillow/assetlib
generator program, running it sandboxed, and repairing against the validator until it passes.

Returns (gif_path, code, attempts) or raises GenerationError.
"""
import os
import subprocess
import sys
import tempfile
import textwrap

from . import config

sys.path.insert(0, config.PI_QUICKSTART)
import validate_gif  # noqa: E402  (our spec checker — check() returns (ok, checks))


class GenerationError(Exception):
    pass


def _spec_text():
    try:
        return open(config.SPEC_PATH).read()
    except OSError:
        return "(spec file unavailable — target: 64x64 GIF, <=90KB, loop forever, 20-60 frames, full colour)"


SYSTEM = """You write a COMPLETE, self-contained Python program that renders one animated GIF for a
64x64 LED matrix panel. The program MUST:
- import assetlib from the path already on sys.path: `from assetlib import Canvas, save_gif`
- build a list of 64x64 PIL frames (use Canvas(64, bg=...) helpers or draw on `c.img`)
- save with `save_gif(frames, OUT, ms=<50-100>, colors=256, dither=True)` where OUT is the env var
  P2P_OUT (an absolute path). Read it: `import os; OUT = os.environ["P2P_OUT"]`.
- keep the file UNDER 90 KB (fewer frames / fewer colours if needed), 20-60 frames, loop forever.
Full colour, gradients and shading are welcome (this panel renders them). Bright saturated colours
read best; pure black is "off". Output ONLY the Python program in a single ```python code block."""


def _extract_code(text):
    if "```" in text:
        block = text.split("```", 2)[1]
        if block.startswith("python"):
            block = block[len("python"):]
        return block.strip()
    return text.strip()


def _run_generator(code):
    """Run model-written code in a subprocess: scratch cwd, clean env, timeout, no secrets."""
    d = tempfile.mkdtemp(prefix="p2p_gen_")
    out = os.path.join(d, "art.gif")
    src = os.path.join(d, "gen.py")
    open(src, "w").write(code)
    env = {"PATH": os.environ.get("PATH", ""), "P2P_OUT": out,
           "PYTHONPATH": config.PI_QUICKSTART}                      # assetlib importable; no API keys
    try:
        r = subprocess.run([sys.executable, src], cwd=d, env=env, capture_output=True,
                           text=True, timeout=config.GEN_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise GenerationError("generator timed out")
    if not os.path.exists(out):
        raise GenerationError(f"generator produced no GIF.\nstderr:\n{r.stderr[-800:]}")
    return out


def generate(prompt, max_repair=None):
    """Sonnet -> generator code -> GIF, repaired against the validator. Returns (gif_path, code, attempts)."""
    import anthropic
    if not config.ANTHROPIC_API_KEY:
        raise GenerationError("ANTHROPIC_API_KEY not set")
    max_repair = config.MAX_REPAIR if max_repair is None else max_repair
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    spec = _spec_text()
    messages = [{"role": "user", "content":
                 f"SPEC:\n{spec}\n\nMake a 64x64 animated GIF of: {prompt}"}]
    last_err = None
    for attempt in range(1, max_repair + 1):
        resp = client.messages.create(model=config.MODEL, max_tokens=4000,
                                      system=SYSTEM, messages=messages)
        text = "".join(b.text for b in resp.content if b.type == "text")
        code = _extract_code(text)
        try:
            gif = _run_generator(code)
        except GenerationError as e:
            last_err = str(e)
            messages += [{"role": "assistant", "content": text},
                         {"role": "user", "content": f"That failed to run: {last_err}\nFix and resend the full program."}]
            continue
        ok, checks = validate_gif.check(gif)
        if ok:
            return gif, code, attempt
        fails = "; ".join(label for label, passed in checks if not passed)
        last_err = f"spec failures: {fails}"
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": textwrap.dedent(f"""\
                        The GIF rendered but failed the spec: {fails}.
                        Fix the program (adjust size/frames/colours/loop) and resend the full program.""")}]
    raise GenerationError(f"could not produce a compliant GIF in {max_repair} tries ({last_err})")
