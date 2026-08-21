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

# v144 closes the third physical-boundary combination for the already-proven used-sub -> unused-bench
# metadata break. v141 supports that semantic bench break with a legacy >500-byte inter-team separator;
# v142 supports it with a compact 214..500-byte separator only when that separator is a local byte-gap
# outlier; and v123/v143 separately prove FM can serialize team arrays with ordinary contiguous spacing.
# Therefore used-sub -> unused-bench metadata + ordinary contiguous team boundary is still invisible.
# Preserve v141/v142 and add only this missing representation.
for prereq in [
    'def used_unused_bench_internal_spacing(rows):',
    'def used_unused_bench_gap_window(j,left_n,right_n):',
    'def used_unused_bench_compact_window(j,left_n,right_n):',
    'def starter_bench_contiguous_window(j,left_n,right_n):',
    "diagnostics['used_unused_bench_compact_candidate_pairs']+=1",
]:
    if prereq not in py:raise RuntimeError('v144 prerequisite missing: '+prereq)

func_start=py.find('def _rich_candidate_squad_pairs(')
if func_start<0:raise RuntimeError('v144 candidate-pair function missing')
func_end=py.find('\ndef ',func_start+1)
if func_end<0:func_end=len(py)
block=py[func_start:func_end]

helper_anchor='    def used_unused_bench_gap_window(j,left_n,right_n):\n'
helper_code="""    def used_unused_bench_contiguous_window(j,left_n,right_n):
        if j-left_n+1<0 or j+right_n>=len(stats):return None
        left=stats[j-left_n+1:j+1];right=stats[j+1:j+1+right_n]
        if len(left)!=left_n or len(right)!=right_n:return None
        team_gap=int(right[0]['offset'])-int(left[-1]['offset'])
        # This path owns ordinary physically contiguous team spacing. v141 keeps >500-byte team
        # separators and v142 keeps compact 214..500 separators that are local outliers.
        if team_gap<214 or team_gap>500:return None
        lok,lgap,lidx=used_unused_bench_internal_spacing(left)
        rok,rgap,ridx=used_unused_bench_internal_spacing(right)
        if not lok and not rok:return None

        # A side not using the special used->unused bench break must remain physically ordinary.
        for rows,ok in ((left,lok),(right,rok)):
            if ok:continue
            gaps=[int(rows[k+1]['offset'])-int(rows[k]['offset']) for k in range(len(rows)-1)]
            if any(g>=1500 for g in gaps):return None
        if not lineup_order_coherent(left) or not lineup_order_coherent(right):return None

        # Establish ordinary player-record spacing while excluding the one semantically validated
        # used-sub -> unused-bench metadata break. v144 only accepts a team boundary BELOW the local
        # outlier threshold; outlier compact boundaries stay owned by v142.
        ordinary=[]
        for rows,ok,sidx in ((left,lok,lidx),(right,rok,ridx)):
            for idx in range(len(rows)-1):
                g=int(rows[idx+1]['offset'])-int(rows[idx]['offset'])
                if ok and idx==sidx and g>=1500:continue
                ordinary.append(g)
        if not ordinary:return None
        ordered=sorted(ordinary);med=ordered[len(ordered)//2];q75=ordered[(3*len(ordered))//4]
        outlier_threshold=max(230,int(med*1.35),q75+16)
        if team_gap>=outlier_threshold:return None

        lp=[int(x.get('player_id',0) or 0) for x in left]
        rp=[int(x.get('player_id',0) or 0) for x in right]
        if any(x<=0 for x in lp+rp):return None
        if len(set(lp))!=len(lp) or len(set(rp))!=len(rp) or set(lp)&set(rp):return None
        return left,right

"""
if 'def used_unused_bench_contiguous_window(j,left_n,right_n):' not in block:
    if helper_anchor not in block:raise RuntimeError('v144 helper anchor missing')
    block=block.replace(helper_anchor,helper_code+helper_anchor,1)

