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

# v155 corrects v154's over-quarantine of the proven 145-byte GAME_MATCH_PLAYER_STATS core.
# Independent reverse-engineering of the original FM26 structure proves the fantasy-critical
# goalkeeper/defensive counters are already in the 145-byte core:
#   +21 goals_conceded
#   +50/+51/+52 save components (saves = their sum)
#   +55 blocks
#   +92/+93 tackles attempted/won
#   +97/+98 interception/clearance candidates
# plus goals, assists, cards, substitution minutes and rating.
#
# The bytes beyond the 145-byte core (+151/+152/+157 in the 214-byte representation) are useful
# extended diagnostics (possession won/lost candidates and shots_on_target_faced) but they are not
# required to reconstruct the fantasy match record because exact saves already live at +50..+52.
# v154 therefore threw away potentially valid historical matches unnecessarily. v155 restores the
# core-only rows to rich-history construction, while explicitly setting only the unavailable extended
# diagnostics to None so no fabricated zero survives.
for token in [
    'def _v150_core_record_at(raw,p):',
    "r['historical_stats_complete_v154']=False",
    "if bool(r.get('core_only_v150')):",
    "globals()['_RICH_CORE_ONLY_ROWS_QUARANTINED_V154']",
    "globals()['_RICH_HEADER_CORE_ONLY_ROWS_QUARANTINED_V154']",
    'def _v131_scan_stats(raw,start,end):',
]:
    if token not in py:raise RuntimeError('v155 prerequisite missing: '+token)

helper="""
def _v155_prepare_core_fantasy_row(r):
    r=dict(r)
    # Preserve proven core fantasy stats. Do not invent values for extended fields whose physical
    # bytes do not exist in a 145..157-byte object representation.
    for k in ('possession_won_candidate','possession_lost_candidate','shots_on_target_faced',
              'team_goals_conceded_while_on_pitch','shots_on_target_against_team',
              'total_shots_on_target_against_team'):
        if k in r:r[k]=None
    r['historical_stats_complete_v154']=False
    r['historical_fantasy_core_complete_v155']=True
    r['historical_extended_stats_complete_v155']=False
    r['missing_extended_fields_v155']=('possession_won_candidate','possession_lost_candidate','shots_on_target_faced')
    # These are independently mapped inside the 145-byte core and must remain authoritative.
    r['core_exact_goals_conceded_v155']=int(r.get('goals_conceded',0) or 0)
    r['core_exact_saves_v155']=int(r.get('saves',0) or 0)
    return r

"""
if 'def _v155_prepare_core_fantasy_row(r):' not in py:
    pos=py.find('def _v150_core_record_at(raw,p):')
    if pos<0:raise RuntimeError('v155 helper anchor missing')
    py=py[:pos]+helper+py[pos:]


def restore_scanner(block:str,append_expr:str,old_counter:str,new_counter:str)->str:
    if f"globals()['{new_counter}']" in block:return block
    start=block.find("                if bool(r.get('core_only_v150')):\n")
    if start<0:raise RuntimeError('v155 core-only guard missing for '+append_expr)
    end_marker='                '+append_expr+'\n'
    end=block.find(end_marker,start)
    if end<0:raise RuntimeError('v155 append marker missing for '+append_expr)
    # The v154 guard may continue at either a proven compact next offset or p+145. Keep exactly
    # that physical advance policy, but append the fantasy-complete core row first.
    guard=block[start:end]
    if "_v154_nxt" not in guard or "p+=145;continue" not in guard:
        raise RuntimeError('v155 unexpected v154 guard shape for '+append_expr)
    repl=("                if bool(r.get('core_only_v150')):\n"
          "                    r=_v155_prepare_core_fantasy_row(r)\n"
          f"                    globals()['{new_counter}']=int(globals().get('{new_counter}',0))+1\n"
          "                    globals()['_RICH_CORE_ONLY_MISSING_EXTENDED_FIELDS_V155']=('possession_won_candidate','possession_lost_candidate','shots_on_target_faced')\n"
          "                    "+append_expr+"\n"
          "                    _v154_nxt=None\n"
          "                    if '_v152_state_pair' in locals() and _v152_state_pair is not None:\n"
          "                        _v154_nxt=_v152_state_nxt\n"
          "                    elif '_v150_nxt' in locals() and _v150_nxt is not None:\n"
          "                        _v154_nxt=_v150_nxt\n"
          "                    if _v154_nxt is not None:\n"
          "                        p=int(_v154_nxt);continue\n"
          "                    p+=145;continue\n")
    return block[:start]+repl+block[end:]

# Restore the global retained-stat scanner.
pos=py.find("globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1")
if pos<0:raise RuntimeError('v155 global scanner marker missing')
fs=py.rfind('\ndef ',0,pos)
if fs<0:fs=py.rfind('def ',0,pos)
else:fs+=1
fe=py.find('\ndef ',pos)
if fe<0:fe=len(py)
g=py[fs:fe]
g=restore_scanner(g,'out.append(r)','_RICH_CORE_ONLY_ROWS_QUARANTINED_V154','_RICH_CORE_ONLY_ROWS_RESTORED_V155')
py=py[:fs]+g+py[fe:]

# Restore the header-first retained-stat scanner identically.
hs=py.find('def _v131_scan_stats(raw,start,end):')
if hs<0:raise RuntimeError('v155 header scanner missing')
he=py.find('\ndef ',hs+1)
if he<0:he=len(py)
h=py[hs:he]
h=restore_scanner(h,'rows.append(r)','_RICH_HEADER_CORE_ONLY_ROWS_QUARANTINED_V154','_RICH_HEADER_CORE_ONLY_ROWS_RESTORED_V155')
py=py[:hs]+h+py[he:]

# Export evidence so a raw-save rerun can immediately show whether this path contributes.
if 'unlabelled_rich_core_only_rows_restored_v155' not in py:
    anchors=[
        "'unlabelled_rich_core_only_rows_quarantined_v154':int(globals().get('_RICH_CORE_ONLY_ROWS_QUARANTINED_V154',0)),",
        "'unlabelled_rich_core_stride_transitions_v150':int(globals().get('_RICH_CORE_STRIDE_TRANSITIONS_V150',0)),",
    ]
    anchor=next((a for a in anchors if a in py),None)
    if anchor:
        extra=(anchor+
          "'unlabelled_rich_core_only_rows_restored_v155':int(globals().get('_RICH_CORE_ONLY_ROWS_RESTORED_V155',0)),"+
          "'unlabelled_rich_header_core_only_rows_restored_v155':int(globals().get('_RICH_HEADER_CORE_ONLY_ROWS_RESTORED_V155',0)),"+
          "'unlabelled_rich_core_only_missing_extended_fields_v155':list(globals().get('_RICH_CORE_ONLY_MISSING_EXTENDED_FIELDS_V155',())),")
        py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def _v155_prepare_core_fantasy_row(r):',
    "r['historical_fantasy_core_complete_v155']=True",
    "r['core_exact_goals_conceded_v155']",
    "r['core_exact_saves_v155']",
    "globals()['_RICH_CORE_ONLY_ROWS_RESTORED_V155']",
    "globals()['_RICH_HEADER_CORE_ONLY_ROWS_RESTORED_V155']",
    "out.append(r)",
    "rows.append(r)",
]:assert token in cpy,token
print('v155 restores proven 145-byte core rows to fantasy rich-history construction; exact core saves/goals-conceded are preserved while unavailable extended diagnostics remain None')
