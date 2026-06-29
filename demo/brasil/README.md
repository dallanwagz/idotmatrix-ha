# Brazil futebol animations (32×32 iDotMatrix)

Solid-colour, panel-safe 🇧🇷 animations. Regenerate: `python generate.py`.

| file | use |
|---|---|
| `flag_L.gif` + `flag_R.gif` | one big bandeira **split across both panels** (left/right halves) |
| `flag.gif` | single complete bandeira (same on each panel) |
| `ball.gif` | bouncing soccer ball on the pitch |
| `brasil.gif` | "BRASIL" scrolling, yellow on blue |
| `gol.gif` | "GOL!" flash — for celebrations |

Push (panel MACs): `IDM_ADDR=6F:5D:FE:85:89:31` (858931) / `1F:D6:5C:D2:8F:7F` (D28F7F)
```
IDM_ADDR=<MAC> ~/.esphome-venv/bin/python ../../tools/etoys_catalog/send_to_panel.py demo/brasil/<file>
```
