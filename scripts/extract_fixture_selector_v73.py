from __future__ import annotations
import base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
py=base64.b64decode(m.group(1)).decode('utf-8') if m else ''
lines=py.splitlines()
def block(start_name,next_names):
    start=next((i for i,l in enumerate(lines) if l.startswith(start_name)),None)
    if start is None:return f'=== {start_name} NOT FOUND ===\n'
    end=len(lines)
    for i in range(start+1,len(lines)):
        if any(lines[i].startswith(n) for n in next_names):end=i;break
    return f'=== {start_name} lines {start+1}-{end} ===\n'+'\n'.join(f'{i+1:05d}: {lines[i]}' for i in range(start,end))+'\n'
out=[]
out.append(block('def _fixture_groups', ['def select_championship_fixtures','def ']))
out.append(block('def select_championship_fixtures', ['def ']))
for name in ['def scan_squads','def build_players','def browser_build_payload_from_fs']:
    out.append(block(name,['def ']))
Path('_fixture_selector_v73.txt').write_text('\n'.join(out))
print('wrote _fixture_selector_v73.txt')
