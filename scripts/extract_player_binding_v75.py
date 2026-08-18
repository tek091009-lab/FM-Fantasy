from __future__ import annotations
import base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html);assert m
py=base64.b64decode(m.group(1)).decode('utf-8')
chunks=[]
for name,nextname in [('bind_target_people','def _rich_stat_record_at'),('browser_build_payload_from_fs','')]:
    s=py.index('def '+name)
    if nextname:
        e=py.index(nextname,s)
    else:
        e=min(len(py),s+18000)
    chunks.append(py[s:e])
Path('_player_binding_v75.txt').write_text('\n\n=====\n\n'.join(chunks))
print('wrote player binding')
