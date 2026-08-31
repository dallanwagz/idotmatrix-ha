#!/usr/bin/env python3
"""
panel_api — the pluggable panel contract for the multi-box installation.

Goal: adding a 5th/6th/7th panel of a NEW model = drop in one PanelDriver subclass + a
filled PanelSpec, add one line to the layout. The orchestrator (pinball.py) and the
animations (celebration/wave/chant) depend ONLY on this contract, never on a model's
quirks. Mixed models are first-class: each panel is driven to its OWN capability, not
rounded down to a least-common-denominator.

Two things an RE agent delivers per new model (see PANEL_RE_SPEC.md):
  1. a PanelDriver subclass (connect / push_frame / set_brightness + any cap methods)
  2. a PanelSpec (geometry + color + MEASURED hardware limits + capabilities)

Design split:
  PanelSpec   = intrinsic to the MODEL  (same for every unit of that model)
  layout entry= per-INSTALL placement   (name, mac, x0/y0 mm)  -> see build_panel()
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# CAPABILITIES — what a panel can do beyond the mandatory baseline.
# The orchestrator checks these to use a panel to its strength (see the
# cap->exploitation table in PANEL_RE_SPEC.md). Tag each in the spec as
# Verified (tested live) / Inferred (from decompile) / Unknown.
# ---------------------------------------------------------------------------
class Caps:
    STILL          = "still"           # push a full native-res still  (MANDATORY — baseline)
    BRIGHTNESS     = "brightness"      # set_brightness(0..100)
    ANIM_UPLOAD    = "anim_upload"     # store+loop a clip on-device (offloads the live link)
    PARTIAL_UPDATE = "partial_update"  # update a sub-rectangle cheaply (sparkles w/o full repush)
    TEXT_NATIVE    = "text_native"     # device-side scrolling-text engine (crisp marquees)
    CLOCK          = "clock"           # built-in clock faces / scenes
    SCREEN_POWER   = "screen_power"    # blank/wake the panel (blackout & snap-back effects)
    AUDIO          = "audio"           # speaker (chant / goal-horn / SFX)
    MIC            = "mic"             # microphone -> sound-reactive input
    SENSORS        = "sensors"         # temp / light / etc. the orchestrator can read
    BUTTONS        = "buttons"         # physical input the orchestrator can read
    HI_REFRESH     = "hi_refresh"      # notably higher safe_fps than the fleet baseline
    STATUS_READ    = "status_read"     # device answers GET_* queries (brightness/temp/...)


@dataclass(frozen=True)
class PanelSpec:
    """Everything I need to know to drive a model well. The RE agent fills this."""
    # --- identity ---
    model: str                         # "pixoo16", "timebox-mini", "ditoo", ...
    family: str                        # transport/framing family, for shared driver code

    # --- geometry (physical; feeds the world<->panel projection) ---
    width: int                         # native pixels
    height: int
    pitch_mm: float                    # LED pitch -> physical scale ("magnifying glass")
    bezel_mm: float = 0.0              # display inset inside the housing (gap between panels)
    shape: str = "square"             # "square" | "rect" | "round" | "segmented"

    # --- colour / encoding ---
    color: str = "rgb888"             # "rgb888" | "rgb444" | "palette"
    max_colors_still: int = 0          # per-still colour cap; 0 = effectively unlimited
    max_colors_anim: int = 0           # streamed/anim colour cap (0 = same as still)
    fixed_palette_stream: bool = False # MUST hold one palette/bpp across a stream or it desyncs
    gamma: float = 1.0                 # brightness curve vs sRGB (for cross-panel match)
    color_gain: tuple = (1.0, 1.0, 1.0)# per-channel gain to match the fleet
    white_mix: float = 0.0             # 0..1 desaturation to tame an over-vivid panel

    # --- MEASURED hardware limits (the framerate/limit tests) ---
    max_fps: float = 0.0               # top sustained full-frame rate before degradation
    safe_fps: float = 0.0              # the rate to actually drive at (with headroom)
    frame_bytes: int = 0               # wire size of one full-frame still
    over_limit_mode: str = ""         # "drop" | "garble" | "linkdrop107" | "queue"
    push_latency_ms: float = 0.0       # send() -> on-screen, for cross-panel sync
    anim_buffer_frames: int = 0        # device-side clip capacity (if ANIM_UPLOAD)

    # --- reliability ---
    single_bond: bool = True           # one host at a time?
    handshake_each_connect: bool = False
    advertises_when_idle: bool = True  # shows up in inquiry scans, or only direct-page?

    # --- capabilities ---
    caps: frozenset = frozenset({Caps.STILL})
    extras: dict = field(default_factory=dict)  # cap-specific params / opcodes / channels

    def supports(self, cap: str) -> bool:
        return cap in self.caps


class NotSupported(NotImplementedError):
    """Raised by a cap-gated method the model doesn't implement. Check spec.supports() first."""


