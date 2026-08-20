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

# v122 adds a compact-gap representation, but it still requires the boundary between the two
# team arrays to be a local byte-gap outlier. FM's GAME_MATCH_PLAYER_STATS rows are themselves
# ordered as 11 starters followed by the bench. A schema can therefore store team A and team B
# contiguously with an ordinary record-to-record gap, leaving no gap outlier at all. Add a third
# representation that uses the lineup-order invariant instead of a separator-size invariant.
# This is deliberately score-constrained and only runs after both legacy >500 and compact-outlier
# paths fail. It never changes downstream club/fixture/register_match safeguards.

compact_tail="""        if len(set(lp))!=len(lp) or len(set(rp))!=len(rp) or set(lp)&set(rp):return None
        return left,right
"""
contiguous_add=compact_tail+"""
    def lineup_order_coherent(rows):
        if len(rows)<18 or len(rows)>22:return False
        starters=rows[:11];bench=rows[11:]
        # A starter cannot have a substitution-on minute. This is the strongest ordering marker.
        if any(int(r.get('sub_on',0) or 0)>0 for r in starters):return False
        def activity(r):
            # Use only fields already decoded directly from the 214-byte stat record. An unused
            # substitute may have a raw rating but must not carry real match actions.
            keys=('goals','assists','yellow_cards','red_cards','passes_attempted','shots_on_target',
                  'shots_blocked','saves','blocks','tackles_attempted','headers_attempted')
            return int(r.get('sub_off',0) or 0)>0 or any(int(r.get(k,0) or 0)>0 for k in keys)
        # Random windows can contain eleven zero-action records. A real starting XI should show
        # substantial activity even in low-event matches.
        if sum(1 for r in starters if activity(r))<6:return False
        # Bench rows with no substitution-on minute are unused and therefore cannot contain match
        # actions. This is what makes an arbitrary split through one long stat run fail.
        for r in bench:
            if int(r.get('sub_on',0) or 0)<=0 and activity(r):return False
        ons=sum(1 for r in bench if int(r.get('sub_on',0) or 0)>0)
        offs=sum(1 for r in starters if int(r.get('sub_off',0) or 0)>0)
        # Allow red cards and the rare substitute-on/substitute-off case, but reject wildly
        # incoherent windows.
        if abs(ons-offs)>2:return False
        return True

    def contiguous_lineup_window(j,left_n,right_n):
        if j-left_n+1<0 or j+right_n>=len(stats):return None
        left=stats[j-left_n+1:j+1];right=stats[j+1:j+1+right_n]
        if len(left)!=left_n or len(right)!=right_n:return None
        gap=right[0]['offset']-left[-1]['offset']
        # This path is specifically for physically contiguous/ordinary spacing. Larger structural
        # separators belong to the legacy/compact paths and keep priority.
        if gap<214 or gap>500:return None
        lg=[left[k+1]['offset']-left[k]['offset'] for k in range(len(left)-1)]
        rg=[right[k+1]['offset']-right[k]['offset'] for k in range(len(right)-1)]
        internal=lg+rg
        if not internal or max(internal)>=1500:return None
        ordered=sorted(internal);med=ordered[len(ordered)//2];q75=ordered[(3*len(ordered))//4]
        outlier_threshold=max(230,int(med*1.35),q75+16)
        # If it is already a byte-gap outlier, v122 owns it. Here the absence of an outlier is the
        # representation we are trying to decode.
        if gap>=outlier_threshold:return None
        lp=[int(x.get('player_id',0) or 0) for x in left]
        rp=[int(x.get('player_id',0) or 0) for x in right]
        if any(x<=0 for x in lp+rp):return None
        if len(set(lp))!=len(lp) or len(set(rp))!=len(rp) or set(lp)&set(rp):return None
        if not lineup_order_coherent(left) or not lineup_order_coherent(right):return None
        return left,right
"""
if 'def contiguous_lineup_window(j,left_n,right_n):' not in py:
    if compact_tail not in py:raise RuntimeError('v123 compact-window tail anchor missing; apply v122 first')
    py=py.replace(compact_tail,contiguous_add,1)

