from __future__ import annotations
import base64,gzip,re
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
    if ''.join(chunks)!=packed:
        raise RuntimeError('bundle split failed')
    for p,c in zip(PARTS,chunks):
        p.write_text(c+'\n')

def main()->None:
    html=reconstruct()
    start=html.index('function confirmTransfers()')
    end=html.find('\nfunction ',start+10)
    if end==-1:
        end=len(html)
    fn=html[start:end]
    pattern=re.compile(r'if\(Number\(state\.lastTransferRollGW\|\|0\)<gw\)\{[^{}]*\}')
    matches=pattern.findall(fn)
    if len(matches)!=1:
        raise RuntimeError(f'expected exactly one confirmTransfers rollover block, found {len(matches)}')
    patched_fn=pattern.sub('/* FT rollover is gameweek-boundary-only; confirmTransfers may only spend the persisted balance */',fn,count=1)
    if 'state.lastTransferRollGW=gw' in patched_fn:
        raise RuntimeError('confirmTransfers still mutates lastTransferRollGW')
    if 'state.freeTransfers' not in patched_fn:
        raise RuntimeError('confirmTransfers lost FT spending logic')
    html=html[:start]+patched_fn+html[end:]
    repack(html)
    print('removed client-side FT rollover from confirmTransfers')

if __name__=='__main__':
    main()

# production trigger 2026-08-21 v10
