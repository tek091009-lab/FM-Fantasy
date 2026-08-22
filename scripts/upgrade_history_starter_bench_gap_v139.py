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

# v139: every existing retained-side geometry still assumes that all player-record starts within
# one team are <1500 bytes apart. That assumption is unnecessarily strong. FM's retained arrays
# have a known semantic boundary after row 11 (starters -> bench), so another schema can place a
# metadata/padding section there while keeping the team as one logical player array. In that case
# every 214-byte GAME_MATCH_PLAYER_STATS row can be valid, but window(), compact_window(), the
# contiguous-lineup path and the appearance-only path all reject the side solely because max(internal)
# is >=1500.
#
# Preserve every existing representation first. Add a separate physical-layout decoder which permits
# at most ONE large internal gap, and ONLY between rows 11 and 12 of a side. All other internal gaps
# must remain ordinary (<1500). The special gap is bounded and must be a strong outlier. This first
# version deliberately keeps the already-proven legacy inter-team separator (>500); compact/contiguous
# team-boundary combinations remain owned by v122/v123 until real-save evidence justifies combining
# both alternate dimensions.

for prereq in [
    'def _rich_candidate_squad_pairs(',
    'def lineup_order_coherent(rows):',
    'def appearance_only_lineup_coherent(rows):',
    "diagnostics['appearance_only_candidate_pairs']+=1",
    "globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1",
]:
    if prereq not in py:raise RuntimeError('v139 prerequisite missing: '+prereq)

func_start=py.find('def _rich_candidate_squad_pairs(')
if func_start<0:raise RuntimeError('v139 candidate-pair function missing')
func_end=py.find('\ndef ',func_start+1)
if func_end<0:func_end=len(py)
block=py[func_start:func_end]

helper_anchor='    def appearance_only_lineup_coherent(rows):\n'
helper_code="""    def starter_bench_internal_spacing(rows):
        # Return (valid, has_special_gap, special_gap_bytes). A side may contain one structural
        # metadata/padding break only at the XI->bench boundary (record 11 -> record 12).
        if len(rows)<11:return False,False,0
        gaps=[int(rows[k+1]['offset'])-int(rows[k]['offset']) for k in range(len(rows)-1)]
        if any(g<214 for g in gaps):return False,False,0
        special=0
        ordinary=[]
        for idx,g in enumerate(gaps):
            if idx==10 and g>=1500:
                special=g
                continue
            if g>=1500:return False,False,0
            ordinary.append(g)
        if not special:return True,False,0
        # Keep this representation bounded. A 1.5..16 KiB XI/bench metadata section is allowed;
        # anything larger remains unresolved until observed in real-save evidence.
        if special>16384:return False,False,0
        if ordinary:
            ordered=sorted(ordinary);med=ordered[len(ordered)//2];q75=ordered[(3*len(ordered))//4]
            if special<max(1500,int(med*2.0),q75+512):return False,False,0
        return True,True,special

    def starter_bench_order_coherent(rows):
        if 18<=len(rows)<=22:return lineup_order_coherent(rows)
        if 11<=len(rows)<=17:return appearance_only_lineup_coherent(rows)
        return False

    def starter_bench_gap_window(j,left_n,right_n):
        if j-left_n+1<0 or j+right_n>=len(stats):return None
        left=stats[j-left_n+1:j+1];right=stats[j+1:j+1+right_n]
        if len(left)!=left_n or len(right)!=right_n:return None
        # v139 changes only the INTERNAL side serialization. Keep the original/proven large
        # inter-team separator for this first decoder so two alternate dimensions are not relaxed
        # simultaneously.
        team_gap=int(right[0]['offset'])-int(left[-1]['offset'])
        if team_gap<=500:return None
        lok,lspecial,lgap=starter_bench_internal_spacing(left)
        rok,rspecial,rgap=starter_bench_internal_spacing(right)
        if not lok or not rok or not (lspecial or rspecial):return None
        if not starter_bench_order_coherent(left) or not starter_bench_order_coherent(right):return None
        lp=[int(x.get('player_id',0) or 0) for x in left]
        rp=[int(x.get('player_id',0) or 0) for x in right]
        if any(x<=0 for x in lp+rp):return None
        if len(set(lp))!=len(lp) or len(set(rp))!=len(rp) or set(lp)&set(rp):return None
        return left,right

"""
if 'def starter_bench_gap_window(j,left_n,right_n):' not in block:
    if helper_anchor not in block:raise RuntimeError('v139 helper insertion anchor missing')
    block=block.replace(helper_anchor,helper_code+helper_anchor,1)

