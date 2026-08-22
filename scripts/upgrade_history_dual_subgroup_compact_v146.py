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

# v146 closes the next combined old-match layout. v145 accepts a complete retained side with BOTH
# natural internal subgroup breaks (XI->bench and used-sub->unused-bench), but deliberately keeps
# the legacy >500-byte Team A->Team B separator. v122/v140/v142 prove that other FM saves can use a
# compact 214..500-byte separator that is only visible as a local spacing outlier. Preserve v145 and
# all compact paths; add a separate dual-subgroup + compact-team-boundary representation.
for prereq in [
    'def _rich_candidate_squad_pairs(',
    'def dual_subgroup_internal_spacing(rows):',
    'def dual_subgroup_gap_window(j,left_n,right_n):',
    'def compact_window(j,left_n,right_n):',
    "diagnostics['dual_subgroup_gap_candidate_pairs']+=1",
    "globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1",
]:
    if prereq not in py:raise RuntimeError('v146 prerequisite missing: '+prereq)

func_start=py.find('def _rich_candidate_squad_pairs(')
if func_start<0:raise RuntimeError('v146 candidate-pair function missing')
func_end=py.find('\ndef ',func_start+1)
if func_end<0:func_end=len(py)
block=py[func_start:func_end]

helper_anchor='    def dual_subgroup_gap_window(j,left_n,right_n):\n'
helper_code="""    def dual_subgroup_compact_window(j,left_n,right_n):
        if j-left_n+1<0 or j+right_n>=len(stats):return None
        left=stats[j-left_n+1:j+1];right=stats[j+1:j+1+right_n]
        if len(left)!=left_n or len(right)!=right_n:return None
        team_gap=int(right[0]['offset'])-int(left[-1]['offset'])
        if team_gap<214 or team_gap>500:return None

        lok,lx,lb,li=dual_subgroup_internal_spacing(left)
        rok,rx,rb,ri=dual_subgroup_internal_spacing(right)
        if not lok and not rok:return None
        # A side not using the dual representation must remain ordinary here. Do not let this
        # combined path absorb some unrelated unexplained >=1500-byte internal corruption.
        for rows,ok in ((left,lok),(right,rok)):
            if ok:continue
            gaps=[int(rows[k+1]['offset'])-int(rows[k]['offset']) for k in range(len(rows)-1)]
            if any(g>=1500 for g in gaps):return None
        if not lineup_order_coherent(left) or not lineup_order_coherent(right):return None

        # Evaluate the compact Team A->Team B separator only against ORDINARY player-record spacing.
        # Exclude both permitted internal subgroup metadata gaps from the local baseline.
        ordinary=[]
        for rows,ok,bench_idx in ((left,lok,li),(right,rok,ri)):
            for idx in range(len(rows)-1):
                g=int(rows[idx+1]['offset'])-int(rows[idx]['offset'])
                if ok and idx in (10,bench_idx) and g>=1500:continue
                ordinary.append(g)
        if not ordinary:return None
        ordered=sorted(ordinary);med=ordered[len(ordered)//2];q75=ordered[(3*len(ordered))//4]
        if team_gap<max(230,int(med*1.35),q75+16):return None

        lp=[int(x.get('player_id',0) or 0) for x in left]
        rp=[int(x.get('player_id',0) or 0) for x in right]
        if any(x<=0 for x in lp+rp):return None
        if len(set(lp))!=len(lp) or len(set(rp))!=len(rp) or set(lp)&set(rp):return None
        return left,right

"""
if 'def dual_subgroup_compact_window(j,left_n,right_n):' not in block:
    if helper_anchor not in block:raise RuntimeError('v146 v145 helper anchor missing')
    block=block.replace(helper_anchor,helper_code+helper_anchor,1)

