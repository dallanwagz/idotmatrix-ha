#!/usr/bin/env python3
"""Switch BOTH iDotMatrix panels to a team's carousel — one command.

    python3 set_team.py brazil
    python3 set_team.py usa

Shared spinning ball (only its background colour changes per team) + that team's flag + wordmark.
Self-contained (bleak only). Addresses panels by CoreBluetooth UUID on macOS, by MAC on Linux/Pi.
Assets are the *.gif in this folder. Add teams by dropping flag_/ball_/text_ gifs + a TEAMS entry.
"""
import asyncio, os, platform, struct, sys, zlib
from bleak import BleakClient

HERE=os.path.dirname(os.path.abspath(__file__))
FA_WRITE="0000fa02-0000-1000-8000-00805f9b34fb"; FA_NOTIFY="0000fa03-0000-1000-8000-00805f9b34fb"
OUTER=4096; SAFE=244; GIF=1

PANELS=[
    {"name":"IDM-858931","uuid":"0A935535-7939-DD31-2CC3-72B639D9560B","mac":"6F:5D:FE:85:89:31"},
    {"name":"IDM-D28F7F","uuid":"D2B7C4A4-4260-203B-6500-9AD27E2F65F3","mac":"1F:D6:5C:D2:8F:7F"},
]
TEAMS={
    "brazil":[("flag_brazil.gif",10),("ball_brazil.gif",8),("text_brazil.gif",8)],
    "usa":   [("flag_usa.gif",10),  ("ball_usa.gif",8),  ("text_usa.gif",8)],
}

def frame(cmd,sub,*p):
    body=bytes(b&0xFF for b in p); t=4+len(body)
    return bytes((t&0xFF,(t>>8)&0xFF,cmd&0xFF,sub&0xFF))+body
def outer_packets(data,slot,ts):
    crc=struct.pack("<I",zlib.crc32(data)&0xFFFFFFFF); tot=len(data)
    ts=0 if slot==12 else ts
    chunks=[data[i:i+OUTER] for i in range(0,len(data),OUTER)] or [b""]
    out=[]
    for i,ch in enumerate(chunks):
        opt=0 if i==0 else 2; ln=len(ch)+16
        out.append(bytes((ln&0xFF,(ln>>8)&0xFF,GIF,0,opt))+struct.pack("<I",tot)+crc+bytes((ts&0xFF,(ts>>8)&0xFF,slot&0xFF))+ch)
    return out
class Link:
    def __init__(self): self.ev=asyncio.Event(); self.status=None
    def cb(self,_,d):
        if len(d)>=5: self.status=d[4]; self.ev.set()

async def push(addr, items):
    link=Link()
    async with BleakClient(addr,timeout=25) as c:
        await c.start_notify(FA_NOTIFY,link.cb)
        await c.write_gatt_char(FA_WRITE,frame(2,1,12,*range(12)),response=False); await asyncio.sleep(1.0)
        await c.write_gatt_char(FA_WRITE,frame(2,1,len(items),*range(len(items))),response=False); await asyncio.sleep(1.0)
        for i,(gif,dw) in enumerate(items):
            for pkt in outer_packets(gif,i,dw):
                for j in range(0,len(pkt),SAFE):
                    await c.write_gatt_char(FA_WRITE,pkt[j:j+SAFE],response=False); await asyncio.sleep(0.02)
                link.ev.clear()
                try: await asyncio.wait_for(link.ev.wait(),8)
                except asyncio.TimeoutError: return False
                if link.status==2: return False
            await asyncio.sleep(0.25)
        await c.write_gatt_char(FA_WRITE,frame(10,1),response=False); await asyncio.sleep(1.0)
    return True

async def main():
    team=(sys.argv[1].lower() if len(sys.argv)>1 else "")
    if team not in TEAMS: sys.exit(f"usage: set_team.py {'|'.join(TEAMS)}")
    items=[(open(os.path.join(HERE,f),"rb").read(),d) for f,d in TEAMS[team]]
    key="uuid" if platform.system()=="Darwin" else "mac"
    print(f"switching BOTH panels -> {team.upper()}", flush=True)
    for pan in PANELS:
        ok=await push(pan[key], items)
        print(f"  {pan['name']}: {'OK' if ok else 'FAILED'}", flush=True)

if __name__=="__main__":
    asyncio.run(main())
