// Raspberry Pi 3B+ enclosure with a top-mounted, face-up 2.4" SPI TFT (ILI9341/XPT2046).
// Screen is wired to the Pi GPIO by jumpers; its header pins point DOWN through a slot in the lid
// into the Pi compartment. Three printed parts: base box, bay-tray lid, snap bezel.
// Defaults are for the 77x43 "red board" MSP2402 module.
//
// Render one part:  part = "base" | "lid" | "bezel" | "assembled"
// Export STL:  openscad -o base.stl  -D 'part="base"'  case.scad   (etc.)

part = "assembled";
eps  = 0.1;
$fn  = 48;

/* ---------------- parameters ---------------- */
// Raspberry Pi 3B+
pi_l = 85; pi_w = 56; pi_pcb_t = 1.4;
hole_dx = 58; hole_dy = 49; hole_edge = 3.5;   // M2.5 mount pattern, 3.5mm from edges
gpio_z = 8.5;

// 2.4" TFT module (77x43 MSP2402) — re-measure header_off & glass offset if yours differs
tft_l = 77.18; tft_w = 42.72; tft_t = 7.0;
tft_aa_l = 48.96; tft_aa_w = 36.72;            // active (visible) area
hdr_slot_l = 38; hdr_slot_w = 8;               // pass-through for the 14-pin header + Dupont housings

// Case
wall = 2.4; floor_t = 2.2; fit = 0.4;
standoff_h = 3.0; standoff_od = 6.0; standoff_pilot = 2.1;   // self-tap M2.5
inner_h = 29;                                  // Pi + GPIO(8.5) + Dupont(~15) headroom
lid_t = 2.5; bay_wall = 2.2; bay_depth = 8.5;
bezel_t = 2.5; reveal = 1.0; snap_clr = 0.25;
boss_od = 7.0; boss_pilot = 2.1;               // lid corner screw bosses (M2.5 self-tap)

/* ---------------- derived ---------------- */
in_l = pi_l + 2*fit;  in_w = pi_w + 2*fit;
out_l = in_l + 2*wall; out_w = in_w + 2*wall;
base_h = floor_t + inner_h;
bx = wall + fit; by = wall + fit;                       // Pi board origin (interior)
pcb_top = floor_t + standoff_h + pi_pcb_t;             // z of the top face of the Pi PCB

// screen bay footprint on the lid (centered in X, biased toward GPIO/back in Y)
bay_l = tft_l + fit; bay_w = tft_w + fit;
bay_x = (out_l - bay_l)/2;
bay_y = out_w - bay_w - bay_wall - 2;                   // toward the back (GPIO) edge

module hole_posts(dia, h, od) {                        // 4 posts at the Pi mount pattern
  for (x=[hole_edge, hole_edge+hole_dx], y=[hole_edge, hole_edge+hole_dy])
    translate([bx+x, by+y, floor_t])
      difference() { cylinder(d=od, h=h); translate([0,0,-eps]) cylinder(d=dia, h=h+2*eps); }
}

module corner_bosses(h) {                               // lid-screw bosses in the 4 case corners
  inset = boss_od/2 + wall;
  for (x=[inset, out_l-inset], y=[inset, out_w-inset])
    translate([x, y, floor_t])
      difference() { cylinder(d=boss_od, h=h); translate([0,0,-eps]) cylinder(d=boss_pilot, h=h+2*eps); }
}
module corner_screw_holes() {
  inset = boss_od/2 + wall;
  for (x=[inset, out_l-inset], y=[inset, out_w-inset])
    translate([x, y, -eps]) cylinder(d=3.0, h=lid_t+2*eps);   // M2.5 clearance through the lid
}

