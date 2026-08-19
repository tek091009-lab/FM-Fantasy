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

# v99: retained rows can carry a decoded football name even when the numeric player-ID
# representation is not useful as a current-squad anchor in this save/schema. Learn exact
# name->club evidence ONLY from retained sides that have already been registered against an
# authoritative played fixture. Then use repeated exact-name agreement as a separate side-
# identity route. This path never fuzzy-matches names and never teaches from unregistered rows.
store_old="    confirmed_side_cohorts=collections.defaultdict(list)\n    confirmed_cohort_seen=set()\n"
store_new="    confirmed_side_cohorts=collections.defaultdict(list)\n    confirmed_cohort_seen=set()\n    confirmed_retained_name_clubs=collections.defaultdict(set)\n"
if 'confirmed_retained_name_clubs=collections.defaultdict(set)' not in py:
    if store_old not in py:raise RuntimeError('v99 confirmed-name store anchor missing')
    py=py.replace(store_old,store_new,1)

func_anchor="    def confirmed_cohort_club(ids):\n"
func_new="""    def _retained_name_key(row):
        raw=str(row.get('player') or row.get('name') or '').strip()
        if not raw:return ''
        # Placeholders are decoder failures, not player-name evidence.
        if raw.lower().startswith('player id '):return ''
        return ' '.join(raw.casefold().split())

    def confirmed_name_club(rows,ids):
        # Exact aliases only. A name seen for more than one confirmed club is neutralised
        # (transfer, collision or schema ambiguity). Require broad agreement across the side.
        votes=collections.Counter();usable=0;seen=set()
        for row in rows:
            key=_retained_name_key(row)
            if not key or key in seen:continue
            seen.add(key)
            owners=confirmed_retained_name_clubs.get(key,set())
            if len(owners)!=1:
                if len(owners)>1:diagnostics['confirmed_name_ambiguous_aliases']+=1
                continue
            usable+=1;votes[next(iter(owners))]+=1
        if not votes:return None
        ranked=votes.most_common(2);top_eid,top_n=ranked[0];second_n=ranked[1][1] if len(ranked)>1 else 0
        # Seven exact independently confirmed names is intentionally stricter than the
        # ordinary player-ID seed. Also demand >=80% of usable aliases and a four-name margin.
        if top_n<7 or usable<7:return None
        if top_n/max(1,usable)<0.80:return None
        if top_n-second_n<4:return None
        if top_n/max(1,len(rows))<0.32:return None
        direct=direct_anchor_club(ids)
        if direct is not None and direct!=top_eid:
            diagnostics['confirmed_name_conflicts_rejected']+=1;return None
        return top_eid,top_n,usable

    def confirmed_cohort_club(ids):
"""
if 'def confirmed_name_club(rows,ids):' not in py:
    if func_anchor not in py:raise RuntimeError('v99 helper anchor missing')
    py=py.replace(func_anchor,func_new,1)

# Every accepted authoritative match teaches exact retained aliases for the two clubs.
reg_old="        for _eid,_ids in ((leid,_lids),(reid,_rids)):\n            _sig=(_eid,tuple(sorted(_ids)))\n            if _sig not in confirmed_cohort_seen:\n                confirmed_cohort_seen.add(_sig);confirmed_side_cohorts[_eid].append(set(_ids))\n        # Only accepted matches teach temporal membership. Speculative side labels never enter\n"
reg_new="        for _eid,_ids,_rows in ((leid,_lids,left),(reid,_rids,right)):\n            _sig=(_eid,tuple(sorted(_ids)))\n            if _sig not in confirmed_cohort_seen:\n                confirmed_cohort_seen.add(_sig);confirmed_side_cohorts[_eid].append(set(_ids))\n            for _row in _rows:\n                _nkey=_retained_name_key(_row)\n                if _nkey:confirmed_retained_name_clubs[_nkey].add(_eid)\n        # Only accepted matches teach temporal membership. Speculative side labels never enter\n"
if 'confirmed_retained_name_clubs[_nkey].add(_eid)' not in py:
    if reg_old not in py:raise RuntimeError('v99 register-match name learning anchor missing')
    py=py.replace(reg_old,reg_new,1)

