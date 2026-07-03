# World Cup team switcher — iDotMatrix panels

Switch every configured panel to whoever's playing, one command:
```bash
python3 set_team.py brazil
python3 set_team.py usa
```
Each team's carousel = its **flag** + the **shared spinning ball** (only the background colour
changes per team) + its **wordmark**. Panels are addressed by CoreBluetooth UUID on macOS and by
MAC on Linux/Pi (auto-detected). Self-contained (bleak only) — assets are the `*.gif` here.

## Panel sizes (32 and 64)

Each panel in `set_team.py`'s `PANELS` list has a `size` (default `32`). The switcher pushes the
**size-matched** asset to each panel automatically:
- a **32×32** panel gets `<base>.gif` (e.g. `ball_brazil.gif`),
- a **64×64** panel gets `<base>_64.gif` (e.g. `ball_brazil_64.gif`).

So the two 32 panels and a brother's 64 panel can all run the same `set_team.py usa` and each
renders at its native resolution. To add the 64 panel, uncomment the example entry in `PANELS`
and fill in its MAC (Pi/Linux) or CoreBluetooth UUID (macOS).

**Regenerate the assets** at any size with:
```bash
python3 gen_worldcup.py 32   # -> flag_brazil.gif, ball_brazil.gif, text_brazil.gif, ...
python3 gen_worldcup.py 64   # -> *_64.gif variants
```
The ball is a realistic rolling adidas Trionda sphere (per-team background); flags and wordmarks
scale with the panel. `gen_ball.py` is the older 32-only ball generator (kept for reference).

**Add a team:** run `gen_worldcup.py` after adding the team's colours/flag, or drop
`flag_<team>{_64}.gif`, `ball_<team>{_64}.gif`, `text_<team>{_64}.gif` here and add a `TEAMS`
entry (base names, no `.gif`) in `set_team.py`.
