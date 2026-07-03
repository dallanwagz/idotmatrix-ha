#!/usr/bin/env python3
"""Generate the World Cup team set at a given panel size (default 64). Per team:
   flag_<team>{sfx}.gif, ball_<team>{sfx}.gif, text_<team>{sfx}.gif   (sfx='' for 32, else '_<size>').
Ball = realistic rolling adidas Trionda (per-team background). Flags + wordmarks scale with size.
Usage: python3 gen_worldcup.py [size]   # 32 or 64
"""
import math, os, sys
from PIL import Image, ImageDraw, ImageFont
HERE=os.path.dirname(os.path.abspath(__file__))
S=int(sys.argv[1]) if len(sys.argv)>1 else 64
SFX="" if S==32 else f"_{S}"
W=(255,255,255)
def save(frames,name,ms):
    p=os.path.join(HERE,f"{name}{SFX}.gif")
    frames[0].save(p,format="GIF",save_all=True,append_images=frames[1:],duration=ms,loop=0,disposal=2)
    print(f"  {os.path.basename(p):22s} {frames[0].size[0]}x{frames[0].size[1]} {len(frames)}f {os.path.getsize(p)}B")
def font(sz):
    for f in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf","/System/Library/Fonts/Menlo.ttc"):
        if os.path.exists(f):
            try: return ImageFont.truetype(f,sz)
            except Exception: pass
    return ImageFont.load_default()

# ---------- shared realistic Trionda ball ----------
GREEN=(0,170,80); BLUE=(0,120,215); RED=(150,22,32); NAVY=(20,30,66); SEAM=(248,248,250); GOLD=(255,205,60)
PANELS=[GREEN,BLUE,RED,NAVY]
_gs=[(0.28,0.62,0.73),(-0.66,0.42,0.62),(0.55,-0.55,0.63),(-0.35,-0.5,0.79)]
_gs=[(x/(x*x+y*y+z*z)**.5,y/(x*x+y*y+z*z)**.5,z/(x*x+y*y+z*z)**.5) for x,y,z in _gs]
Lx,Ly,Lz=-0.5,-0.62,0.60; _n=(Lx*Lx+Ly*Ly+Lz*Lz)**.5; Lx,Ly,Lz=Lx/_n,Ly/_n,Lz/_n
def _tex(bx,by,bz):
    lon=math.atan2(bz,bx); sw=(lon/(2*math.pi)+0.5+0.14*by)%1.0
    sec=int(sw*4)%4; frac=(sw*4)%1.0
    if frac<0.11 or frac>0.89: return SEAM
    for gx,gy,gz in _gs:
        if bx*gx+by*gy+bz*gz>0.985: return GOLD
    return PANELS[sec]
def _shade(c,nx,ny,nz):
    d=nx*Lx+ny*Ly+nz*Lz
    if d>0.95: return (255,255,255)
    t=0.58 if d<0.22 else (0.80 if d<0.60 else 1.0)
    return tuple(min(255,int(v*t)) for v in c)
def ball(bg,name,N=24):
    cx=cy=S/2.0; R=S*0.44          # leave a visible team-colour margin/ring
    frames=[]
    for f in range(N):
        a=2*math.pi*f/N; ca,sa=math.cos(a),math.sin(a)
        img=Image.new("RGB",(S,S),bg); d=ImageDraw.Draw(img)
        d.ellipse([cx-R*0.85,cy+R*0.82,cx+R*0.85,cy+R*1.12],fill=tuple(int(c*0.6) for c in bg))
        px=img.load()
        for y in range(S):
            for x in range(S):
                nx,ny=(x+0.5-cx)/R,(y+0.5-cy)/R; r2=nx*nx+ny*ny
                if r2<=1.0:
                    nz=math.sqrt(1-r2); bx=ca*nx-sa*nz; by=ny; bz=sa*nx+ca*nz
                    px[x,y]=_shade(_tex(bx,by,bz),nx,ny,nz)
        frames.append(img.quantize(colors=24,dither=Image.Dither.NONE).convert("RGB"))
    save(frames,name,55)

