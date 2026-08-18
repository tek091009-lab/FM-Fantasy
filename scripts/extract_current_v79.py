from __future__ import annotations
import base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html); assert m
py=base64.b64decode(m.group(1)).decode('utf-8')
lines=py.splitlines()
blocks=[]
for name in ['read_squad_list_legacy','read_squad_list','_choose_current_squad_option_v75','scan_first_team_squads','_fixture_shift_current_squad_evidence','select_championship_fixtures','browser_build_payload_from_fs']:
    start=next(i for i,l in enumerate(lines) if l.startswith('def '+name))
    end=next((i for i in range(start+1,len(lines)) if lines[i].startswith('def ')),len(lines))
    blocks.append(f'===== {name} =====\n'+'\n'.join(f'{j+1:05d}: {lines[j]}' for j in range(start,end)))
Path('_current_importer_v79.txt').write_text('\n\n'.join(blocks)+'\n',encoding='utf-8')
print('wrote _current_importer_v79.txt')
