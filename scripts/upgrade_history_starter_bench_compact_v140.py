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

# v140 closes a remaining physical-layout combination. v139 allows one bounded metadata/padding
# gap exactly at XI->bench inside a retained side, but only when the two team arrays themselves are
# separated by the legacy >500-byte team boundary. v122 independently supports a compact 214..500
# byte team boundary, but rejects any side containing an internal >=1500-byte gap. A schema using
# BOTH representations at once is therefore still invisible even though every player stat row is
# valid. Preserve both existing decoders and add a separate combined representation only.

for prereq in [
    'def starter_bench_internal_spacing(rows):',
    'def starter_bench_order_coherent(rows):',
    'def starter_bench_gap_window(j,left_n,right_n):',
    'def compact_window(j,left_n,right_n):',
    "diagnostics['starter_bench_internal_gap_candidate_pairs']+=1",
]:
    if prereq not in py:raise RuntimeError('v140 prerequisite missing: '+prereq)

func_start=py.find('def _rich_candidate_squad_pairs(')
if func_start<0:raise RuntimeError('v140 candidate-pair function missing')
func_end=py.find('\ndef ',func_start+1)
if func_end<0:func_end=len(py)
block=py[func_start:func_end]

helper_anchor='    def starter_bench_gap_window(j,left_n,right_n):\n'
helper_code="""    def starter_bench_compact_window(j,left_n,right_n):
        if j-left_n+1<0 or j+right_n>=len(stats):return None
        left=stats[j-left_n+1:j+1];right=stats[j+1:j+1+right_n]
        if len(left)!=left_n or len(right)!=right_n:return None
        team_gap=int(right[0]['offset'])-int(left[-1]['offset'])
        # This decoder owns only the compact physical team separator. The >500-byte combination
        # remains v139's responsibility.
        if team_gap<214 or team_gap>500:return None
        lok,lspecial,_lgap=starter_bench_internal_spacing(left)
        rok,rspecial,_rgap=starter_bench_internal_spacing(right)
        if not lok or not rok or not (lspecial or rspecial):return None
        if not starter_bench_order_coherent(left) or not starter_bench_order_coherent(right):return None

        # Compare the proposed team separator only with ORDINARY within-side record spacing. The
        # allowed XI->bench metadata gap is deliberately excluded from this baseline; otherwise it
        # would distort the compact-boundary outlier test that v122 established.
        ordinary=[]
        for rows in (left,right):
            for idx in range(len(rows)-1):
                g=int(rows[idx+1]['offset'])-int(rows[idx]['offset'])
                if idx==10 and g>=1500:continue
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
if 'def starter_bench_compact_window(j,left_n,right_n):' not in block:
    if helper_anchor not in block:raise RuntimeError('v140 v139 helper anchor missing')
    block=block.replace(helper_anchor,helper_code+helper_anchor,1)

return_marker='    return pairs\n'
loop="""    # v140: combined XI->bench metadata gap + compact 214..500-byte inter-team separator.
    if played_score_pairs:
        seen_v140={(int(l[0]['offset']),int(l[-1]['offset']),int(r[0]['offset']),int(r[-1]['offset'])) for l,r in pairs if l and r}
        v140_sizes=list(range(18,23))+list(range(11,18))
        for j in range(len(stats)-1):
            for left_n in v140_sizes:
                for right_n in v140_sizes:
                    pair=starter_bench_compact_window(j,left_n,right_n)
                    if not pair:continue
                    if agg(pair) not in played_score_pairs:continue
                    key=(int(pair[0][0]['offset']),int(pair[0][-1]['offset']),int(pair[1][0]['offset']),int(pair[1][-1]['offset']))
                    if key in seen_v140:continue
                    seen_v140.add(key);pairs.append(pair)
                    _lv,_ls,_lg=starter_bench_internal_spacing(pair[0])
                    _rv,_rs,_rg=starter_bench_internal_spacing(pair[1])
                    diagnostics['starter_bench_compact_candidate_pairs']+=1
                    diagnostics['starter_bench_compact_left_gap_uses']+=int(bool(_ls))
                    diagnostics['starter_bench_compact_right_gap_uses']+=int(bool(_rs))
                    diagnostics['starter_bench_compact_max_internal_gap_bytes']=max(int(diagnostics.get('starter_bench_compact_max_internal_gap_bytes',0)),int(_lg or 0),int(_rg or 0))
                    diagnostics['starter_bench_compact_max_team_gap_bytes']=max(int(diagnostics.get('starter_bench_compact_max_team_gap_bytes',0)),int(pair[1][0]['offset'])-int(pair[0][-1]['offset']))
