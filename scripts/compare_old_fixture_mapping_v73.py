from __future__ import annotations
import base64,gzip,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OLD='2e0f04196745b9406b97fd55ffa26c21c8a7d3fb'
PART_NAMES=[f'app/part{i:02d}' for i in range(17)]+[f'app/fix{i}' for i in range(17,21)]
def gitshow(path):
    return subprocess.check_output(['git','show',f'{OLD}:{path}'],cwd=ROOT,text=True).strip()
html=gzip.decompress(base64.b64decode(''.join(gitshow(p) for p in PART_NAMES))).decode('utf-8')
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
for name in ['def scan_fixture_groups','def derive_fixture_to_club_shift','def select_championship_fixtures','def scan_first_team_squads','def browser_build_payload_from_fs']:
    out.append(block(name))
Path('_old_fixture_mapping_v73.txt').write_text('\n'.join(out))
print('wrote old mapping diagnostic')
