# Brazil World Cup pack (64x64 iDotMatrix)

12 looping, panel-safe GIFs celebrating Brazil — the 5-time world champions. Every asset is 64x64,
RGB, <=16 flat colours per frame (no gradients/dithering), with a 50 ms frame floor, built by the
project's `assetlib` helper so the panel's GIF decoder plays every frame.

Rebuild everything (GIFs + a `*_preview.png` per GIF + `_montage.png` contact sheet):

```
python3 gen_brazil.py
```

Do NOT push these with an active Bluetooth connection while other tools are talking to the panel;
drive them via the normal carousel/push tooling. This generator only writes files.

## Pack A — Flags & Fan decor

| GIF | Shows | Frames | Size | Dwell |
|-----|-------|-------:|-----:|------:|
| `br_flag_wave.gif`     | Brazilian flag (green field, yellow diamond, blue globe + white band + stars) rippling in a cloth wave | 12 | 4.7 KB | 10 s |
| `br_brasil_scroll.gif` | Bold yellow **BRASIL** wordmark scrolling over a blue field with sweeping green stripes | 40 | 21.7 KB | 12 s |
| `br_stars5.gif`        | The 5 championship stars appearing one-by-one, then twinkling gold/white over a green field | 30 | 9.5 KB | 10 s |
| `br_confetti.gif`      | Samba-colour confetti (green/yellow/blue/white/gold) raining down a black sky | 30 | 10.8 KB | 8 s |
| `br_samba_wave.gif`    | Lively diagonal green/yellow/blue chevron wave with white sparkles — pure colour/refresh decor | 18 | 8.9 KB | 8 s |

## Pack B — Goals & Ball action

| GIF | Shows | Frames | Size | Dwell |
|-----|-------|-------:|-----:|------:|
| `br_ball_roll.gif`     | Flat pixel-art soccer ball rolling across a green pitch with a moving shadow, spinning as it goes | 28 | 7.7 KB | 8 s |
| `br_goal_freekick.gif` | Roberto-Carlos-style banana free-kick: ball bends past a defensive wall into the top corner, net ripples on impact | 34 | 16.7 KB | 12 s |
| `br_gooool.gif`        | **GOOOL!** celebration — text punches in over spinning green/yellow rays | 22 | 16.7 KB | 8 s |
| `br_striker_kick.gif`  | Striker silhouette winding up and striking; the ball rockets off the boot with a trail | 20 | 6.7 KB | 8 s |

## Pack C — Trophies & Glory

| GIF | Shows | Frames | Size | Dwell |
|-----|-------|-------:|-----:|------:|
| `br_trophy.gif`        | The gold World Cup trophy with a white glint sweeping diagonally across it | 18 | 6.8 KB | 10 s |
| `br_trophy_raise.gif`  | Trophy rising from its base while golden rays-of-glory spin behind it | 26 | 17.5 KB | 12 s |
| `br_campeoes.gif`      | **CAMPEOES** flourish with the 5 championship stars twinkling above a gold rule | 24 | 11.5 KB | 12 s |

Total: 12 GIFs, ~139 KB. None exceeds the 200 KB ceiling (largest is `br_brasil_scroll` at 21.7 KB).

## Recommended 12-slot carousel

A balanced flag -> action -> glory rhythm that ends on the trophy:

| Slot | GIF | Dwell |
|-----:|-----|------:|
| 1  | `br_flag_wave`     | 10 s |
| 2  | `br_brasil_scroll` | 12 s |
| 3  | `br_stars5`        | 10 s |
| 4  | `br_samba_wave`    |  8 s |
| 5  | `br_ball_roll`     |  8 s |
| 6  | `br_striker_kick`  |  8 s |
| 7  | `br_goal_freekick` | 12 s |
| 8  | `br_gooool`        |  8 s |
| 9  | `br_confetti`      |  8 s |
| 10 | `br_trophy`        | 10 s |
| 11 | `br_trophy_raise`  | 12 s |
| 12 | `br_campeoes`      | 12 s |

Best-of shortlist (if you only want a handful): `br_flag_wave`, `br_goal_freekick`, `br_gooool`,
`br_trophy_raise`, `br_campeoes`.