# ---------------------------------------------------------------------------
# DRIVER — the behavioural contract the orchestrator calls.
# ---------------------------------------------------------------------------
class PanelDriver(ABC):
    spec: PanelSpec

    # ---- lifecycle (the orchestrator owns the retry loop; keep these cheap) ----
    @abstractmethod
    def connect(self) -> bool:
        """Page + open transport + any required handshake. Return True on a live link.
        Must not raise on a normal failure (return False); the manager retries."""

    @abstractmethod
    def disconnect(self) -> None: ...

    @property
    @abstractmethod
    def connected(self) -> bool: ...

    # ---- THE HOT PATH (mandatory) ----
    @abstractmethod
    def push_frame(self, img) -> None:
        """Encode `img` (a PIL RGB image of exactly spec.width x spec.height) into this
        model's wire format and transmit ONE frame, FIRE-AND-FORGET. Must not block
        longer than one frame. The driver applies its OWN colour correction
        (spec.gamma/color_gain/white_mix) so the orchestrator renders in true colour and
        every panel matches. Honour spec.fixed_palette_stream between begin/end_stream."""

    def begin_stream(self, palette=None) -> None:
        """Called once when a streamed animation with a known palette starts. Drivers
        that need a fixed palette/bpp across the stream pin it here. Default: no-op."""

    def end_stream(self) -> None:
        """Streamed animation finished; release any pinned palette. Default: no-op."""

    @abstractmethod
    def set_brightness(self, level: int) -> None:
        """0..100."""

    # ---- capability-gated (ONLY call if spec.supports(<cap>)) -------------------
    def upload_animation(self, frames, fps: float) -> None:
        """Caps.ANIM_UPLOAD — store a clip on-device; it loops without further BT."""
        raise NotSupported

    def scroll_text(self, text: str, color=(255, 255, 255), speed: float = 1.0) -> None:
        """Caps.TEXT_NATIVE — crisp device-side marquee."""
        raise NotSupported

    def set_clock(self, face: int = 0, color=(255, 255, 255)) -> None:
        """Caps.CLOCK."""
        raise NotSupported

    def screen_power(self, on: bool) -> None:
        """Caps.SCREEN_POWER — blank/wake for blackout effects."""
        raise NotSupported

    def play_sound(self, sound) -> None:
        """Caps.AUDIO — chant / goal-horn / SFX."""
        raise NotSupported

    def update_region(self, x: int, y: int, img) -> None:
        """Caps.PARTIAL_UPDATE — cheap localized update."""
        raise NotSupported

    def read_status(self) -> dict:
        """Caps.STATUS_READ / SENSORS — {'brightness':.., 'temp_c':.., 'buttons':..}."""
        return {}


# ---------------------------------------------------------------------------
# REGISTRY + factory — how a new model is wired in.
# ---------------------------------------------------------------------------
DRIVERS: dict[str, type[PanelDriver]] = {}          # model -> driver class
SPECS:   dict[str, PanelSpec] = {}                  # model -> spec


def register_driver(spec: PanelSpec, driver_cls: type[PanelDriver]) -> None:
    """A new model's module calls this at import to make itself available."""
    SPECS[spec.model] = spec
    DRIVERS[spec.model] = driver_cls


def build_panel(model: str, mac: str, x0_mm: float, y0_mm: float, name: str = "", **kw):
    """Construct a placed, ready-to-connect panel from a layout entry."""
    spec, cls = SPECS[model], DRIVERS[model]
    drv = cls(spec=spec, mac=mac, name=name or model, x0=x0_mm, y0=y0_mm, **kw)
    return drv
