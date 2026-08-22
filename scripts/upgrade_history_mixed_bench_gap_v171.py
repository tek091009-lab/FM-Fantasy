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

# v171: successful decoded rows prove that FM does NOT always order the bench as
# "all used substitutes, then all unused substitutes". In real retained output, used and unused
# bench players can be interleaved after the starting XI. v141/v142/v144 therefore miss a valid
# serialization when metadata/padding splits the bench at a point where BOTH sides of the gap contain
# a mixture of used and unused bench rows. Preserve those semantic-specific paths, and add a separate
# representation that permits exactly one bounded large gap anywhere INSIDE the post-XI bench as long
# as every post-XI row is independently bench-like (used substitute OR inactive/unused).

for token in [
    'def _rich_candidate_squad_pairs(',
    'def lineup_order_coherent(rows):',
    'def used_unused_bench_internal_spacing(rows):',
    "'unrated_inactive_candidate':bool(unrated_inactive)",
    "if agg(pair) not in played_score_pairs:continue",
]:
    if token not in py:raise RuntimeError('v171 prerequisite missing: '+token)

func_start=py.find('def _rich_candidate_squad_pairs(')
if func_start<0:raise RuntimeError('v171 candidate-pair function missing')
func_end=py.find('\ndef ',func_start+1)
if func_end<0:func_end=len(py)
block=py[func_start:func_end]

helper_anchor='    def used_unused_bench_internal_spacing(rows):\n'
helper_code="""    def mixed_bench_internal_spacing_v171(rows):
        # Full matchday-array representation only. v171 is intentionally narrower than a generic
        # "allow one big gap" rule: the gap must be wholly inside the bench (after row 11), while
        # every post-XI row must independently look like either a used substitute or inactive bench.
        if not (18<=len(rows)<=22):return False,0,-1
        if not lineup_order_coherent(rows):return False,0,-1
        gaps=[int(rows[k+1]['offset'])-int(rows[k]['offset']) for k in range(len(rows)-1)]
        if any(g<214 for g in gaps):return False,0,-1

        def inactive_bench_v171(r):
            if int(r.get('sub_on',0) or 0)>0:return False
            if int(r.get('sub_off',0) or 0)>0:return False
            if r.get('unrated_inactive_candidate'):return True
            keys=('goals','assists','yellow_cards','red_cards','passes_attempted','shots_on_target',
                  'shots_blocked','saves','blocks','tackles_attempted','headers_attempted')
            return not any(int(r.get(k,0) or 0)>0 for k in keys)

        def benchish_v171(r):
            return int(r.get('sub_on',0) or 0)>0 or inactive_bench_v171(r)

        # All records after the starting XI must be explicable as bench records. Do not infer a
        # boundary from a player row whose match role is itself unclear.
        if not rows[11:] or not all(benchish_v171(r) for r in rows[11:]):return False,0,-1

        special=[];ordinary=[]
        for idx,g in enumerate(gaps):
            if g>=1500:
                # idx=10 is XI->bench and belongs to v139/v140/v143. v171 owns only a gap between
                # two bench rows, therefore idx must be >=11 and both resulting bench groups nonempty.
                if idx<11:return False,0,-1
                special.append((idx,g))
            else:ordinary.append(g)
        if len(special)!=1:return False,0,-1
        idx,g=special[0]
        if g>16384:return False,0,-1
        if not rows[11:idx+1] or not rows[idx+1:]:return False,0,-1

        # Critical difference from v141: DO NOT require used rows before the gap and unused rows after
        # it. Real decoded retained rows show those roles can be interleaved. We require only that both
        # groups are valid bench records and that the physical break is a strong spacing outlier.
        if ordinary:
            ordered=sorted(ordinary);med=ordered[len(ordered)//2];q75=ordered[(3*len(ordered))//4]
            if g<max(1500,int(med*2.0),q75+512):return False,0,-1
        return True,g,idx

    def mixed_bench_gap_window_v171(j,left_n,right_n):
        if j-left_n+1<0 or j+right_n>=len(stats):return None
        left=stats[j-left_n+1:j+1];right=stats[j+1:j+1+right_n]
        if len(left)!=left_n or len(right)!=right_n:return None
        # First version changes one dimension only: retain the established large inter-team boundary.
        team_gap=int(right[0]['offset'])-int(left[-1]['offset'])
        if team_gap<=500:return None
        lok,lgap,lidx=mixed_bench_internal_spacing_v171(left)
        rok,rgap,ridx=mixed_bench_internal_spacing_v171(right)
        if not lok and not rok:return None
        # A side not using v171 must remain structurally ordinary; another unexplained large gap is
        # never silently accepted.
        if not lok:
            gg=[int(left[k+1]['offset'])-int(left[k]['offset']) for k in range(len(left)-1)]
            if any(g>=1500 for g in gg):return None
        if not rok:
            gg=[int(right[k+1]['offset'])-int(right[k]['offset']) for k in range(len(right)-1)]
            if any(g>=1500 for g in gg):return None
        lp=[int(x.get('player_id',0) or 0) for x in left]
        rp=[int(x.get('player_id',0) or 0) for x in right]
        if any(x<=0 for x in lp+rp):return None
        if len(set(lp))!=len(lp) or len(set(rp))!=len(rp) or set(lp)&set(rp):return None
        return left,right

"""
if 'def mixed_bench_gap_window_v171(j,left_n,right_n):' not in block:
    if helper_anchor not in block:raise RuntimeError('v171 helper insertion anchor missing')
    block=block.replace(helper_anchor,helper_code+helper_anchor,1)

