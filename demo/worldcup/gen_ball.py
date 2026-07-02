#!/usr/bin/env python3
"""Shared soccer ball — a realistic adidas Trionda (WC 2026): shaded, glossy, rolling sphere with
white curved seams between green/blue/red/navy panels + small gold star accents. Modelled on the
real ball (Behance render). Only the background colour changes per team. Palette kept small
(flat shading bands, no smooth gradients) so the panel's GIF decoder plays every frame."""
import math, os
from PIL import Image, ImageDraw
HERE=os.path.dirname(os.path.abspath(__file__))
GREEN=(0,170,80); BLUE=(0,120,215); RED=(150,22,32); NAVY=(20,30,66); SEAM=(248,248,250); GOLD=(255,205,60)
PANELS=[GREEN,BLUE,RED,NAVY]
_gs=[(0.28,0.62,0.73),(-0.66,0.42,0.62),(0.55,-0.55,0.63),(-0.35,-0.5,0.79)]  # gold-star directions
_gs=[(x/(x*x+y*y+z*z)**.5,y/(x*x+y*y+z*z)**.5,z/(x*x+y*y+z*z)**.5) for x,y,z in _gs]
Lx,Ly,Lz=-0.5,-0.62,0.60; _n=(Lx*Lx+Ly*Ly+Lz*Lz)**.5; Lx,Ly,Lz=Lx/_n,Ly/_n,Lz/_n

def _tex(bx,by,bz):
    lon=math.atan2(bz,bx); sw=(lon/(2*math.pi)+0.5+0.14*by)%1.0
    sec=int(sw*4)%4; frac=(sw*4)%1.0
    if frac<0.11 or frac>0.89: return SEAM
    for gx,gy,gz in _gs:
        if bx*gx+by*gy+bz*gz>0.975: return GOLD      # small gold star dot
    return PANELS[sec]

def _shade(col,nx,ny,nz):
    diff=nx*Lx+ny*Ly+nz*Lz
    if diff>0.95: return (255,255,255)               # specular highlight
    t=0.58 if diff<0.22 else (0.80 if diff<0.60 else 1.0)
    return tuple(min(255,int(c*t)) for c in col)

def ball(bg, out, N=24):
    cx=cy=16; R=15; frames=[]
    for f in range(N):
        a=2*math.pi*f/N; ca,sa=math.cos(a),math.sin(a)
        img=Image.new("RGB",(32,32),bg); d=ImageDraw.Draw(img)
        d.ellipse([cx-12,cy+12,cx+12,cy+15],fill=tuple(int(c*0.6) for c in bg))
        px=img.load()
        for y in range(32):
            for x in range(32):
                nx,ny=(x+0.5-cx)/R,(y+0.5-cy)/R; r2=nx*nx+ny*ny
                if r2<=1.0:
                    nz=math.sqrt(1-r2)
                    bx=ca*nx-sa*nz; by=ny; bz=sa*nx+ca*nz
                    px[x,y]=_shade(_tex(bx,by,bz),nx,ny,nz)
        frames.append(img.quantize(colors=16, dither=Image.Dither.NONE).convert("RGB"))
    frames[0].save(out,format="GIF",save_all=True,append_images=frames[1:],duration=55,loop=0,disposal=2)
    print(" ",os.path.basename(out),os.path.getsize(out),"B")

if __name__=="__main__":
    print("shared realistic Trionda, per-team background:")
    ball((0,66,34),  os.path.join(HERE,"ball_brazil.gif"))
    ball((12,28,74), os.path.join(HERE,"ball_usa.gif"))
