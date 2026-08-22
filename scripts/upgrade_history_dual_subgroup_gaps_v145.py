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

# v145: the current physical-layout library supports one bounded metadata break at XI->bench
# (v139) OR one bounded break between used substitutes and unused bench (v141), but rejects a
# complete retained team array containing BOTH natural subgroup boundaries. FM can serialize
# starters, players-who-entered, and unused bench as three physical groups. In that layout every
# 214-byte player-stat row can be valid while all prior side builders reject the team because there
# are two >=1500-byte internal gaps. Preserve every existing path and add only this missing layout.
for prereq in [
    'def _rich_candidate_squad_pairs(',
    'def lineup_order_coherent(rows):',
    'def starter_bench_internal_spacing(rows):',
    'def used_unused_bench_internal_spacing(rows):',
    "'unrated_inactive_candidate':bool(unrated_inactive)",
    "diagnostics['used_unused_bench_contiguous_candidate_pairs']+=1",
    "globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1",
]:
    if prereq not in py:raise RuntimeError('v145 prerequisite missing: '+prereq)

func_start=py.find('def _rich_candidate_squad_pairs(')
if func_start<0:raise RuntimeError('v145 candidate-pair function missing')
func_end=py.find('\ndef ',func_start+1)
if func_end<0:func_end=len(py)
block=py[func_start:func_end]

helper_anchor='    def used_unused_bench_contiguous_window(j,left_n,right_n):\n'
helper_code="""    def dual_subgroup_internal_spacing(rows):
        # Accept exactly two bounded metadata breaks in a complete 18..22-player side:
        #   1) XI -> bench (record 11 -> 12; gap index 10)
        #   2) used substitutes -> unused bench (a later bench gap)
        if not (18<=len(rows)<=22):return False,0,0,-1
        gaps=[int(rows[k+1]['offset'])-int(rows[k]['offset']) for k in range(len(rows)-1)]
        if any(g<214 for g in gaps):return False,0,0,-1
        large=[(idx,g) for idx,g in enumerate(gaps) if g>=1500]
        if len(large)!=2:return False,0,0,-1
        if large[0][0]!=10 or large[1][0]<11:return False,0,0,-1
        xi_gap=int(large[0][1]);bench_idx=int(large[1][0]);bench_gap=int(large[1][1])
        if xi_gap>16384 or bench_gap>16384:return False,0,0,-1

        def inactive_bench(r):
            if int(r.get('sub_on',0) or 0)>0:return False
            if r.get('unrated_inactive_candidate'):return True
            keys=('goals','assists','yellow_cards','red_cards','passes_attempted','shots_on_target',
                  'shots_blocked','saves','blocks','tackles_attempted','headers_attempted')
            if int(r.get('sub_off',0) or 0)>0:return False
            return not any(int(r.get(k,0) or 0)>0 for k in keys)

        used=rows[11:bench_idx+1];unused=rows[bench_idx+1:]
        if not used or not unused:return False,0,0,-1
        if not all(int(r.get('sub_on',0) or 0)>0 for r in used):return False,0,0,-1
        if not all(inactive_bench(r) for r in unused):return False,0,0,-1

        ordinary=[g for idx,g in enumerate(gaps) if idx not in (10,bench_idx)]
        if any(g>=1500 for g in ordinary):return False,0,0,-1
        if ordinary:
            ordered=sorted(ordinary);med=ordered[len(ordered)//2];q75=ordered[(3*len(ordered))//4]
            floor=max(1500,int(med*2.0),q75+512)
            if xi_gap<floor or bench_gap<floor:return False,0,0,-1
        return True,xi_gap,bench_gap,bench_idx

    def dual_subgroup_gap_window(j,left_n,right_n):
        if j-left_n+1<0 or j+right_n>=len(stats):return None
        left=stats[j-left_n+1:j+1];right=stats[j+1:j+1+right_n]
        if len(left)!=left_n or len(right)!=right_n:return None
        # v145 changes only the INTERNAL grouping. Keep the established large inter-team separator;
        # compact/contiguous combinations can remain separate follow-up representations if observed.
        team_gap=int(right[0]['offset'])-int(left[-1]['offset'])
        if team_gap<=500:return None
        lok,lx,lb,li=dual_subgroup_internal_spacing(left)
        rok,rx,rb,ri=dual_subgroup_internal_spacing(right)
        if not lok and not rok:return None
        # A side not using v145 must remain an ordinary full 18..22-player array here. Do not use
        # this decoder to smuggle through some unrelated unexplained internal >=1500-byte gap.
        for rows,ok in ((left,lok),(right,rok)):
            if ok:continue
            gaps=[int(rows[k+1]['offset'])-int(rows[k]['offset']) for k in range(len(rows)-1)]
            if any(g>=1500 for g in gaps):return None
        if not lineup_order_coherent(left) or not lineup_order_coherent(right):return None
        lp=[int(x.get('player_id',0) or 0) for x in left]
        rp=[int(x.get('player_id',0) or 0) for x in right]
        if any(x<=0 for x in lp+rp):return None
        if len(set(lp))!=len(lp) or len(set(rp))!=len(rp) or set(lp)&set(rp):return None
        return left,right

"""
if 'def dual_subgroup_gap_window(j,left_n,right_n):' not in block:
    if helper_anchor not in block:raise RuntimeError('v145 helper anchor missing')
    block=block.replace(helper_anchor,helper_code+helper_anchor,1)