strict_anchor="""        elif played_score_pairs:
            compact_strict=compact_window(j,20,20)
            if compact_strict and agg(compact_strict) in played_score_pairs:
                pairs.append(compact_strict)
                continue
"""
strict_new=strict_anchor+"""            contiguous_strict=contiguous_lineup_window(j,20,20)
            if contiguous_strict and agg(contiguous_strict) in played_score_pairs:
                pairs.append(contiguous_strict)
                continue
"""
# The contiguous path belongs after compact failed, not inside its success branch.
strict_new="""        elif played_score_pairs:
            compact_strict=compact_window(j,20,20)
            if compact_strict and agg(compact_strict) in played_score_pairs:
                pairs.append(compact_strict)
                continue
            contiguous_strict=contiguous_lineup_window(j,20,20)
            if contiguous_strict and agg(contiguous_strict) in played_score_pairs:
                pairs.append(contiguous_strict)
                continue
"""
if 'contiguous_strict=contiguous_lineup_window(j,20,20)' not in py:
    if strict_anchor not in py:raise RuntimeError('v123 compact strict anchor missing')
    py=py.replace(strict_anchor,strict_new,1)

alt_anchor="""                pair=window(j,left_n,right_n)
                if not pair and played_score_pairs:pair=compact_window(j,left_n,right_n)
                if not pair:continue
                if played_score_pairs and agg(pair) not in played_score_pairs:continue
"""
alt_new="""                pair=window(j,left_n,right_n)
                if not pair and played_score_pairs:pair=compact_window(j,left_n,right_n)
                if not pair and played_score_pairs:pair=contiguous_lineup_window(j,left_n,right_n)
                if not pair:continue
                if played_score_pairs and agg(pair) not in played_score_pairs:continue
"""
if 'pair=contiguous_lineup_window(j,left_n,right_n)' not in py:
    if alt_anchor not in py:raise RuntimeError('v123 alternate candidate anchor missing')
    py=py.replace(alt_anchor,alt_new,1)

# Diagnostics identify whether this representation exists in a future hard-save rerun. It uses
# the same cached candidate pair list and therefore adds no archive rescan.
diag_anchor="        diagnostics['compact_boundary_candidate_pairs']+=sum(1 for left,right in pairs if 214<=right[0]['offset']-left[-1]['offset']<=500)\n"
diag_new=diag_anchor+"        diagnostics['contiguous_lineup_boundary_candidate_pairs']+=sum(1 for left,right in pairs if 214<=right[0]['offset']-left[-1]['offset']<=500 and lineup_order_coherent(left) and lineup_order_coherent(right))\n"
if "diagnostics['contiguous_lineup_boundary_candidate_pairs']+=" not in py:
    if diag_anchor not in py:raise RuntimeError('v123 compact diagnostic anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

init_anchor="'compact_boundary_candidate_pairs':0"
if "'contiguous_lineup_boundary_candidate_pairs':0" not in py:
    if init_anchor not in py:raise RuntimeError('v123 diagnostics init anchor missing')
    py=py.replace(init_anchor,init_anchor+",'contiguous_lineup_boundary_candidate_pairs':0",1)

handoff="'unlabelled_rich_compact_boundary_candidate_pairs':member_rich_diag.get('compact_boundary_candidate_pairs',0),"
if 'unlabelled_rich_contiguous_lineup_boundary_candidate_pairs' not in py:
    if handoff not in py:raise RuntimeError('v123 debug handoff anchor missing')
    py=py.replace(handoff,handoff+"'unlabelled_rich_contiguous_lineup_boundary_candidate_pairs':member_rich_diag.get('contiguous_lineup_boundary_candidate_pairs',0),",1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode('ascii')
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
for token in [
    'def lineup_order_coherent(rows):',
    'def contiguous_lineup_window(j,left_n,right_n):',
    'if gap>=outlier_threshold:return None',
    'if sum(1 for r in starters if activity(r))<6:return False',
    "if int(r.get('sub_on',0) or 0)<=0 and activity(r):return False",
    'contiguous_strict=contiguous_lineup_window(j,20,20)',
    'pair=contiguous_lineup_window(j,left_n,right_n)',
    'contiguous_lineup_boundary_candidate_pairs',
]:assert token in cpy,token
print('v123 adds score-constrained contiguous team-array recovery using 11-starter/bench ordering when no byte-gap boundary exists')
