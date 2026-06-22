"""Golden-frame tests for the iDotMatrix protocol.

Frames marked CAPTURED were observed byte-for-byte on real hardware (HXS-002 /
NL-XSD-32, 32x32, firmware TR2306R007) via HCI snoop or live bleak control and
confirmed visually by the operator. See docs/PROTOCOL.md.
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "idotmatrix"))
import protocol as P  # noqa: E402


def h(b: bytes) -> str:
    return b.hex()


# --- framing -------------------------------------------------------------

def test_frame_length_is_total_le16():
    assert P.frame(4, 0x80, 50) == bytes.fromhex("0500048032")
    # length includes the 2 length bytes + cmd + sub + payload
    assert P.frame(1, 0x80) == bytes.fromhex("0400 0180".replace(" ", ""))


# --- CAPTURED golden frames (byte-for-byte on hardware) ------------------

def test_set_time_captured():
    # Captured on connect: 2026-06-22 21:22:51, weekday Mon(1)
    assert h(P.set_time(datetime(2026, 6, 22, 21, 22, 51))) == "0b0001801a061601151633"


def test_enter_diy_captured():
    assert h(P.enter_diy(1)) == "0500040101"


def test_draw_pixel_captured():
    # Captured: red pixel at (col=8,row=8) while drawing in graffiti
    assert h(P.draw_pixel(255, 0, 0, 8, 8)) == "0a00050100ff00000808"


def test_clock_captured():
    # Captured: style 0, show_date + 24h => flags 0xC0, white
    assert h(P.set_clock(0, show_date=True, hour24=True, r=255, g=255, b=255)) == "08000601c0ffffff"


def test_countdown_captured():
    assert h(P.set_countdown(int(P.CountdownMode.START), 0, 30)) == "0700088001001e"


def test_chronograph_captured():
    assert h(P.set_chronograph(int(P.ChronographMode.START))) == "0500098001"


def test_scoreboard_little_endian_captured():
    # Confirmed on-screen: 258 (=0x0102 -> LE 02 01) left, 7 right
    assert h(P.set_scoreboard(258, 7)) == "08000a8002010700"


def test_flip_captured():
    assert h(P.set_flip(True)) == "0500068001"
    assert h(P.set_flip(False)) == "0500068000"


def test_screen_captured():
    assert h(P.set_screen(False)) == "0500070100"
    assert h(P.set_screen(True)) == "0500070101"


# --- validated builders --------------------------------------------------

def test_fullscreen_color():
    assert h(P.set_fullscreen_color(255, 0, 0)) == "07000202ff0000"   # red, visually confirmed
    assert h(P.set_fullscreen_color(0, 0, 255)) == "070002020000ff"   # blue, visually confirmed


def test_brightness_bounds():
    assert h(P.set_brightness(100)) == "0500048064"
    assert h(P.set_brightness(0)) == "0500048000"
    assert h(P.set_brightness(150)) == "0500048064"   # clamped to 100
    assert h(P.set_brightness(-5)) == "0500048000"    # clamped to 0


def test_clock_flag_bits():
    # no date, 12h => flags == style only
    assert P.set_clock(2, show_date=False, hour24=False)[4] == 0x02
    # date only => 0x80 | style
    assert P.set_clock(0, show_date=True, hour24=False)[4] == 0x80
    # 24h only => 0x40 | style
    assert P.set_clock(0, show_date=False, hour24=True)[4] == 0x40


def test_get_device_info():
    assert h(P.get_device_info()) == "0400 0180".replace(" ", "")


# --- image upload (BGR, chunked, CRC32) ----------------------------------

def test_image_upload_header():
    data = bytes([1, 2, 3] * (32 * 32))   # 3072 bytes
    up = P.ImageUpload(data, P.DataType.IMAGE, image_index=12)
    packets = up.outer_packets()
    assert len(packets) == 1
    pkt = packets[0]
    assert len(pkt) == 3072 + 16
    assert pkt[0] | (pkt[1] << 8) == 3072 + 16   # length LE16
    assert pkt[2] == 2 and pkt[3] == 0           # dataType image {2,0}
    assert pkt[4] == 0                            # option (first packet)
    assert pkt[5] | (pkt[6] << 8) | (pkt[7] << 16) | (pkt[8] << 24) == 3072  # totalLen LE32
    import zlib
    assert pkt[9:13] == zlib.crc32(data).to_bytes(4, "little")
    assert pkt[13] == 0 and pkt[14] == 0         # timeSign 0 (image_index==12)
    assert pkt[15] == 12                          # image index


def test_inner_writes_split():
    pkt = bytes(range(256)) * 13   # 3328 bytes
    writes = P.inner_writes(pkt, mtu_ok=True)
    assert all(len(w) <= P.INNER_MTU_HIGH for w in writes)
    assert b"".join(writes) == pkt


# --- notify / status parsing ---------------------------------------------

def test_parse_status_ack():
    # captured ACKs
    assert P.parse_status(bytes.fromhex("0500020201")).ack == P.Ack.NEXT
    assert P.parse_status(bytes.fromhex("0500048001")).ack == P.Ack.NEXT
    s = P.parse_status(bytes.fromhex("0500070101"))
    assert s.data_type == 0x07 and s.ack == P.Ack.NEXT


def test_parse_status_short_frame():
    assert P.parse_status(b"\x01\x02").ack == P.Ack.UNKNOWN
