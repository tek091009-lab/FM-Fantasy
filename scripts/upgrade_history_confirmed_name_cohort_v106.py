from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def reconstruct():
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode()

def repack(html):
    packed=base64.b64encode(gzip.compress(html.encode(),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')

html=reconstruct();m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',html)
if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode()
if 'def _retained_name_owner_set(row):' not in py:
    raise RuntimeError('v105 canonical retained-name layer must exist before v106')

# v106 keeps whole confirmed retained sides as a second name-space cohort representation.
# This is deliberately separate from individual name->club voting: a transferred/colliding name
# cannot identify a club by itself, but a large lineup-level overlap can still be strong evidence.
store_old="    confirmed_retained_canonical_name_clubs=collections.defaultdict(set)\n"
store_new=store_old+"    confirmed_retained_name_side_cohorts=collections.defaultdict(list)\n    confirmed_retained_name_side_seen=set()\n"
if 'confirmed_retained_name_side_cohorts=collections.defaultdict(list)' not in py:
    if store_old not in py:raise RuntimeError('v106 name-cohort store anchor missing')
    py=py.replace(store_old,store_new,1)

helper_anchor="    def confirmed_name_club(rows,ids):\n"
helper_insert="""    def _retained_side_name_set(rows):
        # Use v105's collision-safe canonical representation for cohort overlap. Exact ambiguity
        # is irrelevant at this level: no individual name owns the club; the whole confirmed side
        # is the evidence. Placeholders are excluded by the canonical helper.
        return {k for k in (_retained_name_canonical_key(r) for r in rows) if k}

    def confirmed_name_cohort_club(rows,ids):
        names=_retained_side_name_set(rows)
        if len(names)<8:return None
        ranked=[]
        for eid,cohorts in confirmed_retained_name_side_cohorts.items():
            best_shared=0;best_frac=0.0
            for cohort in cohorts:
                shared=len(names & cohort)
                frac=shared/max(1,min(len(names),len(cohort)))
                if (shared,frac)>(best_shared,best_frac):best_shared,best_frac=shared,frac
            # Eight lineup names plus 38% proportional overlap is intentionally stronger than
            # the sparse individual-alias paths. It is aimed at cross-ID/schema drift, not fuzzy matching.
            if best_shared>=8 and best_frac>=0.38:ranked.append((best_shared,best_frac,eid))
        ranked.sort(reverse=True)
        if not ranked:return None
        top=ranked[0];second=ranked[1] if len(ranked)>1 else (0,0.0,None)
        # Require a clear lineup-level margin. Equal/near-equal club cohorts remain unresolved.
        if top[0]-second[0]<3 and top[1]-second[1]<0.15:
            diagnostics['confirmed_name_cohort_conflicts_rejected']+=1;return None
        direct=direct_anchor_club(ids)
        if direct is not None and direct!=top[2]:
            diagnostics['confirmed_name_cohort_conflicts_rejected']+=1;return None
        return top[2],top[0],top[1]

    def confirmed_name_club(rows,ids):
"""
if 'def confirmed_name_cohort_club(rows,ids):' not in py:
    if helper_anchor not in py:raise RuntimeError('v106 helper anchor missing')
    py=py.replace(helper_anchor,helper_insert,1)

# Every already-authoritatively registered match may teach one full retained-name cohort per side.
learn_anchor="                _ckey=_retained_name_canonical_key(_row)\n                if _ckey:confirmed_retained_canonical_name_clubs[_ckey].add(_eid)\n"
learn_new=learn_anchor+"            _ncohort=_retained_side_name_set(_rows)\n            if len(_ncohort)>=8:\n                _nsig=(_eid,tuple(sorted(_ncohort)))\n                if _nsig not in confirmed_retained_name_side_seen:\n                    confirmed_retained_name_side_seen.add(_nsig);confirmed_retained_name_side_cohorts[_eid].append(set(_ncohort))\n"
if 'confirmed_retained_name_side_seen.add(_nsig)' not in py:
    if learn_anchor not in py:raise RuntimeError('v106 register-match cohort learning anchor missing')
    py=py.replace(learn_anchor,learn_new,1)

pass_anchor="    def single_side_bridge_pass():\n"
pass_insert="""    def confirmed_name_cohort_fixture_pass():
        # Stronger two-sided route: both retained sides independently overlap a confirmed name
        # cohort, then club pair + exact retained score must leave ONE unused authoritative fixture.
        proposals=[]
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lids=ids_of(c['left']);rids=ids_of(c['right'])
            lc=confirmed_name_cohort_club(c['left'],lids);rc=confirmed_name_cohort_club(c['right'],rids)
            if not lc or not rc:continue
            leid,lshared,_lf=lc;reid,rshared,_rf=rc
            if leid==reid:continue
            opts=candidate_fixture_options(ci,leid,reid)
            if len(opts)!=1:continue
            f,rev,le,re=opts[0]
            proposals.append((min(lshared,rshared),lshared+rshared,ci,f,rev,le,re))
        proposals.sort(reverse=True);added=0
        for _mn,_sum,ci,f,rev,leid,reid in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_name_cohort_fixture_v106'):
                added+=1;diagnostics['confirmed_name_cohort_fixture_matches']+=1
        return added

    def confirmed_name_cohort_one_side_pass():
        # If exactly one side has strong lineup-level name-cohort identity, let the authoritative
        # calendar supply the opponent ONLY when known club + exact score leaves one real fixture.
        proposals=[];amb=0
        for ci,c in enumerate(cached):
            if ci in used_candidates:continue
            lids=ids_of(c['left']);rids=ids_of(c['right'])
            lc=confirmed_name_cohort_club(c['left'],lids);rc=confirmed_name_cohort_club(c['right'],rids)
            if bool(lc)==bool(rc):continue
            known=lc or rc;known_left=bool(lc);eid,shared,_frac=known
            lscore,rscore=score_of(c);local={}
            for heid,aeid,hs,as_,f in played:
                fk=fixture_identity(f)
                if fk in used_fixtures:continue
                if known_left:
                    if eid==heid and lscore==hs and rscore==as_:local[fk]=(f,False,heid,aeid)
                    if eid==aeid and lscore==as_ and rscore==hs:local[fk]=(f,True,aeid,heid)
                else:
                    if eid==aeid and lscore==hs and rscore==as_:local[fk]=(f,False,heid,aeid)
                    if eid==heid and lscore==as_ and rscore==hs:local[fk]=(f,True,aeid,heid)
            if len(local)==1:
                f,rev,leid,reid=next(iter(local.values()));proposals.append((shared,ci,f,rev,leid,reid))
            elif len(local)>1:amb+=1
        diagnostics['confirmed_name_cohort_one_side_ambiguities_rejected']+=amb
        proposals.sort(reverse=True);added=0
        for _shared,ci,f,rev,leid,reid in proposals:
            if ci in used_candidates or fixture_identity(f) in used_fixtures:continue
            if register_match(ci,f,rev,leid,reid,'unlabelled_retained_confirmed_name_cohort_one_side_v106'):
                added+=1;diagnostics['confirmed_name_cohort_one_side_fixture_matches']+=1
        return added

    def single_side_bridge_pass():
"""
if 'def confirmed_name_cohort_fixture_pass():' not in py:
    if pass_anchor not in py:raise RuntimeError('v106 pass anchor missing')
    py=py.replace(pass_anchor,pass_insert,1)

# Diagnostics.
diag_anchor="    diagnostics.setdefault('confirmed_name_canonical_ambiguous_aliases',0)\n"
diag_new=diag_anchor+"    diagnostics.setdefault('confirmed_name_cohort_fixture_matches',0)\n    diagnostics.setdefault('confirmed_name_cohort_one_side_fixture_matches',0)\n    diagnostics.setdefault('confirmed_name_cohort_one_side_ambiguities_rejected',0)\n    diagnostics.setdefault('confirmed_name_cohort_conflicts_rejected',0)\n"
if "diagnostics.setdefault('confirmed_name_cohort_fixture_matches',0)" not in py:
    if diag_anchor not in py:raise RuntimeError('v106 diagnostic anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

# Insert v106 after all stronger existing ID/roster and individual-name paths in every fixed-point round.
loop_pat=re.compile(r"        a=fixture_identity_pass\(\);c=confirmed_cohort_fixture_pass\(\);r=confirmed_roster_fixture_pass\(\);q=confirmed_roster_one_side_pass\(\);g=confirmed_roster_global_constraint_pass\(\);n=confirmed_name_fixture_pass\(\);h=confirmed_name_one_side_pass\(\);j=confirmed_name_global_constraint_pass\(\);k=confirmed_name_fixture_conditioned_pair_pass\(\);s=confirmed_name_fixture_conditioned_global_pass\(\);b=single_side_bridge_pass\(\)\n        if a or b or c or r or q or g or n or h or j or k or s:\n            diagnostics\['propagation_rounds'\]\+=1\n            diagnostics\['propagation_matches'\]\+=a\+b\+c\+r\+q\+g\+n\+h\+j\+k\+s\n")
if 'u=confirmed_name_cohort_fixture_pass()' not in py:
    mm=loop_pat.search(py)
    if not mm:raise RuntimeError('v106 fixed-point loop anchor missing')
    repl="        a=fixture_identity_pass();c=confirmed_cohort_fixture_pass();r=confirmed_roster_fixture_pass();q=confirmed_roster_one_side_pass();g=confirmed_roster_global_constraint_pass();n=confirmed_name_fixture_pass();h=confirmed_name_one_side_pass();j=confirmed_name_global_constraint_pass();k=confirmed_name_fixture_conditioned_pair_pass();s=confirmed_name_fixture_conditioned_global_pass();u=confirmed_name_cohort_fixture_pass();v=confirmed_name_cohort_one_side_pass();b=single_side_bridge_pass()\n        if a or b or c or r or q or g or n or h or j or k or s or u or v:\n            diagnostics['propagation_rounds']+=1\n            diagnostics['propagation_matches']+=a+b+c+r+q+g+n+h+j+k+s+u+v\n"
    py=py[:mm.start()]+repl+py[mm.end():]

handoff_anchor="'unlabelled_rich_confirmed_name_canonical_ambiguous_aliases':member_rich_diag.get('confirmed_name_canonical_ambiguous_aliases',0),"
handoff_new=handoff_anchor+"'unlabelled_rich_confirmed_name_cohort_fixture_matches':member_rich_diag.get('confirmed_name_cohort_fixture_matches',0),'unlabelled_rich_confirmed_name_cohort_one_side_fixture_matches':member_rich_diag.get('confirmed_name_cohort_one_side_fixture_matches',0),'unlabelled_rich_confirmed_name_cohort_one_side_ambiguities_rejected':member_rich_diag.get('confirmed_name_cohort_one_side_ambiguities_rejected',0),'unlabelled_rich_confirmed_name_cohort_conflicts_rejected':member_rich_diag.get('confirmed_name_cohort_conflicts_rejected',0),"
if 'unlabelled_rich_confirmed_name_cohort_fixture_matches' not in py:
    if handoff_anchor not in py:raise RuntimeError('v106 diagnostic handoff anchor missing')
    py=py.replace(handoff_anchor,handoff_new,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^\"]+)\"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in [
    'confirmed_retained_name_side_cohorts=collections.defaultdict(list)',
    'def _retained_side_name_set(rows):',
    'def confirmed_name_cohort_club(rows,ids):',
    'best_shared>=8 and best_frac>=0.38',
    'confirmed_retained_name_side_seen.add(_nsig)',
    'def confirmed_name_cohort_fixture_pass():',
    'def confirmed_name_cohort_one_side_pass():',
    "'unlabelled_retained_confirmed_name_cohort_fixture_v106'",
    "'unlabelled_retained_confirmed_name_cohort_one_side_v106'",
    'u=confirmed_name_cohort_fixture_pass()',
    'v=confirmed_name_cohort_one_side_pass()',
    'unlabelled_rich_confirmed_name_cohort_fixture_matches',
]:assert s in cpy,s
print('v106 confirmed retained-name cohort recovery applied')
