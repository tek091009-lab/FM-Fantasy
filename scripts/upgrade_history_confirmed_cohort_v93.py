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
m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode('utf-8')

# v93: once a retained candidate has passed the existing strict fixture registration,
# its player cohort is authoritative evidence for that club on that historical date.
# Reuse those *confirmed* cohorts to identify rotated sides later in the same cached pass.
# This is not recursive speculative voting: only register_match() successes may populate it.
old="    transfer_conflicts=set()\n    # Confirmed retained matches supply dated club appearances. Keep them separately from the\n"
new="    transfer_conflicts=set()\n    confirmed_side_cohorts=collections.defaultdict(list)\n    confirmed_cohort_seen=set()\n    diagnostics.setdefault('confirmed_cohort_side_labels',0)\n    diagnostics.setdefault('confirmed_cohort_conflicts_rejected',0)\n    # Confirmed retained matches supply dated club appearances. Keep them separately from the\n"
if 'confirmed_side_cohorts=collections.defaultdict(list)' not in py:
    if old not in py:raise RuntimeError('v93 cohort store anchor missing')
    py=py.replace(old,new,1)

old="    def best_side_club(ids,min_score=3.0,min_margin=1.15):\n        scores=side_scores(ids)\n        if not scores or scores[0][0]<min_score:return None\n        second=scores[1][0] if len(scores)>1 else 0.0\n        if scores[0][0]-second<min_margin:return None\n        return scores[0][2],scores[0][0],second,scores[0][1]\n"
new="    def confirmed_cohort_club(ids):\n        # A later retained side may rotate heavily away from today's current squad but still\n        # overlap a side already attached to an authoritative fixture. Require substantial\n        # direct player overlap with a CONFIRMED side and a clear club margin.\n        ranked=[]\n        for eid,cohorts in confirmed_side_cohorts.items():\n            best_shared=0;best_frac=0.0\n            for cohort in cohorts:\n                shared=len(ids & cohort)\n                frac=shared/max(1,min(len(ids),len(cohort)))\n                if (shared,frac)>(best_shared,best_frac):best_shared,best_frac=shared,frac\n            if best_shared>=6 and best_frac>=0.34:ranked.append((best_shared,best_frac,eid))\n        ranked.sort(reverse=True)\n        if not ranked:return None\n        top=ranked[0];second=ranked[1] if len(ranked)>1 else (0,0.0,None)\n        # Seven shared players is strong on its own; six requires a two-player margin.\n        if top[0]<7 and top[0]-second[0]<2:return None\n        if top[0]==second[0] and abs(top[1]-second[1])<0.10:\n            diagnostics['confirmed_cohort_conflicts_rejected']+=1;return None\n        # Never let historical cohort evidence contradict a confident unique CURRENT-squad anchor.\n        direct=direct_anchor_club(ids)\n        if direct is not None and direct!=top[2]:\n            diagnostics['confirmed_cohort_conflicts_rejected']+=1;return None\n        return top[2],top[0],top[1]\n\n    def best_side_club(ids,min_score=3.0,min_margin=1.15):\n        scores=side_scores(ids)\n        if scores and scores[0][0]>=min_score:\n            second=scores[1][0] if len(scores)>1 else 0.0\n            if scores[0][0]-second>=min_margin:return scores[0][2],scores[0][0],second,scores[0][1]\n        cohort=confirmed_cohort_club(ids)\n        if cohort:\n            diagnostics['confirmed_cohort_side_labels']+=1\n            # Return a bounded confidence score compatible with existing callers; fixture\n            # registration still requires exact score and authoritative fixture uniqueness.\n            eid,shared,frac=cohort\n            return eid,4.6+min(2.0,(shared-6)*0.35+frac),0.0,shared\n        return None\n"
if 'def confirmed_cohort_club(ids):' not in py:
    if old not in py:raise RuntimeError('v93 best_side_club anchor missing')
    py=py.replace(old,new,1)

old="        used_fixtures.add(fid);used_candidates.add(ci)\n        # Only accepted matches teach temporal membership. Speculative side labels never enter\n"
new="        used_fixtures.add(fid);used_candidates.add(ci)\n        # v93: only an already-accepted authoritative match may teach a retained cohort.\n        # Store each exact side once; no unconfirmed/propagated candidate can self-reinforce.\n        _lids=ids_of(left);_rids=ids_of(right)\n        for _eid,_ids in ((leid,_lids),(reid,_rids)):\n            _sig=(_eid,tuple(sorted(_ids)))\n            if _sig not in confirmed_cohort_seen:\n                confirmed_cohort_seen.add(_sig);confirmed_side_cohorts[_eid].append(set(_ids))\n        # Only accepted matches teach temporal membership. Speculative side labels never enter\n"
if '_sig=(_eid,tuple(sorted(_ids)))' not in py:
    if old not in py:raise RuntimeError('v93 register_match anchor missing')
    py=py.replace(old,new,1)

# Export the new counters in payload meta when the standard diagnostic handoff is present.
anchor="'unlabelled_rich_unmatched_cached_pairs':member_rich_diag.get('unmatched_cached_pairs',0),"
addition=anchor+"'unlabelled_rich_confirmed_cohort_side_labels':member_rich_diag.get('confirmed_cohort_side_labels',0),'unlabelled_rich_confirmed_cohort_conflicts_rejected':member_rich_diag.get('confirmed_cohort_conflicts_rejected',0),"
if 'unlabelled_rich_confirmed_cohort_side_labels' not in py:
    if anchor not in py:raise RuntimeError('v93 diagnostic handoff anchor missing')
    py=py.replace(anchor,addition,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode()
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct()
mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk)
assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8')
compile(cpy,'fm_importer.py','exec')
assert 'confirmed_side_cohorts=collections.defaultdict(list)' in cpy
assert 'def confirmed_cohort_club(ids):' in cpy
assert 'unlabelled_rich_confirmed_cohort_side_labels' in cpy
assert 'only an already-accepted authoritative match may teach a retained cohort' in cpy
print('v93 confirmed-match cohort identity recovery applied')
