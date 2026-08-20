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
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',html)
if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode('utf-8')

# v64/v122/v123 cover full matchday arrays of 18..22 players per side. A different retained
# representation can omit unused substitutes and store only the 11 starters plus substitutes who
# actually entered the match. That yields 11..17 rows per side even though every row is a valid
# GAME_MATCH_PLAYER_STATS record. Treat this as a separate physical representation rather than
# widening the existing full-bench decoder. The defining invariant is that rows after the first 11
# must ALL carry a substitution-on minute; an unused bench row is not allowed in this path.

func_start=py.find('def _rich_candidate_squad_pairs(')
if func_start<0:raise RuntimeError('v124 candidate-pair function missing')
func_end=py.find('\ndef ',func_start+1)
if func_end<0:func_end=len(py)
block=py[func_start:func_end]

helper_anchor='    def contiguous_lineup_window(j,left_n,right_n):\n'
helper_code="""    def appearance_only_lineup_coherent(rows):
        # This representation contains the XI plus only substitutes who actually appeared.
        if len(rows)<11 or len(rows)>17:return False
        starters=rows[:11];used_subs=rows[11:]
        if any(int(r.get('sub_on',0) or 0)>0 for r in starters):return False
        # Any row beyond the XI must be an actually-used substitute; otherwise this is a truncated
        # full-bench window rather than the appearance-only representation.
        if any(int(r.get('sub_on',0) or 0)<=0 for r in used_subs):return False
        # League matches should never need an unbounded number of appearing substitutes. Six keeps
        # concussion/exception representations possible without accepting arbitrary long windows.
        if len(used_subs)>6:return False
        def activity(r):
            keys=('goals','assists','yellow_cards','red_cards','passes_attempted','shots_on_target',
                  'shots_blocked','saves','blocks','tackles_attempted','headers_attempted')
            return int(r.get('sub_off',0) or 0)>0 or any(int(r.get(k,0) or 0)>0 for k in keys)
        if sum(1 for r in starters if activity(r))<6:return False
        # A used substitute must have a sensible positive minute. Bounds are intentionally broad
        # enough for stoppage-time encodings while rejecting garbage integer fields.
        if any(int(r.get('sub_on',0) or 0)>130 for r in used_subs):return False
        ons=len(used_subs)
        offs=sum(1 for r in starters if int(r.get('sub_off',0) or 0)>0)
        if abs(ons-offs)>2:return False
        return True

    def appearance_only_contiguous_window(j,left_n,right_n):
        if j-left_n+1<0 or j+right_n>=len(stats):return None
        left=stats[j-left_n+1:j+1];right=stats[j+1:j+1+right_n]
        if len(left)!=left_n or len(right)!=right_n:return None
        gap=right[0]['offset']-left[-1]['offset']
        if gap<214 or gap>500:return None
        lg=[left[k+1]['offset']-left[k]['offset'] for k in range(len(left)-1)]
        rg=[right[k+1]['offset']-right[k]['offset'] for k in range(len(right)-1)]
        internal=lg+rg
        if not internal or max(internal)>=1500:return None
        ordered=sorted(internal);med=ordered[len(ordered)//2];q75=ordered[(3*len(ordered))//4]
        outlier_threshold=max(230,int(med*1.35),q75+16)
        # Large/compact structural separators are handled by window()/compact_window(). This helper
        # exists for the physically contiguous representation only.
        if gap>=outlier_threshold:return None
        lp=[int(x.get('player_id',0) or 0) for x in left]
        rp=[int(x.get('player_id',0) or 0) for x in right]
        if any(x<=0 for x in lp+rp):return None
        if len(set(lp))!=len(lp) or len(set(rp))!=len(rp) or set(lp)&set(rp):return None
        if not appearance_only_lineup_coherent(left) or not appearance_only_lineup_coherent(right):return None
        return left,right

"""
if 'def appearance_only_lineup_coherent(rows):' not in block:
    if helper_anchor not in block:raise RuntimeError('v124 v123 helper anchor missing; apply v123 first')
    block=block.replace(helper_anchor,helper_code+helper_anchor,1)

