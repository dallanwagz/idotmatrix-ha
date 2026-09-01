# iDotMatrix — Home Assistant integration

Cloud-free, app-free control of the **iDotMatrix HXS-002 / NL-XSD-32** 32×32 BLE LED
panel from Home Assistant — reverse-engineered from the vendor Android app and
**validated on real hardware**. No vendor app or cloud required.

> This repo holds just the HA integration. The BLE protocol RE, standalone driver
> library, the REST/CLI/daily-use control apps, the content-generation pipeline, and
> the asset library all live in the companion repo,
> [**`ledpanels`**](https://github.com/dallanwagz/ledpanels) — start there for anything beyond
> Home Assistant, including the full protocol reference
> ([`docs/PROTOCOL.md`](https://github.com/dallanwagz/ledpanels/blob/main/docs/PROTOCOL.md))
> and the RE methodology/security writeups.

## What's here

| Path | What |
|---|---|
| `custom_components/idotmatrix/` | The HA integration (HACS-installable; Core-PR-shaped). `protocol.py` is a **pure, dependency-free, unit-tested** BLE protocol module — periodically synced from `ledpanels`'s canonical copy at `driver/idm_protocol.py`, kept as its own vendored copy so the HACS install has no external repo dependency. |
| `tests/test_protocol.py` | 30 golden-frame tests, anchored to hardware captures. |
| `hacs.json` | HACS manifest. |

## Quick start

Install via HACS as a custom repository, then add the device through the UI (it's
auto-discovered over Bluetooth as `IDM-*`). Requires a Bluetooth adapter or an
ESPHome/Shelly Bluetooth proxy near the panel.

```bash
python3 -m pytest tests/
```

## What works (validated on hardware)

Power on/off, brightness, fullscreen RGB, clock (date + 24h flags), countdown,
stopwatch, scoreboard, 180° flip, screen on/off, live DIY pixel drawing, and a
32×32 image upload (RGB raster, chunked + CRC32) via `idotmatrix.set_image`. The
integration exposes a **light** (on/off + brightness + colour), a **Flip** switch,
**Sync time** / **Reset** buttons, a **Clock face** select, and a generic
`idotmatrix.send_command` service for everything else. See
[`ledpanels`'s protocol reference](https://github.com/dallanwagz/ledpanels/blob/main/docs/PROTOCOL.md)
for the full command catalog, including carousel/GIF storage and rhythm/spectrum modes
this integration doesn't yet expose as HA entities.

The panel accepts **one** BLE connection at a time — keep the vendor app (and any
script from the `ledpanels` repo) disconnected while this integration controls it; it holds
a persistent connection and will fight anything else trying to connect at the same time.

## Security note

The QR code on the box offers a "local server" APK from `api.e-toys.cn`. It's the same
version as the Play Store build but **DEX-packed (Baidu Protect) and requests extra
permissions** (self-install, read-phone-state, boot, get-tasks). **Use the Play Store
build.** Full analysis:
[`ledpanels`'s `docs/SECURITY-APK-COMPARISON.md`](https://github.com/dallanwagz/ledpanels/blob/main/docs/SECURITY-APK-COMPARISON.md).

## Credits

Cross-checked against [`derkalle4/python-idotmatrix-library`](https://github.com/derkalle4/python3-idotmatrix-library)
and [`8none1/idotmatrix`](https://github.com/8none1/idotmatrix).
