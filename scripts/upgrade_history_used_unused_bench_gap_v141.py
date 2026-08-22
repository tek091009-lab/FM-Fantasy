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

# v141: v125 proved that the 214-byte retained player-stat representation distinguishes an unused
# bench row (zero rating / zero activity), while v123 uses the first 11 rows as starters and rows
# after that as the bench. Every current full-squad physical-layout decoder still assumes the used
# substitutes and unused bench rows are stored contiguously (<1500-byte internal gaps). Another FM
# schema can serialize "players who appeared" and "unused bench" as separate subgroups with metadata
# between them. In that layout every player row is valid and the team is complete, but window(),
# compact/contiguous, v139 and v140 reject the side because the large internal gap is not XI->bench.
#
# Preserve every existing path. Add a separate representation that allows exactly one bounded large
# internal gap only at a semantically proven USED-SUB -> UNUSED-BENCH transition. This first version
# keeps the legacy >500-byte inter-team separator so only one physical dimension changes at a time.

for prereq in [
    'def _rich_candidate_squad_pairs(',
    'def lineup_order_coherent(rows):',
    "'unrated_inactive_candidate':bool(unrated_inactive)",
    'def starter_bench_internal_spacing(rows):',
    "diagnostics['starter_bench_compact_candidate_pairs']+=1",
    "globals()['_RICH_GLOBAL_NONOVERLAP_SCAN_V138']=1",
]:
    if prereq not in py:raise RuntimeError('v141 prerequisite missing: '+prereq)

func_start=py.find('def _rich_candidate_squad_pairs(')
if func_start<0:raise RuntimeError('v141 candidate-pair function missing')
func_end=py.find('\ndef ',func_start+1)
if func_end<0:func_end=len(py)
block=py[func_start:func_end]

helper_anchor='    def starter_bench_compact_window(j,left_n,right_n):\n'
helper_code="""    def used_unused_bench_internal_spacing(rows):
        # Return (valid, special_gap_bytes, special_gap_index). This representation is only for a
        # complete 18..22-player matchday array containing both used substitutes and unused bench.
        if not (18<=len(rows)<=22):return False,0,-1
        gaps=[int(rows[k+1]['offset'])-int(rows[k]['offset']) for k in range(len(rows)-1)]
        if any(g<214 for g in gaps):return False,0,-1

        def inactive_bench(r):
            if int(r.get('sub_on',0) or 0)>0:return False
            if r.get('unrated_inactive_candidate'):return True
            keys=('goals','assists','yellow_cards','red_cards','passes_attempted','shots_on_target',
                  'shots_blocked','saves','blocks','tackles_attempted','headers_attempted')
            if int(r.get('sub_off',0) or 0)>0:return False
            return not any(int(r.get(k,0) or 0)>0 for k in keys)

        special=[];ordinary=[]
        for idx,g in enumerate(gaps):
            if g>=1500:
                # This path owns only a split INSIDE the bench. v139 owns XI->bench (idx 10).
                if idx<11:return False,0,-1
                special.append((idx,g))
            else:ordinary.append(g)
        if len(special)!=1:return False,0,-1
        idx,g=special[0]
        if g>16384:return False,0,-1

        # The large break must separate two actual semantic subgroups: every bench row before the
        # break has entered the match; every row after it is an unused/inactive bench record.
        used=rows[11:idx+1];unused=rows[idx+1:]
        if not used or not unused:return False,0,-1
        if not all(int(r.get('sub_on',0) or 0)>0 for r in used):return False,0,-1
        if not all(inactive_bench(r) for r in unused):return False,0,-1

        if ordinary:
            ordered=sorted(ordinary);med=ordered[len(ordered)//2];q75=ordered[(3*len(ordered))//4]
            if g<max(1500,int(med*2.0),q75+512):return False,0,-1
        return True,g,idx

    def used_unused_bench_gap_window(j,left_n,right_n):
        if j-left_n+1<0 or j+right_n>=len(stats):return None
        left=stats[j-left_n+1:j+1];right=stats[j+1:j+1+right_n]
        if len(left)!=left_n or len(right)!=right_n:return None
        team_gap=int(right[0]['offset'])-int(left[-1]['offset'])
        if team_gap<=500:return None
        lok,lgap,lidx=used_unused_bench_internal_spacing(left)
        rok,rgap,ridx=used_unused_bench_internal_spacing(right)
        if not lok and not rok:return None
        # A side not using this new representation must still obey the existing ordinary full-array
        # layout. Do not silently permit some other unexplained >=1500-byte internal break.
        if not lok:
            gaps=[int(left[k+1]['offset'])-int(left[k]['offset']) for k in range(len(left)-1)]
            if any(g>=1500 for g in gaps):return None
        if not rok:
            gaps=[int(right[k+1]['offset'])-int(right[k]['offset']) for k in range(len(right)-1)]
            if any(g>=1500 for g in gaps):return None
        if not lineup_order_coherent(left) or not lineup_order_coherent(right):return None
        lp=[int(x.get('player_id',0) or 0) for x in left]
        rp=[int(x.get('player_id',0) or 0) for x in right]
        if any(x<=0 for x in lp+rp):return None
        if len(set(lp))!=len(lp) or len(set(rp))!=len(rp) or set(lp)&set(rp):return None
        return left,right

"""
if 'def used_unused_bench_gap_window(j,left_n,right_n):' not in block:
    if helper_anchor not in block:raise RuntimeError('v141 helper insertion anchor missing')
    block=block.replace(helper_anchor,helper_code+helper_anchor,1)

