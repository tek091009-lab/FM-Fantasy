from __future__ import annotations
import base64,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]
html=gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
py=base64.b64decode(m.group(1)).decode() if m else ''
out=[]
def block(label,text,needle,before=2500,after=4500):
    i=text.find(needle);out.append(f'=== {label} ===\nindex={i}')
    if i<0:return
    s=text[max(0,i-before):min(len(text),i+after)]
    # make minified HTML/JS readable enough for connector output
    for sep in [';','{','}']:
        s=s.replace(sep,sep+'\n')
    out.append(s)
for needle in [
 'id="leagueImportPreference"',
 "$('leagueImportPreference')",
 'FM_PENDING_SEASON_LEAGUE',
 "msg.includes('Multiple supported English league seasons')",
 "seasonImportBtn').addEventListener",
 "updateImportBtn').addEventListener",
 'sendFMImport(',
 'function refreshCompetitionUI',
]: block('HTML '+needle,html,needle)
for needle in ['def select_championship_fixtures','contains both supported English leagues','preferred_league','league_preference']:
    block('PY '+needle,py,needle,2000,5000)
Path('_league_selector_diag.txt').write_text('\n\n'.join(out))
print('wrote expanded diagnostic')
