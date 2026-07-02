#!/usr/bin/env python3
"""Shared spinning soccer ball (Telstar) rendered on each team's background colour.
One ball design; only the pitch/background changes per team."""
import math, os
from PIL import Image, ImageDraw
HERE=os.path.dirname(os.path.abspath(__file__))
WHITE=(255,255,255); BLK=(20,20,24); RIM=(225,225,225)
def ball(bg, out):
    cx=cy=16; R=15; N=24
    SH=tuple(int(c*0.6) for c in bg)
    frames=[]
    for f in range(N):
        img=Image.new("RGB",(32,32),bg); d=ImageDraw.Draw(img)
        d.ellipse([cx-12,cy+12,cx+12,cy+15],fill=SH)
        d.ellipse([cx-R,cy-R,cx+R,cy+R],fill=WHITE)
        rot=2*math.pi*f/N
        def pent(pcx,pcy,rad,a0):
            pts=[(pcx+rad*math.cos(a0+i*2*math.pi/5),pcy+rad*math.sin(a0+i*2*math.pi/5)) for i in range(5)]
            d.polygon(pts,fill=BLK)
        pent(cx,cy,3.4,rot)
        for k in range(5):
            a=rot+k*2*math.pi/5
            pent(cx+9.2*math.cos(a),cy+9.2*math.sin(a),2.5,rot+a)
        d.ellipse([cx-R,cy-R,cx+R,cy+R],outline=RIM)
        frames.append(img)
    frames[0].save(out,format="GIF",save_all=True,append_images=frames[1:],duration=60,loop=0,disposal=2)
    print(" ",os.path.basename(out),os.path.getsize(out),"B")
if __name__=="__main__":
    print("shared ball, per-team background:")
    ball((0,66,34),  os.path.join(HERE,"ball_brazil.gif"))   # green pitch
    ball((12,28,74), os.path.join(HERE,"ball_usa.gif"))      # navy
