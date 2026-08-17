from __future__ import annotations
import base64,gzip
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def reconstruct()->str:
    raw=''.join(p.read_text().strip() for p in PARTS)
    return gzip.decompress(base64.b64decode(raw)).decode('utf-8')

def repack(html:str)->None:
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    chunks += ['']*(len(PARTS)-len(chunks))
    if ''.join(chunks)!=packed: raise RuntimeError('bundle split failed')
    for p,c in zip(PARTS,chunks): p.write_text(c+'\n')

def main()->None:
    html=reconstruct()
    old="function fmRecalculateBank(){\n const now=new Set(state.squad||[]);\n if(!state.teamConfirmed){state.bank=fmMoney(100-(state.squad||[]).reduce((s,id)=>s+fmCurrentPrice(id),0));return state.bank}\n const locked=[...(state.lockedSquad||[])],lockedSet=new Set(locked),base=Number(state.lockedBank??state.bank??0);"
    new="function fmRecalculateBank(){\n const now=new Set(state.squad||[]);\n const preFirstGW=!state.firstGameweekPlayed&&!(state.pointsHistory||[]).length;\n if(!state.teamConfirmed||preFirstGW){state.bank=fmMoney(100-(state.squad||[]).reduce((s,id)=>s+fmCurrentPrice(id),0));if(preFirstGW)state.lockedBank=state.bank;return state.bank}\n const locked=[...(state.lockedSquad||[])],lockedSet=new Set(locked),base=Number(state.lockedBank??state.bank??0);"
    n=html.count(old)
    if n!=1: raise RuntimeError(f'expected one bank helper anchor, found {n}')
    html=html.replace(old,new,1)
    repack(html)
    print('patched confirmed pre-GW1 bank repair')

if __name__=='__main__': main()