# Add the appearance-only size family immediately before the function returns. It reuses all three
# already-proven boundary geometries (legacy large gap, v122 compact outlier, v123 contiguous gap),
# but requires the appearance-only lineup invariant on BOTH sides. It is score-constrained before
# entering any of the downstream historical club/fixture logic.
return_marker='    return pairs\n'
appearance_loop="""    # v124: XI + used-subs-only retained arrays (11..17 rows per side).
    if played_score_pairs:
        seen_pair_offsets={(int(l[0]['offset']),int(l[-1]['offset']),int(r[0]['offset']),int(r[-1]['offset'])) for l,r in pairs if l and r}
        for j in range(len(stats)-1):
            for left_n in range(11,18):
                for right_n in range(11,18):
                    pair=window(j,left_n,right_n)
                    if pair and (not appearance_only_lineup_coherent(pair[0]) or not appearance_only_lineup_coherent(pair[1])):pair=None
                    if not pair:
                        pair=compact_window(j,left_n,right_n)
                        if pair and (not appearance_only_lineup_coherent(pair[0]) or not appearance_only_lineup_coherent(pair[1])):pair=None
                    if not pair:pair=appearance_only_contiguous_window(j,left_n,right_n)
                    if not pair:continue
                    if agg(pair) not in played_score_pairs:continue
                    key=(int(pair[0][0]['offset']),int(pair[0][-1]['offset']),int(pair[1][0]['offset']),int(pair[1][-1]['offset']))
                    if key in seen_pair_offsets:continue
                    seen_pair_offsets.add(key);pairs.append(pair)
                    diagnostics['appearance_only_candidate_pairs']+=1
"""
if "diagnostics['appearance_only_candidate_pairs']+=1" not in block:
    idx=block.rfind(return_marker)
    if idx<0:raise RuntimeError('v124 candidate return anchor missing')
    block=block[:idx]+appearance_loop+block[idx:]

py=py[:func_start]+block+py[func_end:]

init_candidates=[
    "'contiguous_lineup_boundary_candidate_pairs':0",
    "'compact_boundary_candidate_pairs':0",
]
if "'appearance_only_candidate_pairs':0" not in py:
    for anchor in init_candidates:
        if anchor in py:
            py=py.replace(anchor,anchor+",'appearance_only_candidate_pairs':0",1)
            break
    else:raise RuntimeError('v124 diagnostics init anchor missing')

handoff_candidates=[
    "'unlabelled_rich_contiguous_lineup_boundary_candidate_pairs':member_rich_diag.get('contiguous_lineup_boundary_candidate_pairs',0),",
    "'unlabelled_rich_compact_boundary_candidate_pairs':member_rich_diag.get('compact_boundary_candidate_pairs',0),",
]
if 'unlabelled_rich_appearance_only_candidate_pairs' not in py:
    for anchor in handoff_candidates:
        if anchor in py:
            py=py.replace(anchor,anchor+"'unlabelled_rich_appearance_only_candidate_pairs':member_rich_diag.get('appearance_only_candidate_pairs',0),",1)
            break
    else:raise RuntimeError('v124 debug handoff anchor missing')

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def appearance_only_lineup_coherent(rows):',
    'if len(rows)<11 or len(rows)>17:return False',
    "if any(int(r.get('sub_on',0) or 0)<=0 for r in used_subs):return False",
    'def appearance_only_contiguous_window(j,left_n,right_n):',
    'for left_n in range(11,18):',
    'for right_n in range(11,18):',
    "if agg(pair) not in played_score_pairs:continue",
    "diagnostics['appearance_only_candidate_pairs']+=1",
    'unlabelled_rich_appearance_only_candidate_pairs',
]:assert token in cpy,token
print('v124 adds score-constrained XI+used-subs-only retained side representation (11..17 rows) alongside full 18..22 matchday arrays')
