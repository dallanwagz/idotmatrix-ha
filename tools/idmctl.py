#!/usr/bin/env python3
"""Send one command to the running idm_daemon via the command file.

Usage: idmctl.py <name> [args...]   (same command names as idm_cli.py build())
Writes "<seq> <hexframe>" to scratch/idm_cmd.txt, incrementing seq.
"""
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "custom_components", "idotmatrix"))
import protocol as P  # noqa: E402

CMDFILE = os.path.join(HERE, "..", "scratch", "idm_cmd.txt")
SEQFILE = os.path.join(HERE, "..", "scratch", "idm_seq.txt")


def build(argv):
    cmd, *a = argv
    f = {
        "time": lambda: P.set_time(),
        "info": lambda: P.get_device_info(),
        "bright": lambda: P.set_brightness(int(a[0])),
        "color": lambda: P.set_fullscreen_color(int(a[0]), int(a[1]), int(a[2])),
        "clock": lambda: P.set_clock(int(a[0]), r=int(a[1]) if len(a) > 1 else 255,
                                     g=int(a[2]) if len(a) > 2 else 255,
                                     b=int(a[3]) if len(a) > 3 else 255),
        "countdown": lambda: P.set_countdown(int(a[0]), int(a[1]), int(a[2])),
        "chrono": lambda: P.set_chronograph(int(a[0])),
        "score": lambda: P.set_scoreboard(int(a[0]), int(a[1])),
        "flip": lambda: P.set_flip(bool(int(a[0]))),
        "screen": lambda: P.set_screen(bool(int(a[0]))),
        "diy": lambda: P.enter_diy(int(a[0])),
        "pixel": lambda: P.draw_pixel(int(a[0]), int(a[1]), int(a[2]), int(a[3]), int(a[4])),
        "reset": lambda: P.reset_device(),
        "quit": lambda: b"\x00",
        "raw": lambda: bytes.fromhex(a[0]),
    }[cmd]()
    return f


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    if sys.argv[1] == "quit":
        frame = "quit"
    else:
        frame = build(sys.argv[1:]).hex()
    seq = 0
    if os.path.exists(SEQFILE):
        seq = int(open(SEQFILE).read().strip() or 0)
    seq += 1
    open(SEQFILE, "w").write(str(seq))
    open(CMDFILE, "w").write(f"{seq} {frame}")
    print(f"sent seq={seq}: {sys.argv[1:]} -> {frame}")


if __name__ == "__main__":
    main()
