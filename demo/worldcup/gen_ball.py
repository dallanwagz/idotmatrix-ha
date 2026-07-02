#!/usr/bin/env python3
"""Shared soccer ball — a real 3-D rolling Telstar (black pentagon patches mapped onto a rotating
sphere, so they wrap and roll off the limb). Rendered on each team's background colour; only the
background changes per team. Solid colours (decoder-safe)."""
import math, os
from PIL import Image, ImageDraw
HERE=os.path.dirname(os.path.abspath(__file__))
WHITE=(255,255,255); BLK=(22,22,26); RIM=(228,228,228)
# 12 icosahedron vertices = the pentagon-patch centres of a soccer ball
_p=(1+5**0.5)/2
_V=[]
for _a,_b in [(1,_p),(1,-_p),(-1,_p),(-1,-_p)]:
    _V+=[(0,_a,_b),(_a,_b,0),(_b,0,_a)]
_V=[(x/(x*x+y*y+z*z)**.5, y/(x*x+y*y+z*z)**.5, z/(x*x+y*y+z*z)**.5) for (x,y,z) in _V]

def ball(bg, out, N=24, spot=0.42):
    cx=cy=16; R=15; SH=tuple(int(c*0.6) for c in bg); TH=math.cos(spot)
    frames=[]
    for f in range(N):
        a=2*math.pi*f/N; ca,sa=math.cos(a),math.sin(a)
        img=Image.new("RGB",(32,32),bg); d=ImageDraw.Draw(img)
        d.ellipse([cx-12,cy+12,cx+12,cy+15],fill=SH)
        px=img.load()
        for y in range(32):
            for x in range(32):
                nx,ny=(x+0.5-cx)/R,(y+0.5-cy)/R; r2=nx*nx+ny*ny
                if r2<=1.0:
                    nz=math.sqrt(1-r2)
                    bx=ca*nx - sa*nz; by=ny; bz=sa*nx + ca*nz   # inverse-rotate to ball space
                    col=WHITE
                    for vx,vy,vz in _V:
                        if bx*vx+by*vy+bz*vz>TH: col=BLK; break
                    px[x,y]=col
        d.ellipse([cx-R,cy-R,cx+R,cy+R],outline=RIM)
        frames.append(img)
    frames[0].save(out,format="GIF",save_all=True,append_images=frames[1:],duration=55,loop=0,disposal=2)
    print(" ",os.path.basename(out),os.path.getsize(out),"B")

if __name__=="__main__":
    print("shared rolling ball, per-team background:")
    ball((0,66,34),  os.path.join(HERE,"ball_brazil.gif"))
    ball((12,28,74), os.path.join(HERE,"ball_usa.gif"))