# Add this alternate physical representation immediately before the candidate function returns.
# Search both the full matchday family (18..22) and appearance-only family (11..17), but only when
# the exact aggregate score exists in the authoritative played calendar. Existing paths retain
# priority because duplicate byte-span candidates are ignored.
return_marker='    return pairs\n'
loop="""    # v139: starter->bench metadata/padding gap inside one/both retained team arrays.
    if played_score_pairs:
        seen_v139={(int(l[0]['offset']),int(l[-1]['offset']),int(r[0]['offset']),int(r[-1]['offset'])) for l,r in pairs if l and r}
        v139_sizes=list(range(18,23))+list(range(11,18))
        for j in range(len(stats)-1):
            for left_n in v139_sizes:
                for right_n in v139_sizes:
                    pair=starter_bench_gap_window(j,left_n,right_n)
                    if not pair:continue
                    if agg(pair) not in played_score_pairs:continue
                    key=(int(pair[0][0]['offset']),int(pair[0][-1]['offset']),int(pair[1][0]['offset']),int(pair[1][-1]['offset']))
                    if key in seen_v139:continue
                    seen_v139.add(key);pairs.append(pair)
                    _lv,_ls,_lg=starter_bench_internal_spacing(pair[0])
                    _rv,_rs,_rg=starter_bench_internal_spacing(pair[1])
                    diagnostics['starter_bench_internal_gap_candidate_pairs']+=1
                    diagnostics['starter_bench_internal_gap_left_uses']+=int(bool(_ls))
                    diagnostics['starter_bench_internal_gap_right_uses']+=int(bool(_rs))
                    diagnostics['starter_bench_internal_gap_max_bytes']=max(int(diagnostics.get('starter_bench_internal_gap_max_bytes',0)),int(_lg or 0),int(_rg or 0))
"""
if "diagnostics['starter_bench_internal_gap_candidate_pairs']+=1" not in block:
    idx=block.rfind(return_marker)
    if idx<0:raise RuntimeError('v139 candidate return anchor missing')
    block=block[:idx]+loop+block[idx:]

py=py[:func_start]+block+py[func_end:]

# Diagnostics make the next hard-save run decisive: representation absent vs found-but-unmatched.
init_candidates=[
    "'appearance_only_candidate_pairs':0",
    "'contiguous_lineup_boundary_candidate_pairs':0",
]
if "'starter_bench_internal_gap_candidate_pairs':0" not in py:
    for anchor in init_candidates:
        if anchor in py:
            extra=(anchor+",'starter_bench_internal_gap_candidate_pairs':0"
                   ",'starter_bench_internal_gap_left_uses':0"
                   ",'starter_bench_internal_gap_right_uses':0"
                   ",'starter_bench_internal_gap_max_bytes':0")
            py=py.replace(anchor,extra,1);break
    else:raise RuntimeError('v139 diagnostics init anchor missing')

handoff_candidates=[
    "'unlabelled_rich_appearance_only_candidate_pairs':member_rich_diag.get('appearance_only_candidate_pairs',0),",
    "'unlabelled_rich_contiguous_lineup_boundary_candidate_pairs':member_rich_diag.get('contiguous_lineup_boundary_candidate_pairs',0),",
]
if 'unlabelled_rich_starter_bench_internal_gap_candidate_pairs' not in py:
    for anchor in handoff_candidates:
        if anchor in py:
            extra=(anchor
                   +"'unlabelled_rich_starter_bench_internal_gap_candidate_pairs':member_rich_diag.get('starter_bench_internal_gap_candidate_pairs',0),"
                   +"'unlabelled_rich_starter_bench_internal_gap_left_uses':member_rich_diag.get('starter_bench_internal_gap_left_uses',0),"
                   +"'unlabelled_rich_starter_bench_internal_gap_right_uses':member_rich_diag.get('starter_bench_internal_gap_right_uses',0),"
                   +"'unlabelled_rich_starter_bench_internal_gap_max_bytes':member_rich_diag.get('starter_bench_internal_gap_max_bytes',0),")
            py=py.replace(anchor,extra,1);break
    else:raise RuntimeError('v139 debug handoff anchor missing')

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def starter_bench_internal_spacing(rows):',
    'if idx==10 and g>=1500:',
    'if special>16384:return False,False,0',
    'def starter_bench_gap_window(j,left_n,right_n):',
    'if team_gap<=500:return None',
    'if not lok or not rok or not (lspecial or rspecial):return None',
    "if agg(pair) not in played_score_pairs:continue",
    "diagnostics['starter_bench_internal_gap_candidate_pairs']+=1",
    'unlabelled_rich_starter_bench_internal_gap_candidate_pairs',
    "globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1",
]:assert token in cpy,token
print('v139 adds score-constrained retained sides with one bounded internal XI->bench metadata gap while preserving all existing layouts')
