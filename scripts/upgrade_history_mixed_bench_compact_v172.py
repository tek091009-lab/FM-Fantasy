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

# v172: v171 proved from successful retained rows that used and unused bench players can be
# interleaved, and therefore permits one metadata gap anywhere inside a semantically valid mixed
# post-XI bench. v171 intentionally kept the legacy >500-byte inter-team boundary. Existing compact
# retained layouts (v122/v142/etc.) prove that FM can also place Team A and Team B only 214..500
# bytes apart. Preserve v171 and add the combined mixed-bench + compact-team-boundary representation.
for token in [
    'def mixed_bench_internal_spacing_v171(rows):',
    'def mixed_bench_gap_window_v171(j,left_n,right_n):',
    'def compact_window(j,left_n,right_n):',
    "diagnostics['mixed_bench_gap_candidate_pairs_v171']+=1",
    "if agg(pair) not in played_score_pairs:continue",
]:
    if token not in py:raise RuntimeError('v172 prerequisite missing: '+token)

func_start=py.find('def _rich_candidate_squad_pairs(')
if func_start<0:raise RuntimeError('v172 candidate-pair function missing')
func_end=py.find('\ndef ',func_start+1)
if func_end<0:func_end=len(py)
block=py[func_start:func_end]

helper_anchor='    def mixed_bench_gap_window_v171(j,left_n,right_n):\n'
helper_code="""    def mixed_bench_compact_window_v172(j,left_n,right_n):
        if j-left_n+1<0 or j+right_n>=len(stats):return None
        left=stats[j-left_n+1:j+1];right=stats[j+1:j+1+right_n]
        if len(left)!=left_n or len(right)!=right_n:return None
        team_gap=int(right[0]['offset'])-int(left[-1]['offset'])
        if team_gap<214 or team_gap>500:return None

        lok,lgap,lidx=mixed_bench_internal_spacing_v171(left)
        rok,rgap,ridx=mixed_bench_internal_spacing_v171(right)
        if not lok and not rok:return None

        # A side not using the mixed-bench metadata representation must remain structurally ordinary.
        for rows,ok in ((left,lok),(right,rok)):
            if ok:continue
            gaps=[int(rows[k+1]['offset'])-int(rows[k]['offset']) for k in range(len(rows)-1)]
            if any(g>=1500 for g in gaps):return None
            if not lineup_order_coherent(rows):return None

        # The compact A->B separator must itself be a local spacing outlier. Exclude only the one
        # semantically validated mixed-bench metadata break from the baseline; otherwise a multi-KiB
        # internal bench gap would make a genuine ~300-byte team separator look ordinary.
        ordinary=[]
        for rows,ok,sidx in ((left,lok,lidx),(right,rok,ridx)):
            for idx in range(len(rows)-1):
                g=int(rows[idx+1]['offset'])-int(rows[idx]['offset'])
                if ok and idx==sidx and g>=1500:continue
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
if 'def mixed_bench_compact_window_v172(j,left_n,right_n):' not in block:
    if helper_anchor not in block:raise RuntimeError('v172 helper insertion anchor missing')
    block=block.replace(helper_anchor,helper_code+helper_anchor,1)

return_marker='    return pairs\n'
loop="""    # v172: mixed post-XI bench metadata gap + compact 214..500 inter-team separator.
    if played_score_pairs:
        seen_v172={(int(l[0]['offset']),int(l[-1]['offset']),int(r[0]['offset']),int(r[-1]['offset'])) for l,r in pairs if l and r}
        for j in range(len(stats)-1):
            for left_n in range(18,23):
                for right_n in range(18,23):
                    pair=mixed_bench_compact_window_v172(j,left_n,right_n)
                    if not pair:continue
                    if agg(pair) not in played_score_pairs:continue
                    key=(int(pair[0][0]['offset']),int(pair[0][-1]['offset']),int(pair[1][0]['offset']),int(pair[1][-1]['offset']))
                    if key in seen_v172:continue
                    seen_v172.add(key);pairs.append(pair)
                    _lv,_lg,_li=mixed_bench_internal_spacing_v171(pair[0])
                    _rv,_rg,_ri=mixed_bench_internal_spacing_v171(pair[1])
                    diagnostics['mixed_bench_compact_candidate_pairs_v172']+=1
                    diagnostics['mixed_bench_compact_left_uses_v172']+=int(bool(_lv))
                    diagnostics['mixed_bench_compact_right_uses_v172']+=int(bool(_rv))
                    diagnostics['mixed_bench_compact_max_internal_gap_bytes_v172']=max(int(diagnostics.get('mixed_bench_compact_max_internal_gap_bytes_v172',0)),int(_lg or 0),int(_rg or 0))
                    diagnostics['mixed_bench_compact_max_team_gap_bytes_v172']=max(int(diagnostics.get('mixed_bench_compact_max_team_gap_bytes_v172',0)),int(pair[1][0]['offset'])-int(pair[0][-1]['offset']))
