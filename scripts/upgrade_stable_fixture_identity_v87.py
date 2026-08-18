from __future__ import annotations
import base64,gzip,re
from pathlib import Path

# v87: fixture identity must not depend on mutable schedule order.  In a validated
# supported double-round-robin league, each ordered home_tid -> away_tid pair is unique.
# Assign the public numeric fixture_id from that immutable pair ordering so a postponement,
# Gameweek relabel or date correction cannot renumber unrelated fixtures on the next save.
ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def reconstruct():
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')

def repack(html:str):
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    chunks += ['']*(len(PARTS)-len(chunks))
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')

html=reconstruct()
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m:raise RuntimeError('embedded importer missing')
py=base64.b64decode(m.group(1)).decode('utf-8')

old="""    fixture_name={tid:normalize_club_name(selected[tid-shift].short or selected[tid-shift].name) for tid in team_ids}
    for i,f in enumerate(sorted(fixtures,key=lambda x:(x['gameweek'],x['date'],x['home_tid'],x['away_tid'])),1):
        f['fixture_id']=i; f['home']=fixture_name[f['home_tid']]; f['away']=fixture_name[f['away_tid']]
"""
new="""    fixture_name={tid:normalize_club_name(selected[tid-shift].short or selected[tid-shift].name) for tid in team_ids}
    # v87: dates/Gameweeks are mutable when FM postpones or reschedules a match.  Never let
    # those fields determine fixture_id, otherwise a weekly save can renumber the season and
    # break monotonic history joins.  The selected league has already passed the exact full
    # double-round-robin shape check, so every ordered home_tid -> away_tid pair is unique.
    pair_keys=[(int(f['home_tid']),int(f['away_tid'])) for f in fixtures]
    if len(set(pair_keys))!=len(fixtures):
        raise RuntimeError('Current league fixture identity is not unique by ordered team pair; refusing mutable schedule-based IDs')
    for i,f in enumerate(sorted(fixtures,key=lambda x:(int(x['home_tid']),int(x['away_tid']))),1):
        f['fixture_id']=i
        f['stable_fixture_key']=f\"{fixture_info['season_start']}:{int(f['home_tid'])}>{int(f['away_tid'])}\"
        f['home']=fixture_name[f['home_tid']]; f['away']=fixture_name[f['away_tid']]
"""
if old not in py:
    if 'stable_fixture_key' in py and 'ordered team pair' in py:
        print('v87 already present');raise SystemExit(0)
    raise RuntimeError('legacy schedule-ordered fixture assignment not found')
py=py.replace(old,new,1)

needle="'historical_freeze_policy':'append-only-by-snapshot-date-v1'"
replacement="'historical_freeze_policy':'append-only-by-snapshot-date-v1','fixture_identity_policy':'ordered-team-pair-v87-stable-across-reschedule'"
if needle not in py:
    raise RuntimeError('meta insertion anchor missing')
py=py.replace(needle,replacement,1)

compile(py,'fm_importer_v87.py','exec')
for token in ['stable_fixture_key','ordered-team-pair-v87-stable-across-reschedule','refusing mutable schedule-based IDs']:
    if token not in py:raise RuntimeError('missing v87 token '+token)
if "sorted(fixtures,key=lambda x:(x['gameweek'],x['date'],x['home_tid'],x['away_tid']))" in py:
    raise RuntimeError('mutable schedule fixture-id assignment still present')

newb64=base64.b64encode(py.encode('utf-8')).decode()
html=html[:m.start(1)]+newb64+html[m.end(1):]
repack(html)
assert reconstruct()==html
print('v87 stable fixture identity applied')
