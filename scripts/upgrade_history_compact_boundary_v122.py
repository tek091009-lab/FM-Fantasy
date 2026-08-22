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

# The v64 variable-squad decoder preserved a fixed >500-byte assumption for the gap between
# the two team stat blocks. A stat record itself is 214 bytes, and the same decoder already
# permits internal adjacent record starts up to 1499 bytes apart. Therefore a schema that stores
# the two sides with a smaller 214..500-byte separator can have every player record decoded but
# never produce a match pair. Keep the original >500 path unchanged and add a second, conservative
# compact-boundary representation. It is eligible only when the boundary is an actual local gap
# outlier, both sides contain unique/disjoint stable player IDs, and the aggregate score exists in
# the authoritative played calendar. All existing downstream club/fixture/register_match checks
# remain authoritative.

old_window="""    def window(j,left_n,right_n):
        if j-left_n+1<0 or j+right_n>=len(stats):return None
        left=stats[j-left_n+1:j+1];right=stats[j+1:j+1+right_n]
        if len(left)!=left_n or len(right)!=right_n:return None
        gap=right[0]['offset']-left[-1]['offset']
        max_l=max((left[k+1]['offset']-left[k]['offset'] for k in range(len(left)-1)),default=0)
        max_r=max((right[k+1]['offset']-right[k]['offset'] for k in range(len(right)-1)),default=0)
        if gap<=500 or max_l>=1500 or max_r>=1500:return None
        return left,right
"""
new_window=old_window+"""
    def compact_window(j,left_n,right_n):
        if j-left_n+1<0 or j+right_n>=len(stats):return None
        left=stats[j-left_n+1:j+1];right=stats[j+1:j+1+right_n]
        if len(left)!=left_n or len(right)!=right_n:return None
        gap=right[0]['offset']-left[-1]['offset']
        # Do not compete with the legacy representation. This path exists only for a smaller
        # but still physically non-overlapping separator between two 214-byte stat records.
        if gap<214 or gap>500:return None
        lg=[left[k+1]['offset']-left[k]['offset'] for k in range(len(left)-1)]
        rg=[right[k+1]['offset']-right[k]['offset'] for k in range(len(right)-1)]
        internal=lg+rg
        if not internal or max(internal)>=1500:return None
        ordered=sorted(internal);med=ordered[len(ordered)//2];q75=ordered[(3*len(ordered))//4]
        # The proposed team boundary must be a real structural discontinuity, not merely another
        # ordinary adjacent player-record step inside one long run.
        if gap<max(230,int(med*1.35),q75+16):return None
        lp=[int(x.get('player_id',0) or 0) for x in left]
        rp=[int(x.get('player_id',0) or 0) for x in right]
        if any(x<=0 for x in lp+rp):return None
        if len(set(lp))!=len(lp) or len(set(rp))!=len(rp) or set(lp)&set(rp):return None
        return left,right
"""
if 'def compact_window(j,left_n,right_n):' not in py:
    if old_window not in py:raise RuntimeError('v122 v64 window anchor missing')
    py=py.replace(old_window,new_window,1)

old_strict="""        strict=window(j,20,20)
        if strict:
            pairs.append(strict)
            # If the legacy representation already produces a score that exists in the
            # authoritative league calendar, do not manufacture alternative sizes here.
            if not played_score_pairs or agg(strict) in played_score_pairs:continue
"""
new_strict="""        strict=window(j,20,20)
        if strict:
            pairs.append(strict)
            # If the legacy representation already produces a score that exists in the
            # authoritative league calendar, do not manufacture alternative sizes here.
            if not played_score_pairs or agg(strict) in played_score_pairs:continue
        elif played_score_pairs:
            compact_strict=compact_window(j,20,20)
            if compact_strict and agg(compact_strict) in played_score_pairs:
                pairs.append(compact_strict)
                continue
"""
if 'compact_strict=compact_window(j,20,20)' not in py:
    if old_strict not in py:raise RuntimeError('v122 strict candidate anchor missing')
    py=py.replace(old_strict,new_strict,1)

old_alt="""                pair=window(j,left_n,right_n)
                if not pair:continue
                if played_score_pairs and agg(pair) not in played_score_pairs:continue
"""
new_alt="""                pair=window(j,left_n,right_n)
                if not pair and played_score_pairs:pair=compact_window(j,left_n,right_n)
                if not pair:continue
                if played_score_pairs and agg(pair) not in played_score_pairs:continue
"""
if 'if not pair and played_score_pairs:pair=compact_window(j,left_n,right_n)' not in py:
    if old_alt not in py:raise RuntimeError('v122 alternate candidate anchor missing')
    py=py.replace(old_alt,new_alt,1)

# Count the compact representation from already-cached candidate pairs. No second archive scan.
diag_anchor="        diagnostics['variable_squad_size_candidate_pairs']+=sum(1 for left,right in pairs if len(left)!=20 or len(right)!=20)\n"
diag_new=diag_anchor+"        diagnostics['compact_boundary_candidate_pairs']+=sum(1 for left,right in pairs if 214<=right[0]['offset']-left[-1]['offset']<=500)\n"
if "diagnostics['compact_boundary_candidate_pairs']+=" not in py:
    if diag_anchor not in py:raise RuntimeError('v122 candidate diagnostic anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

init_anchor="        'temporal_transfer_fixture_evidence':0,'variable_squad_size_candidate_pairs':0\n"
init_new="        'temporal_transfer_fixture_evidence':0,'variable_squad_size_candidate_pairs':0,'compact_boundary_candidate_pairs':0\n"
if "'compact_boundary_candidate_pairs':0" not in py:
    if init_anchor not in py:raise RuntimeError('v122 diagnostics init anchor missing')
    py=py.replace(init_anchor,init_new,1)

handoff_candidates=[
    "'unlabelled_rich_variable_squad_size_candidate_pairs':member_rich_diag.get('variable_squad_size_candidate_pairs',0),",
    "'unlabelled_rich_temporal_transfer_fixture_evidence':member_rich_diag.get('temporal_transfer_fixture_evidence',0),",
]
if 'unlabelled_rich_compact_boundary_candidate_pairs' not in py:
    for anchor in handoff_candidates:
        if anchor in py:
            py=py.replace(anchor,anchor+"'unlabelled_rich_compact_boundary_candidate_pairs':member_rich_diag.get('compact_boundary_candidate_pairs',0),",1)
            break
    else:raise RuntimeError('v122 debug handoff anchor missing')

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def compact_window(j,left_n,right_n):',
    'if gap<214 or gap>500:return None',
    "gap<max(230,int(med*1.35),q75+16)",
    "len(set(lp))!=len(lp) or len(set(rp))!=len(rp) or set(lp)&set(rp)",
    'compact_strict=compact_window(j,20,20)',
    'compact_boundary_candidate_pairs',
    "_rich_candidate_squad_pairs(stats,played_score_pairs)",
]:assert token in cpy,token
print('v122 adds score-constrained compact 214..500-byte retained team-boundary representation without weakening legacy >500 path')
