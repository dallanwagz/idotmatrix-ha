#!/usr/bin/env python3
"""pack.py — manage named content packs on an iDotMatrix panel.

The panel holds TWO content sets at once, each with its own activation command, so you can
keep two packs loaded and flip between them INSTANTLY (no re-upload):
  - carousel : image slots 0-11, activate = cmd 10/1  (04000a01)
  - phrase   : image slots 14-19, activate = cmd 6/2  (06 02 <count> <indices>)

Packs are defined in packs.json (next to this file, or --manifest):
  { "packs": {
      "usa_deluxe":   { "mode": "carousel", "dwell": 8, "gifs": ["usa_deluxe/usd_stadium_goal.gif", ...] },
      "brazil_flip":  { "mode": "phrase",   "gifs": ["brazil_deluxe/brd_flag_wave.gif", ...] }
  } }
Gif paths are relative to --base (default ~/worldcup on the Pi).

Commands (all but `list` need --panel):
  pack.py list
  pack.py --panel big load  <name>                 # upload + show a pack (full library; slow for big packs)
  pack.py --panel big stage <carousel> <phrase>    # load two packs into the two slot-ranges
  pack.py --panel big flip                         # toggle carousel<->phrase        (INSTANT)
  pack.py --panel big show  carousel|phrase         # activate a staged set            (INSTANT)
  pack.py --panel big status                       # what's staged / active

State (what's staged) is kept in ~/.idm-pack-state.json.
"""
import asyncio
import json
import os
import sys

from bleak import BleakClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idm_push                                                          # noqa: E402
from idm_push import FA_WRITE, frame, push, resolve_addr, run_with_retry  # noqa: E402
from phrase_push import PHRASE_BASE, push_phrase                          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.expanduser("~/.idm-pack-state.json")
DEFAULT_BASE = os.path.expanduser("~/worldcup")
CAROUSEL_ACT = frame(10, 1)                                              # 04000a01


def load_manifest(path):
    return json.load(open(path)).get("packs", {})


def read_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def write_state(s):
    json.dump(s, open(STATE, "w"), indent=2)


def pack_gifs(pack, base):
    out = []
    for rel in pack["gifs"]:
        p = rel if os.path.isabs(rel) else os.path.join(base, rel)
        if not os.path.exists(p):
            sys.exit(f"missing gif: {p}")
        out.append(p)
    return out


async def _activate(addr, frame_bytes):
    async with BleakClient(addr, timeout=25) as c:
        await c.write_gatt_char(FA_WRITE, frame_bytes, response=idm_push.WRITE_RESPONSE)
        await asyncio.sleep(0.5)
    return True


def phrase_frame(count):
    return frame(6, 2, count, *range(PHRASE_BASE, PHRASE_BASE + count))


def do_load(addr, name, pack, base):
    gifs = pack_gifs(pack, base)
    if pack["mode"] == "carousel":
        dwell = pack.get("dwell", 8)
        items = [(open(g, "rb").read(), dwell, os.path.basename(g)) for g in gifs[:12]]
        ok = run_with_retry(lambda: push(addr, items))
        return ok, "carousel", len(items)
    else:                                                               # phrase
        blobs = [(open(g, "rb").read(), os.path.basename(g)) for g in gifs[:6]]
        ok = run_with_retry(lambda: push_phrase(addr, blobs))
        return ok, "phrase", len(blobs)


def main():
    args = sys.argv[1:]
    panel = None
    if "--panel" in args:
        i = args.index("--panel"); panel = args[i + 1]; del args[i:i + 2]
    base = DEFAULT_BASE
    if "--base" in args:
        i = args.index("--base"); base = os.path.expanduser(args[i + 1]); del args[i:i + 2]
    manifest = os.path.join(HERE, "packs.json")
    if "--manifest" in args:
        i = args.index("--manifest"); manifest = args[i + 1]; del args[i:i + 2]
    if not args:
        sys.exit(__doc__)
    cmd, rest = args[0], args[1:]
    packs = load_manifest(manifest)

    if cmd == "list":
        for n, p in packs.items():
            print(f"  {n:20s} {p['mode']:9s} {len(p['gifs'])} gifs")
        return
    if cmd == "status":
        print(json.dumps(read_state(), indent=2)); return

    addr = resolve_addr(panel)                                          # sets idm_push.WRITE_RESPONSE
    st = read_state()

    if cmd == "load":
        name = rest[0]
        if name not in packs:
            sys.exit(f"no pack '{name}' (have: {', '.join(packs)})")
        ok, mode, n = do_load(addr, name, packs[name], base)
        if ok:
            st[mode] = name
            if mode == "phrase":
                st["phrase_count"] = n
            st["active"] = mode
            write_state(st)
        print("done" if ok else "FAILED"); sys.exit(0 if ok else 2)

    if cmd == "stage":
        cname, pname = rest[0], rest[1]
        for n, m in ((cname, "carousel"), (pname, "phrase")):
            if n not in packs or packs[n]["mode"] != m:
                sys.exit(f"'{n}' must be a {m}-mode pack")
        okc, _, _ = do_load(addr, cname, packs[cname], base)            # carousel first (it wipes 0-11)
        if not okc:
            sys.exit("carousel load FAILED")
        okp, _, np = do_load(addr, pname, packs[pname], base)           # phrase second (no wipe)
        if not okp:
            sys.exit("phrase load FAILED")
        write_state({"carousel": cname, "phrase": pname, "phrase_count": np, "active": "phrase"})
        print(f"staged: carousel='{cname}', phrase='{pname}'  (active=phrase). Use `flip` to toggle.")
        return

    if cmd in ("flip", "show"):
        target = ("carousel" if st.get("active") == "phrase" else "phrase") if cmd == "flip" else rest[0]
        if target == "carousel":
            asyncio.run(_activate(addr, CAROUSEL_ACT))
        else:
            asyncio.run(_activate(addr, phrase_frame(st.get("phrase_count", 6))))
        st["active"] = target; write_state(st)
        print(f"active -> {target} ({st.get(target, '?')})")
        return

    sys.exit(f"unknown command: {cmd}\n{__doc__}")


if __name__ == "__main__":
    main()
