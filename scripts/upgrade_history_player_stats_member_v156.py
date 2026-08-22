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

# v156 fixes a data-backed regression in historical match candidate admission.
# A newer real import of the same 79-result Championship save family explicitly reports
# player_stats.dat among only three members skipped as "non-retained" and then sees just
# 2,437 stat rows / 54 candidate pairs, versus an older run that scanned three more members
# and saw 15,724 stat rows / 612 candidate pairs. The source filename must never be used as
# proof that a match is valid, but player_stats.dat is too directly relevant to old player
# history to blanket-exclude before the existing structural GAME_MATCH_PLAYER_STATS decoders.
#
# Policy: re-admit ONLY player_stats.dat to the existing unlabelled retained-history scanner.
# It receives no special trust: every row, side, score and fixture must still pass the normal
# structural parsers and authoritative register_match() chain. news.dat and
# play_fixture_manager.dat remain excluded by the current policy.

# Find the recovery function containing the diagnostic key. This deliberately scopes the patch
# to historical retained-member admission and avoids replacing unrelated mentions elsewhere.
key='unlabelled_rich_non_retained_member_names'
pos=py.find(key)
if pos<0: raise RuntimeError('v156 non-retained diagnostic anchor missing')
fs=py.rfind('\ndef ',0,pos)
if fs<0: fs=py.rfind('def ',0,pos)
else: fs+=1
fe=py.find('\ndef ',pos)
if fe<0: fe=len(py)
block=py[fs:fe]
if 'player_stats.dat' not in block:
    raise RuntimeError('v156 player_stats.dat skip policy not found in recovery function')

# Prefer removing player_stats.dat from a literal deny-list/set/tuple. The exact code shape has
# evolved, so use bounded replacements only inside this function. We require news.dat and/or
# play_fixture_manager.dat to remain nearby, proving this is the intended non-retained policy.
if 'news.dat' not in block and 'play_fixture_manager.dat' not in block:
    raise RuntimeError('v156 expected companion non-retained member names missing')

orig=block
patterns=[
    ("'player_stats.dat',",''),
    (",'player_stats.dat'",''),
    ('"player_stats.dat",',''),
    (',"player_stats.dat"',''),
]
for a,b in patterns:
    block=block.replace(a,b)

# If the source used a direct equality clause instead of a collection, remove only that clause.
block=re.sub(r"\s*or\s+[^\n;]*?==\s*['\"]player_stats\.dat['\"]",'',block)
block=re.sub(r"[^\n;]*?==\s*['\"]player_stats\.dat['\"]\s+or\s+",'',block)

if block==orig or 'player_stats.dat' in block:
    # Do not silently weaken some unknown future code shape.
    raise RuntimeError('v156 could not safely remove player_stats.dat from historical skip policy')

# Add an explicit policy marker immediately inside the same function for debug/audit. This marker
# does not affect matching decisions.
lines=block.splitlines(True)
insert_at=1
indent='    '
if lines and lines[0].lstrip().startswith('def '):
    m_indent=re.match(r'(\s*)',lines[0]); base=m_indent.group(1) if m_indent else ''
    indent=base+'    '
marker=(indent+"globals()['_RICH_PLAYER_STATS_MEMBER_READMITTED_V156']=1\n"+
        indent+"globals()['_RICH_PLAYER_STATS_MEMBER_POLICY_V156']='structural-scan-only-no-source-trust'\n")
if "_RICH_PLAYER_STATS_MEMBER_READMITTED_V156" not in block:
    lines.insert(insert_at,marker)
    block=''.join(lines)

py=py[:fs]+block+py[fe:]

# Export diagnostics if an existing history-meta dictionary anchor is available.
if 'unlabelled_rich_player_stats_member_readmitted_v156' not in py:
    anchors=[
        "'unlabelled_rich_non_retained_members_skipped':",
        "'unlabelled_rich_members_scanned':",
    ]
    ap=next((py.find(a) for a in anchors if py.find(a)>=0),-1)
    if ap>=0:
        line_start=py.rfind('\n',0,ap)+1
        line_end=py.find('\n',ap)
        if line_end<0: line_end=len(py)
        line=py[line_start:line_end]
        indent2=re.match(r'\s*',line).group(0)
        extra=(indent2+"'unlabelled_rich_player_stats_member_readmitted_v156':bool(globals().get('_RICH_PLAYER_STATS_MEMBER_READMITTED_V156',0)),\n"+
               indent2+"'unlabelled_rich_player_stats_member_policy_v156':globals().get('_RICH_PLAYER_STATS_MEMBER_POLICY_V156'),\n")
        py=py[:line_start]+extra+py[line_start:]

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
assert 'player_stats.dat' not in cblock
assert 'news.dat' in cblock or 'play_fixture_manager.dat' in cblock
assert "_RICH_PLAYER_STATS_MEMBER_READMITTED_V156" in cblock
assert 'register_match' in cpy
print('v156 re-admits player_stats.dat to the existing structural retained-history scanner; source name grants no match trust and all existing fixture validation remains authoritative')