return_marker='    return pairs\n'
loop="""    # v146: dual XI->bench + used->unused metadata breaks with compact 214..500 team separator.
    if played_score_pairs:
        seen_v146={(int(l[0]['offset']),int(l[-1]['offset']),int(r[0]['offset']),int(r[-1]['offset'])) for l,r in pairs if l and r}
        for j in range(len(stats)-1):
            for left_n in range(18,23):
                for right_n in range(18,23):
                    pair=dual_subgroup_compact_window(j,left_n,right_n)
                    if not pair:continue
                    if agg(pair) not in played_score_pairs:continue
                    key=(int(pair[0][0]['offset']),int(pair[0][-1]['offset']),int(pair[1][0]['offset']),int(pair[1][-1]['offset']))
                    if key in seen_v146:continue
                    seen_v146.add(key);pairs.append(pair)
                    _lv,_lx,_lb,_li=dual_subgroup_internal_spacing(pair[0])
                    _rv,_rx,_rb,_ri=dual_subgroup_internal_spacing(pair[1])
                    diagnostics['dual_subgroup_compact_candidate_pairs']+=1
                    diagnostics['dual_subgroup_compact_left_uses']+=int(bool(_lv))
                    diagnostics['dual_subgroup_compact_right_uses']+=int(bool(_rv))
                    diagnostics['dual_subgroup_compact_max_team_gap_bytes']=max(int(diagnostics.get('dual_subgroup_compact_max_team_gap_bytes',0)),int(pair[1][0]['offset'])-int(pair[0][-1]['offset']))
                    diagnostics['dual_subgroup_compact_max_xi_bench_bytes']=max(int(diagnostics.get('dual_subgroup_compact_max_xi_bench_bytes',0)),int(_lx or 0),int(_rx or 0))
                    diagnostics['dual_subgroup_compact_max_used_unused_bytes']=max(int(diagnostics.get('dual_subgroup_compact_max_used_unused_bytes',0)),int(_lb or 0),int(_rb or 0))
"""
if "diagnostics['dual_subgroup_compact_candidate_pairs']+=1" not in block:
    idx=block.rfind(return_marker)
    if idx<0:raise RuntimeError('v146 candidate return anchor missing')
    block=block[:idx]+loop+block[idx:]

py=py[:func_start]+block+py[func_end:]

if "'dual_subgroup_compact_candidate_pairs':0" not in py:
    anchor="'dual_subgroup_gap_candidate_pairs':0"
    if anchor not in py:raise RuntimeError('v146 diagnostics init anchor missing')
    extra=(anchor+",'dual_subgroup_compact_candidate_pairs':0"
           ",'dual_subgroup_compact_left_uses':0"
           ",'dual_subgroup_compact_right_uses':0"
           ",'dual_subgroup_compact_max_team_gap_bytes':0"
           ",'dual_subgroup_compact_max_xi_bench_bytes':0"
           ",'dual_subgroup_compact_max_used_unused_bytes':0")
    py=py.replace(anchor,extra,1)

if 'unlabelled_rich_dual_subgroup_compact_candidate_pairs' not in py:
    anchor="'unlabelled_rich_dual_subgroup_gap_candidate_pairs':member_rich_diag.get('dual_subgroup_gap_candidate_pairs',0),"
    if anchor not in py:raise RuntimeError('v146 debug handoff anchor missing')
    extra=(anchor
           +"'unlabelled_rich_dual_subgroup_compact_candidate_pairs':member_rich_diag.get('dual_subgroup_compact_candidate_pairs',0),"
           +"'unlabelled_rich_dual_subgroup_compact_left_uses':member_rich_diag.get('dual_subgroup_compact_left_uses',0),"
           +"'unlabelled_rich_dual_subgroup_compact_right_uses':member_rich_diag.get('dual_subgroup_compact_right_uses',0),"
           +"'unlabelled_rich_dual_subgroup_compact_max_team_gap_bytes':member_rich_diag.get('dual_subgroup_compact_max_team_gap_bytes',0),"
           +"'unlabelled_rich_dual_subgroup_compact_max_xi_bench_bytes':member_rich_diag.get('dual_subgroup_compact_max_xi_bench_bytes',0),"
           +"'unlabelled_rich_dual_subgroup_compact_max_used_unused_bytes':member_rich_diag.get('dual_subgroup_compact_max_used_unused_bytes',0),")
    py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def dual_subgroup_compact_window(j,left_n,right_n):',
    'if team_gap<214 or team_gap>500:return None',
    'if ok and idx in (10,bench_idx) and g>=1500:continue',
    "team_gap<max(230,int(med*1.35),q75+16)",
    "if agg(pair) not in played_score_pairs:continue",
    "diagnostics['dual_subgroup_compact_candidate_pairs']+=1",
    'unlabelled_rich_dual_subgroup_compact_candidate_pairs',
    'def dual_subgroup_gap_window(j,left_n,right_n):',
]:assert token in cpy,token
print('v146 adds dual subgroup metadata breaks plus compact team-boundary representation while preserving v145 and earlier paths')