"""
if "diagnostics['mixed_bench_compact_candidate_pairs_v172']+=1" not in block:
    idx=block.rfind(return_marker)
    if idx<0:raise RuntimeError('v172 candidate return anchor missing')
    block=block[:idx]+loop+block[idx:]

py=py[:func_start]+block+py[func_end:]

if "'mixed_bench_compact_candidate_pairs_v172':0" not in py:
    anchor="'mixed_bench_gap_candidate_pairs_v171':0"
    if anchor not in py:raise RuntimeError('v172 diagnostics init anchor missing')
    extra=(anchor+",'mixed_bench_compact_candidate_pairs_v172':0"
           ",'mixed_bench_compact_left_uses_v172':0"
           ",'mixed_bench_compact_right_uses_v172':0"
           ",'mixed_bench_compact_max_internal_gap_bytes_v172':0"
           ",'mixed_bench_compact_max_team_gap_bytes_v172':0")
    py=py.replace(anchor,extra,1)

if 'unlabelled_rich_mixed_bench_compact_candidate_pairs_v172' not in py:
    anchor="'unlabelled_rich_mixed_bench_gap_candidate_pairs_v171':member_rich_diag.get('mixed_bench_gap_candidate_pairs_v171',0),"
    if anchor not in py:raise RuntimeError('v172 debug handoff anchor missing')
    extra=(anchor
           +"'unlabelled_rich_mixed_bench_compact_candidate_pairs_v172':member_rich_diag.get('mixed_bench_compact_candidate_pairs_v172',0),"
           +"'unlabelled_rich_mixed_bench_compact_left_uses_v172':member_rich_diag.get('mixed_bench_compact_left_uses_v172',0),"
           +"'unlabelled_rich_mixed_bench_compact_right_uses_v172':member_rich_diag.get('mixed_bench_compact_right_uses_v172',0),"
           +"'unlabelled_rich_mixed_bench_compact_max_internal_gap_bytes_v172':member_rich_diag.get('mixed_bench_compact_max_internal_gap_bytes_v172',0),"
           +"'unlabelled_rich_mixed_bench_compact_max_team_gap_bytes_v172':member_rich_diag.get('mixed_bench_compact_max_team_gap_bytes_v172',0),")
    py=py.replace(anchor,extra,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def mixed_bench_compact_window_v172(j,left_n,right_n):',
    'if team_gap<214 or team_gap>500:return None',
    'if ok and idx==sidx and g>=1500:continue',
    "if team_gap<max(230,int(med*1.35),q75+16):return None",
    "if agg(pair) not in played_score_pairs:continue",
    "diagnostics['mixed_bench_compact_candidate_pairs_v172']+=1",
    'unlabelled_rich_mixed_bench_compact_candidate_pairs_v172',
    'def mixed_bench_gap_window_v171(j,left_n,right_n):',
]:assert token in cpy,token
print('v172 adds score-constrained mixed-bench metadata-gap + compact inter-team boundary recovery while preserving v171 and all earlier layouts')
