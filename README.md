# iDotMatrix — local control & Home Assistant integration

Cloud-free, app-free control of the **iDotMatrix HXS-002 / NL-XSD-32** 32×32 BLE LED
panel — reverse-engineered from the vendor Android app and **validated on real
hardware**. Drive it from any Python/Bluetooth host or from Home Assistant, no vendor
app or cloud required.

> Reverse-engineered with the [`untether`](https://github.com/dallanwagz/untether)
> methodology. Protocol details in [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

## What's here

| Path | What |
|---|---|
| `custom_components/idotmatrix/` | The Home Assistant integration (HACS-installable; Core-PR-shaped). `protocol.py` is a **pure, dependency-free, unit-tested** protocol module. |
| `tools/idm_cli.py` | Standalone `bleak` CLI — scan/connect/drive the panel from any host. |
| `tools/idm_daemon.py` + `idmctl.py` | Persistent-connection driver for interactive use. |
| `tools/idm_image.py` | Chunked image-upload experiment (see protocol notes). |
| `tests/test_protocol.py` | 18 golden-frame tests, anchored to hardware captures. |
| `docs/PROTOCOL.md` | Full BLE protocol spec + golden frames. |
| `docs/SECURITY-APK-COMPARISON.md` | Play Store vs. e-toys.cn APK security analysis. |
| `decompiled/`, `apks/`, `captures/`, `research/` | RE working material (gitignored binaries where large). |

## Quick start (any host with Bluetooth)

```bash
python3 -m venv venv && ./venv/bin/pip install bleak
./venv/bin/python tools/idm_cli.py scan                 # find your IDM-xxxxxx
export IDM_ADDR=<address-from-scan>
./venv/bin/python tools/idm_cli.py color 255 0 0        # fill red
./venv/bin/python tools/idm_cli.py bright 50
./venv/bin/python tools/idm_cli.py clock 0
./venv/bin/python tools/idm_cli.py countdown 1 5 0      # start a 5:00 countdown
```

The panel accepts **one** BLE connection at a time — keep the vendor app disconnected
while controlling it locally. It reverts to its idle animation when the link drops, so
the HA integration holds a persistent connection.

## What works (validated on hardware)

Power on/off, brightness, fullscreen RGB, clock (date + 24h flags), countdown,
stopwatch, scoreboard, 180° flip, screen on/off, live DIY pixel drawing, and **full
32×32 image upload** (RGB raster, chunked + CRC32). See the
[command catalog](docs/PROTOCOL.md#command-catalog). The HA `idotmatrix.set_image`
service uploads any image file (auto-resized to 32×32).

## Home Assistant

Install via HACS as a custom repository, then add the device through the UI (it's
auto-discovered over Bluetooth as `IDM-*`). Requires a Bluetooth adapter or an
ESPHome/Shelly Bluetooth proxy near the panel. The integration exposes a **light**
(on/off + brightness + colour), a **Flip** switch, **Sync time** / **Reset** buttons, a
**Clock face** select, and a generic `idotmatrix.send_command` service for everything
else.

## Security note

The QR code on the box offers a "local server" APK from `api.e-toys.cn`. It's the same
version as the Play Store build but **DEX-packed (Baidu Protect) and requests extra
permissions** (self-install, read-phone-state, boot, get-tasks). **Use the Play Store
build.** Full analysis: [`docs/SECURITY-APK-COMPARISON.md`](docs/SECURITY-APK-COMPARISON.md).

## Credits

Cross-checked against [`derkalle4/python-idotmatrix-library`](https://github.com/derkalle4/python3-idotmatrix-library)
and [`8none1/idotmatrix`](https://github.com/8none1/idotmatrix).
