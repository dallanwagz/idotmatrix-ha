# Brazil GAME-DAY pack (`brazil_gameday`)

An extensive, full-colour, cinematic Brazil / futebol animation pack for the **64x64 iDotMatrix
RGB panel**. Built to loop **all match long** on a fan's panel during a live Brazil World Cup game
— rich, celebratory, varied. Twelve looping GIFs, all 64x64, all under 95 KB.

Regenerate everything (GIFs + per-file preview PNGs + `_montage.png`) with:

```bash
python3 gen_brazil_gameday.py
```

Files only — the generator never touches Bluetooth / hardware. Rendered through
`assetlib.save_gif(colors=…, dither=True)`, which the 64x64 decoder renders in full colour.

## Animations

| # | File | What it shows | Frames | Size |
|---|------|---------------|-------:|-----:|
| 1 | `brg_flag_wave.gif` | Waving Brazil flag, cloth folds + shaded sky, fills the frame | 44 | 92.4 KB |
| 2 | `brg_gooool.gif` | Ball rockets into the net, green/yellow explosion, flashing **GOOOL!** | 48 | 90.0 KB |
| 3 | `brg_bicycle_kick.gif` | Stadium overhead/bicycle kick, depth crowd, floodlit pitch, goal | 42 | 83.2 KB |
| 4 | `brg_freekick_banana.gif` | Banana free-kick curving past the wall into the top corner, motion trail | 46 | 88.7 KB |
| 5 | `brg_samba.gif` | Samba dancers + drummer silhouettes with glowing layered confetti | 42 | 84.2 KB |
| 6 | `brg_trophy.gif` | Gold World Cup trophy, sweeping specular glint + rotating light rays | 44 | 90.9 KB |
| 7 | `brg_penta.gif` | **PENTA** — five golden champion stars shining (Brazil = 5-time champs) | 44 | 87.8 KB |
| 8 | `brg_vai_brasil.gif` | **VAI BRASIL** scrolling boldly over animated green/yellow chevrons | 36 | 84.2 KB |
| 9 | `brg_tifo.gif` | Crowd tifo mosaic of cards flipping to reveal the flag | 42 | 90.3 KB |
| 10 | `brg_fireworks.gif` | Fireworks bursting over a floodlit stadium bowl | 52 | 92.1 KB |
| 11 | `brg_celebration.gif` | Striker wheeling away arms-out with a streaming flag + confetti | 44 | 91.3 KB |
| 12 | `brg_spin_ball.gif` | Spinning Brazil-colours football with glow | 40 | 84.6 KB |

All twelve are comfortably under the 95 KB ceiling (largest: `brg_flag_wave` at 92.4 KB). Total ~1.03 MB.
Frame times are ~55–70 ms (≈14–18 fps). Colours auto-tuned per file (48–128) to hold the size budget while
keeping gradients/shading — the 64x64 panel only resolves ~126 colours/frame, so these read as full colour.

## Recommended 12-slot carousel order (best-of first)

The panel carousel caps at 12 slots, so this whole pack fits exactly. Lead with the biggest crowd-pleasers:

1. `brg_gooool` — the goal moment, the loudest hit
2. `brg_flag_wave` — instantly reads "Brazil", great anchor
3. `brg_bicycle_kick` — showpiece action scene
4. `brg_trophy` — gold glory shot
5. `brg_penta` — five stars, the bragging rights
6. `brg_celebration` — player wheel-away, pure joy
7. `brg_fireworks` — full celebration energy
8. `brg_freekick_banana` — skill highlight
9. `brg_samba` — festive breather
10. `brg_vai_brasil` — readable rallying cry
11. `brg_tifo` — flag reveal, satisfying build
12. `brg_spin_ball` — clean loop to round out

Tip: during an actual goal, jump the panel straight to `brg_gooool` (or `brg_celebration`).