return_marker='    return pairs\n'
loop="""    # v145: starters -> metadata -> used substitutes -> metadata -> unused bench.
    if played_score_pairs:
        seen_v145={(int(l[0]['offset']),int(l[-1]['offset']),int(r[0]['offset']),int(r[-1]['offset'])) for l,r in pairs if l and r}
        for j in range(len(stats)-1):
            for left_n in range(18,23):
                for right_n in range(18,23):
                    pair=dual_subgroup_gap_window(j,left_n,right_n)
                    if not pair:continue
                    if agg(pair) not in played_score_pairs:continue
                    key=(int(pair[0][0]['offset']),int(pair[0][-1]['offset']),int(pair[1][0]['offset']),int(pair[1][-1]['offset']))
                    if key in seen_v145:continue
                    seen_v145.add(key);pairs.append(pair)
                    _lv,_lx,_lb,_li=dual_subgroup_internal_spacing(pair[0])
                    _rv,_rx,_rb,_ri=dual_subgroup_internal_spacing(pair[1])
                    diagnostics['dual_subgroup_gap_candidate_pairs']+=1
                    diagnostics['dual_subgroup_gap_left_uses']+=int(bool(_lv))
                    diagnostics['dual_subgroup_gap_right_uses']+=int(bool(_rv))
                    diagnostics['dual_subgroup_gap_max_xi_bench_bytes']=max(int(diagnostics.get('dual_subgroup_gap_max_xi_bench_bytes',0)),int(_lx or 0),int(_rx or 0))
                    diagnostics['dual_subgroup_gap_max_used_unused_bytes']=max(int(diagnostics.get('dual_subgroup_gap_max_used_unused_bytes',0)),int(_lb or 0),int(_rb or 0))
"""
if "diagnostics['dual_subgroup_gap_candidate_pairs']+=1" not in block:
    idx=block.rfind(return_marker)
    if idx<0:raise RuntimeError('v145 candidate return anchor missing')
    block=block[:idx]+loop+block[idx:]

py=py[:func_start]+block+py[func_end:]

if "'dual_subgroup_gap_candidate_pairs':0" not in py:
    anchor="'used_unused_bench_contiguous_candidate_pairs':0"
    if anchor not in py:raise RuntimeError('v145 diagnostics init anchor missing')
    extra=(anchor+",'dual_subgroup_gap_candidate_pairs':0"
           ",'dual_subgroup_gap_left_uses':0"
           ",'dual_subgroup_gap_right_uses':0"
           ",'dual_subgroup_gap_max_xi_bench_bytes':0"
           ",'dual_subgroup_gap_max_used_unused_bytes':0")
    py=py.replace(anchor,extra,1)

if 'unlabelled_rich_dual_subgroup_gap_candidate_pairs' not in py:
    anchor="'unlabelled_rich_used_unused_bench_contiguous_candidate_pairs':member_rich_diag.get('used_unused_bench_contiguous_candidate_pairs',0),"
    if anchor not in py:raise RuntimeError('v145 debug handoff anchor missing')
    extra=(anchor
           +"'unlabelled_rich_dual_subgroup_gap_candidate_pairs':member_rich_diag.get('dual_subgroup_gap_candidate_pairs',0),"
           +"'unlabelled_rich_dual_subgroup_gap_left_uses':member_rich_diag.get('dual_subgroup_gap_left_uses',0),"
           +"'unlabelled_rich_dual_subgroup_gap_right_uses':member_rich_diag.get('dual_subgroup_gap_right_uses',0),"
           +"'unlabelled_rich_dual_subgroup_gap_max_xi_bench_bytes':member_rich_diag.get('dual_subgroup_gap_max_xi_bench_bytes',0),"
           +"'unlabelled_rich_dual_subgroup_gap_max_used_unused_bytes':member_rich_diag.get('dual_subgroup_gap_max_used_unused_bytes',0),")
    py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def dual_subgroup_internal_spacing(rows):',
    'if large[0][0]!=10 or large[1][0]<11:return False,0,0,-1',
    "if not all(int(r.get('sub_on',0) or 0)>0 for r in used):return False,0,0,-1",
    'if not all(inactive_bench(r) for r in unused):return False,0,0,-1',
    'def dual_subgroup_gap_window(j,left_n,right_n):',
    'if team_gap<=500:return None',
    "if agg(pair) not in played_score_pairs:continue",
    "diagnostics['dual_subgroup_gap_candidate_pairs']+=1",
    'unlabelled_rich_dual_subgroup_gap_candidate_pairs',
    'def used_unused_bench_contiguous_window(j,left_n,right_n):',
]:assert token in cpy,token
print('v145 adds score-constrained retained sides with BOTH XI->bench and used-sub->unused-bench metadata breaks while preserving all earlier layouts')
