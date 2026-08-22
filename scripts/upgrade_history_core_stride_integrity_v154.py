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
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')

html=reconstruct()
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',html)
if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode('utf-8')

# v154 corrects a correctness flaw in v150-v153. The 145-byte core-only representation was
# zero-filling bytes 145..157 and then allowing those rows into normal rich-match construction.
# But the live GAME_MATCH_PLAYER_STATS parser uses those bytes for real fantasy-relevant values:
#   145 possession
#   146 team_goals_conceded_while_on_pitch
#   151 shots_on_target_against_team
#   152 total_shots_on_target_against_team
#   157 shots_on_target_faced (and goalkeeper saves are derived from this field)
# Therefore a core-only row is useful STRUCTURAL evidence (PID, goals/cards/substitution markers,
# rating etc.) but is NOT a complete historical player-stat row. It must never increase the rich
# history numerator or consume an authoritative fixture until the missing tail is decoded from a
# real representation. Preserve the short-stride detector as evidence, but quarantine those rows
# before they enter squad/match construction.
for token in [
    'def _v150_core_record_at(raw,p):',
    "r['core_only_v150']=True",
    'def _v152_core_stride_continue(raw,p,end,stride,last_pid=None):',
    "globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1",
    'def _v131_scan_stats(raw,start,end):',
]:
    if token not in py:raise RuntimeError('v154 prerequisite missing: '+token)

# Mark the incompleteness explicitly on every isolated 145-byte row. This is useful for diagnostics
# and protects future code from accidentally assuming core_only_v150 means complete rich history.
old="    r=dict(r);r['offset']=p;r['core_only_v150']=True\n    return r\n"
new=("    r=dict(r);r['offset']=p;r['core_only_v150']=True\n"
     "    r['historical_stats_complete_v154']=False\n"
     "    r['missing_tail_fields_v154']=('possession','team_goals_conceded_while_on_pitch','shots_on_target_against_team','total_shots_on_target_against_team','shots_on_target_faced','goalkeeper_saves')\n"
     "    return r\n")
if "historical_stats_complete_v154" not in py:
    if old not in py:raise RuntimeError('v154 core record marker anchor missing')
    py=py.replace(old,new,1)


def patch_scanner(block:str, append_expr:str, counter:str)->str:
    if f"globals()['{counter}']" in block:return block
    needle='                '+append_expr+'\n'
    if needle not in block:raise RuntimeError('v154 append anchor missing: '+append_expr)
    # Do not append incomplete rows to the rich-stat list. Advance using the already-proven compact
    # next offset where possible; otherwise resume byte scanning after the proven 145-byte core.
    # This deliberately preserves the normal >=158/full and v148 158..213 paths unchanged.
    guard=("                if bool(r.get('core_only_v150')):\n"
           f"                    globals()['{counter}']=int(globals().get('{counter}',0))+1\n"
           "                    globals()['_RICH_CORE_ONLY_MISSING_TAIL_FIELDS_V154']=('possession','team_goals_conceded_while_on_pitch','shots_on_target_against_team','total_shots_on_target_against_team','shots_on_target_faced','goalkeeper_saves')\n"
           "                    _v154_nxt=None\n"
           "                    if '_v152_state_pair' in locals() and _v152_state_pair is not None:\n"
           "                        _v154_nxt=_v152_state_nxt\n"
           "                    elif '_v150_nxt' in locals() and _v150_nxt is not None:\n"
           "                        _v154_nxt=_v150_nxt\n"
           "                    if _v154_nxt is not None:\n"
           "                        p=int(_v154_nxt);continue\n"
           "                    p+=145;continue\n"
           +needle)
    return block.replace(needle,guard,1)

# Global retained-stat scanner.
pos=py.find("globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1")
if pos<0:raise RuntimeError('v154 global scanner marker missing')
fs=py.rfind('\ndef ',0,pos)
if fs<0:fs=py.rfind('def ',0,pos)
else:fs+=1
fe=py.find('\ndef ',pos)
if fe<0:fe=len(py)
g=py[fs:fe]
g=patch_scanner(g,'out.append(r)','_RICH_CORE_ONLY_ROWS_QUARANTINED_V154')
py=py[:fs]+g+py[fe:]

# Header-first retained-stat scanner.
hs=py.find('def _v131_scan_stats(raw,start,end):')
if hs<0:raise RuntimeError('v154 header scanner missing')
he=py.find('\ndef ',hs+1)
if he<0:he=len(py)
h=py[hs:he]
h=patch_scanner(h,'rows.append(r)','_RICH_HEADER_CORE_ONLY_ROWS_QUARANTINED_V154')
py=py[:hs]+h+py[he:]

# Export evidence. A non-zero count means the 145..157 physical representation may genuinely exist,
# but it is not counted as recovered rich history until its bytes 145..157 are decoded correctly.
if 'unlabelled_rich_core_only_rows_quarantined_v154' not in py:
    anchors=[
        "'unlabelled_rich_core_stride_tail_rows_v152':int(globals().get('_RICH_CORE_STRIDE_TAIL_ROWS_V152',0)),",
        "'unlabelled_rich_core_stride_transitions_v150':int(globals().get('_RICH_CORE_STRIDE_TRANSITIONS_V150',0)),",
    ]
    anchor=next((a for a in anchors if a in py),None)
    if anchor:
        extra=(anchor+
          "'unlabelled_rich_core_only_rows_quarantined_v154':int(globals().get('_RICH_CORE_ONLY_ROWS_QUARANTINED_V154',0)),"+
          "'unlabelled_rich_header_core_only_rows_quarantined_v154':int(globals().get('_RICH_HEADER_CORE_ONLY_ROWS_QUARANTINED_V154',0)),"+
          "'unlabelled_rich_core_only_missing_tail_fields_v154':list(globals().get('_RICH_CORE_ONLY_MISSING_TAIL_FIELDS_V154',())),")
        py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    "r['historical_stats_complete_v154']=False",
    "'team_goals_conceded_while_on_pitch'",
    "'shots_on_target_faced'",
    "globals()['_RICH_CORE_ONLY_ROWS_QUARANTINED_V154']",
    "globals()['_RICH_HEADER_CORE_ONLY_ROWS_QUARANTINED_V154']",
    "if bool(r.get('core_only_v150')):",
    'def _v150_core_stride_next(raw,p,end):',
    'def _v152_core_stride_continue(raw,p,end,stride,last_pid=None):',
]:assert token in cpy,token
print('v154 quarantines 145-byte core-only rows from rich history because bytes 145..157 contain real defensive/GK stats; short-stride evidence is preserved without fabricating zeros')