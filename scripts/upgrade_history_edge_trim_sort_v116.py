from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def reconstruct():
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode()

def repack(html):
    packed=base64.b64encode(gzip.compress(html.encode(),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')

html=reconstruct();m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',html)
if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode()
if 'def confirmed_id_edge_trim_pair_pass():' not in py:
    raise RuntimeError('v116 prerequisite missing: v115 edge-trim decoder')

old="        proposals.sort(reverse=True);added=0\n        for _negtrim,_strength,ci,f,rev,leid,reid,ls,rs in proposals:\n"
new="        # v116: never let Python compare fixture dictionaries when two proposals have\n        # identical trim/support scores. Prefer fewer removed edge rows, then stronger\n        # confirmed-ID support, then deterministic lower candidate index.\n        proposals.sort(key=lambda x:(x[0],x[1],-x[2]),reverse=True);added=0\n        for _negtrim,_strength,ci,f,rev,leid,reid,ls,rs in proposals:\n"
if 'proposals.sort(key=lambda x:(x[0],x[1],-x[2]),reverse=True)' not in py:
    if old not in py:raise RuntimeError('v116 edge-trim sort anchor missing')
    py=py.replace(old,new,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
assert 'def confirmed_id_edge_trim_pair_pass():' in cpy
assert 'proposals.sort(key=lambda x:(x[0],x[1],-x[2]),reverse=True)' in cpy
assert 'proposals.sort(reverse=True);added=0' not in cpy
print('v116 deterministic edge-trim proposal ordering applied')