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
read best; pure black is "off".
Keep the PROGRAM ITSELF COMPACT — well under ~120 lines so it fits comfortably in one response.
Use loops and helper functions; render any words with `Canvas.text(str, colour)`; NEVER place text
or shapes pixel-by-pixel. A rich request is fine, but the CODE must stay short and COMPLETE.
STAY IN BOUNDS: everything must fit inside the 64x64 frame — nothing may run off the edges (no
clipped text or sprites). Text at 64px is tiny: show at most ONE SHORT word at a time centred with
`Canvas.text` (it auto-fits the width), or SCROLL a longer phrase horizontally across frames by
moving its x each frame. NEVER draw a long phrase as static text — it WILL be clipped. If the user
gives several phrases, cycle or scroll through them one at a time.
Output ONLY the complete Python program in a single ```python code block."""


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
        resp = client.messages.create(model=config.MODEL, max_tokens=config.MAX_TOKENS,
                                      system=SYSTEM, messages=messages)
        text = "".join(b.text for b in resp.content if b.type == "text")
        code = _extract_code(text)

        # Diagnose in the cheapest order: truncation -> syntax -> run -> spec.
        problem = None
        if resp.stop_reason == "max_tokens":
            problem = ("your program was CUT OFF (too long for one response). Rewrite it MUCH more "
                       "compactly — loops/helpers, Canvas.text() for words, fewer frames — and make "
                       "sure it is COMPLETE.")
        if problem is None:
            try:
                compile(code, "<generator>", "exec")
            except SyntaxError as se:
                problem = (f"the program has a syntax error: {se.msg} (line {se.lineno}). It may have "
                           "been cut off — resend the COMPLETE, valid program, more compact if needed.")
        if problem is None:
            try:
                gif = _run_generator(code)
                ok, checks = validate_gif.check(gif)
                if ok:
                    return gif, code, attempt
                problem = "the GIF rendered but failed the spec: " + \
                          "; ".join(l for l, p in checks if not p) + ". Adjust size/frames/colours/loop."
            except GenerationError as e:
                problem = f"it failed to run: {e}"

        last_err = problem
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": textwrap.dedent(f"""\
                        {problem}
                        Resend the FULL corrected program in one ```python block.""")}]
    raise GenerationError(f"could not produce a compliant GIF in {max_repair} tries ({last_err})")
