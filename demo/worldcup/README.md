# World Cup team switcher — iDotMatrix panels

Switch BOTH 32×32 panels to whoever's playing, one command:
```bash
python3 set_team.py brazil
python3 set_team.py usa
```
Each team's carousel = its **flag** + the **shared spinning ball** (only the background colour
changes per team) + its **wordmark**. Panels are addressed by CoreBluetooth UUID on macOS and by
MAC on Linux/Pi (auto-detected). Self-contained (bleak only) — assets are the `*.gif` here.

**Add a team:** drop `flag_<team>.gif`, `ball_<team>.gif` (run `gen_ball.py` with its bg colour),
`text_<team>.gif` here, and add a `TEAMS` entry in `set_team.py`.
