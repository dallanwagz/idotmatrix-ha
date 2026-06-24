#!/usr/bin/env python3
"""Deobfuscate downloaded e-toys assets in place -> real GIFs.
Format (DecryptHelper.getDecryptedFile): strip 32 prefix + 32 suffix, '+'->space,
URL-decode, REVERSE, base64-decode."""
import base64, glob, os, urllib.parse

def deobf(content):
    s = content[32:len(content) - 32].replace("+", " ")
    s = urllib.parse.unquote(s)[::-1].strip().replace("\r", "").replace("\n", "")
    return base64.b64decode(s + "=" * (-len(s) % 4))

ok = bad = 0
for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "library", "*", "*.gif")):
    try:
        raw = open(f).read()
        if raw[:6] in ("GIF89a", "GIF87a"):
            ok += 1; continue                      # already decoded
        gif = deobf(raw)
        if gif[:6] in (b"GIF89a", b"GIF87a"):
            open(f, "wb").write(gif); ok += 1
        else:
            bad += 1
    except Exception:
        bad += 1
print(f"decoded {ok}, failed {bad}")
