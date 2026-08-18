from __future__ import annotations
import base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html);py=base64.b64decode(m.group(1)).decode('utf-8')
lines=py.splitlines();start=next(i for i,l in enumerate(lines) if l.startswith('def scan_first_team_squads'))
end=next(i for i in range(start+1,len(lines)) if lines[i].startswith('def '))
Path('_squad_current_v73.txt').write_text('\n'.join(f'{i+1:05d}: {lines[i]}' for i in range(start,end))+'\n')
print('wrote')
