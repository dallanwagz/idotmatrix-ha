#!/usr/bin/env python3
"""
panel_idotmatrix — PanelDriver for the iDotMatrix HXS-002 / NL-XSD-32 (32x32 RGB888 BLE).

Third reference family alongside Pixoo16 (palette/no-stuffing, SPP) and TimeBox-mini
(rgb444/stuffed, SPP): this one is **BLE GATT, true-colour RGB888, chunked+CRC32 stills**.
It is the fleet's hi-res true-colour HERO panel — big and detailed, but its full-frame
still is an ACK-paced chunked upload, so its sustained fps is low (a detail soldier, not a
motion carrier). It also has a *Verified* SCREEN_POWER (blackout/snap-back), which the
Pixoo could only infer.

Wire protocol + all frame builders live in the vendored, hardware-tested `idm_protocol`
(copied from github.com/dallanwagz/idotmatrix-ha; 18 golden-frame unit tests). This module
adds the sync<->async BLE bridge and the PanelDriver/PanelSpec.

Transport: BLE GATT. service 0x00FA, write fa02, notify fa03 (ACK [len,0,cmd,sub,status]).
Address: `mac` = the BLE address — a MAC on Linux/BlueZ, a CoreBluetooth UUID on macOS.
"""
from __future__ import annotations

import asyncio
import threading
import time

from PIL import Image, ImageDraw, ImageFont

import idm_protocol as IDM
from panel_api import Caps, PanelDriver, PanelSpec, register_driver

WIDTH = HEIGHT = 32


# ---------------------------------------------------------------------------
# colour correction (driver applies its OWN, so the orchestrator renders true colour)
# ---------------------------------------------------------------------------
def _correct_rgb(img: Image.Image, spec: PanelSpec) -> bytes:
    """Apply gamma / per-channel gain / white_mix, return row-major RGB bytes (3/px).

    Identity while gamma=1, gain=(1,1,1), white_mix=0 (i.e. until colour-matched to the
    fleet). Kept pure-python; 32x32 = 1024 px is trivial at this panel's fps.
    """
    g, (kr, kg, kb), wm = spec.gamma, spec.color_gain, spec.white_mix
    do_g = g != 1.0
    do_k = (kr, kg, kb) != (1.0, 1.0, 1.0)
    out = bytearray()
    for (r, gr, b) in img.getdata():
        if do_g:
            r = int(255 * (r / 255) ** g); gr = int(255 * (gr / 255) ** g); b = int(255 * (b / 255) ** g)
        if do_k:
            r *= kr; gr *= kg; b *= kb
        if wm:
            y = 0.299 * r + 0.587 * gr + 0.114 * b
            r = r * (1 - wm) + y * wm; gr = gr * (1 - wm) + y * wm; b = b * (1 - wm) + y * wm
        out += bytes((max(0, min(255, int(r))), max(0, min(255, int(gr))), max(0, min(255, int(b)))))
    return bytes(out)


# ---------------------------------------------------------------------------
# native scrolling text — glyph-bitmap payload the device scrolls itself (dataType 3)
# ---------------------------------------------------------------------------
# Decoded from a captured "Hi": [count][6B hdr][global fg(3) bg(3)][pad] then per char
# [02][fg(3)][bg(3)][11-byte bitmap][00 00]. Bitmap = 11 rows x 8 cols, MSB=leftmost col.
_TEXT_HDR = bytes.fromhex("000101000001")     # 6-byte header (mode/speed flags) from a real frame
_FONT = ImageFont.load_default()


def _glyph_rows(ch: str) -> bytes:
    """Rasterize one char to 11 bytes (row-major, 8 cols, MSB = leftmost), the device format."""
    im = Image.new("1", (8, 11), 0)
    dr = ImageDraw.Draw(im)
    try:
        bb = dr.textbbox((0, 0), ch, font=_FONT)
        x = (8 - (bb[2] - bb[0])) // 2 - bb[0]
        y = (11 - (bb[3] - bb[1])) // 2 - bb[1]
    except Exception:
        x = y = 0
    dr.text((x, y), ch, fill=1, font=_FONT)
    px = im.load()
    # device renders LSB as the LEFTMOST column (decoded from a mirror-flip on "GOAL")
    return bytes(sum((1 << c) for c in range(8) if px[c, r]) for r in range(11))