return_marker='    return pairs\n'
loop="""    # v171: one metadata/padding gap anywhere inside an otherwise coherent MIXED bench.
    # This is backed by successful decoded historical rows where used and unused bench players are
    # interleaved, so v141's used->unused ordering is not a universal serialization rule.
    if played_score_pairs:
        seen_v171={(int(l[0]['offset']),int(l[-1]['offset']),int(r[0]['offset']),int(r[-1]['offset'])) for l,r in pairs if l and r}
        for j in range(len(stats)-1):
            for left_n in range(18,23):
                for right_n in range(18,23):
                    pair=mixed_bench_gap_window_v171(j,left_n,right_n)
                    if not pair:continue
                    if agg(pair) not in played_score_pairs:continue
                    key=(int(pair[0][0]['offset']),int(pair[0][-1]['offset']),int(pair[1][0]['offset']),int(pair[1][-1]['offset']))
                    if key in seen_v171:continue
                    seen_v171.add(key);pairs.append(pair)
                    _lv,_lg,_li=mixed_bench_internal_spacing_v171(pair[0])
                    _rv,_rg,_ri=mixed_bench_internal_spacing_v171(pair[1])
                    diagnostics['mixed_bench_gap_candidate_pairs_v171']+=1
                    diagnostics['mixed_bench_gap_left_uses_v171']+=int(bool(_lv))
                    diagnostics['mixed_bench_gap_right_uses_v171']+=int(bool(_rv))
                    diagnostics['mixed_bench_gap_max_bytes_v171']=max(int(diagnostics.get('mixed_bench_gap_max_bytes_v171',0)),int(_lg or 0),int(_rg or 0))
"""
if "diagnostics['mixed_bench_gap_candidate_pairs_v171']+=1" not in block:
    idx=block.rfind(return_marker)
    if idx<0:raise RuntimeError('v171 candidate return anchor missing')
    block=block[:idx]+loop+block[idx:]

py=py[:func_start]+block+py[func_end:]

if "'mixed_bench_gap_candidate_pairs_v171':0" not in py:
    anchors=["'used_unused_bench_gap_candidate_pairs':0","'starter_bench_internal_gap_candidate_pairs':0"]
    for anchor in anchors:
        if anchor in py:
            extra=(anchor+",'mixed_bench_gap_candidate_pairs_v171':0"
                   ",'mixed_bench_gap_left_uses_v171':0"
                   ",'mixed_bench_gap_right_uses_v171':0"
                   ",'mixed_bench_gap_max_bytes_v171':0")
            py=py.replace(anchor,extra,1);break
    else:raise RuntimeError('v171 diagnostics init anchor missing')

if 'unlabelled_rich_mixed_bench_gap_candidate_pairs_v171' not in py:
    anchors=[
        "'unlabelled_rich_used_unused_bench_gap_candidate_pairs':member_rich_diag.get('used_unused_bench_gap_candidate_pairs',0),",
        "'unlabelled_rich_starter_bench_internal_gap_candidate_pairs':member_rich_diag.get('starter_bench_internal_gap_candidate_pairs',0),",
    ]
    for anchor in anchors:
        if anchor in py:
            extra=(anchor
                   +"'unlabelled_rich_mixed_bench_gap_candidate_pairs_v171':member_rich_diag.get('mixed_bench_gap_candidate_pairs_v171',0),"
                   +"'unlabelled_rich_mixed_bench_gap_left_uses_v171':member_rich_diag.get('mixed_bench_gap_left_uses_v171',0),"
                   +"'unlabelled_rich_mixed_bench_gap_right_uses_v171':member_rich_diag.get('mixed_bench_gap_right_uses_v171',0),"
                   +"'unlabelled_rich_mixed_bench_gap_max_bytes_v171':member_rich_diag.get('mixed_bench_gap_max_bytes_v171',0),")
            py=py.replace(anchor,extra,1);break
    else:raise RuntimeError('v171 debug handoff anchor missing')

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def mixed_bench_internal_spacing_v171(rows):',
    'def mixed_bench_gap_window_v171(j,left_n,right_n):',
    "if idx<11:return False,0,-1",
    'if not rows[11:] or not all(benchish_v171(r) for r in rows[11:]):return False,0,-1',
    "if agg(pair) not in played_score_pairs:continue",
    "diagnostics['mixed_bench_gap_candidate_pairs_v171']+=1",
    'unlabelled_rich_mixed_bench_gap_candidate_pairs_v171',
    'def used_unused_bench_internal_spacing(rows):',
]:assert token in cpy,token
print('v171 adds a score-constrained retained-side representation with one bounded metadata gap anywhere inside a semantically valid mixed bench; existing ordered used->unused and other layouts remain unchanged')