/* ---------------- base box ---------------- */
module base() {
  difference() {
    // shell
    cube([out_l, out_w, base_h]);
    // interior cavity
    translate([wall, wall, floor_t]) cube([in_l, in_w, inner_h+eps]);

    // --- port cutouts (generous; +margin). Heights measured from the PCB top face. ---
    // right short edge (x = out_l): 2x USB stacks (Z16) + Ethernet (Z13.5)
    for (yc=[29, 47]) translate([out_l-wall-eps, by+yc-7.5, pcb_top-0.5]) cube([wall+2*eps, 15, 17.5]);
    translate([out_l-wall-eps, by+10.25-8, pcb_top-0.5]) cube([wall+2*eps, 16, 15]);
    // bottom long edge (y = 0): micro-USB (x=10.6), HDMI (x=32), AV (x=53.5)
    translate([bx+10.6-4.5, -eps, pcb_top-0.5]) cube([9, wall+2*eps, 6]);
    translate([bx+32-8.5,  -eps, pcb_top-0.5]) cube([17, wall+2*eps, 7.5]);
    translate([bx+53.5-4,  -eps, pcb_top-0.5]) cube([8, wall+2*eps, 7]);
    // left short edge (x = 0): microSD access, near the floor
    translate([-eps, by+28-7.5, floor_t+1]) cube([wall+2*eps, 15, 3.5]);

    // --- ventilation: floor slots under the SoC + rear wall ---
    for (i=[0:5]) translate([bx+18+i*8, by+16, -eps]) cube([2.5, 22, floor_t+2*eps]);
    for (i=[0:4]) translate([bx+20+i*10, out_w-wall-eps, floor_t+6]) cube([2.0, wall+2*eps, 10]);
  }
  hole_posts(standoff_pilot, standoff_h, standoff_od);   // Pi standoffs
  corner_bosses(base_h - floor_t);                        // lid-screw bosses up to the rim
}

/* ---------------- lid / bay tray ---------------- */
module lid() {
  difference() {
    union() {
      cube([out_l, out_w, lid_t]);                        // plate
      // raised bay well around the screen
      translate([bay_x-bay_wall, bay_y-bay_wall, lid_t])
        difference() {
          cube([bay_l+2*bay_wall, bay_w+2*bay_wall, bay_depth]);
          translate([bay_wall, bay_wall, -eps]) cube([bay_l, bay_w, bay_depth+2*eps]);
          // 4 snap-tab slots in the well walls (bezel tabs clip in)
          for (sx=[bay_wall+bay_l*0.25, bay_wall+bay_l*0.7])
            for (sy=[-eps, bay_w+bay_wall+eps])
              translate([sx, sy, bay_depth-3]) cube([8, bay_wall+2*eps, 2]);
        }
    }
    corner_screw_holes();
    // header pass-through slot (pins point down into the compartment), over the back/GPIO area
    translate([bay_x + (bay_l-hdr_slot_l)/2, bay_y + bay_w - hdr_slot_w - 2, -eps])
      cube([hdr_slot_l, hdr_slot_w, lid_t+2*eps]);
    // relief pocket in the shelf for the rear SD-slot / touch-IC bump
    translate([bay_x + (bay_l-28)/2, bay_y + 4, lid_t-2.0])
      cube([28, 18, 2.0+eps]);
  }
}

/* ---------------- snap bezel ---------------- */
module bezel() {
  win_l = tft_aa_l + reveal; win_w = tft_aa_w + reveal;
  bl = bay_l + 2*bay_wall; bw = bay_w + 2*bay_wall;
  difference() {
    cube([bl, bw, bezel_t]);
    // window with a 45 chamfer on the inner (top) edge for finger/touch access
    translate([(bl-win_l)/2, (bw-win_w)/2, -eps]) cube([win_l, win_w, bezel_t+2*eps]);
    translate([(bl-win_l)/2-1, (bw-win_w)/2-1, bezel_t-1])
      difference() {                                      // chamfer ring
        cube([win_l+2, win_w+2, 1+eps]);
        translate([1,1,-eps]) cube([win_l, win_w, 1+2*eps]);
      }
  }
  // 4 cantilever snap tabs on the underside that hook into the well-wall slots
  for (sx=[bl*0.25, bl*0.7])
    for (sy=[bay_wall/2, bw-bay_wall/2])
      translate([sx, sy-1.5, -3])
        cube([8, 1.6, 3]);                                // tab bodies (hook simplified for printability)
}

/* ---------------- placement ---------------- */
if (part=="base") base();
else if (part=="lid") lid();
else if (part=="bezel") bezel();
else {                                                    // assembled preview
  color("SteelBlue") base();
  color("Gainsboro") translate([0,0,base_h+0.5]) lid();
  color("DimGray")   translate([bay_x-bay_wall,bay_y-bay_wall,base_h+0.5+lid_t+bay_depth+0.5]) bezel();
}
