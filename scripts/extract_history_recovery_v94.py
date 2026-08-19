from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m: raise RuntimeError('FM_PY_SOURCE_B64 missing')
py=base64.b64decode(m.group(1)).decode('utf-8')

def extract_top_def(name:str)->str:
    start=py.find(f'def {name}(')
    if start<0:return ''
    nxt=re.search(r'\n(?=def [A-Za-z_][A-Za-z0-9_]*\()',py[start+1:])
    end=(start+1+nxt.start()) if nxt else len(py)
    return py[start:end]

outdir=ROOT/'diagnostics';outdir.mkdir(exist_ok=True)
main=extract_top_def('recover_unlabelled_rich_members')
if not main: raise RuntimeError('history function missing')
(outdir/'history_recovery_v94.txt').write_text(main)

names=re.findall(r'^def ([A-Za-z_][A-Za-z0-9_]*)\(',py,re.M)
interesting=[n for n in names if any(k in n.lower() for k in ('rich','retain','match','fixture','date','header'))]
chunks=[]
for n in interesting:
    body=extract_top_def(n)
    if body:chunks.append('\n\n### '+n+'\n'+body)
(outdir/'history_helpers_v94.txt').write_text(''.join(chunks))
print('history recovery bytes',len(main),'helper defs',len(interesting))
