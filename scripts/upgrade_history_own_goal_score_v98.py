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
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode('utf-8')

# v98: retained player rows already decode own_goals separately. A team's real final
# score therefore equals its credited player goals PLUS opponent own goals. The old
# score_of() path used only credited goals, so exact-score fixture binding could never
# recover a genuine own-goal match. Keep score_of() untouched for compatibility and add
# one history-specific score helper; blocks without own goals are byte-for-byte equivalent.
anchor="    def candidate_fixture_options(ci,leid,reid):\n"
helper="""    def historical_score_of(c):
        base_l,base_r=score_of(c)
        left=c.get('left',[]) or [];right=c.get('right',[]) or []
        left_og=sum(max(0,int(r.get('own_goals') or 0)) for r in left)
        right_og=sum(max(0,int(r.get('own_goals') or 0)) for r in right)
        if not left_og and not right_og:return base_l,base_r
        # score_of() is the credited-goal total for each retained side. Own goals are
        # credited to the opposing team, never to the player/team carrying own_goals.
        diagnostics['own_goal_score_candidates_seen']+=1
        return base_l+right_og,base_r+left_og

    def candidate_fixture_options(ci,leid,reid):
"""
if 'def historical_score_of(c):' not in py:
    if anchor not in py:raise RuntimeError('v98 score helper anchor missing')
    py=py.replace(anchor,helper,1)

# All retained-history fixture paths should share the corrected factual score. Do not
# change the underlying player stats or any non-history scoring logic.
# Replace direct candidate score reads, excluding the helper's call to legacy score_of().
needle='lscore,rscore=score_of(c)'
replacements=py.count(needle)
if replacements<3:
    raise RuntimeError(f'v98 expected multiple retained score reads, found {replacements}')
py=py.replace(needle,'lscore,rscore=historical_score_of(c)')

# Some registration code may unpack score_of(c) under different variable names. Patch
# only inside recover_unlabelled_rich_members(), leaving every other importer consumer alone.
start=py.find('def recover_unlabelled_rich_members(')
if start<0:raise RuntimeError('v98 recovery function missing')
end=py.find('\ndef ',start+4)
if end<0:end=len(py)
seg=py[start:end]
# Preserve helper self-call if it happens to lie in this range; swap remaining score_of(c)
# calls to the history-specific helper.
seg_lines=[]
in_helper=False
for line in seg.splitlines(True):
    if line.startswith('    def historical_score_of(c):'):in_helper=True
    elif in_helper and line.startswith('    def ') and not line.startswith('    def historical_score_of(c):'):in_helper=False
    if not in_helper:
        line=line.replace('score_of(c)','historical_score_of(c)')
    seg_lines.append(line)
newseg=''.join(seg_lines)
py=py[:start]+newseg+py[end:]

# Diagnostic counters + payload handoff.
diag_anchor="    diagnostics.setdefault('global_constraint_nonunique_components_rejected',0)\n"
diag_add=diag_anchor+"    diagnostics.setdefault('own_goal_score_candidates_seen',0)\n    diagnostics.setdefault('own_goal_score_fixture_matches',0)\n"
if "diagnostics.setdefault('own_goal_score_candidates_seen',0)" not in py:
    if diag_anchor not in py:raise RuntimeError('v98 diagnostic anchor missing')
    py=py.replace(diag_anchor,diag_add,1)

# Count accepted own-goal matches centrally: register_match sees the candidate after every
# decoder path has passed its normal identity/uniqueness safeguards.
reg_anchor="        used_fixtures.add(fid);used_candidates.add(ci)\n"
reg_add="        if any(int(r.get('own_goals') or 0)>0 for r in (left+right)):\n            diagnostics['own_goal_score_fixture_matches']+=1\n        used_fixtures.add(fid);used_candidates.add(ci)\n"
if "diagnostics['own_goal_score_fixture_matches']+=1" not in py:
    if reg_anchor not in py:raise RuntimeError('v98 register_match anchor missing')
    py=py.replace(reg_anchor,reg_add,1)

handoff_anchor="'unlabelled_rich_global_constraint_nonunique_components_rejected':member_rich_diag.get('global_constraint_nonunique_components_rejected',0),"
handoff=handoff_anchor+"'unlabelled_rich_own_goal_score_candidates_seen':member_rich_diag.get('own_goal_score_candidates_seen',0),'unlabelled_rich_own_goal_score_fixture_matches':member_rich_diag.get('own_goal_score_fixture_matches',0),"
if 'unlabelled_rich_own_goal_score_fixture_matches' not in py:
    if handoff_anchor not in py:raise RuntimeError('v98 diagnostic handoff anchor missing')
    py=py.replace(handoff_anchor,handoff,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode()
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for s in [
    'def historical_score_of(c):',
    'return base_l+right_og,base_r+left_og',
    "diagnostics['own_goal_score_candidates_seen']+=1",
    "diagnostics['own_goal_score_fixture_matches']+=1",
    'unlabelled_rich_own_goal_score_fixture_matches',
    'def confirmed_roster_global_constraint_pass():',
    'def confirmed_roster_one_side_pass():',
    'def confirmed_roster_fixture_pass():',
    'def confirmed_cohort_fixture_pass():',
    'def single_side_bridge_pass():'
]:assert s in cpy,s
# No history candidate path should still use the uncorrected direct score assignment.
recovery=cpy[cpy.find('def recover_unlabelled_rich_members('):]
assert 'lscore,rscore=score_of(c)' not in recovery
print('v98 own-goal-aware retained score recovery applied')