def text_payload(text: str, fg=(255, 255, 255), bg=(0, 0, 0)) -> bytes:
    """Build the dataType-3 glyph payload the device scrolls (fixed 8x11 glyphs)."""
    chars = text[:255]
    out = bytearray([len(chars)]) + _TEXT_HDR + bytes(fg) + bytes(bg) + b"\x00"
    for ch in chars:
        out += b"\x02" + bytes(fg) + bytes(bg) + _glyph_rows(ch) + b"\x00\x00"
    return bytes(out)


def encode_still(img: Image.Image, spec: PanelSpec) -> bytes:
    """Deterministic full-frame wire bytes (the single outer packet for a 32x32 still).

    PURE — no BLE. This is the golden-frame regression anchor: encode_still(known image)
    must reproduce byte-for-byte. push_frame() splits this into MTU-safe GATT writes.
    """
    if img.size != (spec.width, spec.height):
        img = img.resize((spec.width, spec.height))
    rgb = _correct_rgb(img.convert("RGB"), spec)
    packets = IDM.image_rgb(rgb, spec.width, spec.height).outer_packets()
    return packets[0] if len(packets) == 1 else b"".join(packets)


# ---------------------------------------------------------------------------
# sync<->async BLE bridge (bleak loop on a daemon thread)
# ---------------------------------------------------------------------------
class _BleLink:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._client = None
        self.last_notify: bytes = b""
        self.done_acks: int = 0          # count of completed-still ACKs ([..,03]) — the true fps signal
        self.dropped: int = 0            # frames dropped because the previous was still in flight
        self._inflight: bool = False     # a still is uploading + not yet ACKed
        self._inflight_t: float = 0.0
        self._ack_evt = threading.Event()  # set on a NEXT/DONE/NO_SPACE ack (for ACK-gated uploads)
        self._last_ack = None

    def _ensure_loop(self) -> None:
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
            self._thread.start()

    def _run(self, coro, timeout: float = 20.0):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout)

    def _submit(self, coro):
        """Fire-and-forget: queue on the loop, do NOT wait (non-blocking hot path)."""
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def connect(self, address: str, timeout: float = 20.0) -> None:
        from bleak import BleakClient, BleakScanner

        self._ensure_loop()

        def _on_notify(_c, data):
            self.last_notify = bytes(data)
            st = IDM.parse_status(bytes(data))
            if st.ack in (IDM.Ack.NEXT, IDM.Ack.DONE, IDM.Ack.NO_SPACE):
                self._last_ack = st.ack        # ACK-gated upload (GIF/image multi-packet)
                self._ack_evt.set()
            if st.ack is IDM.Ack.DONE:
                self.done_acks += 1
                self._inflight = False         # the still finished -> ready for the next

        async def _finish(client):
            try:
                await client.start_notify(IDM.NOTIFY_UUID, _on_notify)
            except Exception:
                pass
            self._client = client

        async def _aconnect():
            # FAST PATH (BlueZ/Linux, real MAC): connect STRAIGHT to the address — no scan.
            # A fresh BleakScanner scan is the ~5-8s bottleneck on a scene switch; BlueZ
            # connects a cached/recently-seen MAC directly in ~2-4s. Short timeout so a real
            # failure (device off) falls through to the scan quickly instead of stalling.
            if address:
                try:
                    client = BleakClient(address, timeout=6.0)
                    await client.connect()
                    await _finish(client)
                    return
                except Exception:
                    pass
            # FALLBACK: scan by address, then by name (macOS UUID quirks / cold cache).
            dev = None
            if address:
                dev = await BleakScanner.find_device_by_address(address, timeout=8.0)
            if dev is None:
                dev = await BleakScanner.find_device_by_filter(
                    lambda d, a: bool((d.name or "").startswith(IDM.NAME_PREFIX)
                                      or (a.local_name or "").startswith(IDM.NAME_PREFIX)),
                    timeout=10.0,
                )
            client = BleakClient(dev or address, timeout=timeout)
            await client.connect()
            await _finish(client)

        self._run(_aconnect(), timeout + 5)

    @property
    def connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    def write(self, data: bytes) -> None:
        """Blocking single small write (brightness, screen, clock)."""
        self._run(self._client.write_gatt_char(IDM.WRITE_UUID, data, response=False), 5)

    def write_chunks_ff(self, chunks: list[bytes], pace: float = 0.0, stale: float = 1.0) -> bool:
        """Fire-and-forget still upload, returns immediately. DROPS the frame (returns False)
        if the previous still is still uploading — a slow panel must shed frames, not queue
        them unboundedly. `stale` lets a new frame through if an ACK was missed."""
        now = time.monotonic()
        if self._inflight and (now - self._inflight_t) < stale:
            self.dropped += 1
            return False
        self._inflight = True
        self._inflight_t = now

        async def _w():
            for c in chunks:
                await self._client.write_gatt_char(IDM.WRITE_UUID, c, response=False)
                if pace:
                    await asyncio.sleep(pace)
        self._submit(_w())
        return True

    def upload_acked(self, packets: list[bytes], pace: float = 0.01, timeout: float = 10.0):
        """ACK-gated multi-packet upload (GIF/image). Sends each 4K packet, then waits for the
        device's NEXT ([..,1]) / DONE ([..,3]) ack before the next. Returns (ok, info)."""
        for i, pkt in enumerate(packets):
            self._last_ack = None
            self._ack_evt.clear()

            async def _w(p=pkt):
                for c in IDM.inner_writes(p):
                    await self._client.write_gatt_char(IDM.WRITE_UUID, c, response=False)
                    if pace:
                        await asyncio.sleep(pace)
            self._submit(_w())
            if not self._ack_evt.wait(timeout):
                return False, f"timeout waiting for ack on packet {i}/{len(packets)}"
            if self._last_ack is IDM.Ack.NO_SPACE:
                return False, "device reported NO_SPACE"
        return True, f"{len(packets)} packets acked"

    def disconnect(self) -> None:
        if self._client is not None:
            try:
                self._run(self._client.disconnect(), 6)
            except Exception:
                pass
        self._client = None


