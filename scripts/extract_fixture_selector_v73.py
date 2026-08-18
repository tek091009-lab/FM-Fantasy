from __future__ import annotations
import base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
py=base64.b64decode(m.group(1)).decode('utf-8') if m else ''
lines=py.splitlines()
def block(start_name):
    start=next((i for i,l in enumerate(lines) if l.startswith(start_name)),None)
    if start is None:return f'=== {start_name} NOT FOUND ===\n'
    end=len(lines)
    for i in range(start+1,len(lines)):
        if lines[i].startswith('def ') or lines[i].startswith('@dataclass') or lines[i].startswith('class '):end=i;break
    return f'=== {start_name} lines {start+1}-{end} ===\n'+'\n'.join(f'{i+1:05d}: {lines[i]}' for i in range(start,end))+'\n'
out=[]
for name in [
    'def scan_fixture_groups','def derive_fixture_to_club_shift','def select_championship_fixtures',
    'def scan_clubs','def find_squad_candidates','def extract_squads','def scan_squad','def build_players',
    'def browser_build_payload_from_fs'
]:out.append(block(name))
# Also locate every function name containing squad so we know the actual decoder names.
out.append('=== SQUAD FUNCTIONS ===\n'+'\n'.join(f'{i+1:05d}: {l}' for i,l in enumerate(lines) if l.startswith('def ') and 'squad' in l.lower())+'\n')
Path('_fixture_selector_v73.txt').write_text('\n'.join(out))
print('wrote _fixture_selector_v73.txt')
