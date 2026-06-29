# Brazil futebol pack — push to iDotMatrix panels (Pi-ready)

Self-contained: `idm_push.py` (bleak only, no driver) + the GIFs. Drop this folder on the Pi.

## Push the rotating carousel to both panels
```bash
for MAC in 6F:5D:FE:85:89:31 1F:D6:5C:D2:8F:7F; do
  IDM_ADDR=$MAC python3 idm_push.py flag.gif:10 ball.gif:8 brasil.gif:8
done
```
`idm_push.py` wipes all 12 slots, loads the GIFs (each `file:dwell_seconds`), and starts the panel
cycling autonomously — survives disconnect. Up to 12 items.

## Variations
- **One flag across both panels:** `flag_L.gif` on 858931, `flag_R.gif` on D28F7F (dwell 300).
- **GOL! flash:** push `gol.gif:8` to both when Brazil scores, then re-push the carousel.

Panels: **IDM-858931 = `6F:5D:FE:85:89:31`**, **IDM-D28F7F = `1F:D6:5C:D2:8F:7F`** (32x32).
Single BLE central per panel. Never enable the device password. See manifest.json for everything.
