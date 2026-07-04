# Pi 3B+ case with top-mounted 2.4" SPI TFT — design report

> Research report (2026). Build-vs-reuse decision + verified dimensions + parametric design spec.
> Sources at the bottom.

## Verdict: BUILD parametric (from scratch), borrowing geometry
No existing model matches "Pi 3B+ enclosure + *jumper-wired* generic 2.4" ILI9341/XPT2046 module in a
face-up top cradle." Existing designs split into (1) Pi + GPIO-hat 3.5" screen cases (right box, wrong
screen, no wiring clearance) and (2) 2.4"/2.8" ILI9341 + ESP32 cases (right cradle, wrong computer).
Since this screen connects by a 14-wire Dupont bundle (not sitting on the header), it needs internal
headroom + a pass-through no candidate has. Borrow the bezel-clamp from the ILI9341 cases + standard
Pi 3B+ box geometry.

## Closest existing models (donors)
| Model | Link | Closeness |
|---|---|---|
| RPi Display Case (ftobler) | thingiverse.com/thing:1229473 (+ customizable :2395683) | ~60% concept (3.5" GPIO screen) |
| RPi 3.5" TFT Case (Rexchen) | thingiverse.com/thing:1422963 | ~55% |
| Tiny Desktop (MakerWorld) | makerworld.com/en/models/1354105 | ~50% |
| 2.8" ILI9341 case (DorffMeister) | printables.com/model/441958 | ~50% bezel/cradle donor |
| Snap-fit ILI9341 case (Kiko64) | printables.com/model/152702 | snap tolerances donor |

## Verified dimensions
**Pi 3B+** (official mechanical drawing RP-008337-DS): board **85×56 mm**, 3 mm corner radius, PCB
1.4 mm. Mount holes **M2.5, 3.5 mm from edges, 58×49 mm spacing**. GPIO 2×20 header on top long edge,
**Z 8.5 mm**. USB stacks Z 16 mm (centers ~29/47 mm from bottom), Ethernet Z 13.5 mm (~10.25 mm).
Bottom edge: micro-USB x=10.6, HDMI x=32 (Z 6.5), AV jack x=53.5 (Z 6.0). microSD underside, left
edge, ~28 mm from bottom, protrudes ~2.5 mm.

**2.4" TFT module — two variants, so keep cradle parametric:**
- Classic "red board" MSP2402 (ILI9341+XPT2046+SD): **PCB 77.18×42.72 mm, active 36.72×48.96 mm,
  ~7 mm thick**, 1×14 header on one short edge, SD on the back.
- Wider variant (Waveshare-style): **~71×52×7 mm**.
- **Caliper the actual board** (length, width, header offset, glass offset) before printing — those
  are the only params that change. Header pins protrude from the **back** → face-up screen means pins
  point **down** (what the pass-through wants). Dupont housing ≈14 mm, pin ≈6 mm → budget ~15 mm.

## Case design spec (parametric, 3 parts: base box, lid/bay tray, snap bezel)
```
pi_l=85; pi_w=56; pi_hole_dx=58; pi_hole_dy=49; pi_hole_edge=3.5;
wall=2.4; floor_t=2.0; standoff_h=3.0; pcb_t=1.4;
inner_h=29;                                 // 3 + 1.4 + 8.5 GPIO + ~15 Dupont + slack
tft_l=77.5; tft_w=43.0; tft_t=7.0;          // measured PCB + 0.3-0.4 clearance
tft_aa_l=49.0; tft_aa_w=36.7;               // active area (+0.5 reveal in bezel)
tft_hdr_pins=14; tft_hdr_edge="left"; bay_depth=8.5;
bezel_t=2.5; lid_screw="M2.5 x4"; clr_snap=0.25;
```
- **Base box**: inner 89×60×29, outer ≈94×65×31. Four M2.5 standoffs (6 mm OD, 3 mm, 2.2 mm pilot) at
  58×49. Port cutouts +0.75–1 mm/side (USB 15×17.5, Ethernet 17.5×15, micro-USB 9×5, HDMI 17×7,
  AV Ø7.5, microSD 15×3.5 at floor+3 with a finger scallop).
- **Lid = bay tray**: recessed open-top bay `tft_l×tft_w×bay_depth`, 1.5 mm support shelf under PCB
  edges, **header slot ~38×8 through the bay floor** (pins+housings drop into the Pi compartment),
  relief pocket ~28×18×2.5 for the rear SD/touch IC. Place bay so the header slot lands over the Pi's
  GPIO quadrant, clear of the 16 mm USB stacks. 4× M2.5 self-tappers into corner bosses (screws, so
  wiring is serviceable). Zip-tie saddle for the 14-wire ribbon. Vertical budget: 8.5+15=23.5 < 29 ✔.
- **Bezel**: 2.5 mm plate, window = active area +1 mm reveal (~50×37.7), 45° inner chamfer for touch,
  4× cantilever snap tabs (8×3×1.6, 0.8 mm hook, 0.25 mm clearance), underside ribs press PCB corners
  to the shelf.
- **Vents**: 6–8 slots 2.5×20 in base floor under SoC + rear wall (chimney); ≥10 mm over SoC for a
  heatsink.

## Print notes
Orientation: base open-up, lid bay-down, bezel face-down — no supports if port cutouts get 45°
chamfers/sacrificial bridges. Tolerances: PCB pockets +0.3–0.4, snaps +0.2–0.3, ports +0.75–1/side,
M2.5 pilots 2.2 mm (or 3.5 mm bores for heat-set inserts). PETG preferred (cases run warm), 0.2 mm
layers, 3 perimeters. **Print a test coupon** (bay corner + header slot + one snap tab) to validate
the measured TFT dims before the full case.

## Sources
Pi 3B+ mechanical drawing (RP-008337-DS PDF); LCD wiki MSP2402 + user manual; Thingiverse ftobler
:1229473 / :2395683, Rexchen :1422963; MakerWorld 1354105; Printables DorffMeister 441958, Kiko64
152702; Cults3D 2.8" ILI9341 frame.
