# USA World Cup pack — 64×64 iDotMatrix animations

Twelve looping GIFs celebrating the USMNT, built with the project's panel-safe helper
(`pi-quickstart/assetlib.py`): every frame is ≤16 flat colors, no gradients/dithering, so the
panel's GIF decoder plays every frame. All files are 64×64 RGB and loop forever.

Palette: red `(200,30,45)`, white `(255,255,255)`, Old Glory navy `(0,40,104)`, star-gold
`(255,215,0)`, black `(0,0,0)` = LEDs off.

Regenerate everything (GIFs + `*_preview.png` + `_contact_sheet.png`):

```
python3 gen_usa.py
```

All 12 files are far under the 200 KB ceiling (largest ≈ 19 KB).

## Pack A — Flags & Fan decor

| File | Shows | Frames | Size | Dwell |
|------|-------|-------:|-----:|------:|
| `us_flag_wave.gif` | Waving Stars & Stripes — 13 stripes + navy canton with a star grid, rippling column wave with a travelling shadow band | 24 | 19.7 KB | 10 s |
| `us_usa_chant.gif` | Bold **USA** wordmark pulsing through red→white→blue→gold with an expanding ring and corner sparkles | 20 | 9.5 KB | 8 s |
| `us_stars_twinkle.gif` | Field of red/white/gold 5-point stars twinkling over a static navy sky (fast refresh) | 16 | 5.9 KB | 8 s |
| `us_fireworks.gif` | Red-white-blue-gold fireworks bursting and fading over black | 28 | 5.3 KB | 8 s |

## Pack B — Goals & Ball action

| File | Shows | Frames | Size | Dwell |
|------|-------|-------:|-----:|------:|
| `us_ball_roll.gif` | Shaded soccer ball (white + navy pentagons) spinning and rolling left→right across a green pitch | 24 | 8.2 KB | 8 s |
| `us_goal.gif` | Ball driven into the net — arc in, net ripples on impact, then a **GOAL!** flash in team colors | 30 | 12.4 KB | 10 s |
| `us_striker_kick.gif` | Navy striker silhouette swinging its leg and launching the ball off-screen | 16 | 6.1 KB | 6 s |
| `us_eagle.gif` | USMNT bald-eagle crest with flapping wings, gold beak, clutching a gold star | 16 | 6.1 KB | 6 s |

## Pack C — Trophies & Glory

| File | Shows | Frames | Size | Dwell |
|------|-------|-------:|-----:|------:|
| `us_trophy.gif` | Gold World Cup trophy with a bright glint sweeping diagonally across it | 20 | 10.3 KB | 8 s |
| `us_trophy_raise.gif` | Trophy lifted skyward amid rotating gold/red rays-of-glory and a burst of stars | 22 | 12.4 KB | 8 s |
| `us_champions.gif` | **USA!** flourish — waving red/white stripes, a twinkling gold star arc, pulsing wordmark | 20 | 8.9 KB | 8 s |
| `us_stripes_scroll.gif` | Decorative barber-pole: diagonal red/white/navy stripes scrolling with marching gold stars | 16 | 9.3 KB | 6 s |

## Previews

- `_contact_sheet.png` — montage of every animation's first frame.
- `<name>_preview.png` — 8× zoom of each GIF's frame 0.

## Recommended 12-slot carousel ordering

A build-and-release arc: fan warm-up → ball/goal action → trophy payoff, ending on the loop-back
decor. Fits the panel's 12-slot cap exactly.

| Slot | File | Dwell |
|-----:|------|------:|
| 1 | `us_flag_wave.gif` | 10 s |
| 2 | `us_usa_chant.gif` | 8 s |
| 3 | `us_stripes_scroll.gif` | 6 s |
| 4 | `us_ball_roll.gif` | 8 s |
| 5 | `us_striker_kick.gif` | 6 s |
| 6 | `us_goal.gif` | 10 s |
| 7 | `us_eagle.gif` | 6 s |
| 8 | `us_stars_twinkle.gif` | 8 s |
| 9 | `us_fireworks.gif` | 8 s |
| 10 | `us_trophy.gif` | 8 s |
| 11 | `us_trophy_raise.gif` | 8 s |
| 12 | `us_champions.gif` | 8 s |

### Best-of (if you only run a few)

`us_flag_wave` → `us_goal` → `us_trophy_raise` → `us_champions` — the four that best flex color,
motion, and the USA story from kickoff to lifting the cup.