# ---------- Brazil bandeira ----------
def bandeira(name,N=8):
    GF=(0,151,57); YF=(255,223,0); BF=(0,39,118)
    cx,cy=S/2,S/2; r=S*0.30; mx,my=S*0.08,S*0.10
    band=Image.new("L",(S,S),0); ImageDraw.Draw(band).polygon(
        [(cx-r,cy+r*0.20),(cx+r,cy-r*0.45),(cx+r,cy-r*0.10),(cx-r,cy+r*0.55)],fill=255)
    globe=Image.new("L",(S,S),0); ImageDraw.Draw(globe).ellipse([cx-r,cy-r,cx+r,cy+r],fill=255)
    bl,gl=band.load(),globe.load()
    stars=[(cx+r*a,cy+r*b) for a,b in [(-.4,-.3),(.3,-.4),(-.1,.3),(.45,.15),(-.5,.1),(.05,-.55),
            (.25,.45),(-.3,.5),(.15,.1),(-.15,-.1),(.4,-.15),(-.45,-.35),(.5,.4)]]
    frames=[]
    for f in range(N):
        img=Image.new("RGB",(S,S),GF); d=ImageDraw.Draw(img)
        d.polygon([(cx,my),(S-mx,cy),(cx,S-my),(mx,cy)],fill=YF)
        d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=BF)
        px=img.load()
        for y in range(S):
            for x in range(S):
                if gl[x,y] and bl[x,y]: px[x,y]=W
        for i,(sx,sy) in enumerate(stars):
            if (i+f)%3:
                ix,iy=int(sx),int(sy)
                if 0<=ix<S and 0<=iy<S and gl[ix,iy]: px[ix,iy]=W
        frames.append(img)
    save(frames,name,220)

# ---------- USA stars & stripes ----------
def stars_stripes(name,N=8):
    RED=(191,10,48); NAVY2=(0,40,104)
    cw,ch=int(S*0.42),int(S*7/13)
    frames=[]
    for f in range(N):
        img=Image.new("RGB",(S,S),RED); d=ImageDraw.Draw(img)
        for y in range(S):
            if int(y*13/S)%2==1: d.line([(0,y),(S,y)],fill=W)
        d.rectangle([0,0,cw,ch],fill=NAVY2)
        px=img.load(); i=0; step=max(2,S//12)
        for ry in range(step,ch-1,step):
            for rx in range(step,cw-1,step):
                if (i+f)%4: px[rx,ry]=W
                i+=1
        frames.append(img)
    save(frames,name,220)

# ---------- wordmark (fit-to-width) ----------
def wordmark(text,name,fg,bg,accent,N=16):
    fnt=font(int(S*0.5))
    tmp=Image.new("L",(S*6,S),0); ImageDraw.Draw(tmp).text((0,0),text,fill=255,font=fnt)
    b=tmp.getbbox(); mask=tmp.crop(b); tw,th=mask.size
    maxw=S-2
    if tw>maxw:                                   # scale text down to fit the panel width
        nh=max(1,int(th*maxw/tw)); mask=mask.resize((maxw,nh)); tw,th=mask.size
    ml=mask.load()
    frames=[]
    for f in range(N):
        img=Image.new("RGB",(S,S),bg); d=ImageDraw.Draw(img)
        band=max(4,S//8); off=f%band
        for y in range(0,S,band):
            d.rectangle([0,y+off-2,S,y+off],fill=accent)
        ox,oy=(S-tw)//2,(S-th)//2; px=img.load()
        for y in range(th):
            for x in range(tw):
                if ml[x,y]>110 and 0<=ox+x<S and 0<=oy+y<S: px[ox+x,oy+y]=fg
        for sx in range(2,S-1,band):
            if (sx+f)%4: px[sx,1]=W
        frames.append(img)
    save(frames,name,110)

if __name__=="__main__":
    print(f"World Cup set @ {S}x{S}:")
    ball((0,66,34),"ball_brazil"); ball((12,28,74),"ball_usa")
    bandeira("flag_brazil"); stars_stripes("flag_usa")
    wordmark("BRASIL","text_brazil",(255,223,0),(0,39,118),(0,120,60))
    wordmark("USA","text_usa",W,(0,40,104),(160,12,44))