return_marker='    return pairs\n'
loop="""    # v141: metadata/padding between used substitutes and unused bench rows.
    if played_score_pairs:
        seen_v141={(int(l[0]['offset']),int(l[-1]['offset']),int(r[0]['offset']),int(r[-1]['offset'])) for l,r in pairs if l and r}
        for j in range(len(stats)-1):
            for left_n in range(18,23):
                for right_n in range(18,23):
                    pair=used_unused_bench_gap_window(j,left_n,right_n)
                    if not pair:continue
                    if agg(pair) not in played_score_pairs:continue
                    key=(int(pair[0][0]['offset']),int(pair[0][-1]['offset']),int(pair[1][0]['offset']),int(pair[1][-1]['offset']))
                    if key in seen_v141:continue
                    seen_v141.add(key);pairs.append(pair)
                    _lv,_lg,_li=used_unused_bench_internal_spacing(pair[0])
                    _rv,_rg,_ri=used_unused_bench_internal_spacing(pair[1])
                    diagnostics['used_unused_bench_gap_candidate_pairs']+=1
                    diagnostics['used_unused_bench_gap_left_uses']+=int(bool(_lv))
                    diagnostics['used_unused_bench_gap_right_uses']+=int(bool(_rv))
                    diagnostics['used_unused_bench_gap_max_bytes']=max(int(diagnostics.get('used_unused_bench_gap_max_bytes',0)),int(_lg or 0),int(_rg or 0))
"""
if "diagnostics['used_unused_bench_gap_candidate_pairs']+=1" not in block:
    idx=block.rfind(return_marker)
    if idx<0:raise RuntimeError('v141 candidate return anchor missing')
    block=block[:idx]+loop+block[idx:]

py=py[:func_start]+block+py[func_end:]

if "'used_unused_bench_gap_candidate_pairs':0" not in py:
    anchors=["'starter_bench_compact_candidate_pairs':0","'starter_bench_internal_gap_candidate_pairs':0"]
    for anchor in anchors:
        if anchor in py:
            extra=(anchor+",'used_unused_bench_gap_candidate_pairs':0"
                   ",'used_unused_bench_gap_left_uses':0"
                   ",'used_unused_bench_gap_right_uses':0"
                   ",'used_unused_bench_gap_max_bytes':0")
            py=py.replace(anchor,extra,1);break
    else:raise RuntimeError('v141 diagnostics init anchor missing')

if 'unlabelled_rich_used_unused_bench_gap_candidate_pairs' not in py:
    anchors=[
        "'unlabelled_rich_starter_bench_compact_candidate_pairs':member_rich_diag.get('starter_bench_compact_candidate_pairs',0),",
        "'unlabelled_rich_starter_bench_internal_gap_candidate_pairs':member_rich_diag.get('starter_bench_internal_gap_candidate_pairs',0),",
    ]
    for anchor in anchors:
        if anchor in py:
            extra=(anchor
                   +"'unlabelled_rich_used_unused_bench_gap_candidate_pairs':member_rich_diag.get('used_unused_bench_gap_candidate_pairs',0),"
                   +"'unlabelled_rich_used_unused_bench_gap_left_uses':member_rich_diag.get('used_unused_bench_gap_left_uses',0),"
                   +"'unlabelled_rich_used_unused_bench_gap_right_uses':member_rich_diag.get('used_unused_bench_gap_right_uses',0),"
                   +"'unlabelled_rich_used_unused_bench_gap_max_bytes':member_rich_diag.get('used_unused_bench_gap_max_bytes',0),")
            py=py.replace(anchor,extra,1);break
    else:raise RuntimeError('v141 debug handoff anchor missing')

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def used_unused_bench_internal_spacing(rows):',
    'def used_unused_bench_gap_window(j,left_n,right_n):',
    'if idx<11:return False,0,-1',
    "if not all(int(r.get('sub_on',0) or 0)>0 for r in used):return False,0,-1",
    'if not all(inactive_bench(r) for r in unused):return False,0,-1',
    "if agg(pair) not in played_score_pairs:continue",
    "diagnostics['used_unused_bench_gap_candidate_pairs']+=1",
    'unlabelled_rich_used_unused_bench_gap_candidate_pairs',
    'def starter_bench_compact_window(j,left_n,right_n):',
]:assert token in cpy,token
print('v141 adds score-constrained retained sides with one bounded metadata gap between used substitutes and unused bench rows while preserving all earlier layouts')