# ---------------------------------------------------------------------------
# SPEC — every field tagged Verified / Inferred / Unknown (see comments)
# ---------------------------------------------------------------------------
IDOTMATRIX32_SPEC = PanelSpec(
    model="idotmatrix32", family="idotmatrix-ble",
    # GEOMETRY
    width=32, height=32,            # [Verified] adv deviceType 3 + renders 32x32
    pitch_mm=5.32,                  # [Verified — measured] 5.0mm pixel + 0.32mm inter-pixel gap (lit grid ~170mm)
    bezel_mm=8.5,                   # [Verified — measured] uniform black border around the panel
    shape="square",                 # [Verified]
    # COLOUR
    color="rgb888",                 # [Verified] full 24-bit RGB raster, no palette
    max_colors_still=0,             # [Verified] unlimited — true-colour 3 B/px, no cap
    max_colors_anim=0,              # [Verified] same path, no palette cap
    fixed_palette_stream=False,     # [Verified] no palette/bpp to desync (raw RGB)
    # [Verified — operator-matched white vs a Pixoo16 driven live through the untether_spp Wyze
    # bridge, both @100%]: blue cut 15% warms the iDotMatrix's cool/blue white to the Pixoo's.
    # white_mix stays 0 (panel reads matte/dull already — desaturating worsens it). gamma not
    # isolated. PHYSICAL limits, NOT colour-correctable: the iDotMatrix is intrinsically DIMMER
    # at 100% and has a MATTE finish vs the Pixoo's bright glossy diffuser -> run it at max
    # brightness; treat it as the dimmer detail/hero panel, not a brightness-match to the Pixoo.
    gamma=1.0, color_gain=(1.0, 1.0, 0.85), white_mix=0.0,
    # MEASURED LIMITS  [Verified — fps sweep on bench unit, fa03 done-ACK rate = true fps]
    # raw: flat-out sustained=3.2 fps (acks/s); paced 2fps=12/12, 3fps=18/18 (100%), 4fps=~14/24,
    # 5fps=15/30 (drops). Latency send->render-ACK ~256-277ms. The driver's in-flight guard
    # DROPS frames above the ceiling (link survives), so over_limit is a clean "drop".
    max_fps=3.2, safe_fps=2.5,      # [Verified] latency-bound (~260ms/frame); a detail/hero panel, not motion
    frame_bytes=3088,               # [Verified] 32*32*3 + 16B header, measured on the wire
    over_limit_mode="drop",         # [Verified] excess frames dropped by the in-flight guard; no garble/linkdrop
    push_latency_ms=260.0,          # [Verified] send -> done-ACK (device ACKs when the still renders)
    anim_buffer_frames=40,          # [Verified] 40-frame / 65 KB GIF uploaded + looped (tested min, not the ceiling)
    # RELIABILITY
    single_bond=True,               # [Verified] one BLE central; vendor app must be off the link
    handshake_each_connect=False,   # [Verified] plain GATT connect; no app-layer handshake needed for control
    advertises_when_idle=True,      # [Verified] advertises IDM-* as soon as the link is free (re-scan finds it)
    # CAPS — only Verified-on-this-device. STILL=image renders; BRIGHTNESS=dims live;
    # SCREEN_POWER=blank/wake by eye; CLOCK=face renders; ANIM_UPLOAD=GIF loops autonomously
    # (single + 16-packet multi); TEXT_NATIVE=device scrolls rasterized 8x11 glyphs natively
    # (dataType 3). PARTIAL_UPDATE tested-NEGATIVE (draw_pixel=separate DIY canvas) -> out.
    caps=frozenset({Caps.STILL, Caps.BRIGHTNESS, Caps.SCREEN_POWER, Caps.CLOCK,
                    Caps.ANIM_UPLOAD, Caps.TEXT_NATIVE}),
    extras={
        "transport": "ble-gatt", "service": "00fa", "write_char": "fa02", "notify_char": "fa03",
        "ack_format": "[len,0,cmd,sub,status]; status 3=done/ok",
        "still": "image_rgb -> 16B header [len,2,0,opt,totalLen(4LE),CRC32(4LE),timeSign(2),idx=12] + RGB; "
                 "split into <=244B writes (device drops >256B writes despite 512 MTU)",
        "safe_write_len": IDM.SAFE_WRITE_LEN,
        "brightness_opcode": "04/0x80", "screen_power_opcode": "07/01 (Verified blank/wake)",
        "clock_opcode": "06/01",
        "anim_upload": "VERIFIED = the app's 'Download to panel'. Encode frames -> a standard GIF "
                       "(32x32, loop=0) -> same chunked ACK-gated transport as the still but "
                       "dataType byte[2]=1 (GIF). ACKs: [05,00,01,00,01]=send-next-4K, "
                       "[..,03]=done. Device's on-board GIF decoder loops it with NO live link. "
                       "Tested: 8-frame/842B (1 packet) + 40-frame/65KB (16 packets) both loop.",
        "text_native": "VERIFIED = the app's Text feature. dataType byte[2]=3; payload = "
                       "[count][6B hdr 000101000001][global fg(3) bg(3)][pad] then per char "
                       "[02][fg(3)][bg(3)][11-byte bitmap][00 00]. Bitmap = 11 rows x 8 cols, "
                       "LSB=leftmost column (mirror-decoded). Device scrolls it natively (no frames).",
        "diy_pixel": "draw_pixel 05/01 [opt,r,g,b,col,row] RGB — Verified on the DIY canvas only "
                     "(enter_diy 04/01 first); separate mode from an uploaded still",
        "PARTIAL_UPDATE": "TESTED-NEGATIVE (Verified not-supported): draw_pixel switches to a "
                          "separate BLACK DIY canvas — does NOT composite over an uploaded still, "
                          "so no cheap still sub-rect update. Stays OUT of caps. (Also: rapid "
                          "unpaced draw_pixel writes shed pixels -> update_region paces them.)",
        "STATUS_READ": "TESTED-NEGATIVE (Verified not-supported): bare GETs (getLedType 04000180, "
                       "screenlight 05000f80ff) are SILENT; other cmds only echo-ACK. The only data "
                       "reply is the time-sync reply '09000180 04 0f 01 03 00' = static deviceType "
                       "(03=32x32) — brightness-diff (85 vs 0x11) did NOT change it, so no readable "
                       "brightness/temp/state. Out of caps. (fa03 ACK stream still gives link "
                       "liveness; firmware version is on the JieLi RCSP channel, not here.)",
        # No remaining pending caps. AUDIO/MIC/SENSORS/BUTTONS/HI_REFRESH: not applicable to this model.
        "colour_correction": "DONE: white matched live vs a Pixoo16 (driven through the untether_spp "
                             "Wyze bridge) -> blue gain 0.85. Residual dimmer+matte vs Pixoo is physical.",
    },
)


