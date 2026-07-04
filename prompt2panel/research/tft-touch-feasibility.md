# Driving a 2.4" ILI9341 + XPT2046 SPI TFT from a Raspberry Pi 3B+/4 — feasibility & how-to

> Research report (2026). For the stretch-goal on-Pi dashboard. Verified against current library
> status and Pi OS. Sources at the bottom.

## TL;DR
**Feasible, and it will not touch Bluetooth** (SPI display vs UART-attached BT radio — independent).
Recommended for a headless Python status/preview app: **userspace over spidev —
`adafruit-circuitpython-rgb-display` (v3.14.6, 2026-06-02, maintained) for the ILI9341 + Pillow for
drawing + `xpt2046-circuitpython` for touch**, both on SPI0 with separate chip-selects
(CE0 = display, CE1 = touch). Just `dtparam=spi=on` + a pip venv — no device-tree overlays, no
framebuffer, no desktop. Kernel route (`mipi-dbi-spi` DRM + `ads7846` touch) is the alternative if
you ever want a real Linux display device; a nice **hybrid** is userspace display + kernel `ads7846`
touch (clean `/dev/input` events) on CE1.

## Wiring (SPI0, shared bus, two chip-selects)
Display on CE0, touch on CE1; SCK/MOSI shared. Identical on 3B+ and Pi 4.

| Module pin | Function | BCM | Phys | Notes |
|---|---|---|---|---|
| VCC | Power | — | 1/17 (3.3V) | 3.3V safest (check board's J1 jumper for 5V) |
| GND | Ground | — | 6/9/14 | |
| SCK | SPI clock | GPIO11 | 23 | shared w/ T_CLK |
| SDI/MOSI | to display | GPIO10 | 19 | shared w/ T_DIN |
| SDO/MISO | from display | GPIO9 | 21 | **leave display SDO unwired** (MISO contention) |
| CS | display CS | GPIO8 (CE0) | 24 | /dev/spidev0.0 |
| DC/RS | data/command | GPIO25 | 22 | any free GPIO |
| RESET | reset | GPIO24 | 18 | any free GPIO |
| LED | backlight | GPIO18 | 12 | PWM-dimmable, or tie 3.3V |
| T_DO | touch MISO | GPIO9 | 21 | **must** be wired (touch reads back) |
| T_CS | touch CS | GPIO7 (CE1) | 26 | /dev/spidev0.1 |
| T_IRQ | pen-down | GPIO17 | 11 | optional for polling; required for kernel ads7846 |

Gotchas: cheap boards don't tri-state display SDO → wire only T_DO to MISO; 3.3V logic; backlight
usually transistor-driven (safe from GPIO); keep wires <15 cm past ~24 MHz.

## Software approaches
- **(a) Userspace Python (recommended):** `adafruit-circuitpython-rgb-display` (ILI9341, Pillow
  `display.image(pil)`), `xpt2046-circuitpython` for touch (`is_pressed()`/`get_coordinates()`),
  both sharing the Blinka SPI bus. Zero kernel coupling, survives OS upgrades, no desktop — exactly a
  status app. `luma.lcd` also supports ILI9341 but has no touch story.
- **(b) Kernel framebuffer/DRM:** `fbtft` overlay still ships but is **deprecated**; modern
  replacement is `dtoverlay=mipi-dbi-spi` (mainline `panel-mipi-dbi` DRM, needs a small init-blob in
  /lib/firmware). Touch via `dtoverlay=ads7846,cs=1,penirq=17` → standard `/dev/input/event*`. More
  moving parts; right only if you want the panel to be "a Linux display."
- **Hybrid:** userspace display + kernel `ads7846` touch on CE1 (`ads7846` claims only spidev0.1).

## Touch & calibration
XPT2046 is an SPI ADC (12-bit, 0–4095, ≤~2.5 MHz). Resistive → needs calibration: 2-point
(tap two opposite corners, record raw, linear-map to pixels, persist 4 numbers, handle axis
swap/invert), average 3–5 samples to de-jitter. Kernel route uses `xmin/xmax/…/swapxy` overlay params
or `tslib`.

## Performance
Full 240×320@16bpp = 1.23 Mbit; ~20 fps real at 32 MHz SPI. Userspace full-frame: **~8–15 fps Pi 4,
~5–10 fps 3B+** (Pillow→RGB565 conversion dominates). **Small GIF thumbnails / partial (windowed)
updates hit 15–25 fps.** A tappable file-browser UI is easily feasible on either Pi (static redraw
<150 ms). Set display `baudrate=24_000_000` (try 32 MHz with short wires); keep touch ≤2 MHz. On 3B+
pin `core_freq=250` if you see speed-dependent glitching. Ignore `fbcp-ili9341` (needs dead pre-KMS
stack).

## Coexistence with Bluetooth (confirmed independent)
Onboard BT hangs off the internal PL011 UART (hciuart), not the 40-pin header. SPI0 uses GPIO7–11;
DC/RESET/LED/IRQ use GPIO17/18/24/25 — zero overlap with UART/BT/I²C. Headless approach (a) needs no
display server. Only indirect coupling is CPU (GIF re-encode = 1 core). EMI a non-issue with <15 cm
wires.

## Proof-of-concept (recommended)
Libs (pip, venv): `adafruit-circuitpython-rgb-display==3.14.6`, `adafruit-blinka`, `pillow`,
`xpt2046-circuitpython`. Prereq: `dtparam=spi=on`.
```python
import time, board, busio, digitalio
from PIL import Image
from adafruit_rgb_display import ili9341
import xpt2046
spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)
disp = ili9341.ILI9341(spi, cs=digitalio.DigitalInOut(board.CE0),
    dc=digitalio.DigitalInOut(board.D25), rst=digitalio.DigitalInOut(board.D24),
    baudrate=24_000_000, rotation=0)
bl = digitalio.DigitalInOut(board.D18); bl.switch_to_output(value=True)
disp.image(Image.open("test.png").convert("RGB").resize((240, 320)))
touch = xpt2046.Touch(spi, cs=digitalio.DigitalInOut(board.CE1),
    interrupt=digitalio.DigitalInOut(board.D17))
X0,X1,Y0,Y1 = 200,3900,200,3900
while True:
    if touch.is_pressed():
        raw = touch.get_coordinates()
        if raw:
            rx,ry = raw
            print("pixel", int((rx-X0)*240/(X1-X0)), int((ry-Y0)*320/(Y1-Y0)))
        time.sleep(0.05)
    time.sleep(0.01)
```

## Sources
Raspberry Pi firmware overlays README; notro/panel-mipi-dbi wiki; adafruit-circuitpython-rgb-display
(PyPI v3.14.6); luma.lcd (PyPI 2.13.0); humeman/xpt2046-circuitpython; ILI9341 refresh-rate forum
measurements; juj/fbcp-ili9341 analysis.
