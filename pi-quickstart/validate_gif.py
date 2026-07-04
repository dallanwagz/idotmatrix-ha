#!/usr/bin/env python3
"""validate_gif.py — check (or auto-fix) a GIF against the iDotMatrix 64x64 spec.

Spec (see docs/idm64-gif-spec.md): 64x64, animated GIF, loops forever, <=100 KB (target 90 KB),
<=256 colours/frame, frame duration >= ~40 ms.

    python3 validate_gif.py in.gif                 # report PASS/FAIL per rule
    python3 validate_gif.py in.gif --fix out.gif   # write a compliant version

--fix will: resize frames to 64x64, force infinite loop, clamp durations to >=40 ms, and if the
file is over the size target, shrink it (reduce colours, then drop frames) until it fits.
"""
import os
import sys

from PIL import Image, ImageSequence

SIZE = 64
MAX_BYTES = 100 * 1024
TARGET_BYTES = 90 * 1024
MIN_MS = 40


def frames_of(im):
    fs, durs = [], []
    for fr in ImageSequence.Iterator(im):
        fs.append(fr.convert("RGB"))
        durs.append(fr.info.get("duration", 80))
    return fs, durs


def report(path):
    im = Image.open(path)
    fs, durs = frames_of(im)
    size = os.path.getsize(path)
    loop = im.info.get("loop", None)
    maxc = 0
    for f in fs:
        c = f.getcolors(maxcolors=1 << 24)
        maxc = max(maxc, len(c) if c else 99999)
    checks = [
        ("format is GIF", im.format == "GIF"),
        (f"dimensions 64x64 (got {im.size[0]}x{im.size[1]})", im.size == (SIZE, SIZE)),
        (f"file size <= 100 KB (got {size/1024:.1f} KB)", size <= MAX_BYTES),
        (f"animated, >=2 frames (got {len(fs)})", len(fs) >= 2),
        (f"loops forever (loop={loop})", loop == 0),
        (f"<=256 colours/frame (max {maxc})", maxc <= 256),
        (f"frame duration >= {MIN_MS}ms (min {min(durs) if durs else 0}ms)", (min(durs) if durs else 0) >= MIN_MS),
    ]
    ok = all(c[1] for c in checks)
    for label, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}")
    print(f"  == {'COMPLIANT' if ok else 'NOT compliant — run with --fix'} ==")
    return ok


def save(frames, durs, path):
    frames[0].save(path, format="GIF", save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, disposal=2)


def fix(inp, out):
    im = Image.open(inp)
    fs, durs = frames_of(im)
    fs = [f.resize((SIZE, SIZE)) if f.size != (SIZE, SIZE) else f for f in fs]
    durs = [max(MIN_MS, d) for d in durs]
    if len(fs) < 2:                                   # a still -> tiny 2-frame loop
        fs = fs * 2; durs = durs * 2
    save(fs, durs, out)
    # shrink under the target: reduce colours, then drop frames
    for colors in (256, 192, 128, 96, 64, 48, 32):
        if os.path.getsize(out) <= TARGET_BYTES:
            break
        q = [f.quantize(colors=colors, dither=Image.Dither.FLOYDSTEINBERG).convert("RGB") for f in fs]
        save(q, durs, out)
    while os.path.getsize(out) > TARGET_BYTES and len(fs) > 8:
        fs = fs[::2]; durs = [d * 2 for d in durs[::2]]   # halve frames, keep timing
        q = [f.quantize(colors=64, dither=Image.Dither.FLOYDSTEINBERG).convert("RGB") for f in fs]
        save(q, durs, out)
    print(f"wrote {out}  ({os.path.getsize(out)/1024:.1f} KB, {len(fs)} frames)")


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    inp = a[0]
    if "--fix" in a:
        out = a[a.index("--fix") + 1]
        fix(inp, out)
        print("--- validating the fixed file ---")
        report(out)
    else:
        sys.exit(0 if report(inp) else 1)


if __name__ == "__main__":
    main()
