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

# v94: v93 learns strong club cohorts only from matches already attached to authoritative
# fixtures. Use those confirmed cohorts directly for unresolved candidates before the weaker
# one-side bridge. Both sides must independently match a confirmed club cohort with >=7 shared
# players, clubs must differ, and club+score must identify exactly one unused played fixture.
# No archive rescan and no relaxed fixture acceptance.
old="    def single_side_bridge_pass():\n"
new="    def confirmed_cohort_fixture_pass():\n        proposals=[]\n        for ci,c in enumerate(cached):\n            if ci in used_candidates:continue\n            lh=confirmed_cohort_club(ids_of(c['left']));rh=confirmed_cohort_club(ids_of(c['right']))\n            if not lh or not rh:continue\n            leid,lshared,_lfrac=lh;reid,rshared,_rfrac=rh\n            if leid==reid or lshared<7 or rshared<7:continue\n            opts=candidate_fixture_options(ci,leid,reid)\n            if len(opts)!=1:continue\n            f,rev,le,re=opts[0]\n            proposals.append((min(lshared,rshared),lshared+rshared,ci,f,rev,le,re))\n        proposals.sort(reverse=True)\n        added=0\n        for _minshared,_sumshared,ci,f,rev,leid,reid in proposals:\n            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue\n            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_cohort_fixture'):\n                added+=1;diagnostics['confirmed_cohort_fixture_matches']+=1\n        return added\n\n    def single_side_bridge_pass():\n"
if 'def confirmed_cohort_fixture_pass():' not in py:
    if old not in py:raise RuntimeError('v94 insertion anchor missing')
    py=py.replace(old,new,1)

old="    diagnostics.setdefault('confirmed_cohort_conflicts_rejected',0)\n"
new="    diagnostics.setdefault('confirmed_cohort_conflicts_rejected',0)\n    diagnostics.setdefault('confirmed_cohort_fixture_matches',0)\n"
if "diagnostics.setdefault('confirmed_cohort_fixture_matches',0)" not in py:
    if old not in py:raise RuntimeError('v94 diagnostic init anchor missing')
    py=py.replace(old,new,1)

old="        a=fixture_identity_pass();b=single_side_bridge_pass()\n        if a or b:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b\n"
new="        a=fixture_identity_pass();c=confirmed_cohort_fixture_pass();b=single_side_bridge_pass()\n        if a or b or c:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c\n"
if 'c=confirmed_cohort_fixture_pass()' not in py:
    if old not in py:raise RuntimeError('v94 recovery loop anchor missing')
    py=py.replace(old,new,1)

anchor="'unlabelled_rich_confirmed_cohort_conflicts_rejected':member_rich_diag.get('confirmed_cohort_conflicts_rejected',0),"
addition=anchor+"'unlabelled_rich_confirmed_cohort_fixture_matches':member_rich_diag.get('confirmed_cohort_fixture_matches',0),"
if 'unlabelled_rich_confirmed_cohort_fixture_matches' not in py:
    if anchor not in py:raise RuntimeError('v94 diagnostic handoff anchor missing')
    py=py.replace(anchor,addition,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode()
html=html[:m.start(1)]+new_b64+html[m.end(1):]
repack(html)

chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode('utf-8');compile(cpy,'fm_importer.py','exec')
assert 'def confirmed_cohort_fixture_pass():' in cpy
assert 'lshared<7 or rshared<7' in cpy
assert "source_kind,'unlabelled_retained_confirmed_cohort_fixture'" not in cpy  # guard typo shape
assert "'unlabelled_retained_confirmed_cohort_fixture'" in cpy
assert 'c=confirmed_cohort_fixture_pass()' in cpy
assert 'unlabelled_rich_confirmed_cohort_fixture_matches' in cpy
print('v94 direct confirmed-cohort fixture recovery applied')
