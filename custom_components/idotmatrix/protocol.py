"""Pure, dependency-free iDotMatrix BLE protocol.

This module builds the exact byte frames the official iDotMatrix Android app
(``com.tech.idotmatrix`` v2.1.1) writes to the device, and parses the inbound
notify/ACK frames. It has **no Home Assistant or Bluetooth dependencies** so it
can be unit-tested against golden frames and reused from any Python host that
has raw access to a Bluetooth adapter.

Wire facts (reverse-engineered from the decompiled app and cross-checked against
``derkalle4/python-idotmatrix-library`` and ``8none1/idotmatrix``):

* Transport: BLE GATT. Service ``0x00FA``.
* Write characteristic   ``0000fa02-0000-1000-8000-00805f9b34fb`` (write).
* Notify characteristic  ``0000fa03-0000-1000-8000-00805f9b34fb`` (status/ACK).
* Firmware-version read   ``d44bc439-abfd-45a2-b575-925416129602`` (ASCII string).
* Device advertises a name beginning ``IDM-``.

Control-frame format::

    [len_lo, len_hi, CMD, SUB, *payload]

``len`` is the **total** frame length as a little-endian uint16 (it includes the
two length bytes themselves). There is **no checksum** on control frames. Bulk
media (image / GIF / text / DIY animation) uses a separate chunked transport with
a CRC32 — see :class:`ImageUpload`.

Every value here is sourced from ``com/tech/idotmatrix/ble/BleProtocolN.java``,
``ble/send/{BaseSend,SendCore}.java`` and the ``core/data/*Agreement.java`` family.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum

# ---------------------------------------------------------------------------
# GATT identifiers
# ---------------------------------------------------------------------------

SERVICE_UUID = "000000fa-0000-1000-8000-00805f9b34fb"
WRITE_UUID = "0000fa02-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000fa03-0000-1000-8000-00805f9b34fb"
VERSION_UUID = "d44bc439-abfd-45a2-b575-925416129602"

NAME_PREFIX = "IDM-"

# ``ledType`` -> (width, height). Source: AppData.java setLedType().
LED_SIZES: dict[int, tuple[int, int]] = {
    1: (16, 16),
    2: (8, 32),
    3: (32, 32),   # HXS-002 / NL-XSD-32 — the target device
    4: (64, 64),
    6: (24, 48),
    7: (16, 32),
    11: (16, 64),
}


# ---------------------------------------------------------------------------
# Enums mirrored from the app
# ---------------------------------------------------------------------------


class ClockStyle(IntEnum):
    """``sendClockMode`` style index (BleProtocolN.sendClockMode)."""

    RWATCH = 0
    CHRISTMAS = 1
    RACING = 2
    INVERTED_FULL = 3
    ANALOG_LIKE = 4
    SMALL = 5
    SQUARE = 6
    LARGE = 7


class CountdownMode(IntEnum):
    DISABLE = 0
    START = 1
    PAUSE = 2
    RESTART = 3


class ChronographMode(IntEnum):
    RESET = 0
    START = 1
    PAUSE = 2
    CONTINUE = 3


class DiyFun(IntEnum):
    """``DiyImageFun`` — graffiti/DIY draw-mode lifecycle."""

    QUIT_NOSAVE = 0
    ENTER_CLEAR = 1
    QUIT_STILL = 2
    ENTER_NOCLEAR = 3


# ---------------------------------------------------------------------------
# Framing helper
# ---------------------------------------------------------------------------


def _u8(v: int) -> int:
    """Clamp an int into a single unsigned byte (mirrors a Java ``(byte)`` cast)."""
    return v & 0xFF


def frame(cmd: int, sub: int, *payload: int) -> bytes:
    """Build a control frame ``[len_lo, len_hi, cmd, sub, *payload]``.

    ``len`` is the total length (header + payload), little-endian uint16.
    """
    body = bytes(_u8(b) for b in payload)
    total = 4 + len(body)
    return bytes((total & 0xFF, (total >> 8) & 0xFF, _u8(cmd), _u8(sub))) + body


# ---------------------------------------------------------------------------
# Control commands  (each returns the exact bytes to write to fa02)
# ---------------------------------------------------------------------------


def set_time(when: datetime | None = None) -> bytes:
    """Sync the device clock. CMD 1 / SUB 0x80.

    Payload: ``year-2000, month, day, weekday(1=Mon..7=Sun), hour, minute, second``.
    """
    t = when or datetime.now()
    # Java DateUtils.getWeekOfDate(): Mon=1..Sun=7. Python weekday(): Mon=0..Sun=6.
    weekday = t.weekday() + 1
    return frame(1, 0x80, t.year - 2000, t.month, t.day, weekday, t.hour, t.minute, t.second)


def get_device_info() -> bytes:
    """Query LED type / device info. CMD 1 / SUB 0x80, no payload. (``getLedType``)."""
    return frame(1, 0x80)


def set_brightness(percent: int) -> bytes:
    """Screen brightness 0-100. CMD 4 / SUB 0x80."""
    return frame(4, 0x80, max(0, min(100, percent)))


def set_fullscreen_color(r: int, g: int, b: int) -> bytes:
    """Fill the whole panel with one RGB colour. CMD 2 / SUB 2."""
    return frame(2, 2, r, g, b)


def set_clock(
    style: int,
    *,
    show_date: bool = True,
    hour24: bool = True,
    r: int = 255,
    g: int = 255,
    b: int = 255,
) -> bytes:
    """Show a clock face. CMD 6 / SUB 1.

    The style byte packs flags: ``style | (0x80 if show_date) | (0x40 if hour24)``.
    Trailing bytes are the RGB colour.
    """
    flags = (style & 0x3F) | (0x80 if show_date else 0) | (0x40 if hour24 else 0)
    return frame(6, 1, flags, r, g, b)


def set_effect(model: int, speed: int, colors, saturation: int = 100) -> bytes:
    """Lighting effect ("MutilColor"). CMD 3 / SUB 2. (MutilColorAgreement.sendMutilColor)

    ``[3,2, model, speed, count, r0,g0,b0, ...]`` — total len = ``count*3 + 7``.
    ``model`` is the scene/style 0-6 (7 modes); ``speed`` 0-100 (the lightning-bolt slider);
    ``colors`` is a list of (r,g,b). Each channel is value-``1``->``0`` remapped (1 is reserved)
    then scaled by ``saturation/100`` (app default 100 = passthrough). RGB 0-255.
    Hardware-confirmed on the 32×32 (animated multi-colour effect runs; ack ``0500030201``).
    """
    payload = [model & 0xFF, max(0, min(100, speed)), len(colors) & 0xFF]
    for r, g, b in colors:
        for ch in (r, g, b):
            ch = 0 if ch == 1 else (ch & 0xFF)
            payload.append((ch * max(0, min(100, saturation))) // 100)
    return frame(3, 2, *payload)


def set_countdown(mode: int, minutes: int, seconds: int) -> bytes:
    """Countdown timer. CMD 8 / SUB 0x80. ``mode`` per :class:`CountdownMode`."""
    return frame(8, 0x80, mode, minutes, seconds)


def set_chronograph(mode: int) -> bytes:
    """Stopwatch. CMD 9 / SUB 0x80. ``mode`` per :class:`ChronographMode`."""
    return frame(9, 0x80, mode)


def set_scoreboard(count1: int, count2: int) -> bytes:
    """Scoreboard. CMD 10 / SUB 0x80. Two uint16 scores, little-endian on the wire.

    Endianness SETTLED little-endian: verified on hardware (258 shows as 258) and
    independently emitted LE by 8none1, derkalle4, and markusressel + the app
    (``short2Bytes`` BE then placed ``[1],[0]``). The "big-endian" in OSS comments is wrong.
    """
    return frame(10, 0x80, count1 & 0xFF, (count1 >> 8) & 0xFF, count2 & 0xFF, (count2 >> 8) & 0xFF)


def set_flip(flip: bool) -> bytes:
    """Rotate the display 180 degrees. CMD 6 / SUB 0x80."""
    return frame(6, 0x80, 1 if flip else 0)


def set_text_speed(speed: int) -> bytes:
    """Scrolling-text speed. CMD 3 / SUB 1."""
    return frame(3, 1, speed)


def set_screen(on: bool) -> bytes:
    """Turn the panel on/off (``sendSwitchplate``). CMD 7 / SUB 1."""
    return frame(7, 1, 1 if on else 0)


def set_time_indicator(on: bool) -> bytes:
    """Hourly time-indicator master switch. CMD 7 / SUB 0x80."""
    return frame(7, 0x80, 1 if on else 0)


def set_eco(flag: int, start_h: int, start_m: int, end_h: int, end_m: int, light: int = 10) -> bytes:
    """Eco / sleep schedule (auto-dim window). CMD 2 / SUB 0x80.

    Payload = ``flag, start_h, start_m, end_h, end_m, light`` — ground-truthed against
    ``EcoActivity.java:62`` (``setEco(flag, hour1, min1, hour2, min2, light)``). ``flag``
    1=enabled/0=off; ``light`` is the dimmed brightness during the window (app default 10).
    (Corrected from an earlier mislabeled signature; confirmed by 8none1 + derkalle4 + markusressel.)
    """
    return frame(2, 0x80, flag, start_h, start_m, end_h, end_m, light)


def _pwd_pairs(password: str) -> list[int]:
    if len(password) != 6 or not password.isdigit():
        raise ValueError("password must be 6 digits")
    return [int(password[i : i + 2]) for i in (0, 2, 4)]


def set_password(password: str, enable: int = 1) -> bytes:
    """Set the 6-digit device password. CMD 4 / SUB 2. (BleProtocolN.setPwd:140)

    Wire: ``[8,0,4,2, enable, dd1, dd2, dd3]`` where the 6 digits are sent as three
    decimal byte-pairs (e.g. "123456" -> 12,34,56). ``enable`` 1=on/0=off.
    """
    return frame(4, 2, enable, *_pwd_pairs(password))


def verify_password(password: str) -> bytes:
    """Verify the 6-digit device password. CMD 5 / SUB 2. (BleProtocolN.verifyPwd:188)

    Wire: ``[7,0,5,2, dd1, dd2, dd3]`` (same decimal-pair encoding as set_password).
    """
    return frame(5, 2, *_pwd_pairs(password))


def set_screen_light_time(value: int) -> bytes:
    """Screen-on duration setting. CMD 15 / SUB 0x80."""
    return frame(15, 0x80, value)


def get_screen_light_time() -> bytes:
    """Query screen-on duration. CMD 15 / SUB 0x80, payload 0xFF."""
    return frame(15, 0x80, 0xFF)


def set_joint(mode: int) -> bytes:
    """Multi-panel 'joint'/tiling mode. CMD 12 / SUB 0x80. (Not used on a single 32x32.)"""
    return frame(12, 0x80, mode)


def reset_device() -> bytes:
    """Soft reset. CMD 3 / SUB 0x80. (App follows with brightness 0x50.)"""
    return frame(3, 0x80)


def enter_diy(mode: int) -> bytes:
    """Enter/leave the DIY draw mode. CMD 4 / SUB 1. ``mode`` per :class:`DiyFun`."""
    return frame(4, 1, mode)


def draw_pixel(r: int, g: int, b: int, x: int, y: int, option: int = 0) -> bytes:
    """Live graffiti single-pixel draw (no CRC, no ACK). CMD 5 / SUB 1.

    Frame ``[0x0a,0,5,1, option, r,g,b, col,row]`` (DIY type 5). ``option`` is the
    move/effect type (0 = none). Colour is **RGB** order (same as the bulk image
    path). Hardware-captured golden frame: ``0a00050100ff00000808`` = red pixel at
    (col=8,row=8).
    """
    return frame(5, 1, option, r, g, b, x, y)


# ---------------------------------------------------------------------------
# Bulk media upload (image / GIF / text)  — chunked, CRC32, ACK state machine
# ---------------------------------------------------------------------------

OUTER_CHUNK = 4096        # getSendData4096: media split into 4 KiB "big packets"
INNER_MTU_HIGH = 509      # what the Android app uses (negotiated MTU 512 -> 512-3)
INNER_MTU_LOW = 18        # fallback when MTU not negotiated
# Hardware finding: the panel's fa02 receiver silently DROPS GATT writes larger than
# ~256 bytes even when a 512 MTU is negotiated (Android fragments transparently; other
# stacks send the whole value and the device ignores it). Cap inner writes here.
SAFE_WRITE_LEN = 244


class DataType(IntEnum):
    """Value of header byte[2] for the bulk ``*Agreement`` upload path (byte[3]=0).

    NB: this is the legacy ImageAgreement/GifAgreement encoding (byte[2] varies,
    byte[3]=0). The newer SendCore path uses a different 2-byte dataType
    (image={2,0}, gif={3,0}, text={0,1}, diy={5,1}).
    """

    IMAGE = 2   # ImageAgreement: byte[2]=2, byte[3]=0
    GIF = 1     # GifAgreement:   byte[2]=1, byte[3]=0
    ANIM = 0    # DIY animation:  byte[2]=0, byte[3]=0


def _crc32_le(data: bytes) -> bytes:
    return struct.pack("<I", zlib.crc32(data) & 0xFFFFFFFF)


def image_rgb(pixels: bytes, width: int = 32, height: int = 32) -> "ImageUpload":
    """Build an :class:`ImageUpload` from raw **RGB** pixel bytes (row-major, 3 B/px).

    Validated on hardware: the panel wants RGB order (the app's ``bitmap2BGR`` is
    misleadingly named — it actually emits RGB), row-major top-to-bottom. A 32x32
    frame is ``32*32*3 == 3072`` bytes.
    """
    if len(pixels) != width * height * 3:
        raise ValueError(f"expected {width * height * 3} RGB bytes, got {len(pixels)}")
    return ImageUpload(pixels, DataType.IMAGE)


@dataclass
class ImageUpload:
    """Builds the outer 4 KiB packets for a still image upload.

    Mirrors ``ImageAgreement``. For a 32x32 panel a static **RGB** frame is 3072
    bytes => a single outer packet with a 16-byte header.

    Use :meth:`outer_packets` to get the per-4KiB buffers, then split each into GATT
    writes with :func:`inner_writes` (which caps at :data:`SAFE_WRITE_LEN`), sending
    the next outer packet only after the device ACKs (see :func:`parse_status`).
    Hardware-confirmed: a 3072 B RGB frame uploads and ACKs ``[05,00,02,00,03]``.
    """

    data: bytes
    data_type: DataType = DataType.IMAGE
    image_index: int = 12      # byte[15]; 12 => timeSign forced to 0 (no schedule)
    time_sign: int = 0         # bytes[13-14], little-endian; ignored when image_index==12

    def outer_packets(self) -> list[bytes]:
        crc = _crc32_le(self.data)
        total = len(self.data)
        dtype0, dtype1 = int(self.data_type) & 0xFF, 0   # header byte[2]=type, byte[3]=0
        ts = 0 if self.image_index == 12 else self.time_sign
        packets: list[bytes] = []
        chunks = [self.data[i : i + OUTER_CHUNK] for i in range(0, len(self.data), OUTER_CHUNK)] or [b""]
        for i, chunk in enumerate(chunks):
            option = 0 if i == 0 else 2
            length = len(chunk) + 16
            header = (
                bytes((length & 0xFF, (length >> 8) & 0xFF, dtype0, dtype1, option))
                + struct.pack("<I", total)
                + crc
                + bytes((ts & 0xFF, (ts >> 8) & 0xFF, self.image_index & 0xFF))
            )
            packets.append(header + chunk)
        return packets


def inner_writes(outer_packet: bytes, max_len: int = SAFE_WRITE_LEN) -> list[bytes]:
    """Split one outer 4 KiB packet into GATT writes of at most ``max_len`` bytes.

    Defaults to :data:`SAFE_WRITE_LEN` (244) because the panel drops larger writes.
    """
    step = max(20, min(max_len, SAFE_WRITE_LEN))
    return [outer_packet[i : i + step] for i in range(0, len(outer_packet), step)]


# ---------------------------------------------------------------------------
# Inbound notify / ACK parsing
# ---------------------------------------------------------------------------


class Ack(IntEnum):
    UNKNOWN = -1
    INVALID = 0
    NEXT = 1       # device ready for the next 4 KiB packet
    NO_SPACE = 2   # storage full
    DONE = 3       # transfer complete


@dataclass
class Status:
    """Decoded inbound frame from the notify (fa03) characteristic."""

    raw: bytes
    data_type: int | None = None
    ack: Ack = Ack.UNKNOWN


def parse_status(value: bytes) -> Status:
    """Parse an inbound notify frame ``[len, 0, dataType, opt, status, ...]``.

    The upload state machines key on ``value[2]`` (dataType) and ``value[4]``
    (status): 1=send next packet, 2=no space, 3=transfer finished.
    """
    if len(value) < 5:
        return Status(raw=value)
    status = value[4]
    try:
        ack = Ack(status)
    except ValueError:
        ack = Ack.UNKNOWN
    return Status(raw=value, data_type=value[2], ack=ack)
