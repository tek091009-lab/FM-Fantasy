from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def reconstruct()->str:
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode('utf-8')

def repack(html:str)->None:
    packed=base64.b64encode(gzip.compress(html.encode('utf-8'),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks): p.write_text(c+'\n')

html=reconstruct()
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',html)
if not m: raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode('utf-8')

# v157 follows the same data-backed regression identified by v156. In a 79-result
# Championship save family, the older successful history run scanned 62 retained members
# and recovered 41 fresh rich matches from 15,724 player-stat rows / 612 candidate pairs.
# A newer run scans 59 members and explicitly blanket-skips exactly:
#   news.dat, play_fixture_manager.dat, player_stats.dat
# while falling to 2,437 rows / 54 pairs / 11 newly recovered unlabelled matches.
#
# v156 re-admits player_stats.dat first. v157 now re-admits ONLY
# play_fixture_manager.dat as the next isolated source experiment. The filename itself has
# ZERO evidential authority. Its bytes merely become eligible for the exact same
# GAME_MATCH_PLAYER_STATS structural parsing, side reconstruction, exact-score matching,
# authoritative fixture uniqueness and register_match() validation as every other member.
# news.dat intentionally remains excluded so the contribution of the two football-data
# members can be tested before admitting a likely high-noise news archive.

key='unlabelled_rich_non_retained_member_names'
pos=py.find(key)
if pos<0: raise RuntimeError('v157 non-retained diagnostic anchor missing')
fs=py.rfind('\ndef ',0,pos)
if fs<0: fs=py.rfind('def ',0,pos)
else: fs+=1
fe=py.find('\ndef ',pos)
if fe<0: fe=len(py)
block=py[fs:fe]
if 'play_fixture_manager.dat' not in block:
    raise RuntimeError('v157 play_fixture_manager.dat skip policy not found in recovery function')
if 'news.dat' not in block:
    raise RuntimeError('v157 expected news.dat to remain in non-retained policy')

orig=block
patterns=[
    ("'play_fixture_manager.dat',",''),
    (",'play_fixture_manager.dat'",''),
    ('"play_fixture_manager.dat",',''),
    (',"play_fixture_manager.dat"',''),
]
for a,b in patterns:
    block=block.replace(a,b)
block=re.sub(r"\s*or\s+[^\n;]*?==\s*['\"]play_fixture_manager\.dat['\"]",'',block)
block=re.sub(r"[^\n;]*?==\s*['\"]play_fixture_manager\.dat['\"]\s+or\s+",'',block)
if block==orig or 'play_fixture_manager.dat' in block:
    raise RuntimeError('v157 could not safely remove play_fixture_manager.dat from historical skip policy')

lines=block.splitlines(True)
indent='    '
if lines and lines[0].lstrip().startswith('def '):
    mm=re.match(r'(\s*)',lines[0]); base=mm.group(1) if mm else ''
    indent=base+'    '
marker=(indent+"globals()['_RICH_FIXTURE_MANAGER_MEMBER_READMITTED_V157']=1\n"+
        indent+"globals()['_RICH_FIXTURE_MANAGER_MEMBER_POLICY_V157']='structural-scan-only-no-source-trust'\n")
if "_RICH_FIXTURE_MANAGER_MEMBER_READMITTED_V157" not in block:
    lines.insert(1,marker)
    block=''.join(lines)

py=py[:fs]+block+py[fe:]

# Export source-admission diagnostics if the existing history-meta dictionary is available.
if 'unlabelled_rich_fixture_manager_member_readmitted_v157' not in py:
    anchors=["'unlabelled_rich_non_retained_members_skipped':","'unlabelled_rich_members_scanned':"]
    ap=next((py.find(a) for a in anchors if py.find(a)>=0),-1)
    if ap>=0:
        ls=py.rfind('\n',0,ap)+1
        le=py.find('\n',ap); le=len(py) if le<0 else le
        line=py[ls:le]
        ind=re.match(r'\s*',line).group(0)
        extra=(ind+"'unlabelled_rich_fixture_manager_member_readmitted_v157':bool(globals().get('_RICH_FIXTURE_MANAGER_MEMBER_READMITTED_V157',0)),\n"+
               ind+"'unlabelled_rich_fixture_manager_member_policy_v157':globals().get('_RICH_FIXTURE_MANAGER_MEMBER_POLICY_V157'),\n")
        py=py[:ls]+extra+py[ls:]

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct(); mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk); assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8'); compile(cpy,'fm_importer.py','exec')
pos=cpy.find(key); assert pos>=0
fs=cpy.rfind('\ndef ',0,pos); fs=fs+1 if fs>=0 else cpy.rfind('def ',0,pos)
fe=cpy.find('\ndef ',pos); fe=len(cpy) if fe<0 else fe
cblock=cpy[fs:fe]
assert 'play_fixture_manager.dat' not in cblock
assert 'news.dat' in cblock
assert "_RICH_FIXTURE_MANAGER_MEMBER_READMITTED_V157" in cblock
assert 'register_match' in cpy
print('v157 re-admits play_fixture_manager.dat to existing structural retained-history decoding; news.dat remains excluded and source name grants no match authority')