"""
if "diagnostics['starter_bench_compact_candidate_pairs']+=1" not in block:
    idx=block.rfind(return_marker)
    if idx<0:raise RuntimeError('v140 candidate return anchor missing')
    block=block[:idx]+loop+block[idx:]

py=py[:func_start]+block+py[func_end:]

if "'starter_bench_compact_candidate_pairs':0" not in py:
    anchors=["'starter_bench_internal_gap_candidate_pairs':0","'compact_boundary_candidate_pairs':0"]
    for anchor in anchors:
        if anchor in py:
            extra=(anchor+",'starter_bench_compact_candidate_pairs':0"
                   ",'starter_bench_compact_left_gap_uses':0"
                   ",'starter_bench_compact_right_gap_uses':0"
                   ",'starter_bench_compact_max_internal_gap_bytes':0"
                   ",'starter_bench_compact_max_team_gap_bytes':0")
            py=py.replace(anchor,extra,1);break
    else:raise RuntimeError('v140 diagnostics init anchor missing')

if 'unlabelled_rich_starter_bench_compact_candidate_pairs' not in py:
    anchors=[
        "'unlabelled_rich_starter_bench_internal_gap_candidate_pairs':member_rich_diag.get('starter_bench_internal_gap_candidate_pairs',0),",
        "'unlabelled_rich_compact_boundary_candidate_pairs':member_rich_diag.get('compact_boundary_candidate_pairs',0),",
    ]
    for anchor in anchors:
        if anchor in py:
            extra=(anchor
                   +"'unlabelled_rich_starter_bench_compact_candidate_pairs':member_rich_diag.get('starter_bench_compact_candidate_pairs',0),"
                   +"'unlabelled_rich_starter_bench_compact_left_gap_uses':member_rich_diag.get('starter_bench_compact_left_gap_uses',0),"
                   +"'unlabelled_rich_starter_bench_compact_right_gap_uses':member_rich_diag.get('starter_bench_compact_right_gap_uses',0),"
                   +"'unlabelled_rich_starter_bench_compact_max_internal_gap_bytes':member_rich_diag.get('starter_bench_compact_max_internal_gap_bytes',0),"
                   +"'unlabelled_rich_starter_bench_compact_max_team_gap_bytes':member_rich_diag.get('starter_bench_compact_max_team_gap_bytes',0),")
            py=py.replace(anchor,extra,1);break
    else:raise RuntimeError('v140 debug handoff anchor missing')

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def starter_bench_compact_window(j,left_n,right_n):',
    'if team_gap<214 or team_gap>500:return None',
    'if idx==10 and g>=1500:continue',
    "team_gap<max(230,int(med*1.35),q75+16)",
    "if agg(pair) not in played_score_pairs:continue",
    "diagnostics['starter_bench_compact_candidate_pairs']+=1",
    'unlabelled_rich_starter_bench_compact_candidate_pairs',
    'def starter_bench_gap_window(j,left_n,right_n):',
    'def compact_window(j,left_n,right_n):',
]:assert token in cpy,token
print('v140 adds score-constrained combined XI->bench metadata-gap plus compact inter-team-boundary representation while preserving v122 and v139 paths')