return_marker='    return pairs\n'
loop="""    # v144: used-sub -> unused-bench metadata gap + ordinary contiguous inter-team spacing.
    if played_score_pairs:
        seen_v144={(int(l[0]['offset']),int(l[-1]['offset']),int(r[0]['offset']),int(r[-1]['offset'])) for l,r in pairs if l and r}
        for j in range(len(stats)-1):
            for left_n in range(18,23):
                for right_n in range(18,23):
                    pair=used_unused_bench_contiguous_window(j,left_n,right_n)
                    if not pair:continue
                    if agg(pair) not in played_score_pairs:continue
                    key=(int(pair[0][0]['offset']),int(pair[0][-1]['offset']),int(pair[1][0]['offset']),int(pair[1][-1]['offset']))
                    if key in seen_v144:continue
                    seen_v144.add(key);pairs.append(pair)
                    _lv,_lg,_li=used_unused_bench_internal_spacing(pair[0])
                    _rv,_rg,_ri=used_unused_bench_internal_spacing(pair[1])
                    diagnostics['used_unused_bench_contiguous_candidate_pairs']+=1
                    diagnostics['used_unused_bench_contiguous_left_gap_uses']+=int(bool(_lv))
                    diagnostics['used_unused_bench_contiguous_right_gap_uses']+=int(bool(_rv))
                    diagnostics['used_unused_bench_contiguous_max_internal_gap_bytes']=max(int(diagnostics.get('used_unused_bench_contiguous_max_internal_gap_bytes',0)),int(_lg or 0),int(_rg or 0))
                    diagnostics['used_unused_bench_contiguous_max_team_gap_bytes']=max(int(diagnostics.get('used_unused_bench_contiguous_max_team_gap_bytes',0)),int(pair[1][0]['offset'])-int(pair[0][-1]['offset']))
"""
if "diagnostics['used_unused_bench_contiguous_candidate_pairs']+=1" not in block:
    idx=block.rfind(return_marker)
    if idx<0:raise RuntimeError('v144 candidate return anchor missing')
    block=block[:idx]+loop+block[idx:]

py=py[:func_start]+block+py[func_end:]

if "'used_unused_bench_contiguous_candidate_pairs':0" not in py:
    anchor="'used_unused_bench_compact_candidate_pairs':0"
    if anchor not in py:raise RuntimeError('v144 diagnostics init anchor missing')
    extra=(anchor+",'used_unused_bench_contiguous_candidate_pairs':0"
           ",'used_unused_bench_contiguous_left_gap_uses':0"
           ",'used_unused_bench_contiguous_right_gap_uses':0"
           ",'used_unused_bench_contiguous_max_internal_gap_bytes':0"
           ",'used_unused_bench_contiguous_max_team_gap_bytes':0")
    py=py.replace(anchor,extra,1)

if 'unlabelled_rich_used_unused_bench_contiguous_candidate_pairs' not in py:
    anchor="'unlabelled_rich_used_unused_bench_compact_candidate_pairs':member_rich_diag.get('used_unused_bench_compact_candidate_pairs',0),"
    if anchor not in py:raise RuntimeError('v144 debug handoff anchor missing')
    extra=(anchor
           +"'unlabelled_rich_used_unused_bench_contiguous_candidate_pairs':member_rich_diag.get('used_unused_bench_contiguous_candidate_pairs',0),"
           +"'unlabelled_rich_used_unused_bench_contiguous_left_gap_uses':member_rich_diag.get('used_unused_bench_contiguous_left_gap_uses',0),"
           +"'unlabelled_rich_used_unused_bench_contiguous_right_gap_uses':member_rich_diag.get('used_unused_bench_contiguous_right_gap_uses',0),"
           +"'unlabelled_rich_used_unused_bench_contiguous_max_internal_gap_bytes':member_rich_diag.get('used_unused_bench_contiguous_max_internal_gap_bytes',0),"
           +"'unlabelled_rich_used_unused_bench_contiguous_max_team_gap_bytes':member_rich_diag.get('used_unused_bench_contiguous_max_team_gap_bytes',0),")
    py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def used_unused_bench_contiguous_window(j,left_n,right_n):',
    'if team_gap<214 or team_gap>500:return None',
    'if ok and idx==sidx and g>=1500:continue',
    'if team_gap>=outlier_threshold:return None',
    "if agg(pair) not in played_score_pairs:continue",
    "diagnostics['used_unused_bench_contiguous_candidate_pairs']+=1",
    'unlabelled_rich_used_unused_bench_contiguous_candidate_pairs',
    'def used_unused_bench_gap_window(j,left_n,right_n):',
    'def used_unused_bench_compact_window(j,left_n,right_n):',
]:assert token in cpy,token
print('v144 adds score-constrained used-sub/unused-bench metadata gap plus ordinary contiguous inter-team spacing while preserving v141/v142')