pass_anchor="    def single_side_bridge_pass():\n"
pass_new="""    def confirmed_name_fixture_pass():
        # Alternate representation path: exact football-name identity from already-confirmed
        # retained rows. Both sides must independently identify different clubs, then those
        # clubs + exact retained score must leave one unique unused authoritative fixture.
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lids=ids_of(c['left']);rids=ids_of(c['right'])
            lh=confirmed_name_club(c['left'],lids);rh=confirmed_name_club(c['right'],rids)
            if not lh or not rh:continue
            leid,ln,_lu=lh;reid,rn,_ru=rh
            if leid==reid:continue
            opts=candidate_fixture_options(ci,leid,reid)
            if len(opts)!=1:continue
            f,rev,le,re=opts[0]
            proposals.append((min(ln,rn),ln+rn,ci,f,rev,le,re))
        proposals.sort(reverse=True);added=0
        for _mins,_sum,ci,f,rev,leid,reid in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_exact_name_fixture'):
                added+=1;diagnostics['confirmed_name_fixture_matches']+=1
        return added

    def single_side_bridge_pass():
"""
if 'def confirmed_name_fixture_pass():' not in py:
    if pass_anchor not in py:raise RuntimeError('v99 pass anchor missing')
    py=py.replace(pass_anchor,pass_new,1)

diag_anchor="    diagnostics.setdefault('confirmed_cohort_fixture_matches',0)\n"
diag_new=diag_anchor+"    diagnostics.setdefault('confirmed_name_fixture_matches',0)\n    diagnostics.setdefault('confirmed_name_conflicts_rejected',0)\n    diagnostics.setdefault('confirmed_name_ambiguous_aliases',0)\n"
if "diagnostics.setdefault('confirmed_name_fixture_matches',0)" not in py:
    if diag_anchor not in py:raise RuntimeError('v99 diagnostic anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

loop_old="        a=fixture_identity_pass();c=confirmed_cohort_fixture_pass();r=confirmed_roster_fixture_pass();q=confirmed_roster_one_side_pass();g=confirmed_roster_global_constraint_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q or g:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g\n"
loop_new="        a=fixture_identity_pass();c=confirmed_cohort_fixture_pass();r=confirmed_roster_fixture_pass();q=confirmed_roster_one_side_pass();g=confirmed_roster_global_constraint_pass();n=confirmed_name_fixture_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q or g or n:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n\n"
if 'n=confirmed_name_fixture_pass()' not in py:
    if loop_old not in py:raise RuntimeError('v99 fixed-point loop anchor missing')
    py=py.replace(loop_old,loop_new,1)

handoff_anchor="'unlabelled_rich_global_constraint_nonunique_components_rejected':member_rich_diag.get('global_constraint_nonunique_components_rejected',0),"
handoff_new=handoff_anchor+"'unlabelled_rich_confirmed_name_fixture_matches':member_rich_diag.get('confirmed_name_fixture_matches',0),'unlabelled_rich_confirmed_name_conflicts_rejected':member_rich_diag.get('confirmed_name_conflicts_rejected',0),'unlabelled_rich_confirmed_name_ambiguous_aliases':member_rich_diag.get('confirmed_name_ambiguous_aliases',0),"
if 'unlabelled_rich_confirmed_name_fixture_matches' not in py:
    if handoff_anchor not in py:raise RuntimeError('v99 diagnostic handoff anchor missing')
    py=py.replace(handoff_anchor,handoff_new,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in [
    'confirmed_retained_name_clubs=collections.defaultdict(set)',
    'def confirmed_name_club(rows,ids):',
    "raw.lower().startswith('player id ')",
    'top_n<7 or usable<7',
    'top_n/max(1,usable)<0.80',
    'top_n-second_n<4',
    'confirmed_retained_name_clubs[_nkey].add(_eid)',
    'def confirmed_name_fixture_pass():',
    "'unlabelled_retained_confirmed_exact_name_fixture'",
    'n=confirmed_name_fixture_pass()',
    'unlabelled_rich_confirmed_name_fixture_matches',
    'def confirmed_roster_global_constraint_pass():',
    'def confirmed_roster_one_side_pass():',
    'def confirmed_roster_fixture_pass():',
    'def confirmed_cohort_fixture_pass():'
]:assert s in cpy,s
print('v99 exact confirmed-name retained side recovery applied')
