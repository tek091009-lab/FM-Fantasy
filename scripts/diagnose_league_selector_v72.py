from __future__ import annotations
import base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
py=base64.b64decode(m.group(1)).decode() if m else ''
out=[]
def snip(label,text,needle,span=5000):
    i=text.find(needle);out.append(f'=== {label} ===\nindex={i}\n')
    if i>=0:out.append(text[max(0,i-span):i+span]+'\n')
for needle in ['League request:','captured before file selection','AUTO','Current season 2025/26 contains both supported English leagues','select_championship_fixtures','leagueSelect','competitionSelect','importLeague','requestedLeague','requested_league']:
    snip('HTML '+needle,html,needle,4000)
for needle in ['def select_championship_fixtures','contains both supported English leagues','requested_league','preferred_league','league_request']:
    snip('PY '+needle,py,needle,5000)
Path('_league_selector_diag.txt').write_text('\n'.join(out))
print('wrote diagnostic')