class IDotMatrix32Panel(PanelDriver):
    def __init__(self, spec, mac, name="", **kw):
        self.spec, self.mac, self.name = spec, mac, name or "idotmatrix32"
        self._link: _BleLink | None = None
        self.last_error = ""

    def connect(self) -> bool:
        try:
            link = _BleLink()
            link.connect(self.mac)
            if not link.connected:
                self.last_error = "not connected after connect()"
                return False
            self._link = link
            try:
                self.set_brightness(85)
            except Exception:
                pass
            return True
        except Exception as e:
            self._link = None
            self.last_error = "%s %s %s" % (type(e).__name__, getattr(e, "errno", ""), str(e)[:60])
            return False

    def disconnect(self) -> None:
        if self._link is not None:
            self._link.disconnect()
        self._link = None

    @property
    def connected(self) -> bool:
        return self._link is not None and self._link.connected

    # ---- hot path ----
    def push_frame(self, img) -> None:
        packet = encode_still(img, self.spec)
        chunks = IDM.inner_writes(packet)        # <=244B writes (device caps at ~256B)
        self._link.write_chunks_ff(chunks)       # fire-and-forget, non-blocking

    def set_brightness(self, level: int) -> None:
        self._link.write(IDM.set_brightness(max(0, min(100, int(level)))))

    # ---- capability-gated (all Verified on-device) ----
    def _frames_to_gif(self, frames, fps: float) -> bytes:
        """Colour-correct + encode frames as a standard 32x32 GIF (loop=0, disposal=2)."""
        import io
        imgs = []
        for f in frames:
            f = f.convert("RGB")
            if f.size != (self.spec.width, self.spec.height):
                f = f.resize((self.spec.width, self.spec.height))
            imgs.append(Image.frombytes("RGB", f.size, _correct_rgb(f, self.spec)))
        buf = io.BytesIO()
        imgs[0].save(buf, format="GIF", save_all=True, append_images=imgs[1:],
                     duration=max(20, int(1000 / max(1.0, fps))), loop=0, disposal=2)
        return buf.getvalue()

    def store_and_loop(self, frames, fps: float = 12.0, slot: int = 0, dwell: int = 3600) -> int:
        """Caps.ANIM_UPLOAD — store the frames as a GIF in carousel SLOT and start the
        on-device cycle so it LOOPS autonomously (survives disconnect, no live link).

        THIS is the real animated-loop path. (upload_animation() writes image_index=12, the
        show-now/transient buffer, which only displays the FIRST FRAME — not a loop.) Sequence
        verified from the app + send_to_panel.py: slot-setup count=1 -> GIF chunked-upload to
        the slot (image_index=slot, time_sign=dwell) -> enter_asset_view starts playback."""
        gif = self._frames_to_gif(frames, fps)
        self._link.write(IDM.frame(2, 1, 1, slot))          # slot-setup: count=1, this slot
        time.sleep(0.3)
        up = IDM.ImageUpload(gif, IDM.DataType.GIF, image_index=slot, time_sign=dwell)
        ok, info = self._link.upload_acked(up.outer_packets())
        if not ok:
            raise RuntimeError(f"store_and_loop failed ({len(gif)}B gif): {info}")
        self._link.write(IDM.enter_asset_view())            # start the on-device loop
        time.sleep(1.0)                                     # let the loop ENGAGE before the
        #   caller disconnects (send_to_panel.py does the same) — else it can play once and
        #   freeze on the last frame instead of looping.
        return len(gif)

    def upload_animation(self, frames, fps: float = 10.0) -> int:
        """Show-now (image_index=12): displays the GIF's FIRST FRAME transiently — does NOT
        loop on-device. Kept for a one-shot still; use store_and_loop() for an animated loop."""
        gif = self._frames_to_gif(frames, fps)
        ok, info = self._link.upload_acked(IDM.ImageUpload(gif, IDM.DataType.GIF).outer_packets())
        if not ok:
            raise RuntimeError(f"animation upload failed ({len(gif)}B gif): {info}")
        return len(gif)

    def scroll_text(self, text: str, color=(255, 255, 255), speed: float = 1.0) -> int:
        """Caps.TEXT_NATIVE — device-side scrolling marquee. Rasterizes `text` to 8x11 glyph
        bitmaps and uploads the dataType-3 payload; the device scrolls it natively (no frames).
        Returns the payload byte size."""
        payload = text_payload(text, fg=tuple(color), bg=(0, 0, 0))
        packets = IDM.ImageUpload(payload, IDM.DataType.TEXT).outer_packets()
        ok, info = self._link.upload_acked(packets)
        if not ok:
            raise RuntimeError(f"scroll_text upload failed ({len(payload)}B): {info}")
        return len(payload)

    def screen_power(self, on: bool) -> None:                 # Caps.SCREEN_POWER (Verified blank/wake)
        self._link.write(IDM.set_screen(bool(on)))

    def set_clock(self, face: int = 0, color=(255, 255, 255)) -> None:  # Caps.CLOCK
        r, g, b = color
        self._link.write(IDM.set_clock(face, r=r, g=g, b=b))

    def update_region(self, x: int, y: int, img, enter_diy: bool = True, pace: float = 0.012) -> None:
        """NOT a Caps.PARTIAL_UPDATE — draws on the DIY *canvas* (a separate mode).

        TESTED on-device: draw_pixel switches the panel to a blank/black DIY canvas; it does
        NOT composite over an uploaded still, so it can't do a cheap still sub-rect update.
        Kept only for building scenes entirely on the DIY canvas. `pace` (~12ms/pixel) is
        REQUIRED — rapid unpaced writes get shed by the device (ragged output).
        """
        if enter_diy:
            self._link.write(IDM.enter_diy(int(IDM.DiyFun.ENTER_NOCLEAR)))
            time.sleep(0.05)
        for j in range(img.height):
            for i in range(img.width):
                r, g, b = img.getpixel((i, j))[:3]
                self._link.write(IDM.draw_pixel(r, g, b, x + i, y + j))
                if pace:
                    time.sleep(pace)


register_driver(IDOTMATRIX32_SPEC, IDotMatrix32Panel)